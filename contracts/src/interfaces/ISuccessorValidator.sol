// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {FastPayTypes as T} from "../generated/FastPayTypes.sol";

/// The stateless half of `activateSuccessor`: every predicate of document 12 section 5.3 that reads state but writes none (A3, R1 to R3, X1,
/// K1, G1, X2, C1 and C2, O1N and O1E). The manager calls it with STATICCALL (it is a view function), so a validator can wrongly accept or
/// reject but can never write mandate state. The facts about the predecessor are read by the manager from its own storage and bound to the
/// supplied terms and pin by hash before the call. A1 (who may ask) is not here: it is the manager's caller rule and the gateway's signature
/// check.
interface ISuccessorValidator {
    struct SuccessorContext {
        address customer;
        address oldRouter;
        bytes32 lineageId;
        bytes32 predecessorId;
        bytes32 predecessorOfPredecessor;
        uint32 generation;
        T.MandateTerms predTerms;
        T.AccountPin predPin;
        T.MandateTerms newTerms;
        T.AccountPin newPin;
        T.SuccessorAuthorization auth;
    }

    /// Reverts with the error of the failing predicate. `msg.sender` is the manager (its exposure index is the only state read through it).
    function validate(SuccessorContext calldata ctx) external view;
}
