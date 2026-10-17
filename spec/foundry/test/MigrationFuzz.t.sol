// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import "../src/Errors.sol";
import {ContainModel} from "../src/ContainModel.sol";
import {MigrationModel} from "../src/MigrationModel.sol";
import {Fixture} from "./helpers/Fixture.sol";

/// Document 12 section 5.3.2 (containment K.1..K.9), section 5.3.3 (Lemma M, I-MIG-9), section 5.3 (O1N, O1E, R3), section 5.3.1 (the
/// exposure index, I-MIG-10, MIG-TV-43). Fuzz tests; seeds make every case reproducible.
///
///   testFuzz_LemmaM*                containment against the monotone-authority lemma, with the guard logic of tools/model_checks.py
///                                   restated here as `_acceptsOracle` (independent of ContainModel.accepts)
///   testFuzz_ContainedMatchesOracle containedMask == 0 iff the clauses K.1..K.9 written out as plain booleans
///   testFuzz_OldPermission          O1N / O1E over random allowance states, router modes, sibling counts and kinds
///   testFuzz_RouterMode             Mode(R) of the registry against the table of section 5.3.1
///   testFuzz_ExposureIndex          random activate / migrate / revoke / retire sequences: the index equals the recomputed count
contract MigrationFuzzTest is Test {
    Fixture internal fx;
    address internal t1;
    address internal t2;
    address internal t3;
    address internal t4;
    address internal r0;
    address internal r1;

    function setUp() public {
        vm.warp(1_800_000_000);
        fx = new Fixture();
        t1 = fx.T1();
        t2 = fx.T2();
        t3 = fx.T3();
        t4 = fx.T4();
        r0 = fx.R0();
        r1 = fx.R1();
    }

    // ------------------------------------------------------------------------------------------------------------ generators
    function _r(uint256 seed, uint256 i) internal pure returns (uint256) {
        return uint256(keccak256(abi.encode(seed, i)));
    }

    function _cap(uint256 r) internal pure returns (uint256) {
        return r % 5 == 0 ? 0 : (r / 5) % 1000 + 1;
    }

    function _bump(uint256 x, uint256 r) internal pure returns (uint256) {
        int256[7] memory d = [int256(-3), -1, 0, 0, 0, 1, 3];
        int256 v = int256(x) + d[r % 7];
        return v < 0 ? 0 : uint256(v);
    }

    function _randomTerms(uint256 seed) internal pure returns (ContainModel.Terms memory t) {
        t.expiresAt = uint64(100 + _r(seed, 1) % 900);
        t.merchantId = bytes32(uint256(77));
        t.recipientPolicy = bytes32(uint256(82));
        t.subscriptionRef = bytes32(uint256(83));
        t.periodSeconds = 100;
        t.currency = 840;
        uint256 mask = 1 + _r(seed, 2) % 7;
        uint256 n = 0;
        for (uint256 i = 0; i < 3; ++i) {
            if ((mask >> i) & 1 == 0) continue;
            t.tokens[n] = address(uint160(0x7001 + i));
            for (uint256 f = 0; f < 6; ++f) {
                t.caps[n][f] = _cap(_r(seed, 100 + 10 * i + f));
            }
            n += 1;
        }
        t.nTokens = uint8(n);
        for (uint256 g = 0; g < 6; ++g) {
            uint256 r = _r(seed, 20 + g);
            t.fiat[g] = r % 5 == 0 ? 0 : 1 + (r / 5) % 500;
        }
        t.maxQuoteAge = uint64(10 + _r(seed, 30) % 290);
        t.boundsVersion = uint32(_r(seed, 31) % 6); // 0 (the empty band) .. 5
        t.maxChargesPerPeriod = uint32(_r(seed, 33) % 4);
        t.minInterval = uint64([uint256(0), 10, 100][_r(seed, 34) % 3]);
        t.maxFeeBps = uint16(_r(seed, 35) % 201);
    }

    function _clone(ContainModel.Terms memory s) internal pure returns (ContainModel.Terms memory n) {
        n.expiresAt = s.expiresAt;
        n.periodSeconds = s.periodSeconds;
        n.anchorStartsAt = s.anchorStartsAt;
        n.maxQuoteAge = s.maxQuoteAge;
        n.minInterval = s.minInterval;
        n.maxChargesPerPeriod = s.maxChargesPerPeriod;
        n.currency = s.currency;
        n.maxFeeBps = s.maxFeeBps;
        n.nTokens = s.nTokens;
        n.merchantId = s.merchantId;
        n.recipientPolicy = s.recipientPolicy;
        n.subscriptionRef = s.subscriptionRef;
        n.extensionsHash = s.extensionsHash;
        n.boundsVersion = s.boundsVersion;
        for (uint256 i = 0; i < 3; ++i) {
            n.tokens[i] = s.tokens[i];
            for (uint256 f = 0; f < 6; ++f) {
                n.caps[i][f] = s.caps[i][f];
            }
        }
        for (uint256 g = 0; g < 6; ++g) {
            n.fiat[g] = s.fiat[g];
        }
    }

    /// A random successor: each field changes with some probability, in either direction.
    function _mutate(ContainModel.Terms memory s, uint256 seed) internal pure returns (ContainModel.Terms memory n) {
        n = _clone(s);
        if (_r(seed, 1) % 10 < 4) n.expiresAt = uint64(_bump(n.expiresAt, _r(seed, 2)));
        if (_r(seed, 3) % 20 < 3) n.merchantId = bytes32(uint256(78));
        for (uint256 i = 0; i < n.nTokens; ++i) {
            for (uint256 f = 0; f < 6; ++f) {
                if (_r(seed, 10 + 10 * i + f) % 10 < 3) {
                    n.caps[i][f] = _r(seed, 50 + 10 * i + f) % 2 == 0 ? 0 : _bump(n.caps[i][f], _r(seed, 90 + 10 * i + f));
                }
            }
        }
        for (uint256 g = 0; g < 6; ++g) {
            if (_r(seed, 130 + g) % 10 < 3) n.fiat[g] = _r(seed, 140 + g) % 2 == 0 ? 0 : _bump(n.fiat[g], _r(seed, 150 + g));
        }
        if (_r(seed, 160) % 10 < 3) n.maxQuoteAge = uint64(_bump(n.maxQuoteAge, _r(seed, 161)));
        if (_r(seed, 162) % 10 < 3) n.boundsVersion = uint32(_bump(n.boundsVersion, _r(seed, 163)));
        if (_r(seed, 166) % 10 < 3) n.maxChargesPerPeriod = uint32(_r(seed, 167) % 4);
        if (_r(seed, 168) % 10 < 3) n.minInterval = uint64(_bump(n.minInterval, _r(seed, 169)));
        if (_r(seed, 170) % 10 < 3) n.maxFeeBps = uint16(_bump(n.maxFeeBps, _r(seed, 171)));
        if (_r(seed, 172) % 100 < 3) n.extensionsHash = bytes32(uint256(1));
    }

    /// A successor that is contained by construction: every field on the stricter side.
    function _tighten(ContainModel.Terms memory s, uint256 seed) internal pure returns (ContainModel.Terms memory n) {
        n = _clone(s);
        if (_r(seed, 1) % 2 == 0 && n.expiresAt > 0) n.expiresAt = n.expiresAt - uint64(_r(seed, 2) % 5);
        for (uint256 i = 0; i < n.nTokens; ++i) {
            for (uint256 f = 0; f < 6; ++f) {
                if (n.caps[i][f] > 1 && _r(seed, 10 + 10 * i + f) % 2 == 0) n.caps[i][f] = n.caps[i][f] - 1;
                if (n.caps[i][f] == 0 && _r(seed, 60 + 10 * i + f) % 2 == 0) n.caps[i][f] = 1 + _r(seed, 70 + 10 * i + f) % 1000;
            }
        }
        if (n.maxFeeBps > 0 && _r(seed, 3) % 2 == 0) n.maxFeeBps = n.maxFeeBps - 1;
        // K.6: a contained successor keeps the bounds version (the band of a version never changes)
        n.minInterval = n.minInterval + uint64(_r(seed, 6) % 3);
        if (n.maxQuoteAge > 1 && _r(seed, 7) % 2 == 0) n.maxQuoteAge = n.maxQuoteAge - 1;
        if (n.maxChargesPerPeriod > 1 && _r(seed, 8) % 2 == 0) n.maxChargesPerPeriod = n.maxChargesPerPeriod - 1;
        if (n.maxChargesPerPeriod == 0 && _r(seed, 9) % 2 == 0) n.maxChargesPerPeriod = 3;
        for (uint256 g = 0; g < 6; ++g) {
            if (n.fiat[g] > 1 && _r(seed, 200 + g) % 2 == 0) n.fiat[g] = n.fiat[g] - 1;
            if (n.fiat[g] == 0 && _r(seed, 210 + g) % 2 == 0) n.fiat[g] = 1 + _r(seed, 220 + g) % 500;
        }
    }

    function _randomState(uint256 seed) internal pure returns (ContainModel.State memory st) {
        for (uint256 i = 0; i < 3; ++i) {
            for (uint256 f = 0; f < 5; ++f) {
                st.used[i][f] = _r(seed, 300 + 10 * i + f) % 601;
            }
        }
        for (uint256 g = 0; g < 5; ++g) {
            st.fiatUsed[g] = _r(seed, 340 + g) % 301;
        }
        st.chargesInPeriod = _r(seed, 350) % 4;
    }

    function _randomPayment(uint256 seed) internal pure returns (ContainModel.Payment memory p) {
        p.tokenId = 1 + _r(seed, 400) % 3;
        p.a = 1 + _r(seed, 401) % 1100;
        p.tau = 50 + _r(seed, 402) % 1051;
        p.merchant = _r(seed, 403) % 3 == 0 ? 78 : 77;
        p.hasFiat = _r(seed, 404) % 2 == 0;
        p.fiat = 1 + _r(seed, 405) % 600;
        p.age = 1 + _r(seed, 406) % 320;
        p.price = 85 + _r(seed, 407) % 31;
        p.sinceLast = [uint256(0), 5, 10, 50, 100, 200][_r(seed, 408) % 6];
        p.feeBps = _r(seed, 409) % 211;
    }

    // ------------------------------------------------------------------------------------------------------------ the guard oracle (restated)
    function _le(uint256 a, uint256 b) internal pure returns (bool) {
        return b == 0 || (a != 0 && a <= b);
    }

    function _within(uint256 x, uint256 cap) internal pure returns (bool) {
        return cap == 0 || x <= cap;
    }

    /// The registry of price bands restated (independent of ContainModel.band): published versions 1 .. 5, the empty band otherwise.
    function _bandOracle(uint32 version) internal pure returns (uint256 lo, uint256 hi) {
        uint256[2][5] memory bands = [[uint256(98), 102], [uint256(95), 105], [uint256(96), 104], [uint256(94), 106], [uint256(90), 110]];
        if (version >= 1 && version <= 5) return (bands[version - 1][0], bands[version - 1][1]);
        return (1, 0);
    }

    /// The guards of a charge that depend on the mandate, written without reference to ContainModel.accepts.
    function _acceptsOracle(ContainModel.Terms memory m, ContainModel.State memory st, ContainModel.Payment memory p) internal pure returns (bool) {
        uint256 idx = 99;
        for (uint256 i = 0; i < m.nTokens; ++i) {
            if (m.tokens[i] == address(uint160(0x7000 + p.tokenId))) idx = i;
        }
        if (p.tau >= m.expiresAt || idx == 99 || p.merchant != uint256(m.merchantId)) return false;
        if (!_within(p.a, m.caps[idx][0])) return false;
        // day, week, thirtyDay, period, total: caps[2], caps[3], caps[4], caps[5], caps[1]
        if (!_within(st.used[p.tokenId - 1][0] + p.a, m.caps[idx][2])) return false;
        if (!_within(st.used[p.tokenId - 1][1] + p.a, m.caps[idx][3])) return false;
        if (!_within(st.used[p.tokenId - 1][2] + p.a, m.caps[idx][4])) return false;
        if (!_within(st.used[p.tokenId - 1][3] + p.a, m.caps[idx][5])) return false;
        if (!_within(st.used[p.tokenId - 1][4] + p.a, m.caps[idx][1])) return false;
        if (p.hasFiat) {
            if (!_within(p.fiat, m.fiat[0])) return false;
            if (!_within(st.fiatUsed[0] + p.fiat, m.fiat[2])) return false;
            if (!_within(st.fiatUsed[1] + p.fiat, m.fiat[3])) return false;
            if (!_within(st.fiatUsed[2] + p.fiat, m.fiat[4])) return false;
            if (!_within(st.fiatUsed[3] + p.fiat, m.fiat[5])) return false;
            if (!_within(st.fiatUsed[4] + p.fiat, m.fiat[1])) return false;
            (uint256 lo, uint256 hi) = _bandOracle(m.boundsVersion);
            if (p.age > m.maxQuoteAge || p.price < lo || p.price > hi) return false;
        }
        if (m.maxChargesPerPeriod != 0 && st.chargesInPeriod + 1 > m.maxChargesPerPeriod) return false;
        if (p.sinceLast < m.minInterval || p.feeBps > m.maxFeeBps) return false;
        return m.extensionsHash == bytes32(0);
    }

    /// K.1 .. K.9 as plain booleans.
    function _containedOracle(ContainModel.Terms memory s, ContainModel.Terms memory p) internal pure returns (bool) {
        if (s.expiresAt > p.expiresAt) return false;
        if (s.merchantId != p.merchantId || s.recipientPolicy != p.recipientPolicy || s.subscriptionRef != p.subscriptionRef) return false;
        if (s.periodSeconds != p.periodSeconds || s.anchorStartsAt != p.anchorStartsAt) return false;
        for (uint256 i = 0; i < s.nTokens; ++i) {
            bool found = false;
            for (uint256 j = 0; j < p.nTokens; ++j) {
                if (p.tokens[j] != s.tokens[i]) continue;
                found = true;
                for (uint256 f = 0; f < 6; ++f) {
                    if (!_le(s.caps[i][f], p.caps[j][f])) return false;
                }
            }
            if (!found) return false;
        }
        if (s.currency != p.currency || s.maxQuoteAge > p.maxQuoteAge) return false;
        for (uint256 g = 0; g < 6; ++g) {
            if (!_le(s.fiat[g], p.fiat[g])) return false;
        }
        if (s.boundsVersion != p.boundsVersion) return false;
        if (!_le(s.maxChargesPerPeriod, p.maxChargesPerPeriod) || s.minInterval < p.minInterval) return false;
        if (s.maxFeeBps > p.maxFeeBps) return false;
        return s.extensionsHash == bytes32(0) && p.extensionsHash == bytes32(0);
    }

    // ------------------------------------------------------------------------------------------------------------ containment and Lemma M
    function testFuzz_ContainedMatchesOracle(uint256 seed) public {
        seed = bound(seed, 0, type(uint128).max);      // the seed is added to small offsets below: keep checked arithmetic away from 2^256
        ContainModel.Terms memory pred = _randomTerms(seed);
        ContainModel.Terms memory succ = _mutate(pred, seed + 1);
        assertEq(ContainModel.containedMask(succ, pred, 0) == 0, _containedOracle(succ, pred));
        ContainModel.Terms memory tight = _tighten(pred, seed + 2);
        assertEq(ContainModel.containedMask(tight, pred, 0), 0, "a tightened successor is contained");
    }

    function testFuzz_LemmaM(uint256 seed) public {
        seed = bound(seed, 0, type(uint128).max);
        ContainModel.Terms memory pred = _randomTerms(seed);
        ContainModel.Terms memory succ = _mutate(pred, seed + 1);
        _lemma(succ, pred, seed);
    }

    function testFuzz_LemmaM_Tightened(uint256 seed) public {
        seed = bound(seed, 0, type(uint128).max);
        ContainModel.Terms memory pred = _randomTerms(seed);
        ContainModel.Terms memory succ = _tighten(pred, seed + 1);
        assertEq(ContainModel.containedMask(succ, pred, 0), 0);
        _lemma(succ, pred, seed);
    }

    function _lemma(ContainModel.Terms memory succ, ContainModel.Terms memory pred, uint256 seed) internal {
        if (ContainModel.containedMask(succ, pred, 0) != 0) return;
        for (uint256 k = 0; k < 20; ++k) {
            ContainModel.State memory st = _randomState(seed + 1000 * (k + 1));
            ContainModel.Payment memory p = _randomPayment(seed + 1000 * (k + 1) + 7);
            bool sa = _acceptsOracle(succ, st, p);
            assertEq(sa, ContainModel.accepts(succ, st, p), "the model's guards equal the restated oracle");
            if (sa) assertTrue(_acceptsOracle(pred, st, p), "Lemma M: the predecessor accepts what a contained successor accepts");
        }
    }

    // ------------------------------------------------------------------------------------------------------------ O1N and O1E
    /// allowKind: 0 none, 1 expired, 2 bounded usable, 3 unlimited usable. modeKind: 0 ACTIVE, 1 DEPRECATED standard, 2 DEPRECATED security,
    /// 3 DISABLED_EMERGENCY, 4 SUNSET. kind: 0 NORMAL, 1 EMERGENCY. siblings: other live mandates of the customer on R0 using t1.
    function testFuzz_OldPermission(uint8 allowKind, uint8 modeKind, uint8 siblings, uint8 kind) public {
        allowKind = allowKind % 4;
        modeKind = modeKind % 5;
        siblings = siblings % 4;
        kind = kind % 2;
        (, bytes32 a) = fx.activate(r0, fx.one(t1));
        for (uint256 i = 0; i < siblings; ++i) {
            fx.activate(r0, fx.one(t1));
        }
        fx.grantBounded(t1, r1);
        if (allowKind == 1) fx.grant(t1, r0, 100, vm.getBlockTimestamp() - 1);
        if (allowKind == 2) fx.grant(t1, r0, 100, fx.FAR());
        if (allowKind == 3) fx.grant(t1, r0, type(uint160).max, fx.FAR());
        if (modeKind == 1) fx.reg().deprecate(r0, r1, 0, 0, 0);
        if (modeKind == 2) fx.reg().deprecate(r0, r1, 1, 0, 0);
        if (modeKind == 3) fx.reg().emergencyDisable(r0);
        if (modeKind == 4) {
            fx.reg().deprecate(r0, r1, 0, 0, 0);
            vm.warp(vm.getBlockTimestamp() + 180 days);
            fx.reg().sunset(r0, 0);
        }
        bool emergencyMode = modeKind >= 2;
        bool usable = allowKind >= 2;
        bool unlimited = allowKind == 3;
        bytes4 want = bytes4(0);
        if (kind == 0 && emergencyMode) want = ModeMismatch.selector;
        else if (kind == 0 && siblings == 0 && usable) want = OldPermissionNotRevoked.selector;
        else if (kind == 0 && siblings > 0 && unlimited) want = ResidualAllowanceUnbounded.selector;
        else if (kind == 1 && usable) want = OldPermissionNotRevoked.selector;
        bytes4 got = bytes4(0);
        try fx.migrate(a, kind, r1) {} catch (bytes memory err) {
            got = bytes4(err);
        }
        assertEq(bytes32(got), bytes32(want), "outcome of activateSuccessor against the predicates O1N, O1E and R3");
        if (want == bytes4(0)) {
            // Post3N and Post3E
            (uint256 amount, uint256 expiration) = fx.allowanceOf(t1, r0);
            bool nowUsable = amount > 0 && vm.getBlockTimestamp() <= expiration; // getBlockTimestamp: not cached by via_ir after a vm.warp
            if (kind == 0) {
                assertEq(fx.live(r0, t1), siblings);
                if (siblings == 0) assertFalse(nowUsable);
                else assertTrue(amount < type(uint160).max);
            } else {
                assertFalse(nowUsable);
            }
        }
    }

    function testFuzz_RouterMode(uint8 modeKind) public {
        modeKind = modeKind % 5;
        if (modeKind == 1) fx.reg().deprecate(r0, r1, 0, 0, 0);
        if (modeKind == 2) fx.reg().deprecate(r0, r1, 1, 0, 0);
        if (modeKind == 3) fx.reg().emergencyDisable(r0);
        if (modeKind == 4) {
            fx.reg().deprecate(r0, r1, 0, 0, 0);
            vm.warp(vm.getBlockTimestamp() + 180 days);
            fx.reg().sunset(r0, 0);
        }
        uint8 want = modeKind >= 2 ? 1 : 0;
        assertEq(uint256(fx.reg().mode(r0, 0)), uint256(want));
        assertEq(uint256(fx.reg().mode(r1, 0)), 0, "the other router stays normal");
        assertEq(fx.reg().isChargeable(r0), modeKind != 3 && modeKind != 4);
        assertEq(fx.reg().isBindable(r0, 0), modeKind <= 2);
    }

    // ------------------------------------------------------------------------------------------------------------ the exposure index (MIG-TV-43)
    bytes32[] internal ids;

    function _recount(address router, address token) internal view returns (uint256 n) {
        MigrationModel mgr = fx.mgr();
        for (uint256 i = 0; i < ids.length; ++i) {
            MigrationModel.Mandate memory m = mgr.getMandate(ids[i]);
            if (m.customer != fx.CUSTOMER() || m.router != router || m.status != 0 || m.retired) continue;
            ContainModel.Terms memory t = mgr.mandateTerms(ids[i]);
            for (uint256 j = 0; j < t.nTokens; ++j) {
                if (t.tokens[j] == token) n += 1;
            }
        }
    }

    function _checkIndex() internal {
        address[4] memory toks = [t1, t2, t3, t4];
        address[2] memory routers = [r0, r1];
        for (uint256 r = 0; r < 2; ++r) {
            uint256 exposed = 0;
            for (uint256 k = 0; k < 4; ++k) {
                uint256 want = _recount(routers[r], toks[k]);
                assertEq(fx.live(routers[r], toks[k]), want, "live equals the recomputed count of recorded-active mandates");
                if (want > 0) exposed += 1;
            }
            assertEq(fx.mgr().exposedCount(fx.CUSTOMER(), routers[r]), exposed, "Exposed holds exactly the tokens with a non-zero count");
        }
    }

    function testFuzz_ExposureIndex(uint256 seed) public {
        address[4] memory toks = [t1, t2, t3, t4];
        for (uint256 step = 0; step < 24; ++step) {
            uint256 r = _r(seed, step);
            uint256 choice = r % 6;
            if (choice < 2 || ids.length == 0) {
                uint256 mask = 1 + (r / 7) % 15;
                address[] memory list = new address[](_popcount(mask) > 3 ? 3 : _popcount(mask));
                uint256 n = 0;
                for (uint256 k = 0; k < 4 && n < list.length; ++k) {
                    if ((mask >> k) & 1 == 1) {
                        list[n] = toks[k];
                        n += 1;
                    }
                }
                ContainModel.Terms memory nt = fx.baseTerms(list);
                if ((r / 29) % 3 == 0) nt.expiresAt = uint64(vm.getBlockTimestamp() + 1 + (r / 31) % 1_500_000); // a short-lived mandate: retire becomes reachable
                (, bytes32 mid) = fx.activateTerms(fx.CUSTOMER(), (r / 3) % 2 == 0 ? r0 : r1, nt);
                ids.push(mid);
            } else {
                bytes32 id = ids[(r / 11) % ids.length];
                if (choice == 2) {
                    try fx.revoke(id) {} catch {}
                } else if (choice == 3) {
                    vm.warp(vm.getBlockTimestamp() + (r / 13) % 2_000_000 + 1);
                    try fx.retire(id) {} catch {}
                } else {
                    MigrationModel mgr = fx.mgr();
                    MigrationModel.Mandate memory m = mgr.getMandate(id);
                    ContainModel.Terms memory t = mgr.mandateTerms(id);
                    address to = m.router == r0 ? r1 : r0;
                    for (uint256 j = 0; j < t.nTokens; ++j) {
                        fx.grantBounded(t.tokens[j], to);
                        if ((r / 17) % 2 == 0) fx.lock(t.tokens[j], m.router);
                    }
                    try fx.migrate(id, uint8(choice == 4 ? 0 : 1), to) returns (bytes32 nid) {
                        ids.push(nid);
                    } catch {}
                }
            }
            _checkIndex();
        }
    }

    function _popcount(uint256 x) internal pure returns (uint256 n) {
        while (x != 0) {
            n += x & 1;
            x >>= 1;
        }
    }
}
