#!/usr/bin/env python3
"""The complete exported vector suite of revision 0.5, and the machinery to run it against the Python model or a mutant of it.

`build_suite()` assembles every vector family:
  hashes      constants of tools/eip712_vectors.py (quote digests, identifiers and their router independence, route hash, fiat rounding,
              designator hashes, pin constants, the snapshot hash, the Permit2 usability boundary)
  terms       containment and monotone-authority tuples: the explicit witnesses of the clause necessity check (K.1..K.9), the
              clause-by-clause boundaries of MIG-TV-20, the reference snapshot cases, integer-width cases and a seeded sample of
              random (successor, predecessor, state, payment, expected) tuples for Lemma M
  scenarios   programs of tools/scenario_vm.py: MIG-TV-xx, ACP-TV-xx, CAP-TV-xx, registry, timestamp and integer-width boundaries
  tables      the reachable state and transition tables of the single-lineage and the shared-allowance explorations
  backend     vectors that only the planner, the orchestrator or the signer policy can execute (ACP-TV-41..44 evidence states)
Every vector carries its source id. `run_*` executes the suite on the model (the oracle) or on a mutant and reports what fails.
"""
import functools
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import eip712_vectors as V  # noqa: E402
import explore as X  # noqa: E402
import lemma_gen as LG  # noqa: E402
import protocol_model as M  # noqa: E402
import scenario_vm as S  # noqa: E402
import vectors_mig  # noqa: E402
import vectors_misc  # noqa: E402

LEMMA_SEED = 20261016
LEMMA_PAIRS_CONTAINED = 150
LEMMA_PAIRS_OTHER = 60


# ----------------------------------------------------------------------------------------------------------------- scenarios
class Vec:
    def __init__(self, vid, source, title, group, words, listing=None, note=""):
        self.id, self.source, self.title, self.group, self.words, self.listing, self.note = vid, source, title, group, words, listing, note


def scenario_vectors():
    out = []
    for fn, group in ((vectors_mig.build_all, "mig"), (vectors_misc.build_acp, "acp"), (vectors_misc.build_cap, "cap"),
                      (vectors_misc.build_boundaries, "boundary")):
        for sc in fn():
            out.append(Vec(sc.id, sc.source, sc.title, group, sc.a.prog(), S.disassemble(sc.a.prog()), sc.note))
    ids = [v.id for v in out]
    assert len(ids) == len(set(ids)), "duplicate scenario id"
    return out


# ----------------------------------------------------------------------------------------------------------------- terms tuples
def _zero_state():
    return dict(used={t: {f: 0 for f in LG.USED_FAMILIES} for t in LG.TOKENS}, fiatUsed={f: 0 for f in LG.FIAT_USED}, chargesInPeriod=0)


def clause_witnesses():
    """The explicit witnesses of the clause necessity check (document 12 section 5.3.3): for each clause K.x a successor that violates
    only that clause, and a payment, in a stated lineage state, that the successor accepts and the predecessor rejects."""
    return LG.witness_cases()


def boundary_cases():
    """MIG-TV-20: one case per clause, the equal value accepted and the value one step beyond refused."""
    pred = LG.rnd_snapshot(random.Random(7))
    pred.update(tokens=["T1", "T2"], caps={t: dict({f: 100 for f in LG.FAMILIES}, perPaymentMax=50) for t in ("T1", "T2")}, expiresAt=500,
                merchantId="M", maxQuoteAge=60, boundsVersion=1, maxChargesPerPeriod=2, minInterval=50, maxFeeBps=100)
    for f in LG.FIAT:
        pred[f] = 200
    import copy
    cases = []

    def add(label, mutate_fn):
        s = copy.deepcopy(pred)
        mutate_fn(s)
        cases.append((label, s))
    add("MIG-TV-20 equal terms", lambda s: None)
    add("MIG-TV-20 K.1 expiry equal", lambda s: s.update(expiresAt=500))
    add("MIG-TV-20 K.1 expiry +1", lambda s: s.update(expiresAt=501))
    add("MIG-TV-20 K.1 expiry -1", lambda s: s.update(expiresAt=499))
    add("MIG-TV-20 K.2 other merchant", lambda s: s.update(merchantId="M2"))
    add("MIG-TV-20 K.2 other recipient policy", lambda s: s.update(recipientPolicy="R2"))
    add("MIG-TV-20 K.2 other subscription", lambda s: s.update(subscriptionRef="S2"))
    add("MIG-TV-20 K.2 other period", lambda s: s.update(periodSeconds=101))
    add("MIG-TV-20 K.2 other anchor", lambda s: s.update(anchorStartsAt=1))
    add("MIG-TV-20 K.3 one token fewer", lambda s: (s["tokens"].remove("T2"), s["caps"].pop("T2")))
    add("MIG-TV-20 K.3 extra token", lambda s: (s["tokens"].append("T3"), s["caps"].update({"T3": {f: 100 for f in LG.FAMILIES}})))
    for fam in LG.FAMILIES:
        add(f"MIG-TV-20 K.4 {fam} +1", lambda s, f=fam: s["caps"]["T1"].update({f: s["caps"]["T1"][f] + 1}))
        add(f"MIG-TV-20 K.4 {fam} -1", lambda s, f=fam: s["caps"]["T1"].update({f: s["caps"]["T1"][f] - 1}))
        add(f"MIG-TV-20 K.4 {fam} removed (0)", lambda s, f=fam: s["caps"]["T1"].update({f: 0}))
    add("MIG-TV-20 K.5 currency", lambda s: s.update(currency=978))
    for fam in LG.FIAT:
        add(f"MIG-TV-20 K.5 {fam} +1", lambda s, f=fam: s.update({f: s[f] + 1}))
        add(f"MIG-TV-20 K.5 {fam} removed (0)", lambda s, f=fam: s.update({f: 0}))
    add("MIG-TV-20 K.5 quote age +1", lambda s: s.update(maxQuoteAge=61))
    add("MIG-TV-20 K.5 quote age -1", lambda s: s.update(maxQuoteAge=59))
    # K.6: the band of a (token, currency, boundsVersion) never changes, so a migration keeps the version: +1 (version 2, a wider band),
    # -1 (version 0, the empty band), a much wider band (5) and an unpublished version (6, empty band) are all refused; equal terms pass
    add("MIG-TV-20 K.6 bounds version +1", lambda s: s.update(boundsVersion=pred["boundsVersion"] + 1))
    add("MIG-TV-20 K.6 bounds version -1", lambda s: s.update(boundsVersion=pred["boundsVersion"] - 1))
    add("MIG-TV-20 K.6 bounds version 5 (wide band)", lambda s: s.update(boundsVersion=5))
    add("MIG-TV-20 K.6 bounds version unpublished (6)", lambda s: s.update(boundsVersion=6))
    add("MIG-TV-20 K.7 one more charge per period", lambda s: s.update(maxChargesPerPeriod=3))
    add("MIG-TV-20 K.7 charges removed (0)", lambda s: s.update(maxChargesPerPeriod=0))
    add("MIG-TV-20 K.7 one fewer charge per period", lambda s: s.update(maxChargesPerPeriod=1))
    add("MIG-TV-20 K.7 interval -1", lambda s: s.update(minInterval=49))
    add("MIG-TV-20 K.7 interval +1", lambda s: s.update(minInterval=51))
    add("MIG-TV-20 K.8 fee +1", lambda s: s.update(maxFeeBps=101))
    add("MIG-TV-20 K.8 fee -1", lambda s: s.update(maxFeeBps=99))
    add("MIG-TV-20 K.9 extensions", lambda s: s.update(extensionsHash=b"\x01" * 32))
    return pred, cases


def snapshot_cases():
    """The reference snapshot of tools/eip712_vectors.snapshot_vector() and its documented cases."""
    import copy
    pred, ok = V.snapshot_reference()
    t1 = pred["tokens"][0]
    out = [("snapshot narrower", ok, pred)]
    cases = {"longer expiry": ("expiresAt", pred["expiresAt"] + 1), "other merchant": ("merchantId", "0x" + "ac" * 32),
             "higher fee cap": ("maxFeeBps", 101), "bounds version +1": ("boundsVersion", pred["boundsVersion"] + 1),
             "bounds version -1": ("boundsVersion", pred["boundsVersion"] - 1), "faster cadence": ("minInterval", 3600),
             "non-zero extensions": ("extensionsHash", b"\x01" * 32), "more charges per period": ("maxChargesPerPeriod", 2),
             "higher fiat total": ("fiatTotalMax", 60001), "removed fiat total cap": ("fiatTotalMax", 0)}
    for name, (k, val) in cases.items():
        s = copy.deepcopy(ok)
        s[k] = val
        out.append((f"snapshot rejects {name}", s, pred))
    s = copy.deepcopy(ok)
    s["tokens"] = [t1, "0x" + "99" * 20]
    s["caps"]["0x" + "99" * 20] = s["caps"][t1]
    out.append(("snapshot rejects extra token", s, pred))
    s = copy.deepcopy(ok)
    s["caps"][t1]["perPaymentMax"] = pred["caps"][t1]["perPaymentMax"] + 1
    out.append(("snapshot rejects higher per-payment cap", s, pred))
    return out


def terms_vectors():
    """List of (id, source, title, words) tuples for the containment runner; also cross-checks the model against V.contained."""
    out = []
    n = 0
    for label, succ, pred, state, payment in clause_witnesses():
        out.append((f"W_{len(out):03d}", "K." + label[2], label, LG.tuple_words(succ, pred, state, payment)))
    pred, cases = boundary_cases()
    for label, succ in cases:
        out.append((f"B_{len(out):03d}", "MIG-TV-20", label, LG.tuple_words(succ, pred)))
        ok_v, _why = V.contained(succ, pred)
        mask = M.contained_mask(LG.terms_from_snapshot(succ), LG.terms_from_snapshot(pred))
        anchor_only = succ.get("anchorStartsAt", 0) != pred.get("anchorStartsAt", 0)
        assert ok_v == (mask == 0) or anchor_only, (label, ok_v, mask)
    for label, succ, pred in snapshot_cases():
        out.append((f"S_{len(out):03d}", "12 5.3.4", label, LG.tuple_words(succ, pred)))
    rng = random.Random(LEMMA_SEED)
    contained = other = 0
    while contained < LEMMA_PAIRS_CONTAINED or other < LEMMA_PAIRS_OTHER:
        pred = LG.rnd_snapshot(rng)
        succ = LG.mutate(rng, pred)
        mask = M.contained_mask(LG.terms_from_snapshot(succ), LG.terms_from_snapshot(pred))
        ok_v, _why = V.contained(succ, pred)
        assert ok_v == (mask == 0), "the model disagrees with tools/eip712_vectors.contained"
        if mask == 0:
            if contained >= LEMMA_PAIRS_CONTAINED:
                continue
            contained += 1
            for _ in range(3):
                out.append((f"L_{len(out):04d}", "Lemma M", "contained pair, random payment",
                            LG.tuple_words(succ, pred, LG.rnd_state(rng), LG.rnd_payment(rng, pred))))
            out.append((f"L_{len(out):04d}", "Lemma M", "contained pair, payment at the successor's limits",
                        LG.tuple_words(succ, pred, _zero_state(), _boundary_payment(succ))))
        else:
            if other >= LEMMA_PAIRS_OTHER:
                continue
            other += 1
            out.append((f"L_{len(out):04d}", "Lemma M", "uncontained pair, random payment",
                        LG.tuple_words(succ, pred, LG.rnd_state(rng), LG.rnd_payment(rng, pred))))
    # the lemma itself: whenever the successor is contained and accepts, the predecessor accepts
    for vid, _src, label, w in out:
        flags, mask, sa, pa = w[:4]
        if flags and mask == 0 and sa:
            assert pa, (vid, label)
    return out


def _boundary_payment(succ):
    t = succ["tokens"][0]
    cap = succ["caps"][t]["perPaymentMax"]
    return dict(token=t, a=cap if cap else 5, tau=succ["expiresAt"] - 1, merchant=succ["merchantId"] if succ["merchantId"] in ("M", "M2") else "M",
                fiat=None, age=1, price=M.band(succ["boundsVersion"])[0], sinceLast=succ["minInterval"], feeBps=succ["maxFeeBps"])


# ----------------------------------------------------------------------------------------------------------------- hashes
HASH_SEED = 20261017


def _edge_snapshot():
    """Every field at the maximum of its documented width (eip712/types.json): the words must survive the decode and the hash."""
    toks = ["T1", "T2", "T3"]
    u64, u32, u16 = (1 << 64) - 1, (1 << 32) - 1, (1 << 16) - 1
    caps = {t: {f: (1 << 256) - 1 - i for i, f in enumerate(LG.FAMILIES)} for t in toks}
    snap = dict(expiresAt=u64, merchantId="0x" + "ff" * 32, recipientPolicy="0x" + "fe" * 32, subscriptionRef="0x" + "fd" * 32,
                periodSeconds=u64 - 1, anchorStartsAt=u64 - 2, currency=u16, tokens=toks, caps=caps, maxQuoteAge=u32, boundsVersion=u32 - 1,
                maxChargesPerPeriod=u16, minInterval=u32 - 2, maxFeeBps=u16 - 1, extensionsHash=bytes([0xfc]) * 32)
    for i, f in enumerate(LG.FIAT):
        snap[f] = u64 - i
    return snap


def terms_hash_cases():
    """Terms (as the 41 exported words), ids and customer, with the two hashes the Python model computes for them: the snapshot hash
    (the 26 words of eip712/types.json snapshotEncoding: the customer, anchorStartsAt and boundsVersion are covered and the caps are in
    the typed order) and the terms hash = hashStruct(MandateTerms) that a successor authorization carries as newTermsHash (document 12
    A3). The Solidity model must reproduce both for every case, and so must FastPayTypes for the same terms."""
    pred, ok = V.snapshot_reference()
    cases = [("reference predecessor of 12 5.3.4", pred, pred["lineageId"], pred["predecessorId"], pred["generation"], pred["customer"]),
             ("reference narrower successor", ok, ok["lineageId"], ok["predecessorId"], 1, ok["customer"])]
    rng = random.Random(HASH_SEED)
    for i in range(6):
        snap = LG.rnd_snapshot(rng)
        if i % 2:
            snap = LG.mutate(rng, snap)
        cases.append((f"random terms {i}", snap, V.hx(V.tag(f"fastpay.test.lineage.{i}")), V.hx(V.tag(f"fastpay.test.predecessor.{i}")),
                      i + 1, "0x" + V.tag(f"fastpay.test.customer.{i}")[12:].hex()))
    cases.append(("every field at the maximum of its width", _edge_snapshot(), V.hx(V.tag("fastpay.test.lineage.max")),
                  V.hx(V.tag("fastpay.test.predecessor.max")), (1 << 32) - 1, "0x" + "ff" * 20))
    out = []
    for n, (label, snap, lineage, predecessor, generation, customer) in enumerate(cases):
        terms = LG.terms_from_snapshot(snap)
        lid, pid, cust = int(lineage, 16), int(predecessor, 16), int(customer, 16)
        out.append(dict(id=f"TH_{n:02d}", label=label, source="12 section 5.3.2; 12 A3", lineageId=V.hx(M.i2b(lid)), predecessorId=V.hx(M.i2b(pid)),
                        generation=generation, customer=M.addr_hex(cust), words=[str(w) for w in LG.terms_words(snap)],
                        snapshotHash=V.hx(M.i2b(M.snapshot_hash_int(terms, lid, pid, generation, cust))),
                        termsHash=V.hx(M.i2b(M.terms_hash_int(terms)))))
    assert len(set(c["snapshotHash"] for c in out)) == len(out) and len(set(c["termsHash"] for c in out)) == len(out)
    return out


def hash_vectors():
    v = V.VECTOR
    q = V.quote_vector()
    pins = V.pin_vectors()
    out = dict(quote={}, identifiers={}, route={}, fiat=[], pins={}, snapshot={}, permit2=[], designators={})
    out["quote"] = dict(inputs=dict(chainId=v["chainId"], router=v["router"], routerB=v["routerB"], mandateManager=v["mandateManager"],
                                    customer=v["customer"], merchantId=v["merchantId"], subscriptionRef=v["subscriptionRef"],
                                    creationNonce=v["creationNonce"], cycleIndex=v["cycleIndex"], tokenDecimals=v["tokenDecimals"],
                                    quote=v["quote"]), expected=q, source="11 section 4.6")
    cid = v["chainId"]
    lin = V.lineage_id(cid, v["mandateManager"], v["customer"], v["merchantId"], v["subscriptionRef"], v["creationNonce"])
    ids = []
    for gen in (0, 1, 2):
        ids.append(dict(generation=gen, mandateId=V.hx(V.mandate_id(lin, gen))))
    cycles = []
    for k in (0, 1, 2, 7):
        c = V.cycle_id(lin, k)
        cycles.append(dict(cycleIndex=k, cycleId=V.hx(c), paymentId=V.hx(V.payment_id_recurring(cid, v["mandateManager"], lin, c))))
    out["identifiers"] = dict(chainId=cid, mandateManager=v["mandateManager"], customer=v["customer"], merchantId=v["merchantId"],
                              subscriptionRef=v["subscriptionRef"], creationNonce=v["creationNonce"], lineageId=V.hx(lin), mandates=ids,
                              cycles=cycles, source="MIG-TV-19; 12 section 4; 11 section 3.1",
                              payOnce=dict(routerRegistry=v["router"], orderId="0x" + "cc" * 32,
                                           paymentId=V.hx(V.payment_id_pay_once(cid, v["router"], v["merchantId"], "0x" + "cc" * 32))))
    out["route"] = [dict(chainId=c, token=t, routeHash=V.hx(V.route_hash_direct(c, t)), source="11 section 4.1 field 14")
                    for c, t in ((v["chainId"], v["quote"]["token"]), (1, v["quote"]["token"]), (v["chainId"], "0x" + "66" * 20))]
    for amount, price, dec in ((49_990_000, 100 * 10 ** 18, 6), (10_000_001, 1001 * 10 ** 17, 6), (1, 1, 6), (1_000_000, 10 ** 18 * 100, 6),
                               (10 ** 18, 10 ** 18 * 100, 18), (10 ** 5 * 10 ** 18 * 10 ** 18, 99 * 10 ** 18 // 100 + 1, 18),
                               (123_456_789, 98 * 10 ** 18 // 100 * 100, 6), (0, 10 ** 18, 6), (10 ** 40, 10 ** 30, 18), (7, 10 ** 17, 0)):
        out["fiat"].append(dict(amountIn=amount, priceE18=price, tokenDecimals=dec, fiatValueMinor=V.fiat_value_minor(amount, price, dec),
                                source="11 section 4.1; CAP-TV-01..03"))
    d1, d2 = "0x" + "ab" * 20, "0x" + "cd" * 20
    out["designators"] = dict(D1=d1, D2=d2, codeD1=pins["designatorCodeD1"], hashD1=pins["designatorHashD1"], hashD2=pins["designatorHashD2"],
                              keccakEmpty=pins["keccakEmpty"], source="17 section 9")
    out["pins"] = dict(pins, source="17 section 5.1, 9")
    out["pinStructs"] = {k: dict(p, accountCodeHash=V.hx(p["accountCodeHash"]), delegateCodeHash=V.hx(p["delegateCodeHash"]),
                                 implementationFamily=V.hx(p["implementationFamily"])) for k, p in V.example_pins().items()}
    sv = V.snapshot_vector()
    out["snapshot"] = dict(snapshotHash=sv["snapshotHash"], termsHash=sv["termsHash"], source="12 section 5.3.4")
    out["termsHashes"] = terms_hash_cases()
    out["permit2"] = [dict(amount=a, expiration=e, now=n, usable=V.permit2_usable(a, e, n), source="MIG-TV-22, 40")
                      for a, e, n in ((1, 100, 99), (1, 100, 100), (1, 100, 101), (0, 100, 50), (M.UINT160_MAX, 100, 100), (M.UINT160_MAX, 100, 101),
                                      (1, 0, 0), (1, 0, 1), (5, (1 << 48) - 1, (1 << 48) - 1), (5, (1 << 48) - 1, 1 << 48))]
    return out


# ----------------------------------------------------------------------------------------------------------------- tables
@functools.lru_cache(maxsize=None)
def table(config):
    return X.explore(config)


def pack_table(t):
    """states: 8-byte big-endian keys; transitions: 8 bytes each = src(2) dst(2) action(1) sel(1) arg(1) pad(1)."""
    st = b"".join(k.to_bytes(8, "big") for k in t["states"])
    tr = b"".join(src.to_bytes(2, "big") + dst.to_bytes(2, "big") + bytes([action, sel, arg & 0xFF, 0])
                  for (src, action, dst, sel, arg) in t["transitions"])
    return st, tr


# ----------------------------------------------------------------------------------------------------------------- backend-only vectors
class SigCapability:
    """The signature-capability record of document 17 section 5.6 as a state machine (the planner, the orchestrator and the signer
    policy implement it; the contract implements only triggers 1 to 3 on the ERC-1271 path)."""

    def __init__(self, pin_version):
        self.state, self.reason, self.pin_version, self.failures = "VERIFIED", None, pin_version, 0

    def _revoke(self, why):
        self.state, self.reason = "REVOKED", why

    def trigger(self, name, **kw):
        if name == "account_code_changed":
            self._revoke("ACCOUNT_CODE")
        elif name == "delegate_changed":
            self._revoke("DELEGATE")
        elif name == "delegate_code_changed":
            self._revoke("DELEGATE_CODE")
        elif name == "proxy_implementation_changed":
            self._revoke("IMPLEMENTATION")
        elif name == "wallet_version_changed":
            self._revoke("WALLET_VERSION")
        elif name == "probe_changed":
            self._revoke("PROBE")
        elif name == "row_revoked":
            self._revoke("ROW")
        elif name == "preflight_failed":
            self.failures += 1
            if self.failures >= 3:
                self._revoke("PREFLIGHT")
        elif name == "preflight_ok":
            self.failures = 0                                    # restores nothing: re-verification only
        elif name == "evidence_expired":
            if self.state == "VERIFIED":
                self.state = "UNVERIFIED"
        elif name == "pin_version_moved":
            self.pin_version = kw["new_version"]
            if self.state == "VERIFIED":
                self.state = "UNVERIFIED"
        elif name == "family_stopped":
            self._revoke("FAMILY")
        elif name == "reverify":
            self.pin_version = kw["pin_version"]
            self.state, self.reason, self.failures = "VERIFIED", None, 0
        else:
            raise AssertionError(name)

    def sig_transport_allowed(self):
        return self.state == "VERIFIED"


def backend_vectors():
    out = []

    def run(vid, source, title, pin_version, steps):
        rec = SigCapability(pin_version)
        rows = []
        for ev, kw, want_state, want_reason in steps:
            rec.trigger(ev, **kw)
            assert (rec.state, rec.reason) == (want_state, want_reason), (vid, ev, rec.state, rec.reason)
            rows.append(dict(event=ev, args=kw, state=rec.state, reason=rec.reason, pinVersion=rec.pin_version,
                             signatureTransportAllowed=rec.sig_transport_allowed()))
        out.append(dict(id=vid, source=source, title=title, initialPinVersion=pin_version, steps=rows))
    run("ACP_TV_41", "ACP-TV-41", "Mode 3: the proxy implementation changes, the proxy bytecode does not: the chain pin holds, the backend revokes", 1,
        [("proxy_implementation_changed", {}, "REVOKED", "IMPLEMENTATION")])
    run("ACP_TV_42", "ACP-TV-42", "Wallet version label changes with every code hash unchanged: REVOKED(WALLET_VERSION); re-verification with pinVersion + 1 restores", 1,
        [("wallet_version_changed", {}, "REVOKED", "WALLET_VERSION"), ("reverify", {"pin_version": 2}, "VERIFIED", None)])
    run("ACP_TV_43", "ACP-TV-43", "Evidence bound to pinVersion 3; the pin is updated to 4: UNVERIFIED until re-bound and a pre-flight passes", 3,
        [("pin_version_moved", {"new_version": 4}, "UNVERIFIED", None), ("reverify", {"pin_version": 4}, "VERIFIED", None)])
    run("ACP_TV_44", "ACP-TV-44", "Three consecutive pre-flight failures: REVOKED(PREFLIGHT) after the third; one success does not restore it", 1,
        [("preflight_failed", {}, "VERIFIED", None), ("preflight_failed", {}, "VERIFIED", None), ("preflight_failed", {}, "REVOKED", "PREFLIGHT"),
         ("preflight_ok", {}, "REVOKED", "PREFLIGHT"), ("reverify", {"pin_version": 2}, "VERIFIED", None)])
    run("ACP_TV_T_SIG", "ACP-TV-41..44; 17 section 5.6", "Every invalidation trigger of the eleven: the state it leads to", 1,
        [("account_code_changed", {}, "REVOKED", "ACCOUNT_CODE"), ("reverify", {"pin_version": 2}, "VERIFIED", None),
         ("delegate_changed", {}, "REVOKED", "DELEGATE"), ("reverify", {"pin_version": 3}, "VERIFIED", None),
         ("delegate_code_changed", {}, "REVOKED", "DELEGATE_CODE"), ("reverify", {"pin_version": 4}, "VERIFIED", None),
         ("probe_changed", {}, "REVOKED", "PROBE"), ("reverify", {"pin_version": 5}, "VERIFIED", None),
         ("row_revoked", {}, "REVOKED", "ROW"), ("reverify", {"pin_version": 6}, "VERIFIED", None),
         ("evidence_expired", {}, "UNVERIFIED", None), ("reverify", {"pin_version": 7}, "VERIFIED", None),
         ("family_stopped", {}, "REVOKED", "FAMILY")])
    return out


PLANNER_PARTS = [
    dict(id="MIG-TV-26", part="a plan that contains lockdown(t, Rold) while a sibling uses t is refused by the validator (NC-20)", owner="planner"),
    dict(id="MIG-TV-41", part="the planner refuses approve(t, R, 50, T+10) while a sibling relies on the slot (NC-21)", owner="planner"),
    dict(id="MIG-TV-42", part="the orchestrator raises ALLOWANCE_SHORTFALL before submitting a charge that would revert", owner="orchestrator"),
    dict(id="MIG-TV-44", part="NORMAL_PARTIAL with every token shared: no S2, no Q2 state, no hold", owner="planner and orchestrator"),
    dict(id="MIG-TV-04", part="Q2 hold: no charge attempt and no dunning while MIGRATION_IN_PROGRESS", owner="orchestrator"),
    dict(id="MIG-TV-16", part="planner with the experimental flag off never emits a zero-amount permit step", owner="planner"),
    dict(id="MIG-TV-18", part=f"a plan step of {M.MAX_BATCH} successors succeeds, {M.MAX_BATCH + 1} reverts MAX_BATCH (the pure limit is in scenario TB_BATCH; the step on the contracts is in contracts/test/Queue.t.sol)", owner="contracts"),
]


# ----------------------------------------------------------------------------------------------------------------- the suite
@functools.lru_cache(maxsize=None)
def build_suite():
    return dict(scenarios=scenario_vectors(), terms=terms_vectors(), hashes=hash_vectors(), backend=backend_vectors(),
                tables={c: table(c) for c in (S.CONFIG_SINGLE, S.CONFIG_SHARED_X, S.CONFIG_SHARED_Y)})


# ----------------------------------------------------------------------------------------------------------------- running
def run_scenarios(vectors, mut=0, stop_first=False):
    """Returns {vector id: first failure message} for every scenario that fails on the model with mutant `mut`."""
    fails = {}
    for v in vectors:
        try:
            f = S.World(mut).run(v.words, v.id)
        except Exception as exc:                          # a mutant may crash the model (KeyError, ...); that is a kill too
            f = [(v.id, -1, "crash", f"{type(exc).__name__}: {exc}")]
        if f:
            fails[v.id] = f[0]
            if stop_first:
                break
    return fails


def run_terms(tuples, mut=0, stop_first=False):
    """Replay the containment tuples on a mutant of the clause-by-clause containment; `accepts` is the specification's guard model."""
    fails = {}
    for vid, _src, label, w in tuples:
        flags, mask, sa, pa = w[:4]
        got = M.contained_mask(_terms_from_words(w[4:4 + LG.TERMS_WORDS]), _terms_from_words(w[4 + LG.TERMS_WORDS:4 + 2 * LG.TERMS_WORDS]), mut)
        if got != mask:
            fails[vid] = f"{label}: mask {got:#x}, expected {mask:#x}"
            if stop_first:
                break
    return fails


def _terms_from_words(w):
    t = M.Terms(expiresAt=w[0], merchantId=w[1], recipientPolicy=w[2], subscriptionRef=w[3], periodSeconds=w[4], anchorStartsAt=w[5],
                currency=w[6])
    n = w[7]
    for i in range(n):
        a = w[8 + i]
        t.tokens.append(a)
        t.caps[a] = list(w[11 + 6 * i:17 + 6 * i])
    t.fiat = list(w[29:35])
    t.maxQuoteAge, t.boundsVersion, t.maxChargesPerPeriod, t.minInterval, t.maxFeeBps, t.extensionsHash = w[35:41]
    return t


def run_table(t, mut=0, stop_first=False):
    fails = {}
    states = t["states"]
    for i, (src, action, dst, sel, arg) in enumerate(t["transitions"]):
        try:
            err = S.replay_transition(t["config"], states[src], action, sel, arg, states[dst], mut)
        except Exception as exc:                          # a mutant may break the world while it is built (that is a kill)
            err = f"crash: {type(exc).__name__}: {exc}"
        if err:
            fails[f"T{t['config']}_{i}"] = err
            if stop_first:
                break
    return fails
