// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.24;

import {Base, IP2} from "./Base.sol";
import {ContainHarness} from "./ContainHarness.sol";
import {FastPayTypes as T} from "../../src/generated/FastPayTypes.sol";
import {IMandateManager} from "../../src/interfaces/IMandateManager.sol";

/// Builders of successor authorizations and requests, shared by the successor and the queue tests.
abstract contract Builders is Base {
    uint8 constant NORMAL = 0;
    uint8 constant EMERGENCY = 1;
    uint8 constant REVISION = 2;

    ContainHarness internal h;
    uint64 internal deadline;
    uint256 internal nonce;

    function setUp() public virtual override {
        super.setUp();
        h = new ContainHarness();
        deadline = uint64(START + 1 days);
        nonce = 100;
    }

    function _lock(address tok, address spender) internal {
        IP2.TokenSpenderPair[] memory pairs = new IP2.TokenSpenderPair[](1);
        pairs[0] = IP2.TokenSpenderPair(tok, spender);
        vm.prank(customer);
        p2.lockdown(pairs);
    }

    /// The identifying part of an authorization (lineage, predecessor, its predecessor, generation, kind, new router).
    struct Sp {
        bytes32 l;
        bytes32 pid;
        bytes32 ppred;
        uint32 gen;
        uint8 kind;
        address newRouter;
    }

    function _auth(Sp memory s, T.MandateTerms memory pt, T.MandateTerms memory nt, T.AccountPin memory np)
        internal
        returns (T.SuccessorAuthorization memory a)
    {
        address who = customer;
        try manager.partiesOf(s.pid) returns (bytes32, address c) {
            who = c; // the mandate's own customer (a test with several customers needs it)
        } catch {}
        a.customer = who;
        a.lineageId = s.l;
        a.predecessorId = s.pid;
        a.kind = s.kind;
        a.newTermsHash = T.hashStruct(nt);
        a.newRouter = s.newRouter;
        a.newRouterCodeHash = s.newRouter.codehash;
        a.newRouterVersion = routers.versionOf(s.newRouter);
        a.termsSnapshotHash = T.snapshotHash(s.l, s.ppred, s.gen, who, pt);
        a.widenedMask = s.kind == REVISION ? uint32(h.widened(nt, pt)) : 0;
        a.accountPin = np;
        a.deadline = deadline;
        a.nonce = ++nonce;
    }

    function _req(T.MandateTerms memory pt, T.AccountPin memory pp, T.MandateTerms memory nt, T.AccountPin memory np, T.SuccessorAuthorization memory a)
        internal
        pure
        returns (IMandateManager.SuccessorRequest memory r)
    {
        r.predTerms = pt;
        r.predPin = pp;
        r.newTerms = nt;
        r.newPin = np;
        r.auth = a;
    }
}
