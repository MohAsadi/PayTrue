// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.24;

import {Base} from "./helpers/Base.sol";
import {MockERC20} from "./helpers/MockERC20.sol";
import {FastPayTypes as T} from "../src/generated/FastPayTypes.sol";
import {IMandateManager} from "../src/interfaces/IMandateManager.sol";
import {PaymentRouter} from "../src/PaymentRouter.sol";
import "../src/Errors.sol";

/// The mandate lifecycle on the real MandateManager: activation and its refusals, the exposure index (live counts, the position map, the bound
/// of PC-18), the exits that are never gated, retire, the three pause bits, narrowing reductions and account pin updates.
contract MandatesTest is Base {
    function setUp() public override {
        super.setUp();
        _fund(customer, usdc, 10_000e6);
        _grant(customer, usdc, address(routerA), 5_000e6);
    }

    function _act(uint256 n) internal returns (bytes32 lid, bytes32 mid) {
        return _activate(customer, n, address(routerA), _terms(address(usdc)), _pin());
    }

    // ------------------------------------------------------------------------------------------------------------ activation
    function test_Activate_StoresHashesAndIndexesTheTokens() public {
        T.MandateTerms memory t = _terms(address(usdc));
        T.AccountPin memory p = _pin();
        (bytes32 lid, bytes32 mid) = _act(1);
        assertEq(lid, manager.lineageIdOf(customer, MERCHANT, SUBSCRIPTION, 1));
        assertEq(mid, manager.mandateIdOf(lid, 0));
        IMandateManager.MandateView memory v = _view(mid);
        assertEq(v.termsHash, T.hashStruct(t));
        assertEq(v.pinHash, T.hashStruct(p));
        assertEq(v.customer, customer);
        assertEq(v.router, address(routerA));
        assertEq(v.generation, 0);
        assertEq(v.pinVersion, 1);
        assertEq(v.nTokens, 1);
        assertEq(v.tokens[0], address(usdc));
        assertEq(v.expiresAt, t.expiresAt);
        assertEq(manager.live(customer, address(routerA), address(usdc)), 1);
        assertEq(manager.exposedCount(customer, address(routerA)), 1);
        assertEq(manager.exposedAt(customer, address(routerA), 0), address(usdc));
        (, , , , , bytes32 active) = manager.lineages(lid);
        assertEq(active, mid);
    }

    function test_Activate_Event_CarriesTheTermsAndPin() public {
        T.MandateTerms memory t = _terms(address(usdc));
        T.AccountPin memory p = _pin();
        bytes32 lid = manager.lineageIdOf(customer, MERCHANT, SUBSCRIPTION, 1);
        bytes32 mid = manager.mandateIdOf(lid, 0);
        vm.expectEmit(true, true, true, true, address(manager));
        emit MandateActivated(lid, mid, customer, address(routerA), T.hashStruct(t), T.hashStruct(p), t, p);
        _act(1);
    }

    event MandateActivated(bytes32 indexed lineageId, bytes32 indexed mandateId, address indexed customer, address router, bytes32 termsHash, bytes32 pinHash, T.MandateTerms terms, T.AccountPin pin);

    function test_Activate_OnlyTheCustomerOrTheGateway() public {
        vm.prank(stranger);
        vm.expectRevert(NotCustomer.selector);
        manager.activate(customer, 1, address(routerA), _terms(address(usdc)), _pin());
    }

    function test_Activate_SameNonceTwice_LineageExists() public {
        _act(1);
        vm.prank(customer);
        vm.expectRevert(LineageExists.selector);
        manager.activate(customer, 1, address(routerA), _terms(address(usdc)), _pin());
        _act(2); // another creation nonce is another lineage
    }

    function test_Activate_RouterMustBeBindable() public {
        PaymentRouter unregistered = _newRouter();
        vm.prank(customer);
        vm.expectRevert(RouterNotBindable.selector);
        manager.activate(customer, 1, address(unregistered), _terms(address(usdc)), _pin());
    }

    function test_Activate_TermsShape() public {
        T.MandateTerms memory t = _terms(address(usdc));
        T.AccountPin memory p = _pin();
        t.tokens = new T.TokenTerms[](0);
        vm.startPrank(customer);
        vm.expectRevert(abi.encodeWithSelector(TermsInvalid.selector, uint8(1)));
        manager.activate(customer, 1, address(routerA), t, p);
        t = _terms(address(usdc));
        t.tokens = new T.TokenTerms[](4);
        vm.expectRevert(abi.encodeWithSelector(TermsInvalid.selector, uint8(1)));
        manager.activate(customer, 1, address(routerA), t, p);
        address[] memory dup = new address[](2);
        dup[0] = address(usdc);
        dup[1] = address(usdc);
        t = _termsOf(dup);
        vm.expectRevert(abi.encodeWithSelector(TermsInvalid.selector, uint8(2)));
        manager.activate(customer, 1, address(routerA), t, p);
        address[] memory unordered = _sorted2(address(usdc), address(dai));
        (unordered[0], unordered[1]) = (unordered[1], unordered[0]);
        t = _termsOf(unordered);
        vm.expectRevert(abi.encodeWithSelector(TermsInvalid.selector, uint8(2)));
        manager.activate(customer, 1, address(routerA), t, p);
        address[] memory zero = new address[](1);
        t = _termsOf(zero);
        vm.expectRevert(abi.encodeWithSelector(TermsInvalid.selector, uint8(2)));
        manager.activate(customer, 1, address(routerA), t, p);
        t = _terms(address(usdc));
        t.periodSeconds = 0;
        vm.expectRevert(abi.encodeWithSelector(TermsInvalid.selector, uint8(3)));
        manager.activate(customer, 1, address(routerA), t, p);
        vm.stopPrank();
    }

    function test_Activate_ExtensionsMustBeZero() public {
        T.MandateTerms memory t = _terms(address(usdc));
        t.extensionsHash = keccak256("conversion consent");
        vm.prank(customer);
        vm.expectRevert(ExtensionsNotSupported.selector);
        manager.activate(customer, 1, address(routerA), t, _pin());
    }

    function test_Activate_PinMustBeWellFormedLiveAndVersionOne() public {
        T.AccountPin memory p = _pin();
        T.MandateTerms memory t = _terms(address(usdc));
        vm.startPrank(customer);
        p.pinVersion = 0;
        vm.expectRevert(AccountPinMalformed.selector);
        manager.activate(customer, 1, address(routerA), t, p);
        p.pinVersion = 2;
        vm.expectRevert(PinVersionMismatch.selector);
        manager.activate(customer, 1, address(routerA), t, p);
        p = _pin();
        p.accountMode = 5;
        vm.expectRevert(AccountPinMalformed.selector);
        manager.activate(customer, 1, address(routerA), t, p);
        vm.stopPrank();
        // an EOA pin on an account that now has code: PIN_OK fails
        vm.etch(customer, hex"6001");
        vm.prank(customer);
        vm.expectRevert(AccountPinMismatch.selector);
        manager.activate(customer, 1, address(routerA), t, _pin());
    }

    // ------------------------------------------------------------------------------------------------------------ exposure index
    function test_Exposure_CountsSharedTokensOnce() public {
        (, bytes32 m1) = _act(1);
        (, bytes32 m2) = _act(2); // two mandates on the same token and router
        assertEq(manager.live(customer, address(routerA), address(usdc)), 2);
        assertEq(manager.exposedCount(customer, address(routerA)), 1);
        _revoke(m1);
        assertEq(manager.live(customer, address(routerA), address(usdc)), 1);
        assertEq(manager.exposedCount(customer, address(routerA)), 1);
        _revoke(m2);
        assertEq(manager.exposedCount(customer, address(routerA)), 0);
        assertEq(manager.exposedPos(customer, address(routerA), address(usdc)), 0);
    }

    function _tokens(uint256 n) internal returns (MockERC20[] memory toks) {
        toks = new MockERC20[](n);
        for (uint256 i = 0; i < n; ++i) {
            toks[i] = new MockERC20();
        }
    }

    function test_Exposure_TheBoundOfEightDistinctTokensPerRouter() public {
        MockERC20[] memory toks = _tokens(9);
        for (uint256 i = 0; i < 8; ++i) {
            _activate(customer, 100 + i, address(routerA), _terms(address(toks[i])), _pin());
        }
        assertEq(manager.exposedCount(customer, address(routerA)), 8);
        vm.prank(customer);
        vm.expectRevert(ExposureLimit.selector);
        manager.activate(customer, 200, address(routerA), _terms(address(toks[8])), _pin());
        // a mandate on a token that is already exposed adds nothing and is allowed
        _activate(customer, 201, address(routerA), _terms(address(toks[3])), _pin());
        // the same tokens on the OTHER router are a separate count
        _activate(customer, 202, address(routerB), _terms(address(toks[8])), _pin());
        assertEq(manager.exposedCount(customer, address(routerB)), 1);
    }

    function test_Exposure_SwapAndPopKeepsThePositionMapExact() public {
        MockERC20[] memory toks = _tokens(5);
        bytes32[] memory ids = new bytes32[](5);
        for (uint256 i = 0; i < 5; ++i) {
            (, ids[i]) = _activate(customer, 300 + i, address(routerA), _terms(address(toks[i])), _pin());
        }
        // remove from the middle, the front and the back, and check every remaining position
        _revoke(ids[2]);
        _revoke(ids[0]);
        _revoke(ids[4]);
        uint256 n = manager.exposedCount(customer, address(routerA));
        assertEq(n, 2);
        for (uint256 j = 0; j < n; ++j) {
            address t = manager.exposedAt(customer, address(routerA), j);
            assertEq(manager.exposedPos(customer, address(routerA), t), j + 1);
            assertTrue(t == address(toks[1]) || t == address(toks[3]));
        }
        assertEq(manager.exposedPos(customer, address(routerA), address(toks[2])), 0);
        assertEq(manager.exposedPos(customer, address(routerA), address(toks[0])), 0);
    }

    function _revoke(bytes32 mid) internal {
        vm.prank(customer);
        manager.revoke(customer, mid);
    }

    function test_Exposure_UnionCountMatchesTheDefinition() public {
        MockERC20[] memory toks = _tokens(3);
        _activate(customer, 1, address(routerA), _terms(address(toks[0])), _pin());
        T.TokenTerms[] memory two = new T.TokenTerms[](2);
        two[0] = _tokenTerms(address(toks[0]));
        two[1] = _tokenTerms(address(toks[1]));
        assertEq(manager.exposedUnionCount(customer, address(routerA), two), 2);
        assertEq(manager.exposedUnionCount(customer, address(routerB), two), 2);
        assertEq(manager.exposedUnionCount(stranger, address(routerA), two), 2);
    }

    // ------------------------------------------------------------------------------------------------------------ exits
    function test_Revoke_OnlyTheCustomer_AndOnlyOnce() public {
        (, bytes32 mid) = _act(1);
        vm.prank(stranger);
        vm.expectRevert(NotCustomer.selector);
        manager.revoke(stranger, mid);
        vm.prank(stranger);
        vm.expectRevert(NotCustomer.selector);
        manager.revoke(customer, mid);
        _revoke(mid);
        vm.prank(customer);
        vm.expectRevert(MandateNotActive.selector);
        manager.revoke(customer, mid);
        IMandateManager.MandateView memory v = _view(mid);
        assertEq(v.status, 1);
        assertEq(v.reason, 1);
    }

    function test_Exit_IsNeverBlockedByPauseOrByARouterThatWasDisabled() public {
        (, bytes32 mid) = _act(1);
        vm.prank(riskService);
        manager.setPauseBit(mid, 2, true);
        vm.prank(riskService);
        manager.setPauseBit(mid, 4, true);
        vm.prank(customer);
        manager.pause(customer, mid);
        vm.prank(guardian);
        routers.emergencyDisable(address(routerA));
        _revoke(mid); // I-EXIT: with every pause bit set and the router disabled, the customer can still leave
        assertEq(manager.exposedCount(customer, address(routerA)), 0);
    }

    function test_Revoke_OfARetiredMandateDoesNotDecrementTwice() public {
        (, bytes32 mid) = _act(1);
        (, bytes32 mid2) = _act(2);
        vm.warp(START + 366 days);
        manager.retire(mid);
        assertEq(manager.live(customer, address(routerA), address(usdc)), 1);
        _revoke(mid); // allowed: it is still ACTIVE in status; the index was already released
        assertEq(manager.live(customer, address(routerA), address(usdc)), 1, "no second decrement");
        manager.retire(mid2);
        assertEq(manager.live(customer, address(routerA), address(usdc)), 0);
    }

    function test_Retire_OnlyAfterExpiry_OnlyOnce() public {
        (, bytes32 mid) = _act(1);
        vm.expectRevert(NotRetirable.selector);
        manager.retire(mid);
        vm.warp(START + 365 days);
        manager.retire(mid);
        assertEq(manager.exposedCount(customer, address(routerA)), 0);
        vm.expectRevert(NotRetirable.selector);
        manager.retire(mid);
        vm.expectRevert(UnknownMandate.selector);
        manager.retire(keccak256("no such mandate"));
    }

    // ------------------------------------------------------------------------------------------------------------ pause
    function test_Pause_BitsAreIndependent() public {
        (, bytes32 mid) = _act(1);
        vm.prank(customer);
        manager.pause(customer, mid);
        vm.prank(riskService);
        manager.setPauseBit(mid, 2, true);
        assertEq(_view(mid).pause, 3);
        vm.prank(customer);
        manager.resume(customer, mid);
        assertEq(_view(mid).pause, 2, "the customer cannot clear the risk bit");
        vm.prank(riskService);
        manager.setPauseBit(mid, 2, false);
        assertEq(_view(mid).pause, 0);
    }

    function test_Pause_OnlyThePauseAuthorityTouchesRiskAndDelegationBits() public {
        (, bytes32 mid) = _act(1);
        vm.prank(customer);
        vm.expectRevert(NotPauseAuthority.selector);
        manager.setPauseBit(mid, 2, true);
        vm.prank(guardian);
        vm.expectRevert(NotPauseAuthority.selector);
        manager.setPauseBit(mid, 4, true);
        vm.prank(riskService);
        vm.expectRevert(NotPauseAuthority.selector);
        manager.setPauseBit(mid, 1, true); // the authority cannot set the customer's bit
        vm.prank(stranger);
        vm.expectRevert(NotCustomer.selector);
        manager.pause(customer, mid);
    }

    function test_Pause_ARevokedMandateCannotBePaused() public {
        (, bytes32 mid) = _act(1);
        _revoke(mid);
        vm.prank(customer);
        vm.expectRevert(MandateNotActive.selector);
        manager.pause(customer, mid);
    }

    // ------------------------------------------------------------------------------------------------------------ reduce
    function test_Reduce_Narrowing_ReleasesTheDroppedToken() public {
        address[] memory two = _sorted2(address(usdc), address(dai));
        T.MandateTerms memory wide = _termsOf(two);
        _activate(customer, 1, address(routerA), wide, _pin());
        bytes32 mid = manager.mandateIdOf(manager.lineageIdOf(customer, MERCHANT, SUBSCRIPTION, 1), 0);
        assertEq(manager.exposedCount(customer, address(routerA)), 2);
        T.MandateTerms memory narrow = _termsOf(_one(address(dai)));
        narrow.tokens[0].perPaymentMax = 50e6;
        vm.prank(customer);
        manager.reduce(customer, mid, wide, narrow);
        assertEq(manager.exposedCount(customer, address(routerA)), 1);
        assertEq(manager.live(customer, address(routerA), address(usdc)), 0);
        IMandateManager.MandateView memory v = _view(mid);
        assertEq(v.termsHash, T.hashStruct(narrow));
        assertEq(v.nTokens, 1);
        assertEq(v.tokens[0], address(dai));
        assertEq(v.tokens[1], address(0));
    }

    function _one(address a) internal pure returns (address[] memory r) {
        r = new address[](1);
        r[0] = a;
    }

    function test_Reduce_Widening_IsRefused_OnEveryDimension() public {
        (, bytes32 mid) = _act(1);
        T.MandateTerms memory old = _terms(address(usdc));
        T.MandateTerms memory n;
        vm.startPrank(customer);

        n = _terms(address(usdc));
        n.tokens[0].perPaymentMax = old.tokens[0].perPaymentMax + 1;
        vm.expectRevert(TermsNotContained.selector);
        manager.reduce(customer, mid, old, n);

        n = _terms(address(usdc));
        n.tokens[0].totalMax = 0; // no cap is wider than any cap
        vm.expectRevert(TermsNotContained.selector);
        manager.reduce(customer, mid, old, n);

        n = _terms(address(usdc));
        n.fiat.dayMaxMinor = old.fiat.dayMaxMinor + 1;
        vm.expectRevert(TermsNotContained.selector);
        manager.reduce(customer, mid, old, n);

        n = _terms(address(usdc));
        n.fiat.maxQuoteAge = old.fiat.maxQuoteAge + 1;
        vm.expectRevert(TermsNotContained.selector);
        manager.reduce(customer, mid, old, n);

        n = _terms(address(usdc));
        n.fiat.boundsVersion = 2; // K.6: a different bounds version is not a narrowing
        vm.expectRevert(TermsNotContained.selector);
        manager.reduce(customer, mid, old, n);

        n = _terms(address(usdc));
        n.maxFeeBps = old.maxFeeBps + 1;
        vm.expectRevert(TermsNotContained.selector);
        manager.reduce(customer, mid, old, n);

        n = _terms(address(usdc));
        n.minIntervalSeconds = old.minIntervalSeconds - 1;
        vm.expectRevert(TermsNotContained.selector);
        manager.reduce(customer, mid, old, n);

        n = _terms(address(usdc));
        n.expiresAt = old.expiresAt + 1;
        vm.expectRevert(TermsNotContained.selector);
        manager.reduce(customer, mid, old, n);

        n = _terms(address(usdc));
        n.merchantId = keccak256("another merchant");
        vm.expectRevert(TermsNotContained.selector);
        manager.reduce(customer, mid, old, n);

        n = _termsOf(_sorted2(address(usdc), address(dai)));
        vm.expectRevert(TermsNotContained.selector);
        manager.reduce(customer, mid, old, n);
        vm.stopPrank();
    }

    function test_Reduce_NeedsTheStoredTerms_AndAFutureExpiry() public {
        (, bytes32 mid) = _act(1);
        T.MandateTerms memory old = _terms(address(usdc));
        T.MandateTerms memory wrongOld = _terms(address(usdc));
        wrongOld.tokens[0].perPaymentMax = 99e6;
        T.MandateTerms memory n = _terms(address(usdc));
        n.tokens[0].perPaymentMax = 10e6;
        vm.startPrank(customer);
        vm.expectRevert(TermsHashMismatch.selector);
        manager.reduce(customer, mid, wrongOld, n);
        vm.warp(START + 364 days);
        n.expiresAt = uint64(START + 100 days); // already past
        vm.expectRevert(TermsNotContained.selector);
        manager.reduce(customer, mid, old, n);
        vm.stopPrank();
    }

    function test_Reduce_AShorterExpiryEndsTheMandateEarly() public {
        (bytes32 lid, bytes32 mid) = _act(1);
        T.MandateTerms memory old = _terms(address(usdc));
        T.MandateTerms memory n = _terms(address(usdc));
        n.expiresAt = uint64(START + 10 days);
        vm.prank(customer);
        manager.reduce(customer, mid, old, n);
        assertEq(_view(mid).expiresAt, START + 10 days);
        vm.warp(START + 10 days);
        PaymentRouter.QuoteBundle memory q = _quote(routerA, lid, 0, customer, address(usdc), 10e6, PRICE);
        vm.expectRevert(MandateNotConsumable.selector);
        _charge(routerA, mid, n, _pin(), 0, address(usdc), 10e6, 0, q);
        manager.retire(mid); // and it can be retired from the new expiry on
        assertEq(manager.exposedCount(customer, address(routerA)), 0);
    }

    function test_Reduce_ThenChargeUsesTheNewTerms() public {
        (bytes32 lid, bytes32 mid) = _act(1);
        T.MandateTerms memory old = _terms(address(usdc));
        T.MandateTerms memory n = _terms(address(usdc));
        n.tokens[0].perPaymentMax = 40e6;
        n.fiat.perPaymentMaxMinor = 4_000;
        vm.prank(customer);
        manager.reduce(customer, mid, old, n);
        PaymentRouter.QuoteBundle memory q = _quote(routerA, lid, 0, customer, address(usdc), 50e6, PRICE);
        vm.expectRevert(TermsHashMismatch.selector);
        _charge(routerA, mid, old, _pin(), 0, address(usdc), 50e6, 0, q);
        vm.expectRevert(TokenPerPaymentCapExceeded.selector);
        _charge(routerA, mid, n, _pin(), 0, address(usdc), 50e6, 0, q);
        q = _quote(routerA, lid, 0, customer, address(usdc), 40e6, PRICE);
        _charge(routerA, mid, n, _pin(), 0, address(usdc), 40e6, 0, q);
    }

    // ------------------------------------------------------------------------------------------------------------ account pin
    function test_PinUpdate_IncrementsTheVersion_AndChangesNothingElse() public {
        (bytes32 lid, bytes32 mid) = _act(1);
        T.AccountPin memory p2_ = _pin();
        p2_.pinVersion = 2;
        p2_.signatureMode = 0; // a stricter mode: DIRECT_ONLY
        IMandateManager.MandateView memory before_ = _view(mid);
        vm.prank(customer);
        manager.updateAccountPin(customer, mid, p2_);
        IMandateManager.MandateView memory after_ = _view(mid);
        assertEq(after_.pinVersion, 2);
        assertEq(after_.pinHash, T.hashStruct(p2_));
        // I-ACCT-NOWIDEN: every other field of the record is as it was
        assertEq(after_.termsHash, before_.termsHash);
        assertEq(after_.customer, before_.customer);
        assertEq(after_.router, before_.router);
        assertEq(after_.status, before_.status);
        assertEq(after_.pause, before_.pause);
        assertEq(after_.expiresAt, before_.expiresAt);
        assertEq(after_.generation, before_.generation);
        (, , uint32 pv, , ,) = manager.lineages(lid);
        assertEq(pv, 2);
    }

    function test_PinUpdate_VersionMustBeExactlyPlusOne() public {
        (, bytes32 mid) = _act(1);
        T.AccountPin memory p = _pin();
        vm.startPrank(customer);
        vm.expectRevert(PinVersionMismatch.selector);
        manager.updateAccountPin(customer, mid, p); // the same version
        p.pinVersion = 3;
        vm.expectRevert(PinVersionMismatch.selector);
        manager.updateAccountPin(customer, mid, p); // a skip
        p.pinVersion = 2;
        p.accountMode = 0;
        vm.expectRevert(AccountPinMalformed.selector);
        manager.updateAccountPin(customer, mid, p);
        vm.stopPrank();
    }

    function test_PinUpdate_OnlyTheCustomer_AndOnlyWhileLive() public {
        (, bytes32 mid) = _act(1);
        T.AccountPin memory p = _pin();
        p.pinVersion = 2;
        vm.prank(stranger);
        vm.expectRevert(NotCustomer.selector);
        manager.updateAccountPin(customer, mid, p);
        _revoke(mid);
        vm.prank(customer);
        vm.expectRevert(MandateNotActive.selector);
        manager.updateAccountPin(customer, mid, p);
    }

    function test_PinUpdate_ThenChargeNeedsTheNewPin() public {
        (bytes32 lid, bytes32 mid) = _act(1);
        T.AccountPin memory p2_ = _pin();
        p2_.pinVersion = 2;
        vm.prank(customer);
        manager.updateAccountPin(customer, mid, p2_);
        PaymentRouter.QuoteBundle memory q = _quote(routerA, lid, 0, customer, address(usdc), 10e6, PRICE);
        vm.expectRevert(PinHashMismatch.selector);
        _charge(routerA, mid, _terms(address(usdc)), _pin(), 0, address(usdc), 10e6, 0, q);
        _charge(routerA, mid, _terms(address(usdc)), p2_, 0, address(usdc), 10e6, 0, q);
    }

    function test_Spend_NonceIsGatewayOnly() public {
        vm.prank(customer);
        vm.expectRevert(NotGateway.selector);
        manager.spendNonce(customer, 1);
        vm.prank(address(gateway));
        manager.spendNonce(customer, 1);
        vm.prank(address(gateway));
        vm.expectRevert(AuthorizationReplayed.selector);
        manager.spendNonce(customer, 1);
    }
}
