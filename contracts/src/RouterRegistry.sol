// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.24;

import {IRouterRegistry} from "./interfaces/IRouterRegistry.sol";
import "./Errors.sol";

/// RouterRegistry (document 12 section 3, document 06 section 4): router versions with code hash and version, the lifecycle
/// CANDIDATE -> ACTIVE -> DEPRECATED -> SUNSET -> RETIRED, the emergency state DISABLED, the router mode that selects the migration predicate
/// (NORMAL or EMERGENCY, derived from the state, never chosen by a caller), and the Pay Once settle-once record shared by every router version.
/// Immutable code; governance (a timelock in production) moves the lifecycle forward, the guardian can only disable a router (stop-only).
/// Port of the reference model RegistryModel; the number of live routers is a counter, so activation is O(1) however many routers existed.
contract RouterRegistry is IRouterRegistry {
    uint8 public constant ST_UNREGISTERED = 0;
    uint8 public constant ST_CANDIDATE = 1;
    uint8 public constant ST_ACTIVE = 2;
    uint8 public constant ST_DEPRECATED = 3;
    uint8 public constant ST_DISABLED = 4;
    uint8 public constant ST_SUNSET = 5;
    uint8 public constant ST_RETIRED = 6;

    uint8 public constant REASON_STANDARD = 0;
    uint8 public constant REASON_SECURITY = 1;

    uint256 public constant MIN_NOTICE_STANDARD = 180 days; // PC-01, proposal
    uint256 public constant MIN_NOTICE_SECURITY = 60 days; // PC-02, proposal
    uint256 public constant RETENTION = 365 days; // PC-03, proposal
    uint256 public constant ROLLBACK_WINDOW = 30 days; // registry parameter, proposal
    uint256 public constant MAX_LIVE_ROUTERS = 2; // PC-12, proposal

    struct Router {
        uint8 state;
        uint8 reason;
        uint8 prevState;
        uint32 version;
        uint64 deprecatedAt;
        uint64 sunsetNotBefore;
        uint64 sunsetAt;
        bytes32 codeHash;
    }

    address public immutable governance;
    address public immutable guardian;

    mapping(address => Router) public routers;
    mapping(bytes32 => bool) public isSettled;
    uint256 public liveRouters; // routers that are ACTIVE or DEPRECATED

    event RouterProposed(address indexed router, bytes32 codeHash, uint32 version);
    event RouterStateChanged(address indexed router, uint8 oldState, uint8 newState, uint8 reason);
    event PaymentSettled(bytes32 indexed paymentId, address indexed router);

    constructor(address governance_, address guardian_) {
        governance = governance_;
        guardian = guardian_;
    }

    modifier onlyGovernance() {
        if (msg.sender != governance) revert NotGovernance();
        _;
    }

    function _setState(address router, uint8 s, uint8 reason) internal {
        Router storage r = routers[router];
        uint8 old = r.state;
        bool was = old == ST_ACTIVE || old == ST_DEPRECATED;
        bool now_ = s == ST_ACTIVE || s == ST_DEPRECATED;
        if (was && !now_) liveRouters -= 1;
        if (!was && now_) liveRouters += 1;
        r.state = s;
        emit RouterStateChanged(router, old, s, reason);
    }

    // ---- registration
    function propose(address router, bytes32 codeHash, uint32 version) public onlyGovernance {
        Router storage r = routers[router];
        if (r.state != ST_UNREGISTERED) revert WrongRouterState();
        r.codeHash = codeHash;
        r.version = version;
        _setState(router, ST_CANDIDATE, 0);
        emit RouterProposed(router, codeHash, version);
    }

    function activate(address router) public onlyGovernance {
        if (routers[router].state != ST_CANDIDATE) revert WrongRouterState();
        if (liveRouters >= MAX_LIVE_ROUTERS) revert TooManyLiveRouters();
        _setState(router, ST_ACTIVE, 0);
    }

    // ---- lifecycle
    function notice(uint8 reason) public pure returns (uint256) {
        return reason == REASON_SECURITY ? MIN_NOTICE_SECURITY : MIN_NOTICE_STANDARD;
    }

    function deprecate(address router, address successor, uint8 reason, uint64 sunsetNotBefore_) external onlyGovernance {
        Router storage r = routers[router];
        if (r.state != ST_ACTIVE) revert WrongRouterState();
        if (routers[successor].state != ST_ACTIVE || successor == router) revert SuccessorNotActive();
        uint64 limit = uint64(block.timestamp + notice(reason));
        if (sunsetNotBefore_ == 0) sunsetNotBefore_ = limit;
        if (sunsetNotBefore_ < limit) revert NoticeTooShort();
        r.reason = reason;
        r.deprecatedAt = uint64(block.timestamp);
        r.sunsetNotBefore = sunsetNotBefore_;
        _setState(router, ST_DEPRECATED, reason);
    }

    /// Stop-only: the guardian (or governance) disables a router at once. Customers can still exit and migrate (mode EMERGENCY).
    function emergencyDisable(address router) external {
        if (msg.sender != guardian && msg.sender != governance) revert NotAuthorized();
        Router storage r = routers[router];
        if (r.state != ST_ACTIVE && r.state != ST_DEPRECATED) revert WrongRouterState();
        r.prevState = r.state;
        _setState(router, ST_DISABLED, 0);
    }

    function clearEmergency(address router) external onlyGovernance {
        Router storage r = routers[router];
        if (r.state != ST_DISABLED) revert WrongRouterState();
        _setState(router, r.prevState, 0);
    }

    function sunset(address router) external onlyGovernance {
        Router storage r = routers[router];
        if (r.state != ST_DEPRECATED) revert WrongRouterState();
        if (block.timestamp < r.sunsetNotBefore) revert NotYetSunset();
        r.sunsetAt = uint64(block.timestamp);
        _setState(router, ST_SUNSET, 0);
    }

    function retire(address router) external onlyGovernance {
        Router storage r = routers[router];
        if (r.state != ST_SUNSET) revert WrongRouterState();
        if (block.timestamp < uint256(r.sunsetAt) + RETENTION) revert RetentionNotElapsed();
        _setState(router, ST_RETIRED, 0);
    }

    // ---- views
    function stateOf(address router) external view returns (uint8) {
        return routers[router].state;
    }

    function codeHashOf(address router) external view returns (bytes32) {
        return routers[router].codeHash;
    }

    function versionOf(address router) external view returns (uint32) {
        return routers[router].version;
    }

    function isBindable(address router) external view returns (bool) {
        Router storage r = routers[router];
        if (r.state == ST_ACTIVE) return true;
        if (r.state == ST_DEPRECATED) return block.timestamp < uint256(r.deprecatedAt) + ROLLBACK_WINDOW;
        return false;
    }

    function isChargeable(address router) external view returns (bool) {
        uint8 s = routers[router].state;
        return s == ST_ACTIVE || s == ST_DEPRECATED;
    }

    /// Mode(R) is a function of the registry state only: NORMAL for ACTIVE and for DEPRECATED with reason STANDARD, EMERGENCY for everything
    /// else (fail closed).
    function mode(address router) external view returns (uint8) {
        Router storage r = routers[router];
        if (r.state == ST_ACTIVE) return 0;
        if (r.state == ST_DEPRECATED) return r.reason == REASON_SECURITY ? 1 : 0;
        return 1;
    }

    // ---- Pay Once: the settle-once record shared by every router version (a payment cannot settle twice across a migration)
    function markSettled(bytes32 paymentId) external {
        uint8 s = routers[msg.sender].state;
        if (s != ST_ACTIVE && s != ST_DEPRECATED) revert NotRouterOfRegistry();
        if (isSettled[paymentId]) revert PaymentAlreadySettled();
        isSettled[paymentId] = true;
        emit PaymentSettled(paymentId, msg.sender);
    }
}
