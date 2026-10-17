// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.24;

import {FastPayTypes as T} from "../generated/FastPayTypes.sol";
import "../Errors.sol";

/// Terms shape, containment (clauses K.1 to K.9 of document 12 section 5.3.2) and the widened mask of a revision (section 5.6), on the typed
/// `MandateTerms` of eip712/types.json. A cap or a fiat cap of 0 means "no cap in this family": E(0) is infinity. Price bounds are not in the
/// terms any more (ADR-020): clause K.6 asks for the same bounds version, and any other version counts as a widening in a revision.
library ContainLib {
    uint8 internal constant TOKEN_COUNT = 1; // the number of tokens is not in 1 .. MAX_TOKENS_PER_MANDATE
    uint8 internal constant TOKEN_ORDER = 2; // tokens are not non-zero and strictly ascending
    uint8 internal constant PERIOD_ZERO = 3; // periodSeconds is 0: no billing period, no window grid

    /// The canonical form of terms: the widths come from the ABI types, the rest is checked here. Reverts TermsInvalid(reason).
    function requireShape(T.MandateTerms calldata t) internal pure {
        uint256 n = t.tokens.length;
        if (n == 0 || n > T.MAX_TOKENS_PER_MANDATE) revert TermsInvalid(TOKEN_COUNT);
        // loop-bound: TOKENS | tokens.length <= MAX_TOKENS_PER_MANDATE | the line above reverts TermsInvalid above the bound
        for (uint256 i = 0; i < n; ++i) {
            address a = t.tokens[i].token;
            if (a == address(0) || (i > 0 && uint160(a) <= uint160(t.tokens[i - 1].token))) revert TermsInvalid(TOKEN_ORDER);
        }
        if (t.periodSeconds == 0) revert TermsInvalid(PERIOD_ZERO);
    }

    function indexOf(T.MandateTerms calldata t, address token) internal pure returns (uint256 idx, bool found) {
        // loop-bound: TOKENS | tokens.length <= MAX_TOKENS_PER_MANDATE | requireShape ran on these terms before they were stored or hashed into a mandate
        for (uint256 i = 0; i < t.tokens.length; ++i) {
            if (t.tokens[i].token == token) return (i, true);
        }
        return (0, false);
    }

    /// E(a) <= E(b), with 0 meaning infinity.
    function leE(uint256 a, uint256 b) internal pure returns (bool) {
        if (b == 0) return true;
        if (a == 0) return false;
        return a <= b;
    }

    /// x <= E(cap).
    function withinCap(uint256 x, uint256 cap) internal pure returns (bool) {
        return cap == 0 || x <= cap;
    }

    function lineageConstantsEqual(T.MandateTerms calldata a, T.MandateTerms calldata b) internal pure returns (bool) {
        return a.merchantId == b.merchantId && a.subscriptionRef == b.subscriptionRef && a.periodSeconds == b.periodSeconds
            && a.anchorStartsAt == b.anchorStartsAt && a.recipientPolicy == b.recipientPolicy && a.fiat.currency == b.fiat.currency;
    }

    function hasFiatCaps(T.FiatTerms calldata f) internal pure returns (bool) {
        return f.perPaymentMaxMinor != 0 || f.dayMaxMinor != 0 || f.weekMaxMinor != 0 || f.thirtyDayMaxMinor != 0 || f.periodMaxMinor != 0
            || f.totalMaxMinor != 0;
    }

    function _tokensSubset(T.MandateTerms calldata succ, T.MandateTerms calldata snap) private pure returns (bool) {
        // loop-bound: TOKENS | tokens.length <= MAX_TOKENS_PER_MANDATE | requireShape ran on both terms before they were stored or hashed
        for (uint256 i = 0; i < succ.tokens.length; ++i) {
            (, bool found) = indexOf(snap, succ.tokens[i].token);
            if (!found) return false;
        }
        return true;
    }

    function _tokenCapsLe(T.TokenTerms calldata a, T.TokenTerms calldata b) private pure returns (bool) {
        return leE(a.perPaymentMax, b.perPaymentMax) && leE(a.dayMax, b.dayMax) && leE(a.weekMax, b.weekMax)
            && leE(a.thirtyDayMax, b.thirtyDayMax) && leE(a.periodMax, b.periodMax) && leE(a.totalMax, b.totalMax);
    }

    function _capsViolated(T.MandateTerms calldata succ, T.MandateTerms calldata snap) private pure returns (bool) {
        // loop-bound: TOKENS | tokens.length <= MAX_TOKENS_PER_MANDATE | requireShape ran on both terms before they were stored or hashed
        for (uint256 i = 0; i < succ.tokens.length; ++i) {
            (uint256 j, bool found) = indexOf(snap, succ.tokens[i].token);
            if (found && !_tokenCapsLe(succ.tokens[i], snap.tokens[j])) return true;
        }
        return false;
    }

    function _fiatCapsLe(T.FiatTerms calldata a, T.FiatTerms calldata b) private pure returns (bool) {
        return leE(a.perPaymentMaxMinor, b.perPaymentMaxMinor) && leE(a.dayMaxMinor, b.dayMaxMinor) && leE(a.weekMaxMinor, b.weekMaxMinor)
            && leE(a.thirtyDayMaxMinor, b.thirtyDayMaxMinor) && leE(a.periodMaxMinor, b.periodMaxMinor) && leE(a.totalMaxMinor, b.totalMaxMinor);
    }

    /// Containment of a migration successor in the terms of its predecessor: bit k-1 of the result is set when clause K.k is violated.
    function containedMask(T.MandateTerms calldata succ, T.MandateTerms calldata snap) internal pure returns (uint256 m) {
        if (succ.expiresAt > snap.expiresAt) m |= 1; // K.1
        if (
            succ.merchantId != snap.merchantId || succ.recipientPolicy != snap.recipientPolicy || succ.subscriptionRef != snap.subscriptionRef
                || succ.periodSeconds != snap.periodSeconds || succ.anchorStartsAt != snap.anchorStartsAt
        ) m |= 1 << 1; // K.2
        if (!_tokensSubset(succ, snap)) m |= 1 << 2; // K.3
        if (_capsViolated(succ, snap)) m |= 1 << 3; // K.4
        if (succ.fiat.currency != snap.fiat.currency || succ.fiat.maxQuoteAge > snap.fiat.maxQuoteAge || !_fiatCapsLe(succ.fiat, snap.fiat)) {
            m |= 1 << 4; // K.5
        }
        if (succ.fiat.boundsVersion != snap.fiat.boundsVersion) m |= 1 << 5; // K.6 (ADR-020)
        if (!leE(succ.maxChargesPerPeriod, snap.maxChargesPerPeriod) || succ.minIntervalSeconds < snap.minIntervalSeconds) m |= 1 << 6; // K.7
        if (succ.maxFeeBps > snap.maxFeeBps) m |= 1 << 7; // K.8
        if (succ.extensionsHash != bytes32(0) || snap.extensionsHash != bytes32(0)) m |= 1 << 8; // K.9
    }

    /// widenedMask of a revision (document 12 section 5.6): which dimensions grow. Bits: 0 expiry later, 1 token added, 2 per-payment cap
    /// higher, 3 a window cap higher or removed, 4 total cap higher or removed, 5 fiat cap higher or removed, 6 quote age higher or the bounds
    /// version changed, 7 more charges per period or a shorter interval, 8 higher fee cap.
    function widenedMask(T.MandateTerms calldata n, T.MandateTerms calldata snap) internal pure returns (uint256 m) {
        if (n.expiresAt > snap.expiresAt) m |= 1;
        if (!_tokensSubset(n, snap)) m |= 1 << 1;
        // loop-bound: TOKENS | tokens.length <= MAX_TOKENS_PER_MANDATE | requireShape ran on both terms before they were stored or hashed
        for (uint256 i = 0; i < n.tokens.length; ++i) {
            (uint256 j, bool found) = indexOf(snap, n.tokens[i].token);
            if (!found) continue;
            T.TokenTerms calldata a = n.tokens[i];
            T.TokenTerms calldata b = snap.tokens[j];
            if (!leE(a.perPaymentMax, b.perPaymentMax)) m |= 1 << 2;
            if (!leE(a.dayMax, b.dayMax) || !leE(a.weekMax, b.weekMax) || !leE(a.thirtyDayMax, b.thirtyDayMax) || !leE(a.periodMax, b.periodMax)) {
                m |= 1 << 3;
            }
            if (!leE(a.totalMax, b.totalMax)) m |= 1 << 4;
        }
        if (!_fiatCapsLe(n.fiat, snap.fiat)) m |= 1 << 5;
        if (n.fiat.maxQuoteAge > snap.fiat.maxQuoteAge || n.fiat.boundsVersion != snap.fiat.boundsVersion) m |= 1 << 6;
        if (!leE(n.maxChargesPerPeriod, snap.maxChargesPerPeriod) || n.minIntervalSeconds < snap.minIntervalSeconds) m |= 1 << 7;
        if (n.maxFeeBps > snap.maxFeeBps) m |= 1 << 8;
    }
}
