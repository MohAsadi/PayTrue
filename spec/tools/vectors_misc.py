#!/usr/bin/env python3
"""Executable scenarios for the account pin (ACP-TV, document 17), the quote signer sets (CAP-TV, document 11), the registry
boundaries (document 12 section 3), and the timestamp and integer-width boundary vectors (revision 0.5).

Same conventions as tools/vectors_mig.py. Pin registers: 0 plain EOA, 1 ERC-7702 delegate D1, 2 ERC-4337 account, 3 wallet 1271 (mode 4),
4 and up scratch. Roles: 0 governance, 1 guardian. Signer keys 1..3.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import protocol_model as M  # noqa: E402
import scenario_vm as S  # noqa: E402
import eip712_vectors as V  # noqa: E402
from scenario_vm import T0, FAR  # noqa: E402
from vectors_mig import Scenario, MAXU160, N, E, TF, AF, PF, PP  # noqa: E402

GOV, GUARD = M.ROLE_GOVERNANCE, M.ROLE_GUARDIAN
SIGN, SIGE, SIG1 = M.SIG_NONE, M.SIG_ECDSA, M.SIG_ERC1271
P7702 = M.example_pin("pin7702")
P4337 = M.example_pin("pin4337")
P1271 = M.pin_1271()
H1 = M.designator_hash_int(0xABABABABABABABABABABABABABABABABABABABAB)
D1 = P7702.delegate
KE = M.KECCAK_EMPTY
GRACE = M.QUOTE_SET_GRACE


def pins(sc: Scenario):
    """Load the four standard pins into registers 0..3."""
    for slot, preset in enumerate(("PP_EOA", "PP_7702", "PP_4337", "PP_1271")):
        sc.op("PIN_PRESET", slot, PP[preset])
    return sc


def account_7702(sc: Scenario):
    return sc.op("ACCT_SET", 0, P7702.accountCodeHash).op("DELEG_SET", D1, P7702.delegateCodeHash)


def build_acp():
    out = []

    def new(vid, source, title, note=""):
        sc = Scenario(vid, source, title, note)
        out.append(sc)
        return sc

    # ---- ACP-TV-13..17: PIN_OK on the live account hashes
    s = pins(new("ACP_TV_13_17", "ACP-TV-13", "PIN_OK truth table: EOA sentinel, designator, redeployed delegate (also ACP-TV-14, 15, 16, 17)"))
    H2 = M.designator_hash_int(0xCDCDCDCDCDCDCDCDCDCDCDCDCDCDCDCDCDCDCDCD)
    dch = P7702.delegateCodeHash
    s.op("CHK_PINCHECK", 0, H1, 0, M.FIELD_ACCOUNT_CODE)                 # ACP-TV-13: pin PIN_EOA, h = H1
    s.op("CHK_PINCHECK", 1, H2, dch, M.FIELD_ACCOUNT_CODE)               # ACP-TV-14: pin H1, h = H2
    s.op("CHK_PINCHECK", 1, H1, dch, 0)                                  # ACP-TV-15
    s.op("CHK_PINCHECK", 1, 0, dch, M.FIELD_ACCOUNT_CODE)                # ACP-TV-16: delegation cleared, empty account
    s.op("CHK_PINCHECK", 0, 0, 0, 0).op("CHK_PINCHECK", 0, KE, 0, 0)     # ACP-TV-17: both encodings of "no code"
    s.op("CHK_PINCHECK", 0, V.keccak256(b"proxy-bytecode") and M.h2i(V.keccak256(b"proxy-bytecode")), 0, M.FIELD_ACCOUNT_CODE)
    s.op("CHK_PINCHECK", 1, H1, 0, M.FIELD_DELEGATE_CODE)                # delegate without code (ACP-TV-32)
    s.op("CHK_PINCHECK", 1, H1, dch ^ 1, M.FIELD_DELEGATE_CODE)          # redeployed delegate (ACP-TV-31)
    s.op("CHK_PINCHECK", 1, H2, 0, M.FIELD_ACCOUNT_CODE)                 # the account is checked before the delegate
    s.op("CHK_PINCHECK", 2, P4337.accountCodeHash, 0, 0)                 # ACP-TV-33: mode 3, h equal
    s.op("CHK_PINCHECK", 2, P4337.accountCodeHash ^ 1, 0, M.FIELD_ACCOUNT_CODE)
    s.op("CHK_PINCHECK", 3, P1271.accountCodeHash, 99, 0)                # mode 4 ignores hd
    s.op("CHK_PINCHECK", 3, 0, 0, M.FIELD_ACCOUNT_CODE)
    s.op("CHK_PINCHECK", 2, KE, 0, M.FIELD_ACCOUNT_CODE)

    # ---- ACP-TV-13 as a charge: the contract refuses the charge when the account changed
    s = new("ACP_TV_13_CHARGE", "ACP-TV-13", "A charge reverts AccountCodeChanged when the account gained a delegation after activation")
    s.routers().lineage(0).grant(1, 0)
    s.charge(0, 0, 1, 10, 1)
    s.op("ACCT_SET", 0, H1)
    s.charge(0, 0, 1, 10, 2, expect=("AccountCodeChanged", M.FIELD_ACCOUNT_CODE))
    s.op("ACCT_SET", 0, KE)                                              # an existing account without code satisfies the sentinel
    s.charge(0, 0, 1, 10, 2)
    s.op("ACCT_SET", 0, 0)
    s.charge(0, 0, 1, 10, 3)

    # ---- ACP-TV-25..30: PIN_WELLFORMED
    s = pins(new("ACP_TV_25", "ACP-TV-25", "Well-formed pins: plain EOA, 7702 with D1, 4337; their hashStruct values"))
    for slot, key in ((0, "pinHashEoa"), (1, "pinHash7702"), (2, "pinHash4337")):
        s.op("CHK_WF", slot, 0, 0, 1)
        s.op("CHK_PINHASH", slot, M.h2i(bytes.fromhex(V.pin_vectors()[key][2:])))
    s.op("CHK_WF", 3, 0, 0, 1)

    s = pins(new("ACP_TV_26", "ACP-TV-26", "Mode 1 with a delegate, a family, a delegate code hash, or signatureMode 2 is malformed"))
    for field, value in (("PF_DELEGATE", 1), ("PF_FAMILY", 1), ("PF_DCODE", 1), ("PF_SIG", 2), ("PF_CODE", KE)):
        s.op("PIN_PRESET", 4, PP["PP_EOA"]).op("PIN_SET", 4, PF[field], value).op("CHK_WF", 4, 0, 0, 0)
    s.op("PIN_PRESET", 4, PP["PP_EOA"]).op("PIN_SET", 4, PF["PF_SIG"], 0).op("CHK_WF", 4, 0, 0, 1)       # DIRECT_ONLY is allowed

    s = pins(new("ACP_TV_27_28", "ACP-TV-27, 28", "Mode 2: the account code hash is keccak256(0xef0100 || delegate); delegate, delegate code hash and family are set"))
    s.op("PIN_PRESET", 4, PP["PP_7702"]).op("PIN_SET", 4, PF["PF_CODE"], P7702.accountCodeHash ^ 1).op("CHK_WF", 4, 0, 0, 0)        # 27
    for field, value in (("PF_DCODE", 0), ("PF_DCODE", KE), ("PF_DELEGATE", 0), ("PF_FAMILY", 0)):                                  # 28
        s.op("PIN_PRESET", 4, PP["PP_7702"]).op("PIN_SET", 4, PF[field], value).op("CHK_WF", 4, 0, 0, 0)
    s.op("PIN_PRESET", 4, PP["PP_7702"]).op("PIN_SET", 4, PF["PF_DELEGATE"], 0).op("PIN_SET", 4, PF["PF_CODE"], M.designator_hash_int(0))
    s.op("CHK_WF", 4, 0, 0, 0)                                                       # delegate 0 with a matching designator hash
    for sig in (0, 1, 2):
        s.op("PIN_PRESET", 4, PP["PP_7702"]).op("PIN_SET", 4, PF["PF_SIG"], sig).op("CHK_WF", 4, 0, 0, 1)

    s = pins(new("ACP_TV_29", "ACP-TV-29", "Modes 3 and 4: no delegate, no delegate code hash, an account code hash that is not a sentinel, a family, signatureMode in {0,2}"))
    for preset in ("PP_4337", "PP_1271"):
        for field, value in (("PF_DELEGATE", 1), ("PF_DCODE", 1), ("PF_CODE", 0), ("PF_CODE", KE), ("PF_CODE", M.PIN_EOA), ("PF_FAMILY", 0),
                             ("PF_SIG", 1)):
            s.op("PIN_PRESET", 4, PP[preset]).op("PIN_SET", 4, PF[field], value).op("CHK_WF", 4, 0, 0, 0)
        for sig in (0, 2):
            s.op("PIN_PRESET", 4, PP[preset]).op("PIN_SET", 4, PF["PF_SIG"], sig).op("CHK_WF", 4, 0, 0, 1)

    s = pins(new("ACP_TV_30", "ACP-TV-30", "pinVersion = 0, accountMode = 0 (UNKNOWN_CODE) or 5 are malformed"))
    s.op("PIN_PRESET", 4, PP["PP_EOA"]).op("PIN_SET", 4, PF["PF_VERSION"], 0).op("CHK_WF", 4, 0, 0, 0)
    s.op("PIN_PRESET", 4, PP["PP_EOA"]).op("PIN_SET", 4, PF["PF_MODE"], 0).op("CHK_WF", 4, 0, 0, 0)
    s.op("PIN_PRESET", 4, PP["PP_EOA"]).op("PIN_SET", 4, PF["PF_MODE"], 5).op("CHK_WF", 4, 0, 0, 0)
    s.op("PIN_PRESET", 4, PP["PP_EOA"]).op("PIN_SET", 4, PF["PF_VERSION"], M.UINT32_MAX).op("CHK_WF", 4, 0, 0, 1)

    # ---- activation refuses a malformed or mismatching pin
    s = pins(new("ACP_TV_ACTIVATE", "ACP-TV-24", "activate checks PIN_WELLFORMED, PIN_OK and pinVersion = 1 (and the router and the extensions)"))
    s.routers().op("TERMS_RESET", 0, S.TERMS_PRESETS["TP_ONE"])
    s.op("PIN_PRESET", 4, PP["PP_EOA"]).op("PIN_SET", 4, PF["PF_DELEGATE"], 1)
    s.op("ACTIVATE", 0, 0, 0, 0, 4, expect="AccountPinMalformed")
    s.op("ACTIVATE", 0, 0, 0, 0, 1, expect="AccountPinMismatch")                  # 7702 pin, account without delegation
    s.op("PIN_PRESET", 4, PP["PP_EOA"]).op("PIN_SET", 4, PF["PF_VERSION"], 2)
    s.op("ACTIVATE", 0, 0, 0, 0, 4, expect="PinVersionMismatch")
    s.op("ACTIVATE", 0, 0, 3, 0, 0, expect="RouterNotBindable")
    s.op("TERMS_SET", 0, TF["T_EXT"], 0, 0, 5)
    s.op("ACTIVATE", 0, 0, 0, 0, 0, expect="ExtensionsNotSupported")
    s.op("TERMS_SET", 0, TF["T_EXT"], 0, 0, 0)
    s.op("ACTIVATE", 0, 0, 0, 0, 0)
    s.op("EXPECT_PINVER", 0, 1).op("EXPECT_LIVE", 0, 0, 1, 1)

    # ---- ACP-TV-31..33: the live account and the delegate on a charge
    s = new("ACP_TV_31", "ACP-TV-31", "Mode 2: PIN_OK holds, then the delegate is redeployed: AccountCodeChanged(DELEGATE_CODE) on the next charge; ACP-TV-32 no code")
    pins(s)
    s.routers().op("TERMS_RESET", 0, S.TERMS_PRESETS["TP_ONE"])
    account_7702(s)
    s.op("ACTIVATE", 0, 0, 0, 0, 1)
    s.grant(1, 0)
    s.charge(0, 0, 1, 10, 1)
    s.op("DELEG_SET", D1, P7702.delegateCodeHash ^ 1)
    s.charge(0, 0, 1, 10, 2, expect=("AccountCodeChanged", M.FIELD_DELEGATE_CODE))
    s.op("DELEG_SET", D1, 0)                                              # ACP-TV-32: the delegate address has no code at all
    s.charge(0, 0, 1, 10, 2, expect=("AccountCodeChanged", M.FIELD_DELEGATE_CODE))
    s.op("DELEG_SET", D1, P7702.delegateCodeHash)
    s.charge(0, 0, 1, 10, 2)
    s.op("ACCT_SET", 0, H1 ^ 1)
    s.charge(0, 0, 1, 10, 3, expect=("AccountCodeChanged", M.FIELD_ACCOUNT_CODE))

    s = new("ACP_TV_33", "ACP-TV-33", "Mode 3: h equal to the pinned account code hash passes; a different h is AccountCodeChanged(ACCOUNT_CODE)")
    pins(s)
    s.routers().op("TERMS_RESET", 0, S.TERMS_PRESETS["TP_ONE"])
    s.op("ACCT_SET", 0, P4337.accountCodeHash)
    s.op("ACTIVATE", 0, 0, 0, 0, 2)
    s.grant(1, 0)
    s.charge(0, 0, 1, 10, 1)
    s.op("ACCT_SET", 0, P4337.accountCodeHash ^ 1)
    s.charge(0, 0, 1, 10, 2, expect=("AccountCodeChanged", M.FIELD_ACCOUNT_CODE))

    # ---- ACP-TV-34: consume with a pin whose hash differs in any one of the seven fields
    s = new("ACP_TV_34", "ACP-TV-34", "consume with a pin struct that differs from accountPinHash in any one field: PinHashMismatch each time")
    pins(s)
    s.routers().op("TERMS_RESET", 0, S.TERMS_PRESETS["TP_ONE"])
    account_7702(s)
    s.op("ACTIVATE", 0, 0, 0, 0, 1)
    s.grant(1, 0)
    for field, value in (("PF_MODE", 3), ("PF_CODE", P7702.accountCodeHash ^ 1), ("PF_DELEGATE", 0xCDCD), ("PF_DCODE", P7702.delegateCodeHash ^ 1),
                         ("PF_FAMILY", P7702.implementationFamily ^ 1), ("PF_VERSION", 2), ("PF_SIG", 1)):
        s.op("PIN_PRESET", 5, PP["PP_7702"]).op("PIN_SET", 5, PF[field], value)
        s.op("SETREG", 1, 6)
        s.charge(0, 0, 1, 10, 1, expect="PinHashMismatch")
    s.op("SETREG", 1, 0)
    s.charge(0, 0, 1, 10, 1)

    # ---- ACP-TV-20, 21, 35, 36: updateAccountPin
    s = new("ACP_TV_35", "ACP-TV-35", "updateAccountPin: pinVersion = old + 1 accepted, = old and = old + 2 refused; ACP-TV-20, 21, 36")
    pins(s)
    s.routers().op("TERMS_RESET", 0, S.TERMS_PRESETS["TP_ONE"])
    s.op("ACTIVATE", 0, 0, 0, 0, 0)
    s.op("PIN_PRESET", 4, PP["PP_EOA"]).op("PIN_SET", 4, PF["PF_VERSION"], 2)       # every field equal, version + 1 (ACP-TV-36)
    s.op("PIN_PRESET", 5, PP["PP_EOA"]).op("PIN_SET", 5, PF["PF_VERSION"], 3)
    s.op("PIN_PRESET", 6, PP["PP_EOA"])                                               # version 1 = old (replay)
    s.op("UPDATE_PIN", 0, 0, 6, T0 + 100, 1, expect="PinVersionMismatch")
    s.op("UPDATE_PIN", 0, 0, 5, T0 + 100, 1, expect="PinVersionMismatch")             # old + 2
    s.op("AUTH_ACCESS", 0, SIGN, 0)
    s.op("UPDATE_PIN", 0, 0, 4, T0 + 100, 1, expect="NotCustomer")                    # ACP-TV-21: a third party without a signature
    s.op("AUTH_ACCESS", 1, SIGN, 0)
    s.op("PIN_PRESET", 7, PP["PP_7702"]).op("PIN_SET", 7, PF["PF_VERSION"], 2)
    s.op("UPDATE_PIN", 0, 0, 7, T0 + 100, 1, expect="AccountPinMismatch")             # ACP-TV-20: does not match EXTCODEHASH
    s.op("PIN_PRESET", 7, PP["PP_EOA"]).op("PIN_SET", 7, PF["PF_VERSION"], 2).op("PIN_SET", 7, PF["PF_DELEGATE"], 5)
    s.op("UPDATE_PIN", 0, 0, 7, T0 + 100, 1, expect="AccountPinMalformed")
    s.op("UPDATE_PIN", 0, 0, 4, T0 + 100, 1)                                          # old + 1
    s.op("EXPECT_PINVER", 0, 2)
    s.op("UPDATE_PIN", 0, 0, 5, T0 + 100, 1, expect="AuthorizationReplayed")          # nonce 1 is used
    s.op("UPDATE_PIN", 0, 0, 5, T0 - 1, 2, expect="AuthorizationExpired")
    s.op("UPDATE_PIN", 0, 0, 5, T0, 2)                                                # deadline = now accepted
    s.op("EXPECT_PINVER", 0, 3)

    s = new("ACP_TV_UPDATE_TERMINAL", "ACP-TV-35", "updateAccountPin on a revoked or expired mandate is refused")
    pins(s)
    s.routers().lineage(0).lineage(1, expires=T0 + 100)
    s.op("PIN_PRESET", 4, PP["PP_EOA"]).op("PIN_SET", 4, PF["PF_VERSION"], 2)
    s.op("REVOKE", 0, 0)
    s.op("UPDATE_PIN", 0, 0, 4, T0 + 1000, 1, expect="MandateNotActive")
    s.op("NOW", T0 + 100)
    s.op("UPDATE_PIN", 1, 0, 4, T0 + 1000, 2, expect="MandateNotActive")

    # ---- ACP-TV-37: nextPinVersion
    s = pins(new("ACP_TV_37", "ACP-TV-37", "nextPinVersion: first activation 1; update + 1; successor + 1 only if the pin changed; uint32 overflow reverts"))
    s.op("PIN_PRESET", 4, PP["PP_EOA"]).op("PIN_SET", 4, PF["PF_SIG"], 0)            # a changed pin
    s.op("CHK_NEXTVER", 0, 0, 0, 0, 1)
    s.op("CHK_NEXTVER", 1, 7, 0, 0, 8)
    s.op("CHK_NEXTVER", 2, 0, 0, 0, 1)                                                # successor, field-for-field equal: P.pinVersion (1)
    s.op("CHK_NEXTVER", 2, 0, 0, 4, 2)                                                # successor, changed pin: P.pinVersion + 1
    s.op("CHK_NEXTVER", 1, M.UINT32_MAX, 0, 0, 0, expect=("Panic", 0x11))
    s.op("PIN_PRESET", 5, PP["PP_EOA"]).op("PIN_SET", 5, PF["PF_VERSION"], M.UINT32_MAX)
    s.op("CHK_NEXTVER", 2, 0, 5, 4, 0, expect=("Panic", 0x11))                        # changed pin at the maximum version
    s.op("CHK_NEXTVER", 2, 0, 5, 5, M.UINT32_MAX)                                     # unchanged pin at the maximum version

    # ---- ACP-TV-38, 39, 40: AUTH
    s = pins(new("ACP_TV_38", "ACP-TV-38", "AUTH with signatureMode ECDSA_KEY: an ECDSA signature by the account key; an ERC-1271 signature"))
    s.op("CHK_AUTH", 0, 0, 0, SIGE, 1)
    s.op("CHK_AUTH", 0, 0, 0, SIG1, 1, expect="SignatureModeNotPermitted")
    s.op("CHK_AUTH", 0, 0, 0, SIGE, 0, expect="NotCustomer")
    s.op("CHK_AUTH", 0, 0, 1, SIGN, 0)                                                # msg.sender = customer
    s.op("CHK_AUTH", 0, 0, 0, SIGN, 0, expect="NotCustomer")
    s.op("PIN_PRESET", 4, PP["PP_EOA"]).op("PIN_SET", 4, PF["PF_SIG"], 2)             # not allowed for PIN_EOA by PIN_WELLFORMED, but AUTH still gates by the mode
    s.op("CHK_AUTH", 0, 4, 0, SIGE, 1, expect="SignatureModeNotPermitted")             # ECDSA under signatureMode ERC1271 (AUTH_ECDSA_ANY)

    s = pins(new("ACP_TV_39", "ACP-TV-39", "AUTH with signatureMode ERC1271, mode 2: the delegate's code hash changed -> the ERC-1271 path is closed; then msg.sender"))
    account_7702(s)
    s.op("CHK_AUTH", 0, 1, 0, SIG1, 1)
    s.op("CHK_AUTH", 0, 1, 0, SIG1, 0, expect="NotCustomer")
    s.op("DELEG_SET", D1, P7702.delegateCodeHash ^ 1)                                  # the redeployed delegate returns the magic value for any signature
    s.op("CHK_AUTH", 0, 1, 0, SIG1, 1, expect=("AccountCodeChanged", M.FIELD_DELEGATE_CODE))
    s.op("CHK_AUTH", 0, 1, 1, SIGN, 0)
    s.op("DELEG_SET", D1, P7702.delegateCodeHash)
    s.op("ACCT_SET", 0, H1 ^ 1)
    s.op("CHK_AUTH", 0, 1, 0, SIG1, 1, expect=("AccountCodeChanged", M.FIELD_ACCOUNT_CODE))
    s.op("CHK_AUTH", 0, 1, 0, SIGE, 1, expect="SignatureModeNotPermitted")             # ECDSA under ERC1271

    s = pins(new("ACP_TV_40", "ACP-TV-40", "AUTH with DIRECT_ONLY: any signature refused; revokeBySig and pauseBySig accepted through either path"))
    s.op("PIN_PRESET", 4, PP["PP_EOA"]).op("PIN_SET", 4, PF["PF_SIG"], 0)
    s.op("CHK_AUTH", 0, 4, 0, SIGE, 1, expect="SignatureModeNotPermitted")
    s.op("CHK_AUTH", 0, 4, 0, SIG1, 1, expect="SignatureModeNotPermitted")
    s.op("CHK_AUTH", 0, 4, 1, SIGN, 0)
    s.op("CHK_AUTH_EXIT", 4, 0, SIGE, 1)
    s.op("CHK_AUTH_EXIT", 4, 0, SIG1, 1)
    s.op("CHK_AUTH_EXIT", 4, 0, SIGE, 0, expect="NotCustomer")
    s.op("CHK_AUTH_EXIT", 4, 0, SIGN, 0, expect="NotCustomer")
    s.op("CHK_AUTH_EXIT", 4, 1, SIGN, 0)

    s = pins(new("ACP_TV_41", "ACP-TV-41", "Mode 3 account whose proxy implementation changes (bytecode unchanged): the pin holds and the ERC-1271 path stays open on chain",
                 "the backend half (REVOKED(IMPLEMENTATION), no signature transport) is in vectors/backend.json"))
    s.op("ACCT_SET", 0, P4337.accountCodeHash)
    s.op("CHK_PINCHECK", 2, P4337.accountCodeHash, 0, 0)
    s.op("CHK_AUTH", 0, 2, 0, SIG1, 1)

    # ---- the migration successor with the three kinds of pin is in tools/vectors_mig.py (MIG-TV-29)
    return out


# ----------------------------------------------------------------------------------------------------------------- signer sets
def sets_fixture(sc: Scenario, rotate_at=1000):
    """Governance proposes v1 = {k1,k2,k3} at T0 and v2 = {k1,k2} (k3 replaced) and rotates to v2 at T0 + rotate_at."""
    sc.op("SS_PROPOSE", GOV, 1, 7).op("SS_ACTIVATE", GOV, 1)
    sc.op("SS_PROPOSE", GOV, 2, 3)
    sc.op("NOW", T0 + rotate_at).op("SS_ACTIVATE", GOV, 2)
    return sc


def build_cap():
    out = []

    def new(vid, source, title, note=""):
        sc = Scenario(vid, source, title, note)
        out.append(sc)
        return sc

    TR = T0 + 1000
    s = sets_fixture(new("CAP_TV_14_15", "CAP-TV-14", "Retired set: a quote issued before retiredAt is accepted inside the grace (CAP-TV-15) and refused after it"))
    s.op("NOW", TR + 10).op("SS_VERIFY", 1, 1, TR - 10)
    s.op("NOW", TR + GRACE).op("SS_VERIFY", 1, 1, TR - 10)
    s.op("NOW", TR + GRACE + 1).op("SS_VERIFY", 1, 1, TR - 10, expect="QuoteSignerSetRetired")
    s.op("SS_VERIFY", 1, 2, TR + 1)                                                    # the current set is unaffected
    s.op("SS_VERIFY", 3, 2, TR + 1, expect="QuoteSignerUnauthorized")                  # k3 is not a member of v2
    s.op("SS_VERIFY", 1, 9, TR + 1, expect="QuoteSignerUnauthorized")                  # an unknown set

    s = sets_fixture(new("CAP_TV_16", "CAP-TV-16", "A signer removed by the guardian: QuoteSignerRemoved in every set version, from the removal block, no grace"))
    s.op("NOW", TR + 100).op("SS_VERIFY", 1, 1, TR - 10).op("SS_VERIFY", 1, 2, TR + 1)
    s.op("SS_REMOVE", GUARD, 1)
    s.op("SS_VERIFY", 1, 1, TR - 10, expect="QuoteSignerRemoved").op("SS_VERIFY", 1, 2, TR + 1, expect="QuoteSignerRemoved")
    s.op("SS_VERIFY", 3, 1, TR - 10)                                                   # another key of the retired set still works inside the grace
    s.op("SS_VERIFY", 1, 9, TR + 1, expect="QuoteSignerRemoved")                       # even for a set version the key is not in

    s = sets_fixture(new("CAP_TV_23", "CAP-TV-23", "k in the retired set v; the guardian removes k inside the grace; a quote of v issued before retiredAt: accepted one second before the removal, refused one second after"))
    s.op("NOW", TR + 100).op("SS_VERIFY", 3, 1, TR - 10)
    s.op("NOW", TR + 101).op("SS_REMOVE", GUARD, 3)
    s.op("NOW", TR + 102).op("SS_VERIFY", 3, 1, TR - 10, expect="QuoteSignerRemoved")

    s = new("CAP_TV_24", "CAP-TV-24", "Key removed in the current set; a quote issued before the removal is refused in the removal block and later")
    s.op("SS_PROPOSE", GOV, 1, 7).op("SS_ACTIVATE", GOV, 1)
    s.op("NOW", T0 + 50).op("SS_VERIFY", 1, 1, T0 + 40)
    s.op("SS_REMOVE", GUARD, 1)
    s.op("SS_VERIFY", 1, 1, T0 + 40, expect="QuoteSignerRemoved")
    s.op("NOW", T0 + 5000).op("SS_VERIFY", 1, 1, T0 + 40, expect="QuoteSignerRemoved")
    s.op("SS_VERIFY", 2, 1, T0 + 40)

    s = sets_fixture(new("CAP_TV_25_26", "CAP-TV-25", "Retired v: issuedAt = retiredAt - 1 consumed at retiredAt + GRACE, then +1; issuedAt = retiredAt consumed at retiredAt (CAP-TV-26)"))
    s.op("NOW", TR + GRACE).op("SS_VERIFY", 2, 1, TR - 1)
    s.op("NOW", TR + GRACE + 1).op("SS_VERIFY", 2, 1, TR - 1, expect="QuoteSignerSetRetired")
    s.op("NOW", TR).op("SS_VERIFY", 2, 1, TR, expect="QuoteSignerSetRetired")
    s.op("SS_VERIFY", 2, 1, TR + 5, expect="QuoteSignerSetRetired")
    s.op("SS_VERIFY", 2, 1, TR - 1)

    s = new("CAP_TV_27", "CAP-TV-27", "proposeSignerSet naming a tombstoned key is refused; the same set with the key replaced is accepted")
    s.op("SS_PROPOSE", GOV, 1, 7).op("SS_ACTIVATE", GOV, 1)
    s.op("SS_REMOVE", GUARD, 2)
    s.op("SS_PROPOSE", GOV, 2, 7, expect=("QuoteSignerTombstoned", 2))
    s.op("SS_PROPOSE", GOV, 2, 5)
    s.op("SS_ACTIVATE", GOV, 2)
    s.op("SS_VERIFY", 1, 2, T0 + 1).op("SS_VERIFY", 2, 2, T0 + 1, expect="QuoteSignerRemoved")

    s = new("CAP_TV_27B", "CAP-TV-27", "A key removed after a set was proposed and before it is activated cannot enter the current set (SR-4)")
    s.op("SS_PROPOSE", GOV, 1, 7).op("SS_ACTIVATE", GOV, 1)
    s.op("SS_PROPOSE", GOV, 2, 7)
    s.op("SS_REMOVE", GUARD, 3)
    s.op("SS_ACTIVATE", GOV, 2, expect=("QuoteSignerTombstoned", 3))
    s.op("SS_VERIFY", 1, 1, T0)

    s = sets_fixture(new("CAP_TV_28", "CAP-TV-28", "stopSignerSet for the current set and for a retired set inside its grace: QuoteSignerSetStopped; other versions unaffected"))
    s.op("NOW", TR + 10)
    s.op("SS_STOP", GUARD, 1)
    s.op("SS_VERIFY", 1, 1, TR - 10, expect="QuoteSignerSetStopped")
    s.op("SS_VERIFY", 1, 2, TR + 1)
    s.op("SS_STOP", GUARD, 2)
    s.op("SS_VERIFY", 1, 2, TR + 1, expect="QuoteSignerSetStopped")
    s.op("SS_VERIFY", 2, 2, TR + 1, expect="QuoteSignerSetStopped")
    s.op("SS_STOP", GUARD, 7, expect="SignerSetNotProposed")

    s = new("CAP_TV_29", "CAP-TV-29", "Every member of the current set removed: a fiat-capped charge has no valid signer; a charge without fiat caps succeeds")
    s.routers().lineage(0).grant(1, 0)
    s.op("SS_PROPOSE", GOV, 1, 7).op("SS_ACTIVATE", GOV, 1)
    for k in (1, 2, 3):
        s.op("SS_REMOVE", GUARD, k)
    for k in (1, 2, 3):
        s.op("SS_VERIFY", k, 1, T0, expect="QuoteSignerRemoved")
    s.charge(0, 0, 1, 10, 1)                                                           # the guards G1..G12 do not read a quote

    s = sets_fixture(new("CAP_TV_30", "CAP-TV-30", "A key in v and v+1: a quote of v inside the grace is accepted; after the removal it is refused under both versions"))
    s.op("NOW", TR + 10).op("SS_VERIFY", 1, 1, TR - 10).op("SS_VERIFY", 1, 2, TR + 1)
    s.op("SS_REMOVE", GUARD, 1)
    s.op("SS_VERIFY", 1, 1, TR - 10, expect="QuoteSignerRemoved").op("SS_VERIFY", 1, 2, TR + 1, expect="QuoteSignerRemoved")

    s = new("CAP_TV_31", "CAP-TV-31", "The guardian removes a removed key again: an idempotent no-op; the tombstone is never cleared")
    s.op("SS_PROPOSE", GOV, 1, 7).op("SS_ACTIVATE", GOV, 1)
    s.op("SS_REMOVE", GUARD, 1)
    s.op("NOW", T0 + 500).op("SS_REMOVE", GUARD, 1)
    s.op("SS_REMOVE", GOV, 1)
    s.op("SS_VERIFY", 1, 1, T0, expect="QuoteSignerRemoved")
    s.op("SS_PROPOSE", GOV, 2, 1, expect=("QuoteSignerTombstoned", 1))

    s = new("CAP_TV_32", "CAP-TV-32", "The guardian calls proposeSignerSet or activateSignerSet: NotGovernance (the guardian cannot add)")
    s.op("SS_PROPOSE", GUARD, 1, 7, expect="NotGovernance")
    s.op("SS_PROPOSE", GOV, 1, 7)
    s.op("SS_ACTIVATE", GUARD, 1, expect="NotGovernance")
    s.op("SS_ACTIVATE", GOV, 1)
    s.op("SS_ACTIVATE", GOV, 1, expect="SignerSetNotProposed")
    s.op("SS_PROPOSE", GOV, 3, 1)
    s.op("SS_ACTIVATE", GOV, 3, expect="SignerSetVersionOrder")
    s.op("SS_PROPOSE", GOV, 3, 1, expect="SignerSetVersionOrder")

    s = new("CAP_TV_Q13", "CAP-TV-14", "Q13: a quote issued before the set became active is refused; a set is usable from its activation second")
    s.op("NOW", T0 + 100).op("SS_PROPOSE", GOV, 1, 7).op("SS_ACTIVATE", GOV, 1)
    s.op("NOW", T0 + 200)
    s.op("SS_VERIFY", 1, 1, T0 + 99, expect="QuoteSignerSetRetired")
    s.op("SS_VERIFY", 1, 1, T0 + 100)
    return out


# ----------------------------------------------------------------------------------------------------------------- registry and time
def build_boundaries():
    out = []

    def new(vid, source, title, note=""):
        sc = Scenario(vid, source, title, note)
        out.append(sc)
        return sc

    s = new("TB_REGISTRY_NOTICE", "12 section 3", "Deprecation notice: sunsetNotBefore = now + MIN_NOTICE accepted, one second less refused (standard and security)")
    s.routers()
    s.op("REG_DEPRECATE", 0, 1, M.REASON_STANDARD, T0 + M.MIN_NOTICE_STANDARD - 1, expect="NoticeTooShort")
    s.op("REG_DEPRECATE", 0, 1, M.REASON_SECURITY, T0 + M.MIN_NOTICE_SECURITY - 1, expect="NoticeTooShort")
    s.op("REG_DEPRECATE", 0, 1, M.REASON_SECURITY, T0 + M.MIN_NOTICE_SECURITY)
    s.op("EXPECT_MODE", 0, M.MODE_EMERGENCY, 1, 1)
    s.op("REG_DEPRECATE", 0, 1, M.REASON_STANDARD, 0, expect="WrongRouterState")
    s.op("REG_SUNSET", 0, expect="NotYetSunset")
    s.op("NOW", T0 + M.MIN_NOTICE_SECURITY - 1).op("REG_SUNSET", 0, expect="NotYetSunset")
    s.op("NOW", T0 + M.MIN_NOTICE_SECURITY).op("REG_SUNSET", 0)
    s.op("NOW", T0 + M.MIN_NOTICE_SECURITY + M.RETENTION - 1).op("REG_RETIRE", 0, expect="RetentionNotElapsed")
    s.op("NOW", T0 + M.MIN_NOTICE_SECURITY + M.RETENTION).op("REG_RETIRE", 0)
    s.op("EXPECT_MODE", 0, M.MODE_EMERGENCY, 0, 0)
    s.op("REG_DISABLE", 0, expect="WrongRouterState")

    s = new("TB_REGISTRY_GUARDS", "12 section 3", "Registry: a successor must be ACTIVE; at most two live routers; emergency disable and clear restore the state")
    s.routers()
    s.op("REG_PROPOSE", 2)
    s.op("REG_REGISTER", 3, expect="TooManyLiveRouters")
    s.op("REG_DEPRECATE", 0, 2, M.REASON_STANDARD, 0, expect="SuccessorNotActive")        # CANDIDATE is not ACTIVE
    s.op("REG_DEPRECATE", 0, 0, M.REASON_STANDARD, 0, expect="SuccessorNotActive")        # itself
    s.op("REG_DISABLE", 1)
    s.op("EXPECT_MODE", 1, M.MODE_EMERGENCY, 0, 0)
    s.op("REG_CLEAR", 1)
    s.op("EXPECT_MODE", 1, M.MODE_NORMAL, 1, 1)
    s.op("REG_CLEAR", 1, expect="WrongRouterState")
    s.op("REG_DEPRECATE", 0, 1, M.REASON_STANDARD, 0)
    s.op("REG_DISABLE", 0)
    s.op("EXPECT_MODE", 0, M.MODE_EMERGENCY, 0, 0)
    s.op("REG_CLEAR", 0)
    s.op("EXPECT_MODE", 0, M.MODE_NORMAL, 1, 1)                                           # back to DEPRECATED (standard)

    s = new("TB_ALLOWANCE", "MIG-TV-22", "Permit2 mock: usable at now = expiration, expired one second later; expiration 0 stores block.timestamp; lockdown keeps the expiration")
    s.op("P2_APPROVE", 0, 1, 0, 100, T0 + 5)
    s.op("NOW", T0 + 5).op("P2_TRANSFER", 0, 0, 1, 10)
    s.op("NOW", T0 + 6).op("P2_TRANSFER", 0, 0, 1, 10, expect=("AllowanceExpired", T0 + 5))
    s.op("P2_APPROVE", 0, 1, 0, 100, 0)                                                   # expiration 0 stores block.timestamp (F5)
    s.op("P2_EXPECT", 0, 1, 0, 100, T0 + 6)
    s.op("P2_TRANSFER", 0, 0, 1, 10)
    s.op("NOW", T0 + 7).op("P2_TRANSFER", 0, 0, 1, 10, expect=("AllowanceExpired", T0 + 6))
    s.op("P2_APPROVE", 0, 1, 0, 100, T0 + 100)
    s.op("P2_LOCKDOWN", 0, 1, 0)
    s.op("P2_EXPECT", 0, 1, 0, 0, T0 + 100)                                               # lockdown zeroes the amount only
    s.op("P2_TRANSFER", 0, 0, 1, 1, expect=("InsufficientAllowance", 0))
    s.op("P2_APPROVE", 0, 1, 0, 0, 0)                                                     # approve(token, R, 0, 0): amount 0, expiration = now
    s.op("P2_EXPECT", 0, 1, 0, 0, T0 + 7)
    s.op("P2_TRANSFER", 0, 0, 1, 0)                                                       # a zero pull at the boundary is fine
    s.op("P2_INVALIDATE", 0, 1, 0, 65535)
    s.op("P2_EXPECT_NONCE", 0, 1, 0, 65535)
    s.op("P2_INVALIDATE", 0, 1, 0, 65535, expect="InvalidNonce")
    s.op("P2_INVALIDATE", 0, 1, 0, 65535 + 65535)
    s.op("P2_INVALIDATE", 0, 1, 0, 65535 + 65535 + 65536, expect="ExcessiveInvalidation")

    s = new("TB_MANDATE_EXPIRY", "11 section 4.8", "G1: a charge at expiresAt - 1 succeeds, at expiresAt it is refused (tau < expiresAt); retire needs now >= expiresAt")
    s.routers().lineage(0, expires=T0 + 500).grant(1, 0)
    s.op("NOW", T0 + 499).charge(0, 0, 1, 10, 1)
    s.op("RETIRE", 0, 0, expect="NotRetirable")
    s.op("NOW", T0 + 500).charge(0, 0, 1, 10, 2, expect="MandateNotConsumable")
    s.op("RETIRE", 0, 0)
    s.status(0, 0, M.MS_ACTIVE, 0, 1).op("EXPECT_LIVE", 0, 0, 1, 0)

    s = new("TB_QUOTE_TIMES", "11 section 4.2", "Q9..Q12: validAfter = now accepted (now - 1 not yet valid), validUntil = now accepted (+1 expired), TTL = limit accepted (+1 too long)")
    s.op("NOW", T0 + 100)
    s.op("W_QUOTE", T0 + 100, T0 + 100, T0 + 220, 120, 300)                               # TTL 120 = min(120, 300), validAfter = now
    s.op("W_QUOTE", T0 + 100, T0 + 101, T0 + 220, 120, 300, expect="QuoteNotYetValid")
    s.op("W_QUOTE", T0 + 99, T0 + 99, T0 + 100, 120, 300)                                 # validUntil = now
    s.op("W_QUOTE", T0 + 98, T0 + 98, T0 + 99, 120, 300, expect="QuoteExpired")
    s.op("W_QUOTE", T0 + 100, T0 + 100, T0 + 221, 120, 300, expect="QuoteTtlTooLong")     # 121 > 120
    s.op("W_QUOTE", T0 + 100, T0 + 100, T0 + 221, 300, 120, expect="QuoteTtlTooLong")     # min(300, 120) = 120
    s.op("W_QUOTE", T0 + 100, T0 + 100, T0 + 220, 300, 120)
    s.op("W_QUOTE", T0 + 101, T0 + 100, T0 + 220, 120, 300, expect="QuoteTimesInvalid")   # issuedAt > validAfter
    s.op("W_QUOTE", T0 + 99, T0 + 100, T0 + 99, 120, 300, expect="QuoteTimesInvalid")     # validAfter > validUntil
    s.op("W_QUOTE", T0 + 100, T0 + 100, T0 + 100, 0, 300)                                 # TTL 0 with maxQuoteAge 0

    s = new("TB_WINDOW_GRID", "11 section 3.1", "Window and cycle grid: the index changes exactly at anchor + k * length; cycleIndex <= floor((now - anchor)/period)")
    anchor = 1_800_000_000
    for name, ln in (("DAY", 86_400), ("WEEK", 604_800), ("THIRTY", 2_592_000)):
        for k in (1, 2, 12):
            s.op("W_WINDOW", anchor + k * ln - 1, anchor, ln, k - 1)
            s.op("W_WINDOW", anchor + k * ln, anchor, ln, k)
            s.op("W_WINDOW", anchor + k * ln + 1, anchor, ln, k)
    s.op("W_WINDOW", anchor, anchor, 86_400, 0)
    s.op("W_WINDOW", anchor - 1, anchor, 86_400, 0, expect=("Panic", 0x11))                # before the anchor: checked arithmetic
    s.op("W_WINDOW", anchor, anchor, 0, 0, expect=("Panic", 0x12))
    p = 2_592_000
    s.op("NOW", anchor + 3 * p - 1).op("W_CYCLE", 2, anchor, p).op("W_CYCLE", 3, anchor, p, expect="CycleNotYetDue")
    s.op("NOW", anchor + 3 * p).op("W_CYCLE", 3, anchor, p).op("W_CYCLE", 0, anchor, p)  # a late cycle is allowed
    s.op("W_CYCLE", 4, anchor, p, expect="CycleNotYetDue")
    s.op("W_WINDOW", M.UINT64_MAX, 0, 2_592_000, M.UINT64_MAX // 2_592_000)
    s.op("W_WINDOW", (1 << 255), 1, 3, ((1 << 255) - 1) // 3)

    nb = M.MAX_BATCH
    s = new("TB_BATCH", "12 section 13", f"MAX_BATCH: {nb} successors accepted, {nb + 1} refused")
    s.op("W_BATCH", 0).op("W_BATCH", nb - 1).op("W_BATCH", nb).op("W_BATCH", nb + 1, expect="BatchTooLarge").op("W_BATCH", 1 << 200, expect="BatchTooLarge")

    # ---- integer widths
    s = new("IW_PERMIT2", "integer width", "Permit2 mock: uint160 and uint48 limits; uint160.max is unlimited and never decremented; no silent truncation")
    s.op("P2_APPROVE", 0, 1, 0, MAXU160, (1 << 48) - 1)
    s.op("P2_EXPECT", 0, 1, 0, MAXU160, (1 << 48) - 1)
    s.op("P2_TRANSFER", 0, 0, 1, 10 ** 30)
    s.op("P2_TRANSFER", 0, 0, 1, MAXU160)
    s.op("P2_EXPECT", 0, 1, 0, MAXU160, (1 << 48) - 1)                                    # never decremented
    s.op("P2_APPROVE", 0, 1, 0, MAXU160 + 1, FAR, expect="AbiOutOfRange")                 # 2^160: refused, not truncated to 0
    s.op("P2_APPROVE", 0, 1, 0, 100, 1 << 48, expect="AbiOutOfRange")                    # 2^48: refused, not truncated to 0
    s.op("P2_APPROVE", 0, 1, 0, 1 << 255, FAR, expect="AbiOutOfRange")
    s.op("P2_EXPECT", 0, 1, 0, MAXU160, (1 << 48) - 1)
    s.op("P2_TRANSFER", 0, 0, 1, MAXU160 + 1, expect="AbiOutOfRange")
    s.op("NOW", (1 << 48) - 1).op("P2_TRANSFER", 0, 0, 1, 1)                              # usable at the last representable second
    s.op("NOW", 1 << 48).op("P2_TRANSFER", 0, 0, 1, 1, expect=("AllowanceExpired", (1 << 48) - 1))

    s = new("IW_NARROW", "integer width", "Narrowing never truncates: uint32, uint48, uint64, uint160 at the limit and one above")
    for bits in (32, 48, 64, 160):
        s.op("W_NARROW", bits, (1 << bits) - 1)
        s.op("W_NARROW", bits, 1 << bits, expect="UnsafeCast")
        s.op("W_NARROW", bits, (1 << 256) - 1, expect="UnsafeCast")
        s.op("W_NARROW", bits, (1 << bits) + 5, expect="UnsafeCast")
    s.op("W_NARROW", 160, 0)

    s = new("IW_ARITHMETIC", "integer width", "Checked arithmetic: used + amount near 2^256 reverts; a total is never computed modulo 2^256")
    s.op("W_ADD", (1 << 256) - 2, 1).op("W_ADD", (1 << 256) - 1, 0)
    s.op("W_ADD", (1 << 256) - 1, 1, expect=("Panic", 0x11))
    s.op("W_ADD", 1 << 255, 1 << 255, expect=("Panic", 0x11))
    s = new("IW_CONSUME", "integer width", "consume: a total near 2^256 reverts; an amount above uint160 is refused (SafeCast), not truncated")
    s.routers().lineage(0, extra=[(TF["T_CAP"], 1, 0, 0)]).grant(1, 0)               # per-payment cap 0 = no cap
    s.charge(0, 0, 1, 1 << 160, 1, expect="TokenTotalCapExceeded")                   # the lineage total cap of 1000 binds before the cast
    s.charge(0, 0, 1, MAXU160, 3, expect="TokenTotalCapExceeded")
    s.op("TERMS_RESET", 5, S.TERMS_PRESETS["TP_ONE"])
    s.op("TERMS_SET", 5, TF["T_CAP"], 1, 0, 0).op("TERMS_SET", 5, TF["T_CAP"], 1, 1, 0)
    s.op("ACTIVATE", 1, 0, 0, 5, 0)                                                      # no per-payment cap, no total cap
    s.charge(1, 0, 1, 1 << 160, 4, expect="UnsafeCast")
    s.op("P2_APPROVE", 0, 1, 0, MAXU160, FAR)
    s.charge(1, 0, 1, MAXU160, 5)
    s.op("EXPECT_USAGE", 1, 1, MAXU160)
    s.charge(1, 0, 1, (1 << 256) - 1, 6, expect=("Panic", 0x11))                        # used + amount overflows uint256

    s = new("IW_COUNTS", "integer width", "uint32 exposure counts: seeded at 2^32 - 1, one more activation reverts with Panic(0x11); the index is not wrapped")
    s.routers()
    s.lineage(0)
    s.op("SEED_LIVE", 0, 0, 1, M.UINT32_MAX)
    s.op("TERMS_RESET", 4, S.TERMS_PRESETS["TP_ONE"])
    s.op("ACTIVATE", 4, 0, 0, 4, 0, expect=("Panic", 0x11))
    s.op("EXPECT_LIVE", 0, 0, 1, M.UINT32_MAX)

    s = new("IW_CONTAIN", "integer width", "E(0) = infinity compares above uint256.max; a cap of uint256.max is not 'no cap'")
    s.op("TERMS_RESET", 0, 1).op("TERMS_RESET", 1, 1)
    s.op("TERMS_SET", 0, TF["T_CAP"], 1, 0, (1 << 256) - 1)                                # snapshot: per-payment cap 2^256 - 1
    s.op("TERMS_SET", 1, TF["T_CAP"], 1, 0, 0)                                              # successor: no cap
    s.op("CHK_CONTAINED", 1, 0, 0, 1 << 3)                                                  # K.4 violated
    s.op("CHK_CONTAINED", 0, 1, 0, 0)                                                       # the reverse is contained
    s.op("TERMS_SET", 0, TF["T_FIAT"], 1, 0, (1 << 256) - 1)
    s.op("TERMS_SET", 1, TF["T_FIAT"], 1, 0, 0)
    s.op("CHK_CONTAINED", 1, 0, 0, (1 << 3) | (1 << 4))
    s.op("CHK_CONTAINED", 0, 1, 0, 0)
    s.op("TERMS_SET", 0, TF["T_EXPIRES"], 0, 0, (1 << 64) - 1).op("TERMS_SET", 1, TF["T_EXPIRES"], 0, 0, (1 << 64) - 1)
    s.op("CHK_CONTAINED", 0, 0, 0, 0)
    return out
