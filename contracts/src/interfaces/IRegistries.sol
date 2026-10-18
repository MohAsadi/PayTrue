// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

interface IMerchantRegistry {
    /// The recipient valid now; reverts UnknownMerchant, MerchantInactive or MerchantTokenNotAccepted.
    function settlement(bytes32 merchantId, address token) external view returns (address recipient);
}

interface IExecutorRegistry {
    function isExecutor(address who) external view returns (bool);
}

interface IFeeController {
    function feeBps() external view returns (uint16);
    function feeRecipient() external view returns (address);
}
