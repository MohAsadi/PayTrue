// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Base} from "./helpers/Base.sol";
import {FastPayTypes as T} from "../src/generated/FastPayTypes.sol";
import {IMandateManager} from "../src/interfaces/IMandateManager.sol";
import "../src/Errors.sol";

/// A smart account whose ERC-1271 check is the ECDSA signature of its owner; `execute` lets it act as a Permit2 user.
contract Mock1271 {
    address public owner;

    constructor(address o) {
        owner = o;
    }

    function isValidSignature(bytes32 h, bytes memory sig) external view returns (bytes4) {
        if (sig.length != 65) return 0xffffffff;
        bytes32 r;
        bytes32 s;
        uint8 v;
        assembly ("memory-safe") {
            r := mload(add(sig, 32))
            s := mload(add(sig, 64))
            v := byte(0, mload(add(sig, 96)))
        }
        return ecrecover(h, v, r, s) == owner ? bytes4(0x1626ba7e) : bytes4(0xffffffff);
    }
}

/// The signature front of the manager (MandateGateway): every typed message, the pin that governs it, the nonces, the deadlines, the domain,
/// and the rule that exits are accepted through either signature path whatever the pin says.
contract GatewayTest is Base {
    uint64 deadline;

    function setUp() public override {
        super.setUp();
        deadline = uint64(block.timestamp + 1 hours);
    }

    function _pinMode(uint8 sm) internal pure returns (T.AccountPin memory p) {
        p = _pin();
        p.signatureMode = sm;
    }

    function _actTerms(uint256 nonce, T.AccountPin memory p) internal view returns (T.ActivationTerms memory a) {
        a.customer = customer;
        a.router = address(routerA);
        a.routerCodeHash = address(routerA).codehash;
        a.routerVersion = 1;
        a.creationNonce = nonce;
        a.terms = _terms(address(usdc));
        a.accountPin = p;
        a.deadline = deadline;
    }

    function _sigAct(T.ActivationTerms memory a, uint256 key) internal view returns (bytes memory) {
        return _sign(key, _mandatesDigest(T.hashStruct(a)));
    }

    function _lid(uint256 n) internal view returns (bytes32) {
        return manager.lineageIdOf(customer, MERCHANT, SUBSCRIPTION, n);
    }

    function _mid(uint256 n) internal view returns (bytes32) {
        return manager.mandateIdOf(_lid(n), 0);
    }

    // ------------------------------------------------------------------------------------------------------------ activation
    function test_ActivateBySig_AnyoneCanRelay() public {
        T.ActivationTerms memory a = _actTerms(1, _pin());
        bytes memory sig = _sigAct(a, customerKey);
        vm.prank(stranger);
        (bytes32 lid, bytes32 mid) = gateway.activateBySig(a, sig);
        assertEq(lid, _lid(1));
        assertEq(_view(mid).customer, customer);
        assertEq(manager.live(customer, address(routerA), address(usdc)), 1);
    }

    function test_ActivateBySig_ReplayIsRefused() public {
        T.ActivationTerms memory a = _actTerms(1, _pin());
        bytes memory sig = _sigAct(a, customerKey);
        gateway.activateBySig(a, sig);
        vm.expectRevert(LineageExists.selector);
        gateway.activateBySig(a, sig);
    }

    function test_ActivateBySig_Expired_AndTheBoundary() public {
        T.ActivationTerms memory a = _actTerms(1, _pin());
        bytes memory sig = _sigAct(a, customerKey);
        vm.warp(deadline); // now == deadline is still valid
        gateway.activateBySig(a, sig);
        T.ActivationTerms memory b = _actTerms(2, _pin());
        bytes memory sig2 = _sigAct(b, customerKey);
        vm.warp(deadline + 1);
        vm.expectRevert(AuthorizationExpired.selector);
        gateway.activateBySig(b, sig2);
    }

    function test_ActivateBySig_WrongSignerOrTamperedMessage() public {
        T.ActivationTerms memory a = _actTerms(1, _pin());
        (, uint256 otherKey) = makeAddrAndKey("not the customer");
        vm.expectRevert(NotCustomer.selector);
        gateway.activateBySig(a, _sigAct(a, otherKey));
        bytes memory sig = _sigAct(a, customerKey);
        a.terms.tokens[0].perPaymentMax += 1; // the relayer widens a cap after the signature
        vm.expectRevert(NotCustomer.selector);
        gateway.activateBySig(a, sig);
    }

    function test_ActivateBySig_TheSignedRouterCodeHashAndVersionMustBeTheRegistryOnes() public {
        T.ActivationTerms memory a = _actTerms(1, _pin());
        a.routerCodeHash = keccak256("another code");
        vm.expectRevert(AuthorizationMismatch.selector);
        gateway.activateBySig(a, _sigAct(a, customerKey));
        a = _actTerms(1, _pin());
        a.routerVersion = 7;
        vm.expectRevert(AuthorizationMismatch.selector);
        gateway.activateBySig(a, _sigAct(a, customerKey));
    }

    function test_ActivateBySig_TheDomainNamesTheManagerNotTheGateway() public {
        T.ActivationTerms memory a = _actTerms(1, _pin());
        bytes memory wrongDomain = _sign(customerKey, T.digest(T.mandatesDomainSeparator(block.chainid, address(gateway)), T.hashStruct(a)));
        vm.expectRevert(NotCustomer.selector);
        gateway.activateBySig(a, wrongDomain);
        bytes memory otherChain = _sign(customerKey, T.digest(T.mandatesDomainSeparator(block.chainid + 1, address(manager)), T.hashStruct(a)));
        vm.expectRevert(NotCustomer.selector);
        gateway.activateBySig(a, otherChain);
    }

    function test_ActivateBySig_DirectOnlyPinAcceptsNoSignature() public {
        T.ActivationTerms memory a = _actTerms(1, _pinMode(0));
        vm.expectRevert(SignatureModeNotPermitted.selector);
        gateway.activateBySig(a, _sigAct(a, customerKey));
    }

    function test_ActivateBySig_Erc1271_OnlyWhileTheAccountStillMatchesThePin() public {
        Mock1271 acct = new Mock1271(customer);
        T.AccountPin memory p = T.AccountPin({
            accountMode: 3,
            accountCodeHash: address(acct).codehash,
            delegate: address(0),
            delegateCodeHash: 0,
            implementationFamily: keccak256("mock-1271"),
            pinVersion: 1,
            signatureMode: 2
        });
        T.ActivationTerms memory a = _actTerms(1, p);
        a.customer = address(acct);
        bytes memory sig = _sign(customerKey, _mandatesDigest(T.hashStruct(a))); // the OWNER signs; the account validates through ERC-1271
        // the account's code changes (an upgrade): the signature is refused with the field that moved
        bytes memory real = address(acct).code;
        vm.etch(address(acct), hex"60016001");
        vm.expectRevert(abi.encodeWithSelector(AccountCodeChanged.selector, address(acct), uint8(1)));
        gateway.activateBySig(a, sig);
        vm.etch(address(acct), real);
        (bytes32 lid, ) = gateway.activateBySig(a, sig);
        assertEq(_view(manager.mandateIdOf(lid, 0)).customer, address(acct));
        // a signature of somebody else does not pass ERC-1271
        T.ActivationTerms memory b = _actTerms(2, p);
        b.customer = address(acct);
        (, uint256 otherKey) = makeAddrAndKey("not the owner");
        vm.expectRevert(NotCustomer.selector);
        gateway.activateBySig(b, _sign(otherKey, _mandatesDigest(T.hashStruct(b))));
    }

    function test_ActivateBySig_AnEcdsaSignatureOfAContractAccountsOwnerIsNotAnEcdsaSignatureOfTheAccount() public {
        Mock1271 acct = new Mock1271(customer);
        T.AccountPin memory p = T.AccountPin({
            accountMode: 3,
            accountCodeHash: address(acct).codehash,
            delegate: address(0),
            delegateCodeHash: 0,
            implementationFamily: keccak256("mock-1271"),
            pinVersion: 1,
            signatureMode: 1 // ECDSA_KEY is not a mode that mode 3 may carry (PIN_WELLFORMED)
        });
        T.ActivationTerms memory a = _actTerms(1, p);
        a.customer = address(acct);
        vm.expectRevert(); // malformed pin at the manager, or no ECDSA match: either way no mandate
        gateway.activateBySig(a, _sign(customerKey, _mandatesDigest(T.hashStruct(a))));
    }

    // ------------------------------------------------------------------------------------------------------------ exits
    function _live(uint256 n, T.AccountPin memory p) internal returns (bytes32 mid) {
        (, mid) = _activate(customer, n, address(routerA), _terms(address(usdc)), p);
    }

    function test_RevokeBySig_AcceptedUnderEveryPinMode_ExitsAreNeverGated() public {
        bytes32 m0 = _live(1, _pinMode(0)); // DIRECT_ONLY
        bytes32 m1 = _live(2, _pinMode(1));
        T.RevokeMandate memory r = T.RevokeMandate(customer, m0, deadline, 1);
        gateway.revokeBySig(r, _sign(customerKey, _mandatesDigest(T.hashStruct(r))));
        assertEq(_view(m0).status, 1);
        r = T.RevokeMandate(customer, m1, deadline, 2);
        vm.prank(stranger);
        gateway.revokeBySig(r, _sign(customerKey, _mandatesDigest(T.hashStruct(r))));
        assertEq(_view(m1).status, 1);
        assertEq(manager.exposedCount(customer, address(routerA)), 0);
    }

    function test_RevokeBySig_NonceIsSingleUse_AndSharedAcrossMessageTypes() public {
        bytes32 m = _live(1, _pin());
        T.PauseMandate memory p = T.PauseMandate(customer, m, deadline, 5);
        gateway.pauseBySig(p, _sign(customerKey, _mandatesDigest(T.hashStruct(p))));
        assertEq(_view(m).pause, 1);
        T.RevokeMandate memory r = T.RevokeMandate(customer, m, deadline, 5); // the same nonce in another message
        bytes memory sig = _sign(customerKey, _mandatesDigest(T.hashStruct(r)));
        vm.expectRevert(AuthorizationReplayed.selector);
        gateway.revokeBySig(r, sig);
        r.nonce = 6;
        gateway.revokeBySig(r, _sign(customerKey, _mandatesDigest(T.hashStruct(r))));
    }

    function test_RevokeBySig_Expired_AndForAnotherCustomersMandate() public {
        bytes32 m = _live(1, _pin());
        T.RevokeMandate memory r = T.RevokeMandate(customer, m, uint64(block.timestamp - 1), 1);
        bytes memory sig = _sign(customerKey, _mandatesDigest(T.hashStruct(r)));
        vm.expectRevert(AuthorizationExpired.selector);
        gateway.revokeBySig(r, sig);
        // another customer signs a revoke that names this mandate: their own signature is valid, the mandate is not theirs
        (address other, uint256 otherKey) = makeAddrAndKey("other customer");
        T.RevokeMandate memory r2 = T.RevokeMandate(other, m, deadline, 1);
        bytes memory sig2 = _sign(otherKey, _mandatesDigest(T.hashStruct(r2)));
        vm.expectRevert(NotCustomer.selector);
        gateway.revokeBySig(r2, sig2);
        assertEq(_view(m).status, 0);
    }

    function test_RevokeBySig_AForgedSignatureFails() public {
        bytes32 m = _live(1, _pin());
        T.RevokeMandate memory r = T.RevokeMandate(customer, m, deadline, 1);
        (, uint256 otherKey) = makeAddrAndKey("forger");
        bytes memory sig = _sign(otherKey, _mandatesDigest(T.hashStruct(r)));
        vm.expectRevert(NotCustomer.selector);
        gateway.revokeBySig(r, sig);
    }

    function test_PauseBySig_ThenResumeNeedsTheStoredPin() public {
        bytes32 m = _live(1, _pinMode(0)); // DIRECT_ONLY: a signature may stop but never restart
        T.PauseMandate memory p = T.PauseMandate(customer, m, deadline, 1);
        gateway.pauseBySig(p, _sign(customerKey, _mandatesDigest(T.hashStruct(p))));
        assertEq(_view(m).pause, 1);
        T.ResumeMandate memory r = T.ResumeMandate(customer, m, deadline, 2);
        bytes memory sig = _sign(customerKey, _mandatesDigest(T.hashStruct(r)));
        vm.expectRevert(SignatureModeNotPermitted.selector);
        gateway.resumeBySig(r, _pinMode(0), sig);
        vm.prank(customer);
        manager.resume(customer, m); // the customer's own transaction always works
        assertEq(_view(m).pause, 0);
    }

    function test_ResumeBySig_UnderEcdsaMode_AndTheSuppliedPinMustBeTheStoredOne() public {
        bytes32 m = _live(1, _pin());
        vm.prank(customer);
        manager.pause(customer, m);
        T.ResumeMandate memory r = T.ResumeMandate(customer, m, deadline, 1);
        bytes memory sig = _sign(customerKey, _mandatesDigest(T.hashStruct(r)));
        vm.expectRevert(PinHashMismatch.selector);
        gateway.resumeBySig(r, _pinMode(2), sig); // a more permissive pin than the stored one is not the stored pin
        gateway.resumeBySig(r, _pin(), sig);
        assertEq(_view(m).pause, 0);
    }

    // ------------------------------------------------------------------------------------------------------------ reduce
    function test_ReduceBySig() public {
        bytes32 m = _live(1, _pin());
        T.MandateTerms memory old = _terms(address(usdc));
        T.MandateTerms memory n = _terms(address(usdc));
        n.tokens[0].perPaymentMax = 10e6;
        T.ReduceMandate memory r = T.ReduceMandate(customer, m, T.hashStruct(old), T.hashStruct(n), deadline, 1);
        bytes memory sig = _sign(customerKey, _mandatesDigest(T.hashStruct(r)));
        // the relayer swaps the new terms for wider ones: the signed hash no longer matches
        T.MandateTerms memory wider = _terms(address(usdc));
        wider.tokens[0].perPaymentMax = 99e6;
        vm.expectRevert(AuthorizationMismatch.selector);
        gateway.reduceBySig(r, old, wider, _pin(), sig);
        gateway.reduceBySig(r, old, n, _pin(), sig);
        assertEq(_view(m).termsHash, T.hashStruct(n));
        vm.expectRevert(AuthorizationReplayed.selector);
        gateway.reduceBySig(r, old, n, _pin(), sig);
    }

    function test_ReduceBySig_AWideningThroughTheGatewayStillFailsAtTheManager() public {
        bytes32 m = _live(1, _pin());
        T.MandateTerms memory old = _terms(address(usdc));
        T.MandateTerms memory n = _terms(address(usdc));
        n.tokens[0].perPaymentMax = 101e6;
        T.ReduceMandate memory r = T.ReduceMandate(customer, m, T.hashStruct(old), T.hashStruct(n), deadline, 1);
        bytes memory sig = _sign(customerKey, _mandatesDigest(T.hashStruct(r)));
        vm.expectRevert(TermsNotContained.selector);
        gateway.reduceBySig(r, old, n, _pin(), sig);
    }

    // ------------------------------------------------------------------------------------------------------------ pin updates
    function test_UpdateAccountPinBySig_ThenTheOldPinSignsNothingMore() public {
        bytes32 m = _live(1, _pin());
        T.AccountPin memory np = _pin();
        np.pinVersion = 2;
        np.signatureMode = 0;
        T.AccountPinUpdate memory u = T.AccountPinUpdate(customer, m, np, deadline, 1);
        bytes memory sig = _sign(customerKey, _mandatesDigest(T.hashStruct(u)));
        gateway.updateAccountPinBySig(u, _pin(), sig);
        assertEq(_view(m).pinVersion, 2);
        // the stored pin is now DIRECT_ONLY: a signed pin update that presents the OLD pin is not the stored pin
        T.AccountPinUpdate memory u2 = T.AccountPinUpdate(customer, m, np, deadline, 2);
        np.pinVersion = 3;
        u2.newPin = np;
        vm.expectRevert(PinHashMismatch.selector);
        gateway.updateAccountPinBySig(u2, _pin(), _sign(customerKey, _mandatesDigest(T.hashStruct(u2))));
        // and presenting the stored pin fails because DIRECT_ONLY accepts no signature
        T.AccountPin memory stored = _pin();
        stored.pinVersion = 2;
        stored.signatureMode = 0;
        vm.expectRevert(SignatureModeNotPermitted.selector);
        gateway.updateAccountPinBySig(u2, stored, _sign(customerKey, _mandatesDigest(T.hashStruct(u2))));
    }

    function test_UpdateAccountPinsBySig_BatchAndItsBound() public {
        bytes32[] memory ids = new bytes32[](3);
        for (uint256 i = 0; i < 3; ++i) {
            ids[i] = _live(i + 1, _pin());
        }
        T.AccountPin memory np = _pin();
        np.pinVersion = 2;
        T.AccountPinsUpdate memory u = T.AccountPinsUpdate(customer, ids, np, deadline, 1);
        gateway.updateAccountPinsBySig(u, _pin(), _sign(customerKey, _mandatesDigest(T.hashStruct(u))));
        for (uint256 i = 0; i < 3; ++i) {
            assertEq(_view(ids[i]).pinVersion, 2);
            assertEq(_view(ids[i]).pinHash, T.hashStruct(np));
        }
    }

    function test_UpdateAccountPins_OverTheBoundIsRefused() public {
        bytes32[] memory ids = new bytes32[](T.MAX_BATCH + 1);
        T.AccountPin memory np = _pin();
        np.pinVersion = 2;
        vm.prank(customer);
        vm.expectRevert(BatchTooLarge.selector);
        gateway.updateAccountPins(ids, np);
        T.AccountPinsUpdate memory u = T.AccountPinsUpdate(customer, ids, np, deadline, 1);
        vm.expectRevert(BatchTooLarge.selector);
        gateway.updateAccountPinsBySig(u, _pin(), "");
    }

    function test_UpdateAccountPins_CustomerBatch_AndOnlyOwnMandates() public {
        bytes32 mine = _live(1, _pin());
        T.AccountPin memory np = _pin();
        np.pinVersion = 2;
        bytes32[] memory ids = new bytes32[](1);
        ids[0] = mine;
        vm.prank(customer);
        gateway.updateAccountPins(ids, np);
        assertEq(_view(mine).pinVersion, 2);
        np.pinVersion = 3;
        vm.prank(stranger);
        vm.expectRevert(NotCustomer.selector);
        gateway.updateAccountPins(ids, np);
    }

    function test_UpdateAccountPinsBySig_ABatchThatIncludesAMandateAtAnotherPinFailsWhole() public {
        bytes32 a = _live(1, _pin());
        bytes32 b = _live(2, _pin());
        T.AccountPin memory p2_ = _pin();
        p2_.pinVersion = 2;
        vm.prank(customer);
        manager.updateAccountPin(customer, b, p2_); // b is at version 2, a at version 1
        bytes32[] memory ids = new bytes32[](2);
        ids[0] = a;
        ids[1] = b;
        T.AccountPin memory np = _pin();
        np.pinVersion = 2;
        T.AccountPinsUpdate memory u = T.AccountPinsUpdate(customer, ids, np, deadline, 1);
        vm.expectRevert(PinHashMismatch.selector); // b does not store the pin that signed
        gateway.updateAccountPinsBySig(u, _pin(), _sign(customerKey, _mandatesDigest(T.hashStruct(u))));
        assertEq(_view(a).pinVersion, 1, "nothing was applied");
    }

    // ------------------------------------------------------------------------------------------------------------ the gateway is not a free relay
    function test_TheGatewayCannotBeUsedWithoutASignature() public {
        bytes32 m = _live(1, _pin());
        T.RevokeMandate memory r = T.RevokeMandate(customer, m, deadline, 1);
        vm.prank(stranger);
        vm.expectRevert(NotCustomer.selector);
        gateway.revokeBySig(r, hex"00");
        vm.prank(stranger);
        vm.expectRevert(NotCustomer.selector);
        gateway.revokeBySig(r, new bytes(65));
        assertEq(_view(m).status, 0);
    }
}
