// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {FastPayTypes as T} from "../../src/generated/FastPayTypes.sol";
import {ContainLib} from "../../src/lib/ContainLib.sol";
import {PinLib} from "../../src/lib/PinLib.sol";

/// External wrappers around the libraries, so that tests (and the differential tests against the reference model) can call them with
/// calldata arguments exactly as the contracts do.
contract ContainHarness {
    function contained(T.MandateTerms calldata succ, T.MandateTerms calldata snap) external pure returns (uint256) {
        return ContainLib.containedMask(succ, snap);
    }

    function widened(T.MandateTerms calldata n, T.MandateTerms calldata snap) external pure returns (uint256) {
        return ContainLib.widenedMask(n, snap);
    }

    function constantsEqual(T.MandateTerms calldata a, T.MandateTerms calldata b) external pure returns (bool) {
        return ContainLib.lineageConstantsEqual(a, b);
    }

    function shape(T.MandateTerms calldata t) external pure {
        ContainLib.requireShape(t);
    }

    function wellFormed(T.AccountPin calldata p) external pure returns (bool) {
        return PinLib.wellFormed(p);
    }

    function checkField(T.AccountPin calldata p, bytes32 h, bytes32 hd) external pure returns (uint8) {
        return PinLib.checkField(p, h, hd);
    }

    function nextVersionSuccessor(T.AccountPin calldata prev, T.AccountPin calldata p) external pure returns (uint32) {
        return PinLib.nextVersionSuccessor(prev, p);
    }
}
