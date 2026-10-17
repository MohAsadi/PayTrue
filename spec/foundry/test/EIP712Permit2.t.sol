// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.24;

import {FastPayTypes as T} from "../src/generated/FastPayTypes.sol";
import {Permit2Evidence, WitnessSuite, ISigTransfer} from "./helpers/Permit2Evidence.sol";

/// The Pay Once witness and the Permit2 rebuild, without a fork: Permit2 is deployed from the creation code that the reproducible build
/// produced from the pinned commit (evidence/permit2/rebuild.json), through the same deterministic deployment proxy and salt as the
/// canonical deployment, on a chain whose id is the one of the golden vectors. The suite of `WitnessSuite` then runs against that
/// contract: Permit2 itself is the oracle of the witness type string.
contract EIP712Permit2Test is WitnessSuite {
    uint256 internal constant VECTOR_CHAIN_ID = 84532;
    address internal deployed;

    function setUp() public {
        vm.chainId(VECTOR_CHAIN_ID);
        deployed = _deployRebuiltPermit2();
        p2 = ISigTransfer(deployed);
        _prepare();
    }

    function _ready() internal pure override returns (bool) {
        return true;
    }

    function test_Rebuild_Create2AddressIsTheCanonicalOne() public {
        bytes memory creation = _creationCode();
        assertEq(_create2Address(creation), CANONICAL, "the CREATE2 address computed from the rebuilt init code");
        assertEq(deployed, CANONICAL, "the address the deployment proxy returned");
        assertEq(deployed.code.length, 9152);
    }

    function test_Rebuild_RuntimeCodeEqualsTheLocalExpectation() public {
        // the code the proxy left at the canonical address is, byte for byte, the zero-immutable runtime code with the two immutable
        // slots (named by the compiler's immutableReferences) filled with the chain id and the domain separator
        assertEq(deployed.code, _expectedRuntime(deployed));
        assertEq(deployed.codehash, keccak256(_expectedRuntime(deployed)));
    }

    function test_Rebuild_ImmutablesAreWhatTheEvidenceNames() public {
        bytes memory code = deployed.code;
        bytes32 chainWord;
        bytes32 sepWord;
        uint256 o1 = _offset("_CACHED_CHAIN_ID");
        uint256 o2 = _offset("_CACHED_DOMAIN_SEPARATOR");
        assembly ("memory-safe") { // lint: allow assembly
            chainWord := mload(add(add(code, 32), o1))
            sepWord := mload(add(add(code, 32), o2))
        }
        assertEq(uint256(chainWord), VECTOR_CHAIN_ID);
        assertEq(sepWord, p2.DOMAIN_SEPARATOR());
    }

    /// The domain separator of the golden vector (Python, eip712/golden-vectors.json) is the one this Permit2 reports.
    function test_Permit2DomainSeparator_EqualsTheGoldenVector() public {
        assertEq(p2.DOMAIN_SEPARATOR(), T.permit2DomainSeparator(VECTOR_CHAIN_ID, CANONICAL));
    }
}
