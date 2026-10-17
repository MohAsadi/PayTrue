// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Base} from "./helpers/Base.sol";
import {MockERC20} from "./helpers/MockERC20.sol";
import {FastPayTypes as T} from "../src/generated/FastPayTypes.sol";
import {PaymentRouter} from "../src/PaymentRouter.sol";
import "../src/Errors.sol";

/// A token that keeps one percent of every transfer, to exercise the router's minimum-output check (G8, I-MINOUT).
contract FeeOnTransferToken is MockERC20 {
    function transferFrom(address from, address to, uint256 amount) external override returns (bool) {
        uint256 allowed = allowance[from][msg.sender];
        if (allowed != type(uint256).max) allowance[from][msg.sender] = allowed - amount;
        balanceOf[from] -= amount;
        balanceOf[to] += amount - amount / 100;
        return true;
    }
}

/// Pay Once on the real router and the rebuilt Permit2: a SignatureTransfer batch with the PayOnceIntent as the witness. The router is the signed
/// spender, the recipient and the fee are bound through the witness, and nothing is left behind (I-PO-NOSTANDING, I-ZEROBAL).
contract PayOnceTest is Base {
    uint256 constant GROSS = 50_000_000;
    uint256 constant FEE = 250_000; // 50 bps, the controller's rate
    uint256 constant NET = GROSS - FEE;
    uint256 constant P2_NONCE = 0xabc;

    bytes4 constant ERR_INVALID_SIGNER = bytes4(keccak256("InvalidSigner()"));
    bytes4 constant ERR_INVALID_NONCE = bytes4(keccak256("InvalidNonce()"));

    uint256 deadline;

    function setUp() public override {
        super.setUp();
        _fund(customer, usdc, 1_000e6);
        deadline = block.timestamp + 300;
    }

    function _intent() internal view returns (T.PayOnceIntent memory i) {
        i.paymentId = keccak256("order-1");
        i.merchantId = MERCHANT;
        i.recipient = merchantWallet;
        i.feeRecipient = feeWallet;
        i.token = address(usdc);
        i.grossAmountIn = GROSS;
        i.merchantAmount = NET;
        i.feeAmount = FEE;
        i.payer = customer;
        i.validUntil = uint64(deadline);
        i.termsHash = keccak256("order terms shown to the customer");
        i.quoteHash = bytes32(0);
    }

    /// The customer's Permit2 signature for this intent and this spender.
    function _signPermit(T.PayOnceIntent memory i, address spender, uint256 nonce_, uint256 dl) internal view returns (bytes memory) {
        address[] memory toks = new address[](2);
        toks[0] = i.token;
        toks[1] = i.token;
        uint256[] memory amts = new uint256[](2);
        amts[0] = i.merchantAmount;
        amts[1] = i.feeAmount;
        bytes32 structHash = T.permit2BatchWitnessTransferFromHash(toks, amts, spender, nonce_, dl, i);
        return _sign(customerKey, T.digest(T.permit2DomainSeparator(block.chainid, CANONICAL), structHash));
    }

    function _pay(PaymentRouter r, T.PayOnceIntent memory i, bytes memory sig) internal {
        vm.prank(executor);
        r.payOnceWithSignature(i, P2_NONCE, deadline, sig);
    }

    function test_PayOnce_Settles_AndLeavesNothingBehind() public {
        T.PayOnceIntent memory i = _intent();
        bytes memory sig = _signPermit(i, address(routerA), P2_NONCE, deadline);
        _pay(routerA, i, sig);
        assertEq(_bal(usdc, merchantWallet), NET);
        assertEq(_bal(usdc, feeWallet), FEE);
        assertEq(_bal(usdc, customer), 1_000e6 - GROSS);
        assertEq(_bal(usdc, address(routerA)), 0, "I-ZEROBAL");
        (uint160 a,,) = p2.allowance(customer, address(usdc), address(routerA));
        assertEq(a, 0, "I-PO-NOSTANDING: no Permit2 allowance");
        assertEq(usdc.allowance(customer, address(routerA)), 0, "no token allowance to the router");
        assertTrue(routers.isSettled(i.paymentId));
        assertEq(manager.exposedCount(customer, address(routerA)), 0, "no mandate exists");
    }

    function test_PayOnce_ASecondSubmissionOfTheSamePayment_IsRefused() public {
        T.PayOnceIntent memory i = _intent();
        bytes memory sig = _signPermit(i, address(routerA), P2_NONCE, deadline);
        _pay(routerA, i, sig);
        vm.expectRevert(PaymentAlreadySettled.selector);
        _pay(routerA, i, sig);
    }

    function test_PayOnce_ThePaymentSettlesOnceAcrossRouterVersions() public {
        T.PayOnceIntent memory i = _intent();
        _pay(routerA, i, _signPermit(i, address(routerA), P2_NONCE, deadline));
        // a fresh signature for router B and the same order: the settle-once record is shared by every router
        vm.expectRevert(PaymentAlreadySettled.selector);
        vm.prank(executor);
        routerB.payOnceWithSignature(i, P2_NONCE + 1, deadline, _signPermit(i, address(routerB), P2_NONCE + 1, deadline));
    }

    function test_PayOnce_ASignatureForOneRouterIsUselessToAnother() public {
        T.PayOnceIntent memory i = _intent();
        bytes memory sig = _signPermit(i, address(routerA), P2_NONCE, deadline);
        vm.expectRevert(ERR_INVALID_SIGNER);
        _pay(routerB, i, sig);
    }

    function test_PayOnce_OnlyAnExecutorSubmits() public {
        T.PayOnceIntent memory i = _intent();
        bytes memory sig = _signPermit(i, address(routerA), P2_NONCE, deadline);
        vm.expectRevert(NotExecutor.selector);
        vm.prank(stranger);
        routerA.payOnceWithSignature(i, P2_NONCE, deadline, sig);
    }

    /// The base of the tamper tests: a fee well under the controller's rate, so that moving a unit into it stays legal.
    function _lowFee() internal view returns (T.PayOnceIntent memory i) {
        i = _intent();
        i.feeAmount = 100_000;
        i.merchantAmount = GROSS - 100_000;
    }

    function test_PayOnce_TheWitnessBindsEveryTerm() public {
        T.PayOnceIntent memory i = _lowFee();
        bytes memory sig = _signPermit(i, address(routerA), P2_NONCE, deadline);
        T.PayOnceIntent memory t;

        // the executor moves a unit from the merchant to the fee: the split is signed
        t = _lowFee();
        t.feeAmount += 1;
        t.merchantAmount -= 1;
        vm.expectRevert(ERR_INVALID_SIGNER);
        _pay(routerA, t, sig);

        // another order id, other terms shown to the customer, another quote hash
        t = _lowFee();
        t.paymentId = keccak256("order-2");
        vm.expectRevert(ERR_INVALID_SIGNER);
        _pay(routerA, t, sig);
        t = _lowFee();
        t.termsHash = keccak256("other terms");
        vm.expectRevert(ERR_INVALID_SIGNER);
        _pay(routerA, t, sig);
        t = _lowFee();
        t.quoteHash = keccak256("a quote");
        vm.expectRevert(ERR_INVALID_SIGNER);
        _pay(routerA, t, sig);

        // another payer: the signature recovers a different owner
        t = _lowFee();
        t.payer = stranger;
        vm.expectRevert(ERR_INVALID_SIGNER);
        _pay(routerA, t, sig);

        // another merchant id (the registry recipient and token acceptance are those of the same merchant here)
        t = _lowFee();
        t.merchantId = keccak256("merchant-2");
        vm.expectRevert(UnknownMerchant.selector);
        _pay(routerA, t, sig);

        // a different permit nonce
        vm.expectRevert(ERR_INVALID_SIGNER);
        vm.prank(executor);
        routerA.payOnceWithSignature(i, P2_NONCE + 1, deadline, sig);

        // the honest submission passes: every refusal above was caused by the one change it made
        _pay(routerA, i, sig);
        assertEq(_bal(usdc, merchantWallet), GROSS - 100_000);
        assertEq(_bal(usdc, feeWallet), 100_000);
    }

    function test_PayOnce_TheRecipientIsTheRegistryRecipientNow_NotWhatTheSignatureSays() public {
        // the customer signed a payment to a recipient that is not the registry's: the router refuses before Permit2 sees it
        T.PayOnceIntent memory i = _intent();
        i.recipient = stranger;
        bytes memory sig = _signPermit(i, address(routerA), P2_NONCE, deadline);
        vm.expectRevert(IntentInvalid.selector);
        _pay(routerA, i, sig);
        i = _intent();
        i.feeRecipient = stranger;
        sig = _signPermit(i, address(routerA), P2_NONCE, deadline);
        vm.expectRevert(IntentInvalid.selector);
        _pay(routerA, i, sig);
    }

    function test_PayOnce_FeeAndAmountsAreBounded() public {
        T.PayOnceIntent memory i = _intent();
        i.feeAmount = FEE + 1; // above the controller's 50 bps
        i.merchantAmount = NET - 1;
        bytes memory sig = _signPermit(i, address(routerA), P2_NONCE, deadline);
        vm.expectRevert(FeeAboveCeiling.selector);
        _pay(routerA, i, sig);
        i = _intent();
        i.merchantAmount = NET - 1; // gross != merchant + fee
        sig = _signPermit(i, address(routerA), P2_NONCE, deadline);
        vm.expectRevert(IntentInvalid.selector);
        _pay(routerA, i, sig);
    }

    function test_PayOnce_ValidityWindow() public {
        T.PayOnceIntent memory i = _intent();
        bytes memory sig = _signPermit(i, address(routerA), P2_NONCE, deadline);
        vm.warp(deadline + 1);
        vm.expectRevert(IntentExpired.selector);
        _pay(routerA, i, sig);
        // validUntil beyond the signature deadline is refused too
        vm.warp(START);
        i = _intent();
        i.validUntil = uint64(deadline + 1);
        sig = _signPermit(i, address(routerA), P2_NONCE, deadline);
        vm.expectRevert(IntentExpired.selector);
        _pay(routerA, i, sig);
        // the boundary: now == validUntil == deadline
        i = _intent();
        sig = _signPermit(i, address(routerA), P2_NONCE, deadline);
        vm.warp(deadline);
        _pay(routerA, i, sig);
    }

    function test_PayOnce_Permit2NonceIsSingleUse() public {
        T.PayOnceIntent memory i = _intent();
        _pay(routerA, i, _signPermit(i, address(routerA), P2_NONCE, deadline));
        T.PayOnceIntent memory j = _intent();
        j.paymentId = keccak256("order-2");
        bytes memory sig = _signPermit(j, address(routerA), P2_NONCE, deadline); // the same Permit2 nonce for another order
        vm.expectRevert(ERR_INVALID_NONCE);
        _pay(routerA, j, sig);
        // the settle-once record was not consumed by the failed attempt
        assertFalse(routers.isSettled(j.paymentId));
    }

    function test_PayOnce_MerchantAndTokenStatus() public {
        T.PayOnceIntent memory i = _intent();
        bytes memory sig = _signPermit(i, address(routerA), P2_NONCE, deadline);
        vm.prank(guardian);
        merchantReg.pauseMerchant(MERCHANT);
        vm.expectRevert(MerchantInactive.selector);
        _pay(routerA, i, sig);
        vm.prank(merchantAdmin);
        merchantReg.unpauseMerchant(MERCHANT);
        vm.prank(guardian);
        policy.block_(address(usdc));
        vm.expectRevert(TokenBlocked.selector);
        _pay(routerA, i, sig);
    }

    function test_PayOnce_ARouterThatIsNotInTheRegistryCannotMarkPayments() public {
        PaymentRouter unregistered = _newRouter();
        vm.prank(gov);
        execReg.add(executor);
        T.PayOnceIntent memory i = _intent();
        bytes memory sig = _signPermit(i, address(unregistered), P2_NONCE, deadline);
        vm.expectRevert(NotRouterOfRegistry.selector);
        vm.prank(executor);
        unregistered.payOnceWithSignature(i, P2_NONCE, deadline, sig);
        vm.prank(stranger);
        vm.expectRevert(NotRouterOfRegistry.selector);
        routers.markSettled(keccak256("x"));
    }

    // ------------------------------------------------------------------------------------------------------------ MINOUT
    function test_Minout_AFeeOnTransferTokenIsRefusedByPayOnce() public {
        FeeOnTransferToken fot = new FeeOnTransferToken();
        vm.startPrank(gov);
        policy.list(address(fot), 1, 6);
        vm.stopPrank();
        vm.prank(merchantAdmin);
        merchantReg.setAccepted(MERCHANT, address(fot), true);
        fot.mint(customer, 1_000e6);
        vm.prank(customer);
        fot.approve(CANONICAL, type(uint256).max);
        T.PayOnceIntent memory i = _intent();
        i.token = address(fot);
        bytes memory sig = _signPermit(i, address(routerA), P2_NONCE, deadline);
        vm.expectRevert(BelowMinOut.selector);
        _pay(routerA, i, sig);
        assertEq(fot.balanceOf(merchantWallet), 0, "the whole payment reverted");
    }

    function test_Minout_AFeeOnTransferTokenIsRefusedByRecurringCharges() public {
        FeeOnTransferToken fot = new FeeOnTransferToken();
        vm.startPrank(gov);
        policy.list(address(fot), 1, 6);
        policy.setPriceSourceSet(address(fot), USD, SOURCE_SET);
        policy.publishBounds(address(fot), USD, 98e18, 102e18);
        vm.stopPrank();
        vm.prank(merchantAdmin);
        merchantReg.setAccepted(MERCHANT, address(fot), true);
        fot.mint(customer, 1_000e6);
        vm.prank(customer);
        fot.approve(CANONICAL, type(uint256).max);
        _grant(customer, MockERC20(address(fot)), address(routerA), 500e6);
        T.MandateTerms memory t = _terms(address(fot));
        (bytes32 lid, bytes32 mid) = _activate(customer, 1, address(routerA), t, _pin());
        PaymentRouter.QuoteBundle memory q = _quote(routerA, lid, 0, customer, address(fot), 10e6, PRICE);
        vm.expectRevert(BelowMinOut.selector);
        _charge(routerA, mid, t, _pin(), 0, address(fot), 10e6, 0, q);
        assertEq(ledger.cycleRecord(lid, 0), bytes32(0), "the effects were reverted with the pull");
    }

    function test_PayOnce_ReentrancyIsLocked() public {
        // a token that calls back into the router during transferFrom: the nested call is refused by the lock BEFORE any other check,
        // the token records the error and lets the outer payment finish
        ReenteringToken bad = new ReenteringToken(routerA);
        vm.prank(gov);
        policy.list(address(bad), 1, 6);
        vm.prank(merchantAdmin);
        merchantReg.setAccepted(MERCHANT, address(bad), true);
        bad.mint(customer, 1_000e6);
        vm.prank(customer);
        bad.approve(CANONICAL, type(uint256).max);
        T.PayOnceIntent memory i = _intent();
        i.token = address(bad);
        bytes memory sig = _signPermit(i, address(routerA), P2_NONCE, deadline);
        _pay(routerA, i, sig);
        assertTrue(bad.tried());
        assertEq(bad.lastError(), Reentrancy.selector);
    }
}

/// A token whose transferFrom tries to enter the router again and records why that failed.
contract ReenteringToken is MockERC20 {
    PaymentRouter public immutable target;
    bool public tried;
    bytes4 public lastError;

    constructor(PaymentRouter t) {
        target = t;
    }

    function transferFrom(address from, address to, uint256 amount) external override returns (bool) {
        tried = true;
        T.PayOnceIntent memory i;
        try target.payOnceWithSignature(i, 0, 0, "") {}
        catch (bytes memory reason) {
            lastError = bytes4(reason);
        }
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        return true;
    }
}
