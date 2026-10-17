// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.24;

import {Builders} from "./helpers/Builders.sol";
import {MockERC20} from "./helpers/MockERC20.sol";
import {IP2} from "./helpers/Base.sol";
import {FastPayTypes as T} from "../src/generated/FastPayTypes.sol";
import {IMandateManager} from "../src/interfaces/IMandateManager.sol";
import {PaymentRouter} from "../src/PaymentRouter.sol";

/// Stateful fuzzing of the real contracts. The test contract is its own handler: `h_*` functions apply random lifecycle operations (activate,
/// revoke, retire, reduce, pause, migrate in both modes, charge, warp) as one of two customers on one of two routers over four tokens, and a
/// ghost list remembers every mandate that was ever created. After every sequence the invariants are recomputed FROM THE GHOST LIST, not from
/// the contract's own bookkeeping:
///   * the exposure index live(C, R, t) equals the number of live mandates of C on R that use t, and its list is exact and bounded (I-MIG-10);
///   * a lineage has at most one ACTIVE mandate, and it is the lineage's active mandate (I-MIG-1);
///   * at most one router can charge a lineage at any time (Exec3);
///   * a superseded predecessor is revoked as superseded, and a mandate never goes back to ACTIVE (monotone);
///   * the usage counters equal what was charged and never exceed the caps (I-CAP-TOKEN);
///   * the tokens are conserved and the routers hold none (I-ZEROBAL).
contract InvariantsTest is Builders {
    uint256 constant NTOK = 4;
    uint256 constant MAX_GHOST = 60;

    MockERC20[] pool;
    address[2] customers;
    PaymentRouter[2] routerOf;

    bytes32[] ghost;
    mapping(bytes32 => bytes) termsBlob; // abi.encode(MandateTerms) of the terms the mandate was created with (reduce updates it)
    mapping(bytes32 => uint8) liveStatus; // ghost: the last status seen, to check monotonicity
    mapping(bytes32 => bytes32) lastCycleSeen;
    mapping(bytes32 => mapping(address => uint256)) charged; // lineageId => token => total charged
    uint256 minted;
    uint64 nextCycle;
    /// How many operations of each kind actually succeeded in this run (0 activate, 1 revoke, 2 retire, 3 reduce, 4 pause, 5 resume, 6 normal, 7 emergency, 8 charge).
    uint256[9] hits;
    bytes4[] refusedMigrations;
    bytes4[] refusedCharges;
    /// Debugging aid: when set, h_migrate does not swallow the revert (a subclass uses it to look at one refusal).
    bool internal strict;

    function setUp() public override {
        super.setUp();
        routerOf[0] = routerA;
        routerOf[1] = routerB;
        customers[0] = customer;
        customers[1] = makeAddr("customer2");
        for (uint256 i = 0; i < NTOK; ++i) {
            pool.push(new MockERC20());
        }
        for (uint256 i = 0; i < NTOK; ++i) {
            for (uint256 j = i + 1; j < NTOK; ++j) {
                if (uint160(address(pool[j])) < uint160(address(pool[i]))) (pool[i], pool[j]) = (pool[j], pool[i]);
            }
        }
        vm.startPrank(gov);
        for (uint256 i = 0; i < NTOK; ++i) {
            policy.list(address(pool[i]), 1, 6);
        }
        vm.stopPrank();
        vm.startPrank(merchantAdmin);
        for (uint256 i = 0; i < NTOK; ++i) {
            merchantReg.setAccepted(MERCHANT, address(pool[i]), true);
        }
        vm.stopPrank();
        for (uint256 c = 0; c < 2; ++c) {
            for (uint256 i = 0; i < NTOK; ++i) {
                _fund(customers[c], pool[i], 1_000_000e6);
                minted += 1_000_000e6;
                for (uint256 r = 0; r < 2; ++r) {
                    _grant(customers[c], pool[i], address(routerOf[r]), 100_000e6);
                }
            }
        }
        bytes4[] memory sels = new bytes4[](10);
        sels[0] = this.h_activate.selector;
        sels[1] = this.h_revoke.selector;
        sels[2] = this.h_retire.selector;
        sels[3] = this.h_reduce.selector;
        sels[4] = this.h_pause.selector;
        sels[5] = this.h_migrate.selector;
        sels[6] = this.h_charge.selector;
        sels[7] = this.h_warp.selector;
        sels[8] = this.h_lock.selector;
        sels[9] = this.h_grant.selector;
        targetSelector(FuzzSelector({addr: address(this), selectors: sels}));
        targetContract(address(this));
    }

    // ------------------------------------------------------------------------------------------------------------ the operations
    function _subset(uint256 seed) internal view returns (address[] memory t) {
        uint256 mask = (seed % 15) + 1; // a non-empty subset of four tokens, at most three of them
        uint256 n;
        for (uint256 i = 0; i < NTOK; ++i) {
            if (mask & (1 << i) != 0) n++;
        }
        if (n > 3) {
            mask &= ~uint256(1 << (seed % NTOK));
            n = 0;
            for (uint256 i = 0; i < NTOK; ++i) {
                if (mask & (1 << i) != 0) n++;
            }
            if (mask == 0 || n == 0 || n > 3) mask = 1;
        }
        n = 0;
        for (uint256 i = 0; i < NTOK; ++i) {
            if (mask & (1 << i) != 0) n++;
        }
        t = new address[](n);
        uint256 k;
        for (uint256 i = 0; i < NTOK; ++i) {
            if (mask & (1 << i) != 0) t[k++] = address(pool[i]);
        }
    }

    function _noFiat(T.MandateTerms memory t) internal view {
        t.fiat = T.FiatTerms(USD, 0, 0, 0, 0, 0, 0, 120, 1);
        t.minIntervalSeconds = 0;
        t.maxChargesPerPeriod = 0;
        t.anchorStartsAt = uint64(START);
        t.expiresAt = uint64(block.timestamp + 365 days);
    }

    function _remember(bytes32 mid, T.MandateTerms memory t) internal {
        ghost.push(mid);
        termsBlob[mid] = abi.encode(t);
    }

    function h_activate(uint256 seed) external {
        if (ghost.length >= MAX_GHOST) return;
        address c = customers[seed % 2];
        PaymentRouter r = routerOf[(seed >> 1) % 2];
        T.MandateTerms memory t = _termsOf(_subset(seed >> 8));
        _noFiat(t);
        t.subscriptionRef = keccak256(abi.encode("sub", seed % 5)); // a few subscriptions per customer
        uint256 creationNonce = ghost.length + 1;
        vm.prank(c);
        try manager.activate(c, creationNonce, address(r), t, _pin()) returns (bytes32, bytes32 mid) {
            hits[0]++;
            _remember(mid, t);
        } catch {}
    }

    function _pick(uint256 seed) internal view returns (bool ok, bytes32 id) {
        if (ghost.length == 0) return (false, 0);
        return (true, ghost[seed % ghost.length]);
    }

    /// The first mandate from a random start that can still act: ACTIVE, not retired, not expired (so that the operations that need a live mandate
    /// are exercised, not only refused).
    function _pickActive(uint256 seed) internal view returns (bool, bytes32) {
        return _pickLive(seed, false);
    }

    function _pickLive(uint256 seed, bool unpaused) internal view returns (bool, bytes32) {
        uint256 n = ghost.length;
        for (uint256 i = 0; i < n; ++i) {
            bytes32 id = ghost[(seed + i) % n];
            IMandateManager.MandateView memory v = _view(id);
            if (v.status == 0 && !v.retired && v.expiresAt > block.timestamp && (!unpaused || v.pause == 0)) return (true, id);
        }
        return (false, 0);
    }

    function h_revoke(uint256 seed) external {
        if (seed % 4 != 0) return; // exits are rarer than the operations that need a live mandate
        (bool ok, bytes32 id) = _pick(seed >> 2);
        if (!ok) return;
        address c = _view(id).customer;
        vm.prank(c);
        try manager.revoke(c, id) {
            hits[1]++;
        } catch {}
    }

    function h_retire(uint256 seed) external {
        (bool ok, bytes32 id) = _pick(seed);
        if (!ok) return;
        try manager.retire(id) {
            hits[2]++;
        } catch {}
    }

    function h_pause(uint256 seed) external {
        (bool ok, bytes32 id) = _pickActive(seed);
        if (!ok) return;
        address c = _view(id).customer;
        vm.prank(c);
        if (seed % 2 == 0) {
            try manager.pause(c, id) {
                hits[4]++;
            } catch {}
        } else {
            try manager.resume(c, id) {
                hits[5]++;
            } catch {}
        }
    }

    function h_warp(uint256 seed) external {
        if (seed % 5 != 0) return; // time moves rarely, so that a mandate lives long enough for the other operations to meet it
        vm.warp(block.timestamp + (seed % 40 == 0 ? 400 days : ((seed >> 8) % 20 days) + 1)); // now and then past every expiry, so that retire has work
    }

    function h_lock(uint256 seed) external {
        address c = customers[seed % 2];
        PaymentRouter r = routerOf[(seed >> 1) % 2];
        IP2.TokenSpenderPair[] memory pairs = new IP2.TokenSpenderPair[](NTOK);
        for (uint256 i = 0; i < NTOK; ++i) {
            pairs[i] = IP2.TokenSpenderPair(address(pool[i]), address(r));
        }
        vm.prank(c);
        p2.lockdown(pairs);
    }

    function h_reduce(uint256 seed) external {
        (bool ok, bytes32 id) = _pickActive(seed);
        if (!ok) return;
        IMandateManager.MandateView memory v = _view(id);
        if (v.nTokens < 2) return;
        T.MandateTerms memory old = abi.decode(termsBlob[id], (T.MandateTerms));
        address[] memory kept = new address[](old.tokens.length - 1);
        uint256 drop = (seed >> 8) % old.tokens.length;
        uint256 k;
        for (uint256 i = 0; i < old.tokens.length; ++i) {
            if (i != drop) kept[k++] = old.tokens[i].token;
        }
        T.MandateTerms memory n = _termsOf(kept);
        _noFiat(n);
        n.subscriptionRef = old.subscriptionRef;
        n.expiresAt = old.expiresAt;
        vm.prank(v.customer);
        try manager.reduce(v.customer, id, old, n) {
            hits[3]++;
            termsBlob[id] = abi.encode(n);
        } catch {}
    }

    function h_migrate(uint256 seed) external {
        if (ghost.length >= MAX_GHOST) return;
        (bool ok, bytes32 id) = _pickActive(seed);
        if (!ok) return;
        IMandateManager.MandateView memory v = _view(id);
        address c = v.customer;
        PaymentRouter oldR = PaymentRouter(v.router);
        PaymentRouter newR = oldR == routerA ? routerB : routerA;
        T.MandateTerms memory pt = abi.decode(termsBlob[id], (T.MandateTerms));
        T.MandateTerms memory nt = abi.decode(termsBlob[id], (T.MandateTerms));
        uint8 kind = (seed >> 4) % 2 == 0 ? NORMAL : EMERGENCY;
        // S1 and S2: the customer prepares the grants the predicates ask for; a fifth of the time the preparation is skipped, so that the refusals
        // are exercised too
        if ((seed >> 5) % 5 != 0) _prepareMigration(c, oldR, newR, pt, kind);
        T.AccountPin memory p = _pin();
        deadline = uint64(block.timestamp + 1 days); // the authorization is fresh whatever the warps did
        T.SuccessorAuthorization memory a = _auth(Sp(v.lineageId, id, v.predecessorId, v.generation, kind, address(newR)), pt, nt, p);
        IMandateManager.SuccessorRequest memory r = _req(pt, p, nt, _pin(), a);
        if (strict) {
            vm.prank(c);
            bytes32 sid = manager.activateSuccessor(c, r);
            hits[kind == NORMAL ? 6 : 7]++;
            _remember(sid, nt);
            return;
        }
        vm.prank(c);
        try manager.activateSuccessor(c, r) returns (bytes32 nid) {
            hits[kind == NORMAL ? 6 : 7]++;
            _remember(nid, nt);
        } catch (bytes memory reason) {
            refusedMigrations.push(bytes4(reason));
        }
    }

    function _prepareMigration(address c, PaymentRouter oldR, PaymentRouter newR, T.MandateTerms memory pt, uint8 kind) internal {
        vm.startPrank(c);
        for (uint256 i = 0; i < pt.tokens.length; ++i) {
            p2.approve(pt.tokens[i].token, address(newR), 100_000e6, uint48(block.timestamp + 400 days));
        }
        vm.stopPrank();
        // NORMAL: lock the tokens that no sibling uses; EMERGENCY: lock every token that the customer has on the old router
        uint256 n;
        IP2.TokenSpenderPair[] memory pairs = new IP2.TokenSpenderPair[](NTOK);
        for (uint256 i = 0; i < NTOK; ++i) {
            address t = address(pool[i]);
            bool inPred;
            for (uint256 k = 0; k < pt.tokens.length; ++k) {
                if (pt.tokens[k].token == t) inPred = true;
            }
            uint32 lv = manager.live(c, address(oldR), t);
            bool lock = kind == EMERGENCY ? lv > 0 : (inPred && lv == 1);
            if (lock) pairs[n++] = IP2.TokenSpenderPair(t, address(oldR));
        }
        if (n > 0) {
            IP2.TokenSpenderPair[] memory exact = new IP2.TokenSpenderPair[](n);
            for (uint256 j = 0; j < n; ++j) {
                exact[j] = pairs[j];
            }
            vm.prank(c);
            p2.lockdown(exact);
        }
    }

    /// The customer renews the grants of a router (a lockdown or an expiry would otherwise starve every later charge).
    function h_grant(uint256 seed) external {
        address c = customers[seed % 2];
        PaymentRouter r = routerOf[(seed >> 1) % 2];
        vm.startPrank(c);
        for (uint256 i = 0; i < NTOK; ++i) {
            p2.approve(address(pool[i]), address(r), 100_000e6, uint48(block.timestamp + 400 days));
        }
        vm.stopPrank();
    }

    function h_charge(uint256 seed) external {
        (bool ok, bytes32 id) = _pickLive(seed, seed % 5 != 0); // mostly mandates that are not paused; sometimes one that is, to see the refusal
        if (!ok) return;
        IMandateManager.MandateView memory v = _view(id);
        T.MandateTerms memory t = abi.decode(termsBlob[id], (T.MandateTerms));
        address tok = t.tokens[(seed >> 8) % t.tokens.length].token;
        uint256 amount = ((seed >> 16) % 120e6) + 1;
        uint64 cycle = uint64((seed >> 40) % (((block.timestamp - t.anchorStartsAt) / t.periodSeconds) + 1));
        PaymentRouter r = PaymentRouter(v.router);
        uint256 beforeBal = MockERC20(tok).balanceOf(v.customer);
        vm.prank(executor);
        try r.charge(PaymentRouter.ChargeRequest(id, cycle, tok, amount, 0), t, _pin(), _noQuote()) {
            hits[8]++;
            charged[v.lineageId][tok] += amount;
            assertEq(beforeBal - MockERC20(tok).balanceOf(v.customer), amount, "the customer paid exactly the amount");
        } catch (bytes memory reason) {
            refusedCharges.push(bytes4(reason));
        }
    }

    /// Coverage: what the run actually did. Printed so that a campaign that only ever hits the failing branches cannot pass unnoticed.
    function afterInvariant() public {
        emit log_named_uint("coverage: activate", hits[0]);
        emit log_named_uint("coverage: revoke", hits[1]);
        emit log_named_uint("coverage: retire", hits[2]);
        emit log_named_uint("coverage: reduce", hits[3]);
        emit log_named_uint("coverage: pause", hits[4]);
        emit log_named_uint("coverage: resume", hits[5]);
        emit log_named_uint("coverage: normal migration", hits[6]);
        emit log_named_uint("coverage: emergency migration", hits[7]);
        emit log_named_uint("coverage: charge", hits[8]);
        emit log_named_uint("coverage: mandates in the ghost list", ghost.length);
        for (uint256 i = 0; i < refusedMigrations.length; ++i) emit log_named_bytes32("coverage: migration refused with", bytes32(refusedMigrations[i]));
        for (uint256 i = 0; i < refusedCharges.length; ++i) emit log_named_bytes32("coverage: charge refused with", bytes32(refusedCharges[i]));
    }

    // ------------------------------------------------------------------------------------------------------------ the invariants
    function invariant_ExposureIndexIsExact() public view {
        for (uint256 c = 0; c < 2; ++c) {
            for (uint256 r = 0; r < 2; ++r) {
                uint256 distinct;
                for (uint256 i = 0; i < NTOK; ++i) {
                    address t = address(pool[i]);
                    uint256 expected;
                    for (uint256 g = 0; g < ghost.length; ++g) {
                        IMandateManager.MandateView memory v = _view(ghost[g]);
                        if (v.customer != customers[c] || v.router != address(routerOf[r]) || v.status != 0 || v.retired) continue;
                        for (uint256 k = 0; k < v.nTokens; ++k) {
                            if (v.tokens[k] == t) expected++;
                        }
                    }
                    assertEq(manager.live(customers[c], address(routerOf[r]), t), expected, "live(C, R, t) is the number of live mandates that use t");
                    if (expected > 0) distinct++;
                    assertEq(manager.exposedPos(customers[c], address(routerOf[r]), t) != 0, expected > 0, "the position map agrees");
                }
                uint256 n = manager.exposedCount(customers[c], address(routerOf[r]));
                assertEq(n, distinct, "the list holds exactly the tokens with a non-zero count");
                assertLe(n, 8, "PC-18");
                for (uint256 j = 0; j < n; ++j) {
                    address t = manager.exposedAt(customers[c], address(routerOf[r]), j);
                    assertEq(manager.exposedPos(customers[c], address(routerOf[r]), t), j + 1);
                    assertGt(manager.live(customers[c], address(routerOf[r]), t), 0);
                }
            }
        }
    }

    function invariant_OneActiveMandatePerLineage_AndExec3() public view {
        for (uint256 g = 0; g < ghost.length; ++g) {
            bytes32 lid_ = _view(ghost[g]).lineageId;
            uint256 active;
            bytes32 which;
            uint256 chargeableRouters;
            for (uint256 h2 = 0; h2 < ghost.length; ++h2) {
                IMandateManager.MandateView memory v = _view(ghost[h2]);
                if (v.lineageId != lid_) continue;
                if (v.status == 0) {
                    active++;
                    which = ghost[h2];
                }
                for (uint256 r = 0; r < 2; ++r) {
                    if (manager.isConsumable(ghost[h2], address(routerOf[r]))) chargeableRouters++;
                }
            }
            assertLe(active, 1, "I-MIG-1: one active mandate per lineage");
            assertLe(chargeableRouters, 1, "Exec3: at most one (mandate, router) pair can charge the lineage");
            (, , , bool terminated, , bytes32 pointer) = manager.lineages(lid_);
            if (active == 1) {
                assertEq(pointer, which, "the lineage points at its active mandate");
                assertFalse(terminated);
            } else {
                assertTrue(terminated || _view(pointer).status != 0, "no active mandate: the lineage is terminated or its pointer is dead");
            }
        }
    }

    function invariant_SupersededMandatesAreRevokedAsSuperseded_AndStatusIsMonotone() public {
        for (uint256 g = 0; g < ghost.length; ++g) {
            IMandateManager.MandateView memory v = _view(ghost[g]);
            if (liveStatus[ghost[g]] == 1) assertEq(v.status, 1, "a revoked mandate is never active again");
            liveStatus[ghost[g]] = v.status;
            if (v.generation > 0) {
                IMandateManager.MandateView memory p = _view(v.predecessorId);
                assertEq(p.status, 1);
                assertTrue(p.reason == 2 || p.reason == 3, "the predecessor of a successor is superseded");
                assertEq(p.lineageId, v.lineageId);
                assertEq(v.generation, p.generation + 1);
            }
        }
    }

    function invariant_UsageEqualsWhatWasCharged_AndRespectsTheCaps() public view {
        for (uint256 g = 0; g < ghost.length; ++g) {
            bytes32 lid_ = _view(ghost[g]).lineageId;
            for (uint256 i = 0; i < NTOK; ++i) {
                address t = address(pool[i]);
                uint256 total = ledger.tokenUsage(lid_, t).total;
                assertEq(total, charged[lid_][t], "the ledger's total is the sum of the charges that succeeded");
                assertLe(total, 5000e6, "I-CAP-TOKEN: the total cap");
            }
        }
    }

    function invariant_TokensAreConserved_AndTheRoutersHoldNone() public view {
        for (uint256 i = 0; i < NTOK; ++i) {
            MockERC20 t = pool[i];
            uint256 sum = t.balanceOf(customers[0]) + t.balanceOf(customers[1]) + t.balanceOf(merchantWallet) + t.balanceOf(feeWallet);
            assertEq(sum, 2_000_000e6, "no token was created or lost");
            assertEq(t.balanceOf(address(routerA)), 0);
            assertEq(t.balanceOf(address(routerB)), 0);
            assertEq(t.balanceOf(address(manager)), 0);
        }
    }
}
