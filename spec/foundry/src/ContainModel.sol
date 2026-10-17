// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.24;

import "./Errors.sol";
import "./Mutants.sol";
import {WidthLib} from "./WidthLib.sol";
import {FastPayTypes} from "./generated/FastPayTypes.sol";

/// The migration snapshot, the containment predicate K.1..K.9, the widened mask of a revision and the mandate-dependent guards of a
/// charge (the oracle of the monotone-authority lemma). Mirrors protocol_model.contained_mask, widened_mask, accepts, band,
/// snapshot_hash_int and terms_hash_int.
/// The snapshot hash is written out here word by word (eip712/types.json snapshotEncoding: 26 words, caps in the typed order, customer,
/// anchorStartsAt and boundsVersion covered) and is checked against the generated FastPayTypes.snapshotHash; the terms hash is
/// hashStruct(MandateTerms) of the generated library, applied to the model terms converted by `toTyped`.
/// The price band of a mandate is not a field of its terms: `boundsVersion` names it, and `band` stands for the registry content (ADR-020).
/// A cap or a fiat cap of 0 means "no cap in this family": E(0) is infinity, strictly above every finite value, including uint256.max.
library ContainModel {
    bytes32 internal constant SNAPSHOT_TAG = keccak256("fastpay.migration.snapshot.v1");

    /// Static terms of a mandate. Per token (positions 0..nTokens-1, sorted ascending): caps[i] = [perPaymentMax, totalMax, dayMax,
    /// weekMax, thirtyDayMax, periodMax]; fiat has the same family order (the typed data and the snapshot hash use perPaymentMax, dayMax,
    /// weekMax, thirtyDayMax, periodMax, totalMax: see `toTyped` and `snapshotHash`).
    struct Terms {
        uint64 expiresAt;
        uint64 periodSeconds;
        uint64 anchorStartsAt;
        uint64 maxQuoteAge;
        uint64 minInterval;
        uint32 maxChargesPerPeriod;
        uint16 currency;
        uint16 maxFeeBps;
        uint8 nTokens;
        bytes32 merchantId;
        bytes32 recipientPolicy;
        bytes32 subscriptionRef;
        bytes32 extensionsHash;
        address[3] tokens;
        uint256[6][3] caps;
        uint256[6] fiat;
        uint32 boundsVersion; // the price band of (token, currency, boundsVersion) is read from the registry; published versions never change
    }

    /// Lineage usage that the charge guards read (per token position of the mandate under test, in the order of the 15 + 5 + 1 words
    /// of the exported tuple: day, week, thirtyDay, period, total).
    struct State {
        uint256[5][3] used;
        uint256[5] fiatUsed;
        uint256 chargesInPeriod;
    }

    struct Payment {
        uint256 tokenId;
        uint256 a;
        uint256 tau;
        uint256 merchant;
        bool hasFiat;
        uint256 fiat;
        uint256 age;
        uint256 price;
        uint256 sinceLast;
        uint256 feeBps;
    }

    uint256 internal constant TOKEN_BASE = 0x7000;

    // ---- E(x) comparisons
    /// E(a) <= E(b); with `infMax` the mutant C1_E_INF_MAX takes E(0) as uint256 max instead of infinity.
    function leE(uint256 a, uint256 b, bool infMax) internal pure returns (bool) {
        if (infMax) {
            uint256 x = a == 0 ? type(uint256).max : a;
            uint256 y = b == 0 ? type(uint256).max : b;
            return x <= y;
        }
        if (b == 0) return true;
        if (a == 0) return false;
        return a <= b;
    }

    /// E(a) < E(b).
    function ltE(uint256 a, uint256 b) internal pure returns (bool) {
        if (a == 0) return false;
        if (b == 0) return true;
        return a < b;
    }

    /// x <= E(cap).
    function withinCap(uint256 x, uint256 cap) internal pure returns (bool) {
        return cap == 0 || x <= cap;
    }

    /// The model registry of price bands (ADR-020, finding F-09): (lo, hi) of a bounds version, identical to protocol_model.band. Version 0
    /// and every unpublished version have the empty band (1, 0): no price is in it, so a charge that needs a price fails closed.
    function band(uint32 version) internal pure returns (uint256 lo, uint256 hi) {
        if (version == 1) return (98, 102);
        if (version == 2) return (95, 105);
        if (version == 3) return (96, 104);
        if (version == 4) return (94, 106);
        if (version == 5) return (90, 110);
        return (1, 0);
    }

    function _skip(uint256 mutant, uint256 clause) private pure returns (bool) {
        if (clause == 1) return mutant == M_C1_K1_SKIP;
        if (clause == 2) return mutant == M_C1_K2_SKIP;
        if (clause == 3) return mutant == M_C1_K3_SKIP;
        if (clause == 4) return mutant == M_C1_K4_SKIP;
        if (clause == 5) return mutant == M_C1_K5_SKIP;
        if (clause == 6) return mutant == M_C1_K6_SKIP;
        if (clause == 7) return mutant == M_C1_K7_SKIP;
        if (clause == 8) return mutant == M_C1_K8_SKIP;
        return mutant == M_C1_K9_SKIP;
    }

    function indexOf(Terms memory t, address token) internal pure returns (uint256 idx, bool found) {
        // loop-bound: TOKENS | nTokens <= MAX_TOKENS_PER_MANDATE | TermsShape.require_ runs in activate and activateSuccessor before any terms are stored, and the arrays have three slots
        for (uint256 i = 0; i < t.nTokens; ++i) {
            if (t.tokens[i] == token) return (i, true);
        }
        return (0, false);
    }

    // ---- containment: bit k-1 of the result is set when clause K.k is violated
    function containedMask(Terms memory succ, Terms memory snap, uint256 mutant) internal pure returns (uint256 m) {
        if (!_skip(mutant, 1)) {
            bool bad = mutant == M_C1_K1_STRICT ? succ.expiresAt >= snap.expiresAt : succ.expiresAt > snap.expiresAt;
            if (bad) m |= 1;
        }
        if (!_skip(mutant, 2)) {
            if (
                succ.merchantId != snap.merchantId || succ.recipientPolicy != snap.recipientPolicy
                    || succ.subscriptionRef != snap.subscriptionRef || succ.periodSeconds != snap.periodSeconds
                    || succ.anchorStartsAt != snap.anchorStartsAt
            ) m |= 1 << 1;
        }
        if (!_skip(mutant, 3) && !_tokensSubset(succ, snap)) m |= 1 << 2;
        if (!_skip(mutant, 4) && _capsViolated(succ, snap, mutant)) m |= 1 << 3;
        if (!_skip(mutant, 5) && _fiatViolated(succ, snap, mutant)) m |= 1 << 4;
        if (!_skip(mutant, 6)) {
            if (succ.boundsVersion != snap.boundsVersion) m |= 1 << 5; // a migration keeps the version; any change needs a REVISION
        }
        if (!_skip(mutant, 7)) {
            if (!leE(succ.maxChargesPerPeriod, snap.maxChargesPerPeriod, mutant == M_C1_E_INF_MAX) || succ.minInterval < snap.minInterval) {
                m |= 1 << 6;
            }
        }
        if (!_skip(mutant, 8)) {
            bool bad8 = mutant == M_C1_K8_STRICT ? succ.maxFeeBps >= snap.maxFeeBps : succ.maxFeeBps > snap.maxFeeBps;
            if (bad8) m |= 1 << 7;
        }
        if (!_skip(mutant, 9)) {
            if (succ.extensionsHash != bytes32(0) || snap.extensionsHash != bytes32(0)) m |= 1 << 8;
        }
    }

    function _tokensSubset(Terms memory succ, Terms memory snap) private pure returns (bool) {
        // loop-bound: TOKENS | nTokens <= MAX_TOKENS_PER_MANDATE | TermsShape.require_ runs in activate and activateSuccessor before any terms are stored, and the arrays have three slots
        for (uint256 i = 0; i < succ.nTokens; ++i) {
            (, bool found) = indexOf(snap, succ.tokens[i]);
            if (!found) return false;
        }
        return true;
    }

    function _capsViolated(Terms memory succ, Terms memory snap, uint256 mutant) private pure returns (bool) {
        // loop-bound: TOKENS | nTokens <= MAX_TOKENS_PER_MANDATE | TermsShape.require_ runs in activate and activateSuccessor before any terms are stored, and the arrays have three slots
        for (uint256 i = 0; i < succ.nTokens; ++i) {
            (uint256 j, bool found) = indexOf(snap, succ.tokens[i]);
            if (!found) continue;
            // loop-bound: FIXED | 6 cap families per token | a literal of 6: cap families per token
            for (uint256 f = 0; f < 6; ++f) {
                bool bad = mutant == M_C1_K4_STRICT
                    ? !ltE(succ.caps[i][f], snap.caps[j][f])
                    : !leE(succ.caps[i][f], snap.caps[j][f], mutant == M_C1_E_INF_MAX);
                if (bad) return true;
            }
        }
        return false;
    }

    function _fiatViolated(Terms memory succ, Terms memory snap, uint256 mutant) private pure returns (bool) {
        if (succ.currency != snap.currency || succ.maxQuoteAge > snap.maxQuoteAge) return true;
        // loop-bound: FIXED | 6 fiat cap families | a literal of 6: fiat cap families
        for (uint256 f = 0; f < 6; ++f) {
            if (!leE(succ.fiat[f], snap.fiat[f], mutant == M_C1_E_INF_MAX)) return true;
        }
        return false;
    }

    // ---- widenedMask of a revision (document 12 section 5.6): which dimensions grow
    function widenedMask(Terms memory n, Terms memory snap) internal pure returns (uint256 m) {
        if (n.expiresAt > snap.expiresAt) m |= 1;
        if (!_tokensSubset(n, snap)) m |= 1 << 1;
        // loop-bound: TOKENS | nTokens <= MAX_TOKENS_PER_MANDATE | TermsShape.require_ runs in activate and activateSuccessor before any terms are stored, and the arrays have three slots
        for (uint256 i = 0; i < n.nTokens; ++i) {
            (uint256 j, bool found) = indexOf(snap, n.tokens[i]);
            if (!found) continue;
            if (!leE(n.caps[i][0], snap.caps[j][0], false)) m |= 1 << 2;
            // loop-bound: FIXED | 6 cap families per token | a literal of 6: cap families per token
            for (uint256 f = 2; f < 6; ++f) {
                if (!leE(n.caps[i][f], snap.caps[j][f], false)) m |= 1 << 3;
            }
            if (!leE(n.caps[i][1], snap.caps[j][1], false)) m |= 1 << 4;
        }
        // loop-bound: FIXED | 6 fiat cap families | a literal of 6: fiat cap families
        for (uint256 g = 0; g < 6; ++g) {
            if (!leE(n.fiat[g], snap.fiat[g], false)) m |= 1 << 5;
        }
        if (n.maxQuoteAge > snap.maxQuoteAge || n.boundsVersion != snap.boundsVersion) m |= 1 << 6; // a version change is conservatively a widening
        if (!leE(n.maxChargesPerPeriod, snap.maxChargesPerPeriod, false) || n.minInterval < snap.minInterval) m |= 1 << 7;
        if (n.maxFeeBps > snap.maxFeeBps) m |= 1 << 8;
    }

    function lineageConstantsEqual(Terms memory a, Terms memory b) internal pure returns (bool) {
        return a.merchantId == b.merchantId && a.subscriptionRef == b.subscriptionRef && a.periodSeconds == b.periodSeconds
            && a.anchorStartsAt == b.anchorStartsAt && a.recipientPolicy == b.recipientPolicy && a.currency == b.currency;
    }

    // ---- Acc(m, S, p): the mandate-dependent guards of a charge (documents 11 section 4.8 and 12 section 5.3.3)
    /// Checked arithmetic: used + amount near 2^256 reverts with Panic(0x11) instead of wrapping.
    function accepts(Terms memory m, State memory st, Payment memory p) internal pure returns (bool) {
        address token = address(uint160(TOKEN_BASE + p.tokenId));
        (uint256 i, bool found) = indexOf(m, token);
        if (p.tau >= m.expiresAt || !found || p.merchant != uint256(m.merchantId)) return false;
        if (!withinCap(p.a, m.caps[i][0])) return false;
        if (!_windowsOk(m, st, p, i)) return false;
        if (p.hasFiat && !_fiatOk(m, st, p)) return false;
        // chargesInPeriod + 1 > E(maxChargesPerPeriod), written without the addition so that it cannot overflow (0 = no limit)
        if ((m.maxChargesPerPeriod != 0 && st.chargesInPeriod >= m.maxChargesPerPeriod) || p.sinceLast < m.minInterval) return false;
        if (p.feeBps > m.maxFeeBps) return false;
        return m.extensionsHash == bytes32(0);
    }

    function _windowsOk(Terms memory m, State memory st, Payment memory p, uint256 i) private pure returns (bool) {
        uint256 pos = p.tokenId - 1;
        uint8[5] memory capIndex = [2, 3, 4, 5, 1];
        // loop-bound: FIXED | 5 window and total counters | a literal of 5: window and total counters
        for (uint256 f = 0; f < 5; ++f) {
            if (!withinCap(st.used[pos][f] + p.a, m.caps[i][capIndex[f]])) return false;
        }
        return true;
    }

    function _fiatOk(Terms memory m, State memory st, Payment memory p) private pure returns (bool) {
        if (!withinCap(p.fiat, m.fiat[0])) return false;
        uint8[5] memory fiatIndex = [2, 3, 4, 5, 1];
        // loop-bound: FIXED | 5 fiat window and total counters | a literal of 5: fiat window and total counters
        for (uint256 f = 0; f < 5; ++f) {
            if (!withinCap(st.fiatUsed[f] + p.fiat, m.fiat[fiatIndex[f]])) return false;
        }
        (uint256 lo, uint256 hi) = band(m.boundsVersion);
        return p.age <= m.maxQuoteAge && p.price >= lo && p.price <= hi;
    }

    // ---- snapshot hash: the 26 words of eip712/types.json snapshotEncoding, in that order, one 32-byte word each
    /// termsSnapshotHash of the snapshot of a mandate (document 12 section 5.3.2): the arguments (lineage, predecessor, generation,
    /// customer) and the terms. The model arrays are in the order perPayment, total, day, week, thirtyDay, period; the words follow the
    /// typed order perPaymentMax, dayMax, weekMax, thirtyDayMax, periodMax, totalMax, for the token caps and for the fiat caps.
    function snapshotHash(bytes32 lineageId, bytes32 predecessorId, uint256 generation, address customer, Terms memory t)
        internal
        pure
        returns (bytes32)
    {
        bytes memory toks;
        bytes memory capt;
        // loop-bound: TOKENS | nTokens <= MAX_TOKENS_PER_MANDATE | TermsShape.require_ runs in activate and activateSuccessor before any terms are stored, and the arrays have three slots
        for (uint256 i = 0; i < t.nTokens; ++i) {
            toks = bytes.concat(toks, abi.encode(t.tokens[i]));
            capt = bytes.concat(
                capt,
                abi.encode(t.tokens[i], t.caps[i][0], t.caps[i][2], t.caps[i][3], t.caps[i][4], t.caps[i][5], t.caps[i][1])
            );
        }
        bytes memory c1 = abi.encode(SNAPSHOT_TAG, lineageId, predecessorId, generation, customer, t.merchantId);
        bytes memory c2 = abi.encode(
            t.recipientPolicy, t.subscriptionRef, uint256(t.periodSeconds), uint256(t.anchorStartsAt), uint256(t.expiresAt), keccak256(toks), keccak256(capt)
        );
        bytes memory c3 = abi.encode(uint256(t.currency), t.fiat[0], t.fiat[2], t.fiat[3], t.fiat[4], t.fiat[5], t.fiat[1]);
        bytes memory c4 = abi.encode(
            uint256(t.maxQuoteAge), uint256(t.boundsVersion), uint256(t.maxChargesPerPeriod), uint256(t.minInterval), uint256(t.maxFeeBps), t.extensionsHash
        );
        return keccak256(bytes.concat(c1, c2, c3, c4));
    }

    /// The model terms as the typed `MandateTerms` struct of the generated library (eip712/types.json). Every narrowing goes through
    /// WidthLib: a value above the documented width reverts with UnsafeCast (TermsShape refuses such terms before they reach a hash).
    function toTyped(Terms memory t) internal pure returns (FastPayTypes.MandateTerms memory m) {
        m.merchantId = t.merchantId;
        m.recipientPolicy = t.recipientPolicy;
        m.subscriptionRef = t.subscriptionRef;
        m.periodSeconds = t.periodSeconds;
        m.anchorStartsAt = t.anchorStartsAt;
        m.expiresAt = t.expiresAt;
        m.tokens = new FastPayTypes.TokenTerms[](t.nTokens);
        // loop-bound: TOKENS | nTokens <= MAX_TOKENS_PER_MANDATE | TermsShape.require_ runs in activate and activateSuccessor before any terms are stored, and the arrays have three slots
        for (uint256 i = 0; i < t.nTokens; ++i) {
            m.tokens[i] = FastPayTypes.TokenTerms({
                token: t.tokens[i],
                perPaymentMax: t.caps[i][0],
                dayMax: t.caps[i][2],
                weekMax: t.caps[i][3],
                thirtyDayMax: t.caps[i][4],
                periodMax: t.caps[i][5],
                totalMax: t.caps[i][1]
            });
        }
        m.fiat = FastPayTypes.FiatTerms({
            currency: t.currency,
            perPaymentMaxMinor: WidthLib.toUint64(t.fiat[0]),
            dayMaxMinor: WidthLib.toUint64(t.fiat[2]),
            weekMaxMinor: WidthLib.toUint64(t.fiat[3]),
            thirtyDayMaxMinor: WidthLib.toUint64(t.fiat[4]),
            periodMaxMinor: WidthLib.toUint64(t.fiat[5]),
            totalMaxMinor: WidthLib.toUint64(t.fiat[1]),
            maxQuoteAge: WidthLib.toUint32(t.maxQuoteAge),
            boundsVersion: t.boundsVersion
        });
        m.maxChargesPerPeriod = WidthLib.toUint16(t.maxChargesPerPeriod);
        m.minIntervalSeconds = WidthLib.toUint32(t.minInterval);
        m.maxFeeBps = t.maxFeeBps;
        m.extensionsHash = t.extensionsHash;
    }

    /// newTermsHash of a successor authorization (document 12 predicate A3): hashStruct(MandateTerms) of the new terms.
    function termsHash(Terms memory t) internal pure returns (bytes32) {
        return FastPayTypes.hashStruct(toTyped(t));
    }

    /// The predecessor snapshot of document 12 section 5.3.4 (tools/eip712_vectors.snapshot_reference, `pred`).
    function referenceSnapshot() internal pure returns (Terms memory t) {
        t.expiresAt = 1_900_000_000;
        t.merchantId = bytes32(uint256(0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa));
        t.recipientPolicy = bytes32(uint256(0x0101010101010101010101010101010101010101010101010101010101010101));
        t.subscriptionRef = bytes32(uint256(0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb));
        t.periodSeconds = 2_592_000;
        t.anchorStartsAt = 1_800_000_000;
        t.currency = 840;
        t.nTokens = 2;
        t.tokens[0] = 0x5555555555555555555555555555555555555555;
        t.tokens[1] = 0x6666666666666666666666666666666666666666;
        // loop-bound: FIXED | 2 tokens of the reference snapshot | a literal of 2: tokens of the reference snapshot
        for (uint256 i = 0; i < 2; ++i) {
            t.caps[i][0] = 51_020_409;
            t.caps[i][1] = 612_244_908;
            t.caps[i][4] = 51_020_409;
        }
        t.fiat[0] = 5000;
        t.fiat[1] = 60000;
        t.fiat[4] = 5000;
        t.maxQuoteAge = 120;
        t.boundsVersion = 1;
        t.maxChargesPerPeriod = 1;
        t.minInterval = 86_400;
        t.maxFeeBps = 100;
    }

    function referenceSnapshotHash() internal pure returns (bytes32) {
        bytes32 lineage = bytes32(uint256(0x7777777777777777777777777777777777777777777777777777777777777777));
        bytes32 pred = bytes32(uint256(0x7878787878787878787878787878787878787878787878787878787878787878));
        address customer = 0x4444444444444444444444444444444444444444;
        return snapshotHash(lineage, pred, 0, customer, referenceSnapshot());
    }

    function referenceTermsHash() internal pure returns (bytes32) {
        return termsHash(referenceSnapshot());
    }
}

/// The canonical shape and the documented widths of mandate terms (document 11 section 3; eip712/types.json MandateTerms and FiatTerms).
/// The deployed contract gets most of this from its ABI types (a `uint16` cannot carry 2^16) and from the length check of its entry point
/// (`TokenCountInvalid`); the reference model uses wider Solidity fields for convenience, so it states the same limits once, here, and
/// `activate` and `activateSuccessor` refuse terms that break them. Without it a value above its documented width would be accepted by
/// the model and could not exist on chain.
library TermsShape {
    uint256 internal constant MAX_TOKENS_PER_MANDATE = 3; // PC-11, proposal
    uint8 internal constant OK = 0;
    uint8 internal constant TOKEN_COUNT = 1; // nTokens is not in 1 .. MAX_TOKENS_PER_MANDATE
    uint8 internal constant TOKEN_ORDER = 2; // tokens are not non-zero, strictly ascending
    uint8 internal constant NOT_CANONICAL = 3; // a slot beyond nTokens is not zero (two encodings of the same terms)
    uint8 internal constant WIDTH_CHARGES = 4; // maxChargesPerPeriod does not fit uint16
    uint8 internal constant WIDTH_INTERVAL = 5; // minInterval does not fit uint32
    uint8 internal constant WIDTH_QUOTE_AGE = 6; // maxQuoteAge does not fit uint32
    uint8 internal constant WIDTH_FIAT = 7; // a fiat cap does not fit uint64
    uint8 internal constant WIDTH_FEE = 8; // maxFeeBps does not fit uint16 (the fee ceiling is a separate, stricter check)

    function check(ContainModel.Terms memory t) internal pure returns (uint8) {
        uint256 n = t.nTokens;
        if (n == 0 || n > MAX_TOKENS_PER_MANDATE) return TOKEN_COUNT;
        // loop-bound: TOKENS | nTokens <= MAX_TOKENS_PER_MANDATE | TermsShape.require_ runs in activate and activateSuccessor before any terms are stored, and the arrays have three slots
        for (uint256 i = 0; i < n; ++i) {
            if (t.tokens[i] == address(0)) return TOKEN_ORDER;
            if (i > 0 && uint160(t.tokens[i]) <= uint160(t.tokens[i - 1])) return TOKEN_ORDER;
        }
        // loop-bound: TOKENS | nTokens <= MAX_TOKENS_PER_MANDATE | TermsShape.require_ runs in activate and activateSuccessor before any terms are stored, and the arrays have three slots
        for (uint256 i = n; i < MAX_TOKENS_PER_MANDATE; ++i) {
            if (t.tokens[i] != address(0)) return NOT_CANONICAL;
            // loop-bound: FIXED | 6 cap families per token and fiat cap families | a literal of 6: cap families per token and fiat cap families
            for (uint256 f = 0; f < 6; ++f) {
                if (t.caps[i][f] != 0) return NOT_CANONICAL;
            }
        }
        if (t.maxChargesPerPeriod > type(uint16).max) return WIDTH_CHARGES;
        if (t.minInterval > type(uint32).max) return WIDTH_INTERVAL;
        if (t.maxQuoteAge > type(uint32).max) return WIDTH_QUOTE_AGE;
        // loop-bound: FIXED | 6 cap families per token and fiat cap families | a literal of 6: cap families per token and fiat cap families
        for (uint256 f = 0; f < 6; ++f) {
            if (t.fiat[f] > type(uint64).max) return WIDTH_FIAT;
        }
        return OK;
    }

    function require_(ContainModel.Terms memory t) internal pure {
        uint8 r = check(t);
        if (r != OK) revert TermsInvalid(r);
    }
}
