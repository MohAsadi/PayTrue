// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Builders} from "./helpers/Builders.sol";
import {FastPayTypes as T} from "../src/generated/FastPayTypes.sol";
import {IMandateManager} from "../src/interfaces/IMandateManager.sol";
import {MigrationQueue} from "../src/MigrationQueue.sol";
import {PaymentRouter} from "../src/PaymentRouter.sol";
import "../src/Errors.sol";

/// The bounded, resumable migration state machine (ADR-022): a plan commits to an ordered list of successor authorizations as a hash chain,
/// anyone executes it in steps of at most MAX_BATCH, and a step that fails changes nothing.
contract QueueTest is Builders {
    uint256 constant N = 5;
    bytes32[] lids;
    bytes32[] mids;

    function setUp() public override {
        super.setUp();
        _fund(customer, usdc, 10_000e6);
        _grant(customer, usdc, address(routerA), 5_000e6);
        for (uint256 i = 0; i < N; ++i) {
            (bytes32 l, bytes32 m) = _activate(customer, i + 1, address(routerA), _terms(address(usdc)), _pin());
            lids.push(l);
            mids.push(m);
        }
        _grant(customer, usdc, address(routerB), 500e6); // S1
        _lock(address(usdc), address(routerA)); // S2: no sibling will be left, and the siblings along the way only need a bounded allowance
    }

    // ------------------------------------------------------------------------------------------------------------ building plans
    function _entries(uint8 kind) internal returns (MigrationQueue.Entry[] memory es, bytes32 head) {
        return _entriesTo(kind, address(routerB));
    }

    function _entriesTo(uint8 kind, address router) internal returns (MigrationQueue.Entry[] memory es, bytes32 head) {
        es = new MigrationQueue.Entry[](N);
        bytes32[] memory ah = new bytes32[](N);
        for (uint256 i = 0; i < N; ++i) {
            T.MandateTerms memory pt = _terms(address(usdc));
            T.AccountPin memory p = _pin();
            T.SuccessorAuthorization memory a = _auth(Sp(lids[i], mids[i], bytes32(0), 0, kind, router), pt, pt, p);
            es[i].req = _req(pt, p, _terms(address(usdc)), _pin(), a);
            ah[i] = T.hashStruct(a);
        }
        // fold from the end: head(i) = link(auth(i), head(i + 1)), head(N) = 0
        bytes32 nextHead = bytes32(0);
        for (uint256 j = N; j > 0; --j) {
            es[j - 1].next = nextHead;
            nextHead = queue.link(ah[j - 1], nextHead);
        }
        head = nextHead;
    }

    function _open(uint256 planNonce, uint8 kind, uint32 total, bytes32 head, uint64 expiresAt) internal returns (bytes32 planId) {
        vm.prank(customer);
        planId = queue.open(planNonce, kind, address(routerB), total, head, expiresAt);
    }

    function _slice(MigrationQueue.Entry[] memory es, uint256 from, uint256 to) internal pure returns (MigrationQueue.Entry[] memory r) {
        r = new MigrationQueue.Entry[](to - from);
        for (uint256 i = from; i < to; ++i) {
            r[i - from] = es[i];
        }
    }

    function _status(bytes32 planId) internal view returns (uint8 status, uint32 done, bytes32 head) {
        (, , status, , , done, , head) = queue.plans(planId);
    }

    // ------------------------------------------------------------------------------------------------------------ the happy paths
    function test_Plan_OneStepMigratesEveryLineage() public {
        (MigrationQueue.Entry[] memory es, bytes32 head) = _entries(NORMAL);
        bytes32 id = _open(1, NORMAL, uint32(N), head, uint64(START + 1 days));
        assertEq(id, queue.planIdOf(customer, 1));
        vm.prank(stranger); // anyone may crank a plan
        queue.step(id, es);
        (uint8 st, uint32 done, bytes32 h2) = _status(id);
        assertEq(st, queue.ST_DONE());
        assertEq(done, N);
        assertEq(h2, bytes32(0));
        for (uint256 i = 0; i < N; ++i) {
            assertEq(_view(mids[i]).status, 1);
            assertEq(_view(manager.mandateIdOf(lids[i], 1)).router, address(routerB));
        }
        assertEq(manager.live(customer, address(routerB), address(usdc)), N);
        assertEq(manager.exposedCount(customer, address(routerA)), 0);
    }

    function test_Plan_IsResumable_InAnyChunking_ByAnyCaller() public {
        (MigrationQueue.Entry[] memory es, bytes32 head) = _entries(NORMAL);
        bytes32 id = _open(1, NORMAL, uint32(N), head, uint64(START + 1 days));
        queue.step(id, _slice(es, 0, 2));
        (uint8 st, uint32 done,) = _status(id);
        assertEq(st, queue.ST_OPEN());
        assertEq(done, 2);
        assertEq(_view(mids[1]).status, 1);
        assertEq(_view(mids[2]).status, 0, "the rest is untouched");
        vm.warp(START + 3 hours);
        vm.prank(stranger);
        queue.step(id, _slice(es, 2, 3));
        vm.prank(executor);
        queue.step(id, _slice(es, 3, 5));
        (st, done,) = _status(id);
        assertEq(st, queue.ST_DONE());
        assertEq(done, N);
    }

    function test_Plan_Emergency() public {
        (MigrationQueue.Entry[] memory es, bytes32 head) = _entries(EMERGENCY);
        bytes32 id = _open(2, EMERGENCY, uint32(N), head, uint64(START + 1 days));
        queue.step(id, es);
        (uint8 st,,) = _status(id);
        assertEq(st, queue.ST_DONE());
        assertEq(_view(manager.mandateIdOf(lids[0], 1)).reason, 0);
        assertEq(_view(mids[0]).reason, 2);
    }

    // ------------------------------------------------------------------------------------------------------------ the chain is the authority
    function test_Chain_OutOfOrderEntriesAreRefused() public {
        (MigrationQueue.Entry[] memory es, bytes32 head) = _entries(NORMAL);
        bytes32 id = _open(1, NORMAL, uint32(N), head, uint64(START + 1 days));
        MigrationQueue.Entry[] memory two = new MigrationQueue.Entry[](2);
        two[0] = es[1];
        two[1] = es[0];
        vm.expectRevert(PlanEntryMismatch.selector);
        queue.step(id, two);
        // skipping ahead is refused too
        vm.expectRevert(PlanEntryMismatch.selector);
        queue.step(id, _slice(es, 1, 3));
        (, uint32 done,) = _status(id);
        assertEq(done, 0);
    }

    function test_Chain_ATamperedEntryIsRefused() public {
        (MigrationQueue.Entry[] memory es, bytes32 head) = _entries(NORMAL);
        bytes32 id = _open(1, NORMAL, uint32(N), head, uint64(START + 1 days));
        es[0].req.auth.deadline += 1; // any change of the authorization changes its hash
        vm.expectRevert(PlanEntryMismatch.selector);
        queue.step(id, _slice(es, 0, 1));
        (, es[0].next) = (0, es[0].next);
        es[0].req.auth.deadline -= 1;
        es[0].next = keccak256("a forged continuation");
        vm.expectRevert(PlanEntryMismatch.selector);
        queue.step(id, _slice(es, 0, 1));
    }

    function test_Chain_TheAuthorizationInTheEntryDecidesWhatTheManagerSees() public {
        // the request is not part of the chain, only its authorization is: the new terms are bound by auth.newTermsHash (predicate A3),
        // so a stepper who swaps the terms is refused by the manager, not by the queue
        (MigrationQueue.Entry[] memory es, bytes32 head) = _entries(NORMAL);
        bytes32 id = _open(1, NORMAL, uint32(N), head, uint64(START + 1 days));
        es[0].req.newTerms.tokens[0].perPaymentMax -= 1;
        vm.expectRevert(AuthorizationMismatch.selector);
        queue.step(id, _slice(es, 0, 1));
    }

    function test_Chain_AnEntryOfAnotherKindOrRouterIsRefused() public {
        (MigrationQueue.Entry[] memory es, bytes32 head) = _entries(EMERGENCY);
        bytes32 id = _open(1, NORMAL, uint32(N), head, uint64(START + 1 days)); // the plan says NORMAL; the entries are EMERGENCY
        vm.expectRevert(PlanEntryMismatch.selector);
        queue.step(id, _slice(es, 0, 1));
    }

    function test_Chain_AnEntryForAnotherRouterIsRefused() public {
        (MigrationQueue.Entry[] memory es, bytes32 head) = _entriesTo(NORMAL, address(routerA)); // the entries name router A
        bytes32 id = _open(1, NORMAL, uint32(N), head, uint64(START + 1 days)); // the plan says router B
        vm.expectRevert(PlanEntryMismatch.selector);
        queue.step(id, _slice(es, 0, 1));
    }

    function test_Step_MoreEntriesThanThePlanHoldsIsRefused() public {
        (MigrationQueue.Entry[] memory es, bytes32 head) = _entries(NORMAL);
        bytes32 id = _open(1, NORMAL, uint32(N - 1), head, uint64(START + 1 days)); // the chain has N entries, the plan says N - 1
        vm.expectRevert(PlanEntryMismatch.selector);
        queue.step(id, es);
        (, uint32 done,) = _status(id);
        assertEq(done, 0);
    }

    function test_Plan_CannotMigrateSomeoneElsesLineage() public {
        (MigrationQueue.Entry[] memory es, bytes32 head) = _entries(NORMAL);
        // a stranger opens a plan over the customer's authorizations
        vm.prank(stranger);
        bytes32 id = queue.open(1, NORMAL, address(routerB), uint32(N), head, uint64(START + 1 days));
        vm.expectRevert(PlanEntryMismatch.selector); // the entries name the customer, the plan's customer is the stranger
        queue.step(id, _slice(es, 0, 1));
        // the stranger builds entries that name themselves but point at the customer's mandate
        T.MandateTerms memory pt = _terms(address(usdc));
        T.AccountPin memory p = _pin();
        T.SuccessorAuthorization memory a = _auth(Sp(lids[0], mids[0], bytes32(0), 0, NORMAL, address(routerB)), pt, pt, p);
        a.customer = stranger;
        MigrationQueue.Entry[] memory one = new MigrationQueue.Entry[](1);
        one[0].req = _req(pt, p, pt, p, a);
        one[0].next = bytes32(0);
        bytes32 oneHead = queue.link(T.hashStruct(a), bytes32(0));
        vm.prank(stranger);
        bytes32 id2 = queue.open(2, NORMAL, address(routerB), 1, oneHead, uint64(START + 1 days));
        vm.expectRevert(NotCustomer.selector); // the manager: the predecessor is not the stranger's
        queue.step(id2, one);
        assertEq(_view(mids[0]).status, 0);
    }

    // ------------------------------------------------------------------------------------------------------------ a failing step changes nothing
    function test_Step_AFailingEntryRevertsTheWholeStep_AndTheCustomerCanSkipIt() public {
        (MigrationQueue.Entry[] memory es, bytes32 head) = _entries(NORMAL);
        bytes32 id = _open(1, NORMAL, uint32(N), head, uint64(START + 1 days));
        vm.prank(customer);
        manager.revoke(customer, mids[2]); // the third lineage is gone: its entry can never execute
        vm.expectRevert(WrongPredecessor.selector);
        queue.step(id, _slice(es, 0, 4));
        (uint8 st, uint32 done, bytes32 headAfter) = _status(id);
        assertEq(st, queue.ST_OPEN());
        assertEq(done, 0, "nothing of the failed step was applied");
        assertEq(headAfter, head);
        assertEq(_view(mids[0]).status, 0);
        // the entries before the stuck one go through; the stuck one is skipped by the customer only
        queue.step(id, _slice(es, 0, 2));
        vm.prank(stranger);
        vm.expectRevert(NotCustomer.selector);
        queue.skip(id, es[2]);
        vm.prank(customer);
        queue.skip(id, es[2]);
        queue.step(id, _slice(es, 3, 5));
        (st, done,) = _status(id);
        assertEq(st, queue.ST_DONE());
        assertEq(done, N);
        assertEq(_view(manager.mandateIdOf(lids[2], 1)).lineageId, bytes32(0), "the skipped lineage has no successor");
    }

    function test_Step_AnExpiredAuthorizationInTheMiddleRevertsTheStep() public {
        (MigrationQueue.Entry[] memory es, bytes32 head) = _entries(NORMAL);
        bytes32 id = _open(1, NORMAL, uint32(N), head, uint64(START + 3 days));
        vm.warp(deadline + 1); // the authorizations expired (A2) though the plan did not
        vm.expectRevert(AuthorizationExpired.selector);
        queue.step(id, _slice(es, 0, 1));
    }

    function test_Step_Bounds() public {
        (MigrationQueue.Entry[] memory es, bytes32 head) = _entries(NORMAL);
        bytes32 id = _open(1, NORMAL, uint32(N), head, uint64(START + 1 days));
        vm.expectRevert(StepTooLarge.selector);
        queue.step(id, new MigrationQueue.Entry[](T.MAX_BATCH + 1));
        vm.expectRevert(PlanEntryMismatch.selector);
        queue.step(id, new MigrationQueue.Entry[](0));
        queue.step(id, es);
        vm.expectRevert(QueueClosed.selector);
        queue.step(id, _slice(es, 0, 1)); // a finished plan runs no more
    }

    // ------------------------------------------------------------------------------------------------------------ abort and expiry
    function test_Abort_OnlyTheCustomer_AndItStopsTheSteps() public {
        (MigrationQueue.Entry[] memory es, bytes32 head) = _entries(NORMAL);
        bytes32 id = _open(1, NORMAL, uint32(N), head, uint64(START + 1 days));
        queue.step(id, _slice(es, 0, 1));
        vm.prank(stranger);
        vm.expectRevert(NotCustomer.selector);
        queue.abort(id);
        vm.prank(customer);
        queue.abort(id);
        (uint8 st, uint32 done,) = _status(id);
        assertEq(st, queue.ST_ABORTED());
        assertEq(done, 1, "what was done stays done");
        vm.expectRevert(QueueClosed.selector);
        queue.step(id, _slice(es, 1, 2));
        vm.prank(customer);
        vm.expectRevert(QueueClosed.selector);
        queue.abort(id);
        // the customer can still migrate the rest one by one, with the same authorizations
        vm.prank(customer);
        manager.activateSuccessor(customer, es[1].req);
        assertEq(_view(mids[1]).status, 1);
    }

    function test_Expiry_StepsAreRefusedAfterIt_AndAnyoneCanRecordIt() public {
        (MigrationQueue.Entry[] memory es, bytes32 head) = _entries(NORMAL);
        bytes32 id = _open(1, NORMAL, uint32(N), head, uint64(START + 2 hours));
        vm.expectRevert(QueueNotExpired.selector);
        queue.expire(id);
        vm.warp(START + 2 hours); // the boundary: still open
        queue.step(id, _slice(es, 0, 1));
        vm.warp(START + 2 hours + 1);
        vm.expectRevert(QueueClosed.selector);
        queue.step(id, _slice(es, 1, 2));
        vm.prank(stranger);
        queue.expire(id);
        (uint8 st,,) = _status(id);
        assertEq(st, queue.ST_EXPIRED());
        vm.expectRevert(QueueClosed.selector);
        queue.expire(id);
    }

    // ------------------------------------------------------------------------------------------------------------ open
    function test_Open_Validations() public {
        (, bytes32 head) = _entries(NORMAL);
        uint32 tooMany = uint32(queue.MAX_PLAN_ENTRIES() + 1);
        vm.startPrank(customer);
        vm.expectRevert(WrongKind.selector);
        queue.open(1, REVISION, address(routerB), uint32(N), head, uint64(START + 1 days));
        vm.expectRevert(PlanEntryMismatch.selector);
        queue.open(1, NORMAL, address(routerB), 0, head, uint64(START + 1 days));
        vm.expectRevert(PlanEntryMismatch.selector);
        queue.open(1, NORMAL, address(routerB), tooMany, head, uint64(START + 1 days));
        vm.expectRevert(PlanEntryMismatch.selector);
        queue.open(1, NORMAL, address(routerB), uint32(N), bytes32(0), uint64(START + 1 days));
        vm.expectRevert(QueueClosed.selector);
        queue.open(1, NORMAL, address(routerB), uint32(N), head, uint64(START));
        PaymentRouter unregistered = _newRouter();
        vm.expectRevert(RouterNotBindable.selector);
        queue.open(1, NORMAL, address(unregistered), uint32(N), head, uint64(START + 1 days));
        queue.open(1, NORMAL, address(routerB), uint32(N), head, uint64(START + 1 days));
        vm.expectRevert(PlanExists.selector);
        queue.open(1, NORMAL, address(routerB), uint32(N), head, uint64(START + 1 days));
        vm.stopPrank();
        vm.expectRevert(PlanUnknown.selector);
        queue.expire(keccak256("no plan"));
    }

    function test_Open_AFinalHeadThatIsNotZeroNeverCompletes() public {
        (MigrationQueue.Entry[] memory es, bytes32 head) = _entries(NORMAL);
        // a plan that claims 4 entries but whose chain has 5: after the fourth the head is not zero
        bytes32 id = _open(1, NORMAL, uint32(N - 1), head, uint64(START + 1 days));
        vm.expectRevert(PlanEntryMismatch.selector);
        queue.step(id, _slice(es, 0, 4));
    }

    // ------------------------------------------------------------------------------------------------------------ the queue's authority is narrow
    function test_TheQueueMayOnlyActivateSuccessors() public {
        vm.startPrank(address(queue));
        vm.expectRevert(NotCustomer.selector);
        manager.revoke(customer, mids[0]);
        vm.expectRevert(NotCustomer.selector);
        manager.pause(customer, mids[0]);
        vm.expectRevert(NotCustomer.selector);
        manager.updateAccountPin(customer, mids[0], _pin());
        vm.expectRevert(NotCustomer.selector);
        manager.activate(customer, 99, address(routerA), _terms(address(usdc)), _pin());
        vm.expectRevert(NotGateway.selector);
        manager.spendNonce(customer, 1);
        vm.stopPrank();
    }

    function test_TheGatewayMayNotActivateASuccessorForAnotherCustomersMandate() public {
        (MigrationQueue.Entry[] memory es,) = _entries(NORMAL);
        vm.prank(address(gateway));
        vm.expectRevert(NotCustomer.selector);
        manager.activateSuccessor(stranger, es[0].req);
    }
}
