#!/usr/bin/env python3
"""Executable reference model of the FastPay migration, account-pin and signer-set predicates (revision 0.5).

Pure Python, no dependencies beyond tools/eip712_vectors.py and tools/eip712_types.py. This is the SOURCE of the vectors that tools/export_foundry.py writes
into spec/foundry/. It is a model of the specification, not an implementation: nothing here is audited, approved or tested on a chain.
The Solidity reference model in spec/foundry/src/ mirrors this file one to one (same predicate names, same order, same errors, same
mutant numbers); a difference between the two is a defect in one of them.

Contents
  Permit2Model          allowances keyed (owner, token, spender), modelled on AllowanceTransfer.sol at the pinned commit
  RouterRegistryModel   router states, isBindable, Mode(R)                                         (document 12 section 3 and 5.3.1)
  ManagerModel          mandates, lineages, exposure index, activate, activateSuccessor (A1..O1E, E1..E6), revoke, retire, reduce,
                        updateAccountPin, consume                                                  (document 12 section 5.3, 17 section 5)
  pin functions         PIN_WELLFORMED, PIN_OK, nextPinVersion, AUTH, hashStruct(AccountPin)         (document 17 section 5)
  SignerSetModel        signer sets, tombstones, Q1 and Q13                                         (document 11 sections 4.2, 4.7)
  MUTANTS               named mutations of the model (the same numbers are used by the Solidity model); the mutation analysis in
                        tools/model_checks.py checks that the exported vector suite kills every one of them

Every model object has a `mut` attribute (0 = the specification); a non-zero value applies exactly one mutation.
All numbers are Python ints; addresses and bytes32 values are ints too (hashed through tools/eip712_vectors.py).
"""
import dataclasses
import functools
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import eip712_types as ET  # noqa: E402
import eip712_vectors as V  # noqa: E402

# ----------------------------------------------------------------------------------------------------------------- constants
UINT32_MAX = (1 << 32) - 1
UINT48_MAX = (1 << 48) - 1
UINT64_MAX = (1 << 64) - 1
UINT160_MAX = (1 << 160) - 1
UINT256_MAX = (1 << 256) - 1

CHAIN_ID = 84532
MANAGER_ADDRESS = 0x2222222222222222222222222222222222222222

MAX_EXPOSED_TOKENS_PER_ROUTER = 8          # PC-18, proposal
MAX_BATCH = 10                             # PC-04, proposal (50 before the measurement on the actual contracts, ADR-022)
MIN_NOTICE_STANDARD = 180 * 86400          # PC-01, proposal
MIN_NOTICE_SECURITY = 60 * 86400           # PC-02, proposal
RETENTION = 365 * 86400                    # PC-03, proposal
ROLLBACK_WINDOW = 30 * 86400               # registry parameter, proposal
QUOTE_SET_GRACE = 300                      # PC-08, proposal
MAX_QUOTE_TTL = 300                        # PC-06, proposal
MAX_LIVE_ROUTERS = 2                       # PC-12

NORMAL, EMERGENCY, REVISION = 0, 1, 2      # kind (uint8 in the typed data)
MODE_NORMAL, MODE_EMERGENCY = 0, 1
REASON_STANDARD, REASON_SECURITY = 0, 1

ST_UNREGISTERED, ST_CANDIDATE, ST_ACTIVE, ST_DEPRECATED, ST_DISABLED, ST_SUNSET, ST_RETIRED, ST_CANCELLED = range(8)
ST_NAMES = ["UNREGISTERED", "CANDIDATE", "ACTIVE", "DEPRECATED", "DISABLED_EMERGENCY", "SUNSET", "RETIRED", "CANCELLED"]

MS_ACTIVE, MS_REVOKED = 0, 1                                  # mandate status as recorded on chain
RV_NONE, RV_CUSTOMER, RV_SUPERSEDED_MIGRATION, RV_SUPERSEDED_REVISION = 0, 1, 2, 3
PAUSE_CUSTOMER, PAUSE_RISK, PAUSE_DELEGATION = 1, 2, 4

SIG_NONE, SIG_ECDSA, SIG_ERC1271 = 0, 1, 2                    # how a customer message reaches the contract
SM_DIRECT_ONLY, SM_ECDSA_KEY, SM_ERC1271 = 0, 1, 2            # AccountPin.signatureMode
FIELD_ACCOUNT_CODE, FIELD_DELEGATE_CODE = 1, 2                # AccountCodeChanged(customer, field)

ROLE_GOVERNANCE, ROLE_GUARDIAN = 0, 1

KECCAK_EMPTY = int.from_bytes(V.KECCAK_EMPTY, "big")
PIN_EOA = int.from_bytes(V.PIN_EOA, "big")
INF = V.INF


def h2i(b: bytes) -> int:
    return int.from_bytes(b, "big")


def i2b(x: int) -> bytes:
    return x.to_bytes(32, "big")


def addr_hex(x: int) -> str:
    return "0x%040x" % x


def tag_int(s: str) -> int:
    return h2i(V.tag(s))


# ----------------------------------------------------------------------------------------------------------------- reverts
class Revert(Exception):
    """A revert with a custom-error name (or 'Panic') and the one argument the vectors compare (0 if none)."""

    def __init__(self, name, arg=0):
        super().__init__(f"{name}({arg})")
        self.name = name
        self.arg = arg


# name, Solidity signature, index of the revert-data word that carries the compared argument (-1: none), what that word is
ERRORS = [
    ("NotCustomer", "NotCustomer()", -1, "none"),
    ("SignatureModeNotPermitted", "SignatureModeNotPermitted()", -1, "none"),
    ("AuthorizationExpired", "AuthorizationExpired()", -1, "none"),
    ("AuthorizationReplayed", "AuthorizationReplayed()", -1, "none"),
    ("AuthorizationMismatch", "AuthorizationMismatch()", -1, "none"),
    ("WrongPredecessor", "WrongPredecessor()", -1, "none"),
    ("RouterNotBindable", "RouterNotBindable()", -1, "none"),
    ("WrongKind", "WrongKind()", -1, "none"),
    ("ModeMismatch", "ModeMismatch()", -1, "none"),
    ("ExtensionsNotSupported", "ExtensionsNotSupported()", -1, "none"),
    ("AccountPinMalformed", "AccountPinMalformed()", -1, "none"),
    ("AccountPinMismatch", "AccountPinMismatch()", -1, "none"),
    ("PinVersionMismatch", "PinVersionMismatch()", -1, "none"),
    ("PinHashMismatch", "PinHashMismatch()", -1, "none"),
    ("AccountCodeChanged", "AccountCodeChanged(address,uint8)", 1, "uint"),
    ("NewPermissionMissing", "NewPermissionMissing(address)", 0, "token"),
    ("ExposureLimit", "ExposureLimit()", -1, "none"),
    ("TermsInvalid", "TermsInvalid(uint8)", -1, "none"),                     # invented name (TermsShape: canonical form and documented widths; added with the implementation evidence)
    ("TooManySigners", "TooManySigners(uint256,uint256)", -1, "none"),      # invented name (a signer set above MAX_SIGNERS_PER_SET, proposed PC-19)
    ("TermsNotContained", "TermsNotContained()", -1, "none"),
    ("LineageConstantsChanged", "LineageConstantsChanged()", -1, "none"),
    ("WidenedMaskMismatch", "WidenedMaskMismatch()", -1, "none"),
    ("OldPermissionNotRevoked", "OldPermissionNotRevoked(address)", 0, "token"),
    ("ResidualAllowanceUnbounded", "ResidualAllowanceUnbounded(address)", 0, "token"),
    ("PaymentAlreadySettled", "PaymentAlreadySettled()", -1, "none"),
    ("MandateNotConsumable", "MandateNotConsumable()", -1, "none"),          # invented name (11 section 5 names no error for G1)
    ("WrongRouter", "WrongRouter()", -1, "none"),                            # invented name (G2)
    ("RouterNotChargeable", "RouterNotChargeable()", -1, "none"),            # invented name (G2)
    ("TokenNotInMandate", "TokenNotInMandate()", -1, "none"),                # invented name (G4)
    ("TokenPerPaymentCapExceeded", "TokenPerPaymentCapExceeded()", -1, "none"),
    ("TokenTotalCapExceeded", "TokenTotalCapExceeded()", -1, "none"),
    ("MandateNotActive", "MandateNotActive()", -1, "none"),                  # invented name (revoke, retire of a non-active mandate)
    ("NotRetirable", "NotRetirable()", -1, "none"),                          # invented name (retire of a live mandate)
    ("NoTokensLeft", "NoTokensLeft()", -1, "none"),                          # invented name (reduce to zero tokens)
    ("UnknownMandate", "UnknownMandate()", -1, "none"),                      # invented name
    ("QuoteSignerUnauthorized", "QuoteSignerUnauthorized()", -1, "none"),
    ("QuoteSignerRemoved", "QuoteSignerRemoved()", -1, "none"),
    ("QuoteSignerSetRetired", "QuoteSignerSetRetired()", -1, "none"),
    ("QuoteSignerSetStopped", "QuoteSignerSetStopped()", -1, "none"),
    ("QuoteSignerTombstoned", "QuoteSignerTombstoned(address)", 0, "key"),
    ("NotGovernance", "NotGovernance()", -1, "none"),
    ("NotAuthorized", "NotAuthorized()", -1, "none"),                        # invented name (a caller that is neither role)
    ("SignerSetNotProposed", "SignerSetNotProposed()", -1, "none"),          # invented name
    ("SignerSetVersionOrder", "SignerSetVersionOrder()", -1, "none"),        # invented name
    ("SuccessorNotActive", "SuccessorNotActive()", -1, "none"),              # invented name (registry deprecate guard)
    ("NoticeTooShort", "NoticeTooShort()", -1, "none"),                      # invented name (MIN_NOTICE guard)
    ("NotYetSunset", "NotYetSunset()", -1, "none"),                          # invented name
    ("RetentionNotElapsed", "RetentionNotElapsed()", -1, "none"),            # invented name
    ("WrongRouterState", "WrongRouterState()", -1, "none"),                  # invented name
    ("TooManyLiveRouters", "TooManyLiveRouters()", -1, "none"),              # invented name (PC-12)
    ("AllowanceExpired", "AllowanceExpired(uint256)", 0, "uint"),            # Permit2
    ("InsufficientAllowance", "InsufficientAllowance(uint256)", 0, "uint"),  # Permit2
    ("InvalidNonce", "InvalidNonce()", -1, "none"),                          # Permit2
    ("ExcessiveInvalidation", "ExcessiveInvalidation()", -1, "none"),        # Permit2
    ("QuoteTimesInvalid", "QuoteTimesInvalid()", -1, "none"),
    ("QuoteNotYetValid", "QuoteNotYetValid()", -1, "none"),
    ("QuoteExpired", "QuoteExpired()", -1, "none"),
    ("QuoteTtlTooLong", "QuoteTtlTooLong()", -1, "none"),
    ("BatchTooLarge", "BatchTooLarge()", -1, "none"),                        # invented name (MAX_BATCH)
    ("CycleNotYetDue", "CycleNotYetDue()", -1, "none"),                      # invented name (G9: cycleIndex <= currentIndex(now))
    ("AbiOutOfRange", "AbiOutOfRange()", -1, "none"),                        # models the ABI decoder rejecting a value above uint160/uint48
    ("UnsafeCast", "UnsafeCast()", -1, "none"),                              # models SafeCast160 (never truncate silently)
    ("Panic", "Panic(uint256)", 0, "uint"),                                  # built in; arg 0x11 is arithmetic overflow
]
ERROR_ID = {e[0]: i + 1 for i, e in enumerate(ERRORS)}              # 0 means "no revert"
ERROR_BY_ID = {i + 1: e for i, e in enumerate(ERRORS)}


def error_selector(name: str) -> int:
    sig = next(e[1] for e in ERRORS if e[0] == name)
    return int.from_bytes(V.keccak256(sig.encode())[:4], "big")


# ----------------------------------------------------------------------------------------------------------------- mutants
_MUTANT_TABLE = [
    # (name, what it breaks)  -- grouped by the predicate or function it belongs to; the number is the position (from 1)
    ("A1_SKIP", "A1: no authentication of the caller"),
    ("A1_PIN_FROM_NEW", "A1: the signature mode of the NEW pin governs, not the stored one (17 section 5.4 consequence 3)"),
    ("AUTH_1271_NOPIN", "AUTH: the ERC-1271 path does not require PIN_OK on the live account"),
    ("AUTH_DIRECT_ONLY_OK", "AUTH: DIRECT_ONLY accepts a valid signature"),
    ("AUTH_ECDSA_ANY", "AUTH: an ECDSA signature is accepted under signatureMode ERC1271"),
    ("AUTH_1271_ANY", "AUTH: an ERC-1271 signature is accepted under signatureMode ECDSA_KEY"),
    ("AUTH_SIGOK_SKIP", "AUTH: signature validity is not checked"),
    ("AUTH_EXIT_GATED", "AUTH: exits (revokeBySig, pauseBySig) are gated by the signature mode"),
    ("A2_DEADLINE_SKIP", "A2: deadline not checked"),
    ("A2_DEADLINE_STRICT", "A2: now < deadline instead of now <= deadline"),
    ("A2_NONCE_SKIP", "A2: replay not checked"),
    ("A2_NONCE_NOT_MARKED", "A2/E4: the nonce is not marked used"),
    ("A3_SKIP", "A3: no binding check"),
    ("A3_CUSTOMER", "A3: auth.customer not compared"),
    ("A3_LINEAGE", "A3: auth.lineageId not compared"),
    ("A3_PRED", "A3: auth.predecessorId not compared"),
    ("A3_KIND", "A3: auth.kind not compared"),
    ("A3_TERMS", "A3: auth.newTermsHash not compared"),
    ("A3_ROUTER", "A3: auth.newRouter not compared"),
    ("A3_CODEHASH", "A3: auth.newRouterCodeHash not compared"),
    ("A3_VERSION", "A3: auth.newRouterVersion not compared"),
    ("A3_PIN", "A3: hashStruct(auth.accountPin) not compared"),
    ("A3_SNAPSHOT", "A3: auth.termsSnapshotHash not compared"),
    ("L1_SKIP", "L1: no lineage check"),
    ("L1_TERMINAL", "L1: terminal(P) (revoked or expired) not checked"),
    ("R1_SKIP", "R1: isBindable(Rnew) not checked"),
    ("R2_SKIP", "R2: no kind/router consistency check"),
    ("R2_SAME_ROUTER_OK", "R2: a migration to the same router is accepted"),
    ("R2_REVISION_ANY", "R2: a revision to a different router is accepted"),
    ("R3_SKIP", "R3: Mode(Rold) not enforced"),
    ("R3_STRICT", "R3: kind must equal the mode (EMERGENCY on a normal router refused)"),
    ("X1_SKIP", "X1: extensionsHash not checked"),
    ("K1_WF_SKIP", "K1 part 1: PIN_WELLFORMED(N.pin) not checked"),
    ("K1_OK_SKIP", "K1 part 2: PIN_OK(C, N.pin) not checked"),
    ("K1_VER_SKIP", "K1 part 3: pinVersion = nextPinVersion not checked"),
    ("G1_SKIP", "G1: new router funding not checked"),
    ("G1_EXPIRY_STRICT", "G1: now < e instead of now <= e"),
    ("G1_AMOUNT_GT", "G1: a > perPaymentMax instead of a >= perPaymentMax"),
    ("G1_FIRST_ONLY", "G1: only the first token of the new mandate is checked"),
    ("G1_EXPIRY_SKIP", "G1: expiration not checked"),
    ("X2_SKIP", "X2: exposure limit not checked"),
    ("X2_LT", "X2: count < MAX instead of count <= MAX"),
    ("X2_NO_UNION", "X2: only the tokens already exposed are counted, not the new mandate's tokens"),
    ("C1_SKIP", "C1: containment not checked"),
    ("C1_MASK_SKIP", "C1: auth.widenedMask = 0 not checked"),
    ("C1_K1_SKIP", "K.1 expiry not checked"),
    ("C1_K2_SKIP", "K.2 merchant scope not checked"),
    ("C1_K3_SKIP", "K.3 token scope not checked"),
    ("C1_K4_SKIP", "K.4 token caps not checked"),
    ("C1_K5_SKIP", "K.5 fiat caps and quote age not checked"),
    ("C1_K6_SKIP", "K.6 bounds version not checked"),
    ("C1_K7_SKIP", "K.7 cadence not checked"),
    ("C1_K8_SKIP", "K.8 fee cap not checked"),
    ("C1_K9_SKIP", "K.9 extensions not checked"),
    ("C1_K1_STRICT", "K.1 with < instead of <="),
    ("C1_K4_STRICT", "K.4 with < instead of <="),
    ("C1_K8_STRICT", "K.8 with < instead of <="),
    ("C1_E_INF_MAX", "E(0) is taken as uint256 max instead of infinity"),
    ("C2_CONST_SKIP", "C2: lineage constants not compared"),
    ("C2_MASK_SKIP", "C2: widenedMask not compared with the computed one"),
    ("O1N_SKIP", "O1N: not checked"),
    ("O1N_ZERO_SKIP", "O1N first half: Sib = 0 => Unusable not enforced"),
    ("O1N_BOUNDED_SKIP", "O1N second half: Sib > 0 => Bounded not enforced"),
    ("O1N_SIB_LIVE", "O1N: Sib = live instead of live - 1 (the predecessor counted as its own sibling)"),
    ("U_STRICT", "Usable: now < e instead of now <= e (expiration = now counted as unusable)"),
    ("U_NO_UNLIM", "Usable: the uint160.max sentinel counted as unusable"),
    ("U_EXPIRY_ONLY", "Usable: the amount is ignored (a = 0 with a future expiration counted as usable)"),
    ("O1E_SKIP", "O1E: not checked"),
    ("O1E_PRED_ONLY", "O1E: only the predecessor's tokens, not every exposed token"),
    ("MODE_SEC_NORMAL", "Mode: DEPRECATED with reason SECURITY treated as NORMAL"),
    ("MODE_DISABLED_NORMAL", "Mode: DISABLED_EMERGENCY treated as NORMAL"),
    ("MODE_SUNSET_NORMAL", "Mode: SUNSET and RETIRED treated as NORMAL"),
    ("BIND_DEPR_ALWAYS", "isBindable: DEPRECATED always bindable (rollback window ignored)"),
    ("BIND_WINDOW_LE", "isBindable: now <= deprecatedAt + window instead of <"),
    ("REG_NOTICE_SKIP", "registry: minimum notice not enforced at deprecation"),
    ("REG_SUNSET_EARLY", "registry: sunset allowed before sunsetNotBefore"),
    ("REG_RETIRE_EARLY", "registry: retire allowed before RETENTION"),
    ("E1_SKIP", "E1: the predecessor is not revoked"),
    ("E1_REASON", "E1: wrong revocation reason"),
    ("E2_SKIP", "E2: lineage.activeMandateId not updated"),
    ("E3_PAUSE_DROP", "E3: pause bits not inherited"),
    ("E6_SKIP_DEC", "E6: no decrement on the old router"),
    ("E6_SKIP_INC", "E6: no increment on the new router"),
    ("E6_INC_TWO", "E6: increment by two (off by one)"),
    ("E6_DEC_FIRST_ONLY", "E6: only the first predecessor token is decremented"),
    ("CNT_RESET", "I-MIG-3: the successor resets the lineage counters"),
    ("ACT_NO_INC", "activate: exposure not incremented"),
    ("ACT_X2_SKIP", "activate: exposure limit not checked"),
    ("ACT_WF_SKIP", "activate: PIN_WELLFORMED not checked"),
    ("ACT_OK_SKIP", "activate: PIN_OK not checked"),
    ("ACT_VER_SKIP", "activate: pinVersion = 1 not checked"),
    ("ACT_BIND_SKIP", "activate: router bindability not checked"),
    ("REV_NO_DEC", "revoke: exposure not decremented"),
    ("RET_NO_DEC", "retire: exposure not decremented"),
    ("RET_ANYTIME", "retire: allowed for an unexpired mandate"),
    ("RED_NO_DEC", "reduce: exposure not decremented"),
    ("UPD_VER_SKIP", "updateAccountPin: pinVersion = old + 1 not checked"),
    ("UPD_OK_SKIP", "updateAccountPin: PIN_OK not checked"),
    ("UPD_WF_SKIP", "updateAccountPin: PIN_WELLFORMED not checked"),
    ("UPD_AUTH_SKIP", "updateAccountPin: caller not authenticated"),
    ("CON_PINHASH_SKIP", "consume: hashStruct(pin) = accountPinHash not checked"),
    ("CON_PINOK_SKIP", "consume: PIN_OK not checked"),
    ("CON_ROUTER_SKIP", "consume: caller must be the bound router (not checked)"),
    ("CON_ACTIVE_SKIP", "consume: the mandate must be ACTIVE and the lineage's active one (not checked)"),
    ("CON_PAUSE_SKIP", "consume: pause bits not checked"),
    ("CON_TIME_SKIP", "consume: expiry not checked"),
    ("CON_SETTLE_SKIP", "consume: cycle settled once (not checked)"),
    ("CON_TOTAL_SKIP", "consume: lineage total cap not checked"),
    ("CON_PERPAY_SKIP", "consume: per-payment cap not checked"),
    ("CON_CHARGEABLE_SKIP", "consume: router chargeable (registry) not checked"),
    ("PW_VER0", "PIN_WELLFORMED: pinVersion >= 1 not required"),
    ("PW_MODE_RANGE", "PIN_WELLFORMED: accountMode in {1,2,3,4} not required"),
    ("PW_M1_CODE", "PIN_WELLFORMED mode 1: accountCodeHash = PIN_EOA not required"),
    ("PW_M1_DELEGATE", "PIN_WELLFORMED mode 1: delegate = 0 and delegateCodeHash = 0 not required"),
    ("PW_M1_FAMILY", "PIN_WELLFORMED mode 1: family = 0 not required"),
    ("PW_M1_SIG", "PIN_WELLFORMED mode 1: signatureMode in {0,1} not required"),
    ("PW_M2_DELEGATE0", "PIN_WELLFORMED mode 2: delegate != 0 not required"),
    ("PW_M2_CODE", "PIN_WELLFORMED mode 2: accountCodeHash = keccak256(0xef0100 || delegate) not required"),
    ("PW_M2_DCODE", "PIN_WELLFORMED mode 2: delegateCodeHash not in {0, KECCAK_EMPTY} not required"),
    ("PW_M2_FAMILY", "PIN_WELLFORMED mode 2: family != 0 not required"),
    ("PW_M34_DELEGATE", "PIN_WELLFORMED modes 3,4: delegate = 0 and delegateCodeHash = 0 not required"),
    ("PW_M34_CODE", "PIN_WELLFORMED modes 3,4: accountCodeHash not in {0, KECCAK_EMPTY, PIN_EOA} not required"),
    ("PW_M34_FAMILY", "PIN_WELLFORMED modes 3,4: family != 0 not required"),
    ("PW_M34_SIG", "PIN_WELLFORMED modes 3,4: signatureMode in {0,2} not required"),
    ("PO_M1_EMPTY_ONLY", "PIN_OK mode 1: only h = 0 accepted (KECCAK_EMPTY refused)"),
    ("PO_M1_KE_ONLY", "PIN_OK mode 1: only h = KECCAK_EMPTY accepted (0 refused)"),
    ("PO_M2_NO_DELEGATE", "PIN_OK mode 2: the delegate's code hash is not compared"),
    ("PO_M2_NO_ACCOUNT", "PIN_OK mode 2: the account's code hash is not compared"),
    ("PO_M34_SKIP", "PIN_OK modes 3,4: the account's code hash is not compared"),
    ("NV_SUCC_ALWAYS", "nextPinVersion: a successor always increments"),
    ("NV_SUCC_NEVER", "nextPinVersion: a successor never increments"),
    ("NV_UPDATE_SAME", "nextPinVersion: updateAccountPin keeps the version"),
    ("Q1_TOMB_SKIP", "Q1: removedAt(signer) = 0 not required"),
    ("Q1_MEMBER_SKIP", "Q1: membership in the named set not required"),
    ("Q13_STOP_SKIP", "Q13: stopped flag not checked"),
    ("Q13_ACTIVE_SKIP", "Q13: activeFrom <= issuedAt not required"),
    ("Q13_ISSUED_LE", "Q13: issuedAt <= retiredAt instead of issuedAt < retiredAt"),
    ("Q13_GRACE_LT", "Q13: now < retiredAt + GRACE instead of now <= retiredAt + GRACE"),
    ("Q13_GRACE_SKIP", "Q13: the grace limit is not enforced (retired sets stay valid for earlier quotes)"),
    ("SS_PROPOSE_TOMB_SKIP", "proposeSignerSet: tombstoned keys accepted"),
    ("SS_ACTIVATE_TOMB_SKIP", "activateSignerSet: tombstones not re-checked"),
    ("SS_GUARDIAN_PROPOSE", "proposeSignerSet: the guardian may propose"),
    ("SS_GUARDIAN_ACTIVATE", "activateSignerSet: the guardian may activate"),
    ("SS_ROTATE_NO_RETIRE", "rotation: the old set is not retired"),
    ("Q9_SKIP", "Q9: issuedAt <= validAfter <= validUntil not checked"),
    ("Q10_STRICT", "Q10: validAfter < now instead of validAfter <= now"),
    ("Q11_STRICT", "Q11: now < validUntil instead of now <= validUntil"),
    ("Q12_LT", "Q12: validUntil - issuedAt < min(...) instead of <="),
    ("CYC_LT", "G9: cycleIndex < currentIndex(now) instead of <="),
    ("WIN_OFFBYONE", "windows: the index is computed from now - anchor + 1"),
    ("BATCH_GE", "MAX_BATCH: n >= MAX_BATCH refused instead of n > MAX_BATCH"),
]
MUTANTS = [(i + 1, n, d) for i, (n, d) in enumerate(_MUTANT_TABLE)]
MUT = {n: i for i, n, _d in MUTANTS}
MUTANT_NAME = {i: n for i, n, _d in MUTANTS}
assert len(MUT) == len(MUTANTS)


# ----------------------------------------------------------------------------------------------------------------- small helpers
class Clock:
    def __init__(self, now=0):
        self.now = now


def eff(x):
    return INF if x == 0 else x


def narrow(x, bits, name):
    """Never truncate silently: a value above the width reverts (the Solidity WidthLib does the same)."""
    if x < 0 or x >> bits:
        raise Revert("UnsafeCast", 0)
    return x


def add_checked(a, b):
    s = a + b
    if s > UINT256_MAX:
        raise Revert("Panic", 0x11)
    return s


def inc_uint32(x):
    if x + 1 > UINT32_MAX:
        raise Revert("Panic", 0x11)
    return x + 1


def dec_uint32(x):
    if x == 0:
        raise Revert("Panic", 0x11)
    return x - 1


@dataclasses.dataclass
class Pin:
    accountMode: int = 0
    accountCodeHash: int = 0
    delegate: int = 0
    delegateCodeHash: int = 0
    implementationFamily: int = 0
    pinVersion: int = 0
    signatureMode: int = 0

    def clone(self):
        return dataclasses.replace(self)

    def struct_hash(self) -> int:
        return _pin_hash(dataclasses.astuple(self))

    def key(self):
        return dataclasses.astuple(self)


@functools.lru_cache(maxsize=None)
def _pin_hash(key) -> int:
    mode, code, delegate, dcode, family, version, sig = key
    return h2i(V.pin_struct_hash(dict(accountMode=mode, accountCodeHash=i2b(code), delegate=addr_hex(delegate),
                                      delegateCodeHash=i2b(dcode), implementationFamily=i2b(family), pinVersion=version,
                                      signatureMode=sig)))


@functools.lru_cache(maxsize=None)
def _example_pin_key(name: str):
    p = V.example_pins()[name]
    return (p["accountMode"], h2i(p["accountCodeHash"]), int(p["delegate"], 16), h2i(p["delegateCodeHash"]),
            h2i(p["implementationFamily"]), p["pinVersion"], p["signatureMode"])


def example_pin(name: str) -> Pin:
    return Pin(*_example_pin_key(name))


@functools.lru_cache(maxsize=None)
def _pin_1271_key():
    return (4, h2i(V.keccak256(b"fastpay-test-wallet1271-code-v1")), 0, 0, h2i(V.keccak256(b"test-wallet/1271/1")), 1, SM_ERC1271)


def pin_1271() -> Pin:
    """A WALLET_1271 pin (mode 4) for the vectors; the three example pins of document 17 do not include one."""
    return Pin(*_pin_1271_key())


@functools.lru_cache(maxsize=None)
def designator_hash_int(delegate: int) -> int:
    return h2i(V.designator_hash(addr_hex(delegate)))


FAMILY_NAMES = ("perPaymentMax", "totalMax", "dayMax", "weekMax", "thirtyDayMax", "periodMax")       # the order of the model arrays (`caps[t]`, `fiat`), not the typed order
FIAT_NAMES = ("fiatPerPaymentMax", "fiatTotalMax", "fiatDayMax", "fiatWeekMax", "fiatThirtyDayMax", "fiatPeriodMax")


@dataclasses.dataclass
class Terms:
    """The static terms of a mandate (the migration snapshot terms of document 12 section 5.3.2, without the ids)."""
    expiresAt: int = 0
    merchantId: int = 0
    recipientPolicy: int = 0
    subscriptionRef: int = 0
    periodSeconds: int = 0
    anchorStartsAt: int = 0
    currency: int = 0
    tokens: list = dataclasses.field(default_factory=list)            # sorted, unique, at most 3
    caps: dict = dataclasses.field(default_factory=dict)              # token -> [perPaymentMax, totalMax, day, week, thirtyDay, period]
    fiat: list = dataclasses.field(default_factory=lambda: [0] * 6)   # same family order
    maxQuoteAge: int = 0
    boundsVersion: int = 0                                            # the price band of (token, currency, boundsVersion) is read from the registry (ADR-020)
    maxChargesPerPeriod: int = 0
    minInterval: int = 0
    maxFeeBps: int = 0
    extensionsHash: int = 0

    def clone(self):
        c = dataclasses.replace(self)
        c.tokens = list(self.tokens)
        c.caps = {t: list(v) for t, v in self.caps.items()}
        c.fiat = list(self.fiat)
        return c

    def key(self):
        return (self.expiresAt, self.merchantId, self.recipientPolicy, self.subscriptionRef, self.periodSeconds, self.anchorStartsAt,
                self.currency, tuple(self.tokens), tuple((t, tuple(self.caps[t])) for t in self.tokens), tuple(self.fiat),
                self.maxQuoteAge, self.boundsVersion, self.maxChargesPerPeriod, self.minInterval, self.maxFeeBps,
                self.extensionsHash)


def token_addr(i: int) -> int:
    return 0x7000 + i


def base_terms(tokens=(1,)) -> Terms:
    """The base terms every scenario starts from (the Solidity VM has the same presets)."""
    t = Terms(expiresAt=1_900_000_000, merchantId=0xA1, recipientPolicy=0xB1, subscriptionRef=0xC1, periodSeconds=2_592_000,
              anchorStartsAt=1_800_000_000, currency=840, maxQuoteAge=120, boundsVersion=1, maxChargesPerPeriod=1,
              minInterval=86_400, maxFeeBps=100, extensionsHash=0)
    for i in sorted(tokens):
        t.tokens.append(token_addr(i))
        t.caps[token_addr(i)] = [50, 1000, 0, 0, 500, 0]
    return t


def terms_to_typed(t: Terms) -> dict:
    """The value of the typed `MandateTerms` struct of eip712/types.json for the model terms. The model keeps its arrays in the order
    perPayment, total, day, week, thirtyDay, period; the typed data (and the snapshot hash) use perPaymentMax, dayMax, weekMax,
    thirtyDayMax, periodMax, totalMax (findings F-06, F-07). The tokens keep the model order (ascending addresses)."""
    def tok(x):
        c = t.caps[x]
        return dict(token=addr_hex(x), perPaymentMax=c[0], dayMax=c[2], weekMax=c[3], thirtyDayMax=c[4], periodMax=c[5], totalMax=c[1])
    f = t.fiat
    return dict(merchantId=i2b(t.merchantId), recipientPolicy=i2b(t.recipientPolicy), subscriptionRef=i2b(t.subscriptionRef),
                periodSeconds=t.periodSeconds, anchorStartsAt=t.anchorStartsAt, expiresAt=t.expiresAt, tokens=[tok(x) for x in t.tokens],
                fiat=dict(currency=t.currency, perPaymentMaxMinor=f[0], dayMaxMinor=f[2], weekMaxMinor=f[3], thirtyDayMaxMinor=f[4],
                          periodMaxMinor=f[5], totalMaxMinor=f[1], maxQuoteAge=t.maxQuoteAge, boundsVersion=t.boundsVersion),
                maxChargesPerPeriod=t.maxChargesPerPeriod, minIntervalSeconds=t.minInterval, maxFeeBps=t.maxFeeBps,
                extensionsHash=i2b(t.extensionsHash))


_REGISTRY = []
_SNAP_CACHE = {}
_TERMS_CACHE = {}


def _typed_registry():
    if not _REGISTRY:
        _REGISTRY.append(ET.Registry(ET.load()))
    return _REGISTRY[0]


def snapshot_hash_int(t: Terms, lineage_id=0, predecessor_id=0, generation=0, customer=0) -> int:
    """termsSnapshotHash: keccak256 of the 26 words of eip712/types.json snapshotEncoding (tools/eip712_vectors.snapshot_hash), for the
    snapshot of a mandate with these ids, generation, customer and terms (memoized: the pure Python Keccak costs milliseconds)."""
    k = (t.key(), lineage_id, predecessor_id, generation, customer)
    v = _SNAP_CACHE.get(k)
    if v is None:
        v = _SNAP_CACHE[k] = h2i(V.snapshot_hash(i2b(lineage_id), i2b(predecessor_id), generation, addr_hex(customer), terms_to_typed(t)))
    return v


def terms_hash_int(t: Terms) -> int:
    """newTermsHash of a successor authorization: hashStruct(MandateTerms) of the new terms (the typed-data definition, document 12
    predicate A3), built with the generic encoder of tools/eip712_types.py from eip712/types.json."""
    k = t.key()
    v = _TERMS_CACHE.get(k)
    if v is None:
        v = _TERMS_CACHE[k] = h2i(_typed_registry().hash_struct("MandateTerms", terms_to_typed(t)))
    return v


@functools.lru_cache(maxsize=None)
def lineage_id_of(customer, merchant_id, subscription_ref, creation_nonce) -> int:
    return h2i(V.lineage_id(CHAIN_ID, addr_hex(MANAGER_ADDRESS), addr_hex(customer), i2b(merchant_id), i2b(subscription_ref),
                            creation_nonce))


@functools.lru_cache(maxsize=None)
def mandate_id_of(lineage_id, generation) -> int:
    return h2i(V.mandate_id(i2b(lineage_id), generation))


# ----------------------------------------------------------------------------------------------------------------- containment
K_NAMES = ["K.1 expiry", "K.2 merchant scope", "K.3 token scope", "K.4 caps", "K.5 fiat caps", "K.6 price band", "K.7 cadence",
           "K.8 fee cap", "K.9 extensions"]


def contained_mask(succ: Terms, snap: Terms, mut=0) -> int:
    """Containment of a migration successor in the snapshot of its predecessor (document 12 section 5.3.2).
    Returns a bit mask: bit k-1 is set when clause K.k is violated (0 means contained)."""
    def skip(n):
        return mut == MUT["C1_K%d_SKIP" % n]

    def le(a, b):                                   # E(a) <= E(b)
        if mut == MUT["C1_E_INF_MAX"]:
            a = UINT256_MAX if a == 0 else a
            b = UINT256_MAX if b == 0 else b
            return a <= b
        return eff(a) <= eff(b)

    m = 0
    if not skip(1):
        bad = succ.expiresAt >= snap.expiresAt if mut == MUT["C1_K1_STRICT"] else succ.expiresAt > snap.expiresAt
        if bad:
            m |= 1
    if not skip(2):
        if (succ.merchantId != snap.merchantId or succ.recipientPolicy != snap.recipientPolicy or succ.subscriptionRef != snap.subscriptionRef
                or succ.periodSeconds != snap.periodSeconds or succ.anchorStartsAt != snap.anchorStartsAt):
            m |= 1 << 1
    if not skip(3):
        if not set(succ.tokens) <= set(snap.tokens):
            m |= 1 << 2
    if not skip(4):
        for t in succ.tokens:
            if t not in snap.caps:
                continue
            for f in range(6):
                if mut == MUT["C1_K4_STRICT"]:
                    bad = not eff(succ.caps[t][f]) < eff(snap.caps[t][f])
                else:
                    bad = not le(succ.caps[t][f], snap.caps[t][f])
                if bad:
                    m |= 1 << 3
    if not skip(5):
        if succ.currency != snap.currency or succ.maxQuoteAge > snap.maxQuoteAge:
            m |= 1 << 4
        for f in range(6):
            if not le(succ.fiat[f], snap.fiat[f]):
                m |= 1 << 4
    if not skip(6):
        if succ.boundsVersion != snap.boundsVersion:              # a migration keeps the version; any change needs a REVISION
            m |= 1 << 5
    if not skip(7):
        if not le(succ.maxChargesPerPeriod, snap.maxChargesPerPeriod) or succ.minInterval < snap.minInterval:
            m |= 1 << 6
    if not skip(8):
        bad = succ.maxFeeBps >= snap.maxFeeBps if mut == MUT["C1_K8_STRICT"] else succ.maxFeeBps > snap.maxFeeBps
        if bad:
            m |= 1 << 7
    if not skip(9):
        if succ.extensionsHash != 0 or snap.extensionsHash != 0:
            m |= 1 << 8
    return m


def widened_mask(new: Terms, snap: Terms) -> int:
    """widenedMask (document 12 section 5.6): which dimensions a REVISION grows. Bits: 0 expiry later, 1 token added,
    2 per-payment cap higher, 3 a window cap higher or removed, 4 total cap higher or removed, 5 fiat cap higher or removed,
    6 quote age longer or bounds version changed (the band of a version never changes, so any other version is conservatively a
    widening), 7 more charges per period or shorter interval, 8 higher fee cap.
    Caps are compared for tokens present on both sides (a new token is bit 1 only)."""
    m = 0
    if new.expiresAt > snap.expiresAt:
        m |= 1
    if not set(new.tokens) <= set(snap.tokens):
        m |= 1 << 1
    for t in new.tokens:
        if t not in snap.caps:
            continue
        if eff(new.caps[t][0]) > eff(snap.caps[t][0]):
            m |= 1 << 2
        if any(eff(new.caps[t][f]) > eff(snap.caps[t][f]) for f in (2, 3, 4, 5)):
            m |= 1 << 3
        if eff(new.caps[t][1]) > eff(snap.caps[t][1]):
            m |= 1 << 4
    if any(eff(new.fiat[f]) > eff(snap.fiat[f]) for f in range(6)):
        m |= 1 << 5
    if new.maxQuoteAge > snap.maxQuoteAge or new.boundsVersion != snap.boundsVersion:
        m |= 1 << 6
    if eff(new.maxChargesPerPeriod) > eff(snap.maxChargesPerPeriod) or new.minInterval < snap.minInterval:
        m |= 1 << 7
    if new.maxFeeBps > snap.maxFeeBps:
        m |= 1 << 8
    return m


def lineage_constants_equal(a: Terms, b: Terms) -> bool:
    return (a.merchantId == b.merchantId and a.subscriptionRef == b.subscriptionRef and a.periodSeconds == b.periodSeconds
            and a.anchorStartsAt == b.anchorStartsAt and a.recipientPolicy == b.recipientPolicy and a.currency == b.currency)


# ---- the model registry of price bands (ADR-020, finding F-09): the band of (token, currency, boundsVersion) never changes once published
BOUNDS_BANDS = {1: (98, 102), 2: (95, 105), 3: (96, 104), 4: (94, 106), 5: (90, 110)}
EMPTY_BAND = (1, 0)


def band(version):
    """(lo, hi) of a bounds version in the model registry (it stands for the registry content). Version 0 and every unpublished
    version have the empty band (1, 0): no price is in it, so a charge that needs a price fails closed."""
    return BOUNDS_BANDS.get(version, EMPTY_BAND)


# ---- the mandate-dependent guards of a charge (document 11 section 4.8, 12 section 5.3.3), used by Lemma M
def accepts(m, state, p):
    """Acc(m, S, p). `m` is a snapshot-style dict (the shape of tools/model_checks.py), not a Terms object. The price must be inside the
    band of the mandate's bounds version."""
    t = p["token"]
    if p["tau"] >= m["expiresAt"] or t not in m["tokens"] or p["merchant"] != m["merchantId"]:
        return False
    c = m["caps"][t]
    if p["a"] > V.eff(c["perPaymentMax"]):
        return False
    used = state["used"][t]
    for f in ("dayMax", "weekMax", "thirtyDayMax", "periodMax", "totalMax"):
        if add_checked(used[f], p["a"]) > V.eff(c[f]):
            return False
    if p["fiat"] is not None:
        fu = state["fiatUsed"]
        if p["fiat"] > V.eff(m["fiatPerPaymentMax"]):
            return False
        for f in ("fiatDayMax", "fiatWeekMax", "fiatThirtyDayMax", "fiatPeriodMax", "fiatTotalMax"):
            if add_checked(fu[f], p["fiat"]) > V.eff(m[f]):
                return False
        lo, hi = band(m["boundsVersion"])
        if p["age"] > m["maxQuoteAge"] or not (lo <= p["price"] <= hi):
            return False
    if state["chargesInPeriod"] + 1 > V.eff(m["maxChargesPerPeriod"]) or p["sinceLast"] < m["minInterval"]:
        return False
    if p["feeBps"] > m["maxFeeBps"]:
        return False
    return m["extensionsHash"] == bytes(32)


# ----------------------------------------------------------------------------------------------------------------- Permit2
@dataclasses.dataclass
class Allowance:
    amount: int = 0
    expiration: int = 0
    nonce: int = 0


def usable(amount, expiration, now, mut=0):
    """Usable(C,t,R): a > 0 and now <= e (Permit2 reverts AllowanceExpired only when block.timestamp > expiration).
    uint160.max is unlimited and counts as usable."""
    if mut == MUT["U_STRICT"]:
        return amount > 0 and now < expiration
    if mut == MUT["U_NO_UNLIM"]:
        return 0 < amount < UINT160_MAX and now <= expiration
    if mut == MUT["U_EXPIRY_ONLY"]:
        return now <= expiration
    return amount > 0 and now <= expiration


class Permit2Model:
    """allowance[owner][token][spender] = (amount: uint160, expiration: uint48, nonce: uint48), as AllowanceTransfer.sol at
    cc306b601f172c51bc04334a109e98340456620b. `permit` is out of scope except as a re-grant (`permit_regrant`: the same write as a
    signed permit that passes its signature checks)."""

    def __init__(self, clock):
        self.clock = clock
        self.a = {}

    def get(self, owner, token, spender) -> Allowance:
        return self.a.get((owner, token, spender), Allowance())

    def _slot(self, owner, token, spender) -> Allowance:
        return self.a.setdefault((owner, token, spender), Allowance())

    def _read(self, owner, token, spender) -> Allowance:
        """The stored slot, or a zero slot that is NOT stored (a failed call must leave no entry behind)."""
        return self.a.get((owner, token, spender)) or Allowance()

    def approve(self, owner, token, spender, amount, expiration):
        if amount > UINT160_MAX or expiration > UINT48_MAX:
            raise Revert("AbiOutOfRange")
        s = self._slot(owner, token, spender)
        s.expiration = self.clock.now & UINT48_MAX if expiration == 0 else expiration      # F5: 0 stores block.timestamp
        s.amount = amount                                                                    # F2: overwrite

    def permit_regrant(self, owner, token, spender, amount, expiration, nonce):
        if amount > UINT160_MAX or expiration > UINT48_MAX or nonce > UINT48_MAX:
            raise Revert("AbiOutOfRange")
        if self._read(owner, token, spender).nonce != nonce:
            raise Revert("InvalidNonce")
        s = self._slot(owner, token, spender)
        s.amount = amount
        s.expiration = self.clock.now & UINT48_MAX if expiration == 0 else expiration
        s.nonce = (nonce + 1) & UINT48_MAX

    def lockdown(self, owner, pairs):
        for token, spender in pairs:
            self._slot(owner, token, spender).amount = 0                                     # F3: amount only

    def invalidate_nonces(self, owner, token, spender, new_nonce):
        if new_nonce > UINT48_MAX:
            raise Revert("AbiOutOfRange")
        cur = self._read(owner, token, spender)
        if new_nonce <= cur.nonce:
            raise Revert("InvalidNonce")
        if new_nonce - cur.nonce > 0xFFFF:
            raise Revert("ExcessiveInvalidation")
        self._slot(owner, token, spender).nonce = new_nonce

    def transfer_from(self, spender, owner, token, amount):
        """_transfer: reverts AllowanceExpired iff block.timestamp > expiration, then InsufficientAllowance; uint160.max is
        never decremented (F4)."""
        if amount > UINT160_MAX:
            raise Revert("AbiOutOfRange")
        s = self._read(owner, token, spender)
        if self.clock.now > s.expiration:
            raise Revert("AllowanceExpired", s.expiration)
        if s.amount != UINT160_MAX:
            if amount > s.amount:
                raise Revert("InsufficientAllowance", s.amount)
            self._slot(owner, token, spender).amount = s.amount - amount

    def can_transfer(self, spender, owner, token, amount):
        s = self.get(owner, token, spender)
        return amount <= UINT160_MAX and self.clock.now <= s.expiration and (s.amount == UINT160_MAX or amount <= s.amount)

    def snapshot(self):
        """The non-zero allowances (a stored all-zero triple is the same as no entry)."""
        return {k: (v.amount, v.expiration, v.nonce) for k, v in sorted(self.a.items())
                if (v.amount, v.expiration, v.nonce) != (0, 0, 0)}


# ----------------------------------------------------------------------------------------------------------------- router registry
class RouterRegistryModel:
    def __init__(self, clock, mut=0):
        self.clock, self.mut = clock, mut
        self.state, self.reason, self.deprecated_at, self.sunset_not_before = {}, {}, {}, {}
        self.sunset_at, self.prev_state, self.code_hash, self.version = {}, {}, {}, {}

    def st(self, r):
        return self.state.get(r, ST_UNREGISTERED)

    def propose(self, router, code_hash, version):
        if self.st(router) != ST_UNREGISTERED:
            raise Revert("WrongRouterState")
        self.state[router], self.code_hash[router], self.version[router] = ST_CANDIDATE, code_hash, version

    def activate(self, router):
        if self.st(router) != ST_CANDIDATE:
            raise Revert("WrongRouterState")
        live = sum(1 for s in self.state.values() if s in (ST_ACTIVE, ST_DEPRECATED))
        if live >= MAX_LIVE_ROUTERS:
            raise Revert("TooManyLiveRouters")
        self.state[router] = ST_ACTIVE

    def register_active(self, router, code_hash, version):
        """propose + activate in one call (all or nothing, like the Solidity function)."""
        if self.st(router) != ST_UNREGISTERED:
            raise Revert("WrongRouterState")
        if sum(1 for x in self.state.values() if x in (ST_ACTIVE, ST_DEPRECATED)) >= MAX_LIVE_ROUTERS:
            raise Revert("TooManyLiveRouters")
        self.propose(router, code_hash, version)
        self.activate(router)

    def notice(self, reason):
        return MIN_NOTICE_SECURITY if reason == REASON_SECURITY else MIN_NOTICE_STANDARD

    def deprecate(self, router, successor, reason, sunset_not_before):
        now = self.clock.now
        if self.st(router) != ST_ACTIVE:
            raise Revert("WrongRouterState")
        if self.st(successor) != ST_ACTIVE or successor == router:
            raise Revert("SuccessorNotActive")
        if sunset_not_before == 0:
            sunset_not_before = now + self.notice(reason)
        if self.mut != MUT["REG_NOTICE_SKIP"] and sunset_not_before < now + self.notice(reason):
            raise Revert("NoticeTooShort")
        self.state[router], self.reason[router] = ST_DEPRECATED, reason
        self.deprecated_at[router], self.sunset_not_before[router] = now, sunset_not_before

    def emergency_disable(self, router):
        if self.st(router) not in (ST_ACTIVE, ST_DEPRECATED):
            raise Revert("WrongRouterState")
        self.prev_state[router] = self.state[router]
        self.state[router] = ST_DISABLED

    def clear_emergency(self, router):
        if self.st(router) != ST_DISABLED:
            raise Revert("WrongRouterState")
        self.state[router] = self.prev_state[router]

    def sunset(self, router):
        if self.st(router) != ST_DEPRECATED:
            raise Revert("WrongRouterState")
        if self.mut != MUT["REG_SUNSET_EARLY"] and self.clock.now < self.sunset_not_before[router]:
            raise Revert("NotYetSunset")
        self.state[router], self.sunset_at[router] = ST_SUNSET, self.clock.now

    def retire(self, router):
        if self.st(router) != ST_SUNSET:
            raise Revert("WrongRouterState")
        if self.mut != MUT["REG_RETIRE_EARLY"] and self.clock.now < self.sunset_at[router] + RETENTION:
            raise Revert("RetentionNotElapsed")
        self.state[router] = ST_RETIRED

    def is_bindable(self, router):
        s = self.st(router)
        if s == ST_ACTIVE:
            return True
        if s == ST_DEPRECATED:
            if self.mut == MUT["BIND_DEPR_ALWAYS"]:
                return True
            end = self.deprecated_at[router] + ROLLBACK_WINDOW
            return self.clock.now <= end if self.mut == MUT["BIND_WINDOW_LE"] else self.clock.now < end
        return False

    def is_chargeable(self, router):
        return self.st(router) in (ST_ACTIVE, ST_DEPRECATED)

    def mode(self, router):
        s = self.st(router)
        if s == ST_ACTIVE:
            return MODE_NORMAL
        if s == ST_DEPRECATED:
            if self.reason[router] == REASON_SECURITY and self.mut != MUT["MODE_SEC_NORMAL"]:
                return MODE_EMERGENCY
            return MODE_NORMAL
        if s == ST_DISABLED:
            return MODE_NORMAL if self.mut == MUT["MODE_DISABLED_NORMAL"] else MODE_EMERGENCY
        if s in (ST_SUNSET, ST_RETIRED):
            return MODE_NORMAL if self.mut == MUT["MODE_SUNSET_NORMAL"] else MODE_EMERGENCY
        return MODE_EMERGENCY                                                    # fail closed for anything else

    def snapshot(self):
        return tuple(sorted((r, s, self.reason.get(r, 0)) for r, s in self.state.items()))


# ----------------------------------------------------------------------------------------------------------------- pin functions
def pin_wellformed(p: Pin, mut=0) -> bool:
    """PIN_WELLFORMED(pin), document 17 section 5.2, as written (note: the predicate puts no bound on signatureMode for mode 2)."""
    def on(name):
        return mut != MUT[name]
    if on("PW_VER0") and p.pinVersion < 1:
        return False
    if on("PW_MODE_RANGE") and p.accountMode not in (1, 2, 3, 4):
        return False
    if p.accountMode == 1:
        if on("PW_M1_CODE") and p.accountCodeHash != PIN_EOA:
            return False
        if on("PW_M1_DELEGATE") and (p.delegate != 0 or p.delegateCodeHash != 0):
            return False
        if on("PW_M1_FAMILY") and p.implementationFamily != 0:
            return False
        if on("PW_M1_SIG") and p.signatureMode not in (0, 1):
            return False
    if p.accountMode == 2:
        if on("PW_M2_DELEGATE0") and p.delegate == 0:
            return False
        if on("PW_M2_CODE") and p.accountCodeHash != designator_hash_int(p.delegate):
            return False
        if on("PW_M2_DCODE") and p.delegateCodeHash in (0, KECCAK_EMPTY):
            return False
        if on("PW_M2_FAMILY") and p.implementationFamily == 0:
            return False
    if p.accountMode in (3, 4):
        if on("PW_M34_DELEGATE") and (p.delegate != 0 or p.delegateCodeHash != 0):
            return False
        if on("PW_M34_CODE") and p.accountCodeHash in (0, KECCAK_EMPTY, PIN_EOA):
            return False
        if on("PW_M34_FAMILY") and p.implementationFamily == 0:
            return False
        if on("PW_M34_SIG") and p.signatureMode not in (0, 2):
            return False
    return True


def pin_check(p: Pin, h: int, hd: int, mut=0) -> int:
    """PIN_OK(account, pin) with the first failing field: 0 = holds, 1 = ACCOUNT_CODE, 2 = DELEGATE_CODE.
    h = EXTCODEHASH(account), hd = EXTCODEHASH(pin.delegate)."""
    if p.accountMode == 1:
        if mut == MUT["PO_M1_EMPTY_ONLY"]:
            ok = h == 0
        elif mut == MUT["PO_M1_KE_ONLY"]:
            ok = h == KECCAK_EMPTY
        else:
            ok = h in (0, KECCAK_EMPTY)
        return 0 if ok else FIELD_ACCOUNT_CODE
    if p.accountMode == 2:
        if mut != MUT["PO_M2_NO_ACCOUNT"] and h != p.accountCodeHash:
            return FIELD_ACCOUNT_CODE
        if mut != MUT["PO_M2_NO_DELEGATE"] and hd != p.delegateCodeHash:
            return FIELD_DELEGATE_CODE
        return 0
    if p.accountMode in (3, 4):
        if mut != MUT["PO_M34_SKIP"] and h != p.accountCodeHash:
            return FIELD_ACCOUNT_CODE
        return 0
    return 0


def pin_ok(p: Pin, h: int, hd: int, mut=0) -> bool:
    return pin_check(p, h, hd, mut) == 0


NV_FIRST, NV_UPDATE, NV_SUCCESSOR = 0, 1, 2


def next_pin_version(kind, lineage_version, prev: Pin, p: Pin, mut=0) -> int:
    """nextPinVersion(L, pin): 1 for the first activation; L.pinVersion + 1 for updateAccountPin; P.pinVersion + [pin differs from
    P.pin in any field other than pinVersion] for a successor. uint32 arithmetic is checked (Panic 0x11 at 2^32 - 1 + 1)."""
    if kind == NV_FIRST:
        return 1
    if kind == NV_UPDATE:
        return lineage_version if mut == MUT["NV_UPDATE_SAME"] else inc_uint32(lineage_version)
    differs = (prev.accountMode, prev.accountCodeHash, prev.delegate, prev.delegateCodeHash, prev.implementationFamily,
               prev.signatureMode) != (p.accountMode, p.accountCodeHash, p.delegate, p.delegateCodeHash, p.implementationFamily,
                                       p.signatureMode)
    if mut == MUT["NV_SUCC_ALWAYS"]:
        differs = True
    if mut == MUT["NV_SUCC_NEVER"]:
        differs = False
    return inc_uint32(prev.pinVersion) if differs else prev.pinVersion


def auth_signature(sender_is_customer, sig_path, sig_ok, pin_ctx: Pin, h, hd, mut=0):
    """AUTH(C, digest, pinCtx), document 17 section 5.4: raises NotCustomer, SignatureModeNotPermitted or AccountCodeChanged."""
    if sender_is_customer:
        return
    if sig_path == SIG_NONE:
        raise Revert("NotCustomer")
    mode = pin_ctx.signatureMode
    if sig_path == SIG_ECDSA:
        allowed = mode == SM_ECDSA_KEY or (mut == MUT["AUTH_ECDSA_ANY"] and mode == SM_ERC1271) \
            or (mut == MUT["AUTH_DIRECT_ONLY_OK"] and mode == SM_DIRECT_ONLY)
        if not allowed:
            raise Revert("SignatureModeNotPermitted")
        if not sig_ok and mut != MUT["AUTH_SIGOK_SKIP"]:
            raise Revert("NotCustomer")
        return
    allowed = mode == SM_ERC1271 or (mut == MUT["AUTH_1271_ANY"] and mode == SM_ECDSA_KEY) \
        or (mut == MUT["AUTH_DIRECT_ONLY_OK"] and mode == SM_DIRECT_ONLY)
    if not allowed:
        raise Revert("SignatureModeNotPermitted")
    if mut != MUT["AUTH_1271_NOPIN"]:
        field = pin_check(pin_ctx, h, hd, mut)
        if field:
            raise Revert("AccountCodeChanged", field)
    if not sig_ok and mut != MUT["AUTH_SIGOK_SKIP"]:
        raise Revert("NotCustomer")


def auth_exit(sender_is_customer, sig_path, sig_ok, pin_ctx: Pin, mut=0):
    """revokeBySig and pauseBySig: accepted through either path whatever the mode (17 section 5.4 consequence 4)."""
    if sender_is_customer:
        return
    if sig_path == SIG_NONE:
        raise Revert("NotCustomer")
    if mut == MUT["AUTH_EXIT_GATED"] and pin_ctx.signatureMode == SM_DIRECT_ONLY:
        raise Revert("SignatureModeNotPermitted")
    if not sig_ok:
        raise Revert("NotCustomer")


# ----------------------------------------------------------------------------------------------------------------- manager
@dataclasses.dataclass
class Mandate:
    id: int
    lineage: int
    predecessor: int
    generation: int
    customer: int
    router: int
    terms: Terms
    pin: Pin
    status: int = MS_ACTIVE
    reason: int = RV_NONE
    retired: bool = False
    pause: int = 0
    parentSnapshotHash: int = 0

    def digest_key(self):
        return (self.id, self.lineage, self.predecessor, self.generation, self.customer, self.router, self.terms.key(), self.pin.key(),
                self.status, self.reason, self.retired, self.pause, self.parentSnapshotHash)


@dataclasses.dataclass
class Lineage:
    id: int
    customer: int
    active: int
    generation: int
    terminated: bool
    pinVersion: int
    mandate_ids: list = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class Auth:
    customer: int = 0
    lineageId: int = 0
    predecessorId: int = 0
    kind: int = 0
    newTermsHash: int = 0
    newRouter: int = 0
    newRouterCodeHash: int = 0
    newRouterVersion: int = 0
    termsSnapshotHash: int = 0
    widenedMask: int = 0
    accountPin: Pin = dataclasses.field(default_factory=Pin)
    deadline: int = 0
    nonce: int = 0


@dataclasses.dataclass
class Access:
    """How the call reaches the contract: msg.sender = customer, or a signature by the ECDSA key or through ERC-1271."""
    sender_is_customer: bool = True
    sig_path: int = SIG_NONE
    sig_ok: bool = False


class ManagerModel:
    def __init__(self, clock, reg: RouterRegistryModel, p2: Permit2Model, mut=0):
        self.clock, self.reg, self.p2, self.mut = clock, reg, p2, mut
        self.mandates, self.lineages = {}, {}
        self.live = {}
        self.exposed = {}
        self.used_nonce = set()
        self.codehash = {}
        self.used_total = {}
        self.cycle_settled = set()
        self.events = []

    # ---- helpers
    def on(self, name):
        return self.mut != MUT[name]

    def hit(self, name):
        return self.mut == MUT[name]

    def set_codehash(self, address, h):
        self.codehash[address] = h

    def code_of(self, address):
        return self.codehash.get(address, 0)

    def account_state(self, customer, pin):
        return self.code_of(customer), self.code_of(pin.delegate)

    def live_count(self, c, r, t):
        return self.live.get((c, r, t), 0)

    def exposed_list(self, c, r):
        return self.exposed.get((c, r), [])

    def _stage(self, changes):
        """Apply [(customer, router, token, +1 | -1), ...] to COPIES of the exposure index with checked uint32 arithmetic and
        return them. Nothing is written until `_commit`: a Panic in the middle must leave the index untouched, as a revert does."""
        live, exposed = dict(self.live), {}
        for c, r, t, delta in changes:
            n = live.get((c, r, t), 0)
            n = inc_uint32(n) if delta > 0 else dec_uint32(n)
            live[(c, r, t)] = n
            lst = exposed.get((c, r))
            if lst is None:
                lst = exposed[(c, r)] = list(self.exposed.get((c, r), []))
            if delta > 0 and n == 1:
                lst.append(t)
            if delta < 0 and n == 0:
                i = lst.index(t)
                lst[i] = lst[-1]                               # swap and pop, as the enumerable set of the Solidity model
                lst.pop()
        return live, exposed

    def _commit(self, staged):
        live, exposed = staged
        self.live = live
        for k, v in exposed.items():
            self.exposed[k] = v

    def seed_live(self, c, r, t, n):
        """Test-only: set a raw count (for the uint32 boundary vectors)."""
        self.live[(c, r, t)] = n
        lst = self.exposed.setdefault((c, r), [])
        if n > 0 and t not in lst:
            lst.append(t)

    def exposed_count_with(self, c, r, tokens):
        lst = self.exposed_list(c, r)
        extra = 0 if self.hit("X2_NO_UNION") else sum(1 for t in tokens if t not in lst)
        return len(lst) + extra

    def mandate(self, mid) -> Mandate:
        m = self.mandates.get(mid)
        if m is None:
            raise Revert("UnknownMandate")
        return m

    def terminal(self, m: Mandate) -> bool:
        return m.status != MS_ACTIVE or self.clock.now >= m.terms.expiresAt

    def snapshot_hash_of(self, m: Mandate) -> int:
        return snapshot_hash_int(m.terms, m.lineage, m.predecessor, m.generation, m.customer)

    def usable_now(self, c, t, r):
        a = self.p2.get(c, t, r)
        return usable(a.amount, a.expiration, self.clock.now, self.mut)

    # ---- activate
    def activate(self, customer, creation_nonce, router, terms: Terms, pin: Pin):
        h, hd = self.account_state(customer, pin)
        if self.on("ACT_BIND_SKIP") and not self.reg.is_bindable(router):
            raise Revert("RouterNotBindable")
        if terms.extensionsHash != 0:
            raise Revert("ExtensionsNotSupported")
        if self.on("ACT_WF_SKIP") and not pin_wellformed(pin, self.mut):
            raise Revert("AccountPinMalformed")
        if self.on("ACT_OK_SKIP") and not pin_ok(pin, h, hd, self.mut):
            raise Revert("AccountPinMismatch")
        if self.on("ACT_VER_SKIP") and pin.pinVersion != next_pin_version(NV_FIRST, 0, pin, pin, self.mut):
            raise Revert("PinVersionMismatch")
        if self.on("ACT_X2_SKIP") and self.exposed_count_with(customer, router, terms.tokens) > MAX_EXPOSED_TOKENS_PER_ROUTER:
            raise Revert("ExposureLimit")
        lid = lineage_id_of(customer, terms.merchantId, terms.subscriptionRef, creation_nonce)
        mid = mandate_id_of(lid, 0)
        if lid in self.lineages:
            raise Revert("WrongPredecessor")
        staged = self._stage([(customer, router, t, 1) for t in terms.tokens] if self.on("ACT_NO_INC") else [])
        self.lineages[lid] = Lineage(lid, customer, mid, 0, False, pin.pinVersion, [mid])
        self.mandates[mid] = Mandate(mid, lid, 0, 0, customer, router, terms.clone(), pin.clone())
        self._commit(staged)
        self.events.append(("MandateActivated", lid, mid))
        return lid, mid

    # ---- auth construction (what a correct client signs)
    def build_auth(self, predecessor_id, kind, new_router, new_terms: Terms, new_pin: Pin, deadline, nonce) -> Auth:
        P = self.mandate(predecessor_id)
        n_terms_hash = terms_hash_int(new_terms)
        mask = widened_mask(new_terms, P.terms) if kind == REVISION else 0
        return Auth(customer=P.customer, lineageId=P.lineage, predecessorId=P.id, kind=kind, newTermsHash=n_terms_hash,
                    newRouter=new_router, newRouterCodeHash=self.reg.code_hash.get(new_router, 0),
                    newRouterVersion=self.reg.version.get(new_router, 0), termsSnapshotHash=self.snapshot_hash_of(P),
                    widenedMask=mask, accountPin=new_pin.clone(), deadline=deadline, nonce=nonce)

    # ---- activateSuccessor
    def activate_successor(self, predecessor_id, kind, new_router, new_terms: Terms, new_pin: Pin, auth: Auth, access: Access):
        P = self.mandate(predecessor_id)
        L = self.lineages[P.lineage]
        C = P.customer
        now = self.clock.now
        Rold, Rnew = P.router, new_router
        hit = self.hit
        h, hd = self.account_state(C, P.pin)
        # A1 AUTH
        if not hit("A1_SKIP"):
            ctx = new_pin if hit("A1_PIN_FROM_NEW") else P.pin
            if hit("A1_PIN_FROM_NEW"):
                h, hd = self.account_state(C, ctx)
            auth_signature(access.sender_is_customer, access.sig_path, access.sig_ok, ctx, h, hd, self.mut)
        # A2 FRESH
        if not hit("A2_DEADLINE_SKIP"):
            late = now >= auth.deadline if hit("A2_DEADLINE_STRICT") else now > auth.deadline
            if late:
                raise Revert("AuthorizationExpired")
        if not hit("A2_NONCE_SKIP") and (C, auth.nonce) in self.used_nonce:
            raise Revert("AuthorizationReplayed")
        # A3 BIND
        if not hit("A3_SKIP"):
            n_terms_hash = terms_hash_int(new_terms)
            checks = [("A3_CUSTOMER", auth.customer == C), ("A3_LINEAGE", auth.lineageId == L.id),
                      ("A3_PRED", auth.predecessorId == P.id), ("A3_KIND", auth.kind == kind),
                      ("A3_TERMS", auth.newTermsHash == n_terms_hash), ("A3_ROUTER", auth.newRouter == Rnew),
                      ("A3_CODEHASH", auth.newRouterCodeHash == self.reg.code_hash.get(Rnew, 0)),
                      ("A3_VERSION", auth.newRouterVersion == self.reg.version.get(Rnew, 0)),
                      ("A3_PIN", auth.accountPin.struct_hash() == new_pin.struct_hash()),
                      ("A3_SNAPSHOT", auth.termsSnapshotHash == self.snapshot_hash_of(P))]
            for name, ok in checks:
                if not ok and not hit(name):
                    raise Revert("AuthorizationMismatch")
        # L1 LINEAGE
        if not hit("L1_SKIP"):
            # L.activeMandateId = P.id and not L.terminated are implied by "not terminal(P)" in every state E1/E2 can reach
            # (a superseded or revoked mandate is REVOKED); they are checked too, in the same error
            if L.active != P.id or L.terminated:
                raise Revert("WrongPredecessor")
            if not hit("L1_TERMINAL") and self.terminal(P):
                raise Revert("WrongPredecessor")
        # R1 BINDABLE
        if not hit("R1_SKIP") and not self.reg.is_bindable(Rnew):
            raise Revert("RouterNotBindable")
        # R2 KIND
        if kind > REVISION:
            raise Revert("WrongKind")
        if not hit("R2_SKIP"):
            if kind in (NORMAL, EMERGENCY) and Rnew == Rold and not hit("R2_SAME_ROUTER_OK"):
                raise Revert("WrongKind")
            if kind == REVISION and Rnew != Rold and not hit("R2_REVISION_ANY"):
                raise Revert("WrongKind")
        # R3 MODE (migration only)
        if kind in (NORMAL, EMERGENCY) and not hit("R3_SKIP"):
            mode = self.reg.mode(Rold)
            if hit("R3_STRICT"):
                if kind != mode:
                    raise Revert("ModeMismatch")
            elif mode == MODE_EMERGENCY and kind != EMERGENCY:
                raise Revert("ModeMismatch")
        # X1 EXT
        if not hit("X1_SKIP"):
            if new_terms.extensionsHash != 0 or P.terms.extensionsHash != 0:
                raise Revert("ExtensionsNotSupported")
        # K1 ACCOUNT
        h_new, hd_new = self.account_state(C, new_pin)
        if not hit("K1_WF_SKIP") and not pin_wellformed(new_pin, self.mut):
            raise Revert("AccountPinMalformed")
        if not hit("K1_OK_SKIP") and not pin_ok(new_pin, h_new, hd_new, self.mut):
            raise Revert("AccountPinMismatch")
        if not hit("K1_VER_SKIP"):
            if new_pin.pinVersion != next_pin_version(NV_SUCCESSOR, L.pinVersion, P.pin, new_pin, self.mut):
                raise Revert("PinVersionMismatch")
        # G1 NEWPERM
        if not hit("G1_SKIP"):
            toks = new_terms.tokens[:1] if hit("G1_FIRST_ONLY") else new_terms.tokens
            for t in toks:
                a = self.p2.get(C, t, Rnew)
                need = new_terms.caps[t][0]
                short = a.amount <= need if hit("G1_AMOUNT_GT") else a.amount < need
                if hit("G1_EXPIRY_SKIP"):
                    late = False
                elif hit("G1_EXPIRY_STRICT"):
                    late = now >= a.expiration
                else:
                    late = now > a.expiration
                if short or late:
                    raise Revert("NewPermissionMissing", t)
        # X2 EXPOSURE
        if not hit("X2_SKIP"):
            n = self.exposed_count_with(C, Rnew, new_terms.tokens)
            limit = MAX_EXPOSED_TOKENS_PER_ROUTER - (1 if hit("X2_LT") else 0)
            if n > limit:
                raise Revert("ExposureLimit")
        # C1 CONTAIN (migration) / C2 REVISE (revision)
        snap = P.terms
        if kind in (NORMAL, EMERGENCY):
            if not hit("C1_SKIP"):
                if contained_mask(new_terms, snap, self.mut) != 0:
                    raise Revert("TermsNotContained")
                if not hit("C1_MASK_SKIP") and auth.widenedMask != 0:
                    raise Revert("TermsNotContained")
        else:
            if not hit("C2_CONST_SKIP") and not lineage_constants_equal(new_terms, snap):
                raise Revert("LineageConstantsChanged")
            if not hit("C2_MASK_SKIP") and auth.widenedMask != widened_mask(new_terms, snap):
                raise Revert("WidenedMaskMismatch")
        # O1N / O1E
        if kind == NORMAL and not hit("O1N_SKIP"):
            for t in P.terms.tokens:
                live = self.live_count(C, Rold, t)
                sib = live if hit("O1N_SIB_LIVE") else dec_uint32(live)       # Sib = live - 1; Panic 0x11 if the index says 0
                a = self.p2.get(C, t, Rold)
                if sib == 0:
                    if not hit("O1N_ZERO_SKIP") and usable(a.amount, a.expiration, now, self.mut):
                        raise Revert("OldPermissionNotRevoked", t)
                else:
                    if not hit("O1N_BOUNDED_SKIP") and a.amount >= UINT160_MAX:
                        raise Revert("ResidualAllowanceUnbounded", t)
        if kind == EMERGENCY and not hit("O1E_SKIP"):
            toks = P.terms.tokens if hit("O1E_PRED_ONLY") else list(self.exposed_list(C, Rold))
            for t in toks:
                a = self.p2.get(C, t, Rold)
                if usable(a.amount, a.expiration, now, self.mut):
                    raise Revert("OldPermissionNotRevoked", t)
        # ---- effects (only if SuccessorOK); the exposure update can still revert (checked uint32), so it is staged first
        T, TN = list(P.terms.tokens), list(new_terms.tokens)
        changes = []
        if not hit("E6_SKIP_DEC"):
            changes += [(C, Rold, t, -1) for t in (T[:1] if hit("E6_DEC_FIRST_ONLY") else T)]
        if not hit("E6_SKIP_INC"):
            for t in TN:
                changes.append((C, Rnew, t, 1))
                if hit("E6_INC_TWO"):
                    changes.append((C, Rnew, t, 1))
        staged = self._stage(changes)
        gen = P.generation + 1
        nid = mandate_id_of(L.id, gen)
        if not hit("E1_SKIP"):
            P.status = MS_REVOKED
            P.reason = RV_SUPERSEDED_MIGRATION if kind != REVISION else RV_SUPERSEDED_REVISION
            if hit("E1_REASON"):
                P.reason = RV_CUSTOMER
        N = Mandate(nid, L.id, P.id, gen, C, Rnew, new_terms.clone(), new_pin.clone(), MS_ACTIVE, RV_NONE, False,
                    0 if hit("E3_PAUSE_DROP") else P.pause, auth.termsSnapshotHash)
        self.mandates[nid] = N
        L.mandate_ids.append(nid)
        L.generation = gen
        L.pinVersion = new_pin.pinVersion
        if not hit("E2_SKIP"):
            L.active = nid
        if not hit("A2_NONCE_NOT_MARKED"):
            self.used_nonce.add((C, auth.nonce))
        self._commit(staged)
        if hit("CNT_RESET"):
            for t in T:
                self.used_total[(L.id, t)] = 0
            self.cycle_settled = {x for x in self.cycle_settled if x[0] != L.id}
        self.events.append(("MandateSuperseded", L.id, P.id, nid, kind))
        return nid

    # ---- exits and housekeeping
    def revoke(self, mandate_id, sender_is_customer=True):
        m = self.mandate(mandate_id)
        if not sender_is_customer:
            raise Revert("NotCustomer")
        if m.status != MS_ACTIVE:
            raise Revert("MandateNotActive")
        staged = self._stage([(m.customer, m.router, t, -1) for t in m.terms.tokens] if (not m.retired and self.on("REV_NO_DEC")) else [])
        m.status, m.reason = MS_REVOKED, RV_CUSTOMER
        L = self.lineages[m.lineage]
        if L.active == m.id:
            L.terminated = True
        self._commit(staged)
        self.events.append(("MandateRevoked", m.lineage, m.id))

    def retire(self, mandate_id):
        m = self.mandate(mandate_id)
        if m.status != MS_ACTIVE or m.retired:
            raise Revert("NotRetirable")
        if self.on("RET_ANYTIME") and self.clock.now < m.terms.expiresAt:
            raise Revert("NotRetirable")
        staged = self._stage([(m.customer, m.router, t, -1) for t in m.terms.tokens] if self.on("RET_NO_DEC") else [])
        m.retired = True
        self._commit(staged)
        self.events.append(("MandateRetired", m.id))

    def reduce_drop_token(self, mandate_id, token):
        """A customer reduction that removes one token from a live mandate (a token-removing `reduce`)."""
        m = self.mandate(mandate_id)
        if m.status != MS_ACTIVE or m.retired:
            raise Revert("MandateNotActive")
        if token not in m.terms.tokens:
            raise Revert("TokenNotInMandate")
        if len(m.terms.tokens) == 1:
            raise Revert("NoTokensLeft")
        staged = self._stage([(m.customer, m.router, token, -1)] if self.on("RED_NO_DEC") else [])
        m.terms.tokens.remove(token)
        del m.terms.caps[token]
        self._commit(staged)

    def update_account_pin(self, mandate_id, new_pin: Pin, auth_deadline, auth_nonce, access: Access):
        """updateAccountPin (document 17 section 5.3): AUTH, then in the order of the document: mandate non-terminal, PIN_WELLFORMED,
        PIN_OK, newPin.pinVersion = old + 1, nonce unused, deadline not passed. It changes only the pin and the pin version."""
        m = self.mandate(mandate_id)
        C = m.customer
        h, hd = self.account_state(C, m.pin)
        if self.on("UPD_AUTH_SKIP"):
            auth_signature(access.sender_is_customer, access.sig_path, access.sig_ok, m.pin, h, hd, self.mut)
        if self.terminal(m):
            raise Revert("MandateNotActive")
        h_new, hd_new = self.account_state(C, new_pin)
        if self.on("UPD_WF_SKIP") and not pin_wellformed(new_pin, self.mut):
            raise Revert("AccountPinMalformed")
        if self.on("UPD_OK_SKIP") and not pin_ok(new_pin, h_new, hd_new, self.mut):
            raise Revert("AccountPinMismatch")
        L = self.lineages[m.lineage]
        if self.on("UPD_VER_SKIP") and new_pin.pinVersion != next_pin_version(NV_UPDATE, m.pin.pinVersion, m.pin, new_pin, self.mut):
            raise Revert("PinVersionMismatch")
        if (C, auth_nonce) in self.used_nonce:
            raise Revert("AuthorizationReplayed")
        if self.clock.now > auth_deadline:
            raise Revert("AuthorizationExpired")
        m.pin = new_pin.clone()
        L.pinVersion = new_pin.pinVersion
        self.used_nonce.add((C, auth_nonce))
        self.events.append(("AccountPinUpdated", m.id, new_pin.pinVersion))

    def set_pause(self, mandate_id, bit, on):
        """A pause bit (customer, risk, delegation). Pausing is an exit: never blocked."""
        m = self.mandate(mandate_id)
        m.pause = (m.pause | bit) if on else (m.pause & ~bit)

    # ---- consume (a charge by a router)
    def _consume_checks(self, router, mandate_id, token, amount, cycle_index, pin: Pin):
        """G1, G2, G3, G10, G4, G9, G5 in the order of document 11 section 5; returns (mandate, lineage, new total). No state change."""
        m = self.mandates.get(mandate_id)
        if m is None:
            raise Revert("UnknownMandate")
        L = self.lineages[m.lineage]
        C = m.customer
        if self.on("CON_ACTIVE_SKIP") and (m.status != MS_ACTIVE or L.active != m.id):
            raise Revert("MandateNotConsumable")
        if self.on("CON_PAUSE_SKIP") and m.pause != 0:
            raise Revert("MandateNotConsumable")
        if self.on("CON_TIME_SKIP") and self.clock.now >= m.terms.expiresAt:
            raise Revert("MandateNotConsumable")
        if self.on("CON_ROUTER_SKIP") and m.router != router:
            raise Revert("WrongRouter")
        if self.on("CON_CHARGEABLE_SKIP") and not self.reg.is_chargeable(router):
            raise Revert("RouterNotChargeable")
        h, hd = self.account_state(C, m.pin)
        if self.on("CON_PINHASH_SKIP") and pin.struct_hash() != m.pin.struct_hash():
            raise Revert("PinHashMismatch")
        if self.on("CON_PINOK_SKIP"):
            field = pin_check(pin, h, hd, self.mut)
            if field:
                raise Revert("AccountCodeChanged", field)
        if m.terms.extensionsHash != 0:
            raise Revert("ExtensionsNotSupported")
        if token not in m.terms.tokens:
            raise Revert("TokenNotInMandate")
        if self.on("CON_SETTLE_SKIP") and (L.id, cycle_index) in self.cycle_settled:
            raise Revert("PaymentAlreadySettled")
        caps = m.terms.caps[token]
        if self.on("CON_PERPAY_SKIP") and amount > eff(caps[0]):
            raise Revert("TokenPerPaymentCapExceeded")
        total = add_checked(self.used_total.get((L.id, token), 0), amount)
        if self.on("CON_TOTAL_SKIP") and total > eff(caps[1]):
            raise Revert("TokenTotalCapExceeded")
        if amount > UINT160_MAX:
            raise Revert("UnsafeCast")
        return m, L, total

    def consume(self, router, mandate_id, token, amount, cycle_index, pin: Pin):
        m, L, total = self._consume_checks(router, mandate_id, token, amount, cycle_index, pin)
        # interaction first (a revert of the Permit2 pull undoes everything), then the effects
        self.p2.transfer_from(router, m.customer, token, amount)
        self.used_total[(L.id, token)] = total
        self.cycle_settled.add((L.id, cycle_index))

    def would_charge(self, router, mandate_id, token, amount, cycle_index):
        """Dry run of consume (no state change): can this charge succeed right now?"""
        try:
            m, L, total = self._consume_checks(router, mandate_id, token, amount, cycle_index, self.mandates[mandate_id].pin)
            return self.p2.can_transfer(router, m.customer, token, amount)
        except Revert:
            return False

    # ---- views
    def consumable(self, m: Mandate, router) -> bool:
        L = self.lineages[m.lineage]
        h, hd = self.account_state(m.customer, m.pin)
        # document 12 section 5.3 defines Consumable without time; 5.1 defines the derived state ACTIVE as "within time", so the
        # model adds `not retired and now < expiresAt` (reported as a document issue)
        return (m.status == MS_ACTIVE and L.active == m.id and m.router == router and m.pause == 0
                and pin_ok(m.pin, h, hd) and not m.retired and self.clock.now < m.terms.expiresAt)

    def auth_routers(self, lineage_id, routers):
        """AuthRouters(L): routers that can pull under FastPay authority for the lineage right now (document 12 section 5.5)."""
        L = self.lineages[lineage_id]
        out = set()
        for mid in L.mandate_ids:
            m = self.mandates[mid]
            for r in routers:
                if self.consumable(m, r) and any(self.usable_now(m.customer, t, r) for t in m.terms.tokens):
                    out.add(r)
        return out

    def lineage_digest(self, lineage_id):
        L = self.lineages[lineage_id]
        usage = tuple(sorted((k[1], v) for k, v in self.used_total.items() if k[0] == lineage_id))
        cycles = tuple(sorted(x[1] for x in self.cycle_settled if x[0] == lineage_id))
        return (L.id, L.customer, L.active, L.generation, L.terminated, L.pinVersion, tuple(L.mandate_ids), usage, cycles)

    def mandate_digest(self, mandate_id):
        return self.mandates[mandate_id].digest_key()

    def exposure_recomputed(self):
        """The count of recorded-active mandates (status ACTIVE and not retired) per (customer, router, token)."""
        out = {}
        for m in self.mandates.values():
            if m.status == MS_ACTIVE and not m.retired:
                for t in m.terms.tokens:
                    out[(m.customer, m.router, t)] = out.get((m.customer, m.router, t), 0) + 1
        return out

    def exposure_true_live(self):
        """The true number of live mandates: recorded-active, not retired and not expired by time."""
        out = {}
        for m in self.mandates.values():
            if m.status == MS_ACTIVE and not m.retired and self.clock.now < m.terms.expiresAt:
                for t in m.terms.tokens:
                    out[(m.customer, m.router, t)] = out.get((m.customer, m.router, t), 0) + 1
        return out


# ----------------------------------------------------------------------------------------------------------------- time arithmetic
def quote_times_check(issued_at, valid_after, valid_until, max_age, registry_ttl, now, mut=0):
    """Q9..Q12 of document 11 section 4.2: the time checks of a quote."""
    if mut != MUT["Q9_SKIP"] and not (issued_at <= valid_after <= valid_until):
        raise Revert("QuoteTimesInvalid")
    if (valid_after >= now) if mut == MUT["Q10_STRICT"] else (valid_after > now):
        raise Revert("QuoteNotYetValid")
    if (now >= valid_until) if mut == MUT["Q11_STRICT"] else (now > valid_until):
        raise Revert("QuoteExpired")
    ttl = valid_until - issued_at                                   # valid_until >= issued_at after Q9 (checked arithmetic otherwise)
    if ttl < 0:
        raise Revert("Panic", 0x11)
    limit = min(max_age, registry_ttl)
    if (ttl >= limit) if mut == MUT["Q12_LT"] else (ttl > limit):
        raise Revert("QuoteTtlTooLong")


def window_index(now, anchor, length, mut=0):
    """The index of the window (or billing cycle) that contains `now`: floor((now - anchor) / length); checked arithmetic."""
    if now < anchor:
        raise Revert("Panic", 0x11)
    if length == 0:
        raise Revert("Panic", 0x12)
    return (now - anchor + (1 if mut == MUT["WIN_OFFBYONE"] else 0)) // length


def cycle_allowed(cycle_index, now, anchor, period, mut=0):
    """G9 and PC-16: cycleIndex <= floor((now - anchor) / periodSeconds); late cycles are allowed."""
    cur = window_index(now, anchor, period, mut)
    if (cycle_index >= cur) if mut == MUT["CYC_LT"] else (cycle_index > cur):
        raise Revert("CycleNotYetDue")


def batch_check(n, mut=0):
    """MAX_BATCH: at most MAX_BATCH successors per plan step (and mandates per pin batch), ADR-022."""
    if (n >= MAX_BATCH) if mut == MUT["BATCH_GE"] else (n > MAX_BATCH):
        raise Revert("BatchTooLarge")


# ----------------------------------------------------------------------------------------------------------------- signer sets
@dataclasses.dataclass
class SignerSet:
    members: list
    activeFrom: int = 0
    retiredAt: int = 0
    stopped: bool = False
    active: bool = False


class SignerSetModel:
    """Quote signer sets (document 11 section 4.7): versioned sets, planned rotation with a bounded grace, emergency removal with
    none, tombstones, a stop-only guardian."""

    def __init__(self, clock, mut=0, grace=QUOTE_SET_GRACE):
        self.clock, self.mut, self.grace = clock, mut, grace
        self.sets = {}
        self.current = 0
        self.removed_at = {}

    def on(self, name):
        return self.mut != MUT[name]

    def hit(self, name):
        return self.mut == MUT[name]

    def propose(self, role, version, members):
        if role != ROLE_GOVERNANCE and not (self.hit("SS_GUARDIAN_PROPOSE") and role == ROLE_GUARDIAN):
            raise Revert("NotGovernance")
        if version in self.sets:
            raise Revert("SignerSetVersionOrder")
        if self.on("SS_PROPOSE_TOMB_SKIP"):
            for k in members:
                if self.removed_at.get(k, 0) != 0:
                    raise Revert("QuoteSignerTombstoned", k)
        self.sets[version] = SignerSet(list(members))

    def activate(self, role, version):
        if role != ROLE_GOVERNANCE and not (self.hit("SS_GUARDIAN_ACTIVATE") and role == ROLE_GUARDIAN):
            raise Revert("NotGovernance")
        s = self.sets.get(version)
        if s is None or s.active:
            raise Revert("SignerSetNotProposed")
        if version != self.current + 1:
            raise Revert("SignerSetVersionOrder")
        if self.on("SS_ACTIVATE_TOMB_SKIP"):
            for k in s.members:
                if self.removed_at.get(k, 0) != 0:
                    raise Revert("QuoteSignerTombstoned", k)
        now = self.clock.now
        if self.current != 0 and self.on("SS_ROTATE_NO_RETIRE"):
            self.sets[self.current].retiredAt = now
        s.activeFrom, s.active = now, True
        self.current = version

    def remove(self, role, key):
        if role not in (ROLE_GOVERNANCE, ROLE_GUARDIAN):
            raise Revert("NotAuthorized")
        if self.removed_at.get(key, 0) == 0:
            self.removed_at[key] = self.clock.now                  # idempotent: a second removal changes nothing

    def stop(self, role, version):
        if role not in (ROLE_GOVERNANCE, ROLE_GUARDIAN):
            raise Revert("NotAuthorized")
        s = self.sets.get(version)
        if s is None or not s.active:
            raise Revert("SignerSetNotProposed")
        s.stopped = True

    def verify(self, key, version, issued_at):
        """Q1 then Q13 for a quote signed by `key` under set `version`, issued at `issued_at`, consumed now."""
        now = self.clock.now
        if self.on("Q1_TOMB_SKIP") and self.removed_at.get(key, 0) != 0:
            raise Revert("QuoteSignerRemoved")
        s = self.sets.get(version)
        if s is None or not s.active or (self.on("Q1_MEMBER_SKIP") and key not in s.members):
            raise Revert("QuoteSignerUnauthorized")
        if self.on("Q13_STOP_SKIP") and s.stopped:
            raise Revert("QuoteSignerSetStopped")
        if self.on("Q13_ACTIVE_SKIP") and s.activeFrom > issued_at:
            raise Revert("QuoteSignerSetRetired")
        if s.retiredAt != 0:
            early = issued_at <= s.retiredAt if self.hit("Q13_ISSUED_LE") else issued_at < s.retiredAt
            limit = s.retiredAt + self.grace
            in_grace = now < limit if self.hit("Q13_GRACE_LT") else now <= limit
            if self.hit("Q13_GRACE_SKIP"):
                in_grace = True
            if not (early and in_grace):
                raise Revert("QuoteSignerSetRetired")

    def digest(self):
        return (self.current, tuple(sorted((v, tuple(x.members), x.activeFrom, x.retiredAt, x.stopped, x.active) for v, x in self.sets.items())),
                tuple(sorted(self.removed_at.items())))

    def accepts(self, key, version, issued_at) -> bool:
        try:
            self.verify(key, version, issued_at)
            return True
        except Revert:
            return False


def self_check():
    """A few facts that must hold for the model to be what the documents say; the exhaustive checks are in tools/model_checks.py."""
    assert len(MUTANTS) >= 100 and len(set(n for _i, n, _d in MUTANTS)) == len(MUTANTS)
    assert len(ERRORS) == len(ERROR_ID)
    clock = Clock(1_800_000_000)
    p2 = Permit2Model(clock)
    p2.approve(1, 2, 3, 100, 0)
    assert p2.get(1, 2, 3).expiration == clock.now and usable(100, clock.now, clock.now)       # F5: usable in that block only
    assert not usable(100, clock.now, clock.now + 1) and not usable(0, clock.now + 5, clock.now)
    assert pin_wellformed(example_pin("pinEoa")) and pin_wellformed(example_pin("pin7702")) and pin_wellformed(example_pin("pin4337"))
    assert pin_wellformed(pin_1271())
    assert contained_mask(base_terms(), base_terms()) == 0
    # the model registry: published versions have their band, version 0 and any other version the empty band (fail closed)
    assert band(1) == (98, 102) and band(5) == (90, 110) and band(0) == EMPTY_BAND and band(6) == EMPTY_BAND and band(UINT32_MAX) == EMPTY_BAND
    assert all(lo <= hi for lo, hi in BOUNDS_BANDS.values()) and not any(lo <= p <= hi for lo, hi in [EMPTY_BAND] for p in range(0, 200))
    # K.6 and the widened mask follow the version, not a price pair
    a, b = base_terms(), base_terms()
    b.boundsVersion += 1
    assert contained_mask(b, a) == 1 << 5 and widened_mask(b, a) == 1 << 6
    b.boundsVersion -= 2
    assert contained_mask(b, a) == 1 << 5 and widened_mask(b, a) == 1 << 6
    # the typed hashes: the snapshot hash binds the customer, the terms hash does not bind any id
    assert snapshot_hash_int(a, 1, 2, 3, 4) != snapshot_hash_int(a, 1, 2, 3, 5) and terms_hash_int(a) != terms_hash_int(b)
    return True


if __name__ == "__main__":
    print("protocol_model self-check:", "ok" if self_check() else "FAILED", f"({len(MUTANTS)} mutants, {len(ERRORS)} errors)")
