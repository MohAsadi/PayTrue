// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

/// RouterRegistry (document 12 section 3): router lifecycle, code hashes and versions, the router mode that decides which migration
/// predicate applies, and the once-only record of Pay Once payments that is shared by every router version.
interface IRouterRegistry {
    function isChargeable(address router) external view returns (bool);
    function isBindable(address router) external view returns (bool);
    function mode(address router) external view returns (uint8);
    function codeHashOf(address router) external view returns (bytes32);
    function versionOf(address router) external view returns (uint32);
    function markSettled(bytes32 paymentId) external;
    function isSettled(bytes32 paymentId) external view returns (bool);
}
