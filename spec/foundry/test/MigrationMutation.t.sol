// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import "../src/Mutants.sol";
import {ScenarioVM} from "./helpers/ScenarioVM.sol";
import {VectorSuite} from "./helpers/VectorSuite.sol";

/// Mutation testing of the reference model (document 12 section 12, "Executable suites"): the exported vector suite is run against
/// every named mutant of src/Mutants.sol (mutant 1 .. MUTANT_COUNT; each one removes or inverts exactly one predicate, clause, exposure
/// update or comparison of the model: A1, A2, A3, L1, R1, R2, R3, X1, K1 (three parts), G1, X2, C1 (K.1 .. K.9), C2, O1N (both halves),
/// O1E, Mode, the exposure updates E6, AUTH, Q1, Q13, the Permit2 usability boundary, ...) and must make at least one vector fail.
/// Mutant 0 is the specification and must pass everything.
///
/// The same mutants and the same vectors are analysed in Python by `python -I tools/model_checks.py` (check [8], with a kill matrix).
/// This test is the Solidity counterpart: it kills the mutants of the Solidity model, not of the Python one.
contract MigrationMutationTest is Test {
    ScenarioVM internal machine;
    string internal scenarios;
    string internal containment;
    string[3] internal tables;
    uint256 internal constant TABLE_PREFIX = 40; // the same prefix as tools/model_checks.py TABLE_PREFIX: the Python kill analysis proves 151 of 151 with it

    function setUp() public {
        machine = new ScenarioVM();
        scenarios = vm.readFile("vectors/scenarios.json");
        containment = vm.readFile("vectors/containment.json");
        tables[0] = vm.readFile("vectors/table_single.json");
        tables[1] = vm.readFile("vectors/table_shared_x.json");
        tables[2] = vm.readFile("vectors/table_shared_y.json");
    }

    /// Mutant 0 is the specification: every scenario, every containment tuple and the prefix of every table passes.
    function test_Mutant0PassesEverything() public {
        assertEq(VectorSuite.runAllScenarios(machine, scenarios, 0, false), 0, "a scenario fails on the unmutated model");
        assertEq(VectorSuite.runContainment(containment, 0), 0, "a containment tuple fails on the unmutated model");
        for (uint256 c = 0; c < 3; ++c) {
            assertEq(VectorSuite.runTablePrefix(machine, tables[c], c, 0, TABLE_PREFIX), 0, "a table transition fails on the unmutated model");
        }
    }

    function _killed(uint256 mutant) internal returns (bool) {
        if (VectorSuite.runAllScenarios(machine, scenarios, mutant, true) > 0) return true;
        if (VectorSuite.runContainment(containment, mutant) > 0) return true;
        for (uint256 c = 0; c < 3; ++c) {
            if (VectorSuite.runTablePrefix(machine, tables[c], c, mutant, TABLE_PREFIX) > 0) return true;
        }
        return false;
    }

    uint256 internal constant CHUNK = 16;

    /// Every mutant makes at least one vector fail. The 151 mutants are split in chunks of 16, one test each: running them in a single test
    /// exhausts the EVM memory limit (Solidity never frees memory inside a call, and every scenario re-parses the exported JSON).
    function _killRange(uint256 chunk) internal {
        uint256 lo = chunk * CHUNK + 1;
        uint256 hi = lo + CHUNK - 1;
        if (hi > MUTANT_COUNT) hi = MUTANT_COUNT;
        uint256 survivors = 0;
        for (uint256 m = lo; m <= hi; ++m) {
            if (!_killed(m)) {
                emit log_named_uint("SURVIVING MUTANT (number in src/Mutants.sol)", m);
                survivors += 1;
            }
        }
        assertEq(survivors, 0, "a mutant survives the exported vector suite");
    }

    /// The chunk tests below cover mutants 1 .. MUTANT_COUNT exactly.
    function test_ChunksCoverEveryMutant() public pure {
        uint256 chunks = 10;
        require(chunks * CHUNK >= MUTANT_COUNT, "a mutant is not covered by any chunk");
        require((chunks - 1) * CHUNK < MUTANT_COUNT, "a chunk is empty");
    }

    function testMutantsKilled_0() public { _killRange(0); }
    function testMutantsKilled_1() public { _killRange(1); }
    function testMutantsKilled_2() public { _killRange(2); }
    function testMutantsKilled_3() public { _killRange(3); }
    function testMutantsKilled_4() public { _killRange(4); }
    function testMutantsKilled_5() public { _killRange(5); }
    function testMutantsKilled_6() public { _killRange(6); }
    function testMutantsKilled_7() public { _killRange(7); }
    function testMutantsKilled_8() public { _killRange(8); }
    function testMutantsKilled_9() public { _killRange(9); }
}
