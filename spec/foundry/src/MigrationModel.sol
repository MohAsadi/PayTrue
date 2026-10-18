// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import "./Errors.sol";
import "./Mutants.sol";
import {WidthLib} from "./WidthLib.sol";
import {AllowanceMath, Permit2Mock} from "./Permit2Mock.sol";
import {RegistryModel} from "./RegistryModel.sol";
import {PinModel} from "./PinModel.sol";
import {ContainModel, TermsShape} from "./ContainModel.sol";
import {HashModel} from "./HashModel.sol";

/// Reference model of the MandateManager predicates of document 12 section 5.3 (activateSuccessor: A1, A2, A3, L1, R1, R2, R3, X1, K1,
/// G1, X2, C1, C2, O1N, O1E and the effects E1..E6), of the exposure index (section 5.3.1), of revoke, retire, reduce and consume, and
/// of updateAccountPin (document 17 section 5.3). Mirrors protocol_model.ManagerModel line by line.
/// Simplifications (deliberate, see foundry/README.md): the manager builds the successor mandate itself (its lineage, customer and
/// generation are not caller-supplied); the price band of a mandate is the band of its bounds version in the model registry
/// (ContainModel.band), not a pair stored in the mandate; charges check the per-payment and total
/// token caps only (no window counters, no fiat, no fee); activate does not check Permit2 funding; terms and pins are stored once by
/// content hash (an implementation detail that keeps the replay of the state tables affordable).
/// Every function that has a mutation takes `mutant`: 0 is the specification, any other value applies exactly one named mutation.
contract MigrationModel {
    uint8 public constant NORMAL = 0;
    uint8 public constant EMERGENCY = 1;
    uint8 public constant REVISION = 2;
    uint8 public constant MODE_EMERGENCY = 1;
    uint8 public constant MS_ACTIVE = 0;
    uint8 public constant MS_REVOKED = 1;
    uint8 public constant RV_NONE = 0;
    uint8 public constant RV_CUSTOMER = 1;
    uint8 public constant RV_SUPERSEDED_MIGRATION = 2;
    uint8 public constant RV_SUPERSEDED_REVISION = 3;
    uint256 public constant MAX_EXPOSED_TOKENS_PER_ROUTER = 8; // PC-18, proposal
    uint256 public constant TOKEN_BASE = 0x7000;

    Permit2Mock public immutable p2;
    RegistryModel public immutable reg;

    struct Mandate {
        bytes32 id;
        bytes32 lineageId;
        bytes32 predecessorId;
        bytes32 termsKey;
        bytes32 pinKey;
        bytes32 parentSnapshotHash;
        address customer;
        address router;
        uint32 generation;
        uint8 status;
        uint8 reason;
        uint8 pause;
        bool retired;
    }

    struct Lineage {
        address customer;
        bytes32 activeMandateId;
        uint32 generation;
        uint32 pinVersion;
        bool terminated;
        bool exists;
    }

    struct Auth {
        address customer;
        bytes32 lineageId;
        bytes32 predecessorId;
        uint8 kind;
        bytes32 newTermsHash;
        address newRouter;
        bytes32 newRouterCodeHash;
        uint32 newRouterVersion;
        bytes32 termsSnapshotHash;
        uint32 widenedMask;
        PinModel.Pin accountPin;
        uint256 deadline;
        uint256 nonce;
    }

    /// How the call reaches the contract: msg.sender is the customer, or a signature by the account key or through ERC-1271.
    struct Access {
        bool senderIsCustomer;
        uint8 sigPath;
        bool sigOk;
    }

    /// The facts of the predecessor that every predicate reads (kept in one memory struct to stay clear of stack limits).
    struct Ctx {
        Mandate p;
        ContainModel.Terms pTerms;
        PinModel.Pin pPin;
        address c;
        address rOld;
        address rNew;
        uint8 kind;
        uint256 mutant;
    }

    mapping(bytes32 => Mandate) internal mandates;
    mapping(bytes32 => Lineage) public lineages;
    mapping(bytes32 => bytes32[]) public lineageMandateIds;
    mapping(address => mapping(address => mapping(address => uint32))) public live; // live(C, R, t)
    mapping(address => mapping(address => address[])) internal exposedList; // Exposed(C, R)
    mapping(address => mapping(address => mapping(address => uint256))) public exposedPos; // 1-based position of t in exposedList[C][R]; 0 = absent
    mapping(address => mapping(uint256 => bool)) public usedNonce;
    mapping(address => bytes32) public codeHashOf; // EXTCODEHASH of an account or a delegate (harness)
    mapping(bytes32 => mapping(address => uint256)) public usedTotal;
    mapping(bytes32 => uint256) public cycleEpoch;
    mapping(bytes32 => mapping(uint256 => mapping(uint256 => bool))) public cycleSettled;
    mapping(bytes32 => uint256) public cycleCount;

    mapping(bytes32 => ContainModel.Terms) internal termsStore;
    mapping(bytes32 => bool) internal termsKnown;
    mapping(bytes32 => PinModel.Pin) internal pinStore;
    mapping(bytes32 => bool) internal pinKnown;

    event MandateActivated(bytes32 indexed lineageId, bytes32 indexed mandateId);
    event MandateSuperseded(bytes32 indexed lineageId, bytes32 indexed predecessorId, bytes32 newId, uint8 kind);
    event MandateRevoked(bytes32 indexed lineageId, bytes32 indexed mandateId);
    event MandateRetired(bytes32 indexed mandateId);
    event AccountPinUpdated(bytes32 indexed mandateId, uint32 pinVersion);

    constructor(Permit2Mock p2_, RegistryModel reg_) {
        p2 = p2_;
        reg = reg_;
    }

    // ------------------------------------------------------------------------------------------------------------ storage helpers
    function _putTerms(ContainModel.Terms memory t) internal returns (bytes32 k) {
        k = keccak256(abi.encode(t));
        if (!termsKnown[k]) {
            termsStore[k] = t;
            termsKnown[k] = true;
        }
    }

    function _putPin(PinModel.Pin memory p) internal returns (bytes32 k) {
        k = PinModel.structHash(p);
        if (!pinKnown[k]) {
            pinStore[k] = p;
            pinKnown[k] = true;
        }
    }

    function _getTerms(bytes32 k) internal view returns (ContainModel.Terms memory) {
        return termsStore[k];
    }

    function _getPin(bytes32 k) internal view returns (PinModel.Pin memory) {
        return pinStore[k];
    }

    function _mandate(bytes32 id) internal view returns (Mandate storage m) {
        m = mandates[id];
        if (m.id == bytes32(0)) revert UnknownMandate();
    }

    function _accountState(address customer, PinModel.Pin memory pin) internal view returns (bytes32 h, bytes32 hd) {
        h = codeHashOf[customer];
        hd = codeHashOf[pin.delegate];
    }

    function _terminal(Mandate memory m, ContainModel.Terms memory t) internal view returns (bool) {
        return m.status != MS_ACTIVE || block.timestamp >= t.expiresAt;
    }

    // ------------------------------------------------------------------------------------------------------------ exposure index
    /// O(1): the exposure list is a dense array with a 1-based position index (`exposedPos`, 0 = absent), so neither insertion nor
    /// swap-and-pop removal scans the list. Nothing in revoke, retire, reduce or a migration iterates over the exposure list except the
    /// emergency predicate O1E, which is bounded by MAX_EXPOSED_TOKENS_PER_ROUTER (document 12 section 5.3.1, tools/loop_audit.py).
    function _liveInc(address c, address r, address t) internal {
        uint32 n = live[c][r][t] + 1; // checked: Panic(0x11) at 2^32 - 1
        live[c][r][t] = n;
        if (n == 1) {
            address[] storage lst = exposedList[c][r];
            lst.push(t);
            exposedPos[c][r][t] = lst.length;
        }
    }

    function _liveDec(address c, address r, address t) internal {
        uint32 n = live[c][r][t] - 1; // checked: Panic(0x11) at 0
        live[c][r][t] = n;
        if (n == 0) {
            address[] storage lst = exposedList[c][r];
            uint256 pos = exposedPos[c][r][t]; // 1-based; non-zero whenever live was 1 (every push records it)
            assert(pos != 0);
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

    /// |Exposed(C, R) u tokens|; the mutant X2_NO_UNION counts only the tokens already exposed. O(nTokens): one index read per token.
    function _exposedCountWith(address c, address r, ContainModel.Terms memory t, bool noUnion) internal view returns (uint256) {
        address[] storage lst = exposedList[c][r];
        uint256 extra = 0;
        if (!noUnion) {
            // loop-bound: TOKENS | nTokens <= MAX_TOKENS_PER_MANDATE | TermsShape.require_ runs in activate and activateSuccessor before any terms are stored, and the arrays have three slots
            for (uint256 i = 0; i < t.nTokens; ++i) {
                if (exposedPos[c][r][t.tokens[i]] == 0) extra += 1;
            }
        }
        return lst.length + extra;
    }

    function exposedCount(address c, address r) external view returns (uint256) {
        return exposedList[c][r].length;
    }

    function exposedAt(address c, address r, uint256 i) external view returns (address) {
        return exposedList[c][r][i];
    }

    // ------------------------------------------------------------------------------------------------------------ harness
    function setCodeHash(address account, bytes32 h) external {
        codeHashOf[account] = h;
    }

    /// Test-only: set a raw exposure count (for the uint32 boundary vectors).
    function seedLive(address c, address r, address t, uint256 n) external {
        live[c][r][t] = WidthLib.toUint32(n);
        if (n > 0 && exposedPos[c][r][t] == 0) {
            address[] storage lst = exposedList[c][r];
            lst.push(t);
            exposedPos[c][r][t] = lst.length;
        }
    }

    // ------------------------------------------------------------------------------------------------------------ activate
    function activate(
        address customer,
        uint256 creationNonce,
        address router,
        ContainModel.Terms memory terms,
        PinModel.Pin memory pin,
        uint256 mutant
    ) external returns (bytes32 lid, bytes32 mid) {
        TermsShape.require_(terms);
        (bytes32 h, bytes32 hd) = _accountState(customer, pin);
        if (mutant != M_ACT_BIND_SKIP && !reg.isBindable(router, mutant)) revert RouterNotBindable();
        if (terms.extensionsHash != bytes32(0)) revert ExtensionsNotSupported();
        if (mutant != M_ACT_WF_SKIP && !PinModel.wellFormed(pin, mutant)) revert AccountPinMalformed();
        if (mutant != M_ACT_OK_SKIP && !PinModel.pinOk(pin, h, hd, mutant)) revert AccountPinMismatch();
        if (mutant != M_ACT_VER_SKIP && pin.pinVersion != PinModel.nextVersion(PinModel.NV_FIRST, 0, pin, pin, mutant)) {
            revert PinVersionMismatch();
        }
        if (mutant != M_ACT_X2_SKIP && _exposedCountWith(customer, router, terms, mutant == M_X2_NO_UNION) > MAX_EXPOSED_TOKENS_PER_ROUTER) {
            revert ExposureLimit();
        }
        lid = HashModel.lineageId(block.chainid, address(this), customer, terms.merchantId, terms.subscriptionRef, creationNonce);
        mid = HashModel.mandateId(lid, 0);
        if (lineages[lid].exists) revert WrongPredecessor();
        if (mutant != M_ACT_NO_INC) {
            // loop-bound: TOKENS | nTokens <= MAX_TOKENS_PER_MANDATE | TermsShape.require_ runs in activate and activateSuccessor before any terms are stored, and the arrays have three slots
            for (uint256 i = 0; i < terms.nTokens; ++i) {
                _liveInc(customer, router, terms.tokens[i]);
            }
        }
        lineages[lid] = Lineage(customer, mid, 0, pin.pinVersion, false, true);
        lineageMandateIds[lid].push(mid);
        Mandate storage m = mandates[mid];
        m.id = mid;
        m.lineageId = lid;
        m.customer = customer;
        m.router = router;
        m.termsKey = _putTerms(terms);
        m.pinKey = _putPin(pin);
        emit MandateActivated(lid, mid);
    }

    // ------------------------------------------------------------------------------------------------------------ the authorization a correct client signs
    function buildAuth(
        bytes32 predecessorId,
        uint8 kind,
        address newRouter,
        ContainModel.Terms memory newTerms,
        PinModel.Pin memory newPin,
        uint256 deadline,
        uint256 nonce
    ) external view returns (Auth memory a) {
        Mandate storage p = _mandate(predecessorId);
        ContainModel.Terms memory pt = _getTerms(p.termsKey);
        a.customer = p.customer;
        a.lineageId = p.lineageId;
        a.predecessorId = p.id;
        a.kind = kind;
        a.newTermsHash = ContainModel.termsHash(newTerms); // hashStruct(MandateTerms) of the new terms (document 12 A3)
        a.newRouter = newRouter;
        a.newRouterCodeHash = reg.codeHashOf(newRouter);
        a.newRouterVersion = reg.versionOf(newRouter);
        a.termsSnapshotHash = ContainModel.snapshotHash(p.lineageId, p.predecessorId, p.generation, p.customer, pt);
        a.widenedMask = WidthLib.toUint32(kind == REVISION ? ContainModel.widenedMask(newTerms, pt) : 0);
        a.accountPin = newPin;
        a.deadline = deadline;
        a.nonce = nonce;
    }

    // ------------------------------------------------------------------------------------------------------------ activateSuccessor
    function activateSuccessor(
        bytes32 predecessorId,
        uint8 kind,
        address newRouter,
        ContainModel.Terms memory newTerms,
        PinModel.Pin memory newPin,
        Auth memory auth,
        Access memory access,
        uint256 mutant
    ) external returns (bytes32 newId) {
        TermsShape.require_(newTerms);
        Ctx memory x;
        Mandate storage p = _mandate(predecessorId);
        x.p = p;
        x.pTerms = _getTerms(p.termsKey);
        x.pPin = _getPin(p.pinKey);
        x.c = p.customer;
        x.rOld = p.router;
        x.rNew = newRouter;
        x.kind = kind;
        x.mutant = mutant;
        _a1(x, newPin, access);
        _a2(x, auth);
        _a3(x, newTerms, newPin, auth);
        _l1(x);
        _r1r2r3(x);
        _x1(x, newTerms);
        _k1(x, newPin);
        _g1(x, newTerms);
        _x2(x, newTerms);
        _c1c2(x, newTerms, auth);
        if (kind == NORMAL) _o1n(x);
        if (kind == EMERGENCY) _o1e(x);
        newId = _effects(x, newTerms, newPin, auth);
    }

    /// A1 AUTH: msg.sender = C or AUTH(C, digest, P.accountPin) (the stored pin governs, never the one in the message).
    function _a1(Ctx memory x, PinModel.Pin memory newPin, Access memory access) private view {
        if (x.mutant == M_A1_SKIP) return;
        PinModel.Pin memory ctxPin = x.mutant == M_A1_PIN_FROM_NEW ? newPin : x.pPin;
        (bytes32 h, bytes32 hd) = _accountState(x.c, ctxPin);
        PinModel.authSignature(x.c, access.senderIsCustomer, access.sigPath, access.sigOk, ctxPin, h, hd, x.mutant);
    }

    /// A2 FRESH: now <= auth.deadline and the nonce is unused.
    function _a2(Ctx memory x, Auth memory auth) private view {
        if (x.mutant != M_A2_DEADLINE_SKIP) {
            bool late = x.mutant == M_A2_DEADLINE_STRICT ? block.timestamp >= auth.deadline : block.timestamp > auth.deadline;
            if (late) revert AuthorizationExpired();
        }
        if (x.mutant != M_A2_NONCE_SKIP && usedNonce[x.c][auth.nonce]) revert AuthorizationReplayed();
    }

    /// A3 BIND: the authorization names this customer, lineage, predecessor, kind, terms, router (code hash, version), pin and snapshot.
    function _a3(Ctx memory x, ContainModel.Terms memory newTerms, PinModel.Pin memory newPin, Auth memory auth) private view {
        if (x.mutant == M_A3_SKIP) return;
        bytes32 nth = ContainModel.termsHash(newTerms);
        if (x.mutant != M_A3_CUSTOMER && auth.customer != x.c) revert AuthorizationMismatch();
        if (x.mutant != M_A3_LINEAGE && auth.lineageId != x.p.lineageId) revert AuthorizationMismatch();
        if (x.mutant != M_A3_PRED && auth.predecessorId != x.p.id) revert AuthorizationMismatch();
        if (x.mutant != M_A3_KIND && auth.kind != x.kind) revert AuthorizationMismatch();
        if (x.mutant != M_A3_TERMS && auth.newTermsHash != nth) revert AuthorizationMismatch();
        if (x.mutant != M_A3_ROUTER && auth.newRouter != x.rNew) revert AuthorizationMismatch();
        if (x.mutant != M_A3_CODEHASH && auth.newRouterCodeHash != reg.codeHashOf(x.rNew)) revert AuthorizationMismatch();
        if (x.mutant != M_A3_VERSION && auth.newRouterVersion != reg.versionOf(x.rNew)) revert AuthorizationMismatch();
        if (x.mutant != M_A3_PIN && PinModel.structHash(auth.accountPin) != PinModel.structHash(newPin)) revert AuthorizationMismatch();
        bytes32 snap = ContainModel.snapshotHash(x.p.lineageId, x.p.predecessorId, x.p.generation, x.c, x.pTerms);
        if (x.mutant != M_A3_SNAPSHOT && auth.termsSnapshotHash != snap) revert AuthorizationMismatch();
    }

    /// L1 LINEAGE: the lineage's active mandate is the predecessor, the lineage is not terminated and the predecessor is not terminal.
    function _l1(Ctx memory x) private view {
        if (x.mutant == M_L1_SKIP) return;
        Lineage storage l = lineages[x.p.lineageId];
        if (l.activeMandateId != x.p.id || l.terminated) revert WrongPredecessor();
        if (x.mutant != M_L1_TERMINAL && _terminal(x.p, x.pTerms)) revert WrongPredecessor();
    }

    /// R1 BINDABLE, R2 KIND, R3 MODE (the mode is derived from the registry, never chosen by the caller).
    function _r1r2r3(Ctx memory x) private view {
        if (x.mutant != M_R1_SKIP && !reg.isBindable(x.rNew, x.mutant)) revert RouterNotBindable();
        if (x.kind > REVISION) revert WrongKind();
        if (x.mutant != M_R2_SKIP) {
            if (x.kind != REVISION && x.rNew == x.rOld && x.mutant != M_R2_SAME_ROUTER_OK) revert WrongKind();
            if (x.kind == REVISION && x.rNew != x.rOld && x.mutant != M_R2_REVISION_ANY) revert WrongKind();
        }
        if (x.kind != REVISION && x.mutant != M_R3_SKIP) {
            uint8 mode = reg.mode(x.rOld, x.mutant);
            if (x.mutant == M_R3_STRICT) {
                if (x.kind != mode) revert ModeMismatch();
            } else if (mode == MODE_EMERGENCY && x.kind != EMERGENCY) {
                revert ModeMismatch();
            }
        }
    }

    /// X1 EXT: extensionsHash is zero on both sides.
    function _x1(Ctx memory x, ContainModel.Terms memory newTerms) private pure {
        if (x.mutant == M_X1_SKIP) return;
        if (newTerms.extensionsHash != bytes32(0) || x.pTerms.extensionsHash != bytes32(0)) revert ExtensionsNotSupported();
    }

    /// K1 ACCOUNT: PIN_WELLFORMED(N.pin), PIN_OK(C, N.pin), N.pin.pinVersion = nextPinVersion.
    function _k1(Ctx memory x, PinModel.Pin memory newPin) private view {
        (bytes32 h, bytes32 hd) = _accountState(x.c, newPin);
        if (x.mutant != M_K1_WF_SKIP && !PinModel.wellFormed(newPin, x.mutant)) revert AccountPinMalformed();
        if (x.mutant != M_K1_OK_SKIP && !PinModel.pinOk(newPin, h, hd, x.mutant)) revert AccountPinMismatch();
        if (x.mutant != M_K1_VER_SKIP) {
            uint32 want = PinModel.nextVersion(PinModel.NV_SUCCESSOR, lineages[x.p.lineageId].pinVersion, x.pPin, newPin, x.mutant);
            if (newPin.pinVersion != want) revert PinVersionMismatch();
        }
    }

    /// G1 NEWPERM: every token of the new mandate has an allowance on the new router of at least its per-payment cap, not expired.
    function _g1(Ctx memory x, ContainModel.Terms memory newTerms) private view {
        if (x.mutant == M_G1_SKIP) return;
        uint256 n = newTerms.nTokens;
        if (x.mutant == M_G1_FIRST_ONLY && n > 1) n = 1;
        // loop-bound: TOKENS | nTokens <= MAX_TOKENS_PER_MANDATE | TermsShape.require_ runs in activate and activateSuccessor before any terms are stored, and the arrays have three slots
        for (uint256 i = 0; i < n; ++i) {
            address t = newTerms.tokens[i];
            (uint160 amount, uint48 expiration,) = p2.allowance(x.c, t, x.rNew);
            bool short = x.mutant == M_G1_AMOUNT_GT ? amount <= newTerms.caps[i][0] : amount < newTerms.caps[i][0];
            bool late = false;
            if (x.mutant == M_G1_EXPIRY_SKIP) late = false;
            else if (x.mutant == M_G1_EXPIRY_STRICT) late = block.timestamp >= expiration;
            else late = block.timestamp > expiration;
            if (short || late) revert NewPermissionMissing(t);
        }
    }

    /// X2 EXPOSURE: |Exposed(C, Rnew) u TN| <= MAX_EXPOSED_TOKENS_PER_ROUTER.
    function _x2(Ctx memory x, ContainModel.Terms memory newTerms) private view {
        if (x.mutant == M_X2_SKIP) return;
        uint256 n = _exposedCountWith(x.c, x.rNew, newTerms, x.mutant == M_X2_NO_UNION);
        uint256 limit = x.mutant == M_X2_LT ? MAX_EXPOSED_TOKENS_PER_ROUTER - 1 : MAX_EXPOSED_TOKENS_PER_ROUTER;
        if (n > limit) revert ExposureLimit();
    }

    /// C1 CONTAIN (migration) and C2 REVISE (revision).
    function _c1c2(Ctx memory x, ContainModel.Terms memory newTerms, Auth memory auth) private pure {
        if (x.kind != REVISION) {
            if (x.mutant == M_C1_SKIP) return;
            if (ContainModel.containedMask(newTerms, x.pTerms, x.mutant) != 0) revert TermsNotContained();
            if (x.mutant != M_C1_MASK_SKIP && auth.widenedMask != 0) revert TermsNotContained();
        } else {
            if (x.mutant != M_C2_CONST_SKIP && !ContainModel.lineageConstantsEqual(newTerms, x.pTerms)) revert LineageConstantsChanged();
            if (x.mutant != M_C2_MASK_SKIP && auth.widenedMask != ContainModel.widenedMask(newTerms, x.pTerms)) revert WidenedMaskMismatch();
        }
    }

    /// O1N (kind NORMAL): for every predecessor token, Sib = live - 1; Sib = 0 requires the old allowance Unusable, Sib > 0 requires it Bounded.
    function _o1n(Ctx memory x) private view {
        if (x.mutant == M_O1N_SKIP) return;
        // loop-bound: TOKENS | nTokens <= MAX_TOKENS_PER_MANDATE | TermsShape.require_ runs in activate and activateSuccessor before any terms are stored, and the arrays have three slots
        for (uint256 i = 0; i < x.pTerms.nTokens; ++i) {
            address t = x.pTerms.tokens[i];
            uint32 liveN = live[x.c][x.rOld][t];
            uint256 sib = x.mutant == M_O1N_SIB_LIVE ? uint256(liveN) : uint256(liveN - 1); // Panic(0x11) if the index says 0
            (uint160 amount, uint48 expiration,) = p2.allowance(x.c, t, x.rOld);
            if (sib == 0) {
                if (x.mutant != M_O1N_ZERO_SKIP && AllowanceMath.usableMutated(amount, expiration, block.timestamp, x.mutant)) {
                    revert OldPermissionNotRevoked(t);
                }
            } else {
                if (x.mutant != M_O1N_BOUNDED_SKIP && amount >= type(uint160).max) revert ResidualAllowanceUnbounded(t);
            }
        }
    }

    /// O1E (kind EMERGENCY): every token any live mandate of C uses on the old router has an Unusable allowance.
    function _o1e(Ctx memory x) private view {
        if (x.mutant == M_O1E_SKIP) return;
        if (x.mutant == M_O1E_PRED_ONLY) {
            // loop-bound: TOKENS | nTokens <= MAX_TOKENS_PER_MANDATE | TermsShape.require_ runs in activate and activateSuccessor before any terms are stored, and the arrays have three slots
            for (uint256 i = 0; i < x.pTerms.nTokens; ++i) {
                _requireUnusable(x, x.pTerms.tokens[i]);
            }
        } else {
            address[] memory exposed = exposedList[x.c][x.rOld];
            // loop-bound: EXPOSED | exposed.length <= MAX_EXPOSED_TOKENS_PER_ROUTER | predicate X2 refuses any activation that would push |Exposed(C, R)| above the bound; invariant I-MIG-10 and test/LoopBounds.t.sol check the list length
            for (uint256 j = 0; j < exposed.length; ++j) {
                _requireUnusable(x, exposed[j]);
            }
        }
    }

    function _requireUnusable(Ctx memory x, address t) private view {
        (uint160 amount, uint48 expiration,) = p2.allowance(x.c, t, x.rOld);
        if (AllowanceMath.usableMutated(amount, expiration, block.timestamp, x.mutant)) revert OldPermissionNotRevoked(t);
    }

    /// Effects E1..E6 (only if SuccessorOK). No call to Permit2 other than `allowance` views is made, and no sibling is written.
    function _effects(Ctx memory x, ContainModel.Terms memory newTerms, PinModel.Pin memory newPin, Auth memory auth)
        private
        returns (bytes32 nid)
    {
        uint32 gen = x.p.generation + 1;
        nid = HashModel.mandateId(x.p.lineageId, gen);
        // E6 first: it can still revert (checked uint32 arithmetic); a revert undoes everything
        if (x.mutant != M_E6_SKIP_DEC) {
            uint256 nDec = x.pTerms.nTokens;
            if (x.mutant == M_E6_DEC_FIRST_ONLY && nDec > 1) nDec = 1;
            // loop-bound: TOKENS | nTokens <= MAX_TOKENS_PER_MANDATE | TermsShape.require_ runs in activate and activateSuccessor before any terms are stored, and the arrays have three slots
            for (uint256 i = 0; i < nDec; ++i) {
                _liveDec(x.c, x.rOld, x.pTerms.tokens[i]);
            }
        }
        if (x.mutant != M_E6_SKIP_INC) {
            // loop-bound: TOKENS | nTokens <= MAX_TOKENS_PER_MANDATE | TermsShape.require_ runs in activate and activateSuccessor before any terms are stored, and the arrays have three slots
            for (uint256 j = 0; j < newTerms.nTokens; ++j) {
                _liveInc(x.c, x.rNew, newTerms.tokens[j]);
                if (x.mutant == M_E6_INC_TWO) _liveInc(x.c, x.rNew, newTerms.tokens[j]);
            }
        }
        _supersede(x);
        _createSuccessor(x, nid, gen, newTerms, newPin, auth);
        if (x.mutant == M_CNT_RESET) {
            // loop-bound: TOKENS | nTokens <= MAX_TOKENS_PER_MANDATE | TermsShape.require_ runs in activate and activateSuccessor before any terms are stored, and the arrays have three slots
            for (uint256 k = 0; k < x.pTerms.nTokens; ++k) {
                usedTotal[x.p.lineageId][x.pTerms.tokens[k]] = 0;
            }
            cycleEpoch[x.p.lineageId] += 1;
        }
        emit MandateSuperseded(x.p.lineageId, x.p.id, nid, x.kind);
    }

    /// E1: the predecessor is revoked as SUPERSEDED in the same transaction.
    function _supersede(Ctx memory x) private {
        if (x.mutant == M_E1_SKIP) return;
        Mandate storage p = mandates[x.p.id];
        p.status = MS_REVOKED;
        p.reason = x.kind != REVISION ? RV_SUPERSEDED_MIGRATION : RV_SUPERSEDED_REVISION;
        if (x.mutant == M_E1_REASON) p.reason = RV_CUSTOMER;
    }

    /// E2, E3, E4: the lineage's active mandate, the new mandate (pause bits inherited), the authorization nonce.
    function _createSuccessor(
        Ctx memory x,
        bytes32 nid,
        uint32 gen,
        ContainModel.Terms memory newTerms,
        PinModel.Pin memory newPin,
        Auth memory auth
    ) private {
        Mandate storage n = mandates[nid];
        n.id = nid;
        n.lineageId = x.p.lineageId;
        n.predecessorId = x.p.id;
        n.customer = x.c;
        n.router = x.rNew;
        n.generation = gen;
        n.status = MS_ACTIVE;
        n.reason = RV_NONE;
        n.pause = x.mutant == M_E3_PAUSE_DROP ? 0 : x.p.pause;
        n.parentSnapshotHash = auth.termsSnapshotHash;
        n.termsKey = _putTerms(newTerms);
        n.pinKey = _putPin(newPin);
        lineageMandateIds[x.p.lineageId].push(nid);
        Lineage storage l = lineages[x.p.lineageId];
        l.generation = gen;
        l.pinVersion = newPin.pinVersion;
        if (x.mutant != M_E2_SKIP) l.activeMandateId = nid;
        if (x.mutant != M_A2_NONCE_NOT_MARKED) usedNonce[x.c][auth.nonce] = true;
    }

    // ------------------------------------------------------------------------------------------------------------ exits and housekeeping
    function revoke(bytes32 mandateId, bool senderIsCustomer, uint256 mutant) external {
        Mandate storage m = _mandate(mandateId);
        if (!senderIsCustomer) revert NotCustomer();
        if (m.status != MS_ACTIVE) revert MandateNotActive();
        if (!m.retired && mutant != M_REV_NO_DEC) {
            ContainModel.Terms memory t = _getTerms(m.termsKey);
            // loop-bound: TOKENS | nTokens <= MAX_TOKENS_PER_MANDATE | TermsShape.require_ runs in activate and activateSuccessor before any terms are stored, and the arrays have three slots
            for (uint256 i = 0; i < t.nTokens; ++i) {
                _liveDec(m.customer, m.router, t.tokens[i]);
            }
        }
        m.status = MS_REVOKED;
        m.reason = RV_CUSTOMER;
        Lineage storage l = lineages[m.lineageId];
        if (l.activeMandateId == m.id) l.terminated = true;
        emit MandateRevoked(m.lineageId, m.id);
    }

    /// retire(mandateId): permissionless; exists because EXPIRED and EXHAUSTED are derived states no transaction would record.
    function retire(bytes32 mandateId, uint256 mutant) external {
        Mandate storage m = _mandate(mandateId);
        if (m.status != MS_ACTIVE || m.retired) revert NotRetirable();
        ContainModel.Terms memory t = _getTerms(m.termsKey);
        if (mutant != M_RET_ANYTIME && block.timestamp < t.expiresAt) revert NotRetirable();
        if (mutant != M_RET_NO_DEC) {
            // loop-bound: TOKENS | nTokens <= MAX_TOKENS_PER_MANDATE | TermsShape.require_ runs in activate and activateSuccessor before any terms are stored, and the arrays have three slots
            for (uint256 i = 0; i < t.nTokens; ++i) {
                _liveDec(m.customer, m.router, t.tokens[i]);
            }
        }
        m.retired = true;
        emit MandateRetired(m.id);
    }

    /// A customer reduction that removes one token from a live mandate.
    function reduceDropToken(bytes32 mandateId, address token, uint256 mutant) external {
        Mandate storage m = _mandate(mandateId);
        if (m.status != MS_ACTIVE || m.retired) revert MandateNotActive();
        ContainModel.Terms memory t = _getTerms(m.termsKey);
        (uint256 idx, bool found) = ContainModel.indexOf(t, token);
        if (!found) revert TokenNotInMandate();
        if (t.nTokens == 1) revert NoTokensLeft();
        if (mutant != M_RED_NO_DEC) _liveDec(m.customer, m.router, token);
        // loop-bound: TOKENS | nTokens <= MAX_TOKENS_PER_MANDATE | TermsShape.require_ runs in activate and activateSuccessor before any terms are stored, and the arrays have three slots
        for (uint256 i = idx; i + 1 < t.nTokens; ++i) {
            t.tokens[i] = t.tokens[i + 1];
            // loop-bound: FIXED | 6 cap families per token | a literal of 6: cap families per token
            for (uint256 f = 0; f < 6; ++f) {
                t.caps[i][f] = t.caps[i + 1][f];
            }
        }
        uint256 last = t.nTokens - 1;
        t.tokens[last] = address(0);
        // loop-bound: FIXED | 6 cap families per token | a literal of 6: cap families per token
        for (uint256 g = 0; g < 6; ++g) {
            t.caps[last][g] = 0;
        }
        t.nTokens -= 1;
        m.termsKey = _putTerms(t);
    }

    /// A pause bit (customer, risk, delegation). Pausing is an exit: never blocked.
    function setPause(bytes32 mandateId, uint8 bit, bool on) external {
        Mandate storage m = _mandate(mandateId);
        m.pause = on ? (m.pause | bit) : (m.pause & ~bit);
    }

    /// updateAccountPin: AUTH with the stored pin, then (in the order of document 17 section 5.3) mandate non-terminal, PIN_WELLFORMED,
    /// PIN_OK, newPin.pinVersion = old + 1, nonce unused, deadline not passed. It changes only the pin and the pin version.
    function updateAccountPin(
        bytes32 mandateId,
        PinModel.Pin memory newPin,
        uint256 deadline,
        uint256 nonce,
        Access memory access,
        uint256 mutant
    ) external {
        Mandate storage m = _mandate(mandateId);
        address c = m.customer;
        PinModel.Pin memory cur = _getPin(m.pinKey);
        if (mutant != M_UPD_AUTH_SKIP) {
            (bytes32 h, bytes32 hd) = _accountState(c, cur);
            PinModel.authSignature(c, access.senderIsCustomer, access.sigPath, access.sigOk, cur, h, hd, mutant);
        }
        if (_terminal(m, _getTerms(m.termsKey))) revert MandateNotActive();
        (bytes32 h2, bytes32 hd2) = _accountState(c, newPin);
        if (mutant != M_UPD_WF_SKIP && !PinModel.wellFormed(newPin, mutant)) revert AccountPinMalformed();
        if (mutant != M_UPD_OK_SKIP && !PinModel.pinOk(newPin, h2, hd2, mutant)) revert AccountPinMismatch();
        if (mutant != M_UPD_VER_SKIP) {
            if (newPin.pinVersion != PinModel.nextVersion(PinModel.NV_UPDATE, cur.pinVersion, cur, newPin, mutant)) revert PinVersionMismatch();
        }
        if (usedNonce[c][nonce]) revert AuthorizationReplayed();
        if (block.timestamp > deadline) revert AuthorizationExpired();
        m.pinKey = _putPin(newPin);
        lineages[m.lineageId].pinVersion = newPin.pinVersion;
        usedNonce[c][nonce] = true;
        emit AccountPinUpdated(m.id, newPin.pinVersion);
    }

    // ------------------------------------------------------------------------------------------------------------ consume (a charge by a router)
    /// G1, G2, G3, G10, G4, G9, G5 in the order of document 11 section 5, then step 7 (effects) and only then step 8 (the Permit2 pull):
    /// checks-effects-interactions. A token that calls back during the pull (an ERC-777-style hook, a hostile token) finds the cycle settled
    /// and the usage counted. If the pull fails the whole call reverts and the effects are undone. Until finding F-16 this function made
    /// the pull first; `Reentrancy.t.sol` keeps that order as a subclass to show what it allowed.
    function consume(address router, bytes32 mandateId, address token, uint256 amount, uint256 cycleIndex, PinModel.Pin memory pin, uint256 mutant)
        external
        virtual
    {
        (bytes32 lid, address c, uint256 total) = _consumeChecks(router, mandateId, token, amount, cycleIndex, pin, mutant);
        usedTotal[lid][token] = total;
        cycleSettled[lid][cycleEpoch[lid]][cycleIndex] = true;
        cycleCount[lid] += 1;
        p2.pullAs(router, c, token, amount);
    }

    function _consumeChecks(address router, bytes32 mandateId, address token, uint256 amount, uint256 cycleIndex, PinModel.Pin memory pin, uint256 mutant)
        internal
        view
        returns (bytes32 lid, address c, uint256 total)
    {
        Mandate storage m = _mandate(mandateId);
        lid = m.lineageId;
        c = m.customer;
        ContainModel.Terms memory t = _getTerms(m.termsKey);
        PinModel.Pin memory stored = _getPin(m.pinKey);
        if (mutant != M_CON_ACTIVE_SKIP && (m.status != MS_ACTIVE || lineages[lid].activeMandateId != m.id)) revert MandateNotConsumable();
        if (mutant != M_CON_PAUSE_SKIP && m.pause != 0) revert MandateNotConsumable();
        if (mutant != M_CON_TIME_SKIP && block.timestamp >= t.expiresAt) revert MandateNotConsumable();
        if (mutant != M_CON_ROUTER_SKIP && m.router != router) revert WrongRouter();
        if (mutant != M_CON_CHARGEABLE_SKIP && !reg.isChargeable(router)) revert RouterNotChargeable();
        (bytes32 h, bytes32 hd) = _accountState(c, stored);
        if (mutant != M_CON_PINHASH_SKIP && PinModel.structHash(pin) != PinModel.structHash(stored)) revert PinHashMismatch();
        if (mutant != M_CON_PINOK_SKIP) {
            uint8 field = PinModel.checkField(pin, h, hd, mutant);
            if (field != 0) revert AccountCodeChanged(c, field);
        }
        if (t.extensionsHash != bytes32(0)) revert ExtensionsNotSupported();
        (uint256 idx, bool found) = ContainModel.indexOf(t, token);
        if (!found) revert TokenNotInMandate();
        if (mutant != M_CON_SETTLE_SKIP && cycleSettled[lid][cycleEpoch[lid]][cycleIndex]) revert PaymentAlreadySettled();
        if (mutant != M_CON_PERPAY_SKIP && !ContainModel.withinCap(amount, t.caps[idx][0])) revert TokenPerPaymentCapExceeded();
        total = usedTotal[lid][token] + amount; // checked: Panic(0x11) on overflow
        if (mutant != M_CON_TOTAL_SKIP && !ContainModel.withinCap(total, t.caps[idx][1])) revert TokenTotalCapExceeded();
        if (amount > type(uint160).max) revert UnsafeCast();
    }

    /// Probe used by wouldConsume: succeeds iff the charge would.
    function probe(address router, bytes32 mandateId, address token, uint256 amount, uint256 cycleIndex, PinModel.Pin memory pin, uint256 mutant)
        external
        view
        returns (bool)
    {
        (, address c,) = _consumeChecks(router, mandateId, token, amount, cycleIndex, pin, mutant);
        return p2.canPull(c, token, router, amount);
    }

    /// Dry run of consume (no state change): can this charge succeed right now?
    function wouldConsume(address router, bytes32 mandateId, address token, uint256 amount, uint256 cycleIndex, uint256 mutant)
        external
        view
        returns (bool)
    {
        if (mandates[mandateId].id == bytes32(0)) return false;
        PinModel.Pin memory pin = _getPin(mandates[mandateId].pinKey);
        try this.probe(router, mandateId, token, amount, cycleIndex, pin, mutant) returns (bool ok) {
            return ok;
        } catch {
            return false;
        }
    }

    // ------------------------------------------------------------------------------------------------------------ views
    function getMandate(bytes32 id) external view returns (Mandate memory) {
        return mandates[id];
    }

    function mandateTerms(bytes32 id) external view returns (ContainModel.Terms memory) {
        return _getTerms(mandates[id].termsKey);
    }

    function mandatePin(bytes32 id) external view returns (PinModel.Pin memory) {
        return _getPin(mandates[id].pinKey);
    }

    function activeMandateOf(bytes32 lineageId) external view returns (bytes32) {
        return lineages[lineageId].activeMandateId;
    }

    function mandateCount(bytes32 lineageId) external view returns (uint256) {
        return lineageMandateIds[lineageId].length;
    }

    /// Consumable(r, m): status ACTIVE, the lineage's active mandate, bound to r, no pause bit, PIN_OK on the live account, and (the
    /// model adds, see the document issues) not retired and within time.
    function isConsumable(bytes32 id, address router) public view returns (bool) {
        Mandate memory m = mandates[id];
        if (m.id == bytes32(0)) return false;
        ContainModel.Terms memory t = _getTerms(m.termsKey);
        PinModel.Pin memory pin = _getPin(m.pinKey);
        (bytes32 h, bytes32 hd) = _accountState(m.customer, pin);
        return m.status == MS_ACTIVE && lineages[m.lineageId].activeMandateId == m.id && m.router == router && m.pause == 0
            && PinModel.pinOk(pin, h, hd, 0) && !m.retired && block.timestamp < t.expiresAt;
    }

    /// Is `router` in AuthRouters(L): some mandate of the lineage is consumable on it and one of its tokens has a usable allowance.
    function authRouter(bytes32 lineageId, address router, uint256 mutant) external view returns (bool) {
        bytes32[] storage ids = lineageMandateIds[lineageId];
        // loop-bound: ORACLE | ids.length = generations of the lineage | the oracle of AuthRouters(L): it walks the whole history of one lineage; a view for the invariant tests, not reachable from any state-changing function
        for (uint256 i = 0; i < ids.length; ++i) {
            if (!isConsumable(ids[i], router)) continue;
            Mandate memory m = mandates[ids[i]];
            ContainModel.Terms memory t = _getTerms(m.termsKey);
            // loop-bound: TOKENS | nTokens <= MAX_TOKENS_PER_MANDATE | TermsShape.require_ runs in activate and activateSuccessor before any terms are stored, and the arrays have three slots
            for (uint256 j = 0; j < t.nTokens; ++j) {
                (uint160 amount, uint48 expiration,) = p2.allowance(m.customer, t.tokens[j], router);
                if (AllowanceMath.usableMutated(amount, expiration, block.timestamp, mutant)) return true;
            }
        }
        return false;
    }

    function lineageDigest(bytes32 lid) external view returns (bytes32) {
        Lineage memory l = lineages[lid];
        bytes32[] memory ids = lineageMandateIds[lid];
        bytes32 acc = keccak256(abi.encode(l, keccak256(abi.encodePacked(ids)), cycleCount[lid], cycleEpoch[lid]));
        // loop-bound: FIXED | 10 token slots of the digest | a literal of 10: token slots of the digest
        for (uint256 i = 1; i <= 10; ++i) {
            acc = keccak256(abi.encode(acc, usedTotal[lid][address(uint160(TOKEN_BASE + i))]));
        }
        return acc;
    }

    function mandateDigest(bytes32 id) external view returns (bytes32) {
        Mandate memory m = mandates[id];
        return keccak256(abi.encode(m));
    }
}
