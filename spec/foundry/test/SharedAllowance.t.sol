// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import "../src/Errors.sol";
import {Fixture} from "./helpers/Fixture.sol";
import {MigrationModel} from "../src/MigrationModel.sol";
import {ContainModel} from "../src/ContainModel.sol";

/// Document 12 section 5.3.1 (the shared Permit2 allowance), section 5.5 (Claims 2, 3, 4), section 12 (MIG-TV-30 ... 45).
///
/// The vectors MIG-TV-30 ... 45 themselves are exported from the Python model and run by test/generated/GenScenarios.t.sol
/// (MIG_TV_30 ... MIG_TV_45, MIG_TV_35_* for the router modes). This file EXTENDS them with scenarios that are not in the table:
/// three siblings, partially overlapping token sets, the interruption of siblings by a SECURITY deprecation, clearEmergency, an
/// allowance that is drained by a sibling, and the effect of Permit2's overwrite and lockdown on every sibling.
///
///   E1  three siblings share t1: normal migration of A and B keeps the allowance, C (the last) needs the lockdown
///   E2  partial overlap: A uses {t1,t2}, B uses {t2,t3}; A's exclusive token t1 must be unusable, the shared t2 only bounded
///   E3  a SECURITY-deprecated router is in emergency mode: the lockdown interrupts the siblings until their own successors exist
///   E4  clearEmergency restores the normal mode (and with it the normal-migration rule)
///   E5  a sibling that drained the shared allowance: the last lineage then migrates without a lockdown
///   E6  revoking the only sibling turns the next normal migration into a last-lineage migration
///   E7  a revision on a shared token neither requires nor performs a lockdown; the top-up is G1's business
///   E8  the old router can no longer charge the migrated lineage, whatever the shared allowance is (Post2)
///   E9  a sibling's token that the predecessor does not use is still exposed in emergency mode (the index lists every exposed token)
///   E10 Permit2 lockdown for one token leaves the customer's other allowances to the same router alone (F3)
contract SharedAllowanceTest is Test {
    Fixture internal fx;
    address internal t1;
    address internal t2;
    address internal t3;
    address internal r0;
    address internal r1;

    function setUp() public {
        vm.warp(1_800_000_000);
        fx = new Fixture();
        t1 = fx.T1();
        t2 = fx.T2();
        t3 = fx.T3();
        r0 = fx.R0();
        r1 = fx.R1();
    }

    function _bounded(address token, address router) internal {
        fx.grantBounded(token, router);
    }

    // ---- E1
    function test_E1_ThreeSiblings_LastNeedsLockdown() public {
        (, bytes32 a) = fx.activate(r0, fx.one(t1));
        (, bytes32 b) = fx.activate(r0, fx.one(t1));
        (, bytes32 c) = fx.activate(r0, fx.one(t1));
        _bounded(t1, r0);
        _bounded(t1, r1);
        assertEq(fx.live(r0, t1), 3);
        fx.migrate(a, 0, r1);
        assertEq(fx.live(r0, t1), 2);
        fx.migrate(b, 0, r1);
        assertEq(fx.live(r0, t1), 1);
        (uint256 amount,) = fx.allowanceOf(t1, r0);
        assertEq(amount, 100, "the shared allowance was never touched");
        vm.expectRevert(abi.encodeWithSelector(OldPermissionNotRevoked.selector, t1));
        fx.migrate(c, 0, r1);
        fx.lock(t1, r0);
        fx.migrate(c, 0, r1);
        assertEq(fx.live(r0, t1), 0);
        assertEq(fx.live(r1, t1), 3);
    }

    // ---- E2
    function test_E2_PartialOverlap_ExclusiveTokenMustBeUnusable() public {
        (, bytes32 a) = fx.activate(r0, fx.two(t1, t2));
        fx.activate(r0, fx.two(t2, t3));
        _bounded(t1, r0);
        _bounded(t2, r0);
        _bounded(t3, r0);
        _bounded(t1, r1);
        _bounded(t2, r1);
        // t1 is A's alone (Sib = 0) and usable: refused, and the error names t1, not the shared t2
        vm.expectRevert(abi.encodeWithSelector(OldPermissionNotRevoked.selector, t1));
        fx.migrate(a, 0, r1);
        fx.lock(t1, r0);
        fx.migrate(a, 0, r1); // t2 is shared and bounded: it may stay
        (uint256 amount,) = fx.allowanceOf(t2, r0);
        assertEq(amount, 100);
        assertEq(fx.live(r0, t1), 0);
        assertEq(fx.live(r0, t2), 1);
        assertEq(fx.live(r0, t3), 1);
    }

    function test_E2_SharedTokenUnlimited_IsRefusedWhileExclusiveIsClean() public {
        (, bytes32 a) = fx.activate(r0, fx.two(t1, t2));
        fx.activate(r0, fx.two(t2, t3));
        _bounded(t1, r1);
        _bounded(t2, r1);
        fx.grant(t2, r0, type(uint160).max, fx.FAR());
        vm.expectRevert(abi.encodeWithSelector(ResidualAllowanceUnbounded.selector, t2));
        fx.migrate(a, 0, r1);
        fx.grant(t2, r0, type(uint160).max - 1, fx.FAR());
        fx.migrate(a, 0, r1);
    }

    // ---- E3
    function test_E3_SecurityDeprecation_InterruptsSiblings() public {
        (, bytes32 a) = fx.activate(r0, fx.one(t1));
        (, bytes32 b) = fx.activate(r0, fx.one(t1));
        _bounded(t1, r0);
        _bounded(t1, r1);
        fx.reg().deprecate(r0, r1, 1, 0, 0); // SECURITY: emergency mode, but still chargeable
        vm.expectRevert(ModeMismatch.selector);
        fx.migrate(a, 0, r1);
        vm.expectRevert(abi.encodeWithSelector(OldPermissionNotRevoked.selector, t1));
        fx.migrate(a, 1, r1);
        fx.charge(b, r0, t1, 10, 1); // B charges on the old router while the allowance is usable
        fx.lock(t1, r0);
        fx.migrate(a, 1, r1);
        // the lockdown removed the exposure and with it B's funding: B is ACTIVE but cannot pull until its own successor exists
        vm.expectRevert(abi.encodeWithSelector(InsufficientAllowance.selector, 0));
        fx.charge(b, r0, t1, 10, 2);
        bytes32 b2 = fx.migrate(b, 1, r1);
        fx.charge(b2, r1, t1, 10, 3);
    }

    // ---- E4
    function test_E4_ClearEmergency_RestoresNormalMode() public {
        (, bytes32 a) = fx.activate(r0, fx.one(t1));
        fx.activate(r0, fx.one(t1));
        _bounded(t1, r0);
        _bounded(t1, r1);
        fx.reg().emergencyDisable(r0);
        vm.expectRevert(ModeMismatch.selector);
        fx.migrate(a, 0, r1);
        fx.reg().clearEmergency(r0);
        fx.migrate(a, 0, r1); // a sibling remains and the allowance is bounded: normal migration is allowed again
    }

    // ---- E5
    function test_E5_SiblingDrainsTheShareThenLastLineageNeedsNoLockdown() public {
        (, bytes32 a) = fx.activate(r0, fx.one(t1));
        (, bytes32 b) = fx.activate(r0, fx.one(t1));
        fx.grant(t1, r0, 50, fx.FAR());
        _bounded(t1, r1);
        fx.migrate(a, 0, r1); // B remains: bounded residual stays
        fx.charge(b, r0, t1, 50, 1); // B drains the whole share
        (uint256 amount,) = fx.allowanceOf(t1, r0);
        assertEq(amount, 0);
        fx.migrate(b, 0, r1); // Sib = 0 and the allowance is unusable (amount 0): accepted without a lockdown
    }

    // ---- E6
    function test_E6_RevokingTheOnlySibling_MakesTheNextMigrationALastLineageOne() public {
        (, bytes32 a) = fx.activate(r0, fx.one(t1));
        (, bytes32 b) = fx.activate(r0, fx.one(t1));
        _bounded(t1, r0);
        _bounded(t1, r1);
        fx.revoke(b);
        assertEq(fx.live(r0, t1), 1);
        vm.expectRevert(abi.encodeWithSelector(OldPermissionNotRevoked.selector, t1));
        fx.migrate(a, 0, r1);
    }

    // ---- E7
    function test_E7_RevisionOnSharedTokenTouchesNeitherAllowanceNorSibling() public {
        (bytes32 la, bytes32 a) = fx.activate(r0, fx.one(t1));
        (, bytes32 b) = fx.activate(r0, fx.one(t1));
        _bounded(t1, r0);
        MigrationModel mgr = fx.mgr();
        bytes32 before = mgr.mandateDigest(b);
        // a revision on the same router with a higher per-payment cap (60 instead of 50): widenedMask bit 2
        ContainModel.Terms memory nt = mgr.mandateTerms(a);
        nt.caps[0][0] = 60;
        MigrationModel.Auth memory au = mgr.buildAuth(fx.activeOf(la), 2, r0, nt, mgr.mandatePin(a), vm.getBlockTimestamp() + 10, 77);
        assertEq(uint256(au.widenedMask), 4);
        mgr.activateSuccessor(a, 2, r0, nt, mgr.mandatePin(a), au, MigrationModel.Access(true, 0, false), 0);
        assertEq(mgr.mandateDigest(b), before, "a sibling is untouched");
        (uint256 amount,) = fx.allowanceOf(t1, r0);
        assertEq(amount, 100);
        assertEq(fx.live(r0, t1), 2, "the net change of a revision on the same router is zero");
    }

    // ---- E8
    function test_E8_OldRouterCannotChargeTheMigratedLineageWhateverTheAllowance() public {
        (bytes32 la, bytes32 a) = fx.activate(r0, fx.one(t1));
        fx.activate(r0, fx.one(t1));
        _bounded(t1, r0);
        _bounded(t1, r1);
        bytes32 n = fx.migrate(a, 0, r1);
        vm.expectRevert(MandateNotConsumable.selector);
        fx.charge(a, r0, t1, 10, 1); // the predecessor is revoked
        vm.expectRevert(WrongRouter.selector);
        fx.charge(n, r0, t1, 10, 1); // the successor is bound to R1
        fx.charge(n, r1, t1, 10, 1);
        assertTrue(fx.authRouter(la, r1));
        assertFalse(fx.authRouter(la, r0));
    }

    // ---- E9
    function test_E9_EmergencyListsEverySiblingToken() public {
        (, bytes32 a) = fx.activate(r0, fx.one(t1));
        fx.activate(r0, fx.one(t2));
        fx.activate(r0, fx.one(t3));
        _bounded(t1, r0);
        _bounded(t2, r0);
        _bounded(t3, r0);
        _bounded(t1, r1);
        fx.reg().emergencyDisable(r0);
        fx.lock(t1, r0);
        vm.expectRevert(abi.encodeWithSelector(OldPermissionNotRevoked.selector, t2));
        fx.migrate(a, 1, r1);
        fx.lock(t2, r0);
        vm.expectRevert(abi.encodeWithSelector(OldPermissionNotRevoked.selector, t3));
        fx.migrate(a, 1, r1);
        fx.lock(t3, r0);
        fx.migrate(a, 1, r1);
    }

    // ---- E10
    function test_E10_LockdownOfOneTokenLeavesTheOthersAlone() public {
        _bounded(t1, r0);
        _bounded(t2, r0);
        _bounded(t1, r1);
        fx.lock(t1, r0);
        (uint256 a1,) = fx.allowanceOf(t1, r0);
        (uint256 a2,) = fx.allowanceOf(t2, r0);
        (uint256 a3,) = fx.allowanceOf(t1, r1);
        assertEq(a1, 0);
        assertEq(a2, 100);
        assertEq(a3, 100);
        (, uint256 e1) = fx.allowanceOf(t1, r0);
        assertEq(e1, fx.FAR(), "lockdown keeps the expiration (F3)");
    }
}
