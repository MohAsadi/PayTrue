// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import {stdError} from "forge-std/StdError.sol";
import "../src/Errors.sol";
import {WidthLib} from "../src/WidthLib.sol";
import {HashModel} from "../src/HashModel.sol";
import {PinModel} from "../src/PinModel.sol";
import {ContainModel} from "../src/ContainModel.sol";
import {TimeModel} from "../src/TimeModel.sol";
import {Permit2Mock} from "../src/Permit2Mock.sol";
import {MigrationModel} from "../src/MigrationModel.sol";
import {Fixture} from "./helpers/Fixture.sol";

/// External wrappers around the pure libraries, so that `vm.expectRevert` can see their reverts.
contract WidthHarness {
    function narrow8(uint256 x) external pure returns (uint256) {
        return WidthLib.toUint8(x);
    }

    function narrow16(uint256 x) external pure returns (uint256) {
        return WidthLib.toUint16(x);
    }

    function narrow32(uint256 x) external pure returns (uint256) {
        return WidthLib.toUint32(x);
    }

    function narrow48(uint256 x) external pure returns (uint256) {
        return WidthLib.toUint48(x);
    }

    function narrow64(uint256 x) external pure returns (uint256) {
        return WidthLib.toUint64(x);
    }

    function narrow160(uint256 x) external pure returns (uint256) {
        return WidthLib.toUint160(x);
    }

    function nextVersion(uint8 kind, uint32 v, PinModel.Pin memory prev, PinModel.Pin memory p) external pure returns (uint32) {
        return PinModel.nextVersion(kind, v, prev, p, 0);
    }

    function accepts(ContainModel.Terms memory m, ContainModel.State memory st, ContainModel.Payment memory p) external pure returns (bool) {
        return ContainModel.accepts(m, st, p);
    }

    function fiat(uint256 amountIn, uint256 price, uint8 decimals) external pure returns (uint256) {
        return HashModel.fiatValueMinor(amountIn, price, decimals);
    }

    function windowIndex(uint256 nowTs, uint256 anchor, uint256 length) external pure returns (uint256) {
        return TimeModel.windowIndex(nowTs, anchor, length, 0);
    }

    function cycleAllowed(uint256 cycleIndex, uint256 nowTs, uint256 anchor, uint256 period) external pure {
        TimeModel.cycleAllowed(cycleIndex, nowTs, anchor, period, 0);
    }
}

/// Integer widths of the reference model (document 12 section 5.3, document 17 section 5.1, PC-16): uint48 expirations at and around
/// 2^48 - 1, the uint160 sentinel, uint32 pin versions and exposure counts, uint256 caps and checked arithmetic, E(0) = infinity, and the
/// cycle and window arithmetic at large values. Every narrowing must revert instead of truncating silently.
contract IntegerWidthTest is Test {
    uint256 internal constant U48 = type(uint48).max;
    uint256 internal constant U160 = type(uint160).max;

    Permit2Mock internal p2;
    WidthHarness internal h;
    address internal owner = address(uint160(0xA11CE));
    address internal token = address(uint160(0x7001));
    address internal spender = address(uint160(0x1000));

    function setUp() public {
        vm.warp(1_800_000_000);
        p2 = new Permit2Mock();
        h = new WidthHarness();
    }

    // ---- uint48 expirations
    function test_Uint48_ExpirationAtTheLimit() public {
        p2.approveAs(owner, token, spender, 100, U48);
        (, uint48 e,) = p2.allowance(owner, token, spender);
        assertEq(uint256(e), U48);
        vm.warp(U48);
        p2.pullAs(spender, owner, token, 1); // usable in the last representable second
        vm.warp(U48 + 1);
        vm.expectRevert(abi.encodeWithSelector(AllowanceExpired.selector, U48));
        p2.pullAs(spender, owner, token, 1); // the comparison is done in uint256: no wrap-around
    }

    function test_Uint48_AboveTheLimitIsRefusedNotTruncated() public {
        vm.expectRevert(AbiOutOfRange.selector);
        p2.approveAs(owner, token, spender, 100, U48 + 1);
        vm.expectRevert(AbiOutOfRange.selector);
        p2.approveAs(owner, token, spender, 100, (uint256(1) << 48) + 5); // would be 5 if truncated
        vm.expectRevert(AbiOutOfRange.selector);
        p2.approveAs(owner, token, spender, 100, type(uint256).max);
        (uint160 amount, uint48 e,) = p2.allowance(owner, token, spender);
        assertEq(uint256(amount), 0);
        assertEq(uint256(e), 0, "nothing was stored");
    }

    /// Documents the hazard the model avoids: an explicit narrowing cast of a non-constant value truncates silently.
    function test_Hazard_ExplicitCastTruncatesSilently() public {
        uint256 big = (uint256(1) << 48) + 5;
        assertEq(uint256(uint48(big)), 5);
        uint256 big160 = (uint256(1) << 160) + 7;
        assertEq(uint256(uint160(big160)), 7);
        uint256 big32 = (uint256(1) << 32) + 9;
        assertEq(uint256(uint32(big32)), 9);
    }

    function test_WidthLib_RefusesWhatACastWouldTruncate() public {
        vm.expectRevert(UnsafeCast.selector);
        h.narrow48((uint256(1) << 48) + 5);
        vm.expectRevert(UnsafeCast.selector);
        h.narrow160((uint256(1) << 160) + 7);
        vm.expectRevert(UnsafeCast.selector);
        h.narrow32((uint256(1) << 32) + 9);
        vm.expectRevert(UnsafeCast.selector);
        h.narrow64(type(uint64).max + uint256(1));
        vm.expectRevert(UnsafeCast.selector);
        h.narrow16(65_536);
        vm.expectRevert(UnsafeCast.selector);
        h.narrow8(256);
        assertEq(h.narrow48(U48), U48);
        assertEq(h.narrow160(U160), U160);
        assertEq(h.narrow32(type(uint32).max), type(uint32).max);
    }

    function testFuzz_NarrowNeverTruncates(uint256 x) public {
        try h.narrow48(x) returns (uint256 r) {
            assertEq(r, x);
            assertLe(x, U48);
        } catch {
            assertGt(x, U48);
        }
        try h.narrow160(x) returns (uint256 r2) {
            assertEq(r2, x);
            assertLe(x, U160);
        } catch {
            assertGt(x, U160);
        }
        try h.narrow32(x) returns (uint256 r3) {
            assertEq(r3, x);
        } catch {
            assertGt(x, type(uint32).max);
        }
    }

    function testFuzz_ApproveNeverTruncates(uint256 amount, uint256 expiration) public {
        bool fits = amount <= U160 && expiration <= U48;
        try p2.approveAs(owner, token, spender, amount, expiration) {
            assertTrue(fits);
            (uint160 a, uint48 e,) = p2.allowance(owner, token, spender);
            assertEq(uint256(a), amount);
            assertEq(uint256(e), expiration == 0 ? vm.getBlockTimestamp() : expiration);
        } catch (bytes memory err) {
            assertFalse(fits);
            assertEq(bytes32(bytes4(err)), bytes32(AbiOutOfRange.selector));
        }
    }

    // ---- uint160
    function test_Uint160_SentinelIsNeverDecremented() public {
        p2.approveAs(owner, token, spender, U160, U48);
        p2.pullAs(spender, owner, token, 10 ** 30);
        p2.pullAs(spender, owner, token, U160);
        (uint160 a,,) = p2.allowance(owner, token, spender);
        assertEq(uint256(a), U160);
        vm.expectRevert(AbiOutOfRange.selector);
        p2.pullAs(spender, owner, token, U160 + 1);
        p2.approveAs(owner, token, spender, U160 - 1, U48); // one below the sentinel is an ordinary, decreasing amount
        p2.pullAs(spender, owner, token, 1);
        (uint160 b,,) = p2.allowance(owner, token, spender);
        assertEq(uint256(b), U160 - 2);
    }

    function test_Uint160_AmountAboveTheLimitIsRefused() public {
        vm.expectRevert(AbiOutOfRange.selector);
        p2.approveAs(owner, token, spender, U160 + 1, U48);
        vm.expectRevert(AbiOutOfRange.selector);
        p2.approveAs(owner, token, spender, uint256(1) << 200, U48);
    }

    /// G1 compares the uint160 allowance with the uint256 per-payment cap: a cap above uint160.max is never satisfied (it is not
    /// truncated to a small number that any allowance would meet).
    function test_G1_CapAboveUint160IsNotTruncated() public {
        Fixture fx = new Fixture();
        ContainModel.Terms memory t = fx.baseTerms(fx.one(fx.T1()));
        t.caps[0][0] = U160 + 1; // 2^160: uint160(cap) would be 0
        address t1 = fx.T1();
        address r0 = fx.R0();
        address r1 = fx.R1();
        (, bytes32 mid) = fx.activateTerms(fx.CUSTOMER(), r0, t);
        fx.grant(t1, r1, U160, fx.FAR()); // the largest possible allowance
        vm.expectRevert(abi.encodeWithSelector(NewPermissionMissing.selector, t1));
        fx.migrate(mid, 0, r1); // (no getter call inside these arguments: vm.expectRevert applies to the next external call)
    }

    // ---- uint32
    function test_Uint32_PinVersionOverflowReverts() public {
        PinModel.Pin memory eoa = PinModel.Pin(1, PinModel.PIN_EOA, address(0), bytes32(0), bytes32(0), 1, 1);
        PinModel.Pin memory changed = PinModel.Pin(1, PinModel.PIN_EOA, address(0), bytes32(0), bytes32(0), 1, 0);
        PinModel.Pin memory atMax = PinModel.Pin(1, PinModel.PIN_EOA, address(0), bytes32(0), bytes32(0), type(uint32).max, 1);
        vm.expectRevert(stdError.arithmeticError);
        h.nextVersion(PinModel.NV_UPDATE, type(uint32).max, eoa, eoa);
        vm.expectRevert(stdError.arithmeticError);
        h.nextVersion(PinModel.NV_SUCCESSOR, 0, atMax, changed); // a changed pin at the maximum version needs version 2^32
        assertEq(uint256(h.nextVersion(PinModel.NV_SUCCESSOR, 0, atMax, atMax)), type(uint32).max, "unchanged keeps the maximum");
        assertEq(uint256(h.nextVersion(PinModel.NV_UPDATE, type(uint32).max - 1, eoa, eoa)), type(uint32).max);
        assertEq(uint256(h.nextVersion(PinModel.NV_FIRST, 0, eoa, eoa)), 1);
    }

    function test_Uint32_ExposureCountOverflowReverts() public {
        Fixture fx = new Fixture();
        MigrationModel mgr = fx.mgr();
        address cust = fx.CUSTOMER();
        address r0 = fx.R0();
        address t1 = fx.T1();
        address t2 = fx.T2();
        address[] memory onlyT1 = fx.one(t1);
        mgr.seedLive(cust, r0, t1, type(uint32).max);
        vm.expectRevert(stdError.arithmeticError);
        fx.activate(r0, onlyT1);
        assertEq(fx.live(r0, t1), type(uint32).max, "the count did not wrap");
        vm.expectRevert(UnsafeCast.selector);
        mgr.seedLive(cust, r0, t2, uint256(type(uint32).max) + 1);
    }

    function test_Uint32_ExposureCountUnderflowReverts() public {
        Fixture fx = new Fixture();
        (, bytes32 mid) = fx.activate(fx.R0(), fx.one(fx.T1()));
        fx.mgr().seedLive(fx.CUSTOMER(), fx.R0(), fx.T1(), 0); // the index lost the mandate (never happens in the specification)
        vm.expectRevert(stdError.arithmeticError);
        fx.revoke(mid);
    }

    // ---- uint256: checked arithmetic and E(0)
    function test_Uint256_UsedPlusAmountNearTheLimitReverts() public {
        ContainModel.Terms memory m = _oneTokenTerms();
        ContainModel.State memory st;
        st.used[0][0] = type(uint256).max;
        ContainModel.Payment memory p = _payment();
        p.a = 1;
        vm.expectRevert(stdError.arithmeticError);
        h.accepts(m, st, p);
        st.used[0][0] = type(uint256).max - 1;
        // the cap of the window is 0 (none): used + a = 2^256 - 1 does not overflow and is within E(0)
        assertTrue(h.accepts(m, st, p));
    }

    function test_Uint256_FiatProductOverflowReverts() public {
        vm.expectRevert(stdError.arithmeticError);
        h.fiat(uint256(1) << 200, uint256(1) << 100, 6);
        assertEq(h.fiat(10 ** 40, 10 ** 30, 18), 10 ** 34);
    }

    function test_EOfZeroIsInfinity() public {
        assertFalse(ContainModel.leE(0, type(uint256).max, false), "no cap is above every finite cap, uint256.max included");
        assertTrue(ContainModel.leE(type(uint256).max, 0, false));
        assertTrue(ContainModel.leE(0, 0, false));
        assertTrue(ContainModel.leE(5, 5, false));
        assertFalse(ContainModel.ltE(0, 0));
        assertTrue(ContainModel.ltE(type(uint256).max, 0));
        ContainModel.Terms memory snap = _oneTokenTerms();
        ContainModel.Terms memory succ = _oneTokenTerms();
        snap.caps[0][0] = type(uint256).max;
        succ.caps[0][0] = 0;
        assertEq(ContainModel.containedMask(succ, snap, 0), 1 << 3, "removing a cap is widening it, even from uint256.max");
        assertEq(ContainModel.containedMask(snap, succ, 0), 0);
        snap.fiat[1] = type(uint256).max;
        succ.fiat[1] = 0;
        assertEq(ContainModel.containedMask(succ, snap, 0), (1 << 3) | (1 << 4));
    }

    // ---- cycle and window arithmetic at large values
    function test_CycleArithmetic_LargeValues() public {
        assertEq(h.windowIndex(type(uint64).max, 0, 2_592_000), uint256(type(uint64).max) / 2_592_000);
        assertEq(h.windowIndex(uint256(1) << 255, 1, 3), ((uint256(1) << 255) - 1) / 3);
        assertEq(h.windowIndex(1_800_000_000 + 2_592_000 - 1, 1_800_000_000, 2_592_000), 0);
        assertEq(h.windowIndex(1_800_000_000 + 2_592_000, 1_800_000_000, 2_592_000), 1);
        h.cycleAllowed(uint256(type(uint64).max) / 2_592_000, type(uint64).max, 0, 2_592_000);
    }

    function test_CycleArithmetic_RevertsInsteadOfWrapping() public {
        vm.expectRevert(CycleNotYetDue.selector);
        h.cycleAllowed(uint256(type(uint64).max) / 2_592_000 + 1, type(uint64).max, 0, 2_592_000);
        vm.expectRevert(stdError.arithmeticError);
        h.windowIndex(99, 100, 10); // before the anchor: the subtraction is checked
        vm.expectRevert(stdError.divisionError);
        h.windowIndex(100, 0, 0);
        vm.expectRevert(CycleNotYetDue.selector);
        h.cycleAllowed(type(uint256).max, 1_800_000_000, 1_800_000_000, 2_592_000);
    }

    // ---- helpers
    function _oneTokenTerms() internal pure returns (ContainModel.Terms memory t) {
        t.expiresAt = 1_900_000_000;
        t.merchantId = bytes32(uint256(77));
        t.nTokens = 1;
        t.tokens[0] = address(uint160(0x7001));
        t.boundsVersion = 5; // the model registry's band [90, 110]
        t.maxChargesPerPeriod = 1;
        t.maxFeeBps = 100;
    }

    function _payment() internal pure returns (ContainModel.Payment memory p) {
        p.tokenId = 1;
        p.a = 1;
        p.tau = 1_800_000_000;
        p.merchant = 77;
        p.price = 100;
        p.age = 1;
        p.sinceLast = 1_000_000;
    }
}
