// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

/// Token policy and the versioned price-bounds registry (ADR-020, document 11 section 4.3).
interface ITokenPolicyRegistry {
    /// Everything the quote verifier reads about (token, currency) in one call. `pinnedExists` is false for a bounds version that was never
    /// published (a mandate that pins it can never be charged against a fiat cap).
    struct QuoteContext {
        uint8 status;
        uint8 decimals;
        uint64 tokenVersion;
        bytes32 priceSourceSetHash;
        uint32 currentBoundsVersion;
        bool pinnedExists;
        uint256 pinnedMin;
        uint256 pinnedMax;
        uint256 currentMin;
        uint256 currentMax;
        uint32 maxQuoteTtl;
    }

    function quoteContext(address token, uint16 currency, uint32 pinnedBoundsVersion) external view returns (QuoteContext memory);
    function status(address token) external view returns (uint8);
}
