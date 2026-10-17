// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Vm} from "forge-std/Vm.sol";
import {console} from "forge-std/console.sol";
import {WidthLib} from "../../src/WidthLib.sol";
import {ContainModel} from "../../src/ContainModel.sol";
import {ScenarioVM} from "./ScenarioVM.sol";
import {GenManifest} from "../generated/GenManifest.sol";

/// Loads the exported vector files (spec/foundry/vectors/*.json) and runs them: scenario programs on the scenario machine, containment
/// tuples on the containment model, transition tables through the machine. Used by the generated tests (mutant 0) and by the mutation
/// test (mutant 1..N). The JSON layouts are documented in the manifest written by tools/export_foundry.py.
library VectorSuite {
    Vm private constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));

    // ------------------------------------------------------------------------------------------------------------ scenarios
    function loadScenario(string memory json, string memory id) internal view returns (uint256[] memory) {
        return vm.parseJsonUintArray(json, string.concat(".programs.", id));
    }

    /// Run one scenario; returns the number of failed instructions.
    function runScenario(ScenarioVM machine, string memory json, string memory id, uint256 mutant) internal returns (uint256) {
        return machine.run(loadScenario(json, id), mutant);
    }

    /// Run every scenario with `mutant`; with stopFirst the run ends at the first failing scenario. Returns the number of failing scenarios.
    function runAllScenarios(ScenarioVM machine, string memory json, uint256 mutant, bool stopFirst) internal returns (uint256 failing) {
        string[] memory ids = GenManifest.scenarioIds();
        for (uint256 i = 0; i < ids.length; ++i) {
            if (runScenario(machine, json, ids[i], mutant) != 0) {
                failing += 1;
                if (stopFirst) return failing;
            }
        }
    }

    // ------------------------------------------------------------------------------------------------------------ containment tuples
    /// The 41 words of a terms record: expiresAt, merchantId, recipientPolicy, subscriptionRef, periodSeconds, anchorStartsAt, currency, nTokens,
    /// three token addresses, 3 x 6 caps (perPayment, total, day, week, thirtyDay, period), 6 fiat caps (same order), maxQuoteAge, boundsVersion,
    /// maxChargesPerPeriod, minInterval, maxFeeBps, extensionsHash (tools/lemma_gen.terms_words).
    function decodeTerms(uint256[] memory w, uint256 o) internal pure returns (ContainModel.Terms memory t) {
        t.expiresAt = WidthLib.toUint64(w[o]);
        t.merchantId = bytes32(w[o + 1]);
        t.recipientPolicy = bytes32(w[o + 2]);
        t.subscriptionRef = bytes32(w[o + 3]);
        t.periodSeconds = WidthLib.toUint64(w[o + 4]);
        t.anchorStartsAt = WidthLib.toUint64(w[o + 5]);
        t.currency = WidthLib.toUint16(w[o + 6]);
        t.nTokens = WidthLib.toUint8(w[o + 7]);
        for (uint256 i = 0; i < 3; ++i) {
            t.tokens[i] = address(WidthLib.toUint160(w[o + 8 + i]));
            for (uint256 f = 0; f < 6; ++f) {
                t.caps[i][f] = w[o + 11 + 6 * i + f];
            }
        }
        for (uint256 g = 0; g < 6; ++g) {
            t.fiat[g] = w[o + 29 + g];
        }
        t.maxQuoteAge = WidthLib.toUint64(w[o + 35]);
        t.boundsVersion = WidthLib.toUint32(w[o + 36]);
        t.maxChargesPerPeriod = WidthLib.toUint32(w[o + 37]);
        t.minInterval = WidthLib.toUint64(w[o + 38]);
        t.maxFeeBps = WidthLib.toUint16(w[o + 39]);
        t.extensionsHash = bytes32(w[o + 40]);
    }

    function decodeState(uint256[] memory w, uint256 o) internal pure returns (ContainModel.State memory st) {
        for (uint256 i = 0; i < 3; ++i) {
            for (uint256 f = 0; f < 5; ++f) {
                st.used[i][f] = w[o + 5 * i + f];
            }
        }
        for (uint256 g = 0; g < 5; ++g) {
            st.fiatUsed[g] = w[o + 15 + g];
        }
        st.chargesInPeriod = w[o + 20];
    }

    function decodePayment(uint256[] memory w, uint256 o) internal pure returns (ContainModel.Payment memory p) {
        p.tokenId = w[o];
        p.a = w[o + 1];
        p.tau = w[o + 2];
        p.merchant = w[o + 3];
        p.hasFiat = w[o + 4] != 0;
        p.fiat = w[o + 5];
        p.age = w[o + 6];
        p.price = w[o + 7];
        p.sinceLast = w[o + 8];
        p.feeBps = w[o + 9];
    }

    /// One tuple: [flags, expectedMask, succAccepts, predAccepts, succ terms, pred terms, state, payment].
    function checkTuple(uint256[] memory w, uint256 o, uint256 mutant) internal pure returns (bool) {
        uint256 termsWords = GenManifest.TERMS_WORDS;
        ContainModel.Terms memory succ = decodeTerms(w, o + 4);
        ContainModel.Terms memory pred = decodeTerms(w, o + 4 + termsWords);
        if (ContainModel.containedMask(succ, pred, mutant) != w[o + 1]) return false;
        if (w[o] & 1 == 0) return true;
        ContainModel.State memory st = decodeState(w, o + 4 + 2 * termsWords);
        ContainModel.Payment memory pay = decodePayment(w, o + 4 + 2 * termsWords + GenManifest.STATE_WORDS);
        bool sa = ContainModel.accepts(succ, st, pay);
        bool pa = ContainModel.accepts(pred, st, pay);
        if ((sa ? 1 : 0) != w[o + 2] || (pa ? 1 : 0) != w[o + 3]) return false;
        if (w[o + 1] == 0 && sa && !pa) return false; // Lemma M: a contained successor accepts nothing the predecessor rejects
        return true;
    }

    /// Run every containment tuple; returns the number of failing tuples.
    function runContainment(string memory json, uint256 mutant) internal view returns (uint256 failures) {
        uint256[] memory flat = vm.parseJsonUintArray(json, ".flat");
        uint256 n = flat.length / GenManifest.TUPLE_WORDS;
        for (uint256 i = 0; i < n; ++i) {
            if (!checkTuple(flat, i * GenManifest.TUPLE_WORDS, mutant)) failures += 1;
        }
    }

    // ------------------------------------------------------------------------------------------------------------ transition tables
    function _u64(bytes memory b, uint256 off) private pure returns (uint256 v) {
        for (uint256 i = 0; i < 8; ++i) {
            v = (v << 8) | uint8(b[off + i]);
        }
    }

    /// Replay every `stride`-th transition of a table on the machine; returns the number of failing transitions.
    function runTable(ScenarioVM machine, string memory json, uint256 config, uint256 mutant, uint256 stride) internal returns (uint256 failures) {
        bytes memory states = vm.parseJsonBytes(json, ".states");
        bytes memory trans = vm.parseJsonBytes(json, ".transitions");
        uint256 n = trans.length / 8;
        if (stride == 0) stride = 1;
        for (uint256 i = 0; i < n; i += stride) {
            uint256 w = _u64(trans, i * 8);
            uint256 key = _u64(states, ((w >> 48) & 0xFFFF) * 8);
            uint256 next = _u64(states, ((w >> 32) & 0xFFFF) * 8);
            if (!machine.replayTransition(config, key, (w >> 24) & 0xFF, (w >> 16) & 0xFF, (w >> 8) & 0xFF, next, mutant)) {
                if (failures == 0 && mutant == 0) console.log("first failing transition (index in the table):", i);
                failures += 1;
            }
        }
    }

    /// Replay at most `limit` transitions (the prefix of the table).
    function runTablePrefix(ScenarioVM machine, string memory json, uint256 config, uint256 mutant, uint256 limit) internal returns (uint256 failures) {
        bytes memory states = vm.parseJsonBytes(json, ".states");
        bytes memory trans = vm.parseJsonBytes(json, ".transitions");
        uint256 n = trans.length / 8;
        if (n > limit) n = limit;
        for (uint256 i = 0; i < n; ++i) {
            uint256 w = _u64(trans, i * 8);
            uint256 key = _u64(states, ((w >> 48) & 0xFFFF) * 8);
            uint256 next = _u64(states, ((w >> 32) & 0xFFFF) * 8);
            if (!machine.replayTransition(config, key, (w >> 24) & 0xFF, (w >> 16) & 0xFF, (w >> 8) & 0xFF, next, mutant)) {
                if (failures == 0 && mutant == 0) console.log("first failing transition (index in the table):", i);
                failures += 1;
            }
        }
    }
}
