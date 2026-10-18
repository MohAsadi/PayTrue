// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import "../src/Errors.sol";
import {TimeModel} from "../src/TimeModel.sol";
import {Permit2Mock} from "../src/Permit2Mock.sol";
import {RegistryModel} from "../src/RegistryModel.sol";
import {SignerSetModel} from "../src/SignerSetModel.sol";
import {ContainModel} from "../src/ContainModel.sol";
import {Fixture} from "./helpers/Fixture.sol";

contract TimeHarness {
    function quoteTimes(uint256 issuedAt, uint256 validAfter, uint256 validUntil, uint256 maxAge, uint256 registryTtl, uint256 nowTs) external pure {
        TimeModel.quoteTimes(issuedAt, validAfter, validUntil, maxAge, registryTtl, nowTs, 0);
    }

    function windowIndex(uint256 nowTs, uint256 anchor, uint256 length) external pure returns (uint256) {
        return TimeModel.windowIndex(nowTs, anchor, length, 0);
    }

    function cycleAllowed(uint256 cycleIndex, uint256 nowTs, uint256 anchor, uint256 period) external pure {
        TimeModel.cycleAllowed(cycleIndex, nowTs, anchor, period, 0);
    }

    function batchCheck(uint256 n) external pure {
        TimeModel.batchCheck(n, 0);
    }
}

/// Every time comparison of the reference model, with the clock set (vm.warp) to the exact second on each side of it:
///   Permit2 usability and expiration 0 (MIG-TV-22, MIG-TV-40, RV-T04, RV-T08, F5), the new-router allowance (G1), the authorization
///   deadline (A2), the mandate expiry (G1 of a charge, L1, retire), the quote times Q9..Q12, the signer-set grace and its boundaries
///   (Q13, CAP-TV-14, 15, 25, 26), the registry notice, sunset, retention and rollback windows, the window and cycle grid (PC-10, PC-16)
///   and MAX_BATCH.
/// The exported scenarios TB_*, MIG_TV_22*, MIG_TV_40D and CAP_TV_* replay the same boundaries from the Python oracle; the tests here
/// are written independently, in Solidity, with the clock moved by hand.
contract TimestampBoundaryTest is Test {
    uint256 internal constant T0 = 1_800_000_000;

    Fixture internal fx;
    TimeHarness internal h;
    address internal owner = address(uint160(0xA11CE));
    address internal token = address(uint160(0x7001));
    address internal spender = address(uint160(0x1000));
    // The router and token addresses are kept in variables: `vm.expectRevert` applies to the NEXT external call, so a getter call such as
    // `fx.R1()` written inside the arguments of the call under test would consume the expectation instead of the call under test.
    address internal r0;
    address internal r1;
    address internal t1;

    function setUp() public {
        vm.warp(T0);
        fx = new Fixture();
        h = new TimeHarness();
        r0 = fx.R0();
        r1 = fx.R1();
        t1 = fx.T1();
    }

    // ---- Permit2: usable at now == expiration, expired one second later; expiration 0 stores block.timestamp
    function test_Permit2_UsableAtExpiration_ExpiredOneSecondLater() public {
        Permit2Mock p2 = fx.p2();
        p2.approveAs(owner, token, spender, 100, T0 + 5);
        vm.warp(T0 + 5);
        p2.pullAs(spender, owner, token, 10);
        vm.warp(T0 + 6);
        vm.expectRevert(abi.encodeWithSelector(AllowanceExpired.selector, T0 + 5));
        p2.pullAs(spender, owner, token, 10);
    }

    function test_Permit2_ExpirationZeroStoresBlockTimestamp() public {
        Permit2Mock p2 = fx.p2();
        vm.warp(T0 + 7);
        p2.approveAs(owner, token, spender, 100, 0);
        (, uint48 e,) = p2.allowance(owner, token, spender);
        assertEq(uint256(e), T0 + 7);
        p2.pullAs(spender, owner, token, 1); // usable in that block
        vm.warp(T0 + 8);
        vm.expectRevert(abi.encodeWithSelector(AllowanceExpired.selector, T0 + 7));
        p2.pullAs(spender, owner, token, 1);
    }

    function test_Permit2_LockdownKeepsTheExpiration() public {
        Permit2Mock p2 = fx.p2();
        p2.approveAs(owner, token, spender, 100, T0 + 50);
        p2.lockdownAs(owner, token, spender);
        (uint160 a, uint48 e,) = p2.allowance(owner, token, spender);
        assertEq(uint256(a), 0);
        assertEq(uint256(e), T0 + 50);
        vm.expectRevert(abi.encodeWithSelector(InsufficientAllowance.selector, 0));
        p2.pullAs(spender, owner, token, 1);
    }

    // ---- O1N boundary for the last lineage (MIG-TV-22 and MIG-TV-40)
    function _lastLineage() internal returns (bytes32 mid) {
        (, mid) = fx.activate(r0, fx.one(t1));
        fx.grantBounded(t1, r1);
    }

    function test_O1N_ExpirationEqualsNow_StillUsable_Reverts() public {
        bytes32 mid = _lastLineage();
        fx.grant(t1, r0, 100, vm.getBlockTimestamp());
        vm.expectRevert(abi.encodeWithSelector(OldPermissionNotRevoked.selector, t1));
        fx.migrate(mid, 0, r1);
        vm.warp(vm.getBlockTimestamp() + 1); // one second later the allowance is expired
        fx.migrate(mid, 0, r1);
    }

    function test_O1N_ExpirationOneSecondBeforeNow_Accepted() public {
        bytes32 mid = _lastLineage();
        fx.grant(t1, r0, 100, vm.getBlockTimestamp() - 1);
        fx.migrate(mid, 0, r1);
    }

    function test_O1N_ExpirationOneSecondAfterNow_Reverts() public {
        bytes32 mid = _lastLineage();
        fx.grant(t1, r0, 100, vm.getBlockTimestamp() + 1);
        vm.expectRevert(abi.encodeWithSelector(OldPermissionNotRevoked.selector, t1));
        fx.migrate(mid, 0, r1);
    }

    function test_O1N_AmountZero_Accepted() public {
        bytes32 mid = _lastLineage();
        fx.grant(t1, r0, 0, fx.FAR());
        fx.migrate(mid, 0, r1);
    }

    // ---- G1: the new-router allowance
    function test_G1_NewAllowanceExpiringNow_Accepted_OneSecondBefore_Refused() public {
        (, bytes32 mid) = fx.activate(r0, fx.one(t1));
        fx.grant(t1, r1, 50, vm.getBlockTimestamp() - 1);
        vm.expectRevert(abi.encodeWithSelector(NewPermissionMissing.selector, t1));
        fx.migrate(mid, 0, r1);
        fx.grant(t1, r1, 50, vm.getBlockTimestamp());
        fx.migrate(mid, 0, r1);
    }

    // ---- A2: the authorization deadline
    function test_A2_DeadlineEqualsNow_Accepted_OneSecondLate_Refused() public {
        bytes32 mid = _lastLineage();
        fx.lock(t1, r0);
        vm.expectRevert(AuthorizationExpired.selector);
        fx.migrateWith(mid, 0, r1, vm.getBlockTimestamp() - 1, true);
        fx.migrateWith(mid, 0, r1, vm.getBlockTimestamp(), true);
    }

    // ---- mandate expiry: tau < expiresAt; retire needs now >= expiresAt; L1
    function test_MandateExpiry_Boundaries() public {
        ContainModel.Terms memory t = fx.baseTerms(fx.one(t1));
        t.expiresAt = uint64(T0 + 100);
        (, bytes32 mid) = fx.activateTerms(fx.CUSTOMER(), r0, t);
        fx.grantBounded(t1, r0);
        fx.grantBounded(t1, r1);
        vm.warp(T0 + 99);
        fx.charge(mid, r0, t1, 10, 1);
        vm.expectRevert(NotRetirable.selector);
        fx.retire(mid);
        vm.warp(T0 + 100);
        vm.expectRevert(MandateNotConsumable.selector);
        fx.charge(mid, r0, t1, 10, 2);
        vm.expectRevert(WrongPredecessor.selector); // L1: an expired predecessor is terminal
        fx.migrate(mid, 0, r1);
        fx.retire(mid);
        (,, bool retired) = fx.statusOf(mid);
        assertTrue(retired);
    }

    function test_MandateExpiry_SuccessorAllowedOneSecondBefore() public {
        ContainModel.Terms memory t = fx.baseTerms(fx.one(t1));
        t.expiresAt = uint64(T0 + 100);
        (, bytes32 mid) = fx.activateTerms(fx.CUSTOMER(), r0, t);
        fx.grantBounded(t1, r1);
        vm.warp(T0 + 99);
        fx.lock(t1, r0);
        fx.migrate(mid, 0, r1);
    }

    // ---- quote times Q9..Q12
    function test_QuoteTimes_Boundaries() public {
        uint256 n = T0 + 100;
        vm.warp(n);
        h.quoteTimes(n, n, n + 120, 120, 300, n); // validAfter = now, TTL = min(maxAge, registry) = 120
        vm.expectRevert(QuoteNotYetValid.selector);
        h.quoteTimes(n, n + 1, n + 120, 120, 300, n); // validAfter = now + 1
        h.quoteTimes(n - 1, n - 1, n, 120, 300, n); // validUntil = now
        vm.expectRevert(QuoteExpired.selector);
        h.quoteTimes(n - 2, n - 2, n - 1, 120, 300, n); // validUntil = now - 1
        vm.expectRevert(QuoteTtlTooLong.selector);
        h.quoteTimes(n, n, n + 121, 120, 300, n); // TTL 121 > 120
        vm.expectRevert(QuoteTtlTooLong.selector);
        h.quoteTimes(n, n, n + 121, 300, 120, n); // the registry ceiling is the smaller one
        h.quoteTimes(n, n, n + 120, 300, 120, n);
        vm.expectRevert(QuoteTimesInvalid.selector);
        h.quoteTimes(n + 1, n, n + 120, 120, 300, n); // issuedAt > validAfter
        vm.expectRevert(QuoteTimesInvalid.selector);
        h.quoteTimes(n, n + 5, n + 4, 120, 300, n); // validAfter > validUntil
        h.quoteTimes(n, n, n, 0, 300, n); // a zero TTL under a zero maxQuoteAge
    }

    // ---- signer sets: the grace, its two boundaries and issuedAt == retiredAt
    function _rotated() internal returns (SignerSetModel ss, uint256 retiredAt, address k1) {
        ss = new SignerSetModel(300);
        k1 = address(uint160(0x9001));
        address[] memory m = new address[](1);
        m[0] = k1;
        ss.proposeSignerSet(0, 1, m, 0);
        ss.activateSignerSet(0, 1, 0);
        ss.proposeSignerSet(0, 2, m, 0);
        vm.warp(T0 + 1000);
        ss.activateSignerSet(0, 2, 0);
        retiredAt = T0 + 1000;
    }

    function test_SignerSet_GraceBoundaries() public {
        (SignerSetModel ss, uint256 tr, address k1) = _rotated();
        vm.warp(tr + 300);
        ss.verify(k1, 1, tr - 1, 0); // issuedAt = retiredAt - 1, consumed at retiredAt + GRACE: accepted
        vm.warp(tr + 301);
        vm.expectRevert(QuoteSignerSetRetired.selector);
        ss.verify(k1, 1, tr - 1, 0); // one second later: refused
        vm.warp(tr);
        vm.expectRevert(QuoteSignerSetRetired.selector);
        ss.verify(k1, 1, tr, 0); // issuedAt = retiredAt (not strictly earlier)
        ss.verify(k1, 1, tr - 1, 0);
        ss.verify(k1, 2, tr, 0); // the current set accepts it
    }

    function test_SignerSet_RemovalHasNoGrace() public {
        (SignerSetModel ss, uint256 tr, address k1) = _rotated();
        vm.warp(tr + 100);
        ss.verify(k1, 1, tr - 10, 0);
        ss.removeQuoteSigner(1, k1);
        vm.expectRevert(QuoteSignerRemoved.selector);
        ss.verify(k1, 1, tr - 10, 0); // in the removal block, inside the grace: refused
        vm.expectRevert(QuoteSignerRemoved.selector);
        ss.verify(k1, 2, tr + 1, 0);
    }

    // ---- registry: notice, sunset, retention, rollback window
    function test_Registry_NoticeSunsetRetentionBoundaries() public {
        RegistryModel reg = new RegistryModel();
        address a = address(uint160(0xA0));
        address b = address(uint160(0xB0));
        reg.registerActive(a, bytes32(uint256(1)), 1, 0);
        reg.registerActive(b, bytes32(uint256(2)), 2, 0);
        uint256 standard = reg.MIN_NOTICE_STANDARD();
        vm.expectRevert(NoticeTooShort.selector);
        reg.deprecate(a, b, 0, vm.getBlockTimestamp() + standard - 1, 0);
        reg.deprecate(a, b, 0, vm.getBlockTimestamp() + standard, 0);
        uint256 dep = vm.getBlockTimestamp();
        vm.warp(dep + standard - 1);
        vm.expectRevert(NotYetSunset.selector);
        reg.sunset(a, 0);
        vm.warp(dep + standard);
        reg.sunset(a, 0);
        uint256 retention = reg.RETENTION();
        vm.warp(dep + standard + retention - 1);
        vm.expectRevert(RetentionNotElapsed.selector);
        reg.retire(a, 0);
        vm.warp(dep + standard + retention);
        reg.retire(a, 0);
    }

    function test_Registry_SecurityNoticeIsShorter() public {
        RegistryModel reg = new RegistryModel();
        address a = address(uint160(0xA0));
        address b = address(uint160(0xB0));
        reg.registerActive(a, bytes32(uint256(1)), 1, 0);
        reg.registerActive(b, bytes32(uint256(2)), 2, 0);
        uint256 sec = reg.MIN_NOTICE_SECURITY();
        vm.expectRevert(NoticeTooShort.selector);
        reg.deprecate(a, b, 1, vm.getBlockTimestamp() + sec - 1, 0);
        reg.deprecate(a, b, 1, vm.getBlockTimestamp() + sec, 0);
    }

    function test_Registry_RollbackWindow() public {
        RegistryModel reg = new RegistryModel();
        address a = address(uint160(0xA0));
        address b = address(uint160(0xB0));
        reg.registerActive(a, bytes32(uint256(1)), 1, 0);
        reg.registerActive(b, bytes32(uint256(2)), 2, 0);
        reg.deprecate(a, b, 0, 0, 0);
        uint256 dep = vm.getBlockTimestamp();
        uint256 window = reg.ROLLBACK_WINDOW();
        vm.warp(dep + window - 1);
        assertTrue(reg.isBindable(a, 0), "bindable one second before the window closes");
        vm.warp(dep + window);
        assertFalse(reg.isBindable(a, 0), "not bindable once now = deprecatedAt + window");
        assertTrue(reg.isChargeable(a), "a deprecated router still charges");
    }

    // ---- the window and cycle grid
    function test_WindowGrid_ChangesExactlyAtTheBoundary() public {
        uint256[3] memory lens = [uint256(86_400), 604_800, 2_592_000];
        for (uint256 i = 0; i < 3; ++i) {
            for (uint256 k = 1; k <= 3; ++k) {
                assertEq(h.windowIndex(T0 + k * lens[i] - 1, T0, lens[i]), k - 1);
                assertEq(h.windowIndex(T0 + k * lens[i], T0, lens[i]), k);
                assertEq(h.windowIndex(T0 + k * lens[i] + 1, T0, lens[i]), k);
            }
        }
    }

    function test_CycleIndex_Boundaries() public {
        uint256 p = 2_592_000;
        h.cycleAllowed(2, T0 + 3 * p - 1, T0, p);
        vm.expectRevert(CycleNotYetDue.selector);
        h.cycleAllowed(3, T0 + 3 * p - 1, T0, p);
        h.cycleAllowed(3, T0 + 3 * p, T0, p);
        h.cycleAllowed(0, T0 + 3 * p, T0, p); // a late cycle is allowed
    }

    function test_MaxBatch_Boundary() public {
        h.batchCheck(TimeModel.MAX_BATCH);
        vm.expectRevert(BatchTooLarge.selector);
        h.batchCheck(TimeModel.MAX_BATCH + 1);
    }
}
