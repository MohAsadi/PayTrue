// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.24;

import {Base} from "./helpers/Base.sol";
import {FastPayTypes as T} from "../src/generated/FastPayTypes.sol";
import {PaymentRouter} from "../src/PaymentRouter.sol";
import "../src/Errors.sol";

/// The quote verifier on the real router: every check Q1 to Q20 of document 11 section 4.2 refuses the quote that breaks exactly that check
/// and accepts the quote that sits on its boundary; the versioned bounds registry of ADR-020 (a mandate pins a version, the verifier
/// intersects it with the current band); and the non-interference of a quote with the caps.
contract QuoteTest is Base {
    bytes32 lid;
    bytes32 mid;
    uint256 constant AMOUNT = 100e6;

    function setUp() public override {
        super.setUp();
        _fund(customer, usdc, 100_000e6);
        _grant(customer, usdc, address(routerA), type(uint160).max - 1);
        (lid, mid) = _activate(customer, 1, address(routerA), _terms(address(usdc)), _pin());
    }

    function _base() internal view returns (T.PriceQuote memory) {
        return _baseQuote(routerA, lid, 0, customer, address(usdc), AMOUNT, PRICE);
    }

    function _go(PaymentRouter.QuoteBundle memory q) internal {
        _charge(routerA, mid, _terms(address(usdc)), _pin(), 0, address(usdc), AMOUNT, 0, q);
    }

    function _expect(T.PriceQuote memory q, bytes4 err) internal {
        PaymentRouter.QuoteBundle memory b = _bundle(routerA, q);
        vm.expectRevert(err);
        _go(b);
    }

    // ------------------------------------------------------------------------------------------------------------ Q1, Q2, Q3
    function test_Q0_NoQuote_FiatQuoteRequired() public {
        vm.expectRevert(FiatQuoteRequired.selector);
        _go(_noQuote());
    }

    function test_Q1_AKeyOutsideTheSet_Unauthorized() public {
        (, uint256 other) = makeAddrAndKey("other-signer");
        T.PriceQuote memory q = _base();
        PaymentRouter.QuoteBundle memory b;
        b.quote = q;
        b.signature = _sign(other, T.digest(routerA.quoteDomainSeparator(), T.hashStruct(q)));
        vm.expectRevert(QuoteSignerUnauthorized.selector);
        _go(b);
    }

    function test_Q1_ARemovedKeyIsRefusedWithNoGrace_AndStaysRefused() public {
        PaymentRouter.QuoteBundle memory b = _bundle(routerA, _base());
        vm.prank(guardian);
        signerSets.removeQuoteSigner(quoteSigner);
        vm.expectRevert(QuoteSignerRemoved.selector);
        _go(b);
        // a replacement set does not bring the key back: the tombstone is permanent
        address[] memory members = new address[](1);
        members[0] = quoteSigner;
        vm.prank(gov);
        vm.expectRevert(abi.encodeWithSelector(QuoteSignerTombstoned.selector, quoteSigner));
        signerSets.proposeSignerSet(2, members);
    }

    function test_Q2_MalformedSignatures() public {
        T.PriceQuote memory q = _base();
        bytes32 d = T.digest(routerA.quoteDomainSeparator(), T.hashStruct(q));
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(quoteKey, d);
        PaymentRouter.QuoteBundle memory b;
        b.quote = q;
        // wrong length
        b.signature = abi.encodePacked(r, s);
        vm.expectRevert(QuoteSignatureInvalid.selector);
        _go(b);
        // v outside {27, 28}
        b.signature = abi.encodePacked(r, s, uint8(v - 27));
        vm.expectRevert(QuoteSignatureInvalid.selector);
        _go(b);
        // the malleable twin: high s and the other v
        bytes32 hi = bytes32(0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141 - uint256(s));
        b.signature = abi.encodePacked(r, hi, v == 27 ? uint8(28) : uint8(27));
        vm.expectRevert(QuoteSignatureInvalid.selector);
        _go(b);
        // the honest signature passes
        b.signature = abi.encodePacked(r, s, v);
        _go(b);
    }

    function test_Q3_AQuoteForAnotherRouterDoesNotVerify() public {
        T.PriceQuote memory q = _base();
        PaymentRouter.QuoteBundle memory b;
        b.quote = q;
        b.signature = _sign(quoteKey, T.digest(routerB.quoteDomainSeparator(), T.hashStruct(q))); // the domain of router B
        // Q3 is not observable on its own: the digest is built from this router, so the recovered address is a stranger's (Q1)
        vm.expectRevert(QuoteSignerUnauthorized.selector);
        _go(b);
    }

    // ------------------------------------------------------------------------------------------------------------ Q4 to Q8: binding
    function test_Q4_to_Q8_EveryBoundFieldMustMatch() public {
        T.PriceQuote memory q = _base();
        q.paymentId = keccak256("another payment");
        _expect(q, QuoteBindingMismatch.selector);
        q = _base();
        q.payer = stranger;
        _expect(q, QuoteBindingMismatch.selector);
        q = _base();
        q.token = address(dai);
        _expect(q, QuoteBindingMismatch.selector);
        q = _base();
        q.amountIn = AMOUNT - 1;
        _expect(q, QuoteBindingMismatch.selector);
        q = _base();
        q.currency = 978;
        _expect(q, QuoteBindingMismatch.selector);
    }

    // ------------------------------------------------------------------------------------------------------------ Q9 to Q12: times
    function test_Q9_TimesMustBeOrdered() public {
        T.PriceQuote memory q = _base();
        q.issuedAt = q.validAfter + 1;
        _expect(q, QuoteTimesInvalid.selector);
        q = _base();
        q.validAfter = q.validUntil + 1;
        _expect(q, QuoteTimesInvalid.selector);
    }

    function test_Q10_NotYetValid_AndTheBoundary() public {
        T.PriceQuote memory q = _base();
        q.validAfter = uint64(block.timestamp + 1);
        _expect(q, QuoteNotYetValid.selector);
        q = _base();
        q.validAfter = uint64(block.timestamp); // validAfter == now is valid
        _go(_bundle(routerA, q));
    }

    function test_Q11_Expired_AndTheBoundary() public {
        vm.warp(START + 1000); // the quote is issued after the signer set became active (Q13)
        T.PriceQuote memory q = _base();
        q.issuedAt = uint64(block.timestamp - 100);
        q.validAfter = uint64(block.timestamp - 100);
        q.validUntil = uint64(block.timestamp - 1);
        _expect(q, QuoteExpired.selector);
        q.validUntil = uint64(block.timestamp); // validUntil == now is valid
        _go(_bundle(routerA, q));
    }

    function test_Q12_TtlIsBoundedByTheMandateAndByTheRegistry() public {
        T.PriceQuote memory q = _base();
        q.validUntil = q.issuedAt + 121; // the mandate allows 120
        _expect(q, QuoteTtlTooLong.selector);
        q.validUntil = q.issuedAt + 120;
        _go(_bundle(routerA, q));
        // a mandate that allows 1000 seconds is still bounded by the registry's 300
        T.MandateTerms memory t = _terms(address(usdc));
        t.fiat.maxQuoteAge = 1000;
        bytes32 l2 = manager.lineageIdOf(customer, MERCHANT, SUBSCRIPTION, 2);
        bytes32 m2 = manager.mandateIdOf(l2, 0);
        _activate(customer, 2, address(routerA), t, _pin());
        q = _baseQuote(routerA, l2, 0, customer, address(usdc), AMOUNT, PRICE);
        q.validUntil = q.issuedAt + 301;
        PaymentRouter.QuoteBundle memory b = _bundle(routerA, q);
        vm.expectRevert(QuoteTtlTooLong.selector);
        _charge(routerA, m2, t, _pin(), 0, address(usdc), AMOUNT, 0, b);
        q.validUntil = q.issuedAt + 300;
        b = _bundle(routerA, q);
        _charge(routerA, m2, t, _pin(), 0, address(usdc), AMOUNT, 0, b);
    }

    // ------------------------------------------------------------------------------------------------------------ Q13: signer sets
    function test_Q13_RotationHonoursEarlierQuotesForTheGraceOnly() public {
        T.PriceQuote memory old = _base(); // issued now under set 1
        address[] memory members = new address[](1);
        members[0] = quoteSigner;
        vm.startPrank(gov);
        signerSets.proposeSignerSet(2, members);
        vm.warp(block.timestamp + 10);
        signerSets.activateSignerSet(2);
        vm.stopPrank();
        // inside the grace, a quote issued before the rotation still verifies
        old.validUntil = old.issuedAt + 120;
        _go(_bundle(routerA, old));
        // a quote issued AFTER the rotation under the retired set does not
        T.PriceQuote memory late = _baseQuote(routerA, lid, 1, customer, address(usdc), AMOUNT, PRICE);
        vm.warp(START + 30 days + 100);
        late = _baseQuote(routerA, lid, 1, customer, address(usdc), AMOUNT, PRICE); // set version 1 again
        PaymentRouter.QuoteBundle memory b = _bundle(routerA, late);
        vm.expectRevert(QuoteSignerSetRetired.selector);
        _charge(routerA, mid, _terms(address(usdc)), _pin(), 1, address(usdc), AMOUNT, 0, b);
    }

    function test_Q13_AStoppedSetIsRefused() public {
        PaymentRouter.QuoteBundle memory b = _bundle(routerA, _base());
        vm.prank(guardian);
        signerSets.stopSignerSet(1);
        vm.expectRevert(QuoteSignerSetStopped.selector);
        _go(b);
    }

    function test_Q13_AQuoteIssuedBeforeTheSetWasActiveIsRefused() public {
        T.PriceQuote memory q = _base();
        q.issuedAt = uint64(START - 1);
        q.validAfter = uint64(START - 1);
        q.validUntil = uint64(START + 60);
        _expect(q, QuoteSignerSetRetired.selector);
    }

    // ------------------------------------------------------------------------------------------------------------ Q14 to Q17: registry state
    function test_Q14_TokenVersionMustBeCurrent() public {
        PaymentRouter.QuoteBundle memory b = _bundle(routerA, _base());
        vm.prank(gov);
        policy.setPriceSourceSet(address(usdc), USD, SOURCE_SET); // any change of the token's policy bumps its version
        vm.expectRevert(RegistryVersionStale.selector);
        _go(b);
    }

    function test_Q15_BoundsVersionMustBeCurrent() public {
        PaymentRouter.QuoteBundle memory b = _bundle(routerA, _base());
        vm.prank(gov);
        policy.publishBounds(address(usdc), USD, 98e18, 102e18); // a new version, even with the same band
        vm.expectRevert();
        _go(b); // the token version moved too (Q14 comes first); rebuild the quote on the new versions to see Q15 alone
        T.PriceQuote memory q = _base();
        q.boundsVersion = 1; // the old bounds version with the new token version
        _expect(q, BoundsVersionStale.selector);
    }

    function test_Q16_RouteHash() public {
        T.PriceQuote memory q = _base();
        q.routeHash = keccak256(abi.encode(T.ROUTE_DIRECT_TAG, block.chainid + 1, address(usdc)));
        _expect(q, QuoteRouteMismatch.selector);
    }

    function test_Q17_PriceSourceSet() public {
        T.PriceQuote memory q = _base();
        q.priceSourceSetHash = keccak256("another source set");
        _expect(q, QuoteSourceSetMismatch.selector);
    }

    // ------------------------------------------------------------------------------------------------------------ Q18 and ADR-020: bounds
    function test_Q18_BandEdgesAreInside_JustOutsideIsNot() public {
        T.PriceQuote memory q = _base();
        q.priceE18 = 98e18 - 1;
        _expect(q, PriceOutOfBounds.selector);
        q.priceE18 = 102e18 + 1;
        _expect(q, PriceOutOfBounds.selector);
        q.priceE18 = 98e18;
        _go(_bundle(routerA, q));
    }

    function test_Q18_ATighterCurrentBandNarrowsAnExistingMandate() public {
        vm.prank(gov);
        policy.publishBounds(address(usdc), USD, 99e18, 101e18); // v2 inside v1
        T.PriceQuote memory q = _base(); // boundsVersion is now 2 (the current one)
        q.priceE18 = 98_500000000000000000; // inside the pinned v1 band, outside the current one
        _expect(q, PriceOutOfBounds.selector);
        q.priceE18 = 99e18;
        _go(_bundle(routerA, q));
    }

    function test_Q18_AWiderCurrentBandNeverWidensAnExistingMandate() public {
        vm.prank(gov);
        policy.publishBounds(address(usdc), USD, 95e18, 99_500000000000000000); // v2: shifted down, width 473 bps
        T.PriceQuote memory q = _base();
        q.priceE18 = 96e18; // inside v2, outside the pinned v1 band [98, 102]
        _expect(q, PriceOutOfBounds.selector);
        q.priceE18 = 99e18; // inside both
        _go(_bundle(routerA, q));
    }

    function test_Q18_AWiderCurrentUpperBandNeverWidensAnExistingMandate() public {
        vm.prank(gov);
        policy.publishBounds(address(usdc), USD, 98_500000000000000000, 103e18); // v2: the upper edge is above the pinned 102
        T.PriceQuote memory q = _base();
        q.priceE18 = 103e18; // inside v2, outside the pinned v1 band [98, 102]
        _expect(q, PriceOutOfBounds.selector);
        q.priceE18 = PRICE; // inside both (a price of 102 would be inside as well, but 100 tokens at 102 breach the fiat per-payment cap of the mandate)
        _go(_bundle(routerA, q));
    }

    function test_Q18_AnUnpublishedPinnedVersionCanNeverBeCharged() public {
        T.MandateTerms memory t = _terms(address(usdc));
        t.fiat.boundsVersion = 9;
        bytes32 l2 = manager.lineageIdOf(customer, MERCHANT, SUBSCRIPTION, 2);
        bytes32 m2 = manager.mandateIdOf(l2, 0);
        _activate(customer, 2, address(routerA), t, _pin());
        PaymentRouter.QuoteBundle memory b = _quote(routerA, l2, 0, customer, address(usdc), AMOUNT, PRICE);
        vm.expectRevert(BoundsNotPublished.selector);
        _charge(routerA, m2, t, _pin(), 0, address(usdc), AMOUNT, 0, b);
    }

    function test_Bounds_AreBoundedInWidth_AndWellFormed() public {
        vm.startPrank(gov);
        vm.expectRevert(BandTooWide.selector);
        policy.publishBounds(address(usdc), USD, 90e18, 100e18); // 1112 bps
        vm.expectRevert(InvalidBounds.selector);
        policy.publishBounds(address(usdc), USD, 0, 1e18);
        vm.expectRevert(InvalidBounds.selector);
        policy.publishBounds(address(usdc), USD, 5e18, 4e18);
        vm.expectRevert(BandTooWide.selector);
        policy.publishBounds(address(usdc), USD, 99e18, 104e18); // 505 bps
        vm.stopPrank();
        assertEq(policy.currentBoundsVersion(address(usdc), USD), 1, "nothing was published");
    }

    function test_Bounds_WidthIsMeasuredOnTheMinimum() public {
        vm.startPrank(gov);
        // exactly 500 bps: 100 -> 105
        uint32 v = policy.publishBounds(address(usdc), USD, 100e18, 105e18);
        assertEq(v, 2);
        vm.expectRevert(BandTooWide.selector);
        policy.publishBounds(address(usdc), USD, 100e18, 105e18 + 1e12); // a hair above 500 bps rounds up to 501
        vm.stopPrank();
        (bool published, uint256 mn, uint256 mx) = policy.bandOf(address(usdc), USD, 1);
        assertTrue(published);
        assertEq(mn, 98e18);
        assertEq(mx, 102e18); // version 1 was never changed
    }

    // ------------------------------------------------------------------------------------------------------------ Q19, Q20 and non-interference
    function test_Q19_FiatPerPaymentCap() public {
        T.PriceQuote memory q = _base();
        q.priceE18 = 102e18; // 100 tokens are worth 10,200 cents; the cap is 10,000
        _expect(q, FiatPerPaymentCapExceeded.selector);
    }

    function test_Q19_FiatTotalAndWindowCaps() public {
        T.MandateTerms memory t = _terms(address(usdc));
        t.fiat = T.FiatTerms(USD, 10_000, 0, 0, 0, 0, 15_000, 120, 1); // fiat per payment 10,000; fiat total 15,000
        t.minIntervalSeconds = 0;
        t.maxChargesPerPeriod = 0;
        bytes32 l2 = manager.lineageIdOf(customer, MERCHANT, SUBSCRIPTION, 2);
        bytes32 m2 = manager.mandateIdOf(l2, 0);
        _activate(customer, 2, address(routerA), t, _pin());
        PaymentRouter.QuoteBundle memory b = _quote(routerA, l2, 0, customer, address(usdc), 100e6, PRICE);
        _charge(routerA, m2, t, _pin(), 0, address(usdc), 100e6, 0, b);
        vm.warp(START + 30 days + 10);
        b = _quote(routerA, l2, 1, customer, address(usdc), 100e6, PRICE);
        vm.expectRevert(FiatTotalCapExceeded.selector);
        _charge(routerA, m2, t, _pin(), 1, address(usdc), 100e6, 0, b);
        b = _quote(routerA, l2, 1, customer, address(usdc), 50e6, PRICE);
        _charge(routerA, m2, t, _pin(), 1, address(usdc), 50e6, 0, b); // 15,000 exactly
    }

    function test_Q19_FiatValueTooLargeForUint64() public {
        // a band wide enough is not allowed, so exercise the arithmetic through a token with 0 decimals
        MockToken0 z = new MockToken0();
        vm.startPrank(gov);
        policy.list(address(z), 1, 0);
        policy.setPriceSourceSet(address(z), USD, SOURCE_SET);
        policy.publishBounds(address(z), USD, 1e30, 1e30);
        vm.stopPrank();
        vm.prank(merchantAdmin);
        merchantReg.setAccepted(MERCHANT, address(z), true);
        T.MandateTerms memory t = _terms(address(z));
        t.fiat = T.FiatTerms(USD, 0, 0, 0, 0, 0, 1, 120, 1); // some fiat cap so that a quote is required
        bytes32 l2 = manager.lineageIdOf(customer, MERCHANT, SUBSCRIPTION, 2);
        bytes32 m2 = manager.mandateIdOf(l2, 0);
        z.mint(customer, 1e30);
        vm.prank(customer);
        z.approve(CANONICAL, type(uint256).max);
        vm.prank(customer);
        p2.approve(address(z), address(routerA), type(uint160).max - 1, uint48(block.timestamp + 1 days));
        t.tokens[0].perPaymentMax = 0;
        t.tokens[0].dayMax = 0;
        t.tokens[0].weekMax = 0;
        t.tokens[0].thirtyDayMax = 0;
        t.tokens[0].periodMax = 0;
        t.tokens[0].totalMax = 0;
        _activate(customer, 2, address(routerA), t, _pin());
        T.PriceQuote memory q = _baseQuote(routerA, l2, 0, customer, address(z), 1e24, 1e30);
        PaymentRouter.QuoteBundle memory b = _bundle(routerA, q);
        vm.expectRevert(FiatValueTooLarge.selector);
        _charge(routerA, m2, t, _pin(), 0, address(z), 1e24, 0, b);
    }

    function test_NonInterference_AValidQuoteCannotOverrideATokenCap() public {
        // the quote says the price is right and the fiat value is fine, but the token per-payment cap is 100e6
        T.MandateTerms memory t = _terms(address(usdc));
        t.tokens[0].perPaymentMax = 50e6;
        t.fiat = T.FiatTerms(USD, 10_000, 0, 0, 0, 0, 0, 120, 1);
        bytes32 l2 = manager.lineageIdOf(customer, MERCHANT, SUBSCRIPTION, 2);
        bytes32 m2 = manager.mandateIdOf(l2, 0);
        _activate(customer, 2, address(routerA), t, _pin());
        PaymentRouter.QuoteBundle memory b = _quote(routerA, l2, 0, customer, address(usdc), 100e6, PRICE);
        vm.expectRevert(TokenPerPaymentCapExceeded.selector);
        _charge(routerA, m2, t, _pin(), 0, address(usdc), 100e6, 0, b);
    }

    function test_NonInterference_AQuoteForAMandateWithoutFiatCapsIsIgnored() public {
        T.MandateTerms memory t = _terms(address(usdc));
        t.fiat = T.FiatTerms(USD, 0, 0, 0, 0, 0, 0, 120, 1);
        bytes32 l2 = manager.lineageIdOf(customer, MERCHANT, SUBSCRIPTION, 2);
        bytes32 m2 = manager.mandateIdOf(l2, 0);
        _activate(customer, 2, address(routerA), t, _pin());
        PaymentRouter.QuoteBundle memory b = _quote(routerA, l2, 0, customer, address(usdc), 10e6, 1); // a nonsense quote
        _charge(routerA, m2, t, _pin(), 0, address(usdc), 10e6, 0, b);
        assertEq(ledger.fiatUsage(l2).total, 0, "no fiat usage is recorded without a fiat cap");
    }
}

/// A token with no decimals, to push the fiat arithmetic to its limits.
contract MockToken0 {
    string public constant name = "Zero";
    uint8 public constant decimals = 0;
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    function mint(address to, uint256 a) external {
        balanceOf[to] += a;
    }

    function approve(address s, uint256 a) external returns (bool) {
        allowance[msg.sender][s] = a;
        return true;
    }

    function transferFrom(address f, address t, uint256 a) external returns (bool) {
        uint256 al = allowance[f][msg.sender];
        if (al != type(uint256).max) allowance[f][msg.sender] = al - a;
        balanceOf[f] -= a;
        balanceOf[t] += a;
        return true;
    }
}
