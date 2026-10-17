// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.24;

import "./Errors.sol";
import "./Mutants.sol";

/// The time comparisons that are not part of a stateful model: the quote times Q9..Q12 (document 11 section 4.2), the window and
/// cycle grid (section 3.1, PC-16) and the batch limit (document 12 section 13). Mirrors protocol_model.quote_times_check,
/// window_index, cycle_allowed and batch_check. Arithmetic is checked: a negative difference is Panic(0x11), a zero length Panic(0x12).
library TimeModel {
    uint256 internal constant MAX_BATCH = 10; // PC-04, proposal (ADR-022: measured on the contracts)

    function quoteTimes(
        uint256 issuedAt,
        uint256 validAfter,
        uint256 validUntil,
        uint256 maxAge,
        uint256 registryTtl,
        uint256 nowTs,
        uint256 mutant
    ) internal pure {
        if (mutant != M_Q9_SKIP && !(issuedAt <= validAfter && validAfter <= validUntil)) revert QuoteTimesInvalid();
        bool notYet = mutant == M_Q10_STRICT ? validAfter >= nowTs : validAfter > nowTs;
        if (notYet) revert QuoteNotYetValid();
        bool expired = mutant == M_Q11_STRICT ? nowTs >= validUntil : nowTs > validUntil;
        if (expired) revert QuoteExpired();
        uint256 ttl = validUntil - issuedAt;
        uint256 limit = maxAge < registryTtl ? maxAge : registryTtl;
        bool tooLong = mutant == M_Q12_LT ? ttl >= limit : ttl > limit;
        if (tooLong) revert QuoteTtlTooLong();
    }

    /// floor((now - anchor) / length): the index of the window or billing cycle that contains `nowTs`.
    function windowIndex(uint256 nowTs, uint256 anchor, uint256 length, uint256 mutant) internal pure returns (uint256) {
        uint256 d = nowTs - anchor;
        if (mutant == M_WIN_OFFBYONE) d = d + 1;
        return d / length;
    }

    /// G9 and PC-16: cycleIndex <= floor((now - anchor) / periodSeconds); late cycles are allowed.
    function cycleAllowed(uint256 cycleIndex, uint256 nowTs, uint256 anchor, uint256 period, uint256 mutant) internal pure {
        uint256 cur = windowIndex(nowTs, anchor, period, mutant);
        bool tooEarly = mutant == M_CYC_LT ? cycleIndex >= cur : cycleIndex > cur;
        if (tooEarly) revert CycleNotYetDue();
    }

    function batchCheck(uint256 n, uint256 mutant) internal pure {
        bool tooLarge = mutant == M_BATCH_GE ? n >= MAX_BATCH : n > MAX_BATCH;
        if (tooLarge) revert BatchTooLarge();
    }
}
