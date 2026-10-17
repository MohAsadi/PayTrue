// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import "../src/Errors.sol";
import {ContainModel, TermsShape} from "../src/ContainModel.sol";
import {MigrationModel} from "../src/MigrationModel.sol";
import {RegistryModel} from "../src/RegistryModel.sol";
import {SignerSetModel} from "../src/SignerSetModel.sol";
import {TimeModel} from "../src/TimeModel.sol";
import {PinModel} from "../src/PinModel.sol";
import {Fixture} from "./helpers/Fixture.sol";

/// Dynamic evidence for "no unbounded loop can block a revoke, a migration or an emergency response" (the static half is
/// tools/loop_audit.py: every loop of the sources is annotated with its bound, and no loop without a constant bound is reachable from a
/// state-changing function). Four kinds of test:
///
///   1. the cost of an exit does not depend on anything that can grow: the size of the exposure list, the number of sibling mandates of
///      the customer, the number of generations of the lineage;
///   2. the worst cases at the proposed bounds, and at the hard maximum of the safe range of PC-18 (150 exposed tokens), stay far below
///      the block gas limit (the numbers are logged and copied into the evidence report);
///   3. values above a bound are refused before any loop runs (terms with too many tokens, a signer set above its size, a batch above
///      MAX_BATCH) and the refusal is cheap;
///   4. the O(1) counters equal their O(n) definitions after every operation (registry live count, exposure position map).
///
/// Gas figures are those of the REFERENCE MODEL on Foundry 1.8.5 with via-IR and 20 optimizer runs. They are lower bounds for the
/// production contracts (signature recovery, calldata and events are not modelled) and are not a measurement of any deployed contract.
contract LoopBoundsTest is Test {
    uint256 internal constant START = 1_800_000_000;
    uint256 internal constant BLOCK_GAS_LIMIT_FLOOR = 30_000_000; // the lowest gas limit of the launch chains that this repository assumes

    function setUp() public {
        vm.warp(START);
    }

    function _tok(uint256 i) internal pure returns (address) {
        return address(uint160(0x7000 + i));
    }

    // ---------------------------------------------------------------------------------------------------- 1. exits do not grow
    function _revokeGasWithExposure(uint256 extra) internal returns (uint256 used) {
        Fixture fx = new Fixture();
        (, bytes32 mid) = fx.activate(fx.R0(), fx.three(fx.T1(), fx.T2(), fx.T3()));
        MigrationModel mgr = fx.mgr();
        for (uint256 i = 0; i < extra; ++i) {
            mgr.seedLive(fx.CUSTOMER(), fx.R0(), address(uint160(0x9000 + i)), 1); // fills the exposure list behind the mandate's tokens
        }
        uint256 g = gasleft();
        fx.revoke(mid);
        used = g - gasleft();
        assertEq(mgr.exposedCount(fx.CUSTOMER(), fx.R0()), extra, "the three tokens of the mandate left the list");
    }

    /// revoke removes the mandate's tokens from the exposure list by swap-and-pop with a position map: its cost does not depend on the
    /// length of the list, which could be anything from 3 to the hard maximum 150 of PC-18's safe range.
    function test_Revoke_CostIsIndependentOfTheExposureListLength() public {
        uint256 g0 = _revokeGasWithExposure(0);
        uint256 g5 = _revokeGasWithExposure(5);
        uint256 g150 = _revokeGasWithExposure(150);
        emit log_named_uint("revoke gas, exposure list of 3", g0);
        emit log_named_uint("revoke gas, exposure list of 8", g5);
        emit log_named_uint("revoke gas, exposure list of 153", g150);
        // with a seeded list every removal swaps the last entry into the freed slot (three swaps); with no seeded entry the three
        // tokens of the mandate remove each other and most removals are a plain pop. That fixed difference is not growth:
        assertLe(g5, g0 + 45_000);
        assertLe(g150, g5 + 2_000, "from 8 to 153 entries the cost of a revoke does not change: no scan of the list");
    }

    function _revokeGasWithSiblings(uint256 k) internal returns (uint256 used) {
        Fixture fx = new Fixture();
        bytes32 last;
        for (uint256 i = 0; i < k; ++i) {
            (, last) = fx.activate(fx.R0(), fx.three(fx.T1(), fx.T2(), fx.T3()));
        }
        uint256 g = gasleft();
        fx.revoke(last);
        used = g - gasleft();
        assertEq(fx.live(fx.R0(), fx.T1()), k - 1);
    }

    /// The number of other mandates that share the customer's allowance is a counter, not a list: revoking one of 40 costs what revoking one of 1 costs.
    function test_Revoke_CostIsIndependentOfTheNumberOfSiblings() public {
        uint256 g1 = _revokeGasWithSiblings(1);
        uint256 g40 = _revokeGasWithSiblings(40);
        emit log_named_uint("revoke gas, 1 mandate", g1);
        emit log_named_uint("revoke gas, 40 sibling mandates", g40);
        assertLe(g40, g1 + 20_000);
    }

    function _revokeGasAfterGenerations(uint256 generations) internal returns (uint256 used) {
        Fixture fx = new Fixture();
        fx.grantBounded(fx.T1(), fx.R0());
        (bytes32 lid, bytes32 cur) = fx.activate(fx.R0(), fx.one(fx.T1()));
        for (uint256 i = 0; i < generations; ++i) {
            cur = fx.migrate(cur, 2, fx.R0()); // REVISION on the same router: the lineage grows by one mandate each time
        }
        assertEq(fx.mgr().mandateCount(lid), generations + 1);
        uint256 g = gasleft();
        fx.revoke(cur);
        used = g - gasleft();
    }

    /// The history of a lineage (one entry per generation) is never walked by a state-changing function: revoking generation 60 costs what revoking generation 0 costs.
    function test_Revoke_CostIsIndependentOfTheLineageHistory() public {
        uint256 g0 = _revokeGasAfterGenerations(0);
        uint256 g60 = _revokeGasAfterGenerations(60);
        emit log_named_uint("revoke gas, generation 0", g0);
        emit log_named_uint("revoke gas, generation 60", g60);
        assertLe(g60, g0 + 20_000);
    }

    function _reduceRetireGas(uint256 extra) internal returns (uint256 reduceGas, uint256 retireGas) {
        Fixture fx = new Fixture();
        (, bytes32 a) = fx.activate(fx.R0(), fx.three(fx.T1(), fx.T2(), fx.T3()));
        MigrationModel mgr = fx.mgr();
        for (uint256 i = 0; i < extra; ++i) {
            mgr.seedLive(fx.CUSTOMER(), fx.R0(), address(uint160(0x9000 + i)), 1);
        }
        address t1 = fx.T1();
        uint256 g = gasleft();
        mgr.reduceDropToken(a, t1, 0);
        reduceGas = g - gasleft();
        vm.warp(1_900_000_000);
        g = gasleft();
        mgr.retire(a, 0);
        retireGas = g - gasleft();
    }

    /// retire and reduce are exits too: neither walks the exposure list. (A reduction writes the new terms record, which is a cost of
    /// the record, about twenty-five storage slots in the model; it does not depend on the list.)
    function test_Retire_And_Reduce_DoNotScanTheExposureList() public {
        (uint256 r8, uint256 t8) = _reduceRetireGas(5);
        (uint256 r152, uint256 t152) = _reduceRetireGas(149);
        emit log_named_uint("reduce (drop one token) gas, exposure list of 8", r8);
        emit log_named_uint("reduce (drop one token) gas, exposure list of 152", r152);
        emit log_named_uint("retire gas, exposure list of 7", t8);
        emit log_named_uint("retire gas, exposure list of 151", t152);
        assertLe(r152, r8 + 2_000);
        assertLe(t152, t8 + 2_000);
    }

    // ---------------------------------------------------------------------------------------------------- 2. worst cases
    function _world(uint256 mandates, uint256 firstToken) internal returns (Fixture fx, bytes32[] memory mids) {
        fx = new Fixture();
        mids = new bytes32[](mandates);
        uint256 t = firstToken;
        for (uint256 i = 0; i < mandates; ++i) {
            address[] memory toks = new address[](mandates == 3 && i == 2 ? 2 : 3); // 3 + 3 + 2 = 8 tokens: the proposed bound of PC-18
            for (uint256 k = 0; k < toks.length; ++k) {
                toks[k] = _tok(t + k);
            }
            t += toks.length;
            (, mids[i]) = fx.activate(fx.R0(), toks);
        }
    }

    /// The emergency predicate O1E walks the exposure list of the old router, one Permit2 read per token. At the proposed bound (8) and
    /// at the hard maximum of the safe range of PC-18 (150) the migration of a lineage in EMERGENCY mode stays far below a block.
    function test_EmergencyMigration_WorstCase_AtTheProposedBoundAndAtTheHardMax() public {
        (Fixture fx, bytes32[] memory mids) = _world(3, 1);
        assertEq(fx.mgr().exposedCount(fx.CUSTOMER(), fx.R0()), fx.mgr().MAX_EXPOSED_TOKENS_PER_ROUTER(), "the world is at the proposed bound");
        ContainModel.Terms memory t = fx.mgr().mandateTerms(mids[0]);
        for (uint256 i = 0; i < t.nTokens; ++i) {
            fx.grantBounded(t.tokens[i], fx.R1()); // G1: the new router is funded
        }
        fx.reg().emergencyDisable(fx.R0()); // Mode(R0) = EMERGENCY, derived from the registry
        uint256 g = gasleft();
        fx.migrate(mids[0], 1, fx.R1());
        uint256 at8 = g - gasleft();
        emit log_named_uint("emergency migration gas, 8 exposed tokens (PC-18 proposal)", at8);
        assertLt(at8, 1_500_000);

        // the same at the hard maximum of the safe range of PC-18: 150 exposed tokens on the old router
        (Fixture fx2, bytes32[] memory mids2) = _world(3, 1);
        MigrationModel mgr2 = fx2.mgr();
        for (uint256 i = 0; i < 142; ++i) {
            mgr2.seedLive(fx2.CUSTOMER(), fx2.R0(), address(uint160(0x9000 + i)), 1); // 8 + 142 = 150 exposed tokens
        }
        assertEq(mgr2.exposedCount(fx2.CUSTOMER(), fx2.R0()), 150);
        ContainModel.Terms memory t2 = mgr2.mandateTerms(mids2[0]);
        for (uint256 i = 0; i < t2.nTokens; ++i) {
            fx2.grantBounded(t2.tokens[i], fx2.R1());
        }
        fx2.reg().emergencyDisable(fx2.R0());
        g = gasleft();
        fx2.migrate(mids2[0], 1, fx2.R1());
        uint256 at150 = g - gasleft();
        emit log_named_uint("emergency migration gas, 150 exposed tokens (hard max of PC-18)", at150);
        assertLt(at150, 10_000_000, "even at the hard maximum the emergency path is a fraction of a block");
        assertLt(at150, BLOCK_GAS_LIMIT_FLOOR / 3);
    }

    function _batchGas(uint256 n) internal returns (uint256 total) {
        (Fixture fx, bytes32[] memory mids) = _batchWorld(n);
        MigrationModel mgr = fx.mgr();
        address r1 = fx.R1();
        ContainModel.Terms memory terms = mgr.mandateTerms(mids[0]); // every lineage has the same terms and pin
        PinModel.Pin memory pin = mgr.mandatePin(mids[0]);
        fx.reg().emergencyDisable(fx.R0());
        MigrationModel.Access memory access = MigrationModel.Access(true, 0, false);
        for (uint256 i = 0; i < n; ++i) {
            MigrationModel.Auth memory au = mgr.buildAuth(mids[i], 1, r1, terms, pin, block.timestamp + 3600, i + 1);
            uint256 g = gasleft();
            mgr.activateSuccessor(mids[i], 1, r1, terms, pin, au, access, 0);
            total += g - gasleft();
        }
    }

    /// A batch of MAX_BATCH successors in one transaction (the entry point `activateSuccessors` of document 12 section 13 is modelled by
    /// one call per successor; only the call of the model is timed, not the construction of the authorization): the total at the
    /// proposed bound (PC-04: 10, was 50) and at a hundred, to see that the cost per successor stays the same. Every successor writes a new mandate record, the new
    /// exposure entries and its authorization nonce; the model stores the terms of a mandate as a record of about twenty-five slots.
    function test_Batch_OfMaxBatchSuccessors_FitsABlock() public {
        uint256 total = _batchGas(TimeModel.MAX_BATCH);
        emit log_named_uint("batch of MAX_BATCH EMERGENCY successors (3 tokens each), total gas", total);
        emit log_named_uint("per successor gas", total / TimeModel.MAX_BATCH);
        assertLt(total, BLOCK_GAS_LIMIT_FLOOR, "a batch at the proposed MAX_BATCH fits the lowest block gas limit assumed");

        uint256 total100 = _batchGas(100);
        emit log_named_uint("batch of 100 EMERGENCY successors (hard max of PC-04), total gas", total100);
        emit log_named_uint("per successor gas at 100", total100 / 100);
        // whether 100 fit one block depends on the chain; the property tested is that the cost is linear in the batch (no quadratic term): the cost per
        // successor at 100 is within a fifth of the cost per successor at MAX_BATCH (the model's gas, not the contracts': contracts/test/Gas.t.sol)
        assertLe(total100 / 100, (total / TimeModel.MAX_BATCH) * 12 / 10, "linear in the batch size");
    }

    function _batchWorld(uint256 n) internal returns (Fixture fx, bytes32[] memory mids) {
        fx = new Fixture();
        mids = new bytes32[](n);
        for (uint256 i = 0; i < n; ++i) {
            (, mids[i]) = fx.activate(fx.R0(), fx.three(fx.T1(), fx.T2(), fx.T3())); // every lineage uses the same three tokens: live = n
        }
        fx.grantBounded(fx.T1(), fx.R1());
        fx.grantBounded(fx.T2(), fx.R1());
        fx.grantBounded(fx.T3(), fx.R1());
    }

    // ---------------------------------------------------------------------------------------------------- 3. bounds refuse early
    function _terms() internal returns (Fixture fx, ContainModel.Terms memory t) {
        fx = new Fixture();
        t = fx.baseTerms(fx.three(fx.T1(), fx.T2(), fx.T3()));
    }

    function _expectInvalid(Fixture fx, ContainModel.Terms memory t, uint8 reason) internal {
        address customer = fx.CUSTOMER(); // read the getters first: expectRevert applies to the very next call
        address router = fx.R0();
        uint256 g = gasleft();
        vm.expectRevert(abi.encodeWithSelector(TermsInvalid.selector, reason));
        fx.activateTerms(customer, router, t);
        assertLt(g - gasleft(), 100_000, "a malformed terms record is refused before any storage write: a successful activation costs more than 1,000,000");
    }

    function test_Terms_TokenCountOutsideOneToThreeIsRefused() public {
        (Fixture fx, ContainModel.Terms memory t) = _terms();
        t.nTokens = 0;
        _expectInvalid(fx, t, TermsShape.TOKEN_COUNT);
        t.nTokens = 4;
        _expectInvalid(fx, t, TermsShape.TOKEN_COUNT);
        t.nTokens = 255;
        _expectInvalid(fx, t, TermsShape.TOKEN_COUNT);
        t.nTokens = 3;
        fx.activateTerms(fx.CUSTOMER(), fx.R0(), t); // the bound itself is accepted
    }

    function test_Terms_TokenOrderAndCanonicalForm() public {
        (Fixture fx, ContainModel.Terms memory t) = _terms();
        (t.tokens[0], t.tokens[1]) = (t.tokens[1], t.tokens[0]); // not ascending
        _expectInvalid(fx, t, TermsShape.TOKEN_ORDER);
        (fx, t) = _terms();
        t.tokens[1] = t.tokens[0]; // duplicate
        _expectInvalid(fx, t, TermsShape.TOKEN_ORDER);
        (fx, t) = _terms();
        t.tokens[0] = address(0);
        _expectInvalid(fx, t, TermsShape.TOKEN_ORDER);
        (fx, t) = _terms();
        t.nTokens = 2; // the third slot still holds a token: two encodings of the same terms
        _expectInvalid(fx, t, TermsShape.NOT_CANONICAL);
        (fx, t) = _terms();
        t.nTokens = 2;
        t.tokens[2] = address(0);
        t.caps[2][3] = 1; // a stray cap in an unused slot
        _expectInvalid(fx, t, TermsShape.NOT_CANONICAL);
    }

    /// Each documented width of the typed data is a limit of the model: the maximum is accepted, one more is refused.
    function test_Terms_DocumentedWidths() public {
        (Fixture fx, ContainModel.Terms memory t) = _terms();
        t.maxChargesPerPeriod = type(uint16).max;
        t.minInterval = type(uint32).max;
        t.maxQuoteAge = type(uint32).max;
        for (uint256 f = 0; f < 6; ++f) {
            t.fiat[f] = type(uint64).max;
        }
        fx.activateTerms(fx.CUSTOMER(), fx.R0(), t); // every field at its documented maximum

        (fx, t) = _terms();
        t.maxChargesPerPeriod = uint32(type(uint16).max) + 1;
        _expectInvalid(fx, t, TermsShape.WIDTH_CHARGES);
        (fx, t) = _terms();
        t.minInterval = uint64(type(uint32).max) + 1;
        _expectInvalid(fx, t, TermsShape.WIDTH_INTERVAL);
        (fx, t) = _terms();
        t.maxQuoteAge = uint64(type(uint32).max) + 1;
        _expectInvalid(fx, t, TermsShape.WIDTH_QUOTE_AGE);
        for (uint256 f = 0; f < 6; ++f) {
            (fx, t) = _terms();
            t.fiat[f] = uint256(type(uint64).max) + 1;
            _expectInvalid(fx, t, TermsShape.WIDTH_FIAT);
        }
    }

    /// The same shape check guards a successor: an invalid successor is refused before the predecessor is even read.
    function test_Terms_SuccessorWithMalformedTermsIsRefusedFirst() public {
        Fixture fx = new Fixture();
        (, bytes32 mid) = fx.activate(fx.R0(), fx.one(fx.T1()));
        ContainModel.Terms memory bad = fx.mgr().mandateTerms(mid);
        bad.nTokens = 4;
        MigrationModel.Auth memory au = fx.authFor(mid, 2, fx.R0(), block.timestamp + 100);
        PinModel.Pin memory pin = fx.mgr().mandatePin(mid);
        MigrationModel mgr = fx.mgr();
        address r0 = fx.R0();
        vm.expectRevert(abi.encodeWithSelector(TermsInvalid.selector, TermsShape.TOKEN_COUNT));
        mgr.activateSuccessor(mid, 2, r0, bad, pin, au, MigrationModel.Access(true, 0, false), 0);
    }

    function test_Batch_AboveMaxBatchIsRefusedBeforeAnyLoop() public {
        TimeModel.batchCheck(TimeModel.MAX_BATCH, 0);
        vm.expectRevert(BatchTooLarge.selector);
        this.callBatchCheck(TimeModel.MAX_BATCH + 1);
        vm.expectRevert(BatchTooLarge.selector);
        this.callBatchCheck(type(uint256).max);
    }

    function callBatchCheck(uint256 n) external pure {
        TimeModel.batchCheck(n, 0);
    }

    // ---------------------------------------------------------------------------------------------------- signer sets
    function _members(uint256 n) internal pure returns (address[] memory m) {
        m = new address[](n);
        for (uint256 i = 0; i < n; ++i) {
            m[i] = address(uint160(0xA000 + i));
        }
    }

    /// A signer set has at most MAX_SIGNERS_PER_SET members (both member loops are bounded by it); the emergency exits of the signer
    /// sets (removing a key, stopping a set) do not loop at all, so a set at the bound cannot delay them.
    function test_SignerSet_BoundedAndTheEmergencyExitsDoNotLoop() public {
        SignerSetModel s = new SignerSetModel(1 hours);
        uint256 max = s.MAX_SIGNERS_PER_SET();
        s.proposeSignerSet(0, 1, _members(max), 0);
        s.activateSignerSet(0, 1, 0);
        vm.expectRevert(abi.encodeWithSelector(TooManySigners.selector, max + 1, max));
        s.proposeSignerSet(0, 2, _members(max + 1), 0);
        vm.expectRevert(abi.encodeWithSelector(TooManySigners.selector, 5000, max));
        s.proposeSignerSet(0, 2, _members(5000), 0);

        uint256 g = gasleft();
        s.removeQuoteSigner(1, address(uint160(0xA000)));
        uint256 removeGas = g - gasleft();
        g = gasleft();
        s.stopSignerSet(1, 1);
        uint256 stopGas = g - gasleft();
        emit log_named_uint("removeQuoteSigner gas (set of 16)", removeGas);
        emit log_named_uint("stopSignerSet gas (set of 16)", stopGas);
        assertLt(removeGas, 60_000);
        assertLt(stopGas, 60_000);
        // a replacement set at the bound (the tombstoned key cannot be a member of it) is proposed and activated in bounded time
        address[] memory next = _members(max);
        next[0] = address(uint160(0xB000));
        g = gasleft();
        s.proposeSignerSet(0, 2, next, 0);
        uint256 proposeGas = g - gasleft();
        g = gasleft();
        s.activateSignerSet(0, 2, 0);
        uint256 activateGas = g - gasleft();
        emit log_named_uint("proposeSignerSet gas at the bound", proposeGas);
        emit log_named_uint("activateSignerSet gas at the bound", activateGas);
        assertLt(proposeGas, 1_500_000);
        assertLt(activateGas, 400_000);
    }

    // ---------------------------------------------------------------------------------------------------- 4. counters equal their definitions
    /// States that a harness may force: never UNREGISTERED (a router is never un-registered; proposing it again in another group would list
    /// it in two) and never DISABLED (that state only arises from emergencyDisable, which records the state to restore; a forced DISABLED has
    /// none, and clearEmergency would then restore UNREGISTERED).
    function _forcedState(uint256 r) internal pure returns (uint8) {
        uint8[5] memory allowed = [uint8(1), 2, 3, 5, 6];
        return allowed[r % 5];
    }

    /// Random sequences of every registry operation: the O(1) counter of live routers (ACTIVE or DEPRECATED) equals the scan of the group after each step.
    function testFuzz_RegistryLiveCounterEqualsScan(uint256 seed) public {
        RegistryModel reg = new RegistryModel();
        address[6] memory rs;
        for (uint256 i = 0; i < 6; ++i) {
            rs[i] = address(uint160(0x3000 + i));
        }
        for (uint256 step = 0; step < 60; ++step) {
            uint256 r = uint256(keccak256(abi.encode(seed, step)));
            address a = rs[r % 6];
            address b = rs[(r / 7) % 6];
            uint256 op = (r / 49) % 9;
            uint256 group = (r / 1000) % 2;
            if (op == 0) try reg.propose(a, bytes32(r), 1, group) {} catch {}
            else if (op == 1) try reg.activate(a) {} catch {}
            else if (op == 2) try reg.registerActive(a, bytes32(r), 1, group) {} catch {}
            else if (op == 3) try reg.deprecate(a, b, uint8(r % 2), 0, 0) {} catch {}
            else if (op == 4) try reg.emergencyDisable(a) {} catch {}
            else if (op == 5) try reg.clearEmergency(a) {} catch {}
            else if (op == 6) try reg.sunset(a, 0) {} catch {}
            else if (op == 7) {
                vm.warp(vm.getBlockTimestamp() + 400 days);
                try reg.retire(a, 0) {} catch {}
            } else {
                // test harnesses of the model move a router's state directly
                try reg.forceState(a, _forcedState(r), 0, vm.getBlockTimestamp()) {} catch {}
            }
            assertEq(reg.liveCount(0), reg.liveCountScan(0), "group 0");
            assertEq(reg.liveCount(1), reg.liveCountScan(1), "group 1");
        }
    }

    /// The position map of the exposure list after random sequences of grants and revocations (the stateful invariant checks it too).
    function testFuzz_ExposurePositionMapAfterRandomMandates(uint256 seed) public {
        Fixture fx = new Fixture();
        MigrationModel mgr = fx.mgr();
        bytes32[] memory ids = new bytes32[](12);
        uint256 n;
        for (uint256 step = 0; step < 40; ++step) {
            uint256 r = uint256(keccak256(abi.encode(seed, step)));
            if (r % 3 != 0 && n < 12) {
                uint256 a = 1 + (r / 3) % 6;
                address[] memory toks = new address[](1 + (r / 5) % 3);
                for (uint256 k = 0; k < toks.length; ++k) {
                    toks[k] = _tok(a + k); // ascending, 3 slots, tokens 0x7001 .. 0x7008 (the proposed bound is 8)
                }
                try fx.activate(fx.R0(), toks) returns (bytes32, bytes32 mid) {
                    ids[n++] = mid;
                } catch {}
            } else if (n > 0) {
                bytes32 id = ids[(r / 11) % n];
                if (r % 2 == 0) try fx.revoke(id) {} catch {}
                else try fx.retire(id) {} catch {}
            }
            uint256 len = mgr.exposedCount(fx.CUSTOMER(), fx.R0());
            assertLe(len, mgr.MAX_EXPOSED_TOKENS_PER_ROUTER());
            for (uint256 i = 0; i < len; ++i) {
                address t = mgr.exposedAt(fx.CUSTOMER(), fx.R0(), i);
                assertEq(mgr.exposedPos(fx.CUSTOMER(), fx.R0(), t), i + 1);
                assertGt(mgr.live(fx.CUSTOMER(), fx.R0(), t), 0);
            }
            for (uint256 k = 1; k <= 8; ++k) {
                if (mgr.live(fx.CUSTOMER(), fx.R0(), _tok(k)) == 0) assertEq(mgr.exposedPos(fx.CUSTOMER(), fx.R0(), _tok(k)), 0);
            }
        }
    }
}
