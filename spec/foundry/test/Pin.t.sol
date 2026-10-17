// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import "../src/Errors.sol";
import {PinModel} from "../src/PinModel.sol";
import {MigrationModel} from "../src/MigrationModel.sol";
import {Fixture} from "./helpers/Fixture.sol";

contract PinHarness {
    function auth(address customer, bool sender, uint8 path, bool sigOk, PinModel.Pin memory pin, bytes32 h, bytes32 hd) external pure {
        PinModel.authSignature(customer, sender, path, sigOk, pin, h, hd, 0);
    }

    function authExit(bool sender, uint8 path, bool sigOk, PinModel.Pin memory pin) external pure {
        PinModel.authExit(sender, path, sigOk, pin, 0);
    }
}

/// The account pin (document 17 section 5, ACP-TV-25 ... 44, I-ACCT-PIN, I-ACCT-NOWIDEN, I-ACCT-SIG, I-ACCT-VERSION).
///
/// ACP-TV-13 ... 17 and ACP-TV-25 ... 44 are exported from the Python model and run by test/generated/GenScenarios.t.sol
/// (ACP_TV_*; ACP-TV-41 ... 44 also have a backend half in vectors/backend.json that no contract can execute). This file EXTENDS them
/// with fuzz over the account state, the pin fields and the signature path, each restated here independently of PinModel:
///   testFuzz_PinOk              PIN_OK over (mode, account hash, delegate hash)                    ACP-TV-13 ... 17, 31 ... 33
///   testFuzz_WellFormed         PIN_WELLFORMED over random field combinations                      ACP-TV-25 ... 30
///   testFuzz_AuthTruthTable     AUTH over (mode, signatureMode, path, signature, account state)    ACP-TV-38 ... 40, I-ACCT-SIG
///   testFuzz_HashStructInjective each of the seven fields moves hashStruct                        ACP-TV-34
///   test_UpdateAccountPin_*     updateAccountPin changes only the pin and the version              I-ACCT-NOWIDEN, I-ACCT-VERSION, ACP-TV-35 ... 37
contract PinTest is Test {
    PinHarness internal h;
    Fixture internal fx;

    function setUp() public {
        vm.warp(1_800_000_000);
        h = new PinHarness();
        fx = new Fixture();
    }

    // ------------------------------------------------------------------------------------------------------------ generators
    function _pin(uint8 mode) internal pure returns (PinModel.Pin memory p) {
        address d1 = address(uint160(0x00abababababababababababababababababababab));
        if (mode == 1) {
            p = PinModel.Pin(1, PinModel.PIN_EOA, address(0), bytes32(0), bytes32(0), 1, 1);
        } else if (mode == 2) {
            p = PinModel.Pin(2, PinModel.designatorHash(d1), d1, keccak256("fastpay-test-delegate-code-v1"), keccak256("test-wallet/delegator/1"), 1, 2);
        } else if (mode == 3) {
            p = PinModel.Pin(3, keccak256("fastpay-test-account-code-v1"), address(0), bytes32(0), keccak256("test-wallet/account/1"), 1, 2);
        } else {
            p = PinModel.Pin(4, keccak256("fastpay-test-wallet1271-code-v1"), address(0), bytes32(0), keccak256("test-wallet/1271/1"), 1, 2);
        }
    }

    /// An account or delegate hash: 0, KECCAK_EMPTY, the pinned value, the pinned value with one bit flipped, or noise.
    function _hash(uint8 sel, bytes32 pinned, bytes32 noise) internal pure returns (bytes32) {
        if (sel % 5 == 0) return bytes32(0);
        if (sel % 5 == 1) return PinModel.KECCAK_EMPTY;
        if (sel % 5 == 2) return pinned;
        if (sel % 5 == 3) return pinned ^ bytes32(uint256(1));
        return noise;
    }

    // ------------------------------------------------------------------------------------------------------------ PIN_OK
    function testFuzz_PinOk(uint8 modeSel, uint8 hSel, uint8 hdSel, bytes32 noise) public {
        uint8 mode = 1 + (modeSel % 4);
        PinModel.Pin memory p = _pin(mode);
        bytes32 hh = _hash(hSel, p.accountCodeHash, noise);
        bytes32 hd = _hash(hdSel, p.delegateCodeHash, noise);
        bool want;
        if (mode == 1) want = hh == bytes32(0) || hh == PinModel.KECCAK_EMPTY;
        else if (mode == 2) want = hh == p.accountCodeHash && hd == p.delegateCodeHash;
        else want = hh == p.accountCodeHash;
        assertEq(PinModel.pinOk(p, hh, hd, 0), want);
        uint8 field = PinModel.checkField(p, hh, hd, 0);
        if (want) assertEq(uint256(field), 0);
        else if (mode == 2 && hh == p.accountCodeHash) assertEq(uint256(field), 2, "DELEGATE_CODE only when the account matches");
        else assertEq(uint256(field), 1);
    }

    // ------------------------------------------------------------------------------------------------------------ PIN_WELLFORMED
    function _wellFormedOracle(PinModel.Pin memory p) internal pure returns (bool) {
        if (p.pinVersion < 1 || p.accountMode < 1 || p.accountMode > 4) return false;
        bool zeroDelegates = p.delegate == address(0) && p.delegateCodeHash == bytes32(0);
        if (p.accountMode == 1) {
            return p.accountCodeHash == PinModel.PIN_EOA && zeroDelegates && p.implementationFamily == bytes32(0) && p.signatureMode <= 1;
        }
        if (p.accountMode == 2) {
            return p.delegate != address(0) && p.accountCodeHash == PinModel.designatorHash(p.delegate)
                && p.delegateCodeHash != bytes32(0) && p.delegateCodeHash != PinModel.KECCAK_EMPTY && p.implementationFamily != bytes32(0);
        }
        bool codeOk = p.accountCodeHash != bytes32(0) && p.accountCodeHash != PinModel.KECCAK_EMPTY && p.accountCodeHash != PinModel.PIN_EOA;
        return zeroDelegates && codeOk && p.implementationFamily != bytes32(0) && (p.signatureMode == 0 || p.signatureMode == 2);
    }

    function testFuzz_WellFormed(uint8 modeSel, uint256 flips, uint32 version, uint8 sig) public {
        PinModel.Pin memory p = _pin(1 + (modeSel % 4));
        if (flips & 1 != 0) p.accountCodeHash = bytes32(uint256(p.accountCodeHash) ^ 1);
        if (flips & 2 != 0) p.delegate = address(uint160(uint256(uint160(p.delegate)) ^ 1));
        if (flips & 4 != 0) p.delegateCodeHash = bytes32(uint256(p.delegateCodeHash) ^ 1);
        if (flips & 8 != 0) p.implementationFamily = bytes32(uint256(p.implementationFamily) ^ 1);
        if (flips & 16 != 0) p.delegateCodeHash = PinModel.KECCAK_EMPTY;
        if (flips & 32 != 0) p.accountCodeHash = PinModel.PIN_EOA;
        if (flips & 64 != 0) p.implementationFamily = bytes32(0);
        if (flips & 128 != 0) p.accountMode = uint8((uint256(modeSel) / 4) % 7);
        p.pinVersion = version % 3;
        p.signatureMode = sig % 4;
        assertEq(PinModel.wellFormed(p, 0), _wellFormedOracle(p));
    }

    function test_WellFormed_AsWritten_Mode2PutsNoBoundOnSignatureMode() public pure {
        // document 17 section 5.2 bounds signatureMode for modes 1, 3 and 4 only; section 5.1 says mode 2 allows 0, 1 and 2.
        // The model implements the predicate as written, so a mode-2 pin with signatureMode 7 is "well formed" (document issue).
        PinModel.Pin memory p = _pin(2);
        p.signatureMode = 7;
        require(PinModel.wellFormed(p, 0));
    }

    // ------------------------------------------------------------------------------------------------------------ I-ACCT-SIG
    function testFuzz_AuthTruthTable(uint8 modeSel, uint8 sigMode, uint8 path, bool sigOk, bool sender, uint8 stateSel) public {
        uint8 mode = 1 + (modeSel % 4);
        PinModel.Pin memory p = _pin(mode);
        p.signatureMode = sigMode % 3;
        path = path % 3;
        address cust = address(uint160(0xC0FFEE));
        bytes32 hh = mode == 1 ? bytes32(0) : p.accountCodeHash;
        bytes32 hd = p.delegateCodeHash;
        if (stateSel % 3 == 1) hh = mode == 1 ? PinModel.designatorHash(address(uint160(0xAB))) : bytes32(uint256(hh) ^ 1);
        if (stateSel % 3 == 2) hd = bytes32(uint256(hd) ^ 1);
        bool holds = PinModel.pinOk(p, hh, hd, 0);
        bool want = sender || (path == 1 && p.signatureMode == 1 && sigOk) || (path == 2 && p.signatureMode == 2 && holds && sigOk);
        bool got = true;
        bytes4 sel = bytes4(0);
        try h.auth(cust, sender, path, sigOk, p, hh, hd) {} catch (bytes memory err) {
            got = false;
            sel = bytes4(err);
        }
        assertEq(got, want, "I-ACCT-SIG");
        if (!got && !sender && path == 2 && p.signatureMode == 2 && !holds) assertEq(bytes32(sel), bytes32(AccountCodeChanged.selector));
        if (!got && !sender && path != 0 && p.signatureMode == 0) assertEq(bytes32(sel), bytes32(SignatureModeNotPermitted.selector));
        // exits are accepted through either path whatever the mode or the account
        bool exitWant = sender || (path != 0 && sigOk);
        bool exitGot = true;
        try h.authExit(sender, path, sigOk, p) {} catch {
            exitGot = false;
        }
        assertEq(exitGot, exitWant, "exits are never gated by the signature mode");
    }

    // ------------------------------------------------------------------------------------------------------------ the typed struct
    function testFuzz_HashStructInjective(uint8 modeSel, uint8 field) public {
        PinModel.Pin memory a = _pin(1 + (modeSel % 4));
        PinModel.Pin memory b = _pin(1 + (modeSel % 4));
        field = field % 7;
        if (field == 0) b.accountMode ^= 8;
        else if (field == 1) b.accountCodeHash = bytes32(uint256(b.accountCodeHash) ^ 1);
        else if (field == 2) b.delegate = address(uint160(uint256(uint160(b.delegate)) ^ 1));
        else if (field == 3) b.delegateCodeHash = bytes32(uint256(b.delegateCodeHash) ^ 1);
        else if (field == 4) b.implementationFamily = bytes32(uint256(b.implementationFamily) ^ 1);
        else if (field == 5) b.pinVersion ^= 1;
        else b.signatureMode ^= 4;
        assertTrue(PinModel.structHash(a) != PinModel.structHash(b), "each of the seven fields is covered by hashStruct");
        assertEq(PinModel.structHash(a), PinModel.structHash(_pin(1 + (modeSel % 4))));
    }

    // ------------------------------------------------------------------------------------------------------------ updateAccountPin
    function test_UpdateAccountPin_ChangesOnlyThePinAndItsVersion() public {
        (bytes32 lid, bytes32 mid) = fx.activate(fx.R0(), fx.one(fx.T1()));
        MigrationModel mgr = fx.mgr();
        MigrationModel.Mandate memory before = mgr.getMandate(mid);
        bytes32 termsDigest = keccak256(abi.encode(mgr.mandateTerms(mid)));
        PinModel.Pin memory newPin = _pin(1);
        newPin.pinVersion = 2; // every field equal, version + 1: the re-verification attestation (ACP-TV-36)
        mgr.updateAccountPin(mid, newPin, vm.getBlockTimestamp() + 10, 1, MigrationModel.Access(true, 0, false), 0);
        MigrationModel.Mandate memory afterM = mgr.getMandate(mid);
        assertEq(afterM.id, before.id);
        assertEq(afterM.lineageId, before.lineageId);
        assertEq(afterM.termsKey, before.termsKey, "terms are untouched (I-ACCT-NOWIDEN)");
        assertEq(afterM.router, before.router);
        assertEq(uint256(afterM.status), uint256(before.status));
        assertEq(uint256(afterM.pause), uint256(before.pause));
        assertTrue(afterM.pinKey != before.pinKey, "the pin hash moved");
        assertEq(keccak256(abi.encode(mgr.mandateTerms(mid))), termsDigest);
        (,,, uint32 pv,,) = mgr.lineages(lid);
        assertEq(uint256(pv), 2);
        assertEq(uint256(mgr.live(fx.CUSTOMER(), fx.R0(), fx.T1())), 1, "the exposure index is untouched");
    }

    function test_UpdateAccountPin_VersionIsMonotone() public {
        (bytes32 lid, bytes32 mid) = fx.activate(fx.R0(), fx.one(fx.T1()));
        MigrationModel mgr = fx.mgr();
        for (uint32 v = 2; v <= 6; ++v) {
            PinModel.Pin memory p = _pin(1);
            p.pinVersion = v;
            mgr.updateAccountPin(mid, p, vm.getBlockTimestamp() + 10, v, MigrationModel.Access(true, 0, false), 0);
            (,,, uint32 pv,,) = mgr.lineages(lid);
            assertEq(uint256(pv), v);
            // a replay of the same version and a skip are both refused
            vm.expectRevert(PinVersionMismatch.selector);
            mgr.updateAccountPin(mid, p, vm.getBlockTimestamp() + 10, 100 + v, MigrationModel.Access(true, 0, false), 0);
            p.pinVersion = v + 2;
            vm.expectRevert(PinVersionMismatch.selector);
            mgr.updateAccountPin(mid, p, vm.getBlockTimestamp() + 10, 200 + v, MigrationModel.Access(true, 0, false), 0);
        }
    }

    function test_UpdateAccountPin_RefusedUpdateChangesNothing() public {
        (, bytes32 mid) = fx.activate(fx.R0(), fx.one(fx.T1()));
        MigrationModel mgr = fx.mgr();
        bytes32 before = mgr.mandateDigest(mid);
        PinModel.Pin memory p = _pin(2); // a 7702 pin while the account has no delegation: PIN_OK fails
        p.pinVersion = 2;
        vm.expectRevert(AccountPinMismatch.selector);
        mgr.updateAccountPin(mid, p, vm.getBlockTimestamp() + 10, 1, MigrationModel.Access(true, 0, false), 0);
        assertEq(mgr.mandateDigest(mid), before);
        vm.expectRevert(NotCustomer.selector); // ACP-TV-21: a third party without a signature
        mgr.updateAccountPin(mid, _pin(1), vm.getBlockTimestamp() + 10, 1, MigrationModel.Access(false, 0, false), 0);
    }
}
