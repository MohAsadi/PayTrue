// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.24;

import {FastPayTypes as T} from "../generated/FastPayTypes.sol";

/// The account pin of document 17 section 5: PIN_WELLFORMED, PIN_OK (with the failing field) and nextPinVersion for a successor.
/// A port of the reference model's PinModel without its mutation switches. All functions are pure.
library PinLib {
    bytes32 internal constant KECCAK_EMPTY = keccak256("");

    uint8 internal constant SM_DIRECT_ONLY = 0;
    uint8 internal constant SM_ECDSA_KEY = 1;
    uint8 internal constant SM_ERC1271 = 2;
    uint8 internal constant FIELD_ACCOUNT_CODE = 1;
    uint8 internal constant FIELD_DELEGATE_CODE = 2;

    /// The account code of an EIP-7702 delegated account: 0xef0100 || delegate (23 bytes); EXTCODEHASH of the account is its hash.
    function designatorHash(address delegate) internal pure returns (bytes32) {
        return keccak256(abi.encodePacked(hex"ef0100", delegate));
    }

    /// PIN_WELLFORMED(pin), document 17 section 5.2, as written (no bound on signatureMode for mode 2; AuthLib refuses a mode above 2).
    function wellFormed(T.AccountPin memory p) internal pure returns (bool) {
        if (p.pinVersion < 1 || p.accountMode < 1 || p.accountMode > 4) return false;
        if (p.accountMode == 1) {
            return p.accountCodeHash == T.PIN_EOA && p.delegate == address(0) && p.delegateCodeHash == bytes32(0)
                && p.implementationFamily == bytes32(0) && p.signatureMode <= 1;
        }
        if (p.accountMode == 2) {
            return p.delegate != address(0) && p.accountCodeHash == designatorHash(p.delegate)
                && p.delegateCodeHash != bytes32(0) && p.delegateCodeHash != KECCAK_EMPTY && p.implementationFamily != bytes32(0);
        }
        return p.delegate == address(0) && p.delegateCodeHash == bytes32(0) && p.accountCodeHash != bytes32(0)
            && p.accountCodeHash != KECCAK_EMPTY && p.accountCodeHash != T.PIN_EOA && p.implementationFamily != bytes32(0)
            && (p.signatureMode == 0 || p.signatureMode == 2);
    }

    /// PIN_OK(account, pin) with the first failing field: 0 = holds, 1 = ACCOUNT_CODE, 2 = DELEGATE_CODE.
    /// h = EXTCODEHASH(account), hd = EXTCODEHASH(pin.delegate).
    function checkField(T.AccountPin memory p, bytes32 h, bytes32 hd) internal pure returns (uint8) {
        if (p.accountMode == 1) return (h == bytes32(0) || h == KECCAK_EMPTY) ? 0 : FIELD_ACCOUNT_CODE;
        if (p.accountMode == 2) {
            if (h != p.accountCodeHash) return FIELD_ACCOUNT_CODE;
            if (hd != p.delegateCodeHash) return FIELD_DELEGATE_CODE;
            return 0;
        }
        if (p.accountMode == 3 || p.accountMode == 4) return h == p.accountCodeHash ? 0 : FIELD_ACCOUNT_CODE;
        return 0;
    }

    /// The live code hashes against which a pin is checked: the account's, and for a 7702 account the delegate's.
    function liveCheck(address account, T.AccountPin memory p) internal view returns (uint8) {
        bytes32 hd = p.accountMode == 2 ? p.delegate.codehash : bytes32(0);
        return checkField(p, account.codehash, hd);
    }

    function samePinExceptVersion(T.AccountPin memory a, T.AccountPin memory b) internal pure returns (bool) {
        return a.accountMode == b.accountMode && a.accountCodeHash == b.accountCodeHash && a.delegate == b.delegate
            && a.delegateCodeHash == b.delegateCodeHash && a.implementationFamily == b.implementationFamily && a.signatureMode == b.signatureMode;
    }

    /// nextPinVersion for a successor: the predecessor's version, plus one if the pin differs in a field other than the version.
    function nextVersionSuccessor(T.AccountPin memory prev, T.AccountPin memory p) internal pure returns (uint32) {
        return samePinExceptVersion(prev, p) ? prev.pinVersion : prev.pinVersion + 1;
    }
}
