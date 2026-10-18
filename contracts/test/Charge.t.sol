// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Base, IP2} from "./helpers/Base.sol";
import {FastPayTypes as T} from "../src/generated/FastPayTypes.sol";
import {PaymentRouter} from "../src/PaymentRouter.sol";
import {IMandateManager} from "../src/interfaces/IMandateManager.sol";
import {UsageLedger} from "../src/UsageLedger.sol";
import "../src/Errors.sol";

/// Recurring charges end to end on the REAL contracts and the rebuilt Permit2: the guards G1 to G10, the dual caps and their windows, the
/// fee, settle-once, the router's merchant and token checks, and the atomicity of effects and pull (finding F-16).
contract ChargeTest is Base {
    bytes32 lid;
    bytes32 mid;

    function setUp() public override {
        super.setUp();
        _fund(customer, usdc, 10_000e6);
        _grant(customer, usdc, address(routerA), 5_000e6);
        (lid, mid) = _activate(customer, 1, address(routerA), _t(), _pin());
    }

    function _t() internal view returns (T.MandateTerms memory) {
        return _terms(address(usdc));
    }

    function _q(uint64 cycle, uint256 amount) internal view returns (PaymentRouter.QuoteBundle memory) {
        return _quote(routerA, lid, cycle, customer, address(usdc), amount, PRICE);
    }

    function _ok(uint64 cycle, uint256 amount, uint256 fee) internal {
        PaymentRouter.QuoteBundle memory q = _q(cycle, amount);
        _charge(routerA, mid, _t(), _pin(), cycle, address(usdc), amount, fee, q);
    }

    function _use() internal view returns (UsageLedger.Use memory) {
        return ledger.tokenUsage(lid, address(usdc));
    }

    // ------------------------------------------------------------------------------------------------------------ the happy path
    function test_Charge_PaysMerchantAndFee_ZeroBalanceRouter() public {
        _ok(0, 100e6, 500_000);
        assertEq(_bal(usdc, merchantWallet), 99_500_000);
        assertEq(_bal(usdc, feeWallet), 500_000);
        assertEq(_bal(usdc, customer), 9_900e6);
        assertEq(_bal(usdc, address(routerA)), 0, "I-ZEROBAL");
        UsageLedger.Use memory u = _use();
        assertEq(u.total, 100e6);
        assertEq(u.day, 100e6);
        assertEq(ledger.fiatUsage(lid).total, 10_000, "fiat cents");
        assertTrue(ledger.cycleRecord(lid, 0) != bytes32(0));
    }

    function test_Charge_Event_CarriesTheFiatValueAndQuoteDigest() public {
        PaymentRouter.QuoteBundle memory q = _q(0, 100e6);
        bytes32 digest = T.digest(routerA.quoteDomainSeparator(), T.hashStruct(q.quote));
        vm.expectEmit(true, true, true, true, address(routerA));
        emit PaymentRouter.PaymentSettled(routerA.paymentIdOf(lid, 0), mid, customer, address(usdc), 100e6, 0, 10_000, digest);
        _charge(routerA, mid, _t(), _pin(), 0, address(usdc), 100e6, 0, q);
        assertEq(ledger.cycleRecord(lid, 0), digest, "the cycle record stores the quote digest (Q20)");
    }

    function test_Charge_FiatValueIsRoundedUp() public {
        // 33.333333 tokens at 100.5 cents each = 3350.0 .. rounded up: amount * price / (1e6 * 1e18)
        uint256 price = 100_500000000000000000; // 100.5e18, inside the band
        uint256 amount = 33_333_333;
        PaymentRouter.QuoteBundle memory q = _quote(routerA, lid, 0, customer, address(usdc), amount, price);
        _charge(routerA, mid, _t(), _pin(), 0, address(usdc), amount, 0, q);
        // 33_333_333 * 100.5 / 1e6 = 3349.999966 -> 3350
        assertEq(ledger.fiatUsage(lid).total, 3350);
    }

    function test_Charge_PaymentIdHasNoRouterInput() public view {
        bytes32 a = routerA.paymentIdOf(lid, 3);
        bytes32 b = routerB.paymentIdOf(lid, 3);
        assertEq(a, b, "ADR-009: the payment id is the same under every router");
    }

    // ------------------------------------------------------------------------------------------------------------ authorization of the call
    function test_Charge_OnlyAnExecutor() public {
        PaymentRouter.QuoteBundle memory q = _q(0, 100e6);
        vm.expectRevert(NotExecutor.selector);
        vm.prank(stranger);
        routerA.charge(PaymentRouter.ChargeRequest(mid, 0, address(usdc), 100e6, 0), _t(), _pin(), q);
    }

    function test_Charge_AnotherRouterCannotChargeTheMandate() public {
        PaymentRouter.QuoteBundle memory q = _quote(routerB, lid, 0, customer, address(usdc), 100e6, PRICE);
        vm.expectRevert(WrongRouter.selector);
        _charge(routerB, mid, _t(), _pin(), 0, address(usdc), 100e6, 0, q);
    }

    function test_Consume_OnlyTheBoundRouterContract() public {
        vm.expectRevert(WrongRouter.selector);
        vm.prank(executor);
        manager.consume(mid, _t(), _pin(), _input(100e6));
    }

    function _input(uint256 amount) internal pure returns (IMandateManager.ChargeInput memory c) {
        c.token = address(0);
        c.amount = amount;
    }

    // ------------------------------------------------------------------------------------------------------------ cycles and cadence
    function test_Charge_SameCycleTwice_PaymentAlreadySettled() public {
        _ok(0, 50e6, 0);
        vm.warp(START + 2 hours);
        PaymentRouter.QuoteBundle memory q = _q(0, 50e6);
        vm.expectRevert(PaymentAlreadySettled.selector);
        _charge(routerA, mid, _t(), _pin(), 0, address(usdc), 50e6, 0, q);
    }

    function test_Charge_FutureCycle_CycleNotYetDue() public {
        PaymentRouter.QuoteBundle memory q = _q(1, 50e6);
        vm.expectRevert(CycleNotYetDue.selector);
        _charge(routerA, mid, _t(), _pin(), 1, address(usdc), 50e6, 0, q);
    }

    function test_Charge_MinInterval_ChargeTooSoon() public {
        vm.warp(START + 30 days + 10);
        _ok(0, 50e6, 0);
        vm.warp(block.timestamp + 30 minutes);
        PaymentRouter.QuoteBundle memory q = _q(1, 50e6);
        vm.expectRevert(ChargeTooSoon.selector);
        _charge(routerA, mid, _t(), _pin(), 1, address(usdc), 50e6, 0, q);
        vm.warp(block.timestamp + 31 minutes);
        q = _q(1, 50e6);
        _charge(routerA, mid, _t(), _pin(), 1, address(usdc), 50e6, 0, q); // after the interval it passes
    }

    function test_Charge_ChargesPerPeriod() public {
        T.MandateTerms memory t = _t();
        t.maxChargesPerPeriod = 1;
        t.minIntervalSeconds = 0;
        bytes32 l2 = manager.lineageIdOf(customer, MERCHANT, SUBSCRIPTION, 2);
        bytes32 m2 = manager.mandateIdOf(l2, 0);
        _activate(customer, 2, address(routerA), t, _pin());
        vm.warp(START + 30 days + 10);
        PaymentRouter.QuoteBundle memory q = _quote(routerA, l2, 0, customer, address(usdc), 10e6, PRICE);
        _charge(routerA, m2, t, _pin(), 0, address(usdc), 10e6, 0, q);
        q = _quote(routerA, l2, 1, customer, address(usdc), 10e6, PRICE);
        vm.expectRevert(ChargesPerPeriodExceeded.selector);
        _charge(routerA, m2, t, _pin(), 1, address(usdc), 10e6, 0, q);
    }

    function test_Charge_LateRetryOfAnEarlierCycleIsAllowed() public {
        vm.warp(START + 65 days); // cycle 2 is current; cycle 0 never ran
        _ok(0, 50e6, 0);
        assertTrue(ledger.cycleRecord(lid, 0) != bytes32(0));
    }

    // ------------------------------------------------------------------------------------------------------------ token caps
    function _lineageWithCaps(uint256 perPayment, uint256 day, uint256 week, uint256 thirty, uint256 period, uint256 total, uint256 nonce)
        internal
        returns (T.MandateTerms memory t, bytes32 l, bytes32 m)
    {
        t = _t();
        t.tokens[0].perPaymentMax = perPayment;
        t.tokens[0].dayMax = day;
        t.tokens[0].weekMax = week;
        t.tokens[0].thirtyDayMax = thirty;
        t.tokens[0].periodMax = period;
        t.tokens[0].totalMax = total;
        t.fiat = T.FiatTerms(USD, 0, 0, 0, 0, 0, 0, 120, 1); // token caps only
        t.minIntervalSeconds = 0;
        t.maxChargesPerPeriod = 0;
        l = manager.lineageIdOf(customer, MERCHANT, SUBSCRIPTION, nonce);
        m = manager.mandateIdOf(l, 0);
        _activate(customer, nonce, address(routerA), t, _pin());
    }

    function test_Caps_PerPayment() public {
        (T.MandateTerms memory t,, bytes32 m) = _lineageWithCaps(60e6, 0, 0, 0, 0, 0, 10);
        vm.expectRevert(TokenPerPaymentCapExceeded.selector);
        _charge(routerA, m, t, _pin(), 0, address(usdc), 60e6 + 1, 0, _noQuote());
        _charge(routerA, m, t, _pin(), 0, address(usdc), 60e6, 0, _noQuote());
    }

    function test_Caps_Day_ResetsLazilyAtTheNextDay() public {
        (T.MandateTerms memory t,, bytes32 m) = _lineageWithCaps(100e6, 150e6, 0, 0, 0, 0, 11);
        vm.warp(START + 30 days + 10); // cycles 0 and 1 are both due, in the same day
        _charge(routerA, m, t, _pin(), 0, address(usdc), 100e6, 0, _noQuote());
        vm.expectRevert(TokenWindowCapExceeded.selector);
        _charge(routerA, m, t, _pin(), 1, address(usdc), 100e6, 0, _noQuote());
        vm.warp(block.timestamp + 1 days); // a new day: the counter is reset on the next use
        _charge(routerA, m, t, _pin(), 1, address(usdc), 100e6, 0, _noQuote());
    }

    function test_Caps_Total() public {
        (T.MandateTerms memory t,, bytes32 m) = _lineageWithCaps(100e6, 0, 0, 0, 0, 150e6, 12);
        vm.warp(START + 30 days + 10);
        _charge(routerA, m, t, _pin(), 0, address(usdc), 100e6, 0, _noQuote());
        vm.expectRevert(TokenTotalCapExceeded.selector);
        _charge(routerA, m, t, _pin(), 1, address(usdc), 100e6, 0, _noQuote());
        _charge(routerA, m, t, _pin(), 1, address(usdc), 50e6, 0, _noQuote()); // exactly the cap
        vm.warp(START + 60 days + 10); // cycle 2 is due; the lineage total is spent
        vm.expectRevert(TokenTotalCapExceeded.selector);
        _charge(routerA, m, t, _pin(), 2, address(usdc), 1, 0, _noQuote());
    }

    function test_Caps_Week_Thirty_Period_EachOnItsOwn() public {
        // week: cycles 0 and 1 inside one week
        (T.MandateTerms memory t,, bytes32 m) = _lineageWithCaps(100e6, 0, 150e6, 0, 0, 0, 13);
        vm.warp(START + 30 days + 10);
        _charge(routerA, m, t, _pin(), 0, address(usdc), 100e6, 0, _noQuote());
        vm.expectRevert(TokenWindowCapExceeded.selector);
        _charge(routerA, m, t, _pin(), 1, address(usdc), 100e6, 0, _noQuote());
        // thirty days
        (t,, m) = _lineageWithCaps(100e6, 0, 0, 150e6, 0, 0, 14);
        _charge(routerA, m, t, _pin(), 0, address(usdc), 100e6, 0, _noQuote());
        vm.expectRevert(TokenWindowCapExceeded.selector);
        _charge(routerA, m, t, _pin(), 1, address(usdc), 100e6, 0, _noQuote());
        // billing period
        (t,, m) = _lineageWithCaps(100e6, 0, 0, 0, 150e6, 0, 15);
        _charge(routerA, m, t, _pin(), 0, address(usdc), 100e6, 0, _noQuote());
        vm.expectRevert(TokenWindowCapExceeded.selector);
        _charge(routerA, m, t, _pin(), 1, address(usdc), 100e6, 0, _noQuote());
    }

    function test_Caps_AWindowResetsWhenItsIndexMoves() public {
        (T.MandateTerms memory t,, bytes32 m) = _lineageWithCaps(100e6, 0, 0, 0, 150e6, 0, 16);
        _charge(routerA, m, t, _pin(), 0, address(usdc), 100e6, 0, _noQuote());
        vm.warp(START + 30 days + 10); // the next billing period: the period counter starts again
        _charge(routerA, m, t, _pin(), 1, address(usdc), 100e6, 0, _noQuote());
        assertEq(ledger.tokenUsage(manager.lineageIdOf(customer, MERCHANT, SUBSCRIPTION, 16), address(usdc)).total, 200e6);
    }

    function _shortPeriod(uint256 nonce_, uint64 period, uint256 thirty, uint256 periodMax) internal returns (T.MandateTerms memory t, bytes32 l, bytes32 m) {
        t = _t();
        t.periodSeconds = period;
        t.tokens[0].perPaymentMax = 100e6;
        t.tokens[0].dayMax = 0;
        t.tokens[0].weekMax = 0;
        t.tokens[0].thirtyDayMax = thirty;
        t.tokens[0].periodMax = periodMax;
        t.tokens[0].totalMax = 0;
        t.fiat = T.FiatTerms(USD, 0, 0, 0, 0, 0, 0, 120, 1);
        t.minIntervalSeconds = 0;
        t.maxChargesPerPeriod = 0;
        l = manager.lineageIdOf(customer, MERCHANT, SUBSCRIPTION, nonce_);
        m = manager.mandateIdOf(l, 0);
        _activate(customer, nonce_, address(routerA), t, _pin());
    }

    function test_Caps_TheThirtyDayWindowSpansManyDays() public {
        // daily cycles, so that two charges fall on different days of the same thirty-day window
        (T.MandateTerms memory t,, bytes32 m) = _shortPeriod(20, 1 days, 150e6, 0);
        vm.warp(START + 1 hours);
        _charge(routerA, m, t, _pin(), 0, address(usdc), 100e6, 0, _noQuote());
        vm.warp(START + 1 days + 1 hours);
        vm.expectRevert(TokenWindowCapExceeded.selector);
        _charge(routerA, m, t, _pin(), 1, address(usdc), 100e6, 0, _noQuote());
    }

    function test_Caps_TheBillingPeriodWindowResetsPerPeriod_NotPerWeek() public {
        // three-day periods: the second charge is in the next period (the counter is reset) and in the same week
        (T.MandateTerms memory t, bytes32 l, bytes32 m) = _shortPeriod(21, 3 days, 0, 150e6);
        vm.warp(START + 1 hours);
        _charge(routerA, m, t, _pin(), 0, address(usdc), 100e6, 0, _noQuote());
        vm.warp(START + 3 days + 1 hours);
        _charge(routerA, m, t, _pin(), 1, address(usdc), 100e6, 0, _noQuote());
        assertEq(ledger.tokenUsage(l, address(usdc)).period, 100e6, "the period counter was reset by the new period");
        assertEq(ledger.tokenUsage(l, address(usdc)).total, 200e6);
    }

    function test_Ledger_OnlyTheManagerWritesTheCounters() public {
        vm.prank(stranger);
        vm.expectRevert(NotManager.selector);
        ledger.charge(mid, lid, _t(), _input(1e6));
    }

    // ------------------------------------------------------------------------------------------------------------ fee
    function test_Fee_AboveTheMandateCap_FeeTooHigh() public {
        T.MandateTerms memory t = _t();
        t.maxFeeBps = 20; // the controller allows 50; the customer allows 20
        bytes32 l2 = manager.lineageIdOf(customer, MERCHANT, SUBSCRIPTION, 2);
        bytes32 m2 = manager.mandateIdOf(l2, 0);
        _activate(customer, 2, address(routerA), t, _pin());
        PaymentRouter.QuoteBundle memory q = _quote(routerA, l2, 0, customer, address(usdc), 100e6, PRICE);
        vm.expectRevert(FeeTooHigh.selector);
        _charge(routerA, m2, t, _pin(), 0, address(usdc), 100e6, 200_001, q);
        q = _quote(routerA, l2, 0, customer, address(usdc), 100e6, PRICE);
        _charge(routerA, m2, t, _pin(), 0, address(usdc), 100e6, 200_000, q);
    }

    function test_Fee_AboveTheControllersRate_FeeAboveCeiling() public {
        PaymentRouter.QuoteBundle memory q = _q(0, 100e6);
        vm.expectRevert(FeeAboveCeiling.selector);
        _charge(routerA, mid, _t(), _pin(), 0, address(usdc), 100e6, 500_001, q); // 50 bps of 100e6 is 500_000
    }

    function test_Fee_GovernanceCannotRaiseItAboveTheImmutableCeiling() public {
        vm.prank(gov);
        vm.expectRevert(FeeAboveCeiling.selector);
        feeCtl.setFee(FEE_CEILING + 1, feeWallet);
    }

    // ------------------------------------------------------------------------------------------------------------ guards on the mandate
    function test_Guard_Paused_ByEachBit() public {
        PaymentRouter.QuoteBundle memory q = _q(0, 10e6);
        vm.prank(customer);
        manager.pause(customer, mid);
        vm.expectRevert(MandateNotConsumable.selector);
        _charge(routerA, mid, _t(), _pin(), 0, address(usdc), 10e6, 0, q);
        vm.prank(customer);
        manager.resume(customer, mid);
        vm.prank(riskService);
        manager.setPauseBit(mid, 2, true);
        vm.expectRevert(MandateNotConsumable.selector);
        _charge(routerA, mid, _t(), _pin(), 0, address(usdc), 10e6, 0, q);
        vm.prank(riskService);
        manager.setPauseBit(mid, 2, false);
        vm.prank(riskService);
        manager.setPauseBit(mid, 4, true);
        vm.expectRevert(MandateNotConsumable.selector);
        _charge(routerA, mid, _t(), _pin(), 0, address(usdc), 10e6, 0, q);
        vm.prank(riskService);
        manager.setPauseBit(mid, 4, false);
        _charge(routerA, mid, _t(), _pin(), 0, address(usdc), 10e6, 0, q);
    }

    function test_Guard_Revoked() public {
        PaymentRouter.QuoteBundle memory q = _q(0, 10e6);
        vm.prank(customer);
        manager.revoke(customer, mid);
        vm.expectRevert(MandateNotConsumable.selector);
        _charge(routerA, mid, _t(), _pin(), 0, address(usdc), 10e6, 0, q);
    }

    function test_Guard_Expired_AndNotYetStarted() public {
        T.MandateTerms memory t = _t();
        t.anchorStartsAt = uint64(START + 1 days);
        bytes32 l2 = manager.lineageIdOf(customer, MERCHANT, SUBSCRIPTION, 2);
        bytes32 m2 = manager.mandateIdOf(l2, 0);
        _activate(customer, 2, address(routerA), t, _pin());
        PaymentRouter.QuoteBundle memory q = _quote(routerA, l2, 0, customer, address(usdc), 10e6, PRICE);
        vm.expectRevert(MandateNotConsumable.selector); // I-TIME: before startsAt
        _charge(routerA, m2, t, _pin(), 0, address(usdc), 10e6, 0, q);
        vm.warp(START + 366 days);
        q = _quote(routerA, lid, 0, customer, address(usdc), 10e6, PRICE);
        vm.expectRevert(MandateNotConsumable.selector); // after expiresAt
        _charge(routerA, mid, _t(), _pin(), 0, address(usdc), 10e6, 0, q);
    }

    function test_Guard_ExpiryBoundary_TheExpirySecondIsOver() public {
        vm.warp(START + 365 days - 1);
        PaymentRouter.QuoteBundle memory q = _q(0, 10e6);
        _charge(routerA, mid, _t(), _pin(), 0, address(usdc), 10e6, 0, q); // one second before the expiry: valid
        vm.warp(START + 365 days);
        q = _q(1, 10e6);
        vm.expectRevert(MandateNotConsumable.selector); // now == expiresAt: expired (I-TIME)
        _charge(routerA, mid, _t(), _pin(), 1, address(usdc), 10e6, 0, q);
    }

    function test_Guard_StartBoundary_TheStartSecondIsValid() public {
        T.MandateTerms memory t = _t();
        t.anchorStartsAt = uint64(START + 1 days);
        bytes32 l2 = manager.lineageIdOf(customer, MERCHANT, SUBSCRIPTION, 2);
        bytes32 m2 = manager.mandateIdOf(l2, 0);
        _activate(customer, 2, address(routerA), t, _pin());
        vm.warp(START + 1 days);
        PaymentRouter.QuoteBundle memory q = _quote(routerA, l2, 0, customer, address(usdc), 10e6, PRICE);
        _charge(routerA, m2, t, _pin(), 0, address(usdc), 10e6, 0, q); // now == startsAt: valid
    }

    function test_Guard_TermsAreBoundToTheMandateByHash() public {
        T.MandateTerms memory t = _t();
        t.tokens[0].perPaymentMax = 1_000_000e6; // a wider cap than the customer signed
        PaymentRouter.QuoteBundle memory q = _q(0, 10e6);
        vm.expectRevert(TermsHashMismatch.selector);
        _charge(routerA, mid, t, _pin(), 0, address(usdc), 10e6, 0, q);
    }

    function test_Guard_PinIsBoundByHash_AndTheAccountMustStillMatch() public {
        T.AccountPin memory p = _pin();
        p.signatureMode = 0;
        PaymentRouter.QuoteBundle memory q = _q(0, 10e6);
        vm.expectRevert(PinHashMismatch.selector);
        _charge(routerA, mid, _t(), p, 0, address(usdc), 10e6, 0, q);
        // the account gains code (a 7702-style change, or a contract at the address): PIN_OK fails with the field
        vm.etch(customer, hex"6001");
        vm.expectRevert(abi.encodeWithSelector(AccountCodeChanged.selector, customer, uint8(1)));
        _charge(routerA, mid, _t(), _pin(), 0, address(usdc), 10e6, 0, q);
    }

    function test_Guard_TokenNotInTheMandate() public {
        _fund(customer, dai, 1_000e6);
        _grant(customer, dai, address(routerA), 1_000e6);
        PaymentRouter.QuoteBundle memory q = _quote(routerA, lid, 0, customer, address(dai), 10e6, PRICE);
        vm.expectRevert(TokenNotInMandate.selector);
        _charge(routerA, mid, _t(), _pin(), 0, address(dai), 10e6, 0, q);
    }

    // ------------------------------------------------------------------------------------------------------------ the router's own checks
    function test_Router_BlockedToken() public {
        vm.prank(guardian);
        policy.block_(address(usdc));
        PaymentRouter.QuoteBundle memory q = _q(0, 10e6);
        vm.expectRevert(TokenBlocked.selector);
        _charge(routerA, mid, _t(), _pin(), 0, address(usdc), 10e6, 0, q);
    }

    function test_Router_MerchantPausedOrTokenNotAccepted() public {
        PaymentRouter.QuoteBundle memory q = _q(0, 10e6);
        vm.prank(guardian);
        merchantReg.pauseMerchant(MERCHANT);
        vm.expectRevert(MerchantInactive.selector);
        _charge(routerA, mid, _t(), _pin(), 0, address(usdc), 10e6, 0, q);
        vm.prank(merchantAdmin);
        merchantReg.unpauseMerchant(MERCHANT);
        vm.prank(merchantAdmin);
        merchantReg.setAccepted(MERCHANT, address(usdc), false);
        vm.expectRevert(MerchantTokenNotAccepted.selector);
        _charge(routerA, mid, _t(), _pin(), 0, address(usdc), 10e6, 0, q);
    }

    function test_Router_RecipientChangeIsDelayed() public {
        address newWallet = makeAddr("newWallet");
        vm.prank(merchantAdmin);
        merchantReg.proposeRecipient(MERCHANT, newWallet);
        _ok(0, 10e6, 0);
        assertEq(_bal(usdc, merchantWallet), 10e6, "the old recipient is paid until the delay passes");
        vm.prank(merchantAdmin);
        vm.expectRevert(RecipientChangeNotReady.selector);
        merchantReg.acceptRecipient(MERCHANT);
        vm.warp(block.timestamp + 2 days);
        vm.prank(merchantAdmin);
        merchantReg.acceptRecipient(MERCHANT);
        vm.warp(block.timestamp + 2 hours);
        PaymentRouter.QuoteBundle memory q = _q(1, 10e6);
        vm.warp(START + 31 days);
        q = _q(1, 10e6);
        _charge(routerA, mid, _t(), _pin(), 1, address(usdc), 10e6, 0, q);
        assertEq(_bal(usdc, newWallet), 10e6, "I-RECIPIENT: the registry recipient valid at charge time");
    }

    function test_Router_ExecutorRemovedByTheGuardian() public {
        PaymentRouter.QuoteBundle memory q = _q(0, 10e6);
        vm.prank(guardian);
        execReg.remove(executor);
        vm.expectRevert(NotExecutor.selector);
        _charge(routerA, mid, _t(), _pin(), 0, address(usdc), 10e6, 0, q);
    }

    function test_Router_RetiredOrDisabledRouterCannotCharge() public {
        PaymentRouter.QuoteBundle memory q = _q(0, 10e6);
        vm.prank(guardian);
        routers.emergencyDisable(address(routerA));
        vm.expectRevert(RouterNotChargeable.selector);
        _charge(routerA, mid, _t(), _pin(), 0, address(usdc), 10e6, 0, q);
    }

    // ------------------------------------------------------------------------------------------------------------ atomicity (F-16) and Permit2
    function test_Atomic_APullThatFailsRevertsTheCounters() public {
        _grant(customer, usdc, address(routerA), 5e6); // less than the charge
        PaymentRouter.QuoteBundle memory q = _q(0, 100e6);
        vm.expectRevert(abi.encodeWithSelector(bytes4(keccak256("InsufficientAllowance(uint256)")), uint256(5e6)));
        _charge(routerA, mid, _t(), _pin(), 0, address(usdc), 100e6, 0, q);
        assertEq(_use().total, 0, "no usage was recorded");
        assertEq(ledger.fiatUsage(lid).total, 0);
        assertEq(ledger.cycleRecord(lid, 0), bytes32(0), "the cycle is not settled");
        assertEq(_bal(usdc, merchantWallet), 0);
        _grant(customer, usdc, address(routerA), 5_000e6);
        q = _q(0, 100e6);
        _charge(routerA, mid, _t(), _pin(), 0, address(usdc), 100e6, 0, q); // the same cycle can be paid now
        assertEq(_use().total, 100e6);
    }

    function test_Atomic_ABalanceShortfallRevertsEverything() public {
        vm.prank(customer);
        usdc.transfer(stranger, 9_950e6); // the customer holds 50e6
        PaymentRouter.QuoteBundle memory q = _q(0, 100e6);
        vm.expectRevert();
        _charge(routerA, mid, _t(), _pin(), 0, address(usdc), 100e6, 0, q);
        assertEq(_use().total, 0);
    }

    function test_Permit2_AllowanceIsDecrementedByTheRouterOnly() public {
        _ok(0, 100e6, 500_000);
        (uint160 amount,,) = p2.allowance(customer, address(usdc), address(routerA));
        assertEq(amount, 5_000e6 - 100e6);
    }
}
