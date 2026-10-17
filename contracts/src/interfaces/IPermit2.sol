// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.24;

/// The part of Permit2 (Uniswap/permit2 at commit cc306b601f172c51bc04334a109e98340456620b) that FastPay calls. The deployed code at the
/// canonical address is reproduced from that commit (spec/evidence/permit2/rebuild.json).
interface IAllowanceTransfer {
    function allowance(address owner, address token, address spender) external view returns (uint160 amount, uint48 expiration, uint48 nonce);
    function transferFrom(address from, address to, uint160 amount, address token) external;
}

interface ISignatureTransfer {
    struct TokenPermissions {
        address token;
        uint256 amount;
    }

    struct PermitBatchTransferFrom {
        TokenPermissions[] permitted;
        uint256 nonce;
        uint256 deadline;
    }

    struct SignatureTransferDetails {
        address to;
        uint256 requestedAmount;
    }

    function permitWitnessTransferFrom(
        PermitBatchTransferFrom memory permit,
        SignatureTransferDetails[] calldata transferDetails,
        address owner,
        bytes32 witness,
        string calldata witnessTypeString,
        bytes calldata signature
    ) external;
}
