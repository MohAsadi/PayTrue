// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import "../src/Errors.sol";
import {ContainModel, TermsShape} from "../src/ContainModel.sol";
import {MigrationModel} from "../src/MigrationModel.sol";
import {FastPayTypes} from "../src/generated/FastPayTypes.sol";
import {Fixture} from "./helpers/Fixture.sol";

/// Findings F-06, F-07 and the decision on `newTermsHash` (document 12 section 5.3.2 and predicate A3).
///
/// The reference model hashes its own terms in two ways: `ContainModel.snapshotHash` writes the 26 words of eip712/types.json
/// snapshotEncoding out by hand (customer, anchorStartsAt and boundsVersion covered, the caps in the typed order), and
/// `ContainModel.termsHash` is hashStruct(MandateTerms) of the generated library applied to the converted terms. Here the same terms are
/// built both ways, the model way and the generated-library way (a converter written in this file, not `ContainModel.toTyped`), and the
/// hashes must be equal for random terms. The exported Python expectations are checked in GenHashVectors.t.sol (test_TermsHashes_TH_xx);
/// the last test checks that the manager hands the right arguments (lineage, predecessor, generation, customer) to the hash.
contract TermsHashParityTest is Test {
    Fixture internal fx;

    function setUp() public {
        vm.warp(1_800_000_000);
        fx = new Fixture();
    }

    // ------------------------------------------------------------------------------------------------------------ generators
    function _r(uint256 seed, uint256 i) internal pure returns (uint256) {
        return uint256(keccak256(abi.encode(seed, i)));
    }

    /// Random terms with every field inside the documented width of the typed data (TermsShape.OK), including the extreme values.
    function _terms(uint256 seed) internal pure returns (ContainModel.Terms memory t) {
        t.expiresAt = uint64(_r(seed, 1));
        t.periodSeconds = uint64(_r(seed, 2));
        t.anchorStartsAt = uint64(_r(seed, 3));
        t.maxQuoteAge = uint64(uint32(_r(seed, 4)));
        t.minInterval = uint64(uint32(_r(seed, 5)));
        t.maxChargesPerPeriod = uint32(uint16(_r(seed, 6)));
        t.currency = uint16(_r(seed, 7));
        t.maxFeeBps = uint16(_r(seed, 8));
        t.boundsVersion = uint32(_r(seed, 9));
        t.merchantId = bytes32(_r(seed, 10));
        t.recipientPolicy = bytes32(_r(seed, 11));
        t.subscriptionRef = bytes32(_r(seed, 12));
        t.extensionsHash = _r(seed, 13) % 3 == 0 ? bytes32(_r(seed, 14)) : bytes32(0);
        uint256 n = 1 + _r(seed, 15) % 3;
        t.nTokens = uint8(n);
        uint256 next = 1 + _r(seed, 16) % 1000;
        for (uint256 i = 0; i < n; ++i) {
            t.tokens[i] = address(uint160(next));
            next += 1 + _r(seed, 20 + i) % 1000;
            for (uint256 f = 0; f < 6; ++f) {
                uint256 r = _r(seed, 100 + 10 * i + f);
                t.caps[i][f] = r % 4 == 0 ? 0 : (r % 4 == 1 ? type(uint256).max - (r >> 8) % 1000 : r);
            }
        }
        for (uint256 g = 0; g < 6; ++g) {
            uint256 r = _r(seed, 40 + g);
            t.fiat[g] = r % 4 == 0 ? 0 : uint256(uint64(r));
        }
        assertEq(uint256(TermsShape.check(t)), uint256(TermsShape.OK), "the generator stays inside the documented widths");
    }

    /// The generated-library form of the model terms, written independently of ContainModel.toTyped (plain casts: every value is in range).
    function _typed(ContainModel.Terms memory t) internal pure returns (FastPayTypes.MandateTerms memory m) {
        m.merchantId = t.merchantId;
        m.recipientPolicy = t.recipientPolicy;
        m.subscriptionRef = t.subscriptionRef;
        m.periodSeconds = t.periodSeconds;
        m.anchorStartsAt = t.anchorStartsAt;
        m.expiresAt = t.expiresAt;
        m.tokens = new FastPayTypes.TokenTerms[](t.nTokens);
        for (uint256 i = 0; i < t.nTokens; ++i) {
            m.tokens[i].token = t.tokens[i];
            m.tokens[i].perPaymentMax = t.caps[i][0]; // the model order is perPayment, total, day, week, thirtyDay, period
            m.tokens[i].dayMax = t.caps[i][2];
            m.tokens[i].weekMax = t.caps[i][3];
            m.tokens[i].thirtyDayMax = t.caps[i][4];
            m.tokens[i].periodMax = t.caps[i][5];
            m.tokens[i].totalMax = t.caps[i][1];
        }
        m.fiat.currency = t.currency;
        m.fiat.perPaymentMaxMinor = uint64(t.fiat[0]);
        m.fiat.dayMaxMinor = uint64(t.fiat[2]);
        m.fiat.weekMaxMinor = uint64(t.fiat[3]);
        m.fiat.thirtyDayMaxMinor = uint64(t.fiat[4]);
        m.fiat.periodMaxMinor = uint64(t.fiat[5]);
        m.fiat.totalMaxMinor = uint64(t.fiat[1]);
        m.fiat.maxQuoteAge = uint32(t.maxQuoteAge);
        m.fiat.boundsVersion = t.boundsVersion;
        m.maxChargesPerPeriod = uint16(t.maxChargesPerPeriod);
        m.minIntervalSeconds = uint32(t.minInterval);
        m.maxFeeBps = t.maxFeeBps;
        m.extensionsHash = t.extensionsHash;
    }

    // ------------------------------------------------------------------------------------------------------------ the two hashes, both ways
    /// The model's snapshot hash equals FastPayTypes.snapshotHash of the same terms, and the model's terms hash equals
    /// FastPayTypes.hashStruct(MandateTerms), for random terms, ids, generation and customer.
    function testFuzz_ModelHashesEqualTheGeneratedLibrary(uint256 seed, bytes32 lineage, bytes32 predecessor, uint32 generation, address customer)
        public
    {
        ContainModel.Terms memory t = _terms(seed);
        FastPayTypes.MandateTerms memory typed = _typed(t);
        assertEq(
            ContainModel.snapshotHash(lineage, predecessor, generation, customer, t),
            FastPayTypes.snapshotHash(lineage, predecessor, generation, customer, typed),
            "termsSnapshotHash: the model and the generated library hash the same 26 words"
        );
        assertEq(ContainModel.termsHash(t), FastPayTypes.hashStruct(typed), "newTermsHash is hashStruct(MandateTerms)");
        assertEq(FastPayTypes.hashStruct(ContainModel.toTyped(t)), FastPayTypes.hashStruct(typed), "the model's converter equals the one of this test");
        assertEq(
            FastPayTypes.snapshotHash(lineage, predecessor, generation, customer, ContainModel.toTyped(t)),
            FastPayTypes.snapshotHash(lineage, predecessor, generation, customer, typed)
        );
    }

    /// The customer, anchorStartsAt and boundsVersion are covered by the snapshot hash (F-06); the terms hash covers the terms and no id.
    function testFuzz_SnapshotCoversWhatTheDocumentLists(uint256 seed, bytes32 lineage, bytes32 predecessor, uint32 generation, address customer) public {
        ContainModel.Terms memory t = _terms(seed);
        bytes32 base = ContainModel.snapshotHash(lineage, predecessor, generation, customer, t);
        assertTrue(ContainModel.snapshotHash(lineage, predecessor, generation, address(uint160(customer) ^ 1), t) != base, "customer");
        assertTrue(ContainModel.snapshotHash(lineage, predecessor, uint256(generation) + 1, customer, t) != base, "generation");
        assertTrue(ContainModel.snapshotHash(lineage, predecessor ^ bytes32(uint256(1)), generation, customer, t) != base, "predecessorId");
        assertTrue(ContainModel.snapshotHash(lineage ^ bytes32(uint256(1)), predecessor, generation, customer, t) != base, "lineageId");
        bytes32 termsBase = ContainModel.termsHash(t);
        t.anchorStartsAt = t.anchorStartsAt ^ 1;
        assertTrue(ContainModel.snapshotHash(lineage, predecessor, generation, customer, t) != base, "anchorStartsAt");
        assertTrue(ContainModel.termsHash(t) != termsBase, "anchorStartsAt (terms hash)");
        t.anchorStartsAt = t.anchorStartsAt ^ 1;
        t.boundsVersion = t.boundsVersion ^ 1;
        assertTrue(ContainModel.snapshotHash(lineage, predecessor, generation, customer, t) != base, "boundsVersion");
        assertTrue(ContainModel.termsHash(t) != termsBase, "boundsVersion (terms hash)");
        t.boundsVersion = t.boundsVersion ^ 1;
        assertEq(ContainModel.snapshotHash(lineage, predecessor, generation, customer, t), base);
        assertEq(ContainModel.termsHash(t), termsBase);
    }

    /// The order of the caps follows the typed data: the day cap and the total cap are different words in different places.
    function test_CapOrderIsTheTypedOrder() public {
        ContainModel.Terms memory a = _terms(11);
        ContainModel.Terms memory b = _terms(11);
        (a.caps[0][1], a.caps[0][2]) = (1111, 2222); // total, day
        (b.caps[0][1], b.caps[0][2]) = (2222, 1111);
        assertTrue(ContainModel.snapshotHash(0, 0, 0, address(0), a) != ContainModel.snapshotHash(0, 0, 0, address(0), b));
        assertEq(FastPayTypes.hashStruct(ContainModel.toTyped(a)), FastPayTypes.hashStruct(_typed(a)));
        assertEq(ContainModel.toTyped(a).tokens[0].totalMax, 1111);
        assertEq(ContainModel.toTyped(a).tokens[0].dayMax, 2222);
        // fiat: total = fiat[1], day = fiat[2]
        (a.fiat[1], a.fiat[2]) = (7, 9);
        assertEq(uint256(ContainModel.toTyped(a).fiat.totalMaxMinor), 7);
        assertEq(uint256(ContainModel.toTyped(a).fiat.dayMaxMinor), 9);
    }

    /// The converter never narrows silently: a value above the documented width of the typed data reverts (TermsShape refuses it earlier).
    function callToTyped(ContainModel.Terms memory t) external pure returns (bytes32) {
        return ContainModel.termsHash(t);
    }

    function test_ConversionRefusesAboveTheTypedWidth() public {
        ContainModel.Terms memory t = _terms(5);
        this.callToTyped(t);
        t.maxChargesPerPeriod = uint32(type(uint16).max) + 1;
        vm.expectRevert(UnsafeCast.selector);
        this.callToTyped(t);
        t = _terms(5);
        t.maxQuoteAge = uint64(type(uint32).max) + 1;
        vm.expectRevert(UnsafeCast.selector);
        this.callToTyped(t);
        t = _terms(5);
        t.minInterval = uint64(type(uint32).max) + 1;
        vm.expectRevert(UnsafeCast.selector);
        this.callToTyped(t);
        t = _terms(5);
        t.fiat[3] = uint256(type(uint64).max) + 1;
        vm.expectRevert(UnsafeCast.selector);
        this.callToTyped(t);
    }

    // ------------------------------------------------------------------------------------------------------------ the manager hands the right arguments
    /// buildAuth: termsSnapshotHash is the snapshot hash of the PREDECESSOR with its own lineage, predecessor, generation and customer;
    /// newTermsHash is hashStruct(MandateTerms) of the NEW terms (no id in it). Checked for generation 0 and for generation 1, and the
    /// successor stores the snapshot hash it was authorized against as parentSnapshotHash.
    function test_BuildAuthUsesTheTypedHashes() public {
        address t1 = fx.T1();
        address r0 = fx.R0();
        address r1 = fx.R1();
        (bytes32 lid, bytes32 p0) = fx.activate(r0, fx.one(t1));
        ContainModel.Terms memory terms0 = fx.mgr().mandateTerms(p0);
        ContainModel.Terms memory wider = fx.mgr().mandateTerms(p0);
        wider.boundsVersion = 2; // new terms that differ from the predecessor's
        MigrationModel.Auth memory a0 = fx.mgr().buildAuth(p0, 2, r0, wider, fx.mgr().mandatePin(p0), block.timestamp + 100, 1);
        assertEq(a0.termsSnapshotHash, FastPayTypes.snapshotHash(lid, bytes32(0), 0, fx.CUSTOMER(), _typed(terms0)), "snapshot of generation 0");
        assertEq(a0.newTermsHash, FastPayTypes.hashStruct(_typed(wider)), "newTermsHash = hashStruct(MandateTerms) of the new terms");
        assertTrue(a0.newTermsHash != FastPayTypes.hashStruct(_typed(terms0)));
        assertEq(uint256(a0.widenedMask), 1 << 6, "a bounds version change is bit 6 of the widened mask");

        fx.grantBounded(t1, r1);
        fx.lock(t1, r0);
        bytes32 p1 = fx.migrate(p0, 0, r1);
        assertEq(fx.mgr().getMandate(p1).parentSnapshotHash, FastPayTypes.snapshotHash(lid, bytes32(0), 0, fx.CUSTOMER(), _typed(terms0)));
        ContainModel.Terms memory terms1 = fx.mgr().mandateTerms(p1);
        MigrationModel.Auth memory a1 = fx.mgr().buildAuth(p1, 2, r1, terms1, fx.mgr().mandatePin(p1), block.timestamp + 100, 2);
        assertEq(a1.termsSnapshotHash, FastPayTypes.snapshotHash(lid, p0, 1, fx.CUSTOMER(), _typed(terms1)), "snapshot of generation 1");
        assertEq(a1.newTermsHash, FastPayTypes.hashStruct(_typed(terms1)));
        assertEq(a1.newTermsHash, FastPayTypes.hashStruct(_typed(terms0)), "the migration kept the terms: the same hash, whatever the generation");
    }
}
