// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import "../src/Errors.sol";
import {RegistryModel} from "../src/RegistryModel.sol";
import {SignerSetModel} from "../src/SignerSetModel.sol";
import {MigrationModel} from "../src/MigrationModel.sol";
import {Permit2Mock} from "../src/Permit2Mock.sol";
import {HashModel} from "../src/HashModel.sol";
import {PinModel} from "../src/PinModel.sol";
import {TimeModel} from "../src/TimeModel.sol";
import {ContainModel} from "../src/ContainModel.sol";

contract ConfigTimeHarness {
    function cycleAllowed(uint256 cycleIndex, uint256 nowTs, uint256 anchor, uint256 period) external pure {
        TimeModel.cycleAllowed(cycleIndex, nowTs, anchor, period, 0);
    }
}

/// One test per production-blocking constant of document 16 section 7 (PC-01 ... PC-18): the proposed value lies in its safe range.
///
/// `// source: 16 §7` marks a value or range taken from the table of document 16 section 7. The table states a safe range only for
/// PC-08 (`[MAX_QUOTE_TTL, 2 * MAX_QUOTE_TTL]`) and PC-18 (`[MAX_TOKENS_PER_MANDATE, MAX_BATCH * MAX_TOKENS_PER_MANDATE]`) and a lower
/// bound for PC-17 (>= 48 hours). Every other range below is derived from a statement in documents 11, 12 or 17 (cited on the line) or is
/// an ASSUMPTION of the author of this file (marked `range: assumption`); the authoritative ranges will be those of
/// config/pc_records.json (document 18), which this file deliberately does not read. When that file is final, replace the assumptions.
///
/// The model contracts supply the value where they have it (notice, retention, rollback, router count, batch, exposure); the others are
/// the proposals of the table, written down once here.
contract ConfigRecordsTest is Test {
    // proposals of 16 §7 that no model contract carries
    uint256 internal constant MAX_QUOTE_TTL = 300; // source: 16 §7 PC-06
    uint256 internal constant QUOTE_SET_GRACE = 300; // source: 16 §7 PC-08
    uint256 internal constant MAX_BAND_WIDTH_BPS = 500; // source: 16 §7 PC-07
    uint256 internal constant DEFAULT_QUOTE_TTL = 120; // 11 §12 open point 3 (backend-tunable)
    uint256 internal constant TIMELOCK_MIN_DELAY = 72 hours; // source: 16 §7 PC-14
    uint256 internal constant MIN_RECIPIENT_CHANGE_DELAY = 48 hours; // source: 16 §7 PC-17
    uint256 internal constant DAY = 86_400; // source: 16 §7 PC-10
    uint256 internal constant WEEK = 604_800; // source: 16 §7 PC-10
    uint256 internal constant THIRTY_DAYS = 2_592_000; // source: 16 §7 PC-10
    uint256 internal constant MAX_TOKENS_PER_MANDATE = 3; // source: 16 §7 PC-11
    address internal constant PERMIT2 = address(uint160(0x00000000000022d473030f116ddee9f6b43ac78ba3)); // source: 16 §7 PC-13

    RegistryModel internal reg;
    MigrationModel internal mgr;
    ConfigTimeHarness internal th;

    function setUp() public {
        reg = new RegistryModel();
        mgr = new MigrationModel(new Permit2Mock(), reg);
        th = new ConfigTimeHarness();
    }

    function _within(uint256 value, uint256 lo, uint256 hi) internal pure returns (bool) {
        return lo <= value && value <= hi;
    }

    // PC-01
    function test_ConfigRange_MIN_NOTICE_STANDARD() public {
        uint256 v = reg.MIN_NOTICE_STANDARD(); // source: 16 §7 PC-01: 180 days
        assertEq(v, 180 days);
        // range: lower bound 150 days (the reminder schedule of 12 §11.1 starts at S - 150); upper bound 365 days is an assumption
        assertTrue(_within(v, 150 days, 365 days), "MIN_NOTICE_STANDARD outside its safe range");
    }

    // PC-02
    function test_ConfigRange_MIN_NOTICE_SECURITY() public {
        uint256 v = reg.MIN_NOTICE_SECURITY(); // source: 16 §7 PC-02: 60 days
        assertEq(v, 60 days);
        // range: lower bound 30 days (the compressed schedule of 12 §11.1 ends with reminders at S - 30); upper bound: not longer than standard
        assertTrue(_within(v, 30 days, reg.MIN_NOTICE_STANDARD()), "MIN_NOTICE_SECURITY outside its safe range");
    }

    // PC-03
    function test_ConfigRange_RETENTION() public {
        uint256 v = reg.RETENTION(); // source: 16 §7 PC-03: 365 days
        assertEq(v, 365 days);
        assertTrue(_within(v, 90 days, 730 days), "RETENTION outside its safe range"); // range: assumption
    }

    // PC-04
    function test_ConfigRange_MAX_BATCH() public {
        uint256 v = TimeModel.MAX_BATCH; // source: 16 §7 PC-04: 10 (ADR-022: measured on the contracts, contracts/test/Gas.t.sol)
        assertEq(v, 10);
        assertTrue(_within(v, 4, 20), "MAX_BATCH outside its safe range"); // range: [4, 20], mine; the chains are not measured (RP-19)
        assertEq(mgr.MAX_EXPOSED_TOKENS_PER_ROUTER() <= v * MAX_TOKENS_PER_MANDATE, true, "PC-18 upper bound uses PC-04");
    }

    // PC-05
    function test_ConfigRange_FEE_CEILING_BPS() public {
        // source: 16 §7 PC-05: "to be set by Finance": there is no proposal. Only the physical range is asserted: a basis-point cap fits
        // the model's uint16 field and 10,000 bps (100 percent) is representable.
        ContainModel.Terms memory t;
        t.maxFeeBps = 10_000;
        assertEq(uint256(t.maxFeeBps), 10_000);
        assertTrue(type(uint16).max >= 10_000);
    }

    // PC-06
    function test_ConfigRange_MAX_QUOTE_TTL() public {
        // source: 16 §7 PC-06: 300 seconds; range: lower bound = the default quote TTL of 120 s (11 §12 point 3), upper bound assumption
        assertTrue(_within(MAX_QUOTE_TTL, DEFAULT_QUOTE_TTL, 900), "MAX_QUOTE_TTL outside its safe range");
    }

    // PC-07
    function test_ConfigRange_MAX_BAND_WIDTH_BPS() public {
        // source: 16 §7 PC-07: 500 bps; range: lower bound = the widest band of the vectors (CAP-TV-01: 0.98 to 1.02 is 400 bps), upper 1000 (assumption)
        uint256 capTv01 = (102 - 98) * 10_000 / 100;
        uint256 capTv03 = (101 - 99) * 10_000 / 100;
        assertEq(capTv01, 400);
        assertEq(capTv03, 200);
        assertTrue(_within(MAX_BAND_WIDTH_BPS, capTv01, 1000), "MAX_BAND_WIDTH_BPS outside its safe range");
    }

    // PC-08
    function test_ConfigRange_QUOTE_SET_GRACE() public {
        // source: 16 §7 PC-08: 300 seconds, safe range [MAX_QUOTE_TTL, 2 * MAX_QUOTE_TTL] (stated)
        assertTrue(_within(QUOTE_SET_GRACE, MAX_QUOTE_TTL, 2 * MAX_QUOTE_TTL), "QUOTE_SET_GRACE outside [MAX_QUOTE_TTL, 2 * MAX_QUOTE_TTL]");
        assertEq(new SignerSetModel(QUOTE_SET_GRACE).grace(), QUOTE_SET_GRACE);
    }

    // PC-09
    function test_ConfigRange_EIP712_NAMES_TAGS_AND_TYPES() public {
        // source: 16 §7 PC-09: the hash tags and the type strings are fixed forever; the exact values are in test/generated/GenHashVectors.t.sol
        assertEq(HashModel.LINEAGE_TAG, keccak256("fastpay.lineage.v1"));
        assertEq(HashModel.MANDATE_TAG, keccak256("fastpay.mandate.v1"));
        assertEq(HashModel.CYCLE_TAG, keccak256("fastpay.cycle.v1"));
        assertEq(HashModel.ROUTE_DIRECT_TAG, keccak256("fastpay.route.direct.v1"));
        assertEq(PinModel.PIN_EOA, keccak256("fastpay.pin.eoa.v1"));
        assertEq(ContainModel.SNAPSHOT_TAG, keccak256("fastpay.migration.snapshot.v1"));
        // the domain of the quote is "FastPay Quote" version "1": a different name or version gives a different separator
        address router = address(uint160(0x1111));
        bytes32 ds = HashModel.domainSeparator("FastPay Quote", "1", 84532, router);
        assertTrue(ds != HashModel.domainSeparator("FastPay Quote", "2", 84532, router));
        assertTrue(ds != HashModel.domainSeparator("FastPay Mandates", "1", 84532, router));
    }

    // PC-10
    function test_ConfigRange_WINDOW_LENGTHS() public {
        // source: 16 §7 PC-10: DAY 86,400 s, WEEK 604,800 s, THIRTY_DAYS 2,592,000 s (exact values; the relations are the safe range)
        assertEq(DAY, 1 days);
        assertEq(WEEK, 7 * DAY);
        assertEq(THIRTY_DAYS, 30 * DAY);
    }

    // PC-11
    function test_ConfigRange_MAX_TOKENS_PER_MANDATE() public {
        ContainModel.Terms memory t;
        assertEq(t.tokens.length, MAX_TOKENS_PER_MANDATE, "the array bound of the model is PC-11"); // source: 16 §7 PC-11: 3
        assertTrue(_within(MAX_TOKENS_PER_MANDATE, 1, 8), "MAX_TOKENS_PER_MANDATE outside its safe range"); // range: assumption
    }

    // PC-12
    function test_ConfigRange_MAX_ROUTERS_LIVE() public {
        // source: 16 §7 PC-12: 2; 12 §13: at most two routers ACTIVE or DEPRECATED per chain, and a migration needs two
        assertEq(reg.MAX_LIVE_ROUTERS(), 2);
        assertTrue(_within(reg.MAX_LIVE_ROUTERS(), 2, 2));
    }

    // PC-13
    function test_ConfigRange_PERMIT2_ADDRESS() public {
        // source: 16 §7 PC-13: the canonical address 0x000000000022D473030F116dDEE9F6B43aC78BA3 (the vanity prefix is 40 zero bits)
        assertEq(uint256(uint160(PERMIT2)) >> 120, 0);
        assertEq(uint256(uint160(PERMIT2)), uint256(0x22d473030f116ddee9f6b43ac78ba3));
    }

    // PC-14
    function test_ConfigRange_TIMELOCK_MIN_DELAY_AND_GUARDIAN() public {
        // source: 16 §7 PC-14: 72 h, stop-only guardian; range: lower bound 72 h (11 §4.7 KR-9, "72 h minimum"), upper 14 days (assumption)
        assertTrue(_within(TIMELOCK_MIN_DELAY, 72 hours, 14 days), "timelock delay outside its safe range");
        SignerSetModel ss = new SignerSetModel(QUOTE_SET_GRACE);
        address[] memory m = new address[](1);
        m[0] = address(uint160(0x9001));
        vm.expectRevert(NotGovernance.selector);
        ss.proposeSignerSet(1, 1, m, 0); // the guardian cannot add a set
        ss.removeQuoteSigner(1, m[0]); // but it can stop (remove) a key
    }

    // PC-15
    function test_ConfigRange_PIN_EOA_AND_KECCAK_EMPTY() public {
        // source: 16 §7 PC-15 and 17 §5.1: PIN_EOA accepts exactly the two encodings of "no code" (0 and KECCAK_EMPTY)
        PinModel.Pin memory p = PinModel.Pin(1, PinModel.PIN_EOA, address(0), bytes32(0), bytes32(0), 1, 1);
        assertTrue(PinModel.pinOk(p, bytes32(0), bytes32(0), 0));
        assertTrue(PinModel.pinOk(p, PinModel.KECCAK_EMPTY, bytes32(0), 0));
        assertFalse(PinModel.pinOk(p, bytes32(uint256(1)), bytes32(0), 0));
        assertFalse(PinModel.pinOk(p, PinModel.PIN_EOA, bytes32(0), 0));
        assertEq(PinModel.KECCAK_EMPTY, keccak256(""));
    }

    // PC-16
    function test_ConfigRange_CYCLE_RULE() public {
        // source: 16 §7 PC-16: cycleIndex <= floor((t - anchor) / periodSeconds), late cycles allowed
        uint256 anchor = 1_800_000_000;
        th.cycleAllowed(0, anchor, anchor, THIRTY_DAYS);
        vm.expectRevert(CycleNotYetDue.selector);
        th.cycleAllowed(1, anchor + THIRTY_DAYS - 1, anchor, THIRTY_DAYS);
        th.cycleAllowed(1, anchor + THIRTY_DAYS, anchor, THIRTY_DAYS);
        th.cycleAllowed(0, anchor + 5 * THIRTY_DAYS, anchor, THIRTY_DAYS);
    }

    // PC-17
    function test_ConfigRange_MIN_RECIPIENT_CHANGE_DELAY() public {
        // source: 16 §7 PC-17: at least 48 hours (stated lower bound); upper bound 30 days is an assumption
        assertTrue(_within(MIN_RECIPIENT_CHANGE_DELAY, 48 hours, 30 days), "recipient-change delay outside its safe range");
    }

    // PC-18
    function test_ConfigRange_MAX_EXPOSED_TOKENS_PER_ROUTER() public {
        uint256 v = mgr.MAX_EXPOSED_TOKENS_PER_ROUTER(); // source: 16 §7 PC-18: 8
        assertEq(v, 8);
        // source: 16 §7 PC-18: safe range [MAX_TOKENS_PER_MANDATE, MAX_BATCH * MAX_TOKENS_PER_MANDATE] (stated)
        assertTrue(_within(v, MAX_TOKENS_PER_MANDATE, TimeModel.MAX_BATCH * MAX_TOKENS_PER_MANDATE), "PC-18 outside its safe range");
    }

    // PC-19
    function test_ConfigRange_MAX_SIGNERS_PER_SET() public {
        uint256 v = new SignerSetModel(QUOTE_SET_GRACE).MAX_SIGNERS_PER_SET(); // proposal: 16 (the record PC-19, new in the implementation evidence)
        assertEq(v, 16);
        assertTrue(_within(v, 2, 64), "PC-19 outside its safe range"); // range [2, 64]: mine
    }
}
