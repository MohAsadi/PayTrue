// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.24;

/// Versioned quote-signer sets (document 11 section 4.7). `verifySigner` is the whole of Q1 and Q13 and costs a fixed number of storage
/// reads, whatever the size of the set: it reverts QuoteSignerRemoved, QuoteSignerUnauthorized, QuoteSignerSetStopped or QuoteSignerSetRetired.
interface ISignerSetRegistry {
    function verifySigner(address key, uint32 version, uint64 issuedAt) external view;
    function quoteSetGrace() external view returns (uint256);
}
