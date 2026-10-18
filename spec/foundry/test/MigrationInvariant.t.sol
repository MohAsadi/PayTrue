// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import {Vm} from "forge-std/Vm.sol";
import "../src/Errors.sol";
import {ContainModel} from "../src/ContainModel.sol";
import {MigrationModel} from "../src/MigrationModel.sol";
import {Fixture} from "./helpers/Fixture.sol";

/// Stateful invariants of the migration model (document 12 section 12): I-MIG-1, I-MIG-3, I-MIG-7, I-MIG-8, I-MIG-10, I-MIG-11 and
/// "the exposure index never under-counts". A Handler performs random grants, lockdowns, expiries, charges, activations, successor
/// activations of both kinds, revocations, retirements and guardian actions on the model; the invariants are checked after every call.
/// Postconditions of a single successful activation (Post3N, Post3E, Post6) are recorded by the Handler in ghost flags, because they
/// compare the state before and after one call.
contract MigrationHandler {
    Vm internal constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));

    Fixture public fx;
    bytes32[] public ids; // every mandate of every generation
    bytes32[] public lineageList;
    mapping(bytes32 => bool) public isLineage;
    mapping(bytes32 => mapping(address => uint256)) public ghostUsed;
    uint256 public cycle = 1;

    bool public violatedPost3;
    bool public violatedNonInterference;
    bool public countersDecreased;
    uint256 public successfulMigrations;

    constructor(Fixture fx_) {
        fx = fx_;
    }

    function idsLength() external view returns (uint256) {
        return ids.length;
    }

    function lineageCount() external view returns (uint256) {
        return lineageList.length;
    }

    function _token(uint8 sel) internal view returns (address) {
        return address(uint160(0x7001 + (sel % 4)));
    }

    function _router(uint8 sel) internal view returns (address) {
        return sel % 2 == 0 ? fx.R0() : fx.R1();
    }

    // ---- customer actions on Permit2
    function grant(uint8 tokenSel, uint8 routerSel, uint8 kind) external {
        address t = _token(tokenSel);
        address r = _router(routerSel);
        if (kind % 4 == 0) fx.lock(t, r);
        else if (kind % 4 == 1) fx.grant(t, r, 100, fx.FAR());
        else if (kind % 4 == 2) fx.grant(t, r, type(uint160).max, fx.FAR());
        else if (vm.getBlockTimestamp() > 1) fx.grant(t, r, 100, vm.getBlockTimestamp() - 1);
    }

    function warp(uint32 dt) external {
        vm.warp(vm.getBlockTimestamp() + (uint256(dt) % 1_000_000) + 1);
    }

    // ---- mandates
    function activate(uint8 routerSel, uint8 tokenMask, uint8 expirySel) external {
        uint256 mask = 1 + (uint256(tokenMask) % 15);
        address[] memory list = new address[](3);
        uint256 n = 0;
        for (uint256 k = 0; k < 4 && n < 3; ++k) {
            if ((mask >> k) & 1 == 1) {
                list[n] = _token(uint8(k));
                n += 1;
            }
        }
        address[] memory exact = new address[](n);
        for (uint256 i = 0; i < n; ++i) {
            exact[i] = list[i];
        }
        ContainModel.Terms memory nt = fx.baseTerms(exact);
        // every third mandate is short-lived, so that expiry and retire() are reachable within the 64 calls of an invariant run
        if (expirySel % 3 == 0) nt.expiresAt = uint64(vm.getBlockTimestamp() + 1 + (uint256(expirySel) * 4_000) % 400_000);
        try fx.activateTerms(fx.CUSTOMER(), _router(routerSel), nt) returns (bytes32 lid, bytes32 mid) {
            ids.push(mid);
            lineageList.push(lid);
            isLineage[lid] = true;
        } catch {}
    }

    function charge(uint8 idSel, uint8 amountSel) external {
        if (ids.length == 0) return;
        bytes32 id = ids[idSel % ids.length];
        MigrationModel.Mandate memory m = fx.mgr().getMandate(id);
        ContainModel.Terms memory t = fx.mgr().mandateTerms(id);
        address token = t.tokens[0];
        uint256 amount = 1 + (uint256(amountSel) % 50);
        try fx.charge(id, m.router, token, amount, cycle) {
            cycle += 1;
            uint256 used = fx.mgr().usedTotal(m.lineageId, token);
            if (used < ghostUsed[m.lineageId][token]) countersDecreased = true;
            ghostUsed[m.lineageId][token] = used;
        } catch {}
    }

    function revoke(uint8 idSel) external {
        if (ids.length == 0) return;
        try fx.revoke(ids[idSel % ids.length]) {} catch {}
    }

    function retire(uint8 idSel) external {
        if (ids.length == 0) return;
        try fx.retire(ids[idSel % ids.length]) {} catch {}
    }

    // ---- guardian and governance
    function disableRouter(uint8 routerSel) external {
        try fx.reg().emergencyDisable(_router(routerSel)) {} catch {}
    }

    function deprecateRouter(uint8 reasonSel) external {
        try fx.reg().deprecate(fx.R0(), fx.R1(), reasonSel % 2, 0, 0) {} catch {}
    }

    // ---- the rest of the registry lifecycle, so that the O(1) live counter is exercised on every transition
    function clearRouter(uint8 routerSel) external {
        try fx.reg().clearEmergency(_router(routerSel)) {} catch {}
    }

    function sunsetRouter(uint8 routerSel) external {
        try fx.reg().sunset(_router(routerSel), 0) {} catch {}
    }

    function retireRouter(uint8 routerSel) external {
        try fx.reg().retire(_router(routerSel), 0) {} catch {}
    }

    function registerRouter(uint8 sel) external {
        try fx.reg().registerActive(address(uint160(0x2000 + (sel % 4))), bytes32(uint256(sel)), 3, 0) {} catch {}
    }

    // ---- activateSuccessor, with the postconditions recorded
    function migrate(uint8 idSel, uint8 kindSel) external {
        if (ids.length == 0) return;
        bytes32 pid = ids[idSel % ids.length];
        uint8 kind = kindSel % 2;
        MigrationModel.Mandate memory p = fx.mgr().getMandate(pid);
        ContainModel.Terms memory pt = fx.mgr().mandateTerms(pid);
        address rold = p.router;
        address rnew = rold == fx.R0() ? fx.R1() : fx.R0();
        for (uint256 i = 0; i < pt.nTokens; ++i) {
            fx.grantBounded(pt.tokens[i], rnew); // fund the new router so that success is reachable
        }
        bytes32 before = _outside(p.lineageId);
        bool[4] memory wasExposed;
        for (uint256 k = 0; k < 4; ++k) {
            wasExposed[k] = fx.live(rold, _token(uint8(k))) > 0;
        }
        try fx.migrate(pid, kind, rnew) returns (bytes32 nid) {
            ids.push(nid);
            successfulMigrations += 1;
            if (_outside(p.lineageId) != before) violatedNonInterference = true;
            _checkPost3(pt, rold, kind, wasExposed);
        } catch {}
    }

    function _checkPost3(ContainModel.Terms memory pt, address rold, uint8 kind, bool[4] memory wasExposed) internal {
        for (uint256 i = 0; i < pt.nTokens; ++i) {
            (uint256 amount, uint256 expiration) = fx.allowanceOf(pt.tokens[i], rold);
            bool usable = amount > 0 && vm.getBlockTimestamp() <= expiration;
            uint256 liveAfter = fx.live(rold, pt.tokens[i]);
            if (kind == 0) {
                if (liveAfter == 0 && usable) violatedPost3 = true;
                if (liveAfter > 0 && amount >= type(uint160).max) violatedPost3 = true;
            }
        }
        if (kind == 1) {
            for (uint256 k = 0; k < 4; ++k) {
                if (!wasExposed[k]) continue;
                (uint256 amount2, uint256 expiration2) = fx.allowanceOf(_token(uint8(k)), rold);
                if (amount2 > 0 && vm.getBlockTimestamp() <= expiration2) violatedPost3 = true;
            }
        }
    }

    /// A digest of everything a successful activation must not change: the customer's allowances (every token, every router) and every
    /// mandate and lineage other than the migrating lineage.
    function _outside(bytes32 migrating) internal view returns (bytes32 acc) {
        address[3] memory routers = [fx.R0(), fx.R1(), fx.R2()];
        for (uint256 t = 0; t < 4; ++t) {
            for (uint256 r = 0; r < 3; ++r) {
                (uint256 amount, uint256 expiration) = fx.allowanceOf(_token(uint8(t)), routers[r]);
                acc = keccak256(abi.encode(acc, amount, expiration));
            }
        }
        for (uint256 i = 0; i < ids.length; ++i) {
            MigrationModel.Mandate memory m = fx.mgr().getMandate(ids[i]);
            if (m.lineageId == migrating) continue;
            acc = keccak256(abi.encode(acc, fx.mgr().mandateDigest(ids[i])));
        }
        for (uint256 j = 0; j < lineageList.length; ++j) {
            if (lineageList[j] == migrating) continue;
            acc = keccak256(abi.encode(acc, fx.mgr().lineageDigest(lineageList[j])));
        }
    }
}

contract MigrationInvariantTest is Test {
    Fixture internal fx;
    MigrationHandler internal handler;

    function setUp() public {
        vm.warp(1_800_000_000);
        fx = new Fixture();
        handler = new MigrationHandler(fx);
        targetContract(address(handler));
    }

    function _routers() internal view returns (address[3] memory) {
        return [fx.R0(), fx.R1(), fx.R2()];
    }

    function _token(uint256 k) internal pure returns (address) {
        return address(uint160(0x7001 + k));
    }

    /// I-MIG-1: a lineage has at most one ACTIVE mandate, and it is the lineage's active mandate.
    function invariant_I_MIG_1_AtMostOneActiveMandatePerLineage() public {
        for (uint256 j = 0; j < handler.lineageCount(); ++j) {
            bytes32 lid = handler.lineageList(j);
            uint256 count = fx.mgr().mandateCount(lid);
            uint256 active = 0;
            for (uint256 i = 0; i < count; ++i) {
                bytes32 id = fx.mgr().lineageMandateIds(lid, i);
                MigrationModel.Mandate memory m = fx.mgr().getMandate(id);
                if (m.status == 0) {
                    active += 1;
                    assertEq(id, fx.mgr().activeMandateOf(lid), "the only ACTIVE mandate is the lineage's active one");
                }
            }
            assertLe(active, 1);
        }
    }

    /// I-MIG-3: lineage counters are never reduced by a successor.
    function invariant_I_MIG_3_CountersNeverDecrease() public {
        assertFalse(handler.countersDecreased());
    }

    /// I-MIG-7: after a successful migration the old allowance obeys O1N (kind NORMAL) or O1E (kind EMERGENCY): Post3N and Post3E.
    function invariant_I_MIG_7_SharedAllowanceRule() public {
        assertFalse(handler.violatedPost3());
    }

    /// I-MIG-8: at most one router can pull under FastPay authority for a lineage.
    function invariant_I_MIG_8_NoOverlappingAuthority() public {
        address[3] memory routers = _routers();
        for (uint256 j = 0; j < handler.lineageCount(); ++j) {
            bytes32 lid = handler.lineageList(j);
            uint256 n = 0;
            for (uint256 r = 0; r < 3; ++r) {
                if (fx.authRouter(lid, routers[r])) n += 1;
            }
            assertLe(n, 1, "AuthRouters(L) has at most one element");
        }
    }

    /// I-MIG-8 restated (document 12 section 5.5, Claim 1): Exec3(L) = the routers on which some mandate of L is consumable (Layer 3
    /// authority; Permit2 is not consulted) has at most one element. Layer 2 allowances are not part of it and may coexist.
    function invariant_I_MIG_8_Exec3AtMostOneRouterPerLineage() public {
        address[3] memory routers = _routers();
        for (uint256 j = 0; j < handler.lineageCount(); ++j) {
            bytes32 lid = handler.lineageList(j);
            uint256 count = fx.mgr().mandateCount(lid);
            uint256 n = 0;
            for (uint256 r = 0; r < 3; ++r) {
                bool any = false;
                for (uint256 i = 0; i < count; ++i) {
                    if (fx.mgr().isConsumable(fx.mgr().lineageMandateIds(lid, i), routers[r])) any = true;
                }
                if (any) n += 1;
                // AuthRouters(L) is a subset of Exec3(L)
                if (fx.authRouter(lid, routers[r])) assertTrue(any, "an authorized router executes at Layer 3");
            }
            assertLe(n, 1, "|Exec3(L)| <= 1");
        }
    }

    /// The exposure index is a dense array with a position map: every listed token has the position recorded for it, every other token
    /// has none, and the list never exceeds MAX_EXPOSED_TOKENS_PER_ROUTER (the bound that keeps the emergency predicate O1E bounded).
    function invariant_ExposureListIsDenseAndBounded() public {
        address[3] memory routers = _routers();
        for (uint256 r = 0; r < 3; ++r) {
            uint256 n = fx.mgr().exposedCount(fx.CUSTOMER(), routers[r]);
            assertLe(n, fx.mgr().MAX_EXPOSED_TOKENS_PER_ROUTER());
            for (uint256 i = 0; i < n; ++i) {
                address t = fx.mgr().exposedAt(fx.CUSTOMER(), routers[r], i);
                assertEq(fx.mgr().exposedPos(fx.CUSTOMER(), routers[r], t), i + 1, "the recorded position is the position");
                assertGt(fx.live(routers[r], t), 0, "a listed token is live");
            }
            for (uint256 k = 0; k < 4; ++k) {
                if (fx.live(routers[r], _token(k)) == 0) assertEq(fx.mgr().exposedPos(fx.CUSTOMER(), routers[r], _token(k)), 0, "an unlisted token has no position");
            }
        }
    }

    /// The registry's O(1) live counter equals its O(n) definition after every operation of the handler.
    function invariant_RegistryLiveCounterEqualsScan() public {
        assertEq(fx.reg().liveCount(0), fx.reg().liveCountScan(0));
    }

    /// I-MIG-10: live(C, R, t) equals the number of recorded-active mandates and is never below the true live number.
    function invariant_I_MIG_10_ExposureIndexExact() public {
        address[3] memory routers = _routers();
        for (uint256 r = 0; r < 3; ++r) {
            uint256 exposed = 0;
            for (uint256 k = 0; k < 4; ++k) {
                (uint256 recorded, uint256 trulyLive) = _recount(routers[r], _token(k));
                assertEq(fx.live(routers[r], _token(k)), recorded);
                assertGe(fx.live(routers[r], _token(k)), trulyLive, "the exposure index never under-counts");
                if (recorded > 0) exposed += 1;
            }
            assertEq(fx.mgr().exposedCount(fx.CUSTOMER(), routers[r]), exposed);
            assertLe(exposed, 8);
        }
    }

    /// I-MIG-11: a successful activation changed no allowance, no sibling mandate and no sibling lineage.
    function invariant_I_MIG_11_NonInterference() public {
        assertFalse(handler.violatedNonInterference());
    }

    function _recount(address router, address token) internal view returns (uint256 recorded, uint256 trulyLive) {
        for (uint256 i = 0; i < handler.idsLength(); ++i) {
            bytes32 id = handler.ids(i);
            MigrationModel.Mandate memory m = fx.mgr().getMandate(id);
            if (m.customer != fx.CUSTOMER() || m.router != router || m.status != 0 || m.retired) continue;
            ContainModel.Terms memory t = fx.mgr().mandateTerms(id);
            for (uint256 j = 0; j < t.nTokens; ++j) {
                if (t.tokens[j] != token) continue;
                recorded += 1;
                if (vm.getBlockTimestamp() < t.expiresAt) trulyLive += 1;
            }
        }
    }
}
