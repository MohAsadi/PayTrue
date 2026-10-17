// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

/// EIP-712 encoding, identifiers and fiat rounding of documents 11 and 12 (reference model of tools/eip712_vectors.py).
/// Every function is pure; the generated test GenHashVectors.t.sol compares each result with the Python constant.
library HashModel {
    bytes32 internal constant DOMAIN_TYPEHASH =
        keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)");
    bytes32 internal constant QUOTE_TYPEHASH = keccak256(
        "PriceQuote(bytes32 paymentId,address payer,address token,uint256 amountIn,uint16 currency,uint256 priceE18,uint64 issuedAt,uint64 validAfter,uint64 validUntil,uint256 nonce,uint32 signerSetVersion,uint64 registryVersion,uint32 boundsVersion,bytes32 routeHash,bytes32 priceSourceSetHash)"
    );

    bytes32 internal constant LINEAGE_TAG = keccak256("fastpay.lineage.v1");
    bytes32 internal constant MANDATE_TAG = keccak256("fastpay.mandate.v1");
    bytes32 internal constant CYCLE_TAG = keccak256("fastpay.cycle.v1");
    bytes32 internal constant ROUTE_DIRECT_TAG = keccak256("fastpay.route.direct.v1");

    struct Quote {
        bytes32 paymentId;
        address payer;
        address token;
        uint256 amountIn;
        uint16 currency;
        uint256 priceE18;
        uint64 issuedAt;
        uint64 validAfter;
        uint64 validUntil;
        uint256 nonce;
        uint32 signerSetVersion;
        uint64 registryVersion;
        uint32 boundsVersion;
        bytes32 routeHash;
        bytes32 priceSourceSetHash;
    }

    function domainSeparator(string memory name, string memory version, uint256 chainId, address verifyingContract)
        internal
        pure
        returns (bytes32)
    {
        return keccak256(abi.encode(DOMAIN_TYPEHASH, keccak256(bytes(name)), keccak256(bytes(version)), chainId, verifyingContract));
    }

    /// keccak256(typeHash || the fifteen fields, each one 32-byte word); encoded in three chunks to stay clear of stack limits.
    function quoteStructHash(Quote memory q) internal pure returns (bytes32) {
        bytes memory a = abi.encode(QUOTE_TYPEHASH, q.paymentId, q.payer, q.token, q.amountIn, q.currency);
        bytes memory b = abi.encode(q.priceE18, q.issuedAt, q.validAfter, q.validUntil, q.nonce, q.signerSetVersion);
        bytes memory c = abi.encode(q.registryVersion, q.boundsVersion, q.routeHash, q.priceSourceSetHash);
        return keccak256(bytes.concat(a, b, c));
    }

    function digest(bytes32 domainSep, bytes32 structHash) internal pure returns (bytes32) {
        return keccak256(abi.encodePacked(hex"1901", domainSep, structHash));
    }

    // ---- identifiers: none contains a router address, a router version; only mandateId contains the generation
    function lineageId(
        uint256 chainId,
        address manager,
        address customer,
        bytes32 merchantId,
        bytes32 subscriptionRef,
        uint256 creationNonce
    ) internal pure returns (bytes32) {
        return keccak256(abi.encode(LINEAGE_TAG, chainId, manager, customer, merchantId, subscriptionRef, creationNonce));
    }

    function mandateId(bytes32 lineage, uint256 generation) internal pure returns (bytes32) {
        return keccak256(abi.encode(MANDATE_TAG, lineage, generation));
    }

    function cycleId(bytes32 lineage, uint256 cycleIndex) internal pure returns (bytes32) {
        return keccak256(abi.encode(CYCLE_TAG, lineage, cycleIndex));
    }

    function paymentIdRecurring(uint256 chainId, address manager, bytes32 lineage, bytes32 cycle) internal pure returns (bytes32) {
        return keccak256(abi.encode(chainId, manager, lineage, cycle));
    }

    function paymentIdPayOnce(uint256 chainId, address routerRegistry, bytes32 merchantId, bytes32 orderId)
        internal
        pure
        returns (bytes32)
    {
        return keccak256(abi.encode(chainId, routerRegistry, merchantId, orderId));
    }

    function routeHashDirect(uint256 chainId, address token) internal pure returns (bytes32) {
        return keccak256(abi.encode(ROUTE_DIRECT_TAG, chainId, token));
    }

    /// ceil(amountIn * priceE18 / (10^tokenDecimals * 1e18)): rounds UP, never down. The product is checked (Panic on overflow).
    function fiatValueMinor(uint256 amountIn, uint256 priceE18, uint8 tokenDecimals) internal pure returns (uint256) {
        uint256 num = amountIn * priceE18;
        uint256 den = (10 ** uint256(tokenDecimals)) * 1e18;
        if (num == 0) return 0;
        return (num - 1) / den + 1;
    }
}
