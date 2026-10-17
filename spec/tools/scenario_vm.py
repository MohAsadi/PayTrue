#!/usr/bin/env python3
"""A tiny scenario machine over tools/protocol_model.py (revision 0.5).

A scenario is a flat list of 8-word instructions  [op, a, b, c, d, e, expectSel, expectArg]. The same programs are executed by this
module (the oracle that produced every expectation) and by the Solidity interpreter spec/foundry/test/helpers/ScenarioVM.sol, so a
vector is data, not code, and the two implementations cannot drift apart silently: the Solidity run must reproduce every expected
outcome of the Python run (`expectSel` = 0 means the instruction must succeed, otherwise the id of the error in
protocol_model.ERROR_ID; `expectArg` is the compared argument: a token slot, a key slot or a plain number).

Slots: customers 0..3, routers 0..3, tokens 1..10 (token id i has address 0x7000 + i), lineages 0..63, terms and pin registers 0..7,
signer keys 1..3, plain registers 0..7. Time is absolute; a program starts at T0.

The op table below is also the source of spec/foundry/test/generated/GenOps.sol.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import protocol_model as M  # noqa: E402

T0 = 1_800_000_000
WORDS = 8
ANY_ARG = 255                           # in a transition table: the argument of the error is not compared (a plain number such as an expiration)
FAR = T0 + 100_000_000
T_A_EXPIRES = T0 + 2_000_000            # lineage A expires after lineage B (the exploration relies on this order)
T_B_EXPIRES = T0 + 1_000_000

# ----------------------------------------------------------------------------------------------------------------- op table
_OPS = [
    ("NOW", 1), ("SETREG", 2),
    ("REG_REGISTER", 10), ("REG_PROPOSE", 11), ("REG_DEPRECATE", 12), ("REG_DISABLE", 13), ("REG_CLEAR", 14), ("REG_SUNSET", 15),
    ("REG_RETIRE", 16), ("FORCE_REG", 17),
    ("P2_APPROVE", 20), ("P2_LOCKDOWN", 21), ("P2_TRANSFER", 22), ("P2_REGRANT", 23), ("P2_INVALIDATE", 25), ("P2_EXPECT", 26),
    ("P2_EXPECT_NONCE", 27),
    ("TERMS_RESET", 30), ("TERMS_COPY", 31), ("TERMS_SET", 32), ("PIN_PRESET", 33), ("PIN_SET", 34), ("ACCT_SET", 35), ("DELEG_SET", 36),
    ("ACTIVATE", 40), ("AUTH_NEW", 41), ("AUTH_SET", 42), ("AUTH_ACCESS", 43), ("SUCCESSOR", 44), ("REVOKE", 45), ("RETIRE", 46),
    ("REDUCE_DROP", 47), ("UPDATE_PIN", 48), ("CONSUME", 49), ("PAUSE", 50),
    ("EXPECT_STATUS", 60), ("EXPECT_ACTIVE_GEN", 61), ("EXPECT_LIVE", 62), ("EXPECT_EXPOSED", 63), ("EXPECT_AUTHROUTERS", 64),
    ("EXPECT_PINVER", 65), ("EXPECT_MODE", 66), ("EXPECT_USAGE", 67), ("SNAP", 68), ("EXPECT_SNAP_EQ", 69), ("EXPECT_INDEX_EXACT", 70),
    ("CHK_WF", 75), ("CHK_PINCHECK", 76), ("CHK_NEXTVER", 77), ("CHK_AUTH", 78), ("CHK_AUTH_EXIT", 79), ("CHK_PINHASH", 80),
    ("CHK_CONTAINED", 81), ("CHK_WIDENED", 82),
    ("SS_PROPOSE", 90), ("SS_ACTIVATE", 91), ("SS_REMOVE", 92), ("SS_STOP", 93), ("SS_VERIFY", 94),
    ("W_NARROW", 95), ("SEED_LIVE", 96), ("W_ADD", 97), ("W_BATCH", 98), ("W_QUOTE", 99), ("W_CYCLE", 104), ("W_WINDOW", 105),
    ("BUILD", 100), ("ACT", 101), ("OBSERVE", 102),
]
OP = dict(_OPS)
OP_NAME = {v: k for k, v in _OPS}

# terms fields (TERMS_SET b), pin fields (PIN_SET b), auth fields (AUTH_SET a)
T_FIELDS = dict(T_EXPIRES=1, T_MERCHANT=2, T_RECIPIENT=3, T_SUBREF=4, T_PERIOD=5, T_ANCHOR=6, T_CURRENCY=7, T_TOKENS=8, T_CAP=9,
                T_FIAT=10, T_QAGE=11, T_BVER=12, T_CHARGES=14, T_MININT=15, T_FEE=16, T_EXT=17)
# field 13 was the upper bound of the price pair (boundsMax); the band is now read from the registry by `boundsVersion` (field 12, ADR-020).
# The number is retired, not reused: a TERMS_SET with it raises an error in this machine and in ScenarioVM.sol.
RETIRED_T_FIELDS = {13: ("T_BMAX", "the price band moved to the versioned registry (field 12 is now the bounds version)")}
P_FIELDS = dict(PF_MODE=1, PF_CODE=2, PF_DELEGATE=3, PF_DCODE=4, PF_FAMILY=5, PF_VERSION=6, PF_SIG=7)
A_FIELDS = dict(AF_CUSTOMER=1, AF_LINEAGE=2, AF_PRED=3, AF_KIND=4, AF_TERMS=5, AF_ROUTER=6, AF_CODEHASH=7, AF_VERSION=8, AF_SNAPSHOT=9,
                AF_MASK=10, AF_PIN=11, AF_DEADLINE=12, AF_NONCE=13)
PIN_PRESETS = dict(PP_EOA=1, PP_7702=2, PP_4337=3, PP_1271=4)
TERMS_PRESETS = dict(TP_ONE=1, TP_TWO=2, TP_THREE=3)
CHK_AUTH_KINDS = {}

# ---- exploration (BUILD / ACT / OBSERVE) vocabulary: the Solidity VM implements the same
CONFIG_SINGLE, CONFIG_SHARED_X, CONFIG_SHARED_Y = 0, 1, 2
# lineage state nibbles
LS_LIVE_R1, LS_LIVE_R2, LS_EXP_R1, LS_EXP_R2, LS_DONE = range(5)
# registry nibbles
RG_ACTIVE, RG_DEPR_STD, RG_DEPR_SEC, RG_DISABLED, RG_SUNSET, RG_OTHER = range(6)
# allowance nibbles
AV_NONE, AV_EXPIRED, AV_BOUNDED, AV_UNLIM = range(4)
BOUNDED_AMOUNT = 100
CHARGE_SMALL = 1
PROBE_CYCLE = 10 ** 9                    # a cycle index that no action ever settles (the can-charge probe must not see hidden state)
PER_PAYMENT_CAP = 50

ACTIONS = {}


def _reg_actions():
    for i in range(4):
        ACTIONS[i] = ("GRANT_B", (i // 2 + 1, i % 2))
        ACTIONS[4 + i] = ("GRANT_U", (i // 2 + 1, i % 2))
        ACTIONS[8 + i] = ("LOCK", (i // 2 + 1, i % 2))
        ACTIONS[12 + i] = ("EXPIRE_ALLOW", (i // 2 + 1, i % 2))
    ACTIONS[16], ACTIONS[17], ACTIONS[18], ACTIONS[19], ACTIONS[20] = (("DEPR_STD", ()), ("DEPR_SEC", ()), ("DISABLE", (0,)),
                                                                        ("DISABLE", (1,)), ("SUNSET_R1", ()))
    ACTIONS[21], ACTIONS[22] = ("EXPIRE_B", ()), ("EXPIRE_A", ())
    for i in range(8):
        ACTIONS[24 + i] = ("CHARGE", (i // 4, (i // 2) % 2, i % 2 + 1, CHARGE_SMALL))
        ACTIONS[32 + i] = ("CHARGE", (i // 4, (i // 2) % 2, i % 2 + 1, BOUNDED_AMOUNT))
    for i in range(4):
        ACTIONS[40 + i] = ("SUCC", (i // 2, i % 2))
    for i in range(2):
        ACTIONS[44 + i] = ("REVOKE", (i,))
        ACTIONS[46 + i] = ("RETIRE", (i,))


_reg_actions()


def action_label(a):
    kind, p = ACTIONS[a]
    return kind + "(" + ",".join(str(x) for x in p) + ")"


# ----------------------------------------------------------------------------------------------------------------- assembler
class Asm:
    """Builds a program and its human-readable listing."""

    def __init__(self):
        self.words = []
        self.listing = []

    def op(self, name, a=0, b=0, c=0, d=0, e=0, expect=None):
        sel, arg = 0, 0
        if expect is not None:
            if isinstance(expect, tuple):
                sel, arg = M.ERROR_ID[expect[0]], expect[1]
            else:
                sel = M.ERROR_ID[expect]
        self.words += [OP[name], a, b, c, d, e, sel, arg]
        txt = f"{name} " + " ".join(str(x) for x in (a, b, c, d, e))
        if sel:
            txt += f"  => {M.ERROR_BY_ID[sel][0]}" + (f"({arg})" if arg else "")
        self.listing.append(txt)
        return self

    def prog(self):
        return list(self.words)


def disassemble(words):
    out = []
    for i in range(0, len(words), WORDS):
        op, a, b, c, d, e, sel, arg = words[i:i + WORDS]
        txt = f"{OP_NAME[op]} {a} {b} {c} {d} {e}"
        if sel:
            txt += f"  => {M.ERROR_BY_ID[sel][0]}" + (f"({arg})" if arg else "")
        out.append(txt)
    return out


# ----------------------------------------------------------------------------------------------------------------- world
class RetiredField(AssertionError):
    """A program used a field number that no longer exists (ScenarioVM.sol reverts with RetiredTermsField for the same program)."""


class _Lazy(dict):
    """Registers that spring into existence with their default value on first use."""

    def __init__(self, factory):
        super().__init__()
        self.factory = factory

    def __missing__(self, key):
        v = self[key] = self.factory()
        return v


def customer_addr(slot):
    return 0xC000 + slot


def router_addr(slot):
    return 0xD000 + slot


def token_slot_addr(slot):
    return M.token_addr(slot)


def key_addr(slot):
    return 0x9000 + slot


def reg_code(state, reason):
    if state == M.ST_ACTIVE:
        return RG_ACTIVE
    if state == M.ST_DEPRECATED:
        return RG_DEPR_SEC if reason == M.REASON_SECURITY else RG_DEPR_STD
    if state == M.ST_DISABLED:
        return RG_DISABLED
    if state == M.ST_SUNSET:
        return RG_SUNSET
    return RG_OTHER


def av_code(amount, expiration, now):
    if amount == 0:
        return AV_NONE
    if now > expiration:
        return AV_EXPIRED
    if amount == M.UINT160_MAX:
        return AV_UNLIM
    return AV_BOUNDED


class World:
    def __init__(self, mut=0):
        self.mut = mut
        self.clock = M.Clock(T0)
        self.p2 = M.Permit2Model(self.clock)
        self.reg = M.RouterRegistryModel(self.clock, mut)
        self.mgr = M.ManagerModel(self.clock, self.reg, self.p2, mut)
        self.ss = M.SignerSetModel(self.clock, mut)
        self.terms = _Lazy(lambda: M.base_terms((1,)))
        self.pins = _Lazy(M.Pin)
        self.lineage = {}                  # slot -> lineage id
        self.regs = [0] * 8
        self.auth = M.Auth()
        self.access = M.Access()
        self.auth_nonce = 1
        self.snaps = {}
        self.cycle_counter = 1

    # ---- addressing helpers
    def mid(self, lineage_slot, gen_plus1):
        L = self.mgr.lineages[self.lineage[lineage_slot]]
        if gen_plus1 == 0:
            return L.active
        return L.mandate_ids[gen_plus1 - 1]

    def routers(self):
        return [router_addr(i) for i in range(4)]

    # ---- the interpreter
    def run(self, words, label=""):
        """Run a program; returns the list of failures (empty = every expectation held)."""
        fails = []
        for pc in range(0, len(words), WORDS):
            ins = words[pc:pc + WORDS]
            err = self.step(ins)
            if err:
                fails.append((label, pc // WORDS, OP_NAME[ins[0]], err))
        return fails

    def step(self, ins):
        op, a, b, c, d, e, sel, arg = ins
        name = OP_NAME[op]
        try:
            res = getattr(self, "op_" + name)(a, b, c, d, e)
        except M.Revert as r:
            actual = (M.ERROR_ID[r.name], r.arg)
            if sel == 0:
                return f"unexpected revert {r.name}({r.arg})"
            if actual[0] != sel:
                return f"expected {M.ERROR_BY_ID[sel][0]}, got {r.name}({r.arg})"
            kind = M.ERROR_BY_ID[sel][3]
            want = arg
            if kind == "token":
                want = M.token_addr(arg)
            elif kind == "key":
                want = key_addr(arg)
            if kind != "none" and arg != ANY_ARG and r.arg != want:
                return f"expected {M.ERROR_BY_ID[sel][0]} argument {want}, got {r.arg}"
            return None
        if res is not None:                        # an EXPECT_* or CHK_* op reports a mismatch as a string
            return res
        if sel != 0:
            return f"expected {M.ERROR_BY_ID[sel][0]}, the instruction succeeded"
        return None

    # ---- time and registers
    def op_NOW(self, a, b, c, d, e):
        self.clock.now = a

    def op_SETREG(self, a, b, c, d, e):
        self.regs[a] = b

    # ---- registry
    def op_REG_REGISTER(self, a, b, c, d, e):
        self.reg.register_active(router_addr(a), 0xC0DE00 + a, a + 1)

    def op_REG_PROPOSE(self, a, b, c, d, e):
        self.reg.propose(router_addr(a), 0xC0DE00 + a, a + 1)

    def op_REG_DEPRECATE(self, a, b, c, d, e):
        self.reg.deprecate(router_addr(a), router_addr(b), c, d)

    def op_REG_DISABLE(self, a, b, c, d, e):
        self.reg.emergency_disable(router_addr(a))

    def op_REG_CLEAR(self, a, b, c, d, e):
        self.reg.clear_emergency(router_addr(a))

    def op_REG_SUNSET(self, a, b, c, d, e):
        self.reg.sunset(router_addr(a))

    def op_REG_RETIRE(self, a, b, c, d, e):
        self.reg.retire(router_addr(a))

    def op_FORCE_REG(self, a, b, c, d, e):
        """Test harness: put a router into a state directly (a = router slot, b = state, c = reason, d = deprecatedAt)."""
        r = router_addr(a)
        self.reg.state[r], self.reg.reason[r], self.reg.deprecated_at[r] = b, c, d
        self.reg.sunset_not_before[r] = self.clock.now
        self.reg.sunset_at[r] = self.clock.now

    # ---- permit2
    def op_P2_APPROVE(self, a, b, c, d, e):
        self.p2.approve(customer_addr(a), M.token_addr(b), router_addr(c), d, e)

    def op_P2_LOCKDOWN(self, a, b, c, d, e):
        self.p2.lockdown(customer_addr(a), [(M.token_addr(b), router_addr(c))])

    def op_P2_TRANSFER(self, a, b, c, d, e):
        self.p2.transfer_from(router_addr(a), customer_addr(b), M.token_addr(c), d)

    def op_P2_REGRANT(self, a, b, c, d, e):
        cur = self.p2.get(customer_addr(a), M.token_addr(b), router_addr(c))
        self.p2.permit_regrant(customer_addr(a), M.token_addr(b), router_addr(c), d, e, cur.nonce)

    def op_P2_INVALIDATE(self, a, b, c, d, e):
        self.p2.invalidate_nonces(customer_addr(a), M.token_addr(b), router_addr(c), d)

    def op_P2_EXPECT(self, a, b, c, d, e):
        cur = self.p2.get(customer_addr(a), M.token_addr(b), router_addr(c))
        if (cur.amount, cur.expiration) != (d, e):
            return f"allowance is ({cur.amount}, {cur.expiration}), expected ({d}, {e})"

    def op_P2_EXPECT_NONCE(self, a, b, c, d, e):
        cur = self.p2.get(customer_addr(a), M.token_addr(b), router_addr(c))
        if cur.nonce != d:
            return f"nonce is {cur.nonce}, expected {d}"

    # ---- registers
    def op_TERMS_RESET(self, a, b, c, d, e):
        self.terms[a] = M.base_terms({1: (1,), 2: (1, 2), 3: (1, 2, 3)}[b])

    def op_TERMS_COPY(self, a, b, c, d, e):
        self.terms[a] = self.terms[b].clone()

    def op_TERMS_SET(self, a, b, c, d, e):
        t = self.terms[a]
        f = b
        if f == 1:
            t.expiresAt = e
        elif f == 2:
            t.merchantId = e
        elif f == 3:
            t.recipientPolicy = e
        elif f == 4:
            t.subscriptionRef = e
        elif f == 5:
            t.periodSeconds = e
        elif f == 6:
            t.anchorStartsAt = e
        elif f == 7:
            t.currency = e
        elif f == 8:                                          # the token list = ids c, d, e (0 = unused), sorted
            ids = sorted(set(x for x in (c, d, e) if x))
            old = t.caps
            t.tokens = [M.token_addr(i) for i in ids]
            t.caps = {M.token_addr(i): list(old.get(M.token_addr(i), [50, 1000, 0, 0, 500, 0])) for i in ids}
        elif f == 9:                                          # cap of token id c, family d
            t.caps[M.token_addr(c)][d] = e
        elif f == 10:
            t.fiat[c] = e
        elif f == 11:
            t.maxQuoteAge = e
        elif f == 12:
            t.boundsVersion = e
        elif f in RETIRED_T_FIELDS:
            raise RetiredField(f"terms field {f} is retired ({RETIRED_T_FIELDS[f][0]}): {RETIRED_T_FIELDS[f][1]}")
        elif f == 14:
            t.maxChargesPerPeriod = e
        elif f == 15:
            t.minInterval = e
        elif f == 16:
            t.maxFeeBps = e
        elif f == 17:
            t.extensionsHash = e
        else:
            raise AssertionError("terms field")

    def op_PIN_PRESET(self, a, b, c, d, e):
        self.pins[a] = {1: M.example_pin("pinEoa"), 2: M.example_pin("pin7702"), 3: M.example_pin("pin4337"), 4: M.pin_1271()}[b]

    def op_PIN_SET(self, a, b, c, d, e):
        p = self.pins[a]
        name = ["", "accountMode", "accountCodeHash", "delegate", "delegateCodeHash", "implementationFamily", "pinVersion",
                "signatureMode"][b]
        setattr(p, name, c)

    def op_ACCT_SET(self, a, b, c, d, e):
        self.mgr.set_codehash(customer_addr(a), b)

    def op_DELEG_SET(self, a, b, c, d, e):
        self.mgr.set_codehash(a, b)

    # ---- mandates
    def op_ACTIVATE(self, a, b, c, d, e):
        lid, _mid = self.mgr.activate(customer_addr(b), a, router_addr(c), self.terms[d].clone(), self.pins[e].clone())
        self.lineage[a] = lid

    def predecessor(self, lineage_slot):
        """The predecessor a successor call names: the active mandate, or generation regs[2] - 1 when regs[2] != 0."""
        L = self.mgr.lineages[self.lineage[lineage_slot]]
        return L.active if self.regs[2] == 0 else L.mandate_ids[self.regs[2] - 1]

    def op_AUTH_NEW(self, a, b, c, d, e):
        self.auth = self.mgr.build_auth(self.predecessor(a), b, router_addr(c), self.terms[d], self.pins[e], self.clock.now + 3600,
                                        self.auth_nonce)
        self.auth_nonce += 1
        self.access = M.Access(True, M.SIG_NONE, False)

    def op_AUTH_SET(self, a, b, c, d, e):
        au = self.auth
        if a == 1:
            au.customer = customer_addr(b)
        elif a == 2:
            au.lineageId = self.lineage[b]
        elif a == 3:
            au.predecessorId = M.mandate_id_of(au.lineageId, b)
        elif a == 4:
            au.kind = b
        elif a == 5:
            au.newTermsHash = b
        elif a == 6:
            au.newRouter = router_addr(b)
        elif a == 7:
            au.newRouterCodeHash = b
        elif a == 8:
            au.newRouterVersion = b
        elif a == 9:
            au.termsSnapshotHash = b
        elif a == 10:
            au.widenedMask = b
        elif a == 11:
            au.accountPin = self.pins[b].clone()
        elif a == 12:
            au.deadline = b
        elif a == 13:
            au.nonce = b
        else:
            raise AssertionError("auth field")

    def op_AUTH_ACCESS(self, a, b, c, d, e):
        self.access = M.Access(bool(a), b, bool(c))

    def op_SUCCESSOR(self, a, b, c, d, e):
        self.mgr.activate_successor(self.predecessor(a), b, router_addr(c), self.terms[d].clone(), self.pins[e].clone(), self.auth,
                                    self.access)

    def op_REVOKE(self, a, b, c, d, e):
        self.mgr.revoke(self.mid(a, b), self.access.sender_is_customer)

    def op_RETIRE(self, a, b, c, d, e):
        self.mgr.retire(self.mid(a, b))

    def op_REDUCE_DROP(self, a, b, c, d, e):
        self.mgr.reduce_drop_token(self.mid(a, b), M.token_addr(c))

    def op_UPDATE_PIN(self, a, b, c, d, e):
        self.mgr.update_account_pin(self.mid(a, b), self.pins[c].clone(), d, e, self.access)

    def op_CONSUME(self, a, b, c, d, e):
        mid = self.mid(a, b)
        pin = self.pins[self.regs[1] - 1] if self.regs[1] else self.mgr.mandates[mid].pin
        self.mgr.consume(router_addr(c), mid, M.token_addr(d), e, self.regs[0], pin.clone())

    def op_PAUSE(self, a, b, c, d, e):
        self.mgr.set_pause(self.mid(a, b), c, bool(d))

    # ---- expectations
    def op_EXPECT_STATUS(self, a, b, c, d, e):
        m = self.mgr.mandates[self.mid(a, b)]
        got = (m.status, m.reason, int(m.retired))
        if got != (c, d, e):
            return f"mandate (status, reason, retired) = {got}, expected {(c, d, e)}"

    def op_EXPECT_ACTIVE_GEN(self, a, b, c, d, e):
        L = self.mgr.lineages[self.lineage[a]]
        g = self.mgr.mandates[L.active].generation
        if g != b:
            return f"active generation {g}, expected {b}"

    def op_EXPECT_LIVE(self, a, b, c, d, e):
        n = self.mgr.live_count(customer_addr(a), router_addr(b), M.token_addr(c))
        if n != d:
            return f"live({a},{b},{c}) = {n}, expected {d}"

    def op_EXPECT_EXPOSED(self, a, b, c, d, e):
        n = len(self.mgr.exposed_list(customer_addr(a), router_addr(b)))
        if n != c:
            return f"|Exposed({a},{b})| = {n}, expected {c}"

    def op_EXPECT_AUTHROUTERS(self, a, b, c, d, e):
        got = self.mgr.auth_routers(self.lineage[a], self.routers())
        mask = sum(1 << i for i in range(4) if router_addr(i) in got)
        if mask != b:
            return f"AuthRouters mask {mask}, expected {b}"

    def op_EXPECT_PINVER(self, a, b, c, d, e):
        v = self.mgr.lineages[self.lineage[a]].pinVersion
        if v != b:
            return f"lineage pinVersion {v}, expected {b}"

    def op_EXPECT_MODE(self, a, b, c, d, e):
        r = router_addr(a)
        got = (self.reg.mode(r), int(self.reg.is_bindable(r)), int(self.reg.is_chargeable(r)))
        if got != (b, c, d):
            return f"(mode, bindable, chargeable) = {got}, expected {(b, c, d)}"

    def op_EXPECT_USAGE(self, a, b, c, d, e):
        n = self.mgr.used_total.get((self.lineage[a], M.token_addr(b)), 0)
        if n != c:
            return f"usage {n}, expected {c}"

    def _digest(self, exclude):
        lids = [self.lineage[s] for s in sorted(self.lineage) if s != exclude]
        parts = [self.p2.snapshot(), self.reg.snapshot()]
        for lid in lids:
            parts.append(self.mgr.lineage_digest(lid))
            parts.append(tuple(self.mgr.mandate_digest(m) for m in self.mgr.lineages[lid].mandate_ids))
        return tuple(parts)

    def full_digest(self):
        """Every piece of model state (used by the atomicity check: a call that reverts must change nothing)."""
        m = self.mgr
        return (self.p2.snapshot(), self.reg.snapshot(), tuple(sorted(m.lineage_digest(l) for l in m.lineages)),
                tuple(sorted(m.mandate_digest(x) for x in m.mandates)), tuple(sorted(m.live.items())),
                tuple(sorted((k, tuple(v)) for k, v in m.exposed.items())), tuple(sorted(m.used_nonce)), tuple(sorted(m.codehash.items())),
                tuple(sorted(m.used_total.items())), tuple(sorted(m.cycle_settled)), self.ss.digest(), self.clock.now)

    def op_SNAP(self, a, b, c, d, e):
        self.snaps[a] = self._digest(b)

    def op_EXPECT_SNAP_EQ(self, a, b, c, d, e):
        if self.snaps[a] != self._digest(b):
            return "state outside the migrating lineage changed (I-MIG-11)"

    def op_EXPECT_INDEX_EXACT(self, a, b, c, d, e):
        cust = customer_addr(a)
        rec = self.mgr.exposure_recomputed()
        for r in range(4):
            for t in range(1, 11):
                have = self.mgr.live_count(cust, router_addr(r), M.token_addr(t))
                want = rec.get((cust, router_addr(r), M.token_addr(t)), 0)
                if have != want:
                    return f"live({a},{r},{t}) = {have}, recomputed {want}"
            exp = set(self.mgr.exposed_list(cust, router_addr(r)))
            want_set = set(t for (c_, r_, t), n in rec.items() if c_ == cust and r_ == router_addr(r) and n > 0)
            if exp != want_set:
                return f"Exposed({a},{r}) differs from the tokens with a non-zero count"

    # ---- pure checks
    def op_CHK_WF(self, a, b, c, d, e):
        got = int(M.pin_wellformed(self.pins[a], self.mut))
        if got != d:
            return f"PIN_WELLFORMED = {got}, expected {d}"

    def op_CHK_PINCHECK(self, a, b, c, d, e):
        got = M.pin_check(self.pins[a], b, c, self.mut)
        if got != d:
            return f"PIN_OK field = {got}, expected {d}"

    def op_CHK_NEXTVER(self, a, b, c, d, e):
        got = M.next_pin_version(a, b, self.pins[c], self.pins[d], self.mut)
        if got != e:
            return f"nextPinVersion = {got}, expected {e}"

    def op_CHK_AUTH(self, a, b, c, d, e):
        pin = self.pins[b]
        h, hd = self.mgr.account_state(customer_addr(a), pin)
        M.auth_signature(bool(c), d, bool(e), pin, h, hd, self.mut)

    def op_CHK_AUTH_EXIT(self, a, b, c, d, e):
        M.auth_exit(bool(b), c, bool(d), self.pins[a], self.mut)

    def op_CHK_PINHASH(self, a, b, c, d, e):
        got = self.pins[a].struct_hash()
        if got != b:
            return f"hashStruct(pin) = {got:#x}, expected {b:#x}"

    def op_CHK_CONTAINED(self, a, b, c, d, e):
        got = M.contained_mask(self.terms[a], self.terms[b], self.mut)
        if got != d:
            return f"containment mask {got:#x}, expected {d:#x}"

    def op_CHK_WIDENED(self, a, b, c, d, e):
        got = M.widened_mask(self.terms[a], self.terms[b])
        if got != d:
            return f"widened mask {got:#x}, expected {d:#x}"

    # ---- signer sets
    def op_SS_PROPOSE(self, a, b, c, d, e):
        self.ss.propose(a, b, [key_addr(k) for k in (1, 2, 3) if c >> (k - 1) & 1])

    def op_SS_ACTIVATE(self, a, b, c, d, e):
        self.ss.activate(a, b)

    def op_SS_REMOVE(self, a, b, c, d, e):
        self.ss.remove(a, key_addr(b))

    def op_SS_STOP(self, a, b, c, d, e):
        self.ss.stop(a, b)

    def op_SS_VERIFY(self, a, b, c, d, e):
        self.ss.verify(key_addr(a), b, c)

    # ---- widths and arithmetic
    def op_W_NARROW(self, a, b, c, d, e):
        M.narrow(b, a, "width")

    def op_SEED_LIVE(self, a, b, c, d, e):
        self.mgr.seed_live(customer_addr(a), router_addr(b), M.token_addr(c), d)

    def op_W_ADD(self, a, b, c, d, e):
        M.add_checked(a, b)

    def op_W_BATCH(self, a, b, c, d, e):
        M.batch_check(a, self.mut)

    def op_W_QUOTE(self, a, b, c, d, e):
        """a = issuedAt, b = validAfter, c = validUntil, d = maxQuoteAge, e = registry maxQuoteTtl; consumed at the current time."""
        M.quote_times_check(a, b, c, d, e, self.clock.now, self.mut)

    def op_W_CYCLE(self, a, b, c, d, e):
        """a = cycleIndex, b = anchor, c = periodSeconds; consumed at the current time."""
        M.cycle_allowed(a, self.clock.now, b, c, self.mut)

    def op_W_WINDOW(self, a, b, c, d, e):
        """a = now, b = anchor, c = length, d = the expected window index."""
        got = M.window_index(a, b, c, self.mut)
        if got != d:
            return f"window index {got}, expected {d}"

    # ---- the exploration vocabulary: BUILD a world from a state key, ACT, OBSERVE
    def op_BUILD(self, config, key, c, d, e):
        self.build_state(config, key)

    def op_ACT(self, config, action, c, d, e):
        self.act(config, action)

    def op_OBSERVE(self, config, key, c, d, e):
        got = self.observe(config)
        if got != key:
            return f"observation {got:#x}, expected {key:#x}"

    def nib(self, key, i):
        return (key >> (4 * i)) & 0xF

    def build_state(self, config, key):
        """Concretize a state key (see the layout in tools/model_checks.py): a fresh world in which every nibble holds."""
        self.__init__(self.mut)
        reg1, reg2, sa, sb = (self.nib(key, i) for i in range(4))
        av = [self.nib(key, 4 + i) for i in range(4)]
        two = config != CONFIG_SINGLE
        self.op_REG_REGISTER(0, 0, 0, 0, 0)
        self.op_REG_REGISTER(1, 0, 0, 0, 0)
        for slot, st, tokens, expires in ((0, sa, (1,), T_A_EXPIRES), (1, sb, (1, 2) if config == CONFIG_SHARED_Y else (1,), T_B_EXPIRES)):
            if slot == 1 and not two:
                continue
            self.terms[slot] = M.base_terms(tokens)
            self.terms[slot].expiresAt = expires
            self.pins[slot] = M.example_pin("pinEoa")
            rt = 1 if st in (LS_LIVE_R2, LS_EXP_R2) else 0
            self.op_ACTIVATE(slot, 0, rt, slot, slot)
            if st == LS_DONE:
                self.mgr.revoke(self.mgr.lineages[self.lineage[slot]].active, True)
        phase = 2 if sa in (LS_EXP_R1, LS_EXP_R2) else 1 if sb in (LS_EXP_R1, LS_EXP_R2) else 0
        self.clock.now = (T0, T_B_EXPIRES + 1, T_A_EXPIRES + 1)[phase]
        for r, code in ((0, reg1), (1, reg2)):
            st, reason = {RG_ACTIVE: (M.ST_ACTIVE, 0), RG_DEPR_STD: (M.ST_DEPRECATED, 0), RG_DEPR_SEC: (M.ST_DEPRECATED, 1),
                          RG_DISABLED: (M.ST_DISABLED, 0), RG_SUNSET: (M.ST_SUNSET, 0)}[code]
            self.op_FORCE_REG(r, st, reason, self.clock.now - 1, 0)
        for i in range(4):
            t, r = i // 2 + 1, i % 2
            self.set_allowance_value(t, r, av[i])

    def set_allowance_value(self, t, r, v):
        c = customer_addr(0)
        now = self.clock.now
        if v == AV_BOUNDED:
            self.p2.approve(c, M.token_addr(t), router_addr(r), BOUNDED_AMOUNT, FAR)
        elif v == AV_UNLIM:
            self.p2.approve(c, M.token_addr(t), router_addr(r), M.UINT160_MAX, FAR)
        elif v == AV_EXPIRED:
            self.p2.approve(c, M.token_addr(t), router_addr(r), BOUNDED_AMOUNT, now - 1)

    def act(self, config, action):
        kind, p = ACTIONS[action]
        c = customer_addr(0)
        if kind in ("GRANT_B", "GRANT_U"):
            self.p2.approve(c, M.token_addr(p[0]), router_addr(p[1]), BOUNDED_AMOUNT if kind == "GRANT_B" else M.UINT160_MAX, FAR)
        elif kind == "LOCK":
            self.p2.lockdown(c, [(M.token_addr(p[0]), router_addr(p[1]))])
        elif kind == "EXPIRE_ALLOW":
            cur = self.p2.get(c, M.token_addr(p[0]), router_addr(p[1]))
            self.p2.approve(c, M.token_addr(p[0]), router_addr(p[1]), cur.amount, self.clock.now - 1)
        elif kind in ("DEPR_STD", "DEPR_SEC"):
            self.reg.deprecate(router_addr(0), router_addr(1), M.REASON_STANDARD if kind == "DEPR_STD" else M.REASON_SECURITY, 0)
        elif kind == "DISABLE":
            self.reg.emergency_disable(router_addr(p[0]))
        elif kind == "SUNSET_R1":
            if self.reg.st(router_addr(0)) != M.ST_DEPRECATED:
                raise M.Revert("WrongRouterState")
            self.reg.state[router_addr(0)] = M.ST_SUNSET
        elif kind == "EXPIRE_B":
            self.clock.now = max(self.clock.now, T_B_EXPIRES + 1)
        elif kind == "EXPIRE_A":
            self.clock.now = max(self.clock.now, T_A_EXPIRES + 1)
        elif kind == "CHARGE":
            lslot, r, t, amount = p
            self.mgr.consume(router_addr(r), self.mgr.lineages[self.lineage[lslot]].active, M.token_addr(t), amount, 1,
                             self.mgr.mandates[self.mgr.lineages[self.lineage[lslot]].active].pin.clone())
        elif kind == "SUCC":
            lslot, k = p
            L = self.mgr.lineages[self.lineage[lslot]]
            P = self.mgr.mandates[L.active]
            new_router = router_addr(1) if P.router == router_addr(0) else router_addr(0)
            auth = self.mgr.build_auth(P.id, k, new_router, P.terms, P.pin, self.clock.now + 3600, 1)
            self.mgr.activate_successor(P.id, k, new_router, P.terms.clone(), P.pin.clone(), auth, M.Access(True, M.SIG_NONE, False))
        elif kind == "REVOKE":
            self.mgr.revoke(self.mgr.lineages[self.lineage[p[0]]].active, True)
        elif kind == "RETIRE":
            self.mgr.retire(self.mgr.lineages[self.lineage[p[0]]].active)
        else:
            raise AssertionError(kind)

    def lineage_nibble(self, slot, config):
        if slot not in self.lineage:
            return LS_DONE
        L = self.mgr.lineages[self.lineage[slot]]
        m = self.mgr.mandates[L.active]
        if m.status != M.MS_ACTIVE or m.retired or L.terminated:
            return LS_DONE
        on_r2 = m.router == router_addr(1)
        expired = self.clock.now >= m.terms.expiresAt
        return (LS_EXP_R2 if on_r2 else LS_EXP_R1) if expired else (LS_LIVE_R2 if on_r2 else LS_LIVE_R1)

    def observe(self, config):
        """The state key: nibbles 0..7 identify the state (registry, lineages, allowances); 8..11 are the exposure counts
        live(R1,t1), live(R2,t1), live(R1,t2), live(R2,t2); 12 the AuthRouters bits of A and B; 13 whether A and B can charge
        (A on R1, A on R2, B on R1, B on R2) with one unit of t1."""
        c = customer_addr(0)
        key = reg_code(self.reg.st(router_addr(0)), self.reg.reason.get(router_addr(0), 0))
        key |= reg_code(self.reg.st(router_addr(1)), self.reg.reason.get(router_addr(1), 0)) << 4
        key |= self.lineage_nibble(0, config) << 8
        key |= self.lineage_nibble(1, config) << 12
        for i in range(4):
            t, r = i // 2 + 1, i % 2
            a = self.p2.get(c, M.token_addr(t), router_addr(r))
            key |= av_code(a.amount, a.expiration, self.clock.now) << (16 + 4 * i)
            key |= self.mgr.live_count(c, router_addr(r), M.token_addr(t)) << (32 + 4 * i)
        auth_bits = 0
        can = 0
        for slot in (0, 1):
            if slot not in self.lineage:
                continue
            got = self.mgr.auth_routers(self.lineage[slot], [router_addr(0), router_addr(1)])
            auth_bits |= (int(router_addr(0) in got) | int(router_addr(1) in got) << 1) << (2 * slot)
            mid = self.mgr.lineages[self.lineage[slot]].active
            for r in (0, 1):
                if self.mgr.would_charge(router_addr(r), mid, M.token_addr(1), CHARGE_SMALL, PROBE_CYCLE):
                    can |= 1 << (2 * slot + r)
        key |= auth_bits << 48
        key |= can << 52
        return key


def run_program(words, mut=0, label=""):
    w = World(mut)
    return w.run(words, label)


def replay_transition(config, key, action, exp_sel, exp_arg, next_key, mut=0):
    """One row of a transition table: BUILD the state, ACT with the expected outcome, OBSERVE the next state."""
    w = World(mut)
    w.op_BUILD(config, key, 0, 0, 0)
    err = w.step([OP["ACT"], config, action, 0, 0, 0, exp_sel, exp_arg])
    if err:
        return err
    return w.step([OP["OBSERVE"], config, next_key, 0, 0, 0, 0, 0])
