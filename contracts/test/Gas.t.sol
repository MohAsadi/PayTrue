// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Builders} from "./helpers/Builders.sol";
import {MockERC20} from "./helpers/MockERC20.sol";
import {IP2} from "./helpers/Base.sol";
import {FastPayTypes as T} from "../src/generated/FastPayTypes.sol";
import {IMandateManager} from "../src/interfaces/IMandateManager.sol";
import {MigrationQueue} from "../src/MigrationQueue.sol";
import {PaymentRouter} from "../src/PaymentRouter.sol";

/// Gas of the real contracts, measured with every account and slot cold (as in a transaction): the figures behind MAX_BATCH (PC-04), the
/// bound of PC-18 and the cost of a charge. The EVM gas schedule is that of the compiler's target (cancun); a chain with another schedule
/// (Arbitrum's L1 data component, for one) needs the fork measurement of RP-19, which is not done here.
///
/// Method for MAX_BATCH (ADR-022): the worst case per entry is a successor of three tokens drawn from the largest exposure that the bound
/// allows (eight tokens on each router), measured as part of a queue step of k entries; the transaction gas is that plus the intrinsic
/// 21,000 and the calldata (4 per zero byte, 16 per other byte; the EIP-7623 floor is also computed). The budget is HALF of the per-transaction
/// gas cap of 2^24 (EIP-7825, assumed for the launch chains: not verified here), so that a step never comes near the cap and a chain whose
/// schedule is costlier has room.
contract GasTest is Builders {
    uint256 internal constant TX_BUDGET = 8_388_608; // half of 2^24
    uint256 internal constant POOL = 8;

    MockERC20[] pool;
    bytes32[] lids;
    bytes32[] mids;

    function _sortedPool() internal {
        for (uint256 i = 0; i < POOL; ++i) {
            pool.push(new MockERC20());
        }
        // ascending by address
        for (uint256 i = 0; i < POOL; ++i) {
            for (uint256 j = i + 1; j < POOL; ++j) {
                if (uint160(address(pool[j])) < uint160(address(pool[i]))) {
                    (pool[i], pool[j]) = (pool[j], pool[i]);
                }
            }
        }
    }

    /// Three distinct pool tokens, ascending, rotating with i.
    function _triple(uint256 i) internal view returns (address[] memory t) {
        uint256 a = i % POOL;
        uint256 b = (i + 3) % POOL;
        uint256 c = (i + 5) % POOL;
        // sort the three indices
        if (a > b) (a, b) = (b, a);
        if (b > c) (b, c) = (c, b);
        if (a > b) (a, b) = (b, a);
        t = new address[](3);
        t[0] = address(pool[a]);
        t[1] = address(pool[b]);
        t[2] = address(pool[c]);
    }

    function _fillCustomer(uint256 lineages) internal {
        _sortedPool();
        for (uint256 i = 0; i < POOL; ++i) {
            _fund(customer, pool[i], 1_000e6);
            _grant(customer, pool[i], address(routerB), 500e6); // S1: the new router, sized for every lineage
            vm.startPrank(gov);
            policy.list(address(pool[i]), 1, 6);
            vm.stopPrank();
        }
        for (uint256 k = 0; k < lineages; ++k) {
            T.MandateTerms memory t = _termsOf(_triple(k));
            (bytes32 l, bytes32 m) = _activate(customer, k + 1, address(routerA), t, _pin());
            lids.push(l);
            mids.push(m);
        }
    }

    function _lockAll() internal {
        IP2.TokenSpenderPair[] memory pairs = new IP2.TokenSpenderPair[](POOL);
        for (uint256 i = 0; i < POOL; ++i) {
            pairs[i] = IP2.TokenSpenderPair(address(pool[i]), address(routerA));
        }
        vm.prank(customer);
        p2.lockdown(pairs);
    }

    function _entries(uint8 kind, uint256 n) internal returns (MigrationQueue.Entry[] memory es, bytes32 head) {
        es = new MigrationQueue.Entry[](n);
        bytes32[] memory ah = new bytes32[](n);
        for (uint256 i = 0; i < n; ++i) {
            T.MandateTerms memory pt = _termsOf(_triple(i));
            T.AccountPin memory p = _pin();
            T.SuccessorAuthorization memory a = _auth(Sp(lids[i], mids[i], bytes32(0), 0, kind, address(routerB)), pt, pt, p);
            es[i].req = _req(pt, p, _termsOf(_triple(i)), _pin(), a);
            ah[i] = T.hashStruct(a);
        }
        bytes32 nextHead = bytes32(0);
        for (uint256 j = n; j > 0; --j) {
            es[j - 1].next = nextHead;
            nextHead = queue.link(ah[j - 1], nextHead);
        }
        head = nextHead;
    }

    function _cool() internal {
        vm.cool(address(manager));
        vm.cool(address(validator));
        vm.cool(address(ledger));
        vm.cool(address(queue));
        vm.cool(address(gateway));
        vm.cool(address(routers));
        vm.cool(address(policy));
        vm.cool(CANONICAL);
        vm.cool(address(routerA));
        vm.cool(address(routerB));
        for (uint256 i = 0; i < pool.length; ++i) {
            vm.cool(address(pool[i]));
        }
    }

    /// Intrinsic gas of a transaction with this calldata: 21,000 + 4 per zero byte + 16 per other byte, and the EIP-7623 floor.
    function _intrinsic(bytes memory data) internal pure returns (uint256 standard, uint256 floor) {
        uint256 zeros;
        for (uint256 i = 0; i < data.length; ++i) {
            if (data[i] == 0) zeros++;
        }
        uint256 nonzero = data.length - zeros;
        standard = 21_000 + zeros * 4 + nonzero * 16;
        floor = 21_000 + (zeros + nonzero * 4) * 10;
    }

    function _prepare(uint8 kind, uint256 k) internal returns (bytes32 id, MigrationQueue.Entry[] memory es) {
        _fillCustomer(k);
        _lockAll(); // lock everything up front: the worst case for the old-allowance reads and no residue question
        bytes32 head;
        (es, head) = _entries(kind, k);
        vm.prank(customer);
        id = queue.open(1, kind, address(routerB), uint32(k), head, uint64(START + 1 days));
    }

    function _measureStep(uint8 kind, uint256 k) internal returns (uint256 exec, uint256 txGas, uint256 bytesLen) {
        (bytes32 id, MigrationQueue.Entry[] memory es) = _prepare(kind, k);
        bytes memory data = abi.encodeCall(queue.step, (id, es));
        bytesLen = data.length;
        txGas = _intrinsicGas(data);
        _cool();
        uint256 g = gasleft();
        queue.step(id, es);
        exec = g - gasleft();
        txGas += exec;
        assertEq(_view(manager.mandateIdOf(lids[k - 1], 1)).router, address(routerB), "the last entry was applied");
    }

    /// The larger of the standard intrinsic gas and the EIP-7623 floor.
    function _intrinsicGas(bytes memory data) internal pure returns (uint256) {
        (uint256 std, uint256 floor_) = _intrinsic(data);
        return std > floor_ ? std : floor_;
    }

    function _report(string memory label, uint8 kind, uint256 k) internal {
        (uint256 exec, uint256 txGas, uint256 n) = _measureStep(kind, k);
        emit log_named_uint(string.concat(label, " k=", vm.toString(k), " exec gas"), exec);
        emit log_named_uint(string.concat(label, " k=", vm.toString(k), " per entry"), exec / k);
        emit log_named_uint(string.concat(label, " k=", vm.toString(k), " calldata bytes"), n);
        emit log_named_uint(string.concat(label, " k=", vm.toString(k), " tx gas estimate"), txGas);
    }

    // ------------------------------------------------------------------------------------------------------------ queue steps
    function test_Gas_Step_Normal_1() public {
        _report("NORMAL", NORMAL, 1);
    }

    function test_Gas_Step_Normal_5() public {
        _report("NORMAL", NORMAL, 5);
    }

    function test_Gas_Step_Normal_10() public {
        _report("NORMAL", NORMAL, 10);
    }

    function test_Gas_Step_Emergency_1() public {
        _report("EMERGENCY", EMERGENCY, 1);
    }

    function test_Gas_Step_Emergency_5() public {
        _report("EMERGENCY", EMERGENCY, 5);
    }

    function test_Gas_Step_Emergency_10() public {
        _report("EMERGENCY", EMERGENCY, 10);
    }

    /// The marginal cost of an entry, from two steps of different sizes, and what it says about the earlier MAX_BATCH of 50 (an extrapolation: a
    /// step of 50 cannot be run any more, the queue refuses it; it WAS run, at 30,476,455 gas of transaction cost, when the constant was 50).
    function test_Gas_MarginalEntry_AndTheExtrapolationTo50() public {
        uint256 snap = vm.snapshotState();
        (, uint256 g5,) = _measureStep(EMERGENCY, 5);
        vm.revertToState(snap);
        (, uint256 g10,) = _measureStep(EMERGENCY, 10);
        uint256 marginal = (g10 - g5) / 5;
        emit log_named_uint("marginal tx gas per entry", marginal);
        emit log_named_uint("extrapolated tx gas of a step of 50", g10 + 40 * marginal);
        assertGt(g10 + 40 * marginal, TX_BUDGET, "the value 50 would not fit the budget");
    }

    /// The regression guard of the constant: a step of MAX_BATCH worst-case entries fits the budget. A change of MAX_BATCH (types.json,
    /// PC-04) or of the contracts that breaks this must be a decision, not an accident.
    function test_Gas_MaxBatchStepFitsTheBudget() public {
        uint256 k = T.MAX_BATCH;
        (, uint256 txGas,) = _measureStep(EMERGENCY, k);
        emit log_named_uint("MAX_BATCH", k);
        emit log_named_uint("worst-case step, tx gas estimate", txGas);
        emit log_named_uint("budget", TX_BUDGET);
        assertLe(txGas, TX_BUDGET, "a full step must fit half of the per-transaction cap");
    }

    // ------------------------------------------------------------------------------------------------------------ single operations
    function test_Gas_Activation_OneAndThreeTokens() public {
        _sortedPool();
        T.MandateTerms memory one = _terms(address(usdc));
        T.MandateTerms memory three = _termsOf(_triple(0));
        T.AccountPin memory p = _pin();
        _cool();
        vm.prank(customer);
        uint256 g = gasleft();
        manager.activate(customer, 1, address(routerA), one, p);
        emit log_named_uint("activate, 1 token", g - gasleft());
        _cool();
        vm.prank(customer);
        g = gasleft();
        manager.activate(customer, 2, address(routerA), three, p);
        emit log_named_uint("activate, 3 tokens", g - gasleft());
    }

    function test_Gas_Charge_WithQuote_ColdAndWarm() public {
        _fund(customer, usdc, 10_000e6);
        _grant(customer, usdc, address(routerA), 5_000e6);
        (bytes32 lid, bytes32 mid) = _activate(customer, 1, address(routerA), _terms(address(usdc)), _pin());
        PaymentRouter.QuoteBundle memory q = _quote(routerA, lid, 0, customer, address(usdc), 100e6, PRICE);
        T.MandateTerms memory t = _terms(address(usdc));
        T.AccountPin memory p = _pin();
        _cool();
        vm.prank(executor);
        uint256 g = gasleft();
        routerA.charge(PaymentRouter.ChargeRequest(mid, 0, address(usdc), 100e6, 500_000), t, p, q);
        emit log_named_uint("charge with quote, first charge (cold, fresh counters)", g - gasleft());
        vm.warp(START + 31 days);
        q = _quote(routerA, lid, 1, customer, address(usdc), 100e6, PRICE);
        vm.prank(executor);
        g = gasleft();
        routerA.charge(PaymentRouter.ChargeRequest(mid, 1, address(usdc), 100e6, 500_000), t, p, q);
        emit log_named_uint("charge with quote, second charge (warm within the test)", g - gasleft());
    }

    function test_Gas_Revoke_AndRetire() public {
        _sortedPool();
        T.MandateTerms memory three = _termsOf(_triple(0));
        (, bytes32 m) = _activate(customer, 1, address(routerA), three, _pin());
        _cool();
        vm.prank(customer);
        uint256 g = gasleft();
        manager.revoke(customer, m);
        emit log_named_uint("revoke, 3 tokens (the last mandate on them)", g - gasleft());
    }
}
