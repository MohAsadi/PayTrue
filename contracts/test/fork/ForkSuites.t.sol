// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {FastPayTypes as T} from "../../src/generated/FastPayTypes.sol";
import {Base} from "../helpers/Base.sol";
import {ChargeTest} from "../Charge.t.sol";
import {QuoteTest} from "../Quote.t.sol";
import {PayOnceTest} from "../PayOnce.t.sol";
import {SuccessorTest} from "../Successor.t.sol";
import {QueueTest} from "../Queue.t.sol";
import {GasTest} from "../Gas.t.sol";

/// The suites of the actual contracts, run on a FORK of Ethereum, Base or Arbitrum One against the REAL Permit2 of that chain (the one at the
/// canonical address). `tools/fork_run.py --project contracts` sets ETH_RPC_URL, FORK_BLOCK and EXPECT_CHAIN_ID, forks a pinned block that two
/// providers agree on, and records the result per chain. Without a fork each suite is skipped.
///
/// What a fork changes and what it does not: the contracts under test are deployed into the forked state and run on the real Permit2 code and
/// its real storage layout; the gas schedule is that of the EVM of the pinned toolchain (cancun), not the chain's own: Arbitrum's gas accounting
/// (ArbOS, the L1 data component) is NOT modelled, and the per-transaction gas cap of a chain is not enforced by the fork.
contract ForkEvidenceTest is Base {
    function _deployPermit2() internal override {
        _useRealPermit2();
    }

    /// The generated witness and domain code against the domain separator that the chain's Permit2 reports.
    function test_Fork_Permit2DomainSeparatorEqualsTheGeneratedOne() public view {
        (bool ok, bytes memory out) = CANONICAL.staticcall(abi.encodeWithSignature("DOMAIN_SEPARATOR()"));
        assertTrue(ok);
        assertEq(abi.decode(out, (bytes32)), T.permit2DomainSeparator(block.chainid, CANONICAL));
    }

    function test_Fork_EveryRuntimeFitsTheLimitsOnThisChain() public view {
        assertLe(address(manager).code.length, 22_000);
        assertLe(address(gateway).code.length, 22_000);
        assertLe(address(routerA).code.length, 22_000);
        assertLe(address(validator).code.length, 22_000);
        assertLe(address(queue).code.length, 22_000);
    }
}

contract ForkChargeTest is ChargeTest {
    function _deployPermit2() internal override {
        _useRealPermit2();
    }
}

contract ForkQuoteTest is QuoteTest {
    function _deployPermit2() internal override {
        _useRealPermit2();
    }
}

contract ForkPayOnceTest is PayOnceTest {
    function _deployPermit2() internal override {
        _useRealPermit2();
    }
}

contract ForkSuccessorTest is SuccessorTest {
    function _deployPermit2() internal override {
        _useRealPermit2();
    }
}

contract ForkQueueTest is QueueTest {
    function _deployPermit2() internal override {
        _useRealPermit2();
    }
}

contract ForkGasTest is GasTest {
    function _deployPermit2() internal override {
        _useRealPermit2();
    }
}
