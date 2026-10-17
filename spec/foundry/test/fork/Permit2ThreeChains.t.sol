// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.24;

import {FastPayTypes as T} from "../../src/generated/FastPayTypes.sol";
import {WitnessSuite, ISigTransfer} from "../helpers/Permit2Evidence.sol";

/// Fork tests against the REAL Permit2 deployments (0x000000000022D473030F116dDEE9F6B43aC78BA3) on Ethereum, Base and Arbitrum One.
/// The fork is given by ETH_RPC_URL; FORK_BLOCK pins the block and EXPECT_CHAIN_ID names the chain the URL must serve. Without
/// ETH_RPC_URL every test is skipped. tools/fork_run.py runs the suite once per chain and records the block numbers and hashes.
///
///   1. The code deployed on the chain is, byte for byte, the code that the reproducible build of the pinned commit produces with the
///      chain id and the domain separator of that chain written into the two immutable slots named by solc's immutableReferences.
///   2. The domain separator of the deployment is the one the golden vector library computes (name, chain id, address).
///   3. The whole witness suite of `WitnessSuite` (single and batch Pay Once witness; every field and every character of the type
///      string is bound) passes against the real contract.
contract Permit2ThreeChainsTest is WitnessSuite {
    bool internal forkOn;

    function setUp() public {
        string memory url = vm.envOr("ETH_RPC_URL", string(""));
        if (bytes(url).length == 0) return;
        uint256 blockNo = vm.envOr("FORK_BLOCK", uint256(0));
        if (blockNo == 0) vm.createSelectFork(url);
        else vm.createSelectFork(url, blockNo);
        forkOn = true;
        require(CANONICAL.code.length > 0, "Permit2 is not deployed at the canonical address on this fork");
        uint256 expected = vm.envOr("EXPECT_CHAIN_ID", uint256(0));
        require(expected == 0 || expected == block.chainid, "the RPC URL serves another chain than EXPECT_CHAIN_ID");
        p2 = ISigTransfer(CANONICAL);
        _prepare();
    }

    function _ready() internal view override returns (bool) {
        return forkOn;
    }

    function _chainKey() internal view returns (string memory) {
        return string.concat(".chains.", vm.toString(block.chainid));
    }

    function test_Fork_ChainBlockAndCodeAreRecorded() public ready {
        emit log_named_uint("chain id", block.chainid);
        emit log_named_uint("fork block number", block.number);
        emit log_named_uint("fork block timestamp", block.timestamp);
        emit log_named_bytes32("Permit2 code hash on the fork", CANONICAL.codehash);
        emit log_named_uint("Permit2 code length on the fork", CANONICAL.code.length);
        assertTrue(block.chainid == 1 || block.chainid == 8453 || block.chainid == 42161, "one of the three launch chains");
    }

    function test_Fork_DeployedCodeIsExactlyTheRebuiltCode() public ready {
        string memory key = _chainKey();
        assertEq(CANONICAL.codehash, vm.parseJsonBytes32(_evidence(), string.concat(key, ".deployedCodeKeccak256")), "the code hash recorded by the rebuild");
        bytes memory expected = _expectedRuntime(CANONICAL);
        assertEq(CANONICAL.code.length, expected.length);
        assertEq(CANONICAL.code, expected, "every byte of the deployed code equals the rebuilt code with the two immutables filled");
    }

    function test_Fork_ImmutableSlotsHoldTheChainIdAndTheDomainSeparator() public ready {
        bytes memory code = CANONICAL.code;
        uint256 o1 = _offset("_CACHED_CHAIN_ID");
        uint256 o2 = _offset("_CACHED_DOMAIN_SEPARATOR");
        bytes32 chainWord;
        bytes32 sepWord;
        assembly ("memory-safe") { // lint: allow assembly
            chainWord := mload(add(add(code, 32), o1))
            sepWord := mload(add(add(code, 32), o2))
        }
        assertEq(uint256(chainWord), block.chainid);
        assertEq(sepWord, p2.DOMAIN_SEPARATOR());
    }

    function test_Fork_DomainSeparatorEqualsTheGoldenLibrary() public ready {
        bytes32 viaLib = T.permit2DomainSeparator(block.chainid, CANONICAL);
        assertEq(p2.DOMAIN_SEPARATOR(), viaLib);
        assertEq(viaLib, vm.parseJsonBytes32(_evidence(), string.concat(_chainKey(), ".recordedDomainSeparator")));
    }
}
