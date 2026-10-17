// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {ITokenPolicyRegistry} from "./interfaces/ITokenPolicyRegistry.sol";
import "./Errors.sol";

/// TokenPolicyRegistry (document 06 section 4, document 11 section 4.3) with the versioned price-bounds registry of ADR-020.
///
/// A mandate does not carry a price band. It pins the invoice currency and a `boundsVersion`; the band of (token, currency, version) is read
/// here. A published version is NEVER changed or removed (rule V5 of eip712/types.json), so a mandate always reads the band its customer was
/// shown; a new band is a new version, and the verifier intersects the pinned band with the current one so that a later, tighter band
/// narrows existing mandates and a later, wider one never widens them (document 11 N6).
///
/// Governance (a timelock in production) lists tokens, publishes bounds and source-set hashes; the guardian can only block a token (stop-only).
/// Every change of a token's policy increments `tokenVersion`, which a quote names (Q14).
contract TokenPolicyRegistry is ITokenPolicyRegistry {
    uint8 public constant STATUS_UNLISTED = 0;
    uint8 public constant STATUS_SETTLEMENT = 1;
    uint8 public constant STATUS_DIRECT_PAYMENT = 2;
    uint8 public constant STATUS_SWAP_ONLY = 3; // cannot be listed in v1
    uint8 public constant STATUS_BLOCKED = 4;

    struct TokenPolicy {
        uint8 status;
        uint8 decimals;
        uint64 version;
    }

    struct Band {
        bool published;
        uint256 min;
        uint256 max;
    }

    address public immutable governance;
    address public immutable guardian;
    /// MAX_QUOTE_TTL: the ceiling of a quote's life (immutable), also the TTL that Q12 compares with.
    uint32 public immutable maxQuoteTtl;
    /// MAX_BAND_WIDTH_BPS (PC-07): the width of a band, ceil(10,000 * (max - min) / min), never exceeds this immutable ceiling.
    uint256 public immutable maxBandWidthBps;

    mapping(address => TokenPolicy) public policy;
    mapping(address => mapping(uint16 => bytes32)) public priceSourceSetHash;
    mapping(address => mapping(uint16 => uint32)) public currentBoundsVersion;
    mapping(address => mapping(uint16 => mapping(uint32 => Band))) internal bands;

    event TokenListed(address indexed token, uint8 status, uint8 decimals, uint64 version);
    event TokenStatusChanged(address indexed token, uint8 status, uint64 version);
    event SourceSetChanged(address indexed token, uint16 indexed currency, bytes32 priceSourceSetHash, uint64 version);
    event BoundsPublished(address indexed token, uint16 indexed currency, uint32 boundsVersion, uint256 minPriceE18, uint256 maxPriceE18, uint64 tokenVersion);

    constructor(address governance_, address guardian_, uint32 maxQuoteTtl_, uint256 maxBandWidthBps_) {
        governance = governance_;
        guardian = guardian_;
        maxQuoteTtl = maxQuoteTtl_;
        maxBandWidthBps = maxBandWidthBps_;
    }

    modifier onlyGovernance() {
        if (msg.sender != governance) revert NotGovernance();
        _;
    }

    function list(address token, uint8 status_, uint8 decimals_) external onlyGovernance {
        if (status_ != STATUS_SETTLEMENT && status_ != STATUS_DIRECT_PAYMENT) revert TokenNotListed(); // SWAP_ONLY and BLOCKED cannot be listed in v1
        if (decimals_ > 36) revert InvalidBounds(); // 10^decimals * 1e18 must fit in a word
        TokenPolicy storage p = policy[token];
        if (p.status != STATUS_UNLISTED) revert WrongRouterState(); // a token is listed once; a status change is setStatus
        p.status = status_;
        p.decimals = decimals_;
        p.version += 1;
        emit TokenListed(token, status_, decimals_, p.version);
    }

    function setStatus(address token, uint8 status_) external onlyGovernance {
        TokenPolicy storage p = policy[token];
        if (p.status == STATUS_UNLISTED || p.status == STATUS_BLOCKED) revert TokenNotListed(); // a blocked token is blocked for good
        if (status_ != STATUS_SETTLEMENT && status_ != STATUS_DIRECT_PAYMENT && status_ != STATUS_BLOCKED) revert TokenNotListed();
        p.status = status_;
        p.version += 1;
        emit TokenStatusChanged(token, status_, p.version);
    }

    /// Stop-only: the guardian can block a token, never list one or widen anything.
    function block_(address token) external {
        if (msg.sender != guardian && msg.sender != governance) revert NotAuthorized();
        TokenPolicy storage p = policy[token];
        if (p.status == STATUS_UNLISTED || p.status == STATUS_BLOCKED) revert TokenNotListed();
        p.status = STATUS_BLOCKED;
        p.version += 1;
        emit TokenStatusChanged(token, STATUS_BLOCKED, p.version);
    }

    function setPriceSourceSet(address token, uint16 currency, bytes32 hash) external onlyGovernance {
        TokenPolicy storage p = policy[token];
        if (p.status == STATUS_UNLISTED) revert TokenNotListed();
        priceSourceSetHash[token][currency] = hash;
        p.version += 1;
        emit SourceSetChanged(token, currency, hash, p.version);
    }

    /// Publishes the next bounds version of (token, currency): append-only; returns the new version (1 for the first).
    function publishBounds(address token, uint16 currency, uint256 minPriceE18, uint256 maxPriceE18) external onlyGovernance returns (uint32 v) {
        TokenPolicy storage p = policy[token];
        if (p.status == STATUS_UNLISTED) revert TokenNotListed();
        if (minPriceE18 == 0 || minPriceE18 > maxPriceE18) revert InvalidBounds();
        // width = ceil(10,000 * (max - min) / min), measured on the minimum because the blast radius is stated on the lowest price (PC-07)
        uint256 diff = (maxPriceE18 - minPriceE18) * 10_000;
        if ((diff + minPriceE18 - 1) / minPriceE18 > maxBandWidthBps) revert BandTooWide();
        v = currentBoundsVersion[token][currency] + 1;
        currentBoundsVersion[token][currency] = v;
        bands[token][currency][v] = Band(true, minPriceE18, maxPriceE18);
        p.version += 1;
        emit BoundsPublished(token, currency, v, minPriceE18, maxPriceE18, p.version);
    }

    function bandOf(address token, uint16 currency, uint32 boundsVersion) external view returns (bool published, uint256 min, uint256 max) {
        Band storage b = bands[token][currency][boundsVersion];
        return (b.published, b.min, b.max);
    }

    function status(address token) external view returns (uint8) {
        return policy[token].status;
    }

    function tokenVersion(address token) external view returns (uint64) {
        return policy[token].version;
    }

    function quoteContext(address token, uint16 currency, uint32 pinnedBoundsVersion) external view returns (QuoteContext memory c) {
        TokenPolicy storage p = policy[token];
        c.status = p.status;
        c.decimals = p.decimals;
        c.tokenVersion = p.version;
        c.priceSourceSetHash = priceSourceSetHash[token][currency];
        uint32 cur = currentBoundsVersion[token][currency];
        c.currentBoundsVersion = cur;
        Band storage pinned = bands[token][currency][pinnedBoundsVersion];
        c.pinnedExists = pinned.published;
        c.pinnedMin = pinned.min;
        c.pinnedMax = pinned.max;
        Band storage current = bands[token][currency][cur];
        c.currentMin = current.min;
        c.currentMax = current.max;
        c.maxQuoteTtl = maxQuoteTtl;
    }
}
