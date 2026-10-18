// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import {Base} from "./helpers/Base.sol";
import {MockERC20} from "./helpers/MockERC20.sol";
import {PaymentRouter} from "../src/PaymentRouter.sol";
import {ContainHarness} from "./helpers/ContainHarness.sol";
import "../src/Errors.sol";
import {FastPayTypes as T} from "../src/generated/FastPayTypes.sol";

/// Differential tests: the ACTUAL contracts' libraries against the reference model's exported vectors (spec/foundry/vectors, produced by the
/// Python model tools/protocol_model.py and replayed on the Solidity reference model by spec/foundry/test). A pass here says that the
/// contract code and the model agree on those vectors; it says nothing about vectors that the model does not contain.
contract DifferentialTest is Test {
    ContainHarness h;

    uint256 constant TUPLE = 117; // flags, expectedMask, succAccepts, predAccepts, succ terms (41), pred terms (41), state (21), payment (10)
    uint256 constant SUCC_AT = 4;
    uint256 constant PRED_AT = 45;

    function setUp() public {
        h = new ContainHarness();
    }

    /// The model's 41-word terms, as the typed struct of the generated library (typed order of the caps).
    function _typed(uint256[] memory w, uint256 o) internal pure returns (T.MandateTerms memory t) {
        t.expiresAt = uint64(w[o]);
        t.merchantId = bytes32(w[o + 1]);
        t.recipientPolicy = bytes32(w[o + 2]);
        t.subscriptionRef = bytes32(w[o + 3]);
        t.periodSeconds = uint64(w[o + 4]);
        t.anchorStartsAt = uint64(w[o + 5]);
        uint256 n = w[o + 7];
        t.tokens = new T.TokenTerms[](n);
        for (uint256 i = 0; i < n; ++i) {
            uint256 b = o + 11 + 6 * i;
            t.tokens[i] = T.TokenTerms({
                token: address(uint160(w[o + 8 + i])),
                perPaymentMax: w[b],
                dayMax: w[b + 2],
                weekMax: w[b + 3],
                thirtyDayMax: w[b + 4],
                periodMax: w[b + 5],
                totalMax: w[b + 1]
            });
        }
        t.fiat = T.FiatTerms({
            currency: uint16(w[o + 6]),
            perPaymentMaxMinor: uint64(w[o + 29]),
            dayMaxMinor: uint64(w[o + 31]),
            weekMaxMinor: uint64(w[o + 32]),
            thirtyDayMaxMinor: uint64(w[o + 33]),
            periodMaxMinor: uint64(w[o + 34]),
            totalMaxMinor: uint64(w[o + 30]),
            maxQuoteAge: uint32(w[o + 35]),
            boundsVersion: uint32(w[o + 36])
        });
        t.maxChargesPerPeriod = uint16(w[o + 37]);
        t.minIntervalSeconds = uint32(w[o + 38]);
        t.maxFeeBps = uint16(w[o + 39]);
        t.extensionsHash = bytes32(w[o + 40]);
    }

    function test_Containment_MaskEqualsTheModel_OnEveryExportedTuple() public view {
        string memory json = vm.readFile("../spec/foundry/vectors/containment.json");
        uint256[] memory flat = vm.parseJsonUintArray(json, ".flat");
        uint256 n = flat.length / TUPLE;
        assertGt(n, 700, "the exported suite has 742 tuples");
        uint256 differing;
        for (uint256 i = 0; i < n; ++i) {
            uint256 base = i * TUPLE;
            T.MandateTerms memory succ = _typed(flat, base + SUCC_AT);
            T.MandateTerms memory pred = _typed(flat, base + PRED_AT);
            uint256 got = h.contained(succ, pred);
            if (got != flat[base + 1]) differing++;
        }
        assertEq(differing, 0, "the contract's containedMask differs from the model's on some tuple");
    }

    function test_TermsHashes_AndSnapshots_EqualThePythonModel() public view {
        string memory json = vm.readFile("../spec/foundry/vectors/hashes.json");
        uint256 n;
        for (; n < 64; ++n) {
            if (!vm.keyExistsJson(json, string.concat(".termsHashes[", vm.toString(n), "]"))) break;
        }
        assertGe(n, 9, "TH_00 to TH_08");
        for (uint256 i = 0; i < n; ++i) {
            string memory p = string.concat(".termsHashes[", vm.toString(i), "]");
            string[] memory ws = vm.parseJsonStringArray(json, string.concat(p, ".words"));
            uint256[] memory w = new uint256[](ws.length);
            for (uint256 k = 0; k < ws.length; ++k) {
                w[k] = vm.parseUint(ws[k]);
            }
            assertEq(w.length, 41);
            T.MandateTerms memory t = _typed(w, 0);
            assertEq(T.hashStruct(t), vm.parseJsonBytes32(json, string.concat(p, ".termsHash")), string.concat("termsHash ", vm.toString(i)));
            bytes32 snap = T.snapshotHash(
                vm.parseJsonBytes32(json, string.concat(p, ".lineageId")),
                vm.parseJsonBytes32(json, string.concat(p, ".predecessorId")),
                uint32(vm.parseJsonUint(json, string.concat(p, ".generation"))),
                vm.parseJsonAddress(json, string.concat(p, ".customer")),
                t
            );
            assertEq(snap, vm.parseJsonBytes32(json, string.concat(p, ".snapshotHash")), string.concat("snapshotHash ", vm.toString(i)));
        }
    }
}

/// The fiat valuation of the model's vectors (document 11 section 4.1, CAP-TV-01..03), run through the ACTUAL router and ledger: a real quote, a
/// real charge, and the fiat usage that the ledger records. Vectors whose result does not fit the contract's widths are refused, with the error of
/// the width that they break.
contract FiatVectorsTest is Base {
    function test_Fiat_EveryVectorThroughTheRouter() public {
        string memory json = vm.readFile("../spec/foundry/vectors/hashes.json");
        uint256 n;
        for (; n < 64; ++n) {
            if (!vm.keyExistsJson(json, string.concat(".fiat[", vm.toString(n), "]"))) break;
        }
        assertGe(n, 10);
        uint256 charged;
        uint256 refused;
        for (uint256 i = 0; i < n; ++i) {
            string memory p = string.concat(".fiat[", vm.toString(i), "]");
            Vec memory v = Vec(
                i,
                vm.parseJsonUint(json, string.concat(p, ".amountIn")),
                vm.parseJsonUint(json, string.concat(p, ".priceE18")),
                uint8(vm.parseJsonUint(json, string.concat(p, ".tokenDecimals"))),
                vm.parseJsonUint(json, string.concat(p, ".fiatValueMinor"))
            );
            if (_one(v)) charged++;
            else refused++;
        }
        emit log_named_uint("vectors charged through the router", charged);
        emit log_named_uint("vectors refused for their width", refused);
        assertGe(charged, 7);
    }

    /// Terms for one token with no token caps and one fiat cap that never binds, pinned to bounds version 1 of that token.
    function _vectorTerms(address tk) internal view returns (T.MandateTerms memory t) {
        t = _terms(tk);
        t.tokens[0] = T.TokenTerms(tk, 0, 0, 0, 0, 0, 0);
        t.fiat = T.FiatTerms(USD, 0, 0, 0, 0, 0, type(uint64).max, 120, 1);
        t.minIntervalSeconds = 0;
        t.maxChargesPerPeriod = 0;
    }

    struct Vec {
        uint256 i;
        uint256 amount;
        uint256 price;
        uint8 decimals;
        uint256 expected;
    }

    function _list(Vec memory v) internal returns (MockERC20 tk) {
        tk = new MockERC20();
        vm.startPrank(gov);
        policy.list(address(tk), 1, v.decimals);
        policy.setPriceSourceSet(address(tk), USD, SOURCE_SET);
        policy.publishBounds(address(tk), USD, v.price, v.price); // a band of one price: its width is 0, inside PC-07
        vm.stopPrank();
        vm.prank(merchantAdmin);
        merchantReg.setAccepted(MERCHANT, address(tk), true);
    }

    /// The customer leaves the mandate, so that the next vector does not meet the bound of eight tokens per router.
    function _leave(bytes32 mid) internal {
        vm.prank(customer);
        manager.revoke(customer, mid);
    }

    function _one(Vec memory v) internal returns (bool) {
        MockERC20 tk = _list(v);
        T.MandateTerms memory t = _vectorTerms(address(tk));
        (bytes32 lid, bytes32 mid) = _activate(customer, v.i + 1, address(routerA), t, _pin());
        bool fits = v.amount <= type(uint128).max && v.expected <= type(uint64).max;
        if (fits) {
            tk.mint(customer, v.amount);
            vm.prank(customer);
            tk.approve(CANONICAL, type(uint256).max);
            _grant(customer, tk, address(routerA), uint160(v.amount > type(uint160).max ? type(uint160).max : v.amount));
        }
        PaymentRouter.QuoteBundle memory q = _quote(routerA, lid, 0, customer, address(tk), v.amount, v.price);
        if (!fits) {
            vm.expectRevert();
            _charge(routerA, mid, t, _pin(), 0, address(tk), v.amount, 0, q);
            _leave(mid);
            return false;
        }
        _charge(routerA, mid, t, _pin(), 0, address(tk), v.amount, 0, q);
        assertEq(ledger.fiatUsage(lid).total, v.expected, string.concat("fiat value of vector ", vm.toString(v.i)));
        _leave(mid);
        return true;
    }
}
