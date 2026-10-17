// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {FastPayTypes as T} from "../generated/FastPayTypes.sol";

/// What the other contracts (the router, the gateway, the usage ledger, the validator, the queue, the tests) see of the MandateManager.
interface IMandateManager {
    /// One charge, as the router presents it. `fiatValueMinor` is the value derived from a verified quote (Q1..Q18); `hasFiat` is false when
    /// the router has no quote. The ledger decides whether the mandate needs one.
    struct ChargeInput {
        address token;
        uint256 amount;
        uint256 cycleIndex;
        uint256 feeAmount;
        bool hasFiat;
        uint64 fiatValueMinor;
        bytes32 quoteDigest;
    }

    struct MandateView {
        bytes32 lineageId;
        bytes32 predecessorId;
        bytes32 termsHash;
        bytes32 pinHash;
        address customer;
        address router;
        uint32 generation;
        uint32 pinVersion;
        uint8 status;
        uint8 reason;
        uint8 pause;
        bool retired;
        uint64 expiresAt;
        uint8 nTokens;
        address[3] tokens;
    }

    /// A successor activation request: the predecessor's and the successor's terms and pins, and the authorization that binds them.
    struct SuccessorRequest {
        T.MandateTerms predTerms;
        T.AccountPin predPin;
        T.MandateTerms newTerms;
        T.AccountPin newPin;
        T.SuccessorAuthorization auth;
    }

    // ---- the router
    function consume(bytes32 mandateId, T.MandateTerms calldata terms, T.AccountPin calldata pin, ChargeInput calldata c) external;

    // ---- the customer, directly or through the gateway (the first argument is the customer; the caller is that address or the gateway)
    function activate(address customer, uint256 creationNonce, address router, T.MandateTerms calldata terms, T.AccountPin calldata pin)
        external
        returns (bytes32 lineageId, bytes32 mandateId);
    function activateSuccessor(address customer, SuccessorRequest calldata r) external returns (bytes32 newId);
    function reduce(address customer, bytes32 mandateId, T.MandateTerms calldata oldTerms, T.MandateTerms calldata newTerms) external;
    function updateAccountPin(address customer, bytes32 mandateId, T.AccountPin calldata newPin) external;
    function revoke(address customer, bytes32 mandateId) external;
    function pause(address customer, bytes32 mandateId) external;
    function resume(address customer, bytes32 mandateId) external;

    // ---- the gateway only
    function spendNonce(address customer, uint256 nonce) external;

    // ---- views
    function mandateView(bytes32 mandateId) external view returns (MandateView memory);
    function pinHashOf(bytes32 mandateId) external view returns (bytes32);
    function partiesOf(bytes32 mandateId) external view returns (bytes32 lineageId, address customer);
    function live(address customer, address router, address token) external view returns (uint32);
    function exposedCount(address customer, address router) external view returns (uint256);
    function exposedAt(address customer, address router, uint256 i) external view returns (address);
    function exposedUnionCount(address customer, address router, T.TokenTerms[] calldata tokens) external view returns (uint256);
    function domainSeparator() external view returns (bytes32);
    function usedNonce(address customer, uint256 nonce) external view returns (bool);
}
