// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.24;

import "./Errors.sol";
import "./Mutants.sol";

/// The account pin of document 17 section 5: the typed struct, PIN_WELLFORMED, PIN_OK, nextPinVersion and AUTH.
/// Mirrors the pin functions of tools/protocol_model.py. All functions are pure; `mutant` != 0 applies one named mutation.
library PinModel {
    bytes32 internal constant KECCAK_EMPTY = keccak256("");
    bytes32 internal constant PIN_EOA = keccak256("fastpay.pin.eoa.v1");
    bytes32 internal constant ACCOUNT_PIN_TYPEHASH = keccak256(
        "AccountPin(uint8 accountMode,bytes32 accountCodeHash,address delegate,bytes32 delegateCodeHash,bytes32 implementationFamily,uint32 pinVersion,uint8 signatureMode)"
    );

    uint8 internal constant SM_DIRECT_ONLY = 0;
    uint8 internal constant SM_ECDSA_KEY = 1;
    uint8 internal constant SM_ERC1271 = 2;
    uint8 internal constant SIG_NONE = 0;
    uint8 internal constant SIG_ECDSA = 1;
    uint8 internal constant SIG_ERC1271 = 2;
    uint8 internal constant FIELD_ACCOUNT_CODE = 1;
    uint8 internal constant FIELD_DELEGATE_CODE = 2;
    uint8 internal constant NV_FIRST = 0;
    uint8 internal constant NV_UPDATE = 1;
    uint8 internal constant NV_SUCCESSOR = 2;

    struct Pin {
        uint8 accountMode;
        bytes32 accountCodeHash;
        address delegate;
        bytes32 delegateCodeHash;
        bytes32 implementationFamily;
        uint32 pinVersion;
        uint8 signatureMode;
    }

    function structHash(Pin memory p) internal pure returns (bytes32) {
        return keccak256(
            abi.encode(
                ACCOUNT_PIN_TYPEHASH,
                p.accountMode,
                p.accountCodeHash,
                p.delegate,
                p.delegateCodeHash,
                p.implementationFamily,
                p.pinVersion,
                p.signatureMode
            )
        );
    }

    /// The account code of an EIP-7702 delegated account: 0xef0100 || delegate (23 bytes).
    function designatorCode(address delegate) internal pure returns (bytes memory) {
        return abi.encodePacked(hex"ef0100", delegate);
    }

    function designatorHash(address delegate) internal pure returns (bytes32) {
        return keccak256(designatorCode(delegate));
    }

    // ---- PIN_WELLFORMED, document 17 section 5.2, as written (no bound on signatureMode for mode 2)
    function wellFormed(Pin memory p, uint256 mutant) internal pure returns (bool) {
        if (mutant != M_PW_VER0 && p.pinVersion < 1) return false;
        if (mutant != M_PW_MODE_RANGE && (p.accountMode < 1 || p.accountMode > 4)) return false;
        if (p.accountMode == 1) return _wellFormedMode1(p, mutant);
        if (p.accountMode == 2) return _wellFormedMode2(p, mutant);
        if (p.accountMode == 3 || p.accountMode == 4) return _wellFormedMode34(p, mutant);
        return true;
    }

    function _wellFormedMode1(Pin memory p, uint256 mutant) private pure returns (bool) {
        if (mutant != M_PW_M1_CODE && p.accountCodeHash != PIN_EOA) return false;
        if (mutant != M_PW_M1_DELEGATE && (p.delegate != address(0) || p.delegateCodeHash != bytes32(0))) return false;
        if (mutant != M_PW_M1_FAMILY && p.implementationFamily != bytes32(0)) return false;
        if (mutant != M_PW_M1_SIG && p.signatureMode > 1) return false;
        return true;
    }

    function _wellFormedMode2(Pin memory p, uint256 mutant) private pure returns (bool) {
        if (mutant != M_PW_M2_DELEGATE0 && p.delegate == address(0)) return false;
        if (mutant != M_PW_M2_CODE && p.accountCodeHash != designatorHash(p.delegate)) return false;
        if (mutant != M_PW_M2_DCODE && (p.delegateCodeHash == bytes32(0) || p.delegateCodeHash == KECCAK_EMPTY)) return false;
        if (mutant != M_PW_M2_FAMILY && p.implementationFamily == bytes32(0)) return false;
        return true;
    }

    function _wellFormedMode34(Pin memory p, uint256 mutant) private pure returns (bool) {
        if (mutant != M_PW_M34_DELEGATE && (p.delegate != address(0) || p.delegateCodeHash != bytes32(0))) return false;
        if (
            mutant != M_PW_M34_CODE
                && (p.accountCodeHash == bytes32(0) || p.accountCodeHash == KECCAK_EMPTY || p.accountCodeHash == PIN_EOA)
        ) return false;
        if (mutant != M_PW_M34_FAMILY && p.implementationFamily == bytes32(0)) return false;
        if (mutant != M_PW_M34_SIG && p.signatureMode != 0 && p.signatureMode != 2) return false;
        return true;
    }

    // ---- PIN_OK with the first failing field: 0 = holds, 1 = ACCOUNT_CODE, 2 = DELEGATE_CODE
    /// h = EXTCODEHASH(account), hd = EXTCODEHASH(pin.delegate).
    function checkField(Pin memory p, bytes32 h, bytes32 hd, uint256 mutant) internal pure returns (uint8) {
        if (p.accountMode == 1) {
            bool ok;
            if (mutant == M_PO_M1_EMPTY_ONLY) ok = h == bytes32(0);
            else if (mutant == M_PO_M1_KE_ONLY) ok = h == KECCAK_EMPTY;
            else ok = h == bytes32(0) || h == KECCAK_EMPTY;
            return ok ? 0 : FIELD_ACCOUNT_CODE;
        }
        if (p.accountMode == 2) {
            if (mutant != M_PO_M2_NO_ACCOUNT && h != p.accountCodeHash) return FIELD_ACCOUNT_CODE;
            if (mutant != M_PO_M2_NO_DELEGATE && hd != p.delegateCodeHash) return FIELD_DELEGATE_CODE;
            return 0;
        }
        if (p.accountMode == 3 || p.accountMode == 4) {
            if (mutant != M_PO_M34_SKIP && h != p.accountCodeHash) return FIELD_ACCOUNT_CODE;
            return 0;
        }
        return 0;
    }

    function pinOk(Pin memory p, bytes32 h, bytes32 hd, uint256 mutant) internal pure returns (bool) {
        return checkField(p, h, hd, mutant) == 0;
    }

    function samePinExceptVersion(Pin memory a, Pin memory b) internal pure returns (bool) {
        return a.accountMode == b.accountMode && a.accountCodeHash == b.accountCodeHash && a.delegate == b.delegate
            && a.delegateCodeHash == b.delegateCodeHash && a.implementationFamily == b.implementationFamily
            && a.signatureMode == b.signatureMode;
    }

    /// nextPinVersion(L, pin): 1 for the first activation; L.pinVersion + 1 for updateAccountPin; P.pinVersion + [the pin differs from
    /// P.pin in a field other than pinVersion] for a successor. uint32 arithmetic is checked: Panic(0x11) at 2^32 - 1 + 1.
    function nextVersion(uint8 kind, uint32 lineageVersion, Pin memory prev, Pin memory p, uint256 mutant)
        internal
        pure
        returns (uint32)
    {
        if (kind == NV_FIRST) return 1;
        if (kind == NV_UPDATE) {
            if (mutant == M_NV_UPDATE_SAME) return lineageVersion;
            return lineageVersion + 1;
        }
        bool differs = !samePinExceptVersion(prev, p);
        if (mutant == M_NV_SUCC_ALWAYS) differs = true;
        if (mutant == M_NV_SUCC_NEVER) differs = false;
        return differs ? prev.pinVersion + 1 : prev.pinVersion;
    }

    // ---- AUTH(C, digest, pinCtx), document 17 section 5.4
    /// Reverts NotCustomer, SignatureModeNotPermitted or AccountCodeChanged. `h` and `hd` are the live account and delegate code hashes.
    function authSignature(
        address customer,
        bool senderIsCustomer,
        uint8 sigPath,
        bool sigOk,
        Pin memory pinCtx,
        bytes32 h,
        bytes32 hd,
        uint256 mutant
    ) internal pure {
        if (senderIsCustomer) return;
        if (sigPath == SIG_NONE) revert NotCustomer();
        uint8 mode = pinCtx.signatureMode;
        if (sigPath == SIG_ECDSA) {
            bool allowed = mode == SM_ECDSA_KEY || (mutant == M_AUTH_ECDSA_ANY && mode == SM_ERC1271)
                || (mutant == M_AUTH_DIRECT_ONLY_OK && mode == SM_DIRECT_ONLY);
            if (!allowed) revert SignatureModeNotPermitted();
            if (!sigOk && mutant != M_AUTH_SIGOK_SKIP) revert NotCustomer();
            return;
        }
        bool allowed1271 = mode == SM_ERC1271 || (mutant == M_AUTH_1271_ANY && mode == SM_ECDSA_KEY)
            || (mutant == M_AUTH_DIRECT_ONLY_OK && mode == SM_DIRECT_ONLY);
        if (!allowed1271) revert SignatureModeNotPermitted();
        if (mutant != M_AUTH_1271_NOPIN) {
            uint8 field = checkField(pinCtx, h, hd, mutant);
            if (field != 0) revert AccountCodeChanged(customer, field);
        }
        if (!sigOk && mutant != M_AUTH_SIGOK_SKIP) revert NotCustomer();
    }

    /// revokeBySig and pauseBySig: accepted through either path whatever the mode (consequence 4 of section 5.4).
    function authExit(bool senderIsCustomer, uint8 sigPath, bool sigOk, Pin memory pinCtx, uint256 mutant) internal pure {
        if (senderIsCustomer) return;
        if (sigPath == SIG_NONE) revert NotCustomer();
        if (mutant == M_AUTH_EXIT_GATED && pinCtx.signatureMode == SM_DIRECT_ONLY) revert SignatureModeNotPermitted();
        if (!sigOk) revert NotCustomer();
    }
}
