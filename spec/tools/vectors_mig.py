#!/usr/bin/env python3
"""Executable scenarios for document 12 section 12 (MIG-TV-xx), written as programs of tools/scenario_vm.py (revision 0.5).

Each scenario is a small program. tools/vector_suite.py runs every program on the Python model (an expectation the model does not
meet is a defect of the scenario or of the model); spec/foundry/test/generated replays the same words on the Solidity reference model.
Scenarios that the planner or the orchestrator owns (NC-20, NC-21, holds, notices) are executable here only in their on-chain part;
`note` says so.

Conventions: customer 0; router slot 0 is the old router R0, slot 1 the new router R1; token ids 1 and 2; lineage slots 0 (A) and 1 (B);
terms slot i belongs to lineage slot i unless stated; pin slot 0 is the plain-EOA pin; kinds N = NORMAL, E = EMERGENCY, V = REVISION.
"""
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import protocol_model as M  # noqa: E402
import scenario_vm as S  # noqa: E402
from scenario_vm import Asm, T0, FAR  # noqa: E402

N, E, V = M.NORMAL, M.EMERGENCY, M.REVISION
MAXU160 = M.UINT160_MAX
TF = S.T_FIELDS
AF = S.A_FIELDS
PF = S.P_FIELDS
PP = S.PIN_PRESETS
RS_SM, RS_SR = M.RV_SUPERSEDED_MIGRATION, M.RV_SUPERSEDED_REVISION
ACTIVE, REVOKED = M.MS_ACTIVE, M.MS_REVOKED


class Scenario:
    def __init__(self, vid, source, title, note=""):
        self.id, self.source, self.title, self.note = vid, source, title, note
        self.a = Asm()

    def op(self, name, *args, expect=None):
        self.a.op(name, *args, expect=expect)
        return self

    # ---- building blocks
    def routers(self):
        return self.op("REG_REGISTER", 0).op("REG_REGISTER", 1)

    def lineage(self, slot, tokens=(1,), router=0, customer=0, expires=None, pin=0, extra=(), terms=None):
        """Terms slot `terms` (default: the lineage slot) = base terms for `tokens`, then lineage `slot` activated on `router`."""
        ts = slot if terms is None else terms
        self.op("TERMS_RESET", ts, S.TERMS_PRESETS["TP_ONE"])
        if tuple(tokens) != (1,):
            self.op("TERMS_SET", ts, TF["T_TOKENS"], *(list(tokens) + [0] * (3 - len(tokens))))
        if expires is not None:
            self.op("TERMS_SET", ts, TF["T_EXPIRES"], 0, 0, expires)
        for f in extra:
            self.op("TERMS_SET", ts, *f)
        self.op("PIN_PRESET", pin, PP["PP_EOA"])
        return self.op("ACTIVATE", slot, customer, router, ts, pin)

    def grant(self, token, router, amount=100, exp=FAR, customer=0):
        return self.op("P2_APPROVE", customer, token, router, amount, exp)

    def lock(self, token, router, customer=0):
        return self.op("P2_LOCKDOWN", customer, token, router)

    def auth(self, lineage, kind, new_router, terms=None, pin=0):
        return self.op("AUTH_NEW", lineage, kind, new_router, lineage if terms is None else terms, pin)

    def succ(self, lineage, kind, new_router, terms=None, pin=0, expect=None, sets=(), access=None):
        """AUTH_NEW (with optional AUTH_SET tweaks and an access mode) then SUCCESSOR."""
        t = lineage if terms is None else terms
        self.auth(lineage, kind, new_router, t, pin)
        for f in sets:
            self.op("AUTH_SET", *f)
        if access is not None:
            self.op("AUTH_ACCESS", *access)
        return self.op("SUCCESSOR", lineage, kind, new_router, t, pin, expect=expect)

    def charge(self, lineage, router, token, amount, cycle, gen_plus1=0, expect=None):
        return self.op("SETREG", 0, cycle).op("CONSUME", lineage, gen_plus1, router, token, amount, expect=expect)

    def status(self, lineage, gen, status, reason=0, retired=0):
        return self.op("EXPECT_STATUS", lineage, gen + 1, status, reason, retired)

    def auth_routers(self, lineage, mask):
        return self.op("EXPECT_AUTHROUTERS", lineage, mask)

    def fund_new(self, tokens=(1,)):
        for t in tokens:
            self.grant(t, 1)
        return self

    def sibling_fixture(self, b_tokens=(1,), b_router=0, expires_b=None, extra_a=(), extra_b=()):
        """A and B of one customer on R0 (A uses t1, B uses b_tokens); old and new allowances are bounded 100, far expiry."""
        self.routers()
        self.lineage(0, extra=extra_a)
        self.lineage(1, b_tokens, b_router, expires=expires_b, extra=extra_b)
        for t in sorted(set((1,) + tuple(b_tokens))):
            self.grant(t, 0)
            self.grant(t, 1)
        return self

    def single_fixture(self):
        self.routers().lineage(0).grant(1, 0).grant(1, 1)
        return self


# ----------------------------------------------------------------------------------------------------------------- the scenarios
def build_all():
    out = []

    def new(vid, source, title, note=""):
        sc = Scenario(vid, source, title, note)
        out.append(sc)
        return sc

    # ---- MIG-TV-05 (modified): kind NORMAL for the last live mandate
    s = new("MIG_TV_05", "MIG-TV-05", "NORMAL for the last live mandate on the old router while the old allowance is usable").single_fixture()
    s.succ(0, N, 1, expect=("OldPermissionNotRevoked", 1))
    s.status(0, 0, ACTIVE)
    s.lock(1, 0)
    s.succ(0, N, 1)
    s.status(0, 0, REVOKED, RS_SM).status(0, 1, ACTIVE)
    s.op("EXPECT_ACTIVE_GEN", 0, 1).op("EXPECT_LIVE", 0, 0, 1, 0).op("EXPECT_LIVE", 0, 1, 1, 1).auth_routers(0, 2)
    s.op("EXPECT_EXPOSED", 0, 0, 0).op("EXPECT_EXPOSED", 0, 1, 1)

    # ---- MIG-TV-06 / 07: sunset and emergency disable
    s = new("MIG_TV_06", "MIG-TV-06", "Router reaches SUNSET with the lineage unmigrated: no charge, a successor can still be created").single_fixture()
    s.op("REG_DEPRECATE", 0, 1, M.REASON_STANDARD, 0)
    s.charge(0, 0, 1, 10, 1)                                          # DEPRECATED still charges
    s.op("NOW", T0 + M.MIN_NOTICE_STANDARD).op("REG_SUNSET", 0)
    s.op("EXPECT_MODE", 0, M.MODE_EMERGENCY, 0, 0)
    s.charge(0, 0, 1, 10, 2, expect="RouterNotChargeable")
    s.lock(1, 0)
    s.succ(0, E, 1)
    s.charge(0, 1, 1, 10, 3)

    s = new("MIG_TV_07", "MIG-TV-07", "Router emergency-disabled, then a successor to the new router: succeeds, charges resume").single_fixture()
    s.op("REG_DISABLE", 0)
    s.charge(0, 0, 1, 10, 1, expect="RouterNotChargeable")
    s.lock(1, 0)
    s.succ(0, E, 1)
    s.charge(0, 1, 1, 10, 1)
    s.op("EXPECT_MODE", 0, M.MODE_EMERGENCY, 0, 0).op("EXPECT_MODE", 1, M.MODE_NORMAL, 1, 1)

    # ---- MIG-TV-08: unbindable targets
    s = new("MIG_TV_08", "MIG-TV-08", "Successor to an unregistered, CANDIDATE, non-rollback DEPRECATED or SUNSET router")
    s.routers().lineage(0).grant(1, 0).lock(1, 0).grant(1, 3).grant(1, 2).grant(1, 1)
    s.succ(0, N, 3, expect="RouterNotBindable")                       # slot 3 is not registered
    s.op("REG_PROPOSE", 2)
    s.succ(0, N, 2, expect="RouterNotBindable")                       # CANDIDATE
    s.op("REG_DEPRECATE", 1, 0, M.REASON_STANDARD, 0)                 # R1 deprecated, R0 stays ACTIVE
    s.op("NOW", T0 + M.ROLLBACK_WINDOW)
    s.succ(0, N, 1, expect="RouterNotBindable")                       # DEPRECATED, now = deprecatedAt + window
    s.op("NOW", T0 + M.MIN_NOTICE_STANDARD).op("REG_SUNSET", 1)
    s.succ(0, N, 1, expect="RouterNotBindable")                       # SUNSET

    # ---- MIG-TV-09: terms not contained
    s = new("MIG_TV_09", "MIG-TV-09", "Successor with a wider cap, an extra token, a longer expiry, or a non-zero extensionsHash",
            "the extensionsHash case reverts ExtensionsNotSupported (X1 precedes C1), not TermsNotContained as the table says").single_fixture()
    s.lock(1, 0).grant(2, 1)
    s.op("TERMS_COPY", 5, 0).op("TERMS_SET", 5, TF["T_CAP"], 1, 0, 51)
    s.succ(0, N, 1, terms=5, expect="TermsNotContained")
    s.op("TERMS_COPY", 5, 0).op("TERMS_SET", 5, TF["T_TOKENS"], 1, 2, 0)
    s.succ(0, N, 1, terms=5, expect="TermsNotContained")
    s.op("TERMS_COPY", 5, 0).op("TERMS_SET", 5, TF["T_EXPIRES"], 0, 0, 1_900_000_001)
    s.succ(0, N, 1, terms=5, expect="TermsNotContained")
    s.op("TERMS_COPY", 5, 0).op("TERMS_SET", 5, TF["T_EXT"], 0, 0, 7)
    s.succ(0, N, 1, terms=5, expect="ExtensionsNotSupported")
    s.op("TERMS_COPY", 5, 0).op("TERMS_SET", 5, TF["T_CAP"], 1, 0, 49)         # a narrower cap is contained
    s.succ(0, N, 1, terms=5)

    # ---- MIG-TV-10 / 11 / 12 / 19: counters and cycles survive, the old mandate is dead
    s = new("MIG_TV_10", "MIG-TV-10", "Spend 40 of 50 under generation n; migrate; attempt 20 under n+1: the lineage cap binds")
    s.routers().lineage(0, extra=[(TF["T_CAP"], 1, 1, 50)]).grant(1, 0).grant(1, 1)
    s.charge(0, 0, 1, 40, 1)
    s.op("EXPECT_USAGE", 0, 1, 40)
    s.lock(1, 0)
    s.succ(0, N, 1)
    s.op("EXPECT_USAGE", 0, 1, 40)
    s.charge(0, 1, 1, 20, 2, expect="TokenTotalCapExceeded")
    s.charge(0, 1, 1, 51, 2, expect="TokenPerPaymentCapExceeded")       # the per-payment cap (50) is carried too
    s.charge(0, 1, 1, 10, 2)
    s.op("EXPECT_USAGE", 0, 1, 50)

    s = new("MIG_TV_11", "MIG-TV-11", "A cycle settled under generation n cannot settle again under n+1 or router B (MIG-TV-19)").single_fixture()
    s.charge(0, 0, 1, 10, 7)
    s.charge(0, 0, 1, 10, 7, expect="PaymentAlreadySettled")
    s.lock(1, 0)
    s.succ(0, N, 1)
    s.charge(0, 1, 1, 10, 7, expect="PaymentAlreadySettled")
    s.charge(0, 1, 1, 10, 8)

    s = new("MIG_TV_12", "MIG-TV-12", "Old mandate charge attempt after the successor exists reverts although its router is chargeable").single_fixture()
    s.succ(0, N, 1, expect=("OldPermissionNotRevoked", 1))
    s.lock(1, 0)
    s.succ(0, N, 1)
    s.grant(1, 0)                                                      # the old allowance is usable again (a stale permit, MIG-TV-25)
    s.charge(0, 0, 1, 10, 1, gen_plus1=1, expect="MandateNotConsumable")          # generation 0, old router
    s.charge(0, 1, 1, 10, 1, gen_plus1=1, expect="MandateNotConsumable")          # generation 0, new router
    s.charge(0, 0, 1, 10, 1, gen_plus1=0, expect="WrongRouter")                   # the successor is bound to R1, not R0
    s.charge(0, 1, 1, 10, 1)
    s.auth_routers(0, 2)

    s = new("MIG_TV_13", "MIG-TV-13", "Reverse successor to the old router inside the rollback window; outside it")
    s.routers().lineage(0).grant(1, 0).grant(1, 1).lock(1, 0)
    s.op("REG_DEPRECATE", 0, 1, M.REASON_STANDARD, 0)
    s.succ(0, N, 1)                                                     # forward: R0 is deprecated for a standard reason (normal mode)
    s.lock(1, 1).grant(1, 0)
    s.op("NOW", T0 + M.ROLLBACK_WINDOW - 1)
    s.succ(0, N, 0)                                                     # back to R0 one second before the window closes
    s.status(0, 1, REVOKED, RS_SM).op("EXPECT_ACTIVE_GEN", 0, 2).auth_routers(0, 1)
    s.lock(1, 0).grant(1, 1)
    s.succ(0, N, 1)                                                     # forward again (R1 is bindable)
    s.lock(1, 1).grant(1, 0)
    s.op("NOW", T0 + M.ROLLBACK_WINDOW)
    s.succ(0, N, 0, expect="RouterNotBindable")                         # R0: window over

    s = new("MIG_TV_14", "MIG-TV-14", "Predecessor customer-paused; migrate: the successor inherits the pause bit").single_fixture()
    s.op("PAUSE", 0, 0, M.PAUSE_CUSTOMER, 1)
    s.charge(0, 0, 1, 10, 1, expect="MandateNotConsumable")
    s.lock(1, 0)
    s.succ(0, N, 1)
    s.charge(0, 1, 1, 10, 1, expect="MandateNotConsumable")
    s.op("PAUSE", 0, 0, M.PAUSE_CUSTOMER, 0)                            # explicit resume
    s.charge(0, 1, 1, 10, 1)

    s = new("MIG_TV_15", "MIG-TV-15", "Revision on the same router with higher caps and fresh consent; migration kind with the same router").single_fixture()
    s.op("TERMS_COPY", 5, 0).op("TERMS_SET", 5, TF["T_CAP"], 1, 0, 60)
    s.succ(0, N, 0, terms=5, expect="WrongKind")
    s.succ(0, V, 0, terms=5)                                            # the mask is computed by AUTH_NEW (bit 2)
    s.status(0, 0, REVOKED, RS_SR).op("EXPECT_ACTIVE_GEN", 0, 1).op("EXPECT_LIVE", 0, 0, 1, 1).auth_routers(0, 1)

    s = new("MIG_TV_17", "MIG-TV-17", "Authorization signed for router B replayed against router C; every bound field is checked").single_fixture()
    s.lock(1, 0)
    s.auth(0, N, 1).op("AUTH_SET", AF["AF_ROUTER"], 2)
    s.op("SUCCESSOR", 0, N, 1, 0, 0, expect="AuthorizationMismatch")
    s.op("ACTIVATE", 9, 0, 0, 0, 0)                                     # another lineage whose id the first one's authorization must not carry
    for field, value in (("AF_CUSTOMER", 1), ("AF_LINEAGE", 9), ("AF_KIND", E), ("AF_TERMS", 0xBAD), ("AF_CODEHASH", 0xBAD),
                         ("AF_VERSION", 99), ("AF_SNAPSHOT", 0xBAD), ("AF_PIN", 3), ("AF_PRED", 5)):
        s.auth(0, N, 1).op("AUTH_SET", AF[field], value)
        s.op("SUCCESSOR", 0, N, 1, 0, 0, expect="AuthorizationMismatch")
    s.succ(0, N, 1)                                                     # the correct authorization is accepted

    # ---- MIG-TV-21 (modified): the widened mask
    s = new("MIG_TV_21", "MIG-TV-21", "kind NORMAL or EMERGENCY with widenedMask != 0; kind REVISION with a mask that differs from the computed one").single_fixture()
    s.lock(1, 0)
    s.succ(0, N, 1, sets=[(AF["AF_MASK"], 1)], expect="TermsNotContained")
    s.succ(0, E, 1, sets=[(AF["AF_MASK"], 4)], expect="TermsNotContained")
    s.grant(1, 0)
    s.op("TERMS_COPY", 5, 0).op("TERMS_SET", 5, TF["T_CAP"], 1, 0, 60)
    s.succ(0, V, 0, terms=5, sets=[(AF["AF_MASK"], 0)], expect="WidenedMaskMismatch")
    s.succ(0, V, 0, terms=5, sets=[(AF["AF_MASK"], 4 | 1)], expect="WidenedMaskMismatch")
    s.op("TERMS_SET", 5, TF["T_MERCHANT"], 0, 0, 0xA2)
    s.succ(0, V, 0, terms=5, expect="LineageConstantsChanged")
    s.op("TERMS_SET", 5, TF["T_MERCHANT"], 0, 0, 0xA1)
    s.succ(0, V, 0, terms=5)

    # ---- MIG-TV-20 (K.6) and MIG-TV-21: the bounds version (ADR-020, finding F-09)
    s = new("MIG_TV_20_K6", "MIG-TV-20", "K.6 bounds version: a migration with version +1 or -1 is not contained; a revision may change it (widenedMask bit 6, both directions)",
            "the price band of a version is read from the registry and never changes; the model registry is protocol_model.band: 1 = [98, 102], 2 = [95, 105], 0 = empty"
            ).single_fixture()
    s.lock(1, 0)
    s.op("TERMS_COPY", 5, 0).op("TERMS_SET", 5, TF["T_BVER"], 0, 0, 2)          # version +1
    s.op("CHK_CONTAINED", 5, 0, 0, 1 << 5).op("CHK_WIDENED", 5, 0, 0, 1 << 6)
    s.op("TERMS_SET", 5, TF["T_BVER"], 0, 0, 0)                                  # version -1 (the empty band)
    s.op("CHK_CONTAINED", 5, 0, 0, 1 << 5).op("CHK_WIDENED", 5, 0, 0, 1 << 6)
    s.op("TERMS_SET", 5, TF["T_BVER"], 0, 0, 1)                                  # the same version
    s.op("CHK_CONTAINED", 5, 0, 0, 0).op("CHK_WIDENED", 5, 0, 0, 0)
    s.op("TERMS_SET", 5, TF["T_BVER"], 0, 0, 2)
    s.succ(0, N, 1, terms=5, expect="TermsNotContained")                         # NORMAL, version +1
    s.op("TERMS_SET", 5, TF["T_BVER"], 0, 0, 0)
    s.succ(0, N, 1, terms=5, expect="TermsNotContained")                         # NORMAL, version -1
    s.status(0, 0, ACTIVE)
    s.grant(1, 0)                                                                # the revision stays on R0
    s.op("TERMS_SET", 5, TF["T_BVER"], 0, 0, 2)
    s.succ(0, V, 0, terms=5, sets=[(AF["AF_MASK"], 0)], expect="WidenedMaskMismatch")          # a version change is bit 6
    s.auth(0, V, 0, terms=5)                                                     # newTermsHash = hashStruct of the version-2 terms
    s.op("SUCCESSOR", 0, V, 0, 0, 0, expect="AuthorizationMismatch")             # the successor named in the call has version 1: the hash differs
    s.succ(0, V, 0, terms=5)                                                     # the mask computed by AUTH_NEW (1 << 6) is accepted
    s.status(0, 0, REVOKED, RS_SR).op("EXPECT_ACTIVE_GEN", 0, 1)
    s.op("TERMS_COPY", 6, 0)                                                     # back to version 1: version -1 again, a revision
    s.succ(0, V, 0, terms=6, sets=[(AF["AF_MASK"], 0)], expect="WidenedMaskMismatch")
    s.succ(0, V, 0, terms=6)
    s.op("EXPECT_ACTIVE_GEN", 0, 2)

    # ---- MIG-TV-22 / 40: the boundary of Unusable for the last lineage
    for vid, src, title, amount, exp, bad in (
            ("MIG_TV_22A", "MIG-TV-22", "last lineage NORMAL, old allowance expiration = now: still usable, reverts", 100, T0, True),
            ("MIG_TV_22B", "MIG-TV-22", "last lineage NORMAL, old allowance expiration = now - 1: expired, accepted", 100, T0 - 1, False),
            ("MIG_TV_22C", "MIG-TV-22", "last lineage NORMAL, old allowance amount = 0: accepted", 0, FAR, False),
            ("MIG_TV_40D", "MIG-TV-40", "last lineage NORMAL, old allowance amount > 0 and expiration = now + 1: reverts", 100, T0 + 1, True)):
        s = new(vid, src, title)
        s.routers().lineage(0).grant(1, 1)
        s.op("P2_APPROVE", 0, 1, 0, amount, exp)
        if bad:
            s.succ(0, N, 1, expect=("OldPermissionNotRevoked", 1))
            s.op("NOW", exp + 1)                                         # one second later the allowance is expired
        s.succ(0, N, 1)
        s.status(0, 0, REVOKED, RS_SM).op("EXPECT_LIVE", 0, 0, 1, 0)

    # ---- MIG-TV-23: uint160.max counts as usable and as unbounded
    s = new("MIG_TV_23A", "MIG-TV-23", "Old allowance uint160.max, unexpired, last lineage: counts as usable").single_fixture()
    s.op("P2_APPROVE", 0, 1, 0, MAXU160, FAR)
    s.succ(0, N, 1, expect=("OldPermissionNotRevoked", 1))
    s = new("MIG_TV_23B", "MIG-TV-23", "Old allowance uint160.max, a sibling remains: ResidualAllowanceUnbounded; max - 1 is bounded").sibling_fixture()
    s.op("P2_APPROVE", 0, 1, 0, MAXU160, FAR)
    s.succ(0, N, 1, expect=("ResidualAllowanceUnbounded", 1))
    s.op("P2_APPROVE", 0, 1, 0, MAXU160 - 1, FAR)
    s.succ(0, N, 1)
    s = new("MIG_TV_23C", "MIG-TV-23", "Old allowance uint160.max but expired, a sibling remains: the text of O1N still refuses it (document issue)",
            "Bounded(C,t,R) is defined on the amount alone, so an expired unlimited allowance blocks a normal migration with a sibling").sibling_fixture()
    s.op("P2_APPROVE", 0, 1, 0, MAXU160, T0 - 1)
    s.succ(0, N, 1, expect=("ResidualAllowanceUnbounded", 1))

    # ---- MIG-TV-24: new permission
    s = new("MIG_TV_24", "MIG-TV-24", "New allowance missing, below the per-payment cap, or expired: NewPermissionMissing")
    s.routers().lineage(0).grant(1, 0).lock(1, 0)
    s.succ(0, N, 1, expect=("NewPermissionMissing", 1))                 # none
    s.grant(1, 1, 49)
    s.succ(0, N, 1, expect=("NewPermissionMissing", 1))                 # below the cap of 50
    s.grant(1, 1, 100, T0 - 1)
    s.succ(0, N, 1, expect=("NewPermissionMissing", 1))                 # expired
    s.grant(1, 1, 50, T0)
    s.op("NOW", T0 + 1)
    s.succ(0, N, 1, expect=("NewPermissionMissing", 1))                 # expiration = now - 1
    s.grant(1, 1, 50, T0 + 1)
    s.succ(0, N, 1)                                                     # amount = cap, expiration = now: accepted

    # ---- MIG-TV-25: a stale permit re-grants the old allowance
    s = new("MIG_TV_25", "MIG-TV-25", "After S3 a stale signed permit re-grants the old allowance; the old router tries to charge").single_fixture()
    s.lock(1, 0)
    s.succ(0, N, 1)
    s.op("P2_REGRANT", 0, 1, 0, 100, FAR)
    s.charge(0, 0, 1, 10, 1, gen_plus1=1, expect="MandateNotConsumable")
    s.charge(0, 0, 1, 10, 1, gen_plus1=0, expect="WrongRouter")
    s.auth_routers(0, 2)

    # ---- MIG-TV-26 (modified), 30 ... 34: sibling lineages share the allowance
    s = new("MIG_TV_26", "MIG-TV-26", "Two lineages share t; normal migration of one: no lockdown, the sibling keeps charging",
            "the planner half (a plan containing lockdown(t, Rold) is refused, NC-20) is not executable here").sibling_fixture()
    s.op("SNAP", 0, 0)
    s.succ(0, N, 1)
    s.op("EXPECT_SNAP_EQ", 0, 0).op("P2_EXPECT", 0, 1, 0, 100, FAR)
    s.charge(1, 0, 1, 10, 1)
    s.op("P2_EXPECT", 0, 1, 0, 90, FAR)

    s = new("MIG_TV_30", "MIG-TV-30", "Two lineages, ACTIVE old router, same token, bounded usable allowance; normal migration of A without lockdown").sibling_fixture()
    s.succ(0, N, 1)
    s.status(0, 0, REVOKED, RS_SM).status(1, 0, ACTIVE)
    s.op("P2_EXPECT", 0, 1, 0, 100, FAR)
    s.charge(1, 0, 1, 10, 1)
    s.auth_routers(0, 2).auth_routers(1, 1)
    s.op("EXPECT_LIVE", 0, 0, 1, 1).op("EXPECT_LIVE", 0, 1, 1, 1)

    s = new("MIG_TV_31", "MIG-TV-31", "As 30 with the old allowance uint160.max: ResidualAllowanceUnbounded(t)").sibling_fixture()
    s.op("P2_APPROVE", 0, 1, 0, MAXU160, FAR)
    s.succ(0, N, 1, expect=("ResidualAllowanceUnbounded", 1))
    s.status(0, 0, ACTIVE).op("EXPECT_LIVE", 0, 0, 1, 2)

    s = new("MIG_TV_32", "MIG-TV-32", "A migrated; then normal migration of B (now the last lineage) with the allowance usable; then after lockdown").sibling_fixture()
    s.succ(0, N, 1)
    s.succ(1, N, 1, expect=("OldPermissionNotRevoked", 1))
    s.lock(1, 0)
    s.succ(1, N, 1)
    s.status(1, 0, REVOKED, RS_SM).op("EXPECT_LIVE", 0, 0, 1, 0).op("EXPECT_LIVE", 0, 1, 1, 2).op("EXPECT_EXPOSED", 0, 0, 0)

    s = new("MIG_TV_33", "MIG-TV-33", "Router DISABLED_EMERGENCY; emergency migration of A while (t, Rold) shared with B is usable; after one lockdown; then B").sibling_fixture()
    s.op("REG_DISABLE", 0)
    s.succ(0, E, 1, expect=("OldPermissionNotRevoked", 1))
    s.lock(1, 0)
    s.succ(0, E, 1)
    s.status(1, 0, ACTIVE).auth_routers(1, 0)                          # B stays ACTIVE and unfunded
    s.succ(1, E, 1)                                                    # O1E holds without a further lockdown
    s.status(1, 0, REVOKED, RS_SM).auth_routers(0, 2).auth_routers(1, 2)

    s = new("MIG_TV_34", "MIG-TV-34", "Emergency; A uses t1, B uses t2; lockdown only (t1, Rold), then both")
    s.routers().lineage(0).lineage(1, (2,))
    s.grant(1, 0).grant(2, 0).grant(1, 1)
    s.op("REG_DISABLE", 0)
    s.lock(1, 0)
    s.succ(0, E, 1, expect=("OldPermissionNotRevoked", 2))              # B's token t2 is exposed
    s.lock(2, 0)
    s.succ(0, E, 1)

    # ---- MIG-TV-35: router modes
    for label, tag in (("DEPRECATED_SECURITY", "dep_sec"), ("DISABLED_EMERGENCY", "disabled"), ("SUNSET", "sunset"), ("RETIRED", "retired"),
                       ("ACTIVE", "active"), ("DEPRECATED_STANDARD", "dep_std")):
        for kind in (N, E):
            s = new(f"MIG_TV_35_{tag.upper()}_{'N' if kind == N else 'E'}", "MIG-TV-35",
                    f"Router {label}: kind {'NORMAL' if kind == N else 'EMERGENCY'}")
            s.routers().lineage(0).grant(1, 0).grant(1, 1)
            if tag == "dep_sec":
                s.op("REG_DEPRECATE", 0, 1, M.REASON_SECURITY, 0)
            elif tag == "disabled":
                s.op("REG_DISABLE", 0)
            elif tag in ("sunset", "retired"):
                s.op("REG_DEPRECATE", 0, 1, M.REASON_STANDARD, 0).op("NOW", T0 + M.MIN_NOTICE_STANDARD).op("REG_SUNSET", 0)
                if tag == "retired":
                    s.op("NOW", T0 + M.MIN_NOTICE_STANDARD + M.RETENTION).op("REG_RETIRE", 0)
            elif tag == "dep_std":
                s.op("REG_DEPRECATE", 0, 1, M.REASON_STANDARD, 0)
            s.lock(1, 0)
            emergency_mode = tag in ("dep_sec", "disabled", "sunset", "retired")
            s.op("EXPECT_MODE", 0, M.MODE_EMERGENCY if emergency_mode else M.MODE_NORMAL, int(tag in ("active", "dep_std", "dep_sec")),
                 int(tag in ("active", "dep_std", "dep_sec")))
            if kind == N and emergency_mode:
                s.succ(0, N, 1, expect="ModeMismatch")
                s.status(0, 0, ACTIVE)
            else:
                s.succ(0, kind, 1)
                s.status(0, 0, REVOKED, RS_SM)

    # ---- MIG-TV-36: an expired sibling that is not retired
    s = new("MIG_TV_36A", "MIG-TV-36", "Sibling B expired but not retired; normal migration of A with a usable allowance succeeds (the index over-counts)"
            ).sibling_fixture(expires_b=T0 + 1000)
    s.op("NOW", T0 + 2000).op("EXPECT_LIVE", 0, 0, 1, 2)
    s.succ(0, N, 1)
    s.op("EXPECT_LIVE", 0, 0, 1, 1)
    s = new("MIG_TV_36B", "MIG-TV-36", "Sibling B expired and retired: the same call reverts OldPermissionNotRevoked"
            ).sibling_fixture(expires_b=T0 + 1000)
    s.op("NOW", T0 + 2000)
    s.op("RETIRE", 1, 0)
    s.op("EXPECT_LIVE", 0, 0, 1, 1).status(1, 0, ACTIVE, 0, 1)
    s.succ(0, N, 1, expect=("OldPermissionNotRevoked", 1))
    s.op("RETIRE", 1, 0, expect="NotRetirable")
    s.lock(1, 0)
    s.succ(0, N, 1)
    s = new("MIG_TV_36C", "MIG-TV-36", "retire of a live mandate is refused (it exists only for EXPIRED or EXHAUSTED mandates)").single_fixture()
    s.op("RETIRE", 0, 0, expect="NotRetirable")
    s.op("EXPECT_LIVE", 0, 0, 1, 1)

    # ---- MIG-TV-37: the exposure limit
    s = new("MIG_TV_37", "MIG-TV-37", "Eight distinct tokens live on one router; a ninth is refused; after revoking the only mandate that uses one, accepted")
    s.routers()
    s.lineage(0, (1, 2, 3)).lineage(1, (4, 5, 6)).lineage(2, (7,)).lineage(3, (8,))
    s.op("EXPECT_EXPOSED", 0, 0, 8)
    s.op("TERMS_RESET", 4, S.TERMS_PRESETS["TP_ONE"]).op("TERMS_SET", 4, TF["T_TOKENS"], 9, 0, 0)
    s.op("ACTIVATE", 4, 0, 0, 4, 0, expect="ExposureLimit")
    s.op("REVOKE", 3, 0)
    s.op("EXPECT_EXPOSED", 0, 0, 7)
    s.op("ACTIVATE", 4, 0, 0, 4, 0)
    s.op("EXPECT_EXPOSED", 0, 0, 8).op("EXPECT_LIVE", 0, 0, 8, 0).op("EXPECT_LIVE", 0, 0, 9, 1).op("EXPECT_INDEX_EXACT", 0)
    s = new("MIG_TV_37B", "MIG-TV-37", "X2 on a successor: the new router already exposes eight tokens; the successor's ninth token is refused")
    s.routers()
    s.lineage(0, (1, 2, 3), router=1).lineage(1, (4, 5, 6), router=1).lineage(2, (7, 8), router=1)
    s.lineage(3, (9,), router=0)
    s.grant(9, 0).grant(9, 1)
    s.op("REG_DISABLE", 0)
    s.lock(9, 0)
    s.succ(3, E, 1, expect="ExposureLimit")
    s.op("REDUCE_DROP", 2, 0, 8)                                       # the token-removing reduce: seven tokens left on R1
    s.op("EXPECT_EXPOSED", 0, 1, 7)
    s.succ(3, E, 1)                                                    # exactly MAX_EXPOSED_TOKENS_PER_ROUTER after the successor
    s.op("EXPECT_EXPOSED", 0, 1, 8).op("EXPECT_LIVE", 0, 1, 8, 0).op("EXPECT_LIVE", 0, 1, 9, 1).op("EXPECT_INDEX_EXACT", 0)

    # ---- MIG-TV-38: the emergency batch
    nb = M.MAX_BATCH
    s = new("MIG_TV_38", "MIG-TV-38", f"Emergency: one lockdown covering every exposed token; {nb} successors succeed; one more exceeds MAX_BATCH",
            "MAX_BATCH belongs to a plan step (MigrationQueue, ADR-022), which the model does not have: the batch limit is the pure check W_BATCH and the "
            f"{nb} successors run one by one")
    s.routers()
    for i in range(nb):
        s.lineage(i, (1,), terms=0)
    s.grant(1, 0).grant(1, 1)
    s.op("REG_DISABLE", 0)
    s.op("EXPECT_LIVE", 0, 0, 1, nb)
    s.succ(0, E, 1, terms=0, expect=("OldPermissionNotRevoked", 1))
    s.lock(1, 0)
    s.op("W_BATCH", nb).op("W_BATCH", nb + 1, expect="BatchTooLarge")
    for i in range(nb):
        s.succ(i, E, 1, terms=0)
    s.op("EXPECT_LIVE", 0, 0, 1, 0).op("EXPECT_LIVE", 0, 1, 1, nb).op("EXPECT_INDEX_EXACT", 0)

    # ---- MIG-TV-39: non-interference
    for kind, label in ((N, "NORMAL"), (E, "EMERGENCY"), (V, "REVISION")):
        s = new(f"MIG_TV_39_{label}", "MIG-TV-39", f"Snapshot of every Permit2 allowance and of the sibling before and after activateSuccessor, kind {label}"
                ).sibling_fixture()
        if kind == E:
            s.op("REG_DISABLE", 0).lock(1, 0)
        if kind == V:
            s.op("TERMS_COPY", 5, 0).op("TERMS_SET", 5, TF["T_CAP"], 1, 0, 60)
        s.op("SNAP", 0, 0)
        if kind == V:
            s.succ(0, V, 0, terms=5)
        else:
            s.succ(0, kind, 1)
        s.op("EXPECT_SNAP_EQ", 0, 0).op("EXPECT_INDEX_EXACT", 0)

    # ---- MIG-TV-41 / 42: the shared budget
    s = new("MIG_TV_41", "MIG-TV-41", "approve(t, R, 50, T+10) for another lineage overwrites the shared slot; the sibling's later charge reverts",
            "the planner half (NC-21 refuses the step) is not executable here").sibling_fixture()
    s.op("P2_APPROVE", 0, 1, 0, 100, T0 + 1000)
    s.op("P2_APPROVE", 0, 1, 0, 50, T0 + 10)                          # the other lineage's plan lowers the shared slot (F2)
    s.op("P2_EXPECT", 0, 1, 0, 50, T0 + 10)
    s.charge(1, 0, 1, 40, 1)                                           # still fine at T0 within the lowered budget
    s.op("NOW", T0 + 11)
    s.charge(1, 0, 1, 5, 2, expect=("AllowanceExpired", T0 + 10))
    s.op("P2_APPROVE", 0, 1, 0, 5, T0 + 1000)
    s.charge(1, 0, 1, 10, 3, expect=("InsufficientAllowance", 5))
    s.op("EXPECT_USAGE", 1, 1, 40)

    s = new("MIG_TV_42", "MIG-TV-42", "Two lineages share an allowance of 100; A charges 60, then B charges 60: B reverts InsufficientAllowance(40)",
            "the planner half (ALLOWANCE_SHORTFALL before submitting) is not executable here"
            ).sibling_fixture(extra_a=[(TF["T_CAP"], 1, 0, 60)], extra_b=[(TF["T_CAP"], 1, 0, 60)])
    s.charge(0, 0, 1, 60, 1)
    s.charge(1, 0, 1, 60, 1, expect=("InsufficientAllowance", 40))
    s.op("EXPECT_USAGE", 0, 1, 60).op("EXPECT_USAGE", 1, 1, 0).op("P2_EXPECT", 0, 1, 0, 40, FAR)
    s.charge(1, 0, 1, 40, 1)
    s.op("P2_EXPECT", 0, 1, 0, 0, FAR)

    # ---- MIG-TV-27: MIXED flow
    s = new("MIG_TV_27", "MIG-TV-27", "A charge settles on the old router after the customer signed auth and before S3: auth stays valid, counters include the charge").single_fixture()
    s.auth(0, N, 1)
    s.charge(0, 0, 1, 10, 1)
    s.lock(1, 0)
    s.op("SUCCESSOR", 0, N, 1, 0, 0)
    s.op("EXPECT_USAGE", 0, 1, 10)
    s.charge(0, 1, 1, 10, 2)
    s.op("EXPECT_USAGE", 0, 1, 20)

    # ---- MIG-TV-44 / 45
    s = new("MIG_TV_44", "MIG-TV-44", "NORMAL_PARTIAL where every token of the predecessor is shared; legacy flow S1 then S3: no S2, no Q2",
            "the plan kind and the absence of a hold are planner and orchestrator behavior; the on-chain half is that no lockdown is required"
            ).sibling_fixture()
    s.op("P2_APPROVE", 0, 1, 1, 100, FAR)                               # S1
    s.succ(0, N, 1)                                                      # S3, no S2
    s.auth_routers(0, 2).auth_routers(1, 1)
    s.charge(1, 0, 1, 10, 1)                                             # the sibling never stopped charging
    s.op("P2_EXPECT", 0, 1, 0, 90, FAR)

    s = new("MIG_TV_45", "MIG-TV-45", "Emergency: a stale signed permit re-grants (t, Rold) after the lockdown and before S3; the plan re-locks; a later re-grant is inert"
            ).sibling_fixture()
    s.op("REG_DISABLE", 0)
    s.lock(1, 0)
    s.op("P2_REGRANT", 0, 1, 0, 100, FAR)
    s.succ(0, E, 1, expect=("OldPermissionNotRevoked", 1))
    s.lock(1, 0)
    s.succ(0, E, 1)
    s.op("P2_REGRANT", 0, 1, 0, 100, FAR)
    s.auth_routers(0, 2)                                                 # inert for the migrated lineage
    s.charge(0, 0, 1, 10, 1, gen_plus1=1, expect="MandateNotConsumable")
    s.op("P2_EXPECT_NONCE", 0, 1, 0, 2)

    # ---- L1: which predecessors may be superseded
    s = new("MIG_TV_L1", "MIG-TV-12", "L1: a stale predecessor, a revoked one").single_fixture()
    s.lock(1, 0)
    s.succ(0, N, 1)                                                      # generation 1 on R1
    s.grant(1, 0).lock(1, 1)
    s.op("SETREG", 2, 1)                                                 # name generation 0 as the predecessor
    s.succ(0, N, 0, expect="WrongPredecessor")                           # L.activeMandateId is generation 1
    s.op("SETREG", 2, 0)
    s.op("REVOKE", 0, 0)
    s.succ(0, N, 0, expect="WrongPredecessor")                           # the active mandate is revoked: terminal
    s = new("MIG_TV_L1B", "MIG-TV-12", "L1: successor of an expired predecessor")
    s.routers().lineage(0, expires=T0 + 500).grant(1, 0).grant(1, 1).lock(1, 0)
    s.op("NOW", T0 + 500)
    s.succ(0, N, 1, expect="WrongPredecessor")                           # now >= expiresAt

    # ---- A1 / A2: who may call and when
    s = new("MIG_TV_A1", "MIG-TV-17", "A1: who may authenticate a successor (pin signatureMode ECDSA_KEY, ERC-1271, stored pin governs)").single_fixture()
    s.lock(1, 0)
    pin7702 = M.example_pin("pin7702")
    s.op("PIN_PRESET", 1, PP["PP_7702"]).op("PIN_SET", 1, PF["PF_VERSION"], 2)
    s.succ(0, N, 1, access=(0, M.SIG_NONE, 0), expect="NotCustomer")
    s.succ(0, N, 1, access=(0, M.SIG_ECDSA, 0), expect="NotCustomer")                              # ECDSA path, invalid signature
    s.succ(0, N, 1, access=(0, M.SIG_ERC1271, 1), expect="SignatureModeNotPermitted")             # the stored pin says ECDSA_KEY
    s.op("ACCT_SET", 0, pin7702.accountCodeHash).op("DELEG_SET", pin7702.delegate, pin7702.delegateCodeHash)
    s.succ(0, N, 1, pin=1, access=(0, M.SIG_ERC1271, 1), expect="SignatureModeNotPermitted")      # the NEW pin (ERC1271) must not govern
    s.succ(0, N, 1, pin=1, access=(0, M.SIG_ECDSA, 1))                                             # valid ECDSA signature: accepted
    s = new("MIG_TV_A1B", "MIG-TV-17", "A1: a DIRECT_ONLY pin accepts no signature").single_fixture()
    s.lock(1, 0)
    s.op("PIN_PRESET", 1, PP["PP_EOA"]).op("PIN_SET", 1, PF["PF_SIG"], 0)
    s.op("ACTIVATE", 5, 0, 0, 0, 1)                                                                # lineage 5 with a DIRECT_ONLY pin
    s.grant(1, 0).lock(1, 0)
    s.succ(5, N, 1, pin=1, access=(0, M.SIG_ECDSA, 1), expect="SignatureModeNotPermitted")
    s.succ(5, N, 1, pin=1, access=(0, M.SIG_ERC1271, 1), expect="SignatureModeNotPermitted")
    s.succ(5, N, 1, pin=1)
    s = new("MIG_TV_A1C", "MIG-TV-17", "A1: the ERC-1271 path needs the stored pin to hold on the live account").single_fixture()
    s.op("PIN_PRESET", 1, PP["PP_7702"])
    s.op("ACCT_SET", 0, pin7702.accountCodeHash).op("DELEG_SET", pin7702.delegate, pin7702.delegateCodeHash)
    s.op("ACTIVATE", 5, 0, 0, 0, 1)
    s.grant(1, 0).lock(1, 0)
    s.op("DELEG_SET", pin7702.delegate, 0xBAD)                                                    # the delegate was redeployed
    s.succ(5, N, 1, pin=1, access=(0, M.SIG_ERC1271, 1), expect=("AccountCodeChanged", 2))
    s.op("DELEG_SET", pin7702.delegate, pin7702.delegateCodeHash)
    s.succ(5, N, 1, pin=1, access=(0, M.SIG_ERC1271, 0), expect="NotCustomer")                    # valid path, signature rejected
    s.succ(5, N, 1, pin=1, access=(0, M.SIG_ERC1271, 1))
    s = new("MIG_TV_A2", "MIG-TV-17", "A2: deadline (now = deadline accepted, deadline + 1 second refused) and single-use nonce").single_fixture()
    s.lock(1, 0)
    s.succ(0, N, 1, sets=[(AF["AF_DEADLINE"], T0 - 1)], expect="AuthorizationExpired")
    s.succ(0, N, 1, sets=[(AF["AF_DEADLINE"], T0), (AF["AF_NONCE"], 77)])
    s.lock(1, 1).grant(1, 0)
    s.succ(0, N, 0, sets=[(AF["AF_NONCE"], 77)], expect="AuthorizationReplayed")
    s.succ(0, N, 0, sets=[(AF["AF_NONCE"], 78)])

    # ---- MIG-TV-29 (modified): the pin in a successor
    s = new("MIG_TV_29", "MIG-TV-29", "Successor with an accountPin that is malformed, does not match the live account, or has the wrong pinVersion").single_fixture()
    s.lock(1, 0)
    s.op("PIN_PRESET", 1, PP["PP_EOA"]).op("PIN_SET", 1, PF["PF_DELEGATE"], 0xABAB)
    s.succ(0, N, 1, pin=1, expect="AccountPinMalformed")                                            # mode 1 with a delegate
    s.op("PIN_PRESET", 1, PP["PP_7702"])
    s.succ(0, N, 1, pin=1, expect="AccountPinMismatch")                                             # well formed; the account has no delegation
    s.op("PIN_PRESET", 1, PP["PP_EOA"]).op("PIN_SET", 1, PF["PF_VERSION"], 2)
    s.succ(0, N, 1, pin=1, expect="PinVersionMismatch")                                             # unchanged pin, version not the next
    s.op("PIN_PRESET", 1, PP["PP_EOA"]).op("PIN_SET", 1, PF["PF_SIG"], 0)
    s.succ(0, N, 1, pin=1, expect="PinVersionMismatch")                                             # changed pin, version unchanged
    s.op("PIN_SET", 1, PF["PF_VERSION"], 2)
    s.succ(0, N, 1, pin=1)                                                                          # changed pin, version + 1
    s.op("EXPECT_PINVER", 0, 2)

    s = new("MIG_TV_29B", "MIG-TV-29", "Successor to a 7702 pin: account and delegate hashes read live; an unchanged pin keeps the version").single_fixture()
    s.op("ACCT_SET", 0, pin7702.accountCodeHash).op("DELEG_SET", pin7702.delegate, pin7702.delegateCodeHash)
    s.lock(1, 0)
    s.op("PIN_PRESET", 1, PP["PP_7702"]).op("PIN_SET", 1, PF["PF_VERSION"], 2)
    s.succ(0, N, 1, pin=1)                                                                          # EOA -> 7702: changed pin, version 2
    s.op("EXPECT_PINVER", 0, 2)
    s.lock(1, 1).grant(1, 0)
    s.op("DELEG_SET", pin7702.delegate, 0)                                                          # the delegate has no code any more
    s.succ(0, N, 0, pin=1, expect="AccountPinMismatch")
    s.op("DELEG_SET", pin7702.delegate, pin7702.delegateCodeHash)
    s.succ(0, N, 0, pin=1)                                                                          # field-for-field equal pin: version unchanged
    s.op("EXPECT_PINVER", 0, 2)

    # ---- MIG-TV-28
    s = new("MIG_TV_28", "MIG-TV-28", "MIGRATION (either kind) to the same router; REVISION to a different router; a kind outside {0,1,2}").single_fixture()
    s.lock(1, 0)
    s.succ(0, N, 0, expect="WrongKind")
    s.succ(0, E, 0, expect="WrongKind")
    s.succ(0, V, 1, expect="WrongKind")
    s.succ(0, 3, 1, expect="WrongKind")
    s.status(0, 0, ACTIVE)

    # ---- MIG-TV-43: random sequences, the index after every step
    for seed in range(1, 7):
        out.append(random_program(seed))
    return out


# ----------------------------------------------------------------------------------------------------------------- MIG-TV-43
def random_program(seed, steps=70):
    """A seeded random sequence of activate, successor (both kinds), revoke, retire, token-removing reduce, grants, lockdowns,
    registry changes and time over two customers and two routers. The oracle (the Python model) decides the outcome of every
    call; the program records it as the expectation and checks, after every step, that the exposure index equals the recomputed
    number of recorded-active mandates (EXPECT_INDEX_EXACT), which is never below the true live number (I-MIG-10)."""
    rng = random.Random(0xF00D + seed)
    s = Scenario(f"MIG_TV_43_{seed}", "MIG-TV-43", f"Random sequence {seed}: the exposure index equals the recomputed count after every step")
    w = S.World()
    a = s.a
    now = [T0]
    live_slots = []

    def emit(name, *args):
        """Run on the oracle; record the instruction with the outcome the oracle produced."""
        padded = list(args) + [0] * (5 - len(args))
        ins = [S.OP[name]] + padded + [0, 0]
        try:
            res = getattr(w, "op_" + name)(*padded)
            assert res is None, res
        except M.Revert as r:
            sel, arg = M.ERROR_ID[r.name], r.arg
            kind = M.ERROR_BY_ID[sel][3]
            if kind == "token":
                arg -= 0x7000
            elif kind == "key":
                arg -= 0x9000
            ins[6], ins[7] = sel, arg
        a.words += ins
        a.listing.append(S.disassemble(ins)[0])

    emit("REG_REGISTER", 0)
    emit("REG_REGISTER", 1)
    emit("PIN_PRESET", 0, PP["PP_EOA"])
    free = list(range(8))
    for _step in range(steps):
        r = rng.random()
        if r < 0.22 and free:
            slot = free.pop(0)
            toks = sorted(rng.sample([1, 2, 3, 4], rng.randint(1, 3)))
            emit("TERMS_RESET", slot, S.TERMS_PRESETS["TP_ONE"])
            emit("TERMS_SET", slot, TF["T_TOKENS"], *(toks + [0] * (3 - len(toks))))
            emit("TERMS_SET", slot, TF["T_EXPIRES"], 0, 0, T0 + rng.choice([3000, 6000, 1_000_000]))
            emit("ACTIVATE", slot, rng.randint(0, 1), rng.randint(0, 1), slot, 0)
            if slot in w.lineage:
                live_slots.append(slot)
        elif r < 0.50 and live_slots:
            slot = rng.choice(live_slots)
            P = w.mgr.mandates[w.mgr.lineages[w.lineage[slot]].active]
            new_router = 1 if P.router == S.router_addr(0) else 0
            kind = rng.choice([N, N, E])
            cust = P.customer - 0xC000
            for t in P.terms.tokens:
                emit("P2_APPROVE", cust, t - 0x7000, new_router, 100, FAR)
                if rng.random() < 0.7:
                    emit("P2_LOCKDOWN", cust, t - 0x7000, 1 - new_router)
            emit("AUTH_NEW", slot, kind, new_router, slot, 0)
            emit("SUCCESSOR", slot, kind, new_router, slot, 0)
        elif r < 0.62 and live_slots:
            emit("REVOKE", rng.choice(live_slots), 0)
        elif r < 0.74 and live_slots:
            emit("RETIRE", rng.choice(live_slots), 0)
        elif r < 0.82 and live_slots:
            slot = rng.choice(live_slots)
            toks = w.mgr.mandates[w.mgr.lineages[w.lineage[slot]].active].terms.tokens
            emit("REDUCE_DROP", slot, 0, rng.choice(toks) - 0x7000)
        elif r < 0.90:
            cust, t, rt = rng.randint(0, 1), rng.randint(1, 4), rng.randint(0, 1)
            if rng.random() < 0.5:
                emit("P2_APPROVE", cust, t, rt, rng.choice([0, 100, MAXU160]), rng.choice([FAR, T0 - 1, FAR]))
            else:
                emit("P2_LOCKDOWN", cust, t, rt)
        elif r < 0.96:
            now[0] += rng.choice([100, 2500, 5000])
            emit("NOW", now[0])
        else:
            emit("REG_DISABLE", rng.randint(0, 1))
        for c in (0, 1):
            emit("EXPECT_INDEX_EXACT", c)
    return s
