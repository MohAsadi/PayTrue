// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {FastPayTypes as T} from "./generated/FastPayTypes.sol";
import {IMandateManager} from "./interfaces/IMandateManager.sol";
import {IRouterRegistry} from "./interfaces/IRouterRegistry.sol";
import "./Errors.sol";

/// A bounded, resumable migration (ADR-022, replaces the single large `activateSuccessors` batch of document 12 section 5.3.1).
///
/// The customer migrates the lineages of one router with a PLAN: one transaction that commits to the ordered list of their
/// `SuccessorAuthorization`s as a hash chain (one 32-byte word of storage, whatever the length of the list). Anyone may then execute the plan
/// in STEPS of at most MAX_BATCH entries each, in any number of transactions, and a step that fails changes nothing. The plan is a state
/// machine (OPEN -> DONE | ABORTED | EXPIRED) with a cursor, so a migration that does not fit one block, or that one stuck entry would block,
/// is resumed, skipped over (by the customer) or abandoned (by the customer, or by the deadline) rather than lost.
///
///   head(i) = keccak256(abi.encode(PLAN_ENTRY_TAG, hashStruct(auth(i)), head(i + 1)))      head(count) = 0
///
/// What a plan can and cannot do. The customer authorizes the plan by sending `open` (msg.sender is the customer) and each entry binds its
/// lineage, predecessor, new terms, new router, pin and snapshot (predicate A3), so a stepper can choose WHEN but never WHAT. Each entry runs
/// through the manager's `activateSuccessor` with every predicate of document 12 section 5.3 (A2, A3, L1, R1 to R3, X1, K1, G1, X2, C1 or C2, O1N or
/// O1E): the queue relaxes none of them and writes no mandate state itself. Steps are in the order of the chain, so the customer chooses
/// the order (for example the lineages that share no token with their siblings first). A plan opened by relayed signature needs a typed plan
/// message that types.json does not have; a relayer holding per-entry signatures uses MandateGateway.activateSuccessorBySig instead.
contract MigrationQueue {
    bytes32 internal constant PLAN_TAG = keccak256("fastpay.plan.v1");
    bytes32 internal constant PLAN_ENTRY_TAG = keccak256("fastpay.plan.entry.v1");

    uint8 public constant ST_NONE = 0;
    uint8 public constant ST_OPEN = 1;
    uint8 public constant ST_DONE = 2;
    uint8 public constant ST_ABORTED = 3;
    uint8 public constant ST_EXPIRED = 4;

    /// A plan is a few words however long it is; this only keeps a planner's mistake from opening an absurd plan.
    uint32 public constant MAX_PLAN_ENTRIES = 1024;

    struct Plan {
        address customer;
        uint8 kind;
        uint8 status;
        address newRouter;
        uint32 total;
        uint32 done;
        uint64 expiresAt;
        bytes32 head;
    }

    struct Entry {
        IMandateManager.SuccessorRequest req;
        bytes32 next; // head(i + 1)
    }

    IMandateManager public immutable manager;
    IRouterRegistry public immutable registry;

    mapping(bytes32 => Plan) public plans;

    event PlanOpened(bytes32 indexed planId, address indexed customer, uint8 kind, address newRouter, uint32 total, uint64 expiresAt, bytes32 head);
    event PlanStepped(bytes32 indexed planId, uint32 done, uint32 total, bytes32 head);
    event PlanEntrySkipped(bytes32 indexed planId, bytes32 indexed predecessorId, uint32 done);
    event PlanClosed(bytes32 indexed planId, uint8 status);

    constructor(IMandateManager manager_, IRouterRegistry registry_) {
        manager = manager_;
        registry = registry_;
    }

    function planIdOf(address customer, uint256 planNonce) public view returns (bytes32) {
        return keccak256(abi.encode(PLAN_TAG, block.chainid, address(this), customer, planNonce));
    }

    /// The commitment of one link; the planner (and the tests) fold the list from the last entry to the first.
    function link(bytes32 authHash, bytes32 next) public pure returns (bytes32) {
        return keccak256(abi.encode(PLAN_ENTRY_TAG, authHash, next));
    }

    /// The customer opens a plan. `head` is head(0) of the chain over `total` entries; `kind` is NORMAL or EMERGENCY (a revision is a single
    /// activateSuccessor, never a migration).
    function open(uint256 planNonce, uint8 kind, address newRouter, uint32 total, bytes32 head, uint64 expiresAt)
        external
        returns (bytes32 planId)
    {
        if (kind > 1) revert WrongKind();
        if (total == 0 || total > MAX_PLAN_ENTRIES || head == bytes32(0)) revert PlanEntryMismatch();
        if (expiresAt <= block.timestamp) revert QueueClosed();
        if (!registry.isBindable(newRouter)) revert RouterNotBindable();
        planId = planIdOf(msg.sender, planNonce);
        Plan storage p = plans[planId];
        if (p.status != ST_NONE) revert PlanExists();
        p.customer = msg.sender;
        p.kind = kind;
        p.status = ST_OPEN;
        p.newRouter = newRouter;
        p.total = total;
        p.expiresAt = expiresAt;
        p.head = head;
        emit PlanOpened(planId, msg.sender, kind, newRouter, total, expiresAt, head);
    }

    function _open(bytes32 planId) internal view returns (Plan storage p) {
        p = plans[planId];
        if (p.status == ST_NONE) revert PlanUnknown();
        if (p.status != ST_OPEN || block.timestamp > p.expiresAt) revert QueueClosed();
    }

    /// The next entries of the plan, at most MAX_BATCH of them, executed in order. Permissionless. All of them succeed or none does.
    function step(bytes32 planId, Entry[] calldata entries) external {
        if (entries.length > T.MAX_BATCH) revert StepTooLarge();
        if (entries.length == 0) revert PlanEntryMismatch();
        Plan storage p = _open(planId);
        bytes32 head = p.head;
        // loop-bound: BATCH | entries.length <= MAX_BATCH | the first line reverts StepTooLarge
        for (uint256 i = 0; i < entries.length; ++i) {
            Entry calldata e = entries[i];
            head = _advance(p, head, e);
            manager.activateSuccessor(p.customer, e.req);
        }
        _finish(planId, p, head, uint32(entries.length));
    }

    /// The customer gives up one entry that cannot execute any more (its predecessor was revoked, its router changed) and the plan goes on.
    function skip(bytes32 planId, Entry calldata e) external {
        Plan storage p = _open(planId);
        if (msg.sender != p.customer) revert NotCustomer();
        bytes32 head = _advance(p, p.head, e);
        emit PlanEntrySkipped(planId, e.req.auth.predecessorId, p.done + 1);
        _finish(planId, p, head, 1);
    }

    /// The entry extends the chain from `head`, and is the one the plan was opened for (customer, kind, router).
    function _advance(Plan storage p, bytes32 head, Entry calldata e) internal view returns (bytes32) {
        T.SuccessorAuthorization calldata a = e.req.auth;
        if (a.customer != p.customer || a.kind != p.kind || a.newRouter != p.newRouter) revert PlanEntryMismatch();
        if (link(T.hashStruct(a), e.next) != head) revert PlanEntryMismatch();
        return e.next;
    }

    function _finish(bytes32 planId, Plan storage p, bytes32 head, uint32 n) internal {
        uint32 done = p.done + n;
        if (done > p.total) revert PlanEntryMismatch();
        p.done = done;
        p.head = head;
        if (done == p.total) {
            if (head != bytes32(0)) revert PlanEntryMismatch(); // the chain ends exactly where the plan says
            p.status = ST_DONE;
            emit PlanClosed(planId, ST_DONE);
        }
        emit PlanStepped(planId, done, p.total, head);
    }

    function abort(bytes32 planId) external {
        Plan storage p = plans[planId];
        if (p.status == ST_NONE) revert PlanUnknown();
        if (msg.sender != p.customer) revert NotCustomer();
        if (p.status != ST_OPEN) revert QueueClosed();
        p.status = ST_ABORTED;
        emit PlanClosed(planId, ST_ABORTED);
    }

    /// State hygiene: anyone can record that a plan ran out of time (a step already refuses it).
    function expire(bytes32 planId) external {
        Plan storage p = plans[planId];
        if (p.status == ST_NONE) revert PlanUnknown();
        if (p.status != ST_OPEN) revert QueueClosed();
        if (block.timestamp <= p.expiresAt) revert QueueNotExpired();
        p.status = ST_EXPIRED;
        emit PlanClosed(planId, ST_EXPIRED);
    }
}
