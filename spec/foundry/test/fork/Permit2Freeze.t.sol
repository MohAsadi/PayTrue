// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import "../../src/Errors.sol";
import {Permit2Mock} from "../../src/Permit2Mock.sol";
import {MockERC20} from "../helpers/MockERC20.sol";

/// The interface of the canonical Permit2 (Uniswap/permit2 at commit cc306b601f172c51bc04334a109e98340456620b, AllowanceTransfer.sol).
interface IPermit2 {
    struct TokenSpenderPair {
        address token;
        address spender;
    }

    struct PermitDetails {
        address token;
        uint160 amount;
        uint48 expiration;
        uint48 nonce;
    }

    struct PermitSingle {
        PermitDetails details;
        address spender;
        uint256 sigDeadline;
    }

    function allowance(address owner, address token, address spender) external view returns (uint160 amount, uint48 expiration, uint48 nonce);
    function approve(address token, address spender, uint160 amount, uint48 expiration) external;
    function permit(address owner, PermitSingle memory permitSingle, bytes calldata signature) external;
    function transferFrom(address from, address to, uint160 amount, address token) external;
    function lockdown(TokenSpenderPair[] calldata approvals) external;
    function invalidateNonces(address token, address spender, uint48 newNonce) external;
    function DOMAIN_SEPARATOR() external view returns (bytes32);
}

/// A minimal contract account: its owner can have it call any contract (the shape of every smart wallet's execute).
contract MiniWallet {
    address public immutable owner;

    constructor(address owner_) {
        owner = owner_;
    }

    function execute(address to, bytes calldata data) external returns (bytes memory out) {
        require(msg.sender == owner, "not owner");
        bool ok;
        (ok, out) = to.call(data);
        if (!ok) {
            assembly ("memory-safe") { // lint: allow assembly
                revert(add(out, 32), mload(out))
            }
        }
    }
}

/// Fork tests of the Permit2 freeze subset (document 16 sections 5.3 and 5.5, document 05 section 2.1) against the real canonical Permit2
/// at 0x000000000022D473030F116dDEE9F6B43aC78BA3, on a fork given by the environment variable ETH_RPC_URL. Without the variable every test
/// is skipped with the message "SKIPPED: ETH_RPC_URL is not set". No real token and no real key is needed: a mock ERC-20 is deployed on the
/// fork and the customer is a pranked address (RV-T07 uses a test key made by makeAddrAndKey).
///
///   RV-T01 lockdown zeroes the amount, keeps expiration and nonce, emits Lockdown, and a pull then reverts InsufficientAllowance(0)
///   RV-T02 as 01 with amount uint160.max (the sentinel becomes 0, not unlimited)
///   RV-T04 lockdown of an already expired allowance does not revert
///   RV-T05 lockdown with no allowance does not revert
///   RV-T07 an allowance created by a signed permit: lockdown as 01, and replaying the old signature fails on the nonce
///   RV-T08 approve(token, router, 0, 0): amount 0, stored expiration = block.timestamp, Approval emitted, a pull reverts
///   RV-T11 the same lockdown for the three account kinds that own an allowance: a plain EOA, an EOA whose code is an EIP-7702 designator, and a
///          contract account that calls Permit2 itself (the owner of the allowance is msg.sender of the call, whatever code the account has)
///   F2     approve OVERWRITES amount and expiration of the shared (owner, token, spender) slot
///   F4     uint160.max is never decremented; a pull above the amount reverts InsufficientAllowance
///   F5     expiration 0 stores block.timestamp
///   MIG-TV-22 / MIG-TV-40 the usability boundary: usable at now == expiration, AllowanceExpired one second later
///   differential: the same operation sequences on Permit2Mock and on the real Permit2 leave identical allowance triples and identical outcomes
contract Permit2FreezeTest is Test {
    address internal constant PERMIT2 = address(uint160(0x00000000000022d473030f116ddee9f6b43ac78ba3));
    bytes32 internal constant PERMIT_DETAILS_TYPEHASH = keccak256("PermitDetails(address token,uint160 amount,uint48 expiration,uint48 nonce)");
    bytes32 internal constant PERMIT_SINGLE_TYPEHASH = keccak256(
        "PermitSingle(PermitDetails details,address spender,uint256 sigDeadline)PermitDetails(address token,uint160 amount,uint48 expiration,uint48 nonce)"
    );

    event Lockdown(address indexed owner, address token, address spender);
    event Approval(address indexed owner, address indexed token, address indexed spender, uint160 amount, uint48 expiration);

    IPermit2 internal p2 = IPermit2(PERMIT2);
    MockERC20 internal token;
    address internal owner;
    uint256 internal ownerKey;
    address internal router;
    address internal otherRouter;
    address internal sink;
    bool internal forkEnabled;

    function setUp() public {
        string memory url = vm.envOr("ETH_RPC_URL", string(""));
        if (bytes(url).length == 0) return;
        uint256 blockNo = vm.envOr("FORK_BLOCK", uint256(0)); // tools/fork_run.py pins the block and records it
        if (blockNo == 0) vm.createSelectFork(url);
        else vm.createSelectFork(url, blockNo);
        forkEnabled = true;
        uint256 expected = vm.envOr("EXPECT_CHAIN_ID", uint256(0));
        require(expected == 0 || expected == block.chainid, "the RPC URL serves another chain than EXPECT_CHAIN_ID");
        require(PERMIT2.code.length > 0, "Permit2 is not deployed on this fork");
        (owner, ownerKey) = makeAddrAndKey("fastpay.owner");
        router = makeAddr("fastpay.router");
        otherRouter = makeAddr("fastpay.otherRouter");
        sink = makeAddr("fastpay.sink");
        token = new MockERC20();
        token.mint(owner, 1_000_000_000_000);
        vm.prank(owner);
        token.approve(PERMIT2, type(uint256).max); // L1: the token allowance to Permit2
    }

    modifier onlyFork() {
        if (!forkEnabled) {
            emit log_string("SKIPPED: ETH_RPC_URL is not set; the Permit2 freeze fork tests did not run");
            vm.skip(true);
        }
        _;
    }

    // ---- helpers
    function _approve(address spender, uint160 amount, uint48 expiration) internal {
        vm.prank(owner);
        p2.approve(address(token), spender, amount, expiration);
    }

    function _lockdown(address spender) internal {
        IPermit2.TokenSpenderPair[] memory pairs = new IPermit2.TokenSpenderPair[](1);
        pairs[0] = IPermit2.TokenSpenderPair(address(token), spender);
        vm.prank(owner);
        p2.lockdown(pairs);
    }

    function _pull(address spender, uint160 amount) internal {
        vm.prank(spender);
        p2.transferFrom(owner, sink, amount, address(token));
    }

    function _triple(address spender) internal view returns (uint256 amount, uint256 expiration, uint256 nonce) {
        (uint160 a, uint48 e, uint48 n) = p2.allowance(owner, address(token), spender);
        return (a, e, n);
    }

    // ---- RV-T01
    function test_RV_T01_LockdownZeroesTheAmountOnly() public onlyFork {
        uint48 exp = uint48(vm.getBlockTimestamp() + 1000);
        _approve(router, 100, exp);
        (, , uint256 nonceBefore) = _triple(router);
        vm.expectEmit(true, false, false, true, PERMIT2);
        emit Lockdown(owner, address(token), router);
        _lockdown(router);
        (uint256 a, uint256 e, uint256 n) = _triple(router);
        assertEq(a, 0);
        assertEq(e, exp, "expiration unchanged");
        assertEq(n, nonceBefore, "nonce unchanged");
        vm.expectRevert(abi.encodeWithSelector(InsufficientAllowance.selector, 0));
        _pull(router, 1);
    }

    // ---- RV-T02
    function test_RV_T02_LockdownOfTheUnlimitedSentinel() public onlyFork {
        _approve(router, type(uint160).max, uint48(vm.getBlockTimestamp() + 1000));
        _lockdown(router);
        (uint256 a,,) = _triple(router);
        assertEq(a, 0, "the sentinel becomes 0, not unlimited");
        vm.expectRevert(abi.encodeWithSelector(InsufficientAllowance.selector, 0));
        _pull(router, 1);
    }

    // ---- RV-T03 (two tokens in one call and an unrelated spender)
    function test_RV_T03_OneCallTwoPairsLeavesOtherSpendersAlone() public onlyFork {
        MockERC20 token2 = new MockERC20();
        vm.startPrank(owner);
        p2.approve(address(token), router, 100, uint48(vm.getBlockTimestamp() + 1000));
        p2.approve(address(token2), router, 100, uint48(vm.getBlockTimestamp() + 1000));
        p2.approve(address(token), otherRouter, 100, uint48(vm.getBlockTimestamp() + 1000));
        IPermit2.TokenSpenderPair[] memory pairs = new IPermit2.TokenSpenderPair[](2);
        pairs[0] = IPermit2.TokenSpenderPair(address(token), router);
        pairs[1] = IPermit2.TokenSpenderPair(address(token2), router);
        p2.lockdown(pairs);
        vm.stopPrank();
        (uint160 a1,,) = p2.allowance(owner, address(token), router);
        (uint160 a2,,) = p2.allowance(owner, address(token2), router);
        (uint160 a3,,) = p2.allowance(owner, address(token), otherRouter);
        assertEq(uint256(a1), 0);
        assertEq(uint256(a2), 0);
        assertEq(uint256(a3), 100, "another spender's allowance is untouched (F3)");
    }

    // ---- RV-T04
    function test_RV_T04_LockdownOfAnExpiredAllowance() public onlyFork {
        _approve(router, 100, uint48(vm.getBlockTimestamp() + 10));
        vm.warp(vm.getBlockTimestamp() + 11);
        _lockdown(router);
        (uint256 a,,) = _triple(router);
        assertEq(a, 0);
    }

    // ---- RV-T05
    function test_RV_T05_LockdownWithNoAllowance() public onlyFork {
        _lockdown(router);
        (uint256 a, uint256 e, uint256 n) = _triple(router);
        assertEq(a, 0);
        assertEq(e, 0);
        assertEq(n, 0);
    }

    // ---- RV-T06 (an attacker's lockdown touches only the attacker's allowances)
    function test_RV_T06_AnAttackersLockdownChangesNothingOfTheOwner() public onlyFork {
        _approve(router, 100, uint48(vm.getBlockTimestamp() + 1000));
        address attacker = makeAddr("attacker");
        IPermit2.TokenSpenderPair[] memory pairs = new IPermit2.TokenSpenderPair[](1);
        pairs[0] = IPermit2.TokenSpenderPair(address(token), router);
        vm.prank(attacker);
        p2.lockdown(pairs);
        (uint256 a,,) = _triple(router);
        assertEq(a, 100);
    }

    // ---- RV-T07
    function _permitDigest(IPermit2.PermitSingle memory ps) internal view returns (bytes32) {
        bytes32 detailsHash = keccak256(abi.encode(PERMIT_DETAILS_TYPEHASH, ps.details.token, ps.details.amount, ps.details.expiration, ps.details.nonce));
        bytes32 structHash = keccak256(abi.encode(PERMIT_SINGLE_TYPEHASH, detailsHash, ps.spender, ps.sigDeadline));
        return keccak256(abi.encodePacked("\x19\x01", p2.DOMAIN_SEPARATOR(), structHash));
    }

    function test_RV_T07_AllowanceFromASignedPermit_LockdownAndReplay() public onlyFork {
        (,, uint48 nonce) = p2.allowance(owner, address(token), router);
        IPermit2.PermitSingle memory ps = IPermit2.PermitSingle(
            IPermit2.PermitDetails(address(token), 100, uint48(vm.getBlockTimestamp() + 1000), nonce), router, vm.getBlockTimestamp() + 1000
        );
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(ownerKey, _permitDigest(ps));
        bytes memory sig = abi.encodePacked(r, s, v);
        p2.permit(owner, ps, sig); // anyone may submit
        (uint256 a,, uint256 n) = _triple(router);
        assertEq(a, 100);
        assertEq(n, uint256(nonce) + 1, "the nonce moved");
        _lockdown(router);
        (uint256 a2,, uint256 n2) = _triple(router);
        assertEq(a2, 0);
        assertEq(n2, n, "lockdown leaves the nonce");
        vm.expectRevert(InvalidNonce.selector); // replaying the old signature fails on the nonce (F6: a stale permit cannot re-grant)
        p2.permit(owner, ps, sig);
    }

    // ---- RV-T08
    function test_RV_T08_ApproveZeroZero() public onlyFork {
        _approve(router, 100, uint48(vm.getBlockTimestamp() + 1000));
        vm.expectEmit(true, true, true, true, PERMIT2);
        emit Approval(owner, address(token), router, 0, 0);
        _approve(router, 0, 0);
        (uint256 a, uint256 e,) = _triple(router);
        assertEq(a, 0);
        assertEq(e, vm.getBlockTimestamp(), "expiration 0 stores vm.getBlockTimestamp() (F5)");
        vm.expectRevert(abi.encodeWithSelector(InsufficientAllowance.selector, 0));
        _pull(router, 1);
        vm.warp(vm.getBlockTimestamp() + 1);
        vm.expectRevert(abi.encodeWithSelector(AllowanceExpired.selector, e));
        _pull(router, 1);
    }


    // ---- RV-T11: the allowance owner is msg.sender of the call to Permit2, whatever code that account has
    function _lockdownBy(address account, address spender) internal {
        IPermit2.TokenSpenderPair[] memory pairs = new IPermit2.TokenSpenderPair[](1);
        pairs[0] = IPermit2.TokenSpenderPair(address(token), spender);
        vm.prank(account);
        p2.lockdown(pairs);
    }

    function test_RV_T11_LockdownForEoa_DelegatedEoa_AndContractAccount() public onlyFork {
        // (a) a plain EOA is RV-T01. (b) an EOA whose code is an EIP-7702 designator (0xef0100 || delegate): the transaction it sends calls
        // Permit2 with the account as msg.sender; the designator is never executed for a call that the account makes.
        address delegated = makeAddr("fastpay.delegated");
        vm.etch(delegated, abi.encodePacked(hex"ef0100", address(uint160(0xD311E6A7E))));
        assertEq(delegated.code.length, 23, "a designator is 23 bytes");
        token.mint(delegated, 1_000);
        vm.prank(delegated);
        p2.approve(address(token), router, 100, uint48(vm.getBlockTimestamp() + 1000));
        (uint160 a1,,) = p2.allowance(delegated, address(token), router);
        assertEq(uint256(a1), 100);
        _lockdownBy(delegated, router);
        (uint160 a2, uint48 e2,) = p2.allowance(delegated, address(token), router);
        assertEq(uint256(a2), 0, "lockdown by a delegated account zeroes its own allowance");
        assertEq(uint256(e2), vm.getBlockTimestamp() + 1000, "expiration unchanged");
        vm.prank(router);
        vm.expectRevert(abi.encodeWithSelector(InsufficientAllowance.selector, 0));
        p2.transferFrom(delegated, sink, 1, address(token));

        // (c) a contract account that calls Permit2 itself through execute()
        MiniWallet w = new MiniWallet(owner);
        token.mint(address(w), 1_000);
        vm.prank(owner);
        w.execute(address(token), abi.encodeCall(MockERC20.approve, (PERMIT2, type(uint256).max)));
        vm.prank(owner);
        w.execute(PERMIT2, abi.encodeCall(IPermit2.approve, (address(token), router, 100, uint48(vm.getBlockTimestamp() + 1000))));
        (uint160 a3,,) = p2.allowance(address(w), address(token), router);
        assertEq(uint256(a3), 100);
        IPermit2.TokenSpenderPair[] memory pairs = new IPermit2.TokenSpenderPair[](1);
        pairs[0] = IPermit2.TokenSpenderPair(address(token), router);
        vm.prank(owner);
        w.execute(PERMIT2, abi.encodeCall(IPermit2.lockdown, (pairs)));
        (uint160 a4,,) = p2.allowance(address(w), address(token), router);
        assertEq(uint256(a4), 0, "lockdown by a contract account zeroes its own allowance");
        vm.prank(router);
        vm.expectRevert(abi.encodeWithSelector(InsufficientAllowance.selector, 0));
        p2.transferFrom(address(w), sink, 1, address(token));
        // the owner of the wallet is not the owner of the allowance: the owner's own allowance was never touched
        (uint160 ownerAmount,,) = p2.allowance(owner, address(token), router);
        assertEq(uint256(ownerAmount), 0);
    }

    // ---- RV-T10 (the cap on invalidation)
    function test_RV_T10_InvalidateNonces_Cap() public onlyFork {
        vm.prank(owner);
        p2.invalidateNonces(address(token), router, 65_535);
        (,, uint256 n) = _triple(router);
        assertEq(n, 65_535);
        vm.prank(owner);
        vm.expectRevert(ExcessiveInvalidation.selector);
        p2.invalidateNonces(address(token), router, uint48(65_535 + 65_536));
        vm.prank(owner);
        vm.expectRevert(InvalidNonce.selector);
        p2.invalidateNonces(address(token), router, 65_535);
    }

    // ---- F2: approve overwrites the shared slot
    function test_F2_ApproveOverwritesTheSharedSlot() public onlyFork {
        _approve(router, 100, uint48(vm.getBlockTimestamp() + 1000));
        _approve(router, 50, uint48(vm.getBlockTimestamp() + 10)); // another lineage's plan lowers amount AND expiration of every sibling
        (uint256 a, uint256 e,) = _triple(router);
        assertEq(a, 50);
        assertEq(e, vm.getBlockTimestamp() + 10);
        vm.warp(vm.getBlockTimestamp() + 11);
        vm.expectRevert(abi.encodeWithSelector(AllowanceExpired.selector, e));
        _pull(router, 1);
    }

    // ---- F4 and the shared budget
    function test_F4_UnlimitedIsNeverDecremented_BoundedIs() public onlyFork {
        _approve(router, type(uint160).max, uint48(vm.getBlockTimestamp() + 1000));
        _pull(router, 1_000_000);
        (uint256 a,,) = _triple(router);
        assertEq(a, type(uint160).max);
        _approve(router, 100, uint48(vm.getBlockTimestamp() + 1000));
        _pull(router, 60);
        vm.expectRevert(abi.encodeWithSelector(InsufficientAllowance.selector, 40));
        _pull(router, 60); // MIG-TV-42: the second lineage finds 40 left
        _pull(router, 40);
        (uint256 b,,) = _triple(router);
        assertEq(b, 0);
    }

    // ---- F5: expiration 0
    function test_F5_ExpirationZeroStoresBlockTimestamp() public onlyFork {
        _approve(router, 100, 0);
        (, uint256 e,) = _triple(router);
        assertEq(e, vm.getBlockTimestamp());
        _pull(router, 1); // usable in that block only
        vm.warp(vm.getBlockTimestamp() + 1);
        vm.expectRevert(abi.encodeWithSelector(AllowanceExpired.selector, e));
        _pull(router, 1);
    }

    // ---- MIG-TV-22 and MIG-TV-40: the usability boundary
    function test_MIG_TV_22_40_UsabilityBoundary() public onlyFork {
        uint48 exp = uint48(vm.getBlockTimestamp() + 100);
        _approve(router, 100, exp);
        vm.warp(exp - 1);
        _pull(router, 1);
        vm.warp(exp); // now == expiration: still usable
        _pull(router, 1);
        vm.warp(uint256(exp) + 1); // one second later: expired
        vm.expectRevert(abi.encodeWithSelector(AllowanceExpired.selector, exp));
        _pull(router, 1);
    }

    // ---- differential: Permit2Mock against the real Permit2, same operations, same outcomes
    function testFuzz_DifferentialAgainstMock(uint256 seed) public onlyFork {
        Permit2Mock mock = new Permit2Mock();
        for (uint256 i = 0; i < 24; ++i) {
            uint256 r = uint256(keccak256(abi.encode(seed, i)));
            uint256 op = r % 6;
            address spender = (r / 8) % 2 == 0 ? router : otherRouter;
            bytes4 realSel;
            bytes4 mockSel;
            if (op == 0 || op == 1) {
                uint160 amount = (r / 16) % 5 == 0 ? type(uint160).max : uint160((r / 32) % 200);
                uint48 exp = (r / 64) % 4 == 0 ? 0 : uint48(vm.getBlockTimestamp() + (r / 128) % 300);
                vm.prank(owner);
                try p2.approve(address(token), spender, amount, exp) {} catch (bytes memory e1) {
                    realSel = bytes4(e1);
                }
                vm.prank(owner);
                try mock.approve(address(token), spender, amount, exp) {} catch (bytes memory e2) {
                    mockSel = bytes4(e2);
                }
            } else if (op == 2) {
                IPermit2.TokenSpenderPair[] memory pairs = new IPermit2.TokenSpenderPair[](1);
                pairs[0] = IPermit2.TokenSpenderPair(address(token), spender);
                Permit2Mock.TokenSpenderPair[] memory mpairs = new Permit2Mock.TokenSpenderPair[](1);
                mpairs[0] = Permit2Mock.TokenSpenderPair(address(token), spender);
                vm.prank(owner);
                p2.lockdown(pairs);
                vm.prank(owner);
                mock.lockdown(mpairs);
            } else if (op == 3) {
                vm.warp(vm.getBlockTimestamp() + 1 + (r / 16) % 200);
            } else if (op == 4) {
                uint160 pull = uint160((r / 16) % 120);
                vm.prank(spender);
                try p2.transferFrom(owner, sink, pull, address(token)) {} catch (bytes memory e3) {
                    realSel = bytes4(e3);
                }
                vm.prank(spender);
                try mock.transferFrom(owner, sink, pull, address(token)) {} catch (bytes memory e4) {
                    mockSel = bytes4(e4);
                }
            } else {
                (,, uint48 cur) = p2.allowance(owner, address(token), spender);
                uint48 target = cur + 1 + uint48((r / 16) % 70_000);
                vm.prank(owner);
                try p2.invalidateNonces(address(token), spender, target) {} catch (bytes memory e5) {
                    realSel = bytes4(e5);
                }
                vm.prank(owner);
                try mock.invalidateNonces(address(token), spender, target) {} catch (bytes memory e6) {
                    mockSel = bytes4(e6);
                }
            }
            assertEq(bytes32(realSel), bytes32(mockSel), "the same operation fails the same way on both");
            (uint160 ra, uint48 re, uint48 rn) = p2.allowance(owner, address(token), spender);
            (uint160 ma, uint48 me, uint48 mn) = mock.allowance(owner, address(token), spender);
            assertEq(uint256(ra), uint256(ma));
            assertEq(uint256(re), uint256(me));
            assertEq(uint256(rn), uint256(mn));
        }
    }
}
