// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import "./Errors.sol";
import "./Mutants.sol";

/// Reference model of the quote signer sets (document 11 sections 4.2 Q1 and Q13, 4.7): versioned sets, planned rotation with a
/// bounded grace, emergency removal with none, permanent tombstones, a stop-only guardian. Mirrors protocol_model.SignerSetModel.
contract SignerSetModel {
    uint8 public constant ROLE_GOVERNANCE = 0;
    uint8 public constant ROLE_GUARDIAN = 1;

    uint256 public immutable grace; // QUOTE_SET_GRACE (PC-08)
    uint256 public constant MAX_SIGNERS_PER_SET = 16; // bounds both member loops below; a new constant with no configuration record yet (PC-19, proposal)

    struct SignerSet {
        uint256 activeFrom;
        uint256 retiredAt;
        bool stopped;
        bool active;
        bool exists;
    }

    mapping(uint256 => SignerSet) public sets;
    mapping(uint256 => address[]) internal memberList;
    mapping(uint256 => mapping(address => bool)) public isMember;
    mapping(address => uint256) public removedAt;
    uint256 public current;

    constructor(uint256 grace_) {
        grace = grace_;
    }

    function proposeSignerSet(uint8 role, uint256 version, address[] calldata members, uint256 mutant) external {
        if (role != ROLE_GOVERNANCE && !(mutant == M_SS_GUARDIAN_PROPOSE && role == ROLE_GUARDIAN)) revert NotGovernance();
        if (sets[version].exists) revert SignerSetVersionOrder();
        if (members.length > MAX_SIGNERS_PER_SET) revert TooManySigners(members.length, MAX_SIGNERS_PER_SET);
        if (mutant != M_SS_PROPOSE_TOMB_SKIP) {
            // loop-bound: SIGNERS | members.length <= MAX_SIGNERS_PER_SET | the entry point reverts TooManySigners above the bound before the loop
            for (uint256 i = 0; i < members.length; ++i) {
                if (removedAt[members[i]] != 0) revert QuoteSignerTombstoned(members[i]);
            }
        }
        sets[version].exists = true;
        // loop-bound: SIGNERS | members.length <= MAX_SIGNERS_PER_SET | the entry point reverts TooManySigners above the bound before the loop
        for (uint256 j = 0; j < members.length; ++j) {
            memberList[version].push(members[j]);
            isMember[version][members[j]] = true;
        }
    }

    function activateSignerSet(uint8 role, uint256 version, uint256 mutant) external {
        if (role != ROLE_GOVERNANCE && !(mutant == M_SS_GUARDIAN_ACTIVATE && role == ROLE_GUARDIAN)) revert NotGovernance();
        SignerSet storage s = sets[version];
        if (!s.exists || s.active) revert SignerSetNotProposed();
        if (version != current + 1) revert SignerSetVersionOrder();
        if (mutant != M_SS_ACTIVATE_TOMB_SKIP) {
            address[] storage list = memberList[version];
            // loop-bound: SIGNERS | memberList[version].length <= MAX_SIGNERS_PER_SET | a set has at most the proposed members, and proposeSignerSet refuses more than the bound
            for (uint256 i = 0; i < list.length; ++i) {
                if (removedAt[list[i]] != 0) revert QuoteSignerTombstoned(list[i]);
            }
        }
        if (current != 0 && mutant != M_SS_ROTATE_NO_RETIRE) sets[current].retiredAt = block.timestamp;
        s.activeFrom = block.timestamp;
        s.active = true;
        current = version;
    }

    /// removeQuoteSigner: idempotent; the key is tombstoned forever.
    function removeQuoteSigner(uint8 role, address key) external {
        if (role != ROLE_GOVERNANCE && role != ROLE_GUARDIAN) revert NotAuthorized();
        if (removedAt[key] == 0) removedAt[key] = block.timestamp;
    }

    function stopSignerSet(uint8 role, uint256 version) external {
        if (role != ROLE_GOVERNANCE && role != ROLE_GUARDIAN) revert NotAuthorized();
        SignerSet storage s = sets[version];
        if (!s.exists || !s.active) revert SignerSetNotProposed();
        s.stopped = true;
    }

    /// Q1 then Q13 for a quote signed by `key` under set `version`, issued at `issuedAt`, consumed now.
    function verify(address key, uint256 version, uint256 issuedAt, uint256 mutant) external view {
        if (mutant != M_Q1_TOMB_SKIP && removedAt[key] != 0) revert QuoteSignerRemoved();
        SignerSet storage s = sets[version];
        if (!s.exists || !s.active || (mutant != M_Q1_MEMBER_SKIP && !isMember[version][key])) revert QuoteSignerUnauthorized();
        if (mutant != M_Q13_STOP_SKIP && s.stopped) revert QuoteSignerSetStopped();
        if (mutant != M_Q13_ACTIVE_SKIP && s.activeFrom > issuedAt) revert QuoteSignerSetRetired();
        if (s.retiredAt != 0) {
            bool early = mutant == M_Q13_ISSUED_LE ? issuedAt <= s.retiredAt : issuedAt < s.retiredAt;
            uint256 limit = s.retiredAt + grace;
            bool inGrace = mutant == M_Q13_GRACE_LT ? block.timestamp < limit : block.timestamp <= limit;
            if (mutant == M_Q13_GRACE_SKIP) inGrace = true;
            if (!(early && inGrace)) revert QuoteSignerSetRetired();
        }
    }

    function accepts(address key, uint256 version, uint256 issuedAt, uint256 mutant) external view returns (bool) {
        try this.verify(key, version, issuedAt, mutant) {
            return true;
        } catch {
            return false;
        }
    }
}
