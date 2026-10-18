// SPDX-License-Identifier: Apache-2.0
pragma solidity 0.8.24;

import {FastPayTypes as T} from "../generated/FastPayTypes.sol";
import {PinLib} from "./PinLib.sol";
import "../Errors.sol";

/// SignatureVerifier of document 06 section 4 and AUTH of document 17 section 5.4: ECDSA with a low s, ERC-1271 by STATICCALL with no
/// artificial gas cap, and the rule that decides which of the two a customer's signature may use. No function reads `tx.origin`.
library AuthLib {
    /// secp256k1 order / 2: a larger s is the malleable twin of a smaller one (EIP-2).
    uint256 internal constant HALF_N = 0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A0;
    bytes4 internal constant ERC1271_MAGIC = 0x1626ba7e;

    /// The signer of a 65-byte `r || s || v` signature; address(0) if it is malformed (length, v outside 27 and 28, high s) or does not recover.
    function recover(bytes32 digest, bytes calldata sig) internal pure returns (address) {
        if (sig.length != 65) return address(0);
        bytes32 r = bytes32(sig[0:32]);
        bytes32 s = bytes32(sig[32:64]);
        uint8 v = uint8(sig[64]);
        if (uint256(s) > HALF_N || (v != 27 && v != 28)) return address(0);
        return ecrecover(digest, v, r, s);
    }

    /// ERC-1271 `isValidSignature(digest, sig)` of `account` through STATICCALL; only the first return word is read (a hostile account cannot
    /// force a large copy). An account without code never validates here.
    function valid1271(address account, bytes32 digest, bytes calldata sig) internal view returns (bool ok) {
        if (account.code.length == 0) return false;
        bytes memory data = abi.encodeWithSelector(ERC1271_MAGIC, digest, sig);
        bytes32 word;
        assembly ("memory-safe") {
            ok := staticcall(gas(), account, add(data, 32), mload(data), 0, 32)
            if lt(returndatasize(), 32) { ok := 0 }
            word := mload(0)
        }
        return ok && bytes4(word) == ERC1271_MAGIC;
    }

    /// AUTH(C, digest, pinCtx) for a signature that creates or widens authority (activation, successor, pin update, reduce, resume):
    /// `pinCtx` is the pin ALREADY STORED for the lineage (for a new lineage, the pin in the message). DIRECT_ONLY accepts no signature;
    /// ECDSA_KEY accepts the account key's ECDSA signature; ERC1271 accepts `isValidSignature` only while the account still satisfies the pin.
    function authAuthority(address customer, bytes32 digest, bytes calldata sig, T.AccountPin memory pinCtx) internal view {
        uint8 mode = pinCtx.signatureMode;
        if (mode == PinLib.SM_ECDSA_KEY) {
            if (recover(digest, sig) != customer) revert NotCustomer();
        } else if (mode == PinLib.SM_ERC1271) {
            uint8 field = PinLib.liveCheck(customer, pinCtx);
            if (field != 0) revert AccountCodeChanged(customer, field);
            if (!valid1271(customer, digest, sig)) revert NotCustomer();
        } else {
            revert SignatureModeNotPermitted();
        }
    }

    /// revokeBySig and pauseBySig: accepted through either path whatever the pin says (exits are never gated, consequence 4 of section 5.4):
    /// a signature that only forges can only stop charges.
    function authExit(address customer, bytes32 digest, bytes calldata sig) internal view {
        if (recover(digest, sig) == customer) return;
        if (!valid1271(customer, digest, sig)) revert NotCustomer();
    }
}
