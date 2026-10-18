// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {IP2} from "./helpers/Base.sol";
import {Builders} from "./helpers/Builders.sol";
import {MockERC20} from "./helpers/MockERC20.sol";
import {FastPayTypes as T} from "../src/generated/FastPayTypes.sol";
import {IMandateManager} from "../src/interfaces/IMandateManager.sol";
import {PaymentRouter} from "../src/PaymentRouter.sol";
import "../src/Errors.sol";

/// Successor activation on the real contracts: every predicate of document 12 section 5.3 (A1 to O1E) accepts its passing case and refuses
/// its failing case with the error of the model, the effects E1 to E6, and what a successor must keep (counters, settle-once, pause bits,
/// siblings, Permit2).
contract SuccessorTest is Builders {
    bytes32 lid;
    bytes32 m0;

    function setUp() public override {
        super.setUp();
        _fund(customer, usdc, 10_000e6);
        _fund(customer, dai, 10_000e6);
        _grant(customer, usdc, address(routerA), 5_000e6);
        (lid, m0) = _activate(customer, 1, address(routerA), _terms(address(usdc)), _pin());
    }

    // ------------------------------------------------------------------------------------------------------------ builders (helpers/Builders.sol)
    /// The default successor: generation 1 of lineage 1 on router B, the same token, the same caps.
    function _default(uint8 kind, address newRouter) internal returns (IMandateManager.SuccessorRequest memory) {
        T.MandateTerms memory pt = _terms(address(usdc));
        T.MandateTerms memory nt = _terms(address(usdc));
        T.AccountPin memory p = _pin();
        return _req(pt, p, nt, p, _auth(Sp(lid, m0, bytes32(0), 0, kind, newRouter), pt, nt, p));
    }

    function _prepareNormal() internal {
        _grant(customer, usdc, address(routerB), 500e6); // S1
        _lock(address(usdc), address(routerA)); // S2
    }

    function _go(IMandateManager.SuccessorRequest memory r) internal returns (bytes32) {
        vm.prank(customer);
        return manager.activateSuccessor(customer, r);
    }

    function _fail(IMandateManager.SuccessorRequest memory r, bytes memory err) internal {
        vm.expectRevert(err);
        vm.prank(customer);
        manager.activateSuccessor(customer, r);
    }

    // ------------------------------------------------------------------------------------------------------------ the happy path and E1 to E6
    function test_Normal_Migration_Effects() public {
        _prepareNormal();
        IMandateManager.SuccessorRequest memory r = _default(NORMAL, address(routerB));
        bytes32 m1 = _go(r);
        assertEq(m1, manager.mandateIdOf(lid, 1));
        IMandateManager.MandateView memory old = _view(m0);
        IMandateManager.MandateView memory nw = _view(m1);
        assertEq(old.status, 1, "E1: the predecessor is revoked");
        assertEq(old.reason, 2, "E1: as superseded by a migration");
        assertEq(nw.status, 0);
        assertEq(nw.router, address(routerB));
        assertEq(nw.generation, 1);
        assertEq(nw.predecessorId, m0);
        assertEq(nw.lineageId, lid);
        assertEq(nw.termsHash, T.hashStruct(_terms(address(usdc))));
        (, uint32 gen, , bool terminated, , bytes32 active) = manager.lineages(lid);
        assertEq(active, m1, "E2: the lineage's active mandate");
        assertEq(gen, 1);
        assertFalse(terminated);
        assertTrue(manager.usedNonce(customer, r.auth.nonce), "E4: the nonce is spent");
        assertEq(manager.live(customer, address(routerA), address(usdc)), 0, "E6: the old exposure is released");
        assertEq(manager.live(customer, address(routerB), address(usdc)), 1, "E6: the new exposure is counted");
        assertEq(manager.exposedCount(customer, address(routerA)), 0);
        assertEq(manager.exposedCount(customer, address(routerB)), 1);
    }

    function test_Migration_WritesNothingToPermit2() public {
        _prepareNormal();
        (uint160 aOld, uint48 eOld, uint48 nOld) = p2.allowance(customer, address(usdc), address(routerA));
        (uint160 aNew, uint48 eNew, uint48 nNew) = p2.allowance(customer, address(usdc), address(routerB));
        _go(_default(NORMAL, address(routerB)));
        (uint160 a1, uint48 e1, uint48 n1) = p2.allowance(customer, address(usdc), address(routerA));
        (uint160 a2, uint48 e2, uint48 n2) = p2.allowance(customer, address(usdc), address(routerB));
        assertEq(a1, aOld);
        assertEq(e1, eOld);
        assertEq(n1, nOld);
        assertEq(a2, aNew);
        assertEq(e2, eNew);
        assertEq(n2, nNew);
    }

    function test_Migration_TheOldRouterCanNoLongerChargeThePredecessor() public {
        _prepareNormal();
        _go(_default(NORMAL, address(routerB)));
        _grant(customer, usdc, address(routerA), 100e6); // the customer re-grants the old allowance: the allowance alone must not matter
        PaymentRouter.QuoteBundle memory q = _quote(routerA, lid, 0, customer, address(usdc), 10e6, PRICE);
        vm.expectRevert(MandateNotConsumable.selector);
        _charge(routerA, m0, _terms(address(usdc)), _pin(), 0, address(usdc), 10e6, 0, q);
    }

    function test_Migration_CountersAndSettledCyclesCarryOver() public {
        PaymentRouter.QuoteBundle memory q = _quote(routerA, lid, 0, customer, address(usdc), 60e6, PRICE);
        _charge(routerA, m0, _terms(address(usdc)), _pin(), 0, address(usdc), 60e6, 0, q);
        _prepareNormal();
        bytes32 m1 = _go(_default(NORMAL, address(routerB)));
        // the usage is the lineage's, not the mandate's
        assertEq(ledger.tokenUsage(lid, address(usdc)).total, 60e6);
        // I-ONCE: cycle 0 settled under router A cannot settle again under router B in the next generation
        q = _quote(routerB, lid, 0, customer, address(usdc), 10e6, PRICE);
        vm.warp(START + 2 hours);
        q = _quote(routerB, lid, 0, customer, address(usdc), 10e6, PRICE);
        vm.expectRevert(PaymentAlreadySettled.selector);
        _charge(routerB, m1, _terms(address(usdc)), _pin(), 0, address(usdc), 10e6, 0, q);
        // the next cycle charges under router B and adds to the same counters
        vm.warp(START + 31 days);
        q = _quote(routerB, lid, 1, customer, address(usdc), 40e6, PRICE);
        _charge(routerB, m1, _terms(address(usdc)), _pin(), 1, address(usdc), 40e6, 0, q);
        assertEq(ledger.tokenUsage(lid, address(usdc)).total, 100e6);
    }

    function test_Migration_PauseBitsAreInherited() public {
        _prepareNormal();
        vm.prank(customer);
        manager.pause(customer, m0);
        vm.prank(riskService);
        manager.setPauseBit(m0, 2, true);
        bytes32 m1 = _go(_default(NORMAL, address(routerB)));
        assertEq(_view(m1).pause, 3, "E3: a successor cannot be a way out of a stop");
    }

    function test_Migration_SiblingsAreUntouched() public {
        (bytes32 l2, bytes32 sib) = _activate(customer, 2, address(routerA), _terms(address(usdc)), _pin());
        l2;
        _grant(customer, usdc, address(routerB), 500e6);
        // normal mode, the token is shared with the sibling: the old allowance stays (bounded) and the sibling keeps charging
        IMandateManager.MandateView memory before_ = _view(sib);
        _go(_default(NORMAL, address(routerB)));
        IMandateManager.MandateView memory after_ = _view(sib);
        assertEq(after_.status, before_.status);
        assertEq(after_.pause, before_.pause);
        assertEq(after_.termsHash, before_.termsHash);
        assertEq(manager.live(customer, address(routerA), address(usdc)), 1, "the sibling still counts");
        (uint160 a,,) = p2.allowance(customer, address(usdc), address(routerA));
        assertEq(a, 5_000e6, "Post6: the sibling's funding is exactly as before");
    }

    function test_Migration_SecondGenerationUsesTheGrandparentInTheSnapshot() public {
        _prepareNormal();
        bytes32 m1 = _go(_default(NORMAL, address(routerB)));
        // back to router A: lock B and grant A
        _grant(customer, usdc, address(routerA), 500e6);
        _lock(address(usdc), address(routerB));
        T.MandateTerms memory pt = _terms(address(usdc));
        T.MandateTerms memory nt = _terms(address(usdc));
        T.AccountPin memory p = _pin();
        T.SuccessorAuthorization memory a = _auth(Sp(lid, m1, m0, 1, NORMAL, address(routerA)), pt, nt, p);
        bytes32 m2 = _go(_req(pt, p, nt, p, a));
        assertEq(m2, manager.mandateIdOf(lid, 2));
        assertEq(_view(m2).generation, 2);
        // a snapshot built with the wrong generation or the wrong grandparent is refused
        _lock(address(usdc), address(routerA));
        _grant(customer, usdc, address(routerB), 500e6);
        T.SuccessorAuthorization memory bad = _auth(Sp(lid, m2, m1, 1, NORMAL, address(routerB)), pt, nt, p); // generation 1 instead of 2
        _fail(_req(pt, p, nt, p, bad), abi.encodeWithSelector(AuthorizationMismatch.selector));
    }

    // ------------------------------------------------------------------------------------------------------------ A1, A2, A3
    function test_A1_AStrangerCannotActivateWithoutTheCustomersSignature() public {
        _prepareNormal();
        IMandateManager.SuccessorRequest memory r = _default(NORMAL, address(routerB));
        vm.prank(stranger);
        vm.expectRevert(NotCustomer.selector);
        manager.activateSuccessor(customer, r);
        vm.prank(stranger);
        vm.expectRevert(NotCustomer.selector);
        manager.activateSuccessor(stranger, r); // naming oneself does not help: the mandate is not theirs
    }

    function test_A1_ThroughTheGateway_WithTheStoredPinGoverning() public {
        _prepareNormal();
        IMandateManager.SuccessorRequest memory r = _default(NORMAL, address(routerB));
        bytes memory sig = _sign(customerKey, _mandatesDigest(T.hashStruct(r.auth)));
        vm.prank(stranger);
        bytes32 m1 = gateway.activateSuccessorBySig(r, sig);
        assertEq(_view(m1).status, 0);
        assertEq(manager.live(customer, address(routerB), address(usdc)), 1);
    }

    function test_A1_TheGatewayRefusesAForgedOrReplayedSignature() public {
        _prepareNormal();
        IMandateManager.SuccessorRequest memory r = _default(NORMAL, address(routerB));
        (, uint256 otherKey) = makeAddrAndKey("forger");
        bytes memory forged = _sign(otherKey, _mandatesDigest(T.hashStruct(r.auth)));
        vm.expectRevert(NotCustomer.selector);
        gateway.activateSuccessorBySig(r, forged);
        bytes memory sig = _sign(customerKey, _mandatesDigest(T.hashStruct(r.auth)));
        gateway.activateSuccessorBySig(r, sig);
        vm.expectRevert(); // the predecessor is gone (L1) and the nonce is spent; either ends the replay
        gateway.activateSuccessorBySig(r, sig);
    }

    function test_A1_AStoredDirectOnlyPinAcceptsNoRelayedSuccessor() public {
        T.AccountPin memory np = _pin();
        np.pinVersion = 2;
        np.signatureMode = 0;
        vm.prank(customer);
        manager.updateAccountPin(customer, m0, np);
        _prepareNormal();
        T.MandateTerms memory pt = _terms(address(usdc));
        T.MandateTerms memory nt = _terms(address(usdc));
        T.SuccessorAuthorization memory a = _auth(Sp(lid, m0, bytes32(0), 0, NORMAL, address(routerB)), pt, nt, np);
        IMandateManager.SuccessorRequest memory r = _req(pt, np, nt, np, a);
        bytes memory sig = _sign(customerKey, _mandatesDigest(T.hashStruct(a)));
        vm.expectRevert(SignatureModeNotPermitted.selector);
        gateway.activateSuccessorBySig(r, sig);
        _go(r); // the customer's own transaction works
    }

    function test_A2_DeadlineAndNonce() public {
        _prepareNormal();
        IMandateManager.SuccessorRequest memory r = _default(NORMAL, address(routerB));
        vm.warp(deadline + 1);
        _fail(r, abi.encodeWithSelector(AuthorizationExpired.selector));
        vm.warp(deadline); // the boundary is valid
        _go(r);
    }

    function test_A2_ANonceUsedByAnotherMessageIsRefused() public {
        _prepareNormal();
        IMandateManager.SuccessorRequest memory r = _default(NORMAL, address(routerB));
        vm.prank(address(gateway));
        manager.spendNonce(customer, r.auth.nonce);
        _fail(r, abi.encodeWithSelector(AuthorizationReplayed.selector));
    }

    function test_A3_EveryBoundFieldMustMatch() public {
        _prepareNormal();
        IMandateManager.SuccessorRequest memory r;
        bytes memory err = abi.encodeWithSelector(AuthorizationMismatch.selector);

        r = _default(NORMAL, address(routerB));
        r.auth.customer = stranger;
        _fail(r, err);

        r = _default(NORMAL, address(routerB));
        r.auth.lineageId = keccak256("another lineage");
        _fail(r, err);

        r = _default(NORMAL, address(routerB));
        r.auth.newTermsHash = keccak256("other terms");
        _fail(r, err);

        r = _default(NORMAL, address(routerB));
        r.auth.newRouterCodeHash = keccak256("other code");
        _fail(r, err);

        r = _default(NORMAL, address(routerB));
        r.auth.newRouterVersion = 9;
        _fail(r, err);

        r = _default(NORMAL, address(routerB));
        r.auth.accountPin = _pin(); // a separate copy: the default request shares one memory struct for the pins
        r.auth.accountPin.signatureMode = 0; // the authorization names another pin than the one supplied
        _fail(r, err);

        r = _default(NORMAL, address(routerB));
        r.auth.termsSnapshotHash = keccak256("another snapshot");
        _fail(r, err);

        // the new terms are the ones that were signed: a relayer who changes one cap breaks newTermsHash
        r = _default(NORMAL, address(routerB));
        r.newTerms.tokens[0].perPaymentMax -= 1;
        _fail(r, err);
    }

    function test_A3_TheSnapshotCoversCustomerAnchorAndBoundsVersion() public {
        // ADR-020 and F-06/F-07: customer, anchorStartsAt and boundsVersion are part of the snapshot, so changing any of them changes the hash
        T.MandateTerms memory t = _terms(address(usdc));
        bytes32 base = T.snapshotHash(lid, bytes32(0), 0, customer, t);
        assertTrue(base != T.snapshotHash(lid, bytes32(0), 0, stranger, t), "customer");
        T.MandateTerms memory t2 = _terms(address(usdc));
        t2.anchorStartsAt += 1;
        assertTrue(base != T.snapshotHash(lid, bytes32(0), 0, customer, t2), "anchorStartsAt");
        t2 = _terms(address(usdc));
        t2.fiat.boundsVersion = 2;
        assertTrue(base != T.snapshotHash(lid, bytes32(0), 0, customer, t2), "boundsVersion");
        t2 = _terms(address(usdc));
        t2.fiat.maxQuoteAge += 1;
        assertTrue(base != T.snapshotHash(lid, bytes32(0), 0, customer, t2), "maxQuoteAge");
    }

    // ------------------------------------------------------------------------------------------------------------ L1
    function test_L1_PredecessorMustBeTheActiveMandateOfALiveLineage() public {
        _prepareNormal();
        IMandateManager.SuccessorRequest memory r = _default(NORMAL, address(routerB));
        bytes memory err = abi.encodeWithSelector(WrongPredecessor.selector);
        vm.prank(customer);
        manager.revoke(customer, m0);
        _fail(r, err); // revoked
    }

    function test_L1_AnExpiredPredecessorIsRefused_AndASupersededOneToo() public {
        _prepareNormal();
        IMandateManager.SuccessorRequest memory r = _default(NORMAL, address(routerB));
        _go(r);
        IMandateManager.SuccessorRequest memory again = _default(NORMAL, address(routerB));
        _fail(again, abi.encodeWithSelector(WrongPredecessor.selector)); // m0 is superseded
        vm.warp(START + 365 days); // m1 has expired
        T.MandateTerms memory pt = _terms(address(usdc));
        T.AccountPin memory p = _pin();
        bytes32 m1 = manager.mandateIdOf(lid, 1);
        T.SuccessorAuthorization memory a = _auth(Sp(lid, m1, m0, 1, NORMAL, address(routerA)), pt, pt, p);
        a.deadline = uint64(block.timestamp + 1 days);
        _fail(_req(pt, p, pt, p, a), abi.encodeWithSelector(WrongPredecessor.selector));
    }

    // ------------------------------------------------------------------------------------------------------------ R1, R2, R3
    function test_R1_TheNewRouterMustBeBindable() public {
        _prepareNormal();
        PaymentRouter unregistered = _newRouter();
        IMandateManager.SuccessorRequest memory r = _default(NORMAL, address(unregistered));
        // A3 comes first: the registry knows no code hash or version for an unregistered router, so the authorization names zeros
        _fail(r, abi.encodeWithSelector(AuthorizationMismatch.selector));
        r.auth.newRouterCodeHash = bytes32(0);
        r.auth.newRouterVersion = 0;
        _fail(r, abi.encodeWithSelector(RouterNotBindable.selector));
    }

    function test_R2_KindAgainstTheRouters() public {
        _prepareNormal();
        _fail(_default(NORMAL, address(routerA)), abi.encodeWithSelector(WrongKind.selector)); // a migration to the same router
        _fail(_default(EMERGENCY, address(routerA)), abi.encodeWithSelector(WrongKind.selector));
        _fail(_default(REVISION, address(routerB)), abi.encodeWithSelector(WrongKind.selector)); // a revision to another router
        _fail(_default(3, address(routerB)), abi.encodeWithSelector(WrongKind.selector));
    }

    function test_R3_TheModeIsDerivedFromTheRegistry_NotChosenByTheCaller() public {
        _prepareNormal();
        // router A is deprecated for a SECURITY reason: its mode is EMERGENCY, a NORMAL migration is refused
        vm.prank(gov);
        routers.deprecate(address(routerA), address(routerB), 1, 0);
        _fail(_default(NORMAL, address(routerB)), abi.encodeWithSelector(ModeMismatch.selector));
        // the emergency kind is accepted
        _go(_default(EMERGENCY, address(routerB)));
    }

    function test_R3_ADeprecatedStandardRouterIsStillNormalMode() public {
        _prepareNormal();
        vm.prank(gov);
        routers.deprecate(address(routerA), address(routerB), 0, 0);
        _go(_default(NORMAL, address(routerB)));
    }

    function test_R3_ADisabledRouterIsEmergencyMode() public {
        _prepareNormal();
        vm.prank(guardian);
        routers.emergencyDisable(address(routerA));
        _fail(_default(NORMAL, address(routerB)), abi.encodeWithSelector(ModeMismatch.selector));
        _go(_default(EMERGENCY, address(routerB))); // customers can still leave a disabled router
    }

    // ------------------------------------------------------------------------------------------------------------ X1, K1
    function test_X1_ExtensionsMustBeZeroOnBothSides() public {
        _prepareNormal();
        IMandateManager.SuccessorRequest memory r = _default(NORMAL, address(routerB));
        r.newTerms.extensionsHash = keccak256("conversion");
        r.auth.newTermsHash = T.hashStruct(r.newTerms);
        r.auth.termsSnapshotHash = T.snapshotHash(lid, bytes32(0), 0, customer, r.predTerms);
        _fail(r, abi.encodeWithSelector(ExtensionsNotSupported.selector));
    }

    function test_K1_NewPinWellFormedLiveAndWithTheRightVersion() public {
        _prepareNormal();
        T.MandateTerms memory pt = _terms(address(usdc));
        T.AccountPin memory pp = _pin();
        // a malformed new pin
        T.AccountPin memory np = _pin();
        np.pinVersion = 0;
        _fail(_req(pt, pp, pt, np, _auth(Sp(lid, m0, bytes32(0), 0, NORMAL, address(routerB)), pt, pt, np)), abi.encodeWithSelector(AccountPinMalformed.selector));
        // a version that skips: the same pin must keep the predecessor's version, a changed pin goes up by one
        np = _pin();
        np.pinVersion = 2; // the pin did not change otherwise
        _fail(_req(pt, pp, pt, np, _auth(Sp(lid, m0, bytes32(0), 0, NORMAL, address(routerB)), pt, pt, np)), abi.encodeWithSelector(PinVersionMismatch.selector));
        // a changed pin with the right version is accepted
        np = _pin();
        np.signatureMode = 0;
        np.pinVersion = 2;
        _go(_req(pt, pp, pt, np, _auth(Sp(lid, m0, bytes32(0), 0, NORMAL, address(routerB)), pt, pt, np)));
        assertEq(_view(manager.mandateIdOf(lid, 1)).pinVersion, 2);
    }

    function test_K1_ThePinMustHoldOnTheLiveAccount() public {
        _prepareNormal();
        vm.etch(customer, hex"6001"); // the account now has code: the EOA pin does not hold
        T.MandateTerms memory pt = _terms(address(usdc));
        T.AccountPin memory p = _pin();
        // the customer must still be the caller; with code the account still can call here through the cheatcode
        _fail(_req(pt, p, pt, p, _auth(Sp(lid, m0, bytes32(0), 0, NORMAL, address(routerB)), pt, pt, p)), abi.encodeWithSelector(AccountPinMismatch.selector));
    }

    // ------------------------------------------------------------------------------------------------------------ G1
    function test_G1_TheNewRouterNeedsAnAllowanceOfAtLeastThePerPaymentCap() public {
        _lock(address(usdc), address(routerA));
        IMandateManager.SuccessorRequest memory r = _default(NORMAL, address(routerB));
        _fail(r, abi.encodeWithSelector(NewPermissionMissing.selector, address(usdc))); // none
        _grant(customer, usdc, address(routerB), 100e6 - 1);
        _fail(r, abi.encodeWithSelector(NewPermissionMissing.selector, address(usdc))); // one unit short
        _grant(customer, usdc, address(routerB), 100e6);
        _go(r); // exactly the per-payment cap
    }

    function test_G1_AnExpiredAllowanceDoesNotCount() public {
        _lock(address(usdc), address(routerA));
        vm.prank(customer);
        p2.approve(address(usdc), address(routerB), 500e6, uint48(block.timestamp + 10));
        vm.warp(block.timestamp + 11);
        _fail(_default(NORMAL, address(routerB)), abi.encodeWithSelector(NewPermissionMissing.selector, address(usdc)));
    }

    function test_G1_EveryTokenOfTheNewMandateIsChecked() public {
        _lock(address(usdc), address(routerA));
        _grant(customer, usdc, address(routerB), 500e6); // dai has no allowance on router B
        T.MandateTerms memory pt = _terms(address(usdc));
        T.MandateTerms memory nt = _termsOf(_sorted2(address(usdc), address(dai)));
        // the new terms must be contained: two tokens are not (K.3), so use a revision to test G1 on a widening
        T.AccountPin memory p = _pin();
        T.SuccessorAuthorization memory a = _auth(Sp(lid, m0, bytes32(0), 0, REVISION, address(routerA)), pt, nt, p);
        _grant(customer, usdc, address(routerA), 500e6);
        _fail(_req(pt, p, nt, p, a), abi.encodeWithSelector(NewPermissionMissing.selector, address(dai)));
    }

    function test_G1_AnAllowanceThatExpiresThisSecondStillCounts() public {
        _lock(address(usdc), address(routerA));
        vm.prank(customer);
        p2.approve(address(usdc), address(routerB), 500e6, uint48(block.timestamp + 10));
        IMandateManager.SuccessorRequest memory r = _default(NORMAL, address(routerB));
        vm.warp(block.timestamp + 10); // now == expiration: Permit2 treats it as usable (expired only when now is greater)
        _go(r);
    }

    // ------------------------------------------------------------------------------------------------------------ X2
    function test_X2_ExactlyEightExposedTokensAreAllowed() public {
        // seven other tokens and usdc are exposed on router B: the union with the successor's token (usdc) is eight, the bound itself
        for (uint256 i = 0; i < 7; ++i) {
            MockERC20 t = new MockERC20();
            _activate(customer, 700 + i, address(routerB), _terms(address(t)), _pin());
        }
        _activate(customer, 800, address(routerB), _terms(address(usdc)), _pin());
        assertEq(manager.exposedCount(customer, address(routerB)), 8);
        _prepareNormal();
        _go(_default(NORMAL, address(routerB)));
    }

    function test_X2_TheBoundOfEightTokensPerRouterAppliesToTheUnionWithTheNewTokens() public {
        MockERC20[] memory toks = new MockERC20[](8);
        for (uint256 i = 0; i < 8; ++i) {
            toks[i] = new MockERC20();
            _activate(customer, 500 + i, address(routerB), _terms(address(toks[i])), _pin());
        }
        _prepareNormal();
        _fail(_default(NORMAL, address(routerB)), abi.encodeWithSelector(ExposureLimit.selector)); // usdc would be the ninth token on B
    }

    // ------------------------------------------------------------------------------------------------------------ C1, C2
    function _nt() internal view returns (T.MandateTerms memory) {
        return _terms(address(usdc));
    }

    function _contain(T.MandateTerms memory nt) internal {
        _prepareNormal();
        T.MandateTerms memory pt = _terms(address(usdc));
        T.AccountPin memory p = _pin();
        _fail(_req(pt, p, nt, p, _auth(Sp(lid, m0, bytes32(0), 0, NORMAL, address(routerB)), pt, nt, p)), abi.encodeWithSelector(TermsNotContained.selector));
        // the state is unchanged, so the next case starts from the same predecessor
        assertEq(_view(m0).status, 0);
    }

    function test_C1_EachClauseOfContainmentIsEnforced() public {
        T.MandateTerms memory n;
        n = _nt();
        n.expiresAt += 1; // K.1
        _contain(n);
        n = _nt();
        n.recipientPolicy = keccak256("another policy"); // K.2
        _contain(n);
        n = _nt();
        n.tokens[0].perPaymentMax += 1; // K.4
        _contain(n);
        n = _nt();
        n.tokens[0].dayMax = 0; // K.4: no cap is wider than a cap
        _contain(n);
        n = _nt();
        n.fiat.totalMaxMinor += 1; // K.5
        _contain(n);
        n = _nt();
        n.fiat.maxQuoteAge += 1; // K.5
        _contain(n);
        n = _nt();
        n.fiat.boundsVersion = 2; // K.6 (ADR-020)
        _contain(n);
        n = _nt();
        n.maxChargesPerPeriod += 1; // K.7
        _contain(n);
        n = _nt();
        n.minIntervalSeconds -= 1; // K.7
        _contain(n);
        n = _nt();
        n.maxFeeBps += 1; // K.8
        _contain(n);
    }

    function test_C1_ANarrowerSuccessorIsAccepted_AndAMigrationMayDropATokenOrShortenTheExpiry() public {
        _prepareNormal();
        T.MandateTerms memory pt = _terms(address(usdc));
        T.MandateTerms memory nt = _terms(address(usdc));
        nt.tokens[0].perPaymentMax = 50e6;
        nt.expiresAt = pt.expiresAt - 30 days;
        nt.maxFeeBps = 10;
        T.AccountPin memory p = _pin();
        _go(_req(pt, p, nt, p, _auth(Sp(lid, m0, bytes32(0), 0, NORMAL, address(routerB)), pt, nt, p)));
    }

    function test_C1_ANormalMigrationCannotDeclareAWidening() public {
        _prepareNormal();
        IMandateManager.SuccessorRequest memory r = _default(NORMAL, address(routerB));
        r.auth.widenedMask = 1;
        _fail(r, abi.encodeWithSelector(TermsNotContained.selector));
    }

    function test_C2_ARevisionMayWidenWithTheExactMask_AndNothingElse() public {
        T.MandateTerms memory pt = _terms(address(usdc));
        T.MandateTerms memory nt = _terms(address(usdc));
        nt.tokens[0].perPaymentMax = 200e6;
        nt.fiat.perPaymentMaxMinor = 20_000;
        T.AccountPin memory p = _pin();
        T.SuccessorAuthorization memory a = _auth(Sp(lid, m0, bytes32(0), 0, REVISION, address(routerA)), pt, nt, p);
        assertEq(a.widenedMask, 4 | 32, "per-payment cap higher (bit 2) and a fiat cap higher (bit 5)");
        // an understated mask
        a.widenedMask = 4;
        _fail(_req(pt, p, nt, p, a), abi.encodeWithSelector(WidenedMaskMismatch.selector));
        a.widenedMask = 4 | 32 | 1;
        _fail(_req(pt, p, nt, p, a), abi.encodeWithSelector(WidenedMaskMismatch.selector)); // an overstated one
        a.widenedMask = 4 | 32;
        bytes32 m1 = _go(_req(pt, p, nt, p, a));
        assertEq(_view(m1).router, address(routerA));
        assertEq(_view(m0).reason, 3, "superseded by a revision");
    }

    function test_C2_ARevisionCannotChangeTheLineageConstants() public {
        T.MandateTerms memory pt = _terms(address(usdc));
        T.AccountPin memory p = _pin();
        T.MandateTerms memory nt = _terms(address(usdc));
        nt.recipientPolicy = keccak256("another");
        _fail(_req(pt, p, nt, p, _auth(Sp(lid, m0, bytes32(0), 0, REVISION, address(routerA)), pt, nt, p)), abi.encodeWithSelector(LineageConstantsChanged.selector));
        nt = _terms(address(usdc));
        nt.fiat.currency = 978;
        _fail(_req(pt, p, nt, p, _auth(Sp(lid, m0, bytes32(0), 0, REVISION, address(routerA)), pt, nt, p)), abi.encodeWithSelector(LineageConstantsChanged.selector));
        nt = _terms(address(usdc));
        nt.merchantId = keccak256("another merchant");
        _fail(_req(pt, p, nt, p, _auth(Sp(lid, m0, bytes32(0), 0, REVISION, address(routerA)), pt, nt, p)), abi.encodeWithSelector(LineageConstantsChanged.selector));
        nt = _terms(address(usdc));
        nt.anchorStartsAt += 1; // the window grid is a lineage constant (ADR-020 snapshot)
        _fail(_req(pt, p, nt, p, _auth(Sp(lid, m0, bytes32(0), 0, REVISION, address(routerA)), pt, nt, p)), abi.encodeWithSelector(LineageConstantsChanged.selector));
    }

    function test_C2_ABoundsVersionChangeIsAWideningOfARevision() public {
        T.MandateTerms memory pt = _terms(address(usdc));
        T.MandateTerms memory nt = _terms(address(usdc));
        nt.fiat.boundsVersion = 2;
        assertEq(h.widened(nt, pt) & 64, 64, "bit 6: quote age higher or the bounds version changed");
    }

    // ------------------------------------------------------------------------------------------------------------ O1N
    function test_O1N_NoSibling_TheOldAllowanceMustBeUnusable() public {
        _grant(customer, usdc, address(routerB), 500e6);
        _fail(_default(NORMAL, address(routerB)), abi.encodeWithSelector(OldPermissionNotRevoked.selector, address(usdc)));
        _lock(address(usdc), address(routerA));
        _go(_default(NORMAL, address(routerB)));
    }

    function test_O1N_AnExpiredOldAllowanceCountsAsUnusable() public {
        _grant(customer, usdc, address(routerB), 500e6);
        vm.prank(customer);
        p2.approve(address(usdc), address(routerA), 100e6, uint48(block.timestamp + 5));
        vm.warp(block.timestamp + 6);
        _go(_default(NORMAL, address(routerB)));
    }

    function test_O1N_AllowanceZeroedByApproveZeroIsUnusable() public {
        _grant(customer, usdc, address(routerB), 500e6);
        vm.prank(customer);
        p2.approve(address(usdc), address(routerA), 0, uint48(block.timestamp + 1000));
        _go(_default(NORMAL, address(routerB)));
    }

    function test_O1N_WithASibling_TheOldAllowanceMayStayButNotUnlimited() public {
        _activate(customer, 2, address(routerA), _terms(address(usdc)), _pin()); // a sibling on the same token and router
        _grant(customer, usdc, address(routerB), 500e6);
        _go(_default(NORMAL, address(routerB))); // bounded old allowance of 5000e6: accepted
    }

    function test_O1N_WithASibling_AnUnlimitedOldAllowanceIsRefused() public {
        _activate(customer, 2, address(routerA), _terms(address(usdc)), _pin());
        _grant(customer, usdc, address(routerB), 500e6);
        _grant(customer, usdc, address(routerA), type(uint160).max);
        _fail(_default(NORMAL, address(routerB)), abi.encodeWithSelector(ResidualAllowanceUnbounded.selector, address(usdc)));
    }

    function test_O1N_TheLastSiblingToLeaveMustLockTheTokenDown() public {
        (, bytes32 sib) = _activate(customer, 2, address(routerA), _terms(address(usdc)), _pin());
        _grant(customer, usdc, address(routerB), 500e6);
        _go(_default(NORMAL, address(routerB))); // the first migration leaves the sibling: the allowance stays
        // the sibling migrates: now the token has no sibling and the old allowance must go
        T.MandateTerms memory pt = _terms(address(usdc));
        T.AccountPin memory p = _pin();
        bytes32 l2 = manager.lineageIdOf(customer, MERCHANT, SUBSCRIPTION, 2);
        T.SuccessorAuthorization memory a = _auth(Sp(l2, sib, bytes32(0), 0, NORMAL, address(routerB)), pt, pt, p);
        _fail(_req(pt, p, pt, p, a), abi.encodeWithSelector(OldPermissionNotRevoked.selector, address(usdc)));
        _lock(address(usdc), address(routerA));
        _go(_req(pt, p, pt, p, a));
    }

    function test_O1N_BoundaryAtTheExpirySecond() public {
        _grant(customer, usdc, address(routerB), 500e6);
        vm.prank(customer);
        p2.approve(address(usdc), address(routerA), 100e6, uint48(block.timestamp + 5));
        IMandateManager.SuccessorRequest memory r = _default(NORMAL, address(routerB));
        vm.warp(block.timestamp + 5); // the allowance is usable this second: it must be locked down
        _fail(r, abi.encodeWithSelector(OldPermissionNotRevoked.selector, address(usdc)));
        vm.warp(block.timestamp + 1); // one second later it has expired
        _go(r);
    }

    function test_O1E_BoundaryAtTheExpirySecond() public {
        _grant(customer, usdc, address(routerB), 500e6);
        vm.prank(customer);
        p2.approve(address(usdc), address(routerA), 100e6, uint48(block.timestamp + 5));
        IMandateManager.SuccessorRequest memory r = _default(EMERGENCY, address(routerB));
        vm.warp(block.timestamp + 5);
        _fail(r, abi.encodeWithSelector(OldPermissionNotRevoked.selector, address(usdc)));
        vm.warp(block.timestamp + 1);
        _go(r);
    }

    function test_C2_ALaterExpiryIsAWidening() public {
        T.MandateTerms memory pt = _terms(address(usdc));
        T.MandateTerms memory nt = _terms(address(usdc));
        nt.expiresAt = pt.expiresAt + 1 days;
        T.AccountPin memory p = _pin();
        T.SuccessorAuthorization memory a = _auth(Sp(lid, m0, bytes32(0), 0, REVISION, address(routerA)), pt, nt, p);
        assertEq(a.widenedMask, 1, "bit 0: a later expiry");
        a.widenedMask = 0;
        _fail(_req(pt, p, nt, p, a), abi.encodeWithSelector(WidenedMaskMismatch.selector));
        a.widenedMask = 1;
        _go(_req(pt, p, nt, p, a));
    }

    // ------------------------------------------------------------------------------------------------------------ O1E
    function test_O1E_EveryExposedTokenMustBeUnusable_NotOnlyThePredecessorsTokens() public {
        // a sibling uses dai on router A; the lineage under migration uses usdc
        _grant(customer, dai, address(routerA), 500e6);
        _activate(customer, 2, address(routerA), _terms(address(dai)), _pin());
        _grant(customer, usdc, address(routerB), 500e6);
        _lock(address(usdc), address(routerA));
        // the predecessor's own token is locked, the sibling's is not: the emergency migration is refused and names the sibling's token
        _fail(_default(EMERGENCY, address(routerB)), abi.encodeWithSelector(OldPermissionNotRevoked.selector, address(dai)));
        _lock(address(dai), address(routerA));
        _go(_default(EMERGENCY, address(routerB)));
    }

    function test_O1E_IsEnumeratedFromTheIndex_SoACallerCannotOmitASiblingsToken() public {
        MockERC20[] memory toks = new MockERC20[](3);
        for (uint256 i = 0; i < 3; ++i) {
            toks[i] = new MockERC20();
            _fund(customer, toks[i], 1_000e6);
            _grant(customer, toks[i], address(routerA), 500e6);
            _activate(customer, 10 + i, address(routerA), _terms(address(toks[i])), _pin());
        }
        _grant(customer, usdc, address(routerB), 500e6);
        _lock(address(usdc), address(routerA));
        for (uint256 i = 0; i < 2; ++i) {
            _lock(address(toks[i]), address(routerA));
        }
        // the third sibling token is still usable on router A
        _fail(_default(EMERGENCY, address(routerB)), abi.encodeWithSelector(OldPermissionNotRevoked.selector, address(toks[2])));
        _lock(address(toks[2]), address(routerA));
        _go(_default(EMERGENCY, address(routerB)));
    }

    function test_O1E_AnEmergencyMigrationFromANormalRouterIsAllowedAndStricter() public {
        _grant(customer, usdc, address(routerB), 500e6);
        _fail(_default(EMERGENCY, address(routerB)), abi.encodeWithSelector(OldPermissionNotRevoked.selector, address(usdc)));
    }

    function test_O1E_ARegrantedOldAllowanceBlocksTheNextEmergencyActivation() public {
        _grant(customer, usdc, address(routerB), 500e6);
        _lock(address(usdc), address(routerA));
        _grant(customer, usdc, address(routerA), 1); // re-granted after the lockdown
        _fail(_default(EMERGENCY, address(routerB)), abi.encodeWithSelector(OldPermissionNotRevoked.selector, address(usdc)));
    }

    // ------------------------------------------------------------------------------------------------------------ revocation of a successor
    function test_AfterAMigration_TheCustomerCanRevokeTheSuccessor_AndTheLineageTerminates() public {
        _prepareNormal();
        bytes32 m1 = _go(_default(NORMAL, address(routerB)));
        vm.prank(customer);
        manager.revoke(customer, m1);
        (, , , bool terminated, , ) = manager.lineages(lid);
        assertTrue(terminated);
        assertEq(manager.exposedCount(customer, address(routerB)), 0);
    }
}
