// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import "./Errors.sol";

/// Narrowing conversions that never truncate silently: a value above the width reverts with UnsafeCast.
/// Mirrors protocol_model.narrow. Every place of the reference model that narrows a uint256 goes through this library.
library WidthLib {
    function toUint8(uint256 x) internal pure returns (uint8) {
        if (x > type(uint8).max) revert UnsafeCast();
        return uint8(x);
    }

    function toUint16(uint256 x) internal pure returns (uint16) {
        if (x > type(uint16).max) revert UnsafeCast();
        return uint16(x);
    }

    function toUint32(uint256 x) internal pure returns (uint32) {
        if (x > type(uint32).max) revert UnsafeCast();
        return uint32(x);
    }

    function toUint48(uint256 x) internal pure returns (uint48) {
        if (x > type(uint48).max) revert UnsafeCast();
        return uint48(x);
    }

    function toUint64(uint256 x) internal pure returns (uint64) {
        if (x > type(uint64).max) revert UnsafeCast();
        return uint64(x);
    }

    function toUint160(uint256 x) internal pure returns (uint160) {
        if (x > type(uint160).max) revert UnsafeCast();
        return uint160(x);
    }
}
