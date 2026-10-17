// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.24;

import {FastPayTypes as T} from "./generated/FastPayTypes.sol";
import {IMandateManager} from "./interfaces/IMandateManager.sol";
import {IRouterRegistry} from "./interfaces/IRouterRegistry.sol";
import {ISuccessorValidator} from "./interfaces/ISuccessorValidator.sol";
import {PinLib} from "./lib/PinLib.sol";
import {ContainLib} from "./lib/ContainLib.sol";
import {UsageLedger} from "./UsageLedger.sol";
import "./Errors.sol";

/// MandateManager (document 06 section 4, documents 11, 12 and 17): the mandates and lineages, the account pin, activation, successor
/// activation, the three pause bits, revoke, retire, reduce, and the guards of `consume`. It is the ONLY contract that writes mandate state, so
/// every cross-contract invariant is enforced here, at the moment of the write:
///   * a lineage has at most one active mandate, and a successor continues the lineage constants of its predecessor;
///   * the exposure index live(C, R, t) and its list change only together with the mandates that they count;
///   * an authorization nonce is spent in the same transaction that uses it;
///   * `consume` runs only for the router the mandate is bound to, and moves no tokens.
///
/// The manager is one of four contracts that share the work (its runtime would not fit EIP-170 alone). There is no delegatecall and no generic
/// call between them: each link is a typed call to an address fixed at deployment.
///   * UsageLedger: the usage counters, windows and cadence. Only this manager can write there; `consume` calls it after its own guards.
///   * SuccessorValidator: the predicates of `activateSuccessor` that read state and write none, called with STATICCALL.
///   * MandateGateway: verifies the customer's EIP-712 signatures and then calls the functions below as the customer's relay. It can do
///     exactly what the customer can do with the signature that it verified, and nothing else (it holds no state but the immutable addresses).
/// Who may call what: a function that takes `customer` as its first argument accepts the customer or the gateway as the caller; consume
/// accepts the router of the mandate; the pause authority sets the risk and delegation bits; retire is permissionless. Exits (revoke,
/// pause) never depend on the gateway or the validator: the customer calls them directly.
///
/// The terms of a mandate are not stored: only their hash and the data that the exits need (expiry, tokens). Every function that needs the
/// terms takes them as calldata and compares their hash with the stored one; the events carry the full terms. This keeps a successor at a
/// handful of storage slots instead of a record of about twenty-five (finding F-12).
contract MandateManager is IMandateManager {
    uint8 public constant NORMAL = 0;
    uint8 public constant EMERGENCY = 1;
    uint8 public constant REVISION = 2;

    uint8 public constant MS_ACTIVE = 0;
    uint8 public constant MS_REVOKED = 1;
    uint8 public constant RV_NONE = 0;
    uint8 public constant RV_CUSTOMER = 1;
    uint8 public constant RV_SUPERSEDED_MIGRATION = 2;
    uint8 public constant RV_SUPERSEDED_REVISION = 3;

    uint8 public constant PAUSE_CUSTOMER = 1;
    uint8 public constant PAUSE_RISK = 2;
    uint8 public constant PAUSE_DELEGATION = 4;

    uint256 public constant MAX_EXPOSED_TOKENS_PER_ROUTER = T.MAX_EXPOSED_TOKENS_PER_ROUTER; // PC-18, proposal 8 (eip712/types.json)

    struct Mandate {
        bytes32 lineageId;
        bytes32 predecessorId;
        bytes32 termsHash;
        bytes32 pinHash;
        address customer;
        uint32 generation;
        uint32 pinVersion;
        uint8 status;
        uint8 reason;
        uint8 pause;
        bool retired;
        address router;
        uint64 expiresAt;
        uint8 nTokens;
        address[3] tokens;
    }

    struct Lineage {
        address customer;
        uint32 generation;
        uint32 pinVersion;
        bool terminated;
        bool exists;
        bytes32 activeMandateId;
    }

    IRouterRegistry public immutable registry;
    ISuccessorValidator public immutable validator;
    UsageLedger public immutable ledger;
    address public immutable gateway;
    /// The migration queue: it may call `activateSuccessor` (and only that) for the customer who opened the plan that the entry belongs to.
    address public immutable queue;
    /// The risk service and the guardian act through this address: it can set and clear the risk and the delegation pause bits, nothing else.
    address public immutable pauseAuthority;

    mapping(bytes32 => Mandate) internal mandates;
    mapping(bytes32 => Lineage) public lineages;
    mapping(address => mapping(uint256 => bool)) public usedNonce;

    mapping(address => mapping(address => mapping(address => uint32))) public live; // live(C, R, t)
    mapping(address => mapping(address => address[])) internal exposedList; // Exposed(C, R)
    mapping(address => mapping(address => mapping(address => uint256))) public exposedPos; // 1-based position in exposedList; 0 = absent

    event MandateActivated(
        bytes32 indexed lineageId, bytes32 indexed mandateId, address indexed customer, address router, bytes32 termsHash, bytes32 pinHash, T.MandateTerms terms, T.AccountPin pin
    );
    event MandateSuperseded(
        bytes32 indexed lineageId, bytes32 indexed predecessorId, bytes32 newId, uint8 kind, address newRouter, bytes32 termsHash, bytes32 pinHash, T.MandateTerms terms, T.AccountPin pin
    );
    event MandateRevoked(bytes32 indexed lineageId, bytes32 indexed mandateId);
    event MandateRetired(bytes32 indexed mandateId);
    event MandateReduced(bytes32 indexed mandateId, bytes32 oldTermsHash, bytes32 newTermsHash, T.MandateTerms terms);
    event MandatePauseChanged(bytes32 indexed mandateId, uint8 pause);
    event AccountPinUpdated(bytes32 indexed mandateId, bytes32 oldPinHash, uint32 pinVersion, T.AccountPin pin);

    constructor(
        IRouterRegistry registry_,
        ISuccessorValidator validator_,
        UsageLedger ledger_,
        address gateway_,
        address queue_,
        address pauseAuthority_
    ) {
        registry = registry_;
        validator = validator_;
        ledger = ledger_;
        gateway = gateway_;
        queue = queue_;
        pauseAuthority = pauseAuthority_;
    }

    // ------------------------------------------------------------------------------------------------------------ identifiers and digests
    function domainSeparator() public view returns (bytes32) {
        return T.mandatesDomainSeparator(block.chainid, address(this));
    }

    function lineageIdOf(address customer, bytes32 merchantId, bytes32 subscriptionRef, uint256 creationNonce) public view returns (bytes32) {
        return keccak256(abi.encode(T.LINEAGE_TAG, block.chainid, address(this), customer, merchantId, subscriptionRef, creationNonce));
    }

    function mandateIdOf(bytes32 lineageId, uint256 generation) public pure returns (bytes32) {
        return keccak256(abi.encode(T.MANDATE_TAG, lineageId, generation));
    }

    function _mandate(bytes32 id) internal view returns (Mandate storage m) {
        m = mandates[id];
        if (m.lineageId == bytes32(0)) revert UnknownMandate();
    }

    /// The caller is the customer or the gateway relaying the customer's signature.
    function _as(address customer) internal view {
        if (msg.sender != customer && msg.sender != gateway) revert NotCustomer();
    }

    /// The mandate belongs to `customer`, and the caller may act as that customer.
    function _own(address customer, bytes32 mandateId) internal view returns (Mandate storage m) {
        _as(customer);
        m = _mandate(mandateId);
        if (m.customer != customer) revert NotCustomer();
    }

    function _terminal(Mandate storage m) internal view returns (bool) {
        return m.status != MS_ACTIVE || block.timestamp >= m.expiresAt;
    }

    /// A signed authorization is single-use: the gateway spends its nonce here before it calls the function that it authorizes.
    function spendNonce(address customer, uint256 nonce) external {
        if (msg.sender != gateway) revert NotGateway();
        if (usedNonce[customer][nonce]) revert AuthorizationReplayed();
        usedNonce[customer][nonce] = true;
    }

    // ------------------------------------------------------------------------------------------------------------ exposure index (O(1))
    function _liveInc(address c, address r, address t) internal {
        uint32 n = live[c][r][t] + 1;
        live[c][r][t] = n;
        if (n == 1) {
            address[] storage lst = exposedList[c][r];
            if (lst.length >= MAX_EXPOSED_TOKENS_PER_ROUTER) revert ExposureLimit(); // the bound holds whatever a predicate said
            lst.push(t);
            exposedPos[c][r][t] = lst.length;
        }
    }

    function _liveDec(address c, address r, address t) internal {
        uint32 n = live[c][r][t] - 1;
        live[c][r][t] = n;
        if (n == 0) {
            address[] storage lst = exposedList[c][r];
            uint256 pos = exposedPos[c][r][t];
            uint256 len = lst.length;
            if (pos != len) {
                address moved = lst[len - 1];
                lst[pos - 1] = moved; // swap and pop
                exposedPos[c][r][moved] = pos;
            }
            lst.pop();
            exposedPos[c][r][t] = 0;
        }
    }

    /// |Exposed(C, R) united with the tokens|: one index read per token.
    function exposedUnionCount(address customer, address router, T.TokenTerms[] calldata tokens) public view returns (uint256 n) {
        n = exposedList[customer][router].length;
        // loop-bound: TOKENS | tokens.length <= MAX_TOKENS_PER_MANDATE | every caller passes terms that requireShape has accepted
        for (uint256 i = 0; i < tokens.length; ++i) {
            if (exposedPos[customer][router][tokens[i].token] == 0) n += 1;
        }
    }

    function exposedCount(address customer, address router) external view returns (uint256) {
        return exposedList[customer][router].length;
    }

    function exposedAt(address customer, address router, uint256 i) external view returns (address) {
        return exposedList[customer][router][i];
    }

    // ------------------------------------------------------------------------------------------------------------ activation
    /// A new lineage with its first mandate. The caller is the customer, or the gateway with the customer's signature over ActivationTerms.
    function activate(address customer, uint256 creationNonce, address router, T.MandateTerms calldata terms, T.AccountPin calldata pin)
        external
        returns (bytes32 lid, bytes32 mid)
    {
        _as(customer);
        ContainLib.requireShape(terms);
        if (!registry.isBindable(router)) revert RouterNotBindable();
        if (terms.extensionsHash != bytes32(0)) revert ExtensionsNotSupported();
        if (!PinLib.wellFormed(pin)) revert AccountPinMalformed();
        if (PinLib.liveCheck(customer, pin) != 0) revert AccountPinMismatch();
        if (pin.pinVersion != 1) revert PinVersionMismatch();
        if (exposedUnionCount(customer, router, terms.tokens) > MAX_EXPOSED_TOKENS_PER_ROUTER) revert ExposureLimit();
        lid = lineageIdOf(customer, terms.merchantId, terms.subscriptionRef, creationNonce);
        mid = mandateIdOf(lid, 0);
        Lineage storage l = lineages[lid];
        if (l.exists) revert LineageExists();
        l.customer = customer;
        l.pinVersion = pin.pinVersion;
        l.exists = true;
        l.activeMandateId = mid;
        Mandate storage m = mandates[mid];
        _head(m, lid, bytes32(0), 0, customer, router);
        _body(m, terms, pin);
        _incTokens(customer, router, terms.tokens);
        emit MandateActivated(lid, mid, customer, router, m.termsHash, m.pinHash, terms, pin);
    }

    /// The identity part of a new mandate record.
    function _head(Mandate storage m, bytes32 lid, bytes32 predecessorId, uint32 generation, address customer, address router) internal {
        m.lineageId = lid;
        m.predecessorId = predecessorId;
        m.customer = customer;
        m.generation = generation;
        m.router = router;
    }

    /// The terms and pin part: the hashes, the expiry and the token list (everything else of the terms lives in the hash and the events).
    function _body(Mandate storage m, T.MandateTerms calldata terms, T.AccountPin calldata pin) internal {
        m.termsHash = T.hashStruct(terms);
        m.pinHash = T.hashStruct(pin);
        m.pinVersion = pin.pinVersion;
        m.expiresAt = terms.expiresAt;
        _setTokens(m, terms.tokens);
    }

    function _setTokens(Mandate storage m, T.TokenTerms[] calldata tokens) internal {
        uint256 n = tokens.length;
        m.nTokens = uint8(n);
        // loop-bound: TOKENS | tokens.length <= MAX_TOKENS_PER_MANDATE | requireShape ran on the terms that these tokens belong to
        for (uint256 i = 0; i < n; ++i) {
            m.tokens[i] = tokens[i].token;
        }
        // loop-bound: TOKENS | the slots n .. 2 of a three-slot array | the array has MAX_TOKENS_PER_MANDATE slots
        for (uint256 i = n; i < 3; ++i) {
            m.tokens[i] = address(0);
        }
    }

    function _incTokens(address customer, address router, T.TokenTerms[] calldata tokens) internal {
        // loop-bound: TOKENS | tokens.length <= MAX_TOKENS_PER_MANDATE | requireShape ran on these terms
        for (uint256 i = 0; i < tokens.length; ++i) {
            _liveInc(customer, router, tokens[i].token);
        }
    }

    function _decStored(Mandate storage m) internal {
        // loop-bound: TOKENS | nTokens <= MAX_TOKENS_PER_MANDATE | nTokens was set from requireShape'd terms
        for (uint256 i = 0; i < m.nTokens; ++i) {
            _liveDec(m.customer, m.router, m.tokens[i]);
        }
    }

    // ------------------------------------------------------------------------------------------------------------ consume (a charge)
    /// G1 (the mandate may be charged now, by this router, under the stored pin and terms), then the ledger applies G2 to G5, G9, the fee bound
    /// and the cadence and writes the counters. The router, not this contract, pulls the tokens afterwards (it is the Permit2 spender), so
    /// the effects are written before any token moves, and a failed pull reverts them (finding F-16).
    function consume(bytes32 mandateId, T.MandateTerms calldata terms, T.AccountPin calldata pin, ChargeInput calldata c) external {
        Mandate storage m = _mandate(mandateId);
        Lineage storage l = lineages[m.lineageId];
        if (m.status != MS_ACTIVE || l.activeMandateId != mandateId || l.terminated || m.pause != 0 || m.retired) revert MandateNotConsumable();
        if (block.timestamp >= m.expiresAt || block.timestamp < terms.anchorStartsAt) revert MandateNotConsumable();
        if (msg.sender != m.router) revert WrongRouter();
        if (!registry.isChargeable(m.router)) revert RouterNotChargeable();
        if (T.hashStruct(pin) != m.pinHash) revert PinHashMismatch();
        uint8 field = PinLib.liveCheck(m.customer, pin);
        if (field != 0) revert AccountCodeChanged(m.customer, field);
        if (T.hashStruct(terms) != m.termsHash) revert TermsHashMismatch();
        if (terms.extensionsHash != bytes32(0)) revert ExtensionsNotSupported();
        ledger.charge(mandateId, m.lineageId, terms, c);
    }

    // ------------------------------------------------------------------------------------------------------------ exits (never gated)
    function revoke(address customer, bytes32 mandateId) external {
        Mandate storage m = _own(customer, mandateId);
        if (m.status != MS_ACTIVE) revert MandateNotActive();
        if (!m.retired) _decStored(m);
        m.status = MS_REVOKED;
        m.reason = RV_CUSTOMER;
        Lineage storage l = lineages[m.lineageId];
        if (l.activeMandateId == mandateId) l.terminated = true;
        emit MandateRevoked(m.lineageId, mandateId);
    }

    /// Permissionless: EXPIRED and EXHAUSTED are derived states that no transaction would record, so the exposure index needs a call that
    /// releases a mandate that can no longer be charged. Only an expired mandate can be retired.
    function retire(bytes32 mandateId) external {
        Mandate storage m = _mandate(mandateId);
        if (m.status != MS_ACTIVE || m.retired || block.timestamp < m.expiresAt) revert NotRetirable();
        _decStored(m);
        m.retired = true;
        emit MandateRetired(mandateId);
    }

    function pause(address customer, bytes32 mandateId) external {
        Mandate storage m = _own(customer, mandateId);
        _setPause(m, mandateId, m.pause | PAUSE_CUSTOMER);
    }

    /// resume creates no authority the mandate did not have, but it ends a stop: through the gateway it needs the AUTH of the stored pin.
    function resume(address customer, bytes32 mandateId) external {
        Mandate storage m = _own(customer, mandateId);
        _setPause(m, mandateId, m.pause & ~PAUSE_CUSTOMER);
    }

    /// The risk service and the guardian: stop-only bits (risk, delegation). They can set and clear them; they can do nothing else.
    function setPauseBit(bytes32 mandateId, uint8 bit, bool on) external {
        if (msg.sender != pauseAuthority) revert NotPauseAuthority();
        if (bit != PAUSE_RISK && bit != PAUSE_DELEGATION) revert NotPauseAuthority();
        Mandate storage m = _mandate(mandateId);
        _setPause(m, mandateId, on ? (m.pause | bit) : (m.pause & ~bit));
    }

    function _setPause(Mandate storage m, bytes32 mandateId, uint8 value) internal {
        if (m.status != MS_ACTIVE) revert MandateNotActive();
        m.pause = value;
        emit MandatePauseChanged(mandateId, value);
    }

    // ------------------------------------------------------------------------------------------------------------ reduce (narrowing only)
    function reduce(address customer, bytes32 mandateId, T.MandateTerms calldata oldTerms, T.MandateTerms calldata newTerms) external {
        Mandate storage m = _own(customer, mandateId);
        if (_terminal(m) || m.retired) revert MandateNotActive();
        if (T.hashStruct(oldTerms) != m.termsHash) revert TermsHashMismatch();
        ContainLib.requireShape(newTerms);
        if (ContainLib.containedMask(newTerms, oldTerms) != 0) revert TermsNotContained();
        if (newTerms.expiresAt <= block.timestamp) revert TermsNotContained();
        // the tokens that the reduction drops leave the exposure index; the tokens it keeps stay as they are (K.3: a subset)
        // loop-bound: TOKENS | nTokens <= MAX_TOKENS_PER_MANDATE | nTokens was set from requireShape'd terms
        for (uint256 i = 0; i < m.nTokens; ++i) {
            (, bool kept) = ContainLib.indexOf(newTerms, m.tokens[i]);
            if (!kept) _liveDec(m.customer, m.router, m.tokens[i]);
        }
        bytes32 newHash = T.hashStruct(newTerms);
        _setTokens(m, newTerms.tokens);
        m.expiresAt = newTerms.expiresAt;
        emit MandateReduced(mandateId, m.termsHash, newHash, newTerms);
        m.termsHash = newHash;
    }

    // ------------------------------------------------------------------------------------------------------------ account pin updates
    /// updateAccountPin: only `accountPinHash` and `pinVersion` change (I-ACCT-NOWIDEN). One account change affects every mandate of the
    /// customer; the gateway applies it to at most MAX_BATCH mandates, one call each.
    function updateAccountPin(address customer, bytes32 mandateId, T.AccountPin calldata newPin) external {
        Mandate storage m = _own(customer, mandateId);
        if (_terminal(m)) revert MandateNotActive();
        if (!PinLib.wellFormed(newPin)) revert AccountPinMalformed();
        if (PinLib.liveCheck(customer, newPin) != 0) revert AccountPinMismatch();
        if (newPin.pinVersion != m.pinVersion + 1) revert PinVersionMismatch();
        bytes32 old = m.pinHash;
        m.pinHash = T.hashStruct(newPin);
        m.pinVersion = newPin.pinVersion;
        lineages[m.lineageId].pinVersion = newPin.pinVersion;
        emit AccountPinUpdated(mandateId, old, newPin.pinVersion, newPin);
    }

    // ------------------------------------------------------------------------------------------------------------ successor activation
    /// activateSuccessor of document 12 section 5.3. The caller (A1) is the customer, the gateway relaying the customer's signature over
    /// SuccessorAuthorization, or the migration queue executing a plan that the customer opened. The structural checks and every write are here; the predicates that only read state are in the
    /// validator, called with STATICCALL.
    function activateSuccessor(address customer, SuccessorRequest calldata r) external returns (bytes32 newId) {
        if (msg.sender != queue) _as(customer);
        Mandate storage p = _mandate(r.auth.predecessorId);
        if (p.customer != customer) revert NotCustomer();
        Lineage storage l = lineages[p.lineageId];
        if (l.activeMandateId != r.auth.predecessorId || l.terminated || _terminal(p) || p.retired) revert WrongPredecessor(); // L1
        if (block.timestamp > r.auth.deadline) revert AuthorizationExpired(); // A2
        if (usedNonce[customer][r.auth.nonce]) revert AuthorizationReplayed();
        if (T.hashStruct(r.predTerms) != p.termsHash) revert TermsHashMismatch();
        if (T.hashStruct(r.predPin) != p.pinHash) revert PinHashMismatch();
        ContainLib.requireShape(r.newTerms);
        validator.validate(_context(p, r));
        return _applySuccessor(p, l, r);
    }

    function _context(Mandate storage p, SuccessorRequest calldata r) internal view returns (ISuccessorValidator.SuccessorContext memory ctx) {
        ctx.customer = p.customer;
        ctx.oldRouter = p.router;
        ctx.lineageId = p.lineageId;
        ctx.predecessorId = r.auth.predecessorId;
        ctx.predecessorOfPredecessor = p.predecessorId;
        ctx.generation = p.generation;
        ctx.predTerms = r.predTerms;
        ctx.predPin = r.predPin;
        ctx.newTerms = r.newTerms;
        ctx.newPin = r.newPin;
        ctx.auth = r.auth;
    }

    /// E1 to E6: the predecessor is revoked as superseded, the successor is the lineage's active mandate (pause bits inherited), the nonce is
    /// spent, the exposure index moves from the old tokens to the new ones. Nothing here touches Permit2 or any sibling mandate.
    function _applySuccessor(Mandate storage p, Lineage storage l, SuccessorRequest calldata r) internal returns (bytes32 nid) {
        // the structural invariants of a lineage, re-checked here whatever the validator said
        if (
            r.newTerms.merchantId != r.predTerms.merchantId || r.newTerms.subscriptionRef != r.predTerms.subscriptionRef
                || r.newTerms.anchorStartsAt != r.predTerms.anchorStartsAt || r.newTerms.periodSeconds != r.predTerms.periodSeconds
        ) revert LineageConstantsChanged();
        nid = mandateIdOf(p.lineageId, p.generation + 1);
        usedNonce[p.customer][r.auth.nonce] = true;
        _decStored(p);
        p.status = MS_REVOKED;
        p.reason = r.auth.kind == REVISION ? RV_SUPERSEDED_REVISION : RV_SUPERSEDED_MIGRATION;
        Mandate storage n = mandates[nid];
        _head(n, p.lineageId, r.auth.predecessorId, p.generation + 1, p.customer, r.auth.newRouter);
        _body(n, r.newTerms, r.newPin);
        n.pause = p.pause; // E3: the pause bits carry over
        _incTokens(p.customer, r.auth.newRouter, r.newTerms.tokens);
        l.activeMandateId = nid;
        l.generation = p.generation + 1;
        l.pinVersion = r.newPin.pinVersion;
        emit MandateSuperseded(p.lineageId, r.auth.predecessorId, nid, r.auth.kind, r.auth.newRouter, n.termsHash, n.pinHash, r.newTerms, r.newPin);
    }

    // ------------------------------------------------------------------------------------------------------------ views
    function mandateView(bytes32 id) external view returns (MandateView memory v) {
        Mandate storage m = mandates[id];
        v = MandateView({
            lineageId: m.lineageId,
            predecessorId: m.predecessorId,
            termsHash: m.termsHash,
            pinHash: m.pinHash,
            customer: m.customer,
            router: m.router,
            generation: m.generation,
            pinVersion: m.pinVersion,
            status: m.status,
            reason: m.reason,
            pause: m.pause,
            retired: m.retired,
            expiresAt: m.expiresAt,
            nTokens: m.nTokens,
            tokens: m.tokens
        });
    }

    function pinHashOf(bytes32 id) external view returns (bytes32) {
        return _mandate(id).pinHash;
    }

    function partiesOf(bytes32 id) external view returns (bytes32 lineageId, address customer) {
        Mandate storage m = _mandate(id);
        return (m.lineageId, m.customer);
    }

    /// Consumable(r, m) at the level of Layer 3 (Permit2 is not consulted): the lineage's active mandate, ACTIVE, not paused, bound to `router`,
    /// not retired and not expired. (PIN_OK needs the pin and is checked by consume.)
    function isConsumable(bytes32 id, address router) external view returns (bool) {
        Mandate storage m = mandates[id];
        if (m.lineageId == bytes32(0)) return false;
        Lineage storage l = lineages[m.lineageId];
        return m.status == MS_ACTIVE && l.activeMandateId == id && !l.terminated && m.router == router && m.pause == 0 && !m.retired
            && block.timestamp < m.expiresAt;
    }
}
