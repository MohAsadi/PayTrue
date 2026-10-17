// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.24;

import "./Errors.sol";
import "./Mutants.sol";

/// Reference model of the RouterRegistry lifecycle (document 12 section 3) and of the router mode (section 5.3.1).
/// Mirrors protocol_model.RouterRegistryModel. Routers belong to a `group` (a chain): at most two routers per group are ACTIVE or
/// DEPRECATED. The functions that carry a `mutant` argument apply exactly one named mutation when it is non-zero.
contract RegistryModel {
    uint8 public constant ST_UNREGISTERED = 0;
    uint8 public constant ST_CANDIDATE = 1;
    uint8 public constant ST_ACTIVE = 2;
    uint8 public constant ST_DEPRECATED = 3;
    uint8 public constant ST_DISABLED = 4;
    uint8 public constant ST_SUNSET = 5;
    uint8 public constant ST_RETIRED = 6;

    uint8 public constant MODE_NORMAL = 0;
    uint8 public constant MODE_EMERGENCY = 1;
    uint8 public constant REASON_STANDARD = 0;
    uint8 public constant REASON_SECURITY = 1;

    uint256 public constant MIN_NOTICE_STANDARD = 180 days; // PC-01, proposal
    uint256 public constant MIN_NOTICE_SECURITY = 60 days; // PC-02, proposal
    uint256 public constant RETENTION = 365 days; // PC-03, proposal
    uint256 public constant ROLLBACK_WINDOW = 30 days; // registry parameter, proposal
    uint256 public constant MAX_LIVE_ROUTERS = 2; // PC-12

    struct Router {
        uint8 state;
        uint8 reason;
        uint8 prevState;
        uint32 version;
        uint256 group;
        uint256 deprecatedAt;
        uint256 sunsetNotBefore;
        uint256 sunsetAt;
        bytes32 codeHash;
    }

    mapping(address => Router) public routers;
    mapping(uint256 => address[]) internal routerList; // every router ever proposed in the group; never iterated by a state-changing function
    mapping(uint256 => uint256) internal liveByGroup; // |{ r in group : state(r) in {ACTIVE, DEPRECATED} }|, maintained by _setState (O(1) reads)

    mapping(address => bool) internal listed; // set by propose: only a listed router belongs to a group and counts in liveByGroup

    /// Every write of `state` goes through here, so `liveByGroup` can never drift from the states (invariant checked by
    /// `liveCountScan`, the O(n) oracle used by the tests).
    function _setState(address router, uint8 s) internal {
        Router storage r = routers[router];
        if (listed[router]) {
            bool was = r.state == ST_ACTIVE || r.state == ST_DEPRECATED;
            bool now_ = s == ST_ACTIVE || s == ST_DEPRECATED;
            if (was && !now_) liveByGroup[r.group] -= 1;
            if (!was && now_) liveByGroup[r.group] += 1;
        }
        r.state = s;
    }

    // ---- registration
    function propose(address router, bytes32 codeHash, uint32 version, uint256 group) public {
        Router storage r = routers[router];
        if (r.state != ST_UNREGISTERED) revert WrongRouterState();
        _setState(router, ST_CANDIDATE);
        r.codeHash = codeHash;
        r.version = version;
        r.group = group;
        listed[router] = true;
        routerList[group].push(router);
    }

    function activate(address router) public {
        Router storage r = routers[router];
        if (r.state != ST_CANDIDATE) revert WrongRouterState();
        if (liveCount(r.group) >= MAX_LIVE_ROUTERS) revert TooManyLiveRouters();
        _setState(router, ST_ACTIVE);
    }

    /// propose + activate in one call (all or nothing).
    function registerActive(address router, bytes32 codeHash, uint32 version, uint256 group) external {
        if (routers[router].state != ST_UNREGISTERED) revert WrongRouterState();
        if (liveCount(group) >= MAX_LIVE_ROUTERS) revert TooManyLiveRouters();
        propose(router, codeHash, version, group);
        activate(router);
    }

    /// O(1): the number of routers of the group that are ACTIVE or DEPRECATED (PC-12).
    function liveCount(uint256 group) public view returns (uint256) {
        return liveByGroup[group];
    }

    /// The O(n) definition, kept as the oracle that the counter must equal after every operation (tests only: it iterates over every
    /// router ever proposed in the group and must not be called by a state-changing function).
    function liveCountScan(uint256 group) external view returns (uint256 n) {
        address[] storage list = routerList[group];
        // loop-bound: ORACLE | routerList[group].length = routers ever proposed in the group | the O(n) definition of liveCount, kept as the oracle of the O(1) counter; a view for the tests, not reachable from any state-changing function
        for (uint256 i = 0; i < list.length; ++i) {
            uint8 s = routers[list[i]].state;
            if (s == ST_ACTIVE || s == ST_DEPRECATED) n += 1;
        }
    }

    function routerCount(uint256 group) external view returns (uint256) {
        return routerList[group].length;
    }

    // ---- lifecycle
    function notice(uint8 reason) public pure returns (uint256) {
        return reason == REASON_SECURITY ? MIN_NOTICE_SECURITY : MIN_NOTICE_STANDARD;
    }

    function deprecate(address router, address successor, uint8 reason, uint256 sunsetNotBefore, uint256 mutant) external {
        Router storage r = routers[router];
        if (r.state != ST_ACTIVE) revert WrongRouterState();
        if (routers[successor].state != ST_ACTIVE || successor == router) revert SuccessorNotActive();
        uint256 limit = block.timestamp + notice(reason);
        if (sunsetNotBefore == 0) sunsetNotBefore = limit;
        if (mutant != M_REG_NOTICE_SKIP && sunsetNotBefore < limit) revert NoticeTooShort();
        _setState(router, ST_DEPRECATED);
        r.reason = reason;
        r.deprecatedAt = block.timestamp;
        r.sunsetNotBefore = sunsetNotBefore;
    }

    function emergencyDisable(address router) external {
        Router storage r = routers[router];
        if (r.state != ST_ACTIVE && r.state != ST_DEPRECATED) revert WrongRouterState();
        r.prevState = r.state;
        _setState(router, ST_DISABLED);
    }

    function clearEmergency(address router) external {
        Router storage r = routers[router];
        if (r.state != ST_DISABLED) revert WrongRouterState();
        _setState(router, r.prevState);
    }

    function sunset(address router, uint256 mutant) external {
        Router storage r = routers[router];
        if (r.state != ST_DEPRECATED) revert WrongRouterState();
        if (mutant != M_REG_SUNSET_EARLY && block.timestamp < r.sunsetNotBefore) revert NotYetSunset();
        _setState(router, ST_SUNSET);
        r.sunsetAt = block.timestamp;
    }

    function retire(address router, uint256 mutant) external {
        Router storage r = routers[router];
        if (r.state != ST_SUNSET) revert WrongRouterState();
        if (mutant != M_REG_RETIRE_EARLY && block.timestamp < r.sunsetAt + RETENTION) revert RetentionNotElapsed();
        _setState(router, ST_RETIRED);
    }

    /// Test harness: put a router into a state directly (the guards of the lifecycle are covered by their own vectors). The router must
    /// already be registered (propose or registerActive): a router that was never proposed has no group and does not count in liveCount.
    function forceState(address router, uint8 state, uint8 reason, uint256 deprecatedAt) external {
        Router storage r = routers[router];
        _setState(router, state);
        r.reason = reason;
        r.deprecatedAt = deprecatedAt;
        r.sunsetNotBefore = block.timestamp;
        r.sunsetAt = block.timestamp;
    }

    /// Test harness: mark a router SUNSET without touching its other fields (the notice guard has its own vectors).
    function markSunset(address router) external {
        _setState(router, ST_SUNSET);
    }

    // ---- views
    function snap(address router) external view returns (uint8, uint8) {
        Router storage r = routers[router];
        return (r.state, r.reason);
    }

    function stateOf(address router) external view returns (uint8) {
        return routers[router].state;
    }

    function codeHashOf(address router) external view returns (bytes32) {
        return routers[router].codeHash;
    }

    function versionOf(address router) external view returns (uint32) {
        return routers[router].version;
    }

    function isBindable(address router, uint256 mutant) external view returns (bool) {
        Router storage r = routers[router];
        if (r.state == ST_ACTIVE) return true;
        if (r.state == ST_DEPRECATED) {
            if (mutant == M_BIND_DEPR_ALWAYS) return true;
            uint256 end = r.deprecatedAt + ROLLBACK_WINDOW;
            if (mutant == M_BIND_WINDOW_LE) return block.timestamp <= end;
            return block.timestamp < end;
        }
        return false;
    }

    function isChargeable(address router) external view returns (bool) {
        uint8 s = routers[router].state;
        return s == ST_ACTIVE || s == ST_DEPRECATED;
    }

    /// Mode(R) is a function of the registry state only (R3): NORMAL for ACTIVE and for DEPRECATED with reason STANDARD, EMERGENCY for
    /// everything else (fail closed).
    function mode(address router, uint256 mutant) external view returns (uint8) {
        Router storage r = routers[router];
        if (r.state == ST_ACTIVE) return MODE_NORMAL;
        if (r.state == ST_DEPRECATED) {
            if (r.reason == REASON_SECURITY && mutant != M_MODE_SEC_NORMAL) return MODE_EMERGENCY;
            return MODE_NORMAL;
        }
        if (r.state == ST_DISABLED) return mutant == M_MODE_DISABLED_NORMAL ? MODE_NORMAL : MODE_EMERGENCY;
        if (r.state == ST_SUNSET || r.state == ST_RETIRED) return mutant == M_MODE_SUNSET_NORMAL ? MODE_NORMAL : MODE_EMERGENCY;
        return MODE_EMERGENCY;
    }
}
