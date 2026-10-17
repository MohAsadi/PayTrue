// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import {Vm} from "forge-std/Vm.sol";
import "../src/Errors.sol";
import {SignerSetModel} from "../src/SignerSetModel.sol";

/// The properties SR-1 ... SR-5 and SR-7 of document 11 section 4.7.1, checked on a grid of (key, set version, issuedAt) against the
/// current time. A violation is reported as a string, so that the fuzz tests and the invariant handler share one checker.
library SignerChecks {
    uint256 internal constant T0 = 1_800_000_000;
    /// The cheatcode address (`block.timestamp` may be moved across `vm.warp` by the optimizer, `vm.getBlockTimestamp()` cannot).
    Vm internal constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));

    function sampleTimes(uint256 nowTs) internal pure returns (uint256[8] memory q) {
        q = [uint256(0), T0, T0 + 1, T0 + 250, T0 + 999, T0 + 1000, T0 + 1001, nowTs];
    }

    /// The acceptance bitmap over (key 1..3, version 0..4, sample 0..7): bit k*40 + v*8 + s is set when verify accepts.
    function bitmap(SignerSetModel ss) internal view returns (uint256 bits) {
        uint256[8] memory q = sampleTimes(vm.getBlockTimestamp());
        for (uint256 k = 1; k <= 3; ++k) {
            for (uint256 v = 0; v <= 4; ++v) {
                for (uint256 s = 0; s < 8; ++s) {
                    if (ss.accepts(address(uint160(0x9000 + k)), v, q[s], 0)) bits |= (uint256(1) << ((k - 1) * 40 + v * 8 + s));
                }
            }
        }
    }

    /// SR-1, SR-2, SR-5 on the present state. Returns "" if they hold.
    function check(SignerSetModel ss) internal view returns (string memory) {
        uint256 grace = ss.grace();
        uint256[8] memory q = sampleTimes(vm.getBlockTimestamp());
        for (uint256 k = 1; k <= 3; ++k) {
            address key = address(uint160(0x9000 + k));
            for (uint256 v = 0; v <= 4; ++v) {
                (uint256 activeFrom, uint256 retiredAt, bool stopped, bool active,) = ss.sets(v);
                for (uint256 s = 0; s < 8; ++s) {
                    bool ok = ss.accepts(key, v, q[s], 0);
                    if (ss.removedAt(key) != 0 && ok) return "SR-1: a removed key is accepted";
                    if (ok && !(active && ss.isMember(v, key) && !stopped && activeFrom <= q[s])) return "a quote is accepted outside Q1 and Q13";
                    if (ok && retiredAt != 0 && !(q[s] < retiredAt && vm.getBlockTimestamp() <= retiredAt + grace)) return "SR-2: a retired set accepts too much";
                    if (active && retiredAt != 0 && (q[s] >= retiredAt || vm.getBlockTimestamp() > retiredAt + grace) && ok) return "SR-2: late or later-issued quote accepted";
                }
            }
        }
        uint256 cur = ss.current();
        if (cur != 0) {
            (,, bool curStopped,,) = ss.sets(cur);
            bool allRemoved = true;
            for (uint256 j = 1; j <= 3; ++j) {
                if (ss.isMember(cur, address(uint160(0x9000 + j))) && ss.removedAt(address(uint160(0x9000 + j))) == 0) allRemoved = false;
            }
            if (curStopped || allRemoved) {
                for (uint256 k2 = 1; k2 <= 3; ++k2) {
                    for (uint256 s2 = 0; s2 < 8; ++s2) {
                        if (ss.accepts(address(uint160(0x9000 + k2)), cur, q[s2], 0)) return "SR-5: the current set verifies although it is dead";
                    }
                }
            }
        }
        return "";
    }

    /// SR-4: a key removed before a set became current is not a member of it.
    function checkTombstones(SignerSetModel ss) internal view returns (string memory) {
        for (uint256 v = 1; v <= 4; ++v) {
            (uint256 activeFrom,,, bool active,) = ss.sets(v);
            if (!active) continue;
            for (uint256 k = 1; k <= 3; ++k) {
                address key = address(uint160(0x9000 + k));
                uint256 r = ss.removedAt(key);
                if (ss.isMember(v, key) && r != 0 && activeFrom > r) return "SR-4: a tombstoned key entered a set that became current later";
            }
        }
        return "";
    }
}

/// Random actions on the signer-set model; ghost flags record the monotonicity of removal, stop and the passage of time (SR-3).
contract SignerSetHandler {
    Vm internal constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));

    SignerSetModel public ss;
    uint256 public nextVersion = 1;
    bool public monotoneViolated;
    bool public guardianAdded;

    constructor(SignerSetModel ss_) {
        ss = ss_;
    }

    function _members(uint8 mask) internal pure returns (address[] memory out) {
        uint256 m = 1 + (uint256(mask) % 7);
        uint256 n = 0;
        address[] memory tmp = new address[](3);
        for (uint256 k = 1; k <= 3; ++k) {
            if ((m >> (k - 1)) & 1 == 1) {
                tmp[n] = address(uint160(0x9000 + k));
                n += 1;
            }
        }
        out = new address[](n);
        for (uint256 i = 0; i < n; ++i) {
            out[i] = tmp[i];
        }
    }

    function _guarded(uint256 before) internal {
        uint256 afterBits = SignerChecks.bitmap(ss);
        if (afterBits & ~before != 0) monotoneViolated = true; // Accept_after must be a subset of Accept_before
    }

    function warp(uint16 dt) external {
        uint256 before = SignerChecks.bitmap(ss);
        vm.warp(vm.getBlockTimestamp() + 1 + (uint256(dt) % 400));
        _guarded(before);
    }

    function proposeAndActivate(uint8 mask) external {
        if (nextVersion > 4) return;
        try ss.proposeSignerSet(0, nextVersion, _members(mask), 0) {
            try ss.activateSignerSet(0, nextVersion, 0) {
                nextVersion += 1;
            } catch {}
        } catch {}
    }

    function remove(uint8 keySel) external {
        uint256 before = SignerChecks.bitmap(ss);
        ss.removeQuoteSigner(1, address(uint160(0x9001 + (uint256(keySel) % 3))));
        _guarded(before);
    }

    function stop(uint8 versionSel) external {
        uint256 before = SignerChecks.bitmap(ss);
        try ss.stopSignerSet(1, 1 + (uint256(versionSel) % 4)) {} catch {}
        _guarded(before);
    }

    /// SR-7: the guardian cannot add a set or activate one.
    function guardianTries(uint8 mask) external {
        try ss.proposeSignerSet(1, 9, _members(mask), 0) {
            guardianAdded = true;
        } catch {}
        try ss.activateSignerSet(1, nextVersion, 0) {
            guardianAdded = true;
        } catch {}
    }
}

contract SignerSetTest is Test {
    uint256 internal constant T0 = 1_800_000_000;
    uint256 internal constant GRACE = 300;

    SignerSetModel internal ss;
    SignerSetHandler internal handler;

    function setUp() public {
        vm.warp(T0);
        ss = new SignerSetModel(GRACE);
        handler = new SignerSetHandler(ss);
        targetContract(address(handler));
    }

    // ---- invariants over the handler's random histories
    function invariant_SR1_SR2_SR5_HoldInEveryState() public {
        assertEq(SignerChecks.check(ss), "");
    }

    function invariant_SR3_RemovalStopAndTimeOnlyShrinkAcceptance() public {
        assertFalse(handler.monotoneViolated());
    }

    function invariant_SR4_TombstonePermanence() public {
        assertEq(SignerChecks.checkTombstones(ss), "");
    }

    function invariant_SR7_GuardianCannotAdd() public {
        assertFalse(handler.guardianAdded());
    }

    // ---- the same properties as fuzz tests over seeded histories
    function _apply(uint256 r) internal {
        uint256 choice = r % 5;
        uint256 v = 1 + (r / 5) % 4;
        if (choice == 0) {
            vm.warp(vm.getBlockTimestamp() + 1 + (r / 7) % 400);
        } else if (choice == 1) {
            address[] memory m = new address[](2);
            m[0] = address(uint160(0x9001 + (r / 11) % 3));
            m[1] = address(uint160(0x9001 + (r / 13) % 3));
            if (m[0] == m[1]) {
                m = new address[](1);
                m[0] = address(uint160(0x9001 + (r / 11) % 3));
            }
            try ss.proposeSignerSet(0, v, m, 0) {} catch {}
        } else if (choice == 2) {
            try ss.activateSignerSet(0, v, 0) {} catch {}
        } else if (choice == 3) {
            ss.removeQuoteSigner(1, address(uint160(0x9001 + (r / 17) % 3)));
        } else {
            try ss.stopSignerSet(1, v) {} catch {}
        }
    }

    function testFuzz_SR1_to_SR5_OnRandomHistories(uint256 seed) public {
        for (uint256 i = 0; i < 16; ++i) {
            uint256 r = uint256(keccak256(abi.encode(seed, i)));
            uint256 before = SignerChecks.bitmap(ss);
            uint256 choice = r % 5;
            _apply(r);
            uint256 afterBits = SignerChecks.bitmap(ss);
            if (choice == 0 || choice == 3 || choice == 4) {
                assertEq(afterBits & ~before, 0, "SR-3: removal, stop and time never make a rejected quote acceptable");
            }
            assertEq(SignerChecks.check(ss), "");
            assertEq(SignerChecks.checkTombstones(ss), "");
        }
    }

    function testFuzz_SR7_GuardianCannotAddFromAnyHistory(uint256 seed, uint8 mask) public {
        for (uint256 i = 0; i < 8; ++i) {
            _apply(uint256(keccak256(abi.encode(seed, i))));
        }
        address[] memory m = new address[](1);
        m[0] = address(uint160(0x9001 + (uint256(mask) % 3)));
        vm.expectRevert(NotGovernance.selector);
        ss.proposeSignerSet(1, 99, m, 0);
        uint256 nextVersion = ss.current() + 1; // read before vm.expectRevert: the expectation applies to the next external call
        vm.expectRevert(NotGovernance.selector);
        ss.activateSignerSet(1, nextVersion, 0);
    }

    // ---- CAP-TV-27, 31 extensions: tombstones and idempotent removal (the vectors themselves are generated: CAP_TV_*)
    function test_Tombstone_IsPermanentAndRemovalIsIdempotent() public {
        address k = address(uint160(0x9001));
        ss.removeQuoteSigner(1, k);
        uint256 first = ss.removedAt(k);
        vm.warp(vm.getBlockTimestamp() + 50);
        ss.removeQuoteSigner(1, k);
        ss.removeQuoteSigner(0, k);
        assertEq(ss.removedAt(k), first, "a second removal changes nothing");
        address[] memory m = new address[](1);
        m[0] = k;
        vm.expectRevert(abi.encodeWithSelector(QuoteSignerTombstoned.selector, k));
        ss.proposeSignerSet(0, 1, m, 0);
    }

    function testFuzz_TombstoneSurvivesAnyHistory(uint256 seed) public {
        address k = address(uint160(0x9002));
        ss.removeQuoteSigner(1, k);
        uint256 removed = ss.removedAt(k);
        for (uint256 i = 0; i < 10; ++i) {
            _apply(uint256(keccak256(abi.encode(seed, i))));
        }
        assertEq(ss.removedAt(k), removed);
    }
}
