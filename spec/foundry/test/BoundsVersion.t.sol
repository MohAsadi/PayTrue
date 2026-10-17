// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import "../src/Errors.sol";
import "../src/Mutants.sol";
import {ContainModel} from "../src/ContainModel.sol";
import {MigrationModel} from "../src/MigrationModel.sol";
import {PinModel} from "../src/PinModel.sol";
import {Fixture} from "./helpers/Fixture.sol";
import {ScenarioVM} from "./helpers/ScenarioVM.sol";
import "./generated/GenOps.sol";

/// Finding F-09 and ADR-020: the price band is not a pair in the mandate. A mandate carries `boundsVersion`; the band [lo, hi] of a
/// (token, currency, boundsVersion) is read from a registry whose published versions never change (here: ContainModel.band, the model
/// registry). K.6 is "the version is the predecessor's"; widenedMask bit 6 is set by a longer quote age or any other version; a charge
/// that needs a price is accepted only inside the band of the version, and version 0 or an unpublished version has the empty band.
contract BoundsVersionTest is Test {
    Fixture internal fx;

    function setUp() public {
        vm.warp(1_800_000_000);
        fx = new Fixture();
    }

    function _bands() internal pure returns (uint256[2][8] memory b) {
        b[1] = [uint256(98), 102];
        b[2] = [uint256(95), 105];
        b[3] = [uint256(96), 104];
        b[4] = [uint256(94), 106];
        b[5] = [uint256(90), 110];
        b[0] = [uint256(1), 0];
        b[6] = [uint256(1), 0];
        b[7] = [uint256(1), 0];
    }

    function test_RegistryBands() public {
        uint256[2][8] memory want = _bands();
        for (uint32 v = 0; v < 8; ++v) {
            (uint256 lo, uint256 hi) = ContainModel.band(v);
            assertEq(lo, want[v][0]);
            assertEq(hi, want[v][1]);
        }
        (uint256 lo2, uint256 hi2) = ContainModel.band(type(uint32).max);
        assertEq(lo2, 1);
        assertEq(hi2, 0);
    }

    /// K.6 and widenedMask bit 6, every pair of versions 0..7: a difference in either direction is a violation / a widening, equality is neither.
    function test_K6AndWidenedMaskBit6FollowTheVersion() public {
        for (uint32 a = 0; a < 8; ++a) {
            for (uint32 b = 0; b < 8; ++b) {
                ContainModel.Terms memory snap = fx.baseTerms(fx.one(fx.T1()));
                ContainModel.Terms memory succ = fx.baseTerms(fx.one(fx.T1()));
                snap.boundsVersion = a;
                succ.boundsVersion = b;
                assertEq(ContainModel.containedMask(succ, snap, 0), a == b ? 0 : 1 << 5, "K.6 is bit 5 of the containment mask");
                assertEq(ContainModel.widenedMask(succ, snap), a == b ? 0 : 1 << 6, "bit 6 of the widened mask");
            }
        }
    }

    /// The mutant that skips K.6 is visible: the same pair is contained when the clause is skipped.
    function test_K6SkipMutantAcceptsAChangedVersion() public {
        ContainModel.Terms memory snap = fx.baseTerms(fx.one(fx.T1()));
        ContainModel.Terms memory succ = fx.baseTerms(fx.one(fx.T1()));
        succ.boundsVersion = snap.boundsVersion + 1;
        assertEq(ContainModel.containedMask(succ, snap, 0), 1 << 5);
        assertEq(ContainModel.containedMask(succ, snap, M_C1_K6_SKIP), 0);
        succ.boundsVersion = snap.boundsVersion - 1;
        assertEq(ContainModel.containedMask(succ, snap, 0), 1 << 5);
        assertEq(ContainModel.containedMask(succ, snap, M_C1_K6_SKIP), 0);
    }

    function _state() internal pure returns (ContainModel.State memory st) {
        st.chargesInPeriod = 0;
    }

    function _payment(uint256 price) internal pure returns (ContainModel.Payment memory p) {
        p.tokenId = 1;
        p.a = 1;
        p.tau = 1_800_000_000;
        p.merchant = 0xA1;
        p.hasFiat = true;
        p.fiat = 1;
        p.age = 1;
        p.price = price;
        p.sinceLast = 1_000_000;
    }

    /// `accepts` reads the band of the version: inside [lo, hi] accepted, one step outside refused; the empty band accepts no price.
    function test_AcceptsReadsTheBandOfTheVersion() public {
        uint256[2][8] memory want = _bands();
        for (uint32 v = 0; v < 8; ++v) {
            ContainModel.Terms memory m = fx.baseTerms(fx.one(fx.T1()));
            m.boundsVersion = v;
            for (uint256 price = 85; price <= 115; ++price) {
                bool inside = price >= want[v][0] && price <= want[v][1];
                assertEq(ContainModel.accepts(m, _state(), _payment(price)), inside, "a priced charge is accepted exactly inside the band");
            }
            ContainModel.Payment memory noFiat = _payment(0);
            noFiat.hasFiat = false;
            assertTrue(ContainModel.accepts(m, _state(), noFiat), "a charge without a fiat quote does not read the band");
        }
    }

    /// A migration that changes the version is refused by the manager (K.6), in both directions.
    function test_ManagerRefusesAMigrationThatChangesTheVersion() public {
        address t1 = fx.T1();
        address r1 = fx.R1();
        (, bytes32 p0) = fx.activate(fx.R0(), fx.one(t1));
        fx.grantBounded(t1, r1);
        fx.lock(t1, fx.R0());
        MigrationModel mgr = fx.mgr();
        PinModel.Pin memory pin = mgr.mandatePin(p0);
        for (uint32 v = 0; v < 4; ++v) {
            if (v == 1) continue; // the base terms have version 1
            ContainModel.Terms memory n = mgr.mandateTerms(p0);
            n.boundsVersion = v;
            MigrationModel.Auth memory au = mgr.buildAuth(p0, 0, r1, n, pin, block.timestamp + 100, 100 + v);
            assertEq(uint256(au.widenedMask), 0, "a migration signs no widening");
            vm.expectRevert(TermsNotContained.selector);
            mgr.activateSuccessor(p0, 0, r1, n, pin, au, MigrationModel.Access(true, 0, false), 0);
        }
        // the same migration with the predecessor's version goes through
        ContainModel.Terms memory same = mgr.mandateTerms(p0);
        MigrationModel.Auth memory ok = mgr.buildAuth(p0, 0, r1, same, pin, block.timestamp + 100, 200);
        mgr.activateSuccessor(p0, 0, r1, same, pin, ok, MigrationModel.Access(true, 0, false), 0);
    }

    /// A revision may change the version; the mask it signs must be exactly the computed one (bit 6), whichever way the version moves.
    function test_ManagerAcceptsARevisionWithBit6() public {
        address t1 = fx.T1();
        address r0 = fx.R0();
        (, bytes32 p0) = fx.activate(r0, fx.one(t1));
        fx.grantBounded(t1, r0);
        MigrationModel mgr = fx.mgr();
        PinModel.Pin memory pin = mgr.mandatePin(p0);
        ContainModel.Terms memory n = mgr.mandateTerms(p0);
        n.boundsVersion = 2;
        MigrationModel.Auth memory au = mgr.buildAuth(p0, 2, r0, n, pin, block.timestamp + 100, 7);
        assertEq(uint256(au.widenedMask), 1 << 6);
        // zero (or any other mask) is refused; bit 6 is accepted
        MigrationModel.Auth memory zeroMask = mgr.buildAuth(p0, 2, r0, n, pin, block.timestamp + 100, 8);
        zeroMask.widenedMask = 0;
        vm.expectRevert(WidenedMaskMismatch.selector);
        mgr.activateSuccessor(p0, 2, r0, n, pin, zeroMask, MigrationModel.Access(true, 0, false), 0);
        bytes32 p1 = mgr.activateSuccessor(p0, 2, r0, n, pin, au, MigrationModel.Access(true, 0, false), 0);
        assertEq(uint256(mgr.mandateTerms(p1).boundsVersion), 2);
        // and back to version 1 (version - 1) is a revision with bit 6 again
        ContainModel.Terms memory back = mgr.mandateTerms(p1);
        back.boundsVersion = 1;
        MigrationModel.Auth memory au2 = mgr.buildAuth(p1, 2, r0, back, pin, block.timestamp + 100, 9);
        assertEq(uint256(au2.widenedMask), 1 << 6);
        bytes32 p2 = mgr.activateSuccessor(p1, 2, r0, back, pin, au2, MigrationModel.Access(true, 0, false), 0);
        assertEq(uint256(mgr.mandateTerms(p2).boundsVersion), 1);
    }

    // ------------------------------------------------------------------------------------------------------------ the retired scenario field
    /// Field 13 of TERMS_SET was the upper price bound. The number is retired: the scenario machine raises RetiredTermsField (the Python
    /// machine raises RetiredField for the same program); field 12 is the bounds version; an unknown field still fails its expectation.
    function test_RetiredScenarioField13() public {
        assertEq(T_BVER, 12);
        assertEq(T_RETIRED_BMAX, 13);
        ScenarioVM machine = new ScenarioVM();
        vm.expectRevert(abi.encodeWithSignature("RetiredTermsField()"));
        machine.exec(OP_TERMS_SET, 0, T_RETIRED_BMAX, 0, 0, 5);
        // as a program: the instruction cannot succeed
        uint256[] memory prog = new uint256[](WORDS);
        prog[0] = OP_TERMS_SET;
        prog[2] = T_RETIRED_BMAX;
        prog[5] = 5;
        assertEq(machine.run(prog, 0), 1, "a program that sets the retired field fails");
        // and an instruction that expects it to revert with some other error does not match either
        prog[6] = 1;
        assertEq(machine.run(prog, 0), 1);
        // field 12 sets the bounds version
        prog[2] = T_BVER;
        prog[6] = 0;
        prog[5] = 3;
        assertEq(machine.run(prog, 0), 0);
        // an unknown field (18) still fails
        prog[2] = 18;
        assertEq(machine.run(prog, 0), 1);
    }
}
