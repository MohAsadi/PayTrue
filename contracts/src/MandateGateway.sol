// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.24;

import {FastPayTypes as T} from "./generated/FastPayTypes.sol";
import {IMandateManager} from "./interfaces/IMandateManager.sol";
import {IRouterRegistry} from "./interfaces/IRouterRegistry.sol";
import {AuthLib} from "./lib/AuthLib.sol";
import "./Errors.sol";

/// The signature front of the MandateManager (document 17 section 5.4): it verifies a customer's EIP-712 signature over one of the typed
/// authorizations, spends the nonce at the manager, and then calls the manager function that the authorization names, as the customer's relay.
/// It holds no state. It can do exactly what the customer can do with the signature it verified: the manager still enforces every invariant of
/// the write (containment, exposure, pin, lineage), and a call that the customer could not make directly is refused there too.
///
/// The signed domain is "FastPay Mandates" with the MANAGER as the verifying contract (types.json), so a signature names the contract that holds
/// the state, not the relay. Signatures that create or widen authority (activation, successor, reduce, resume, pin update) are checked with
/// AUTH under the pin that is STORED at the manager (the pin in the message is only a context for a new lineage); the exits (revoke, pause)
/// are accepted through either signature path whatever the pin says, so a forged exit can only stop charges.
contract MandateGateway {
    IMandateManager public immutable manager;
    IRouterRegistry public immutable registry;

    constructor(IMandateManager manager_, IRouterRegistry registry_) {
        manager = manager_;
        registry = registry_;
    }

    function _digest(bytes32 structHash) internal view returns (bytes32) {
        return T.digest(T.mandatesDomainSeparator(block.chainid, address(manager)), structHash);
    }

    function _fresh(uint64 deadline) internal view {
        if (block.timestamp > deadline) revert AuthorizationExpired();
    }

    /// The signed pin is the one the manager stores for that mandate (never one that the message supplies).
    function _stored(bytes32 mandateId, T.AccountPin calldata pin) internal view {
        if (T.hashStruct(pin) != manager.pinHashOf(mandateId)) revert PinHashMismatch();
    }

    // ------------------------------------------------------------------------------------------------------------ activation
    function activateBySig(T.ActivationTerms calldata a, bytes calldata sig) external returns (bytes32 lineageId, bytes32 mandateId) {
        _fresh(a.deadline);
        if (a.routerCodeHash != registry.codeHashOf(a.router) || a.routerVersion != registry.versionOf(a.router)) revert AuthorizationMismatch();
        AuthLib.authAuthority(a.customer, _digest(T.hashStruct(a)), sig, a.accountPin);
        return manager.activate(a.customer, a.creationNonce, a.router, a.terms, a.accountPin);
    }

    /// The customer's signature over the SuccessorAuthorization, under the pin stored for the predecessor. The manager spends the nonce.
    function activateSuccessorBySig(IMandateManager.SuccessorRequest calldata r, bytes calldata sig) external returns (bytes32 newId) {
        _stored(r.auth.predecessorId, r.predPin);
        AuthLib.authAuthority(r.auth.customer, _digest(T.hashStruct(r.auth)), sig, r.predPin);
        return manager.activateSuccessor(r.auth.customer, r);
    }

    // ------------------------------------------------------------------------------------------------------------ exits
    function revokeBySig(T.RevokeMandate calldata r, bytes calldata sig) external {
        _fresh(r.deadline);
        manager.spendNonce(r.customer, r.nonce);
        AuthLib.authExit(r.customer, _digest(T.hashStruct(r)), sig);
        manager.revoke(r.customer, r.mandateId);
    }

    function pauseBySig(T.PauseMandate calldata p, bytes calldata sig) external {
        _fresh(p.deadline);
        manager.spendNonce(p.customer, p.nonce);
        AuthLib.authExit(p.customer, _digest(T.hashStruct(p)), sig);
        manager.pause(p.customer, p.mandateId);
    }

    /// resume ends a stop, so it needs AUTH of the stored pin.
    function resumeBySig(T.ResumeMandate calldata r, T.AccountPin calldata pin, bytes calldata sig) external {
        _fresh(r.deadline);
        _stored(r.mandateId, pin);
        manager.spendNonce(r.customer, r.nonce);
        AuthLib.authAuthority(r.customer, _digest(T.hashStruct(r)), sig, pin);
        manager.resume(r.customer, r.mandateId);
    }

    // ------------------------------------------------------------------------------------------------------------ reduce and pin updates
    function reduceBySig(
        T.ReduceMandate calldata r,
        T.MandateTerms calldata oldTerms,
        T.MandateTerms calldata newTerms,
        T.AccountPin calldata pin,
        bytes calldata sig
    ) external {
        _fresh(r.deadline);
        if (r.oldTermsHash != T.hashStruct(oldTerms) || r.newTermsHash != T.hashStruct(newTerms)) revert AuthorizationMismatch();
        _stored(r.mandateId, pin);
        manager.spendNonce(r.customer, r.nonce);
        AuthLib.authAuthority(r.customer, _digest(T.hashStruct(r)), sig, pin);
        manager.reduce(r.customer, r.mandateId, oldTerms, newTerms);
    }

    function updateAccountPinBySig(T.AccountPinUpdate calldata u, T.AccountPin calldata curPin, bytes calldata sig) external {
        _fresh(u.deadline);
        _stored(u.mandateId, curPin);
        manager.spendNonce(u.customer, u.nonce);
        AuthLib.authAuthority(u.customer, _digest(T.hashStruct(u)), sig, curPin);
        manager.updateAccountPin(u.customer, u.mandateId, u.newPin);
    }

    /// One account change affects every mandate of the customer: at most MAX_BATCH mandates, each of the signer and each at the pin that signed.
    function updateAccountPinsBySig(T.AccountPinsUpdate calldata u, T.AccountPin calldata curPin, bytes calldata sig) external {
        if (u.mandateIds.length > T.MAX_BATCH) revert BatchTooLarge();
        _fresh(u.deadline);
        manager.spendNonce(u.customer, u.nonce);
        AuthLib.authAuthority(u.customer, _digest(T.hashStruct(u)), sig, curPin);
        // loop-bound: BATCH | mandateIds.length <= MAX_BATCH | the first line reverts BatchTooLarge
        for (uint256 i = 0; i < u.mandateIds.length; ++i) {
            _stored(u.mandateIds[i], curPin); // the pin that signed is the stored pin of every mandate named
            manager.updateAccountPin(u.customer, u.mandateIds[i], u.newPin);
        }
    }

    /// The customer applies the same new pin to several mandates in one transaction (no signature: the caller is the customer).
    function updateAccountPins(bytes32[] calldata mandateIds, T.AccountPin calldata newPin) external {
        if (mandateIds.length > T.MAX_BATCH) revert BatchTooLarge();
        // loop-bound: BATCH | mandateIds.length <= MAX_BATCH | the line above reverts BatchTooLarge
        for (uint256 i = 0; i < mandateIds.length; ++i) {
            manager.updateAccountPin(msg.sender, mandateIds[i], newPin);
        }
    }
}
