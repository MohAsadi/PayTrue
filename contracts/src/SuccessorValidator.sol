// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.24;

import {FastPayTypes as T} from "./generated/FastPayTypes.sol";
import {IMandateManager} from "./interfaces/IMandateManager.sol";
import {IRouterRegistry} from "./interfaces/IRouterRegistry.sol";
import {ISuccessorValidator} from "./interfaces/ISuccessorValidator.sol";
import {IAllowanceTransfer} from "./interfaces/IPermit2.sol";
import {PinLib} from "./lib/PinLib.sol";
import {ContainLib} from "./lib/ContainLib.sol";
import "./Errors.sol";

/// The predicates of `activateSuccessor` that read state and write none (document 12 section 5.3): A3 binding, R1 to R3
/// router, X1 extensions, K1 pin, G1 new permission, X2 exposure, C1 and C2 containment, O1N and O1E old-permission rules. The manager
/// calls `validate` with STATICCALL (it is a view function), so this contract can wrongly accept or reject a successor, but it can never
/// write mandate state; the effects E1 to E6 and the structural lineage checks (L1, A2) stay in the manager. It is stateless: the exposure
/// index it reads is the manager's (msg.sender), and Permit2 and the router registry are immutable.
contract SuccessorValidator is ISuccessorValidator {
    uint8 internal constant NORMAL = 0;
    uint8 internal constant EMERGENCY = 1;
    uint8 internal constant REVISION = 2;

    IRouterRegistry public immutable registry;
    IAllowanceTransfer public immutable permit2;

    constructor(IRouterRegistry registry_, IAllowanceTransfer permit2_) {
        registry = registry_;
        permit2 = permit2_;
    }

    function validate(SuccessorContext calldata x) external view {
        _a3(x);
        _r(x);
        if (x.newTerms.extensionsHash != bytes32(0) || x.predTerms.extensionsHash != bytes32(0)) revert ExtensionsNotSupported(); // X1
        _k1(x);
        _g1(x);
        _x2(x);
        _c(x);
        if (x.auth.kind == NORMAL) _o1n(x);
        else if (x.auth.kind == EMERGENCY) _o1e(x);
    }

    /// A3: the authorization names this customer, lineage, predecessor, terms, router (with its code hash and version), pin and snapshot.
    function _a3(SuccessorContext calldata x) private view {
        T.SuccessorAuthorization calldata a = x.auth;
        if (a.customer != x.customer || a.lineageId != x.lineageId || a.predecessorId != x.predecessorId) revert AuthorizationMismatch();
        if (a.newTermsHash != T.hashStruct(x.newTerms)) revert AuthorizationMismatch();
        if (a.newRouterCodeHash != registry.codeHashOf(a.newRouter) || a.newRouterVersion != registry.versionOf(a.newRouter)) {
            revert AuthorizationMismatch();
        }
        if (T.hashStruct(a.accountPin) != T.hashStruct(x.newPin)) revert AuthorizationMismatch();
        bytes32 snap = T.snapshotHash(x.lineageId, x.predecessorOfPredecessor, x.generation, x.customer, x.predTerms);
        if (a.termsSnapshotHash != snap) revert AuthorizationMismatch();
    }

    /// R1 bindable, R2 kind against the routers, R3 mode (derived from the registry, never chosen by the caller).
    function _r(SuccessorContext calldata x) private view {
        address rNew = x.auth.newRouter;
        uint8 kind = x.auth.kind;
        if (!registry.isBindable(rNew)) revert RouterNotBindable();
        if (kind > REVISION) revert WrongKind();
        if (kind != REVISION && rNew == x.oldRouter) revert WrongKind();
        if (kind == REVISION && rNew != x.oldRouter) revert WrongKind();
        if (kind != REVISION && registry.mode(x.oldRouter) == 1 && kind != EMERGENCY) revert ModeMismatch();
    }

    /// K1: the new pin is well-formed, holds on the live account, and carries the version the successor rule gives.
    function _k1(SuccessorContext calldata x) private view {
        if (!PinLib.wellFormed(x.newPin)) revert AccountPinMalformed();
        if (PinLib.liveCheck(x.customer, x.newPin) != 0) revert AccountPinMismatch();
        if (x.newPin.pinVersion != PinLib.nextVersionSuccessor(x.predPin, x.newPin)) revert PinVersionMismatch();
    }

    /// G1: every token of the new mandate has a Permit2 allowance for the new router of at least its per-payment cap, not expired.
    function _g1(SuccessorContext calldata x) private view {
        address rNew = x.auth.newRouter;
        // loop-bound: TOKENS | newTerms.tokens.length <= MAX_TOKENS_PER_MANDATE | the manager runs requireShape on the new terms before it calls validate
        for (uint256 i = 0; i < x.newTerms.tokens.length; ++i) {
            address t = x.newTerms.tokens[i].token;
            (uint160 amount, uint48 expiration,) = permit2.allowance(x.customer, t, rNew);
            if (amount < x.newTerms.tokens[i].perPaymentMax || block.timestamp > expiration) revert NewPermissionMissing(t);
        }
    }

    /// X2: |Exposed(C, Rnew) united with the new tokens| <= MAX_EXPOSED_TOKENS_PER_ROUTER. One index read per token.
    function _x2(SuccessorContext calldata x) private view {
        if (IMandateManager(msg.sender).exposedUnionCount(x.customer, x.auth.newRouter, x.newTerms.tokens) > T.MAX_EXPOSED_TOKENS_PER_ROUTER) {
            revert ExposureLimit();
        }
    }

    /// C1 (migration): the new terms are contained in the predecessor's and the authorization declares no widening. C2 (revision): the lineage
    /// constants are unchanged and the declared widened mask is exactly the computed one.
    function _c(SuccessorContext calldata x) private pure {
        if (x.auth.kind != REVISION) {
            if (ContainLib.containedMask(x.newTerms, x.predTerms) != 0) revert TermsNotContained();
            if (x.auth.widenedMask != 0) revert TermsNotContained();
        } else {
            if (!ContainLib.lineageConstantsEqual(x.newTerms, x.predTerms)) revert LineageConstantsChanged();
            if (x.auth.widenedMask != ContainLib.widenedMask(x.newTerms, x.predTerms)) revert WidenedMaskMismatch();
        }
    }

    /// O1N (kind NORMAL): for every predecessor token, Sib = live - 1; Sib = 0 requires the old allowance Unusable, Sib > 0 requires it Bounded.
    function _o1n(SuccessorContext calldata x) private view {
        IMandateManager mgr = IMandateManager(msg.sender);
        // loop-bound: TOKENS | predTerms.tokens.length <= MAX_TOKENS_PER_MANDATE | the terms were hash-bound to a stored mandate that requireShape accepted
        for (uint256 i = 0; i < x.predTerms.tokens.length; ++i) {
            address t = x.predTerms.tokens[i].token;
            uint32 liveN = mgr.live(x.customer, x.oldRouter, t);
            (uint160 amount, uint48 expiration,) = permit2.allowance(x.customer, t, x.oldRouter);
            if (liveN - 1 == 0) {
                if (amount > 0 && block.timestamp <= expiration) revert OldPermissionNotRevoked(t);
            } else if (amount >= type(uint160).max) {
                revert ResidualAllowanceUnbounded(t);
            }
        }
    }

    /// O1E (kind EMERGENCY): every token that any live mandate of the customer uses on the old router has an Unusable allowance there.
    function _o1e(SuccessorContext calldata x) private view {
        IMandateManager mgr = IMandateManager(msg.sender);
        uint256 n = mgr.exposedCount(x.customer, x.oldRouter);
        // loop-bound: EXPOSED | exposedCount <= MAX_EXPOSED_TOKENS_PER_ROUTER | the manager's _liveInc refuses a ninth token and predicate X2 refuses the activation
        for (uint256 j = 0; j < n; ++j) {
            address t = mgr.exposedAt(x.customer, x.oldRouter, j);
            (uint160 amount, uint48 expiration,) = permit2.allowance(x.customer, t, x.oldRouter);
            if (amount > 0 && block.timestamp <= expiration) revert OldPermissionNotRevoked(t);
        }
    }
}
