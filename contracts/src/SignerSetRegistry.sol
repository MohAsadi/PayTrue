// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.24;

import {ISignerSetRegistry} from "./interfaces/ISignerSetRegistry.sol";
import {FastPayTypes as T} from "./generated/FastPayTypes.sol";
import "./Errors.sol";

/// Versioned quote-signer sets (document 11 section 4.7): planned rotation with a bounded grace for quotes already issued, emergency removal
/// with NO grace and permanent tombstones, a stop-only guardian. Port of the reference model SignerSetModel.
///
/// Verification is O(1): `verifySigner` reads a fixed number of storage slots (the tombstone of the key, the set, the membership of the key in
/// the set) whatever the size of any set. The only loops are over the members of ONE set when it is proposed and when it is activated, and
/// they are bounded by MAX_SIGNERS_PER_SET (configuration record PC-19, proposed): a larger set is refused before any loop runs, so the
/// activation of a replacement set (the emergency rotation) cannot be made to run out of gas.
contract SignerSetRegistry is ISignerSetRegistry {
    uint256 public constant MAX_SIGNERS_PER_SET = T.MAX_SIGNERS_PER_SET; // PC-19, proposal 16 (eip712/types.json)

    struct SignerSet {
        uint64 activeFrom;
        uint64 retiredAt;
        bool stopped;
        bool active;
        bool exists;
    }

    address public immutable governance;
    address public immutable guardian;
    /// QUOTE_SET_GRACE (PC-08): at least MAX_QUOTE_TTL, at most twice that (constraints X-01 and X-02 of document 18).
    uint256 public immutable quoteSetGrace;

    mapping(uint32 => SignerSet) public sets;
    mapping(uint32 => address[]) internal memberList;
    mapping(uint32 => mapping(address => bool)) public isMember;
    mapping(address => uint64) public removedAt;
    uint32 public current;

    event SignerSetProposed(uint32 indexed version, address[] members);
    event SignerSetActivated(uint32 indexed version, uint64 activeFrom, uint32 retired);
    event QuoteSignerRemovedEvent(address indexed key, uint64 removedAt);
    event SignerSetStopped(uint32 indexed version);

    constructor(address governance_, address guardian_, uint256 maxQuoteTtl, uint256 grace) {
        if (grace < maxQuoteTtl || grace > 2 * maxQuoteTtl) revert InvalidBounds();
        governance = governance_;
        guardian = guardian_;
        quoteSetGrace = grace;
    }

    modifier onlyGovernance() {
        if (msg.sender != governance) revert NotGovernance();
        _;
    }

    function proposeSignerSet(uint32 version, address[] calldata members) external onlyGovernance {
        if (sets[version].exists) revert SignerSetVersionOrder();
        if (members.length > MAX_SIGNERS_PER_SET) revert TooManySigners(members.length, MAX_SIGNERS_PER_SET);
        // loop-bound: SIGNERS | members.length <= MAX_SIGNERS_PER_SET | the line above reverts TooManySigners before the loop
        for (uint256 i = 0; i < members.length; ++i) {
            if (removedAt[members[i]] != 0) revert QuoteSignerTombstoned(members[i]);
            memberList[version].push(members[i]);
            isMember[version][members[i]] = true;
        }
        sets[version].exists = true;
        emit SignerSetProposed(version, members);
    }

    function activateSignerSet(uint32 version) external onlyGovernance {
        SignerSet storage s = sets[version];
        if (!s.exists || s.active) revert SignerSetNotProposed();
        if (version != current + 1) revert SignerSetVersionOrder();
        address[] storage list = memberList[version];
        // loop-bound: SIGNERS | memberList[version].length <= MAX_SIGNERS_PER_SET | proposeSignerSet refuses a larger set
        for (uint256 i = 0; i < list.length; ++i) {
            if (removedAt[list[i]] != 0) revert QuoteSignerTombstoned(list[i]); // a key removed after the proposal cannot join
        }
        uint32 old = current;
        if (old != 0) sets[old].retiredAt = uint64(block.timestamp);
        s.activeFrom = uint64(block.timestamp);
        s.active = true;
        current = version;
        emit SignerSetActivated(version, s.activeFrom, old);
    }

    /// Emergency removal: idempotent, no grace, permanent. Guardian or governance (the guardian cannot add a key or a set).
    function removeQuoteSigner(address key) external {
        if (msg.sender != guardian && msg.sender != governance) revert NotAuthorized();
        if (removedAt[key] == 0) {
            removedAt[key] = uint64(block.timestamp);
            emit QuoteSignerRemovedEvent(key, uint64(block.timestamp));
        }
    }

    function stopSignerSet(uint32 version) external {
        if (msg.sender != guardian && msg.sender != governance) revert NotAuthorized();
        SignerSet storage s = sets[version];
        if (!s.exists || !s.active) revert SignerSetNotProposed();
        s.stopped = true;
        emit SignerSetStopped(version);
    }

    function memberCount(uint32 version) external view returns (uint256) {
        return memberList[version].length;
    }

    /// Q1 then Q13 for a quote signed by `key` under set `version`, issued at `issuedAt`, consumed now. O(1).
    function verifySigner(address key, uint32 version, uint64 issuedAt) external view {
        if (removedAt[key] != 0) revert QuoteSignerRemoved();
        SignerSet storage s = sets[version];
        if (!s.exists || !s.active || !isMember[version][key]) revert QuoteSignerUnauthorized();
        if (s.stopped) revert QuoteSignerSetStopped();
        if (s.activeFrom > issuedAt) revert QuoteSignerSetRetired();
        if (s.retiredAt != 0) {
            if (!(issuedAt < s.retiredAt && block.timestamp <= uint256(s.retiredAt) + quoteSetGrace)) revert QuoteSignerSetRetired();
        }
    }
}
