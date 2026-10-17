#!/usr/bin/env python3
"""Minimal secp256k1 for the evidence tools: address derivation, ECDSA recovery and (for tests only) deterministic signing.

Pure Python, no dependencies, not constant time: it is for verifying signatures that people made in wallets and for producing test
vectors. It must never be given a real private key. The recovery is checked against `ecrecover` of the EVM in
foundry/test/generated/EIP712Golden.t.sol (the golden signatures are produced here and recovered there).
"""
import hashlib
import hmac
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import eip712_vectors as V  # noqa: E402

P = 2 ** 256 - 2 ** 32 - 977
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
G = (0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
     0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)


def _add(a, b):
    if a is None:
        return b
    if b is None:
        return a
    if a[0] == b[0] and (a[1] + b[1]) % P == 0:
        return None
    if a == b:
        lam = 3 * a[0] * a[0] * pow(2 * a[1], -1, P) % P
    else:
        lam = (b[1] - a[1]) * pow(b[0] - a[0], -1, P) % P
    x = (lam * lam - a[0] - b[0]) % P
    return x, (lam * (a[0] - x) - a[1]) % P


def _mul(k, pt):
    r = None
    while k:
        if k & 1:
            r = _add(r, pt)
        pt = _add(pt, pt)
        k >>= 1
    return r


def public_key(priv: int):
    assert 0 < priv < N
    return _mul(priv, G)


def address_of(pub) -> str:
    return "0x" + V.keccak256(pub[0].to_bytes(32, "big") + pub[1].to_bytes(32, "big"))[12:].hex()


def sign(msg_hash: bytes, priv: int):
    """Deterministic ECDSA (RFC 6979 with HMAC-SHA256) with a low s; returns (v, r, s) with v in {27, 28}."""
    z = int.from_bytes(msg_hash, "big")
    x = priv.to_bytes(32, "big")
    k_, v_ = b"\x00" * 32, b"\x01" * 32
    k_ = hmac.new(k_, v_ + b"\x00" + x + msg_hash, hashlib.sha256).digest()
    v_ = hmac.new(k_, v_, hashlib.sha256).digest()
    k_ = hmac.new(k_, v_ + b"\x01" + x + msg_hash, hashlib.sha256).digest()
    v_ = hmac.new(k_, v_, hashlib.sha256).digest()
    while True:
        v_ = hmac.new(k_, v_, hashlib.sha256).digest()
        k = int.from_bytes(v_, "big")
        if 1 <= k < N:
            pt = _mul(k, G)
            r = pt[0] % N
            s = pow(k, -1, N) * (z + r * priv) % N
            if r and s:
                rec = pt[1] & 1
                if s > N // 2:
                    s = N - s
                    rec ^= 1
                return 27 + rec, r, s
        k_ = hmac.new(k_, v_ + b"\x00", hashlib.sha256).digest()
        v_ = hmac.new(k_, v_, hashlib.sha256).digest()


def recover(msg_hash: bytes, v: int, r: int, s: int):
    """The address that signed `msg_hash`, or None. Accepts v in {0, 1, 27, 28}; refuses a high s (EIP-2) and zero r or s."""
    if v in (27, 28):
        v -= 27
    if v not in (0, 1) or not (0 < r < N) or not (0 < s <= N // 2):
        return None
    x = r
    y2 = (pow(x, 3, P) + 7) % P
    y = pow(y2, (P + 1) // 4, P)
    if y * y % P != y2:
        return None
    if (y & 1) != v:
        y = P - y
    z = int.from_bytes(msg_hash, "big")
    rinv = pow(r, -1, N)
    q = _add(_mul(s * rinv % N, (x, y)), _mul((-z * rinv) % N, G))
    return None if q is None else address_of(q)


def recover_signature(msg_hash: bytes, sig_hex: str):
    sig = bytes.fromhex(sig_hex[2:] if sig_hex.startswith("0x") else sig_hex)
    if len(sig) != 65:
        return None
    return recover(msg_hash, sig[64], int.from_bytes(sig[:32], "big"), int.from_bytes(sig[32:64], "big"))


def personal_hash(message: bytes) -> bytes:
    """EIP-191 version 0x45 (personal_sign): keccak256("\\x19Ethereum Signed Message:\\n" + len + message)."""
    return V.keccak256(b"\x19Ethereum Signed Message:\n" + str(len(message)).encode() + message)


def self_check():
    # private key 1 is the generator: the address every EVM tool knows
    assert address_of(public_key(1)) == "0x7e5f4552091a69125d5dfcb7b8c2659029395bdf"
    for priv in (1, 2, 0xC0FFEE, N - 1):
        h = V.keccak256(b"fastpay-test-" + priv.to_bytes(32, "big"))
        v, r, s = sign(h, priv)
        assert recover(h, v, r, s) == address_of(public_key(priv))
        assert recover(V.keccak256(h), v, r, s) != address_of(public_key(priv))        # another message: another signer
        assert recover(h, 55 - v, r, s) != address_of(public_key(priv))                 # the other recovery id
        assert recover(h, v, r, N - s) is None                                           # a high s is refused
    return True


if __name__ == "__main__":
    print("secp256k1 self-check:", "ok" if self_check() else "FAILED")
