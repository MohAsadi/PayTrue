// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.24;

import {Vm} from "forge-std/Vm.sol";
import "../../src/Errors.sol";
import "../../src/Mutants.sol";
import {WidthLib} from "../../src/WidthLib.sol";
import {AllowanceMath, Permit2Mock} from "../../src/Permit2Mock.sol";
import {RegistryModel} from "../../src/RegistryModel.sol";
import {PinModel} from "../../src/PinModel.sol";
import {ContainModel} from "../../src/ContainModel.sol";
import {HashModel} from "../../src/HashModel.sol";
import {TimeModel} from "../../src/TimeModel.sol";
import {MigrationModel} from "../../src/MigrationModel.sol";
import {SignerSetModel} from "../../src/SignerSetModel.sol";
import "../generated/GenOps.sol";
import {GenErrorIds} from "../generated/GenErrorIds.sol";

error ExpectFailed();
/// A TERMS_SET named a field number that was retired (13 was the upper price bound; the band is now read from the registry by the bounds
/// version, field 12). tools/scenario_vm.py raises RetiredField for the same program.
error RetiredTermsField();

/// The Solidity interpreter of the scenario programs of tools/scenario_vm.py (the oracle that produced every expectation).
/// A program is a flat array of 8-word instructions [op, a, b, c, d, e, expectSel, expectArg]; expectSel is 0 when the instruction
/// must succeed, otherwise the id of the custom error it must revert with (GenErrorIds), and expectArg the compared argument
/// (a token slot, a signer-key slot, or a plain number). Every instruction runs in a self-call, so a revert undoes everything the
/// instruction did, like a transaction. Each run uses fresh customers and routers (an `instance` namespace) so that one deployed
/// model serves every scenario; delegate code hashes, the only shared addresses, are reset at the end of a run.
contract ScenarioVM {
    Vm internal constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));

    uint256 internal constant QUOTE_SET_GRACE = 300; // PC-08, proposal (the same value as protocol_model.QUOTE_SET_GRACE)
    uint256 internal constant NONE = type(uint256).max;

    Permit2Mock public p2;
    RegistryModel public reg;
    MigrationModel public mgr;
    SignerSetModel public ss;

    uint256 public instance;
    uint256 public mutant;
    uint256 public firstFailurePc;
    uint256 public failureCount;

    uint256[8] internal regs;
    ContainModel.Terms[8] internal terms;
    uint256 internal termsInit;
    PinModel.Pin[8] internal pins;
    uint256 internal pinsInit;
    MigrationModel.Auth internal auth;
    MigrationModel.Access internal access;
    uint256 internal authNonce;
    bytes32[64] internal lineageId;
    uint256 internal knownMask;
    bytes32[4] internal snaps;
    address[] internal touched;

    constructor() {
        p2 = new Permit2Mock();
        reg = new RegistryModel();
        mgr = new MigrationModel(p2, reg);
    }

    // ------------------------------------------------------------------------------------------------------------ addresses
    function customerAddr(uint256 slot) public view returns (address) {
        return address(uint160(uint256(keccak256(abi.encode("fastpay.vm.customer", instance, slot)))));
    }

    function routerAddr(uint256 slot) public view returns (address) {
        return address(uint160(uint256(keccak256(abi.encode("fastpay.vm.router", instance, slot)))));
    }

    function tokenAddr(uint256 id) public pure returns (address) {
        return address(uint160(0x7000 + id));
    }

    function keyAddr(uint256 slot) public pure returns (address) {
        return address(uint160(0x9000 + slot));
    }

    // ------------------------------------------------------------------------------------------------------------ running programs
    function _reset(uint256 mut) internal {
        instance += 1;
        mutant = mut;
        delete regs;
        termsInit = 0;
        pinsInit = 0;
        delete auth;
        access = MigrationModel.Access(true, 0, false);
        authNonce = 1;
        knownMask = 0;
        delete snaps;
        ss = SignerSetModel(address(0));
    }

    function _cleanup() internal {
        for (uint256 i = 0; i < touched.length; ++i) {
            mgr.setCodeHash(touched[i], bytes32(0));
        }
        delete touched;
    }

    /// Run a program on the model with mutant `mut` (0 = the specification); returns the number of instructions whose expectation failed.
    function run(uint256[] memory prog, uint256 mut) external returns (uint256) {
        _reset(mut);
        vm.warp(T0);
        failureCount = 0;
        firstFailurePc = NONE;
        uint256 n = prog.length / WORDS;
        for (uint256 pc = 0; pc < n; ++pc) {
            if (prog[pc * WORDS] >= OP_SS_PROPOSE && prog[pc * WORDS] <= OP_SS_VERIFY && address(ss) == address(0)) {
                ss = new SignerSetModel(QUOTE_SET_GRACE);
            }
            uint256[8] memory ins;
            for (uint256 k = 0; k < WORDS; ++k) {
                ins[k] = prog[pc * WORDS + k];
            }
            if (!_step(ins)) {
                if (failureCount == 0) firstFailurePc = pc;
                failureCount += 1;
            }
        }
        _cleanup();
        return failureCount;
    }

    /// One row of a transition table: BUILD the state, ACT with the expected outcome, OBSERVE the next state. Returns true if all hold.
    function replayTransition(uint256 config, uint256 key, uint256 action, uint256 expSel, uint256 expArg, uint256 nextKey, uint256 mut)
        external
        returns (bool)
    {
        _reset(mut);
        vm.warp(T0);
        if (expArg == 255) expArg = NONE; // "not compared" in a table
        uint256[8] memory build = [OP_BUILD, config, key, 0, 0, 0, 0, 0];
        uint256[8] memory act = [OP_ACT, config, action, 0, 0, 0, expSel, expArg];
        uint256[8] memory obs = [OP_OBSERVE, config, nextKey, 0, 0, 0, 0, 0];
        bool ok = _step(build) && _step(act) && _step(obs);
        _cleanup();
        return ok;
    }

    function _step(uint256[8] memory ins) internal returns (bool) {
        (bool ok, bytes memory ret) = address(this).call(abi.encodeCall(this.exec, (ins[0], ins[1], ins[2], ins[3], ins[4], ins[5])));
        uint256 expectSel = ins[6];
        if (ok) return expectSel == 0;
        if (expectSel == 0) return false;
        return _matches(ret, expectSel, ins[7]);
    }

    function _matches(bytes memory ret, uint256 expectSel, uint256 expectArg) internal pure returns (bool) {
        if (ret.length < 4) return false;
        uint256 id = GenErrorIds.idOf(bytes4(ret));
        if (id != expectSel) return false;
        uint256 kind = GenErrorIds.argKind(id);
        if (kind == 0 || expectArg == NONE) return true;
        uint256 got = _word(ret, GenErrorIds.argIndex(id));
        uint256 want = expectArg;
        if (kind == 2) want = uint256(uint160(tokenAddr(expectArg)));
        if (kind == 3) want = uint256(uint160(keyAddr(expectArg)));
        return got == want;
    }

    function _word(bytes memory ret, uint256 idx) internal pure returns (uint256) {
        uint256 start = 4 + 32 * idx;
        if (ret.length < start + 32) return NONE;
        bytes memory chunk = new bytes(32);
        for (uint256 i = 0; i < 32; ++i) {
            chunk[i] = ret[start + i];
        }
        return abi.decode(chunk, (uint256));
    }

    // ------------------------------------------------------------------------------------------------------------ registers
    function _baseTerms(uint256 n) internal pure returns (ContainModel.Terms memory t) {
        t.expiresAt = 1_900_000_000;
        t.merchantId = bytes32(uint256(0xA1));
        t.recipientPolicy = bytes32(uint256(0xB1));
        t.subscriptionRef = bytes32(uint256(0xC1));
        t.periodSeconds = 2_592_000;
        t.anchorStartsAt = 1_800_000_000;
        t.currency = 840;
        t.maxQuoteAge = 120;
        t.boundsVersion = 1;
        t.maxChargesPerPeriod = 1;
        t.minInterval = 86_400;
        t.maxFeeBps = 100;
        t.nTokens = uint8(n);
        for (uint256 i = 0; i < n; ++i) {
            t.tokens[i] = tokenAddr(i + 1);
            _defaultCaps(t, i);
        }
    }

    function _defaultCaps(ContainModel.Terms memory t, uint256 i) internal pure {
        t.caps[i][0] = 50;
        t.caps[i][1] = 1000;
        t.caps[i][2] = 0;
        t.caps[i][3] = 0;
        t.caps[i][4] = 500;
        t.caps[i][5] = 0;
    }

    function _T(uint256 i) internal returns (ContainModel.Terms memory) {
        if ((termsInit >> i) & 1 == 0) {
            terms[i] = _baseTerms(1);
            termsInit |= (uint256(1) << i);
        }
        return terms[i];
    }

    function _P(uint256 i) internal returns (PinModel.Pin memory) {
        if ((pinsInit >> i) & 1 == 0) {
            delete pins[i];
            pinsInit |= (uint256(1) << i);
        }
        return pins[i];
    }

    function _setTerms(uint256 i, ContainModel.Terms memory t) internal {
        terms[i] = t;
        termsInit |= (uint256(1) << i);
    }

    function _setPin(uint256 i, PinModel.Pin memory p) internal {
        pins[i] = p;
        pinsInit |= (uint256(1) << i);
    }

    function _pinPreset(uint256 preset) internal pure returns (PinModel.Pin memory p) {
        if (preset == PP_EOA) {
            p = PinModel.Pin(1, PinModel.PIN_EOA, address(0), bytes32(0), bytes32(0), 1, 1);
        } else if (preset == PP_7702) {
            address d1 = address(uint160(0x00abababababababababababababababababababab));
            p = PinModel.Pin(
                2, PinModel.designatorHash(d1), d1, keccak256("fastpay-test-delegate-code-v1"), keccak256("test-wallet/delegator/1"), 1, 2
            );
        } else if (preset == PP_4337) {
            p = PinModel.Pin(3, keccak256("fastpay-test-account-code-v1"), address(0), bytes32(0), keccak256("test-wallet/account/1"), 1, 2);
        } else {
            p = PinModel.Pin(4, keccak256("fastpay-test-wallet1271-code-v1"), address(0), bytes32(0), keccak256("test-wallet/1271/1"), 1, 2);
        }
    }

    function _mid(uint256 slot, uint256 genPlus1) internal view returns (bytes32) {
        bytes32 lid = lineageId[slot];
        if (genPlus1 == 0) return mgr.activeMandateOf(lid);
        return mgr.lineageMandateIds(lid, genPlus1 - 1);
    }

    /// The predecessor a successor call names: the active mandate, or generation regs[2] - 1 when regs[2] != 0.
    function _predecessor(uint256 slot) internal view returns (bytes32) {
        bytes32 lid = lineageId[slot];
        if (regs[2] == 0) return mgr.activeMandateOf(lid);
        return mgr.lineageMandateIds(lid, regs[2] - 1);
    }

    // ------------------------------------------------------------------------------------------------------------ dispatcher
    function exec(uint256 op, uint256 a, uint256 b, uint256 c, uint256 d, uint256 e) external {
        if (op < OP_P2_APPROVE) {
            _execWorld(op, a, b, c, d);
        } else if (op < OP_TERMS_RESET) {
            _execPermit2(op, a, b, c, d, e);
        } else if (op < OP_ACTIVATE) {
            _execRegisters(op, a, b, c, d, e);
        } else if (op < OP_EXPECT_STATUS) {
            _execMandates(op, a, b, c, d, e);
        } else if (op < OP_CHK_WF) {
            _execExpect(op, a, b, c, d, e);
        } else if (op < OP_SS_PROPOSE) {
            _execChecks(op, a, b, c, d, e);
        } else if (op < OP_BUILD) {
            _execMisc(op, a, b, c, d, e);
        } else if (op == OP_BUILD) {
            _build(a, b);
        } else if (op == OP_ACT) {
            _act(a, b);
        } else if (op == OP_OBSERVE) {
            if (_observe(a) != b) revert ExpectFailed();
        } else if (op == OP_W_CYCLE) {
            TimeModel.cycleAllowed(a, block.timestamp, b, c, mutant);
        } else if (op == OP_W_WINDOW) {
            if (TimeModel.windowIndex(a, b, c, mutant) != d) revert ExpectFailed();
        } else {
            revert ExpectFailed();
        }
    }

    function _execWorld(uint256 op, uint256 a, uint256 b, uint256 c, uint256 d) internal {
        if (op == OP_NOW) {
            vm.warp(a);
        } else if (op == OP_SETREG) {
            regs[a] = b;
        } else if (op == OP_REG_REGISTER) {
            _regRegister(a);
        } else if (op == OP_REG_PROPOSE) {
            reg.propose(routerAddr(a), bytes32(0xC0DE00 + a), uint32(a + 1), instance);
        } else if (op == OP_REG_DEPRECATE) {
            reg.deprecate(routerAddr(a), routerAddr(b), WidthLib.toUint8(c), d, mutant);
        } else if (op == OP_REG_DISABLE) {
            reg.emergencyDisable(routerAddr(a));
        } else if (op == OP_REG_CLEAR) {
            reg.clearEmergency(routerAddr(a));
        } else if (op == OP_REG_SUNSET) {
            reg.sunset(routerAddr(a), mutant);
        } else if (op == OP_REG_RETIRE) {
            reg.retire(routerAddr(a), mutant);
        } else if (op == OP_FORCE_REG) {
            reg.forceState(routerAddr(a), WidthLib.toUint8(b), WidthLib.toUint8(c), d);
        } else {
            revert ExpectFailed();
        }
    }

    function _regRegister(uint256 slot) internal {
        reg.registerActive(routerAddr(slot), bytes32(0xC0DE00 + slot), uint32(slot + 1), instance);
    }

    function _execPermit2(uint256 op, uint256 a, uint256 b, uint256 c, uint256 d, uint256 e) internal {
        if (op == OP_P2_APPROVE) {
            p2.approveAs(customerAddr(a), tokenAddr(b), routerAddr(c), d, e);
        } else if (op == OP_P2_LOCKDOWN) {
            p2.lockdownAs(customerAddr(a), tokenAddr(b), routerAddr(c));
        } else if (op == OP_P2_TRANSFER) {
            p2.pullAs(routerAddr(a), customerAddr(b), tokenAddr(c), d);
        } else if (op == OP_P2_REGRANT) {
            (,, uint48 nonce) = p2.allowance(customerAddr(a), tokenAddr(b), routerAddr(c));
            p2.permitRegrantAs(customerAddr(a), tokenAddr(b), routerAddr(c), d, e, nonce);
        } else if (op == OP_P2_INVALIDATE) {
            p2.invalidateAs(customerAddr(a), tokenAddr(b), routerAddr(c), d);
        } else if (op == OP_P2_EXPECT) {
            (uint160 amount, uint48 expiration,) = p2.allowance(customerAddr(a), tokenAddr(b), routerAddr(c));
            if (amount != d || expiration != e) revert ExpectFailed();
        } else if (op == OP_P2_EXPECT_NONCE) {
            (,, uint48 nonce2) = p2.allowance(customerAddr(a), tokenAddr(b), routerAddr(c));
            if (nonce2 != d) revert ExpectFailed();
        } else {
            revert ExpectFailed();
        }
    }

    function _execRegisters(uint256 op, uint256 a, uint256 b, uint256 c, uint256 d, uint256 e) internal {
        if (op == OP_TERMS_RESET) {
            _setTerms(a, _baseTerms(b));
        } else if (op == OP_TERMS_COPY) {
            _setTerms(a, _T(b));
        } else if (op == OP_TERMS_SET) {
            _termsSet(a, b, c, d, e);
        } else if (op == OP_PIN_PRESET) {
            _setPin(a, _pinPreset(b));
        } else if (op == OP_PIN_SET) {
            _pinSet(a, b, c);
        } else if (op == OP_ACCT_SET) {
            mgr.setCodeHash(customerAddr(a), bytes32(b));
        } else if (op == OP_DELEG_SET) {
            address dl = address(uint160(WidthLib.toUint160(a)));
            mgr.setCodeHash(dl, bytes32(b));
            touched.push(dl);
        } else {
            revert ExpectFailed();
        }
    }

    function _termsSet(uint256 slot, uint256 field, uint256 c, uint256 d, uint256 e) internal {
        ContainModel.Terms memory t = _T(slot);
        if (field == T_EXPIRES) {
            t.expiresAt = WidthLib.toUint64(e);
        } else if (field == T_MERCHANT) {
            t.merchantId = bytes32(e);
        } else if (field == T_RECIPIENT) {
            t.recipientPolicy = bytes32(e);
        } else if (field == T_SUBREF) {
            t.subscriptionRef = bytes32(e);
        } else if (field == T_PERIOD) {
            t.periodSeconds = WidthLib.toUint64(e);
        } else if (field == T_ANCHOR) {
            t.anchorStartsAt = WidthLib.toUint64(e);
        } else if (field == T_CURRENCY) {
            t.currency = WidthLib.toUint16(e);
        } else if (field == T_TOKENS) {
            _setTokens(t, c, d, e);
        } else if (field == T_CAP) {
            (uint256 idx, bool found) = ContainModel.indexOf(t, tokenAddr(c));
            if (!found) revert ExpectFailed();
            t.caps[idx][d] = e;
        } else if (field == T_FIAT) {
            t.fiat[c] = e;
        } else if (field == T_QAGE) {
            t.maxQuoteAge = WidthLib.toUint64(e);
        } else if (field == T_BVER) {
            t.boundsVersion = WidthLib.toUint32(e);
        } else if (field == T_RETIRED_BMAX) {
            revert RetiredTermsField();
        } else if (field == T_CHARGES) {
            t.maxChargesPerPeriod = WidthLib.toUint32(e);
        } else if (field == T_MININT) {
            t.minInterval = WidthLib.toUint64(e);
        } else if (field == T_FEE) {
            t.maxFeeBps = WidthLib.toUint16(e);
        } else if (field == T_EXT) {
            t.extensionsHash = bytes32(e);
        } else {
            revert ExpectFailed();
        }
        _setTerms(slot, t);
    }

    /// The token list becomes the ids c, d, e (0 = unused), sorted; tokens that stay keep their caps, new ones get the default caps.
    function _setTokens(ContainModel.Terms memory t, uint256 c, uint256 d, uint256 e) internal pure {
        address[3] memory oldTokens;
        uint256[6][3] memory oldCaps;
        for (uint256 q = 0; q < 3; ++q) {
            oldTokens[q] = t.tokens[q];
            for (uint256 w = 0; w < 6; ++w) {
                oldCaps[q][w] = t.caps[q][w];
            }
        }
        uint256 oldN = t.nTokens;
        uint256[3] memory ids = [c, d, e];
        // sort ascending and drop zeros and duplicates
        uint256 n = 0;
        uint256[3] memory sorted;
        for (uint256 i = 0; i < 3; ++i) {
            if (ids[i] == 0) continue;
            bool dup = false;
            for (uint256 j = 0; j < n; ++j) {
                if (sorted[j] == ids[i]) dup = true;
            }
            if (dup) continue;
            uint256 pos = n;
            while (pos > 0 && sorted[pos - 1] > ids[i]) {
                sorted[pos] = sorted[pos - 1];
                pos -= 1;
            }
            sorted[pos] = ids[i];
            n += 1;
        }
        t.nTokens = uint8(n);
        for (uint256 k = 0; k < 3; ++k) {
            if (k >= n) {
                t.tokens[k] = address(0);
                for (uint256 z = 0; z < 6; ++z) {
                    t.caps[k][z] = 0;
                }
                continue;
            }
            t.tokens[k] = tokenAddr(sorted[k]);
            bool kept = false;
            for (uint256 m = 0; m < oldN; ++m) {
                if (oldTokens[m] == t.tokens[k]) {
                    kept = true;
                    for (uint256 f = 0; f < 6; ++f) {
                        t.caps[k][f] = oldCaps[m][f];
                    }
                }
            }
            if (!kept) _defaultCaps(t, k);
        }
    }

    function _pinSet(uint256 slot, uint256 field, uint256 v) internal {
        PinModel.Pin memory p = _P(slot);
        if (field == PF_MODE) {
            p.accountMode = WidthLib.toUint8(v);
        } else if (field == PF_CODE) {
            p.accountCodeHash = bytes32(v);
        } else if (field == PF_DELEGATE) {
            p.delegate = address(WidthLib.toUint160(v));
        } else if (field == PF_DCODE) {
            p.delegateCodeHash = bytes32(v);
        } else if (field == PF_FAMILY) {
            p.implementationFamily = bytes32(v);
        } else if (field == PF_VERSION) {
            p.pinVersion = WidthLib.toUint32(v);
        } else if (field == PF_SIG) {
            p.signatureMode = WidthLib.toUint8(v);
        } else {
            revert ExpectFailed();
        }
        _setPin(slot, p);
    }

    // ------------------------------------------------------------------------------------------------------------ mandates
    function _execMandates(uint256 op, uint256 a, uint256 b, uint256 c, uint256 d, uint256 e) internal {
        if (op == OP_ACTIVATE) {
            (bytes32 lid,) = mgr.activate(customerAddr(b), a, routerAddr(c), _T(d), _P(e), mutant);
            lineageId[a] = lid;
            knownMask |= (uint256(1) << a);
        } else if (op == OP_AUTH_NEW) {
            auth = mgr.buildAuth(_predecessor(a), WidthLib.toUint8(b), routerAddr(c), _T(d), _P(e), block.timestamp + 3600, authNonce);
            authNonce += 1;
            access = MigrationModel.Access(true, 0, false);
        } else if (op == OP_AUTH_SET) {
            _authSet(a, b);
        } else if (op == OP_AUTH_ACCESS) {
            access = MigrationModel.Access(a != 0, WidthLib.toUint8(b), c != 0);
        } else if (op == OP_SUCCESSOR) {
            MigrationModel.Auth memory au = auth;
            MigrationModel.Access memory ac = access;
            mgr.activateSuccessor(_predecessor(a), WidthLib.toUint8(b), routerAddr(c), _T(d), _P(e), au, ac, mutant);
        } else if (op == OP_REVOKE) {
            mgr.revoke(_mid(a, b), access.senderIsCustomer, mutant);
        } else if (op == OP_RETIRE) {
            mgr.retire(_mid(a, b), mutant);
        } else if (op == OP_REDUCE_DROP) {
            mgr.reduceDropToken(_mid(a, b), tokenAddr(c), mutant);
        } else if (op == OP_UPDATE_PIN) {
            MigrationModel.Access memory ac2 = access;
            mgr.updateAccountPin(_mid(a, b), _P(c), d, e, ac2, mutant);
        } else if (op == OP_CONSUME) {
            bytes32 mid = _mid(a, b);
            PinModel.Pin memory pin = regs[1] != 0 ? _P(regs[1] - 1) : mgr.mandatePin(mid);
            mgr.consume(routerAddr(c), mid, tokenAddr(d), e, regs[0], pin, mutant);
        } else if (op == OP_PAUSE) {
            mgr.setPause(_mid(a, b), WidthLib.toUint8(c), d != 0);
        } else {
            revert ExpectFailed();
        }
    }

    function _authSet(uint256 field, uint256 v) internal {
        if (field == AF_CUSTOMER) {
            auth.customer = customerAddr(v);
        } else if (field == AF_LINEAGE) {
            auth.lineageId = lineageId[v];
        } else if (field == AF_PRED) {
            auth.predecessorId = HashModel.mandateId(auth.lineageId, v);
        } else if (field == AF_KIND) {
            auth.kind = WidthLib.toUint8(v);
        } else if (field == AF_TERMS) {
            auth.newTermsHash = bytes32(v);
        } else if (field == AF_ROUTER) {
            auth.newRouter = routerAddr(v);
        } else if (field == AF_CODEHASH) {
            auth.newRouterCodeHash = bytes32(v);
        } else if (field == AF_VERSION) {
            auth.newRouterVersion = WidthLib.toUint32(v);
        } else if (field == AF_SNAPSHOT) {
            auth.termsSnapshotHash = bytes32(v);
        } else if (field == AF_MASK) {
            auth.widenedMask = WidthLib.toUint32(v);
        } else if (field == AF_PIN) {
            auth.accountPin = _P(v);
        } else if (field == AF_DEADLINE) {
            auth.deadline = v;
        } else if (field == AF_NONCE) {
            auth.nonce = v;
        } else {
            revert ExpectFailed();
        }
    }

    // ------------------------------------------------------------------------------------------------------------ expectations
    function _execExpect(uint256 op, uint256 a, uint256 b, uint256 c, uint256 d, uint256 e) internal {
        if (op == OP_EXPECT_STATUS) {
            MigrationModel.Mandate memory m = mgr.getMandate(_mid(a, b));
            if (m.status != c || m.reason != d || (m.retired ? 1 : 0) != e) revert ExpectFailed();
        } else if (op == OP_SNAP) {
            snaps[a] = _digest(b);
        } else if (op == OP_EXPECT_SNAP_EQ) {
            if (snaps[a] != _digest(b)) revert ExpectFailed();
        } else if (op == OP_EXPECT_INDEX_EXACT) {
            _expectIndexExact(a);
        } else {
            _execExpect2(op, a, b, c, d);
        }
    }

    function _execExpect2(uint256 op, uint256 a, uint256 b, uint256 c, uint256 d) internal view {
        if (op == OP_EXPECT_ACTIVE_GEN) {
            if (mgr.getMandate(mgr.activeMandateOf(lineageId[a])).generation != b) revert ExpectFailed();
        } else if (op == OP_EXPECT_LIVE) {
            if (mgr.live(customerAddr(a), routerAddr(b), tokenAddr(c)) != d) revert ExpectFailed();
        } else if (op == OP_EXPECT_EXPOSED) {
            if (mgr.exposedCount(customerAddr(a), routerAddr(b)) != c) revert ExpectFailed();
        } else if (op == OP_EXPECT_AUTHROUTERS) {
            uint256 mask = 0;
            for (uint256 i = 0; i < 4; ++i) {
                if (mgr.authRouter(lineageId[a], routerAddr(i), mutant)) mask |= (uint256(1) << i);
            }
            if (mask != b) revert ExpectFailed();
        } else if (op == OP_EXPECT_PINVER) {
            (,,, uint32 pv,,) = mgr.lineages(lineageId[a]);
            if (pv != b) revert ExpectFailed();
        } else if (op == OP_EXPECT_MODE) {
            address r = routerAddr(a);
            if (reg.mode(r, mutant) != b) revert ExpectFailed();
            if (reg.isBindable(r, mutant) != (c != 0)) revert ExpectFailed();
            if (reg.isChargeable(r) != (d != 0)) revert ExpectFailed();
        } else if (op == OP_EXPECT_USAGE) {
            if (mgr.usedTotal(lineageId[a], tokenAddr(b)) != c) revert ExpectFailed();
        } else {
            revert ExpectFailed();
        }
    }

    // ------------------------------------------------------------------------------------------------------------ pure checks
    function _execChecks(uint256 op, uint256 a, uint256 b, uint256 c, uint256 d, uint256 e) internal {
        if (op == OP_CHK_WF) {
            if ((PinModel.wellFormed(_P(a), mutant) ? 1 : 0) != d) revert ExpectFailed();
        } else if (op == OP_CHK_PINCHECK) {
            if (PinModel.checkField(_P(a), bytes32(b), bytes32(c), mutant) != d) revert ExpectFailed();
        } else if (op == OP_CHK_NEXTVER) {
            if (PinModel.nextVersion(WidthLib.toUint8(a), WidthLib.toUint32(b), _P(c), _P(d), mutant) != e) revert ExpectFailed();
        } else if (op == OP_CHK_AUTH) {
            PinModel.Pin memory pin = _P(b);
            address cust = customerAddr(a);
            PinModel.authSignature(cust, c != 0, WidthLib.toUint8(d), e != 0, pin, mgr.codeHashOf(cust), mgr.codeHashOf(pin.delegate), mutant);
        } else if (op == OP_CHK_AUTH_EXIT) {
            PinModel.authExit(b != 0, WidthLib.toUint8(c), d != 0, _P(a), mutant);
        } else if (op == OP_CHK_PINHASH) {
            if (PinModel.structHash(_P(a)) != bytes32(b)) revert ExpectFailed();
        } else if (op == OP_CHK_CONTAINED) {
            if (ContainModel.containedMask(_T(a), _T(b), mutant) != d) revert ExpectFailed();
        } else if (op == OP_CHK_WIDENED) {
            if (ContainModel.widenedMask(_T(a), _T(b)) != d) revert ExpectFailed();
        } else {
            revert ExpectFailed();
        }
    }

    // ------------------------------------------------------------------------------------------------------------ signer sets, widths, snapshots
    function _execMisc(uint256 op, uint256 a, uint256 b, uint256 c, uint256 d, uint256 e) internal {
        e;
        if (op == OP_SS_PROPOSE) {
            address[] memory members = new address[](3);
            uint256 n = 0;
            for (uint256 k = 1; k <= 3; ++k) {
                if ((c >> (k - 1)) & 1 == 1) {
                    members[n] = keyAddr(k);
                    n += 1;
                }
            }
            address[] memory exact = new address[](n);
            for (uint256 i = 0; i < n; ++i) {
                exact[i] = members[i];
            }
            ss.proposeSignerSet(WidthLib.toUint8(a), b, exact, mutant);
        } else if (op == OP_SS_ACTIVATE) {
            ss.activateSignerSet(WidthLib.toUint8(a), b, mutant);
        } else if (op == OP_SS_REMOVE) {
            ss.removeQuoteSigner(WidthLib.toUint8(a), keyAddr(b));
        } else if (op == OP_SS_STOP) {
            ss.stopSignerSet(WidthLib.toUint8(a), b);
        } else if (op == OP_SS_VERIFY) {
            ss.verify(keyAddr(a), b, c, mutant);
        } else if (op == OP_W_NARROW) {
            _narrow(a, b);
        } else if (op == OP_SEED_LIVE) {
            mgr.seedLive(customerAddr(a), routerAddr(b), tokenAddr(c), d);
        } else if (op == OP_W_ADD) {
            uint256 s = a + b;
            if (s < a) revert ExpectFailed();
        } else if (op == OP_W_BATCH) {
            TimeModel.batchCheck(a, mutant);
        } else if (op == OP_W_QUOTE) {
            TimeModel.quoteTimes(a, b, c, d, e, block.timestamp, mutant);
        } else {
            revert ExpectFailed();
        }
    }

    function _narrow(uint256 bits, uint256 v) internal pure {
        if (bits == 32) WidthLib.toUint32(v);
        else if (bits == 48) WidthLib.toUint48(v);
        else if (bits == 64) WidthLib.toUint64(v);
        else if (bits == 160) WidthLib.toUint160(v);
        else if (bits == 16) WidthLib.toUint16(v);
        else if (bits == 8) WidthLib.toUint8(v);
        else revert ExpectFailed();
    }

    /// A digest of everything outside the migrating lineage: every Permit2 allowance of the four customers, the router states, and every
    /// other lineage with all its mandates.
    function _digest(uint256 exclude) internal view returns (bytes32 acc) {
        for (uint256 ci = 0; ci < 4; ++ci) {
            for (uint256 t = 1; t <= 10; ++t) {
                for (uint256 r = 0; r < 4; ++r) {
                    (uint160 amount, uint48 expiration, uint48 nonce) = p2.allowance(customerAddr(ci), tokenAddr(t), routerAddr(r));
                    acc = keccak256(abi.encode(acc, amount, expiration, nonce));
                }
            }
        }
        for (uint256 r2 = 0; r2 < 4; ++r2) {
            (uint8 st, uint8 rs) = reg.snap(routerAddr(r2));
            acc = keccak256(abi.encode(acc, st, rs));
        }
        for (uint256 slot = 0; slot < 64; ++slot) {
            if ((knownMask >> slot) & 1 == 0 || slot == exclude) continue;
            bytes32 lid = lineageId[slot];
            acc = keccak256(abi.encode(acc, mgr.lineageDigest(lid)));
            uint256 count = mgr.mandateCount(lid);
            for (uint256 i = 0; i < count; ++i) {
                acc = keccak256(abi.encode(acc, mgr.mandateDigest(mgr.lineageMandateIds(lid, i))));
            }
        }
    }

    /// I-MIG-10: for customer `ci`, live(C, R, t) equals the number of recorded-active mandates (status ACTIVE, not retired) and Exposed(C, R)
    /// holds exactly the tokens with a non-zero count.
    function _expectIndexExact(uint256 ci) internal view {
        address cust = customerAddr(ci);
        for (uint256 r = 0; r < 4; ++r) {
            address router = routerAddr(r);
            uint256 exposedExpected = 0;
            for (uint256 t = 1; t <= 10; ++t) {
                address token = tokenAddr(t);
                uint256 want = _recordedActive(cust, router, token);
                if (mgr.live(cust, router, token) != want) revert ExpectFailed();
                if (want > 0) {
                    exposedExpected += 1;
                    if (!_inExposed(cust, router, token)) revert ExpectFailed(); // the SET of tokens, not only its size (like the Python oracle)
                }
            }
            if (mgr.exposedCount(cust, router) != exposedExpected) revert ExpectFailed();
        }
    }

    function _inExposed(address cust, address router, address token) internal view returns (bool) {
        uint256 n = mgr.exposedCount(cust, router);
        for (uint256 k = 0; k < n; ++k) {
            if (mgr.exposedAt(cust, router, k) == token) return true;
        }
        return false;
    }

    function _recordedActive(address cust, address router, address token) internal view returns (uint256 n) {
        for (uint256 slot = 0; slot < 64; ++slot) {
            if ((knownMask >> slot) & 1 == 0) continue;
            bytes32 lid = lineageId[slot];
            uint256 count = mgr.mandateCount(lid);
            for (uint256 i = 0; i < count; ++i) {
                bytes32 id = mgr.lineageMandateIds(lid, i);
                MigrationModel.Mandate memory m = mgr.getMandate(id);
                if (m.customer != cust || m.router != router || m.status != 0 || m.retired) continue;
                ContainModel.Terms memory t = mgr.mandateTerms(id);
                for (uint256 j = 0; j < t.nTokens; ++j) {
                    if (t.tokens[j] == token) n += 1;
                }
            }
        }
    }

    // ------------------------------------------------------------------------------------------------------------ BUILD, ACT, OBSERVE
    function _build(uint256 config, uint256 key) internal {
        uint256 reg1 = key & 0xF;
        uint256 reg2 = (key >> 4) & 0xF;
        uint256 sa = (key >> 8) & 0xF;
        uint256 sb = (key >> 12) & 0xF;
        _regRegister(0);
        _regRegister(1);
        _buildLineage(0, sa, 1, T_A_EXPIRES);
        if (config != CFG_SINGLE) _buildLineage(1, sb, config == CFG_SHARED_Y ? 2 : 1, T_B_EXPIRES);
        bool aExpired = sa == LS_EXP_R1 || sa == LS_EXP_R2;
        bool bExpired = sb == LS_EXP_R1 || sb == LS_EXP_R2;
        if (aExpired) vm.warp(T_A_EXPIRES + 1);
        else if (bExpired) vm.warp(T_B_EXPIRES + 1);
        _forceRegistry(0, reg1);
        _forceRegistry(1, reg2);
        for (uint256 i = 0; i < 4; ++i) {
            _setAllowanceValue(i / 2 + 1, i % 2, (key >> (16 + 4 * i)) & 0xF);
        }
    }

    function _buildLineage(uint256 slot, uint256 st, uint256 nTokens, uint256 expires) internal {
        ContainModel.Terms memory t = _baseTerms(nTokens);
        t.expiresAt = WidthLib.toUint64(expires);
        PinModel.Pin memory pin = _pinPreset(PP_EOA);
        address router = (st == LS_LIVE_R2 || st == LS_EXP_R2) ? routerAddr(1) : routerAddr(0);
        (bytes32 lid, bytes32 mid) = mgr.activate(customerAddr(0), slot, router, t, pin, mutant);
        lineageId[slot] = lid;
        knownMask |= (uint256(1) << slot);
        if (st == LS_DONE) mgr.revoke(mid, true, mutant);
    }

    function _forceRegistry(uint256 slot, uint256 code) internal {
        uint8 state = 2; // ACTIVE
        uint8 reason = 0;
        if (code == RG_DEPR_STD) state = 3;
        else if (code == RG_DEPR_SEC) {
            state = 3;
            reason = 1;
        } else if (code == RG_DISABLED) state = 4;
        else if (code == RG_SUNSET) state = 5;
        reg.forceState(routerAddr(slot), state, reason, block.timestamp - 1);
    }

    function _setAllowanceValue(uint256 token, uint256 router, uint256 v) internal {
        address cust = customerAddr(0);
        if (v == AV_BOUNDED) {
            p2.approveAs(cust, tokenAddr(token), routerAddr(router), BOUNDED_AMOUNT, FAR);
        } else if (v == AV_UNLIM) {
            p2.approveAs(cust, tokenAddr(token), routerAddr(router), type(uint160).max, FAR);
        } else if (v == AV_EXPIRED) {
            p2.approveAs(cust, tokenAddr(token), routerAddr(router), BOUNDED_AMOUNT, block.timestamp - 1);
        }
    }

    function _act(uint256 config, uint256 action) internal {
        config;
        address cust = customerAddr(0);
        if (action <= ACT_EXPIRE_ALLOW_LAST) {
            uint256 grp = action / 4;
            uint256 idx = action % 4;
            address token = tokenAddr(idx / 2 + 1);
            address router = routerAddr(idx % 2);
            if (grp == 0) p2.approveAs(cust, token, router, BOUNDED_AMOUNT, FAR);
            else if (grp == 1) p2.approveAs(cust, token, router, type(uint160).max, FAR);
            else if (grp == 2) p2.lockdownAs(cust, token, router);
            else {
                (uint160 amount,,) = p2.allowance(cust, token, router);
                p2.approveAs(cust, token, router, amount, block.timestamp - 1);
            }
        } else if (action <= 20) {
            _actRegistry(action);
        } else if (action <= 22) {
            uint256 until = (action == 21 ? T_B_EXPIRES : T_A_EXPIRES) + 1;
            if (block.timestamp < until) vm.warp(until);
        } else if (action <= 39) {
            uint256 base = action >= 32 ? 32 : 24;
            uint256 i = action - base;
            bytes32 mid = mgr.activeMandateOf(lineageId[i / 4]);
            mgr.consume(
                routerAddr((i / 2) % 2),
                mid,
                tokenAddr(i % 2 + 1),
                action >= 32 ? BOUNDED_AMOUNT : CHARGE_SMALL,
                1,
                mgr.mandatePin(mid),
                mutant
            );
        } else if (action <= 43) {
            _actSuccessor((action - 40) / 2, (action - 40) % 2);
        } else if (action <= 45) {
            mgr.revoke(mgr.activeMandateOf(lineageId[action - 44]), true, mutant);
        } else {
            mgr.retire(mgr.activeMandateOf(lineageId[action - 46]), mutant);
        }
    }

    function _actRegistry(uint256 action) internal {
        if (action == 16) reg.deprecate(routerAddr(0), routerAddr(1), 0, 0, mutant);
        else if (action == 17) reg.deprecate(routerAddr(0), routerAddr(1), 1, 0, mutant);
        else if (action == 18) reg.emergencyDisable(routerAddr(0));
        else if (action == 19) reg.emergencyDisable(routerAddr(1));
        else {
            if (reg.stateOf(routerAddr(0)) != 3) revert WrongRouterState();
            reg.markSunset(routerAddr(0));
        }
    }

    function _actSuccessor(uint256 slot, uint256 kind) internal {
        bytes32 pid = mgr.activeMandateOf(lineageId[slot]);
        MigrationModel.Mandate memory p = mgr.getMandate(pid);
        ContainModel.Terms memory pt = mgr.mandateTerms(pid);
        PinModel.Pin memory pp = mgr.mandatePin(pid);
        address newRouter = p.router == routerAddr(0) ? routerAddr(1) : routerAddr(0);
        MigrationModel.Auth memory au = mgr.buildAuth(pid, uint8(kind), newRouter, pt, pp, block.timestamp + 3600, 1);
        mgr.activateSuccessor(pid, uint8(kind), newRouter, pt, pp, au, MigrationModel.Access(true, 0, false), mutant);
    }

    function _regCode(address router) internal view returns (uint256) {
        (uint8 st, uint8 rs) = reg.snap(router);
        if (st == 2) return RG_ACTIVE;
        if (st == 3) return rs == 1 ? RG_DEPR_SEC : RG_DEPR_STD;
        if (st == 4) return RG_DISABLED;
        if (st == 5) return RG_SUNSET;
        return RG_OTHER;
    }

    function _lineageNibble(uint256 slot) internal view returns (uint256) {
        if ((knownMask >> slot) & 1 == 0) return LS_DONE;
        bytes32 lid = lineageId[slot];
        bytes32 mid = mgr.activeMandateOf(lid);
        MigrationModel.Mandate memory m = mgr.getMandate(mid);
        (,,,, bool terminated,) = mgr.lineages(lid);
        if (m.status != 0 || m.retired || terminated) return LS_DONE;
        bool onR2 = m.router == routerAddr(1);
        bool expired = block.timestamp >= mgr.mandateTerms(mid).expiresAt;
        if (expired) return onR2 ? LS_EXP_R2 : LS_EXP_R1;
        return onR2 ? LS_LIVE_R2 : LS_LIVE_R1;
    }

    function _avCode(uint256 amount, uint256 expiration) internal view returns (uint256) {
        if (amount == 0) return AV_NONE;
        if (block.timestamp > expiration) return AV_EXPIRED;
        if (amount == type(uint160).max) return AV_UNLIM;
        return AV_BOUNDED;
    }

    /// The state key (see tools/scenario_vm.World.observe): nibbles 0..7 identify the state, 8..11 are the exposure counts, 12 the
    /// AuthRouters bits of A and B, 13 whether A and B can charge one unit of t1 on R1 and on R2.
    function _observe(uint256 config) internal view returns (uint256 key) {
        config;
        address cust = customerAddr(0);
        key = _regCode(routerAddr(0)) | (_regCode(routerAddr(1)) << 4) | (_lineageNibble(0) << 8) | (_lineageNibble(1) << 12);
        for (uint256 i = 0; i < 4; ++i) {
            address token = tokenAddr(i / 2 + 1);
            address router = routerAddr(i % 2);
            (uint160 amount, uint48 expiration,) = p2.allowance(cust, token, router);
            key |= _avCode(amount, expiration) << (16 + 4 * i);
            key |= uint256(mgr.live(cust, router, token)) << (32 + 4 * i);
        }
        uint256 authBits = 0;
        uint256 can = 0;
        for (uint256 slot = 0; slot < 2; ++slot) {
            if ((knownMask >> slot) & 1 == 0) continue;
            bytes32 lid = lineageId[slot];
            uint256 got = 0;
            if (mgr.authRouter(lid, routerAddr(0), mutant)) got |= 1;
            if (mgr.authRouter(lid, routerAddr(1), mutant)) got |= 2;
            authBits |= got << (2 * slot);
            bytes32 mid = mgr.activeMandateOf(lid);
            for (uint256 r = 0; r < 2; ++r) {
                if (mgr.wouldConsume(routerAddr(r), mid, tokenAddr(1), CHARGE_SMALL, PROBE_CYCLE, mutant)) can |= (uint256(1) << (2 * slot + r));
            }
        }
        key |= authBits << 48;
        key |= can << 52;
    }
}
