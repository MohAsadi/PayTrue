// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.24;

import {FastPayTypes as T} from "./generated/FastPayTypes.sol";
import {IMandateManager} from "./interfaces/IMandateManager.sol";
import {ContainLib} from "./lib/ContainLib.sol";
import "./Errors.sol";

/// The usage counters of a lineage (document 11 sections 3 to 5): the per-token and the fiat usage in the four windows and in total, the
/// settled cycles, and the cadence (minimum interval, charges per billing period). Windows are DAY, WEEK, THIRTY_DAYS and BILLING_PERIOD
/// (PC-10), anchored at `anchorStartsAt`, and each counter is reset lazily when the index of its window moves.
///
/// This contract is the half of `consume` that owns the counters. Only the MandateManager can write here (an immutable address, the manager
/// calls it inside `consume` after its own guards), so a counter moves if and only if a charge was authorized by a live mandate in the same
/// transaction. It holds no tokens and makes no external call.
contract UsageLedger {
    uint256 internal constant DAY = 86_400;
    uint256 internal constant WEEK = 604_800;
    uint256 internal constant THIRTY_DAYS = 2_592_000;

    /// Usage of one family of caps: the total and the four windows, each with the index of the window that its counter belongs to.
    struct Use {
        uint128 total;
        uint128 day;
        uint128 week;
        uint128 thirty;
        uint128 period;
        uint64 dayIdx;
        uint64 weekIdx;
        uint64 thirtyIdx;
        uint64 periodIdx;
    }

    struct Cadence {
        uint64 lastChargeAt;
        uint64 periodIndex;
        uint32 chargesInPeriod;
    }

    address public immutable manager;

    mapping(bytes32 => mapping(address => Use)) internal tokenUse;
    mapping(bytes32 => Use) internal fiatUse;
    mapping(bytes32 => Cadence) public cadence;
    /// cycleRecord[lineageId][cycleIndex] is non-zero once the cycle settled: the digest of the quote that priced it, or 1 without a quote.
    mapping(bytes32 => mapping(uint256 => bytes32)) public cycleRecord;

    event Consumed(
        bytes32 indexed lineageId, bytes32 indexed mandateId, address indexed token, uint256 amount, uint256 cycleIndex, uint64 fiatValueMinor, bytes32 quoteDigest
    );

    constructor(address manager_) {
        manager = manager_;
    }

    /// G2 to G5, G9, the fee bound and the cadence, then the effects of step 7. The manager has already checked G1 (the mandate is live and
    /// consumable, the router is the bound one, the pin and the terms are the stored ones, `now >= anchorStartsAt`).
    function charge(bytes32 mandateId, bytes32 lineageId, T.MandateTerms calldata terms, IMandateManager.ChargeInput calldata c) external {
        if (msg.sender != manager) revert NotManager();
        uint256 el = block.timestamp - terms.anchorStartsAt;
        (uint256 idx, bool found) = ContainLib.indexOf(terms, c.token);
        if (!found) revert TokenNotInMandate();
        _cadence(lineageId, terms, c.cycleIndex, el);
        if (c.amount > type(uint128).max) revert AmountTooLarge();
        if (c.feeAmount * 10_000 > c.amount * terms.maxFeeBps) revert FeeTooHigh();
        T.TokenTerms calldata tt = terms.tokens[idx];
        _bump(tokenUse[lineageId][c.token], c.amount, el, terms.periodSeconds, _caps(tt), false);
        if (ContainLib.hasFiatCaps(terms.fiat)) {
            if (!c.hasFiat) revert FiatQuoteRequired();
            _bump(fiatUse[lineageId], c.fiatValueMinor, el, terms.periodSeconds, _fiatCaps(terms.fiat), true);
        }
        cycleRecord[lineageId][c.cycleIndex] = c.quoteDigest != bytes32(0) ? c.quoteDigest : bytes32(uint256(1));
        emit Consumed(lineageId, mandateId, c.token, c.amount, c.cycleIndex, c.fiatValueMinor, c.quoteDigest);
    }

    /// G9 (the cycle is not in the future and not settled) and the cadence rules.
    function _cadence(bytes32 lineageId, T.MandateTerms calldata terms, uint256 cycleIndex, uint256 el) internal {
        uint256 current = el / terms.periodSeconds;
        if (cycleIndex > current) revert CycleNotYetDue();
        if (cycleRecord[lineageId][cycleIndex] != bytes32(0)) revert PaymentAlreadySettled();
        Cadence storage k = cadence[lineageId];
        uint32 count = k.periodIndex == current ? k.chargesInPeriod : 0;
        if (terms.maxChargesPerPeriod != 0 && count >= terms.maxChargesPerPeriod) revert ChargesPerPeriodExceeded();
        if (k.lastChargeAt != 0 && block.timestamp - k.lastChargeAt < terms.minIntervalSeconds) revert ChargeTooSoon();
        k.periodIndex = uint64(current);
        k.chargesInPeriod = count + 1;
        k.lastChargeAt = uint64(block.timestamp);
    }

    function _caps(T.TokenTerms calldata t) private pure returns (uint256[6] memory c) {
        c = [t.perPaymentMax, t.dayMax, t.weekMax, t.thirtyDayMax, t.periodMax, t.totalMax];
    }

    function _fiatCaps(T.FiatTerms calldata f) private pure returns (uint256[6] memory c) {
        c = [uint256(f.perPaymentMaxMinor), f.dayMaxMinor, f.weekMaxMinor, f.thirtyDayMaxMinor, f.periodMaxMinor, f.totalMaxMinor];
    }

    /// One family: the per-payment cap, the four windows (lazy reset when the index moved) and the total. A cap of 0 means none.
    /// `fiat` only chooses which error is raised: token and fiat counters differ in nothing else.
    function _bump(Use storage u, uint256 amount, uint256 el, uint256 period, uint256[6] memory caps, bool fiat) internal {
        if (!ContainLib.withinCap(amount, caps[0])) _capFail(0, fiat);
        uint128 a = uint128(amount);
        (u.day, u.dayIdx) = _window(u.day, u.dayIdx, el / DAY, a, caps[1], fiat);
        (u.week, u.weekIdx) = _window(u.week, u.weekIdx, el / WEEK, a, caps[2], fiat);
        (u.thirty, u.thirtyIdx) = _window(u.thirty, u.thirtyIdx, el / THIRTY_DAYS, a, caps[3], fiat);
        (u.period, u.periodIdx) = _window(u.period, u.periodIdx, el / period, a, caps[4], fiat);
        u.total += a;
        if (!ContainLib.withinCap(u.total, caps[5])) _capFail(2, fiat);
    }

    /// The error of the cap that was exceeded: 0 per payment, 1 window, 2 total; the fiat family has its own names.
    function _capFail(uint8 kind, bool fiat) private pure {
        if (kind == 0) {
            if (fiat) revert FiatPerPaymentCapExceeded();
            revert TokenPerPaymentCapExceeded();
        }
        if (kind == 1) {
            if (fiat) revert FiatWindowCapExceeded();
            revert TokenWindowCapExceeded();
        }
        if (fiat) revert FiatTotalCapExceeded();
        revert TokenTotalCapExceeded();
    }

    function _window(uint128 used, uint64 storedIdx, uint256 idx, uint128 amount, uint256 cap, bool fiat) private pure returns (uint128, uint64) {
        if (storedIdx != idx) used = 0;
        used += amount;
        if (!ContainLib.withinCap(used, cap)) _capFail(1, fiat);
        return (used, uint64(idx));
    }

    function tokenUsage(bytes32 lineageId, address token) external view returns (Use memory) {
        return tokenUse[lineageId][token];
    }

    function fiatUsage(bytes32 lineageId) external view returns (Use memory) {
        return fiatUse[lineageId];
    }
}
