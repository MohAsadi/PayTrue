#!/usr/bin/env python3
"""Executable model checks for the protocol claims of documents 11, 12 and 17 (revision 0.5).

These are checks on small Python models of the specification (tools/protocol_model.py), not tests of any contract. They exist so that
the proofs in the documents are also exercised by code, and so that a change to a predicate that breaks a claim is caught.

Run:   python -I spec/tools/model_checks.py [--trials N] [--matrix]      (--matrix prints one line per mutant instead of one per family)

  [1] Lemma M (monotone authority): for random predecessor snapshots and random successors, if Contained(succ, snap) holds then every
      payment accepted by the successor is accepted by the predecessor in the same lineage state.
  [2] Clause necessity: for each containment clause K.x, a successor that violates only that clause accepts some payment that the
      predecessor rejects (so no clause is redundant).
  [3] No overlapping authority (I-MIG-8), the original abstract machine: grant, lockdown, re-grant, expiry, successor, revoke.
  [4] Account pin: PIN_OK over the kinds of account hash and the update rule; the typed-struct predicates PIN_WELLFORMED, PIN_OK and
      nextPinVersion over the three example pins and their variations.
  [5] SHARED-ALLOWANCE exploration on the reference model (tools/explore.py): one customer, two lineages sharing token t1 (and B also
      t2), two routers with the modes of the registry, allowance values {none, expired, bounded, unlimited}; every reachable state and
      transition satisfies I-MIG-8, Post3N, Post3E, I-MIG-11, I-MIG-10, Claim 4 and the refusals of R3 and of the unbounded residual.
  [6] SIGNER-SET exploration: rotate, remove a key, stop a set, advance time, verify; SR-1..SR-5 on every reachable state.
  [7] Pin and AUTH truth table over (mode, signatureMode, path, live-account state): I-ACCT-SIG, with the exits.
  [8] MUTATION ANALYSIS: every named mutant of the model (tools/protocol_model.MUTANTS) must make at least one exported vector fail.
  [9] Atomicity: a call that reverts in a scenario changes nothing (the Solidity model reverts all or nothing).
 [10] Bounds registry (ADR-020, F-09): the model band table, K.6 and widenedMask bit 6 as functions of the bounds version, `accepts` reading
      the band of the version, the snapshot hash (26 words, typed cap order) and the terms hash, and the retired scenario field 13.
Exit code 1 on any failure.
"""
import collections
import copy
import itertools
import pathlib
import random
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import eip712_vectors as V  # noqa: E402
import explore as X  # noqa: E402
import lemma_gen as LG  # noqa: E402
import protocol_model as M  # noqa: E402
import scenario_vm as S  # noqa: E402
import vector_suite as VS  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

INF = V.INF
FAMILIES = LG.FAMILIES
FIAT = LG.FIAT
TOKENS = LG.TOKENS
accepts = M.accepts
TABLE_PREFIX = 40                     # the first transitions of each table are replayed per mutant (the Solidity mutation test uses the same prefix)
rnd_snapshot, mutate, rnd_state, rnd_payment = LG.rnd_snapshot, LG.mutate, LG.rnd_state, LG.rnd_payment


# ----------------------------------------------------------------------------------------------------------------- [1], [2]
def check_lemma_m(trials, rng):
    contained_n = violations = 0
    for _ in range(trials):
        pred = rnd_snapshot(rng)
        succ = mutate(rng, pred)
        ok, _why = V.contained(succ, pred)
        if not ok:
            continue
        contained_n += 1
        for _ in range(60):
            state = rnd_state(rng)
            p = rnd_payment(rng, pred)
            if accepts(succ, state, p) and not accepts(pred, state, p):
                violations += 1
    return contained_n, violations


def check_clause_necessity(rng):
    """For each clause, a successor violating only that clause and an explicit witness: a payment (in a stated lineage state) that
    the successor accepts and the predecessor rejects. Every witness differs from a payment both accept by one boundary step."""
    results = {}
    for label, succ, pred, state, payment in LG.witness_cases():
        mask = M.contained_mask(LG.terms_from_snapshot(succ), LG.terms_from_snapshot(pred))
        ok_v, _why = V.contained(succ, pred)
        k = int(label[2]) - 1
        rejected = (not ok_v) and mask == 1 << k
        if label.startswith("K.9"):
            # not an authority-widening clause: a mandate with a non-zero extensions field accepts nothing on a v1.0 manager (guard G10)
            distinguished = not any(accepts(succ, rnd_state(rng), rnd_payment(rng, pred)) for _ in range(5000))
        else:
            distinguished = accepts(succ, state, payment) and not accepts(pred, state, payment)
        results[label] = (rejected, distinguished)
    return results


# ----------------------------------------------------------------------------------------------------------------- [3] (unchanged)
def check_no_overlap():
    """State: (new_usable, old_usable, active in {P, N, none}). Explore every reachable state; assert the claims."""
    start = (False, True, "P")
    seen, frontier, worst = {start}, [start], 0

    def auth(s):
        new_u, old_u, act = s
        return ({"Rold"} if act == "P" and old_u else set()) | ({"Rnew"} if act == "N" and new_u else set())
    transitions = 0
    while frontier:
        s = frontier.pop()
        new_u, old_u, act = s
        nxt = [(True, old_u, act), (new_u, False, act), (new_u, True, act), (False, old_u, act), (new_u, old_u, "none")]
        if act == "P" and new_u and not old_u:                  # SuccessorOK: G1 and O1 hold
            nxt.append((new_u, old_u, "N"))
        for n in nxt:
            transitions += 1
            worst = max(worst, len(auth(n)))
            # after a successful migration the old router is never consumable, whatever happens to its allowance
            if n[2] == "N":
                assert "Rold" not in auth(n), n
            if n not in seen:
                seen.add(n)
                frontier.append(n)
    return len(seen), transitions, worst


# ----------------------------------------------------------------------------------------------------------------- [4]
def check_pin():
    d1, d2 = "0x" + "ab" * 20, "0x" + "cd" * 20
    h1, h2 = V.designator_hash(d1), V.designator_hash(d2)
    contract = V.keccak256(b"proxy-bytecode")
    cases = [(bytes(32), V.PIN_EOA, True), (V.KECCAK_EMPTY, V.PIN_EOA, True), (h1, V.PIN_EOA, False), (contract, V.PIN_EOA, False),
             (h1, h1, True), (h2, h1, False), (bytes(32), h1, False), (V.KECCAK_EMPTY, h1, False), (contract, contract, True), (h1, contract, False)]
    ok = all(V.pin_ok(h, pin) == want for h, pin, want in cases)
    n = len(cases)
    # the typed-struct predicates of revision 0.5
    eoa, p7702, p4337 = M.example_pin("pinEoa"), M.example_pin("pin7702"), M.example_pin("pin4337")
    h = lambda b: M.h2i(b)  # noqa: E731
    struct_cases = [
        (M.pin_wellformed(eoa), True), (M.pin_wellformed(p7702), True), (M.pin_wellformed(p4337), True), (M.pin_wellformed(M.pin_1271()), True),
        (M.pin_ok(eoa, 0, 0), True), (M.pin_ok(eoa, M.KECCAK_EMPTY, 0), True), (M.pin_ok(eoa, h(h1), 0), False),
        (M.pin_ok(p7702, h(h1), p7702.delegateCodeHash), True), (M.pin_ok(p7702, h(h1), 0), False), (M.pin_ok(p7702, h(h2), p7702.delegateCodeHash), False),
        (M.pin_ok(p4337, p4337.accountCodeHash, 0), True), (M.pin_ok(p4337, 0, 0), False),
        (M.next_pin_version(M.NV_FIRST, 0, eoa, eoa), 1), (M.next_pin_version(M.NV_UPDATE, 4, eoa, eoa), 5),
        (M.next_pin_version(M.NV_SUCCESSOR, 4, dict_replace(eoa, pinVersion=4), eoa), 4),
        (M.next_pin_version(M.NV_SUCCESSOR, 4, dict_replace(eoa, pinVersion=4), dict_replace(eoa, signatureMode=0)), 5),
    ]
    # each of the seven fields moves hashStruct
    base = M.example_pin("pin7702")
    hashes = {base.struct_hash()}
    for f in ("accountMode", "accountCodeHash", "delegate", "delegateCodeHash", "implementationFamily", "pinVersion", "signatureMode"):
        hashes.add(dict_replace(base, **{f: getattr(base, f) ^ 1}).struct_hash())
    struct_cases.append((len(hashes), 8))
    ok = ok and all(a == b for a, b in struct_cases)
    return ok, n + len(struct_cases)


def dict_replace(pin, **kw):
    import dataclasses
    return dataclasses.replace(pin, **kw)


# ----------------------------------------------------------------------------------------------------------------- [5]
def check_shared():
    """Run the three explorations with every check of the specification; also make sure the interesting transitions occur."""
    lines = []
    tot_states = tot_trans = 0
    max_auth = 0
    seen_outcomes = collections.Counter()
    for config in (S.CONFIG_SINGLE, S.CONFIG_SHARED_X, S.CONFIG_SHARED_Y):
        t0 = time.time()
        r = X.explore(config, check=True)
        tot_states += len(r["states"])
        tot_trans += len(r["transitions"])
        max_auth = max(max_auth, r["max_auth"])
        for (_si, a, _di, sel, _arg) in r["transitions"]:
            k, p = S.ACTIONS[a]
            if k == "SUCC":
                seen_outcomes[(config, p[1], M.ERROR_BY_ID[sel][0] if sel else "OK")] += 1
        lines.append(f"      {X.CONFIGS[config]['name']:34s} {len(r['states']):5d} states {len(r['transitions']):6d} transitions "
                     f"max routers with authority {r['max_auth']}  ({time.time() - t0:.1f}s)")
    need = [(S.CONFIG_SHARED_X, M.NORMAL, "OK"), (S.CONFIG_SHARED_X, M.EMERGENCY, "OK"), (S.CONFIG_SHARED_X, M.NORMAL, "ModeMismatch"),
            (S.CONFIG_SHARED_X, M.NORMAL, "ResidualAllowanceUnbounded"), (S.CONFIG_SHARED_X, M.NORMAL, "OldPermissionNotRevoked"),
            (S.CONFIG_SHARED_X, M.EMERGENCY, "OldPermissionNotRevoked"), (S.CONFIG_SHARED_Y, M.EMERGENCY, "OldPermissionNotRevoked"),
            (S.CONFIG_SINGLE, M.NORMAL, "OK")]
    missing = [n for n in need if seen_outcomes[n] == 0]
    return tot_states, tot_trans, max_auth, lines, missing


# ----------------------------------------------------------------------------------------------------------------- [6]
class _ClockBox:
    pass


def check_signer_sets():
    """Exhaustive exploration of the signer-set state machine on a small time grid (GRACE = 2 ticks, time 0..4), keys k1..k3, sets
    v1 = {k1,k2,k3}, v2 = {k1,k2}, v3 = {k2,k3}. The guardian may remove k1 or k2 and stop v1 or v2; governance proposes and activates
    the sets in order. SR-1..SR-5 are asserted on every reachable state and, for monotonicity, on every transition; SR-7 from every
    state. (The domain is kept small so that the whole graph, about ten thousand states, is explored in a few seconds.)"""
    GRACE, TMAX = 2, 4
    members = {1: (1, 2, 3), 2: (1, 2), 3: (2, 3)}
    keys = (1, 2, 3)
    removable, stoppable = (1, 2), (1, 2)

    def key_of(clock, ss):
        return (clock.now, ss.digest())

    def apply(clock, ss, act):
        kind, arg = act
        if kind == "tick":
            clock.now += 1
        elif kind == "propose":
            ss.propose(M.ROLE_GOVERNANCE, arg, list(members[arg]))
        elif kind == "activate":
            ss.activate(M.ROLE_GOVERNANCE, arg)
        elif kind == "remove":
            ss.remove(M.ROLE_GUARDIAN, 10 + arg)
        elif kind == "stop":
            ss.stop(M.ROLE_GUARDIAN, arg)
        else:
            raise AssertionError(kind)

    def actions(clock, ss):
        out = []
        if clock.now < TMAX:
            out.append(("tick", 0))
        for v in (1, 2, 3):
            if v not in ss.sets:
                if v == 1 or v - 1 in ss.sets:
                    out.append(("propose", v))
            elif not ss.sets[v].active and v == ss.current + 1:
                out.append(("activate", v))
        for k in removable:
            out.append(("remove", k))
        for v in stoppable:
            if v in ss.sets and ss.sets[v].active:
                out.append(("stop", v))
        return out

    def check_state(clock, ss):
        now = clock.now
        acc = set()
        for k in keys:
            for v in (1, 2, 3, 4):
                for q in range(0, TMAX + 1):
                    ok = ss.accepts(10 + k, v, q)
                    if ok:
                        acc.add((k, v, q))
                    removed = ss.removed_at.get(10 + k, 0) != 0
                    # SR-1: no grace after removal, for every set version, issuedAt and validUntil
                    assert not (removed and ok), ("SR-1", k, v, q, now)
                    s = ss.sets.get(v)
                    if ok:
                        assert s is not None and s.active and (10 + k) in s.members and not s.stopped
                        assert s.activeFrom <= q
                        if s.retiredAt:
                            # SR-2: bounded, earlier-quotes-only rotation
                            assert q < s.retiredAt and now <= s.retiredAt + GRACE, ("SR-2", k, v, q, now)
                    if s is not None and s.active and s.retiredAt and (q >= s.retiredAt or now > s.retiredAt + GRACE):
                        assert not ok, ("SR-2b", k, v, q, now)
        # SR-4: a tombstoned key is a member of no set that became current after the removal
        for v, s in ss.sets.items():
            if s.active:
                for k in s.members:
                    r = ss.removed_at.get(k, 0)
                    assert not (r and s.activeFrom > r), ("SR-4", v, k)
        # SR-5: fail closed
        cur = ss.sets.get(ss.current)
        if cur is not None:
            dead = cur.stopped or all(ss.removed_at.get(k, 0) != 0 for k in cur.members)
            if dead:
                assert not any(v == ss.current for (_k, v, _q) in acc), ("SR-5", now)
        return acc

    clock0 = M.Clock(0)
    start = (clock0, M.SignerSetModel(clock0, 0, GRACE))
    seen = {key_of(*start): start}
    accepted = {key_of(*start): check_state(*start)}               # the set of accepted (key, version, issuedAt) per state, checked once
    frontier = [start]
    transitions = 0
    while frontier:
        clock, ss = frontier.pop()
        before = accepted[key_of(clock, ss)]
        for act in actions(clock, ss):
            clock2, ss2 = copy.deepcopy(clock), copy.deepcopy(ss)
            ss2.clock = clock2
            try:
                apply(clock2, ss2, act)
            except M.Revert as r:                                   # a refused call changes nothing
                assert r.name == "QuoteSignerTombstoned", (act, r.name)
                assert act[0] in ("propose", "activate")
                assert any(ss2.removed_at.get(10 + k, 0) or ss2.removed_at.get(k, 0) for k in members[act[1]])
                assert ss2.digest() == ss.digest() and clock2.now == clock.now
            transitions += 1
            kk = key_of(clock2, ss2)
            if kk not in accepted:
                accepted[kk] = check_state(clock2, ss2)
            after = accepted[kk]
            kind = act[0]
            if kind in ("remove", "stop", "tick"):
                assert after <= before, ("SR-3", act)                          # Accept_after is a subset of Accept_before
            elif kind == "activate":
                assert all(v == act[1] for (_k, v, _q) in after - before), ("SR-3 rotation", act)   # a rotation adds only the new set
            else:
                assert after == before, ("SR-6", act)                          # proposing changes nothing that verifies
            if kk not in seen:
                seen[kk] = (clock2, ss2)
                frontier.append((clock2, ss2))
    # SR-7: the guardian can add nothing, from any state
    for clock, ss in seen.values():
        for v in (1, 2, 3, 4):
            for call in (lambda: ss.propose(M.ROLE_GUARDIAN, v + 10, [11]), lambda: ss.activate(M.ROLE_GUARDIAN, v)):
                try:
                    call()
                    raise AssertionError("SR-7: the guardian added a set")
                except M.Revert as r:
                    assert r.name == "NotGovernance"
    return len(seen), transitions


# ----------------------------------------------------------------------------------------------------------------- [7]
def check_auth_table():
    """I-ACCT-SIG over (mode, signatureMode, path, signature validity, sender, live-account state), from a closed formula."""
    pins = {1: M.example_pin("pinEoa"), 2: M.example_pin("pin7702"), 3: M.example_pin("pin4337"), 4: M.pin_1271()}
    cases = 0
    for mode, p0 in pins.items():
        for sigmode in (0, 1, 2):
            pin = dict_replace(p0, signatureMode=sigmode)
            live_states = {"holds": (pin.accountCodeHash if mode != 1 else 0, pin.delegateCodeHash),
                           "account changed": (pin.accountCodeHash ^ 1 if mode != 1 else M.h2i(V.designator_hash("0x" + "ab" * 20)), pin.delegateCodeHash)}
            if mode == 2:
                live_states["delegate changed"] = (pin.accountCodeHash, pin.delegateCodeHash ^ 1)
            for name, (h, hd) in live_states.items():
                holds = M.pin_ok(pin, h, hd)
                for sender, path, sig_ok in itertools.product((False, True), (M.SIG_NONE, M.SIG_ECDSA, M.SIG_ERC1271), (False, True)):
                    want = sender or (path == M.SIG_ECDSA and sigmode == M.SM_ECDSA_KEY and sig_ok) \
                        or (path == M.SIG_ERC1271 and sigmode == M.SM_ERC1271 and holds and sig_ok)
                    try:
                        M.auth_signature(sender, path, sig_ok, pin, h, hd)
                        got = True
                    except M.Revert as r:
                        got = False
                        if not sender and path == M.SIG_ERC1271 and sigmode == M.SM_ERC1271 and not holds:
                            assert r.name == "AccountCodeChanged", (mode, sigmode, name, r.name)
                        if not sender and path != M.SIG_NONE and sigmode == M.SM_DIRECT_ONLY:
                            assert r.name == "SignatureModeNotPermitted"
                    assert got == want, ("I-ACCT-SIG", mode, sigmode, name, sender, path, sig_ok, got, want)
                    # exits: through either path whatever the mode or the account
                    try:
                        M.auth_exit(sender, path, sig_ok, pin)
                        exit_ok = True
                    except M.Revert:
                        exit_ok = False
                    assert exit_ok == (sender or (path != M.SIG_NONE and sig_ok)), ("exit", mode, sigmode, name, sender, path, sig_ok)
                    cases += 2
    return cases


# ----------------------------------------------------------------------------------------------------------------- [8]
def mutation_analysis(verbose=True):
    suite = VS.build_suite()
    scen, terms, tables = suite["scenarios"], suite["terms"], suite["tables"]
    quick = {c: dict(t, transitions=t["transitions"][:TABLE_PREFIX]) for c, t in tables.items()}
    rows = []
    survivors = []
    for mid, name, desc in M.MUTANTS:
        fs = VS.run_scenarios(scen, mid, stop_first=True)      # one killing vector per class is enough: the matrix says which classes kill
        ft = VS.run_terms(terms, mid, stop_first=True)
        fx = {}
        for c, t in quick.items():
            fx.update(VS.run_table(t, mid, stop_first=True))
            if fx:
                break
        crash = sum(1 for v in fs.values() if v[2] == "crash")
        first = next(iter(fs), None) or next(iter(ft), None) or next(iter(fx), None)
        rows.append((mid, name, len(fs), len(ft), len(fx), crash, first))
        if not (fs or ft or fx):
            survivors.append(name)
    if verbose:
        print(f"      {'#':>3} {'mutant':22s} {'scenario':>8} {'tuple':>5} {'table':>5}  first killing vector (1 = some vector of that class kills it)")
        for mid, name, a, b, c, crash, first in rows:
            print(f"      {mid:3d} {name:22s} {a:8d} {b:5d} {c:5d}  {first}" + (f"  (by crash)" if crash else ""))
    return len(rows), survivors, rows


def family(name):
    """The predicate or function a mutant belongs to (A1, A2, A3, AUTH, L1, R1, ..., C1, O1N, E6, Q13, ...)."""
    head = name.split("_")[0]
    return head


def print_kill_matrix(rows):
    """One line per family: how many mutants, how many are killed by scenarios, by containment tuples, by the first transitions of the
    tables, and how many only by one of the three (the vector families are complementary)."""
    fam = collections.OrderedDict()
    for mid, name, a, b, c, crash, first in rows:
        f = fam.setdefault(family(name), dict(n=0, s=0, t=0, x=0, only_s=0, only_t=0, only_x=0, ids=[]))
        f["n"] += 1
        f["s"] += a > 0
        f["t"] += b > 0
        f["x"] += c > 0
        f["only_s"] += a > 0 and not b and not c
        f["only_t"] += b > 0 and not a and not c
        f["only_x"] += c > 0 and not a and not b
        f["ids"].append(mid)
    print(f"      {'family':8s} {'mutants':>7} {'by scen.':>9} {'by tuples':>9} {'by tables':>9}   killed only by: scenarios / tuples / tables")
    for k, f in fam.items():
        print(f"      {k:8s} {f['n']:7d} {f['s']:9d} {f['t']:9d} {f['x']:9d}   {f['only_s']:3d} / {f['only_t']:3d} / {f['only_x']:3d}")


# ----------------------------------------------------------------------------------------------------------------- [9]
def check_atomicity():
    """Replay every scenario step by step; an instruction that must revert has to leave the whole model state unchanged."""
    n = 0
    for v in VS.build_suite()["scenarios"]:
        w = S.World()
        for pc in range(0, len(v.words), S.WORDS):
            ins = v.words[pc:pc + S.WORDS]
            before = w.full_digest() if ins[6] else None
            err = w.step(ins)
            assert err is None, (v.id, pc // S.WORDS, err)
            if ins[6]:
                assert w.full_digest() == before, f"{v.id}: instruction {pc // S.WORDS} reverted but changed the model state"
                n += 1
    return n


# ----------------------------------------------------------------------------------------------------------------- [10]
def check_bounds_registry():
    """The price band moved to a versioned registry (ADR-020, finding F-09): the model registry, K.6 and widenedMask bit 6 follow the
    version, `accepts` reads the band of the version, the hashes cover the new snapshot words, and the retired terms field 13 is an error."""
    n = 0
    # the registry: published versions have a band, version 0 and every other version the empty band (fail closed)
    want = {0: (1, 0), 1: (98, 102), 2: (95, 105), 3: (96, 104), 4: (94, 106), 5: (90, 110), 6: (1, 0), 7: (1, 0), 2 ** 32 - 1: (1, 0)}
    for v, b in want.items():
        assert M.band(v) == b, (v, M.band(v), b)
        n += 1
    # K.6 and the widened mask: violated / set exactly when the version differs, in both directions, and nothing else changes
    for v0 in range(0, 8):
        for v1 in range(0, 8):
            a, b = M.base_terms(), M.base_terms()
            a.boundsVersion, b.boundsVersion = v0, v1
            assert M.contained_mask(b, a) == (0 if v0 == v1 else 1 << 5), (v0, v1)
            assert M.widened_mask(b, a) == (0 if v0 == v1 else 1 << 6), (v0, v1)
            n += 2
    # accepts: the price must be inside the band of the mandate's version; no price is accepted by version 0 or an unpublished version
    for v in range(0, 8):
        lo, hi = M.band(v)
        snap = dict(LG.witness_base(), boundsVersion=v, maxQuoteAge=1000, merchantId="M", expiresAt=10_000)
        state = dict(used={t: {f: 0 for f in LG.USED_FAMILIES} for t in LG.TOKENS}, fiatUsed={f: 0 for f in LG.FIAT_USED}, chargesInPeriod=0)
        for price in range(80, 121):
            p = dict(token="T1", a=1, tau=100, merchant="M", fiat=1, age=1, price=price, sinceLast=100, feeBps=1)
            assert M.accepts(snap, state, p) == (lo <= price <= hi), (v, price)
            n += 1
        p = dict(token="T1", a=1, tau=100, merchant="M", fiat=None, age=1, price=0, sinceLast=100, feeBps=1)
        assert M.accepts(snap, state, p), "a charge without a fiat quote does not read the band"
    # the hashes: the customer, anchorStartsAt and boundsVersion move the snapshot hash; the terms hash does not depend on any id
    t = M.base_terms((1, 2))
    base = M.snapshot_hash_int(t, 11, 12, 3, 0xC0FFEE)
    assert M.snapshot_hash_int(t, 11, 12, 3, 0xC0FFEF) != base
    for field, delta in (("anchorStartsAt", 1), ("boundsVersion", 1), ("expiresAt", 1), ("currency", 1)):
        u = t.clone()
        setattr(u, field, getattr(u, field) + delta)
        assert M.snapshot_hash_int(u, 11, 12, 3, 0xC0FFEE) != base and M.terms_hash_int(u) != M.terms_hash_int(t), field
        n += 1
    u = t.clone()
    u.caps[u.tokens[0]][2], u.caps[u.tokens[0]][1] = u.caps[u.tokens[0]][1] + 1, u.caps[u.tokens[0]][2] + 2     # day and total: both words move
    assert M.snapshot_hash_int(u, 11, 12, 3, 0xC0FFEE) != base
    # the snapshot words follow the typed order (perPaymentMax, dayMax, weekMax, thirtyDayMax, periodMax, totalMax)
    typed = M.terms_to_typed(t)
    assert [list(x)[1:] for x in typed["tokens"]] == [["perPaymentMax", "dayMax", "weekMax", "thirtyDayMax", "periodMax", "totalMax"]] * 2
    assert (typed["tokens"][0]["dayMax"], typed["tokens"][0]["totalMax"]) == (t.caps[t.tokens[0]][2], t.caps[t.tokens[0]][1])
    assert typed["fiat"]["boundsVersion"] == t.boundsVersion and typed["anchorStartsAt"] == t.anchorStartsAt
    # the retired scenario field: 13 raises, 12 is the bounds version, an unknown number raises too
    w = S.World()
    w.op_TERMS_SET(0, S.T_FIELDS["T_BVER"], 0, 0, 4)
    assert w.terms[0].boundsVersion == 4 and S.T_FIELDS["T_BVER"] == 12 and 13 not in S.T_FIELDS.values()
    for field, exc in ((13, S.RetiredField), (18, AssertionError), (0, AssertionError)):
        try:
            w.op_TERMS_SET(0, field, 0, 0, 5)
        except exc:
            n += 1
        else:
            raise AssertionError(f"TERMS_SET with field {field} did not raise")
    try:
        w.step([S.OP["TERMS_SET"], 0, 13, 0, 0, 5, 0, 0])
    except S.RetiredField:
        n += 1
    else:
        raise AssertionError("the scenario machine swallowed the retired field")
    return n


def main():
    trials = 60000
    if "--trials" in sys.argv:
        trials = int(sys.argv[sys.argv.index("--trials") + 1])
    rng = random.Random(20261015)
    fail = []
    n, bad = check_lemma_m(trials, rng)
    print(f"[1] Lemma M: {trials} random pairs, {n} contained, {n * 60} payments compared, violations: {bad}")
    if bad or n < trials // 200:
        fail.append("lemma M")
    res = check_clause_necessity(rng)
    for k, (rejected, distinguished) in res.items():
        print(f"[2] {k:26s} rejected by Contained: {rejected}; distinguishing payment found: {distinguished}")
        if not (rejected and distinguished):
            fail.append("necessity " + k)
    states, trans, worst = check_no_overlap()
    print(f"[3] migration state machine: {states} states, {trans} transitions, maximum routers with authority: {worst}")
    if worst > 1:
        fail.append("overlap")
    ok, cnt = check_pin()
    print(f"[4] pin predicate: {cnt} cases, {'ok' if ok else 'FAILED'}")
    if not ok:
        fail.append("pin")
    try:
        states, trans, worst, lines, missing = check_shared()
        print(f"[5] shared-allowance exploration: {states} states, {trans} transitions, maximum routers with authority: {worst}")
        for ln in lines:
            print(ln)
        if missing:
            print("    transitions never exercised:", missing)
            fail.append("shared coverage")
        if worst > 1:
            fail.append("shared overlap")
    except (X.Violation, AssertionError) as exc:
        print(f"[5] shared-allowance exploration: VIOLATION: {exc}")
        fail.append("shared")
    try:
        t0 = time.time()
        s6, t6 = check_signer_sets()
        print(f"[6] signer-set exploration: {s6} states, {t6} transitions, SR-1..SR-5 hold ({time.time() - t0:.1f}s)")
    except AssertionError as exc:
        print(f"[6] signer-set exploration: VIOLATION: {exc}")
        fail.append("signer sets")
    try:
        print(f"[7] pin and AUTH truth table: {check_auth_table()} cases, I-ACCT-SIG holds")
    except AssertionError as exc:
        print(f"[7] pin and AUTH truth table: VIOLATION: {exc}")
        fail.append("auth table")
    t0 = time.time()
    total, survivors, rows = mutation_analysis(verbose="--matrix" in sys.argv)
    print_kill_matrix(rows)
    print(f"[8] mutation analysis: {total} mutants, killed {total - len(survivors)} of {total} by the exported vector suite "
          f"({time.time() - t0:.1f}s)" + (f"; SURVIVORS: {', '.join(survivors)}" if survivors else ""))
    if survivors:
        fail.append("mutants survive")
    try:
        print(f"[9] atomicity: {check_atomicity()} reverting instructions left the model state unchanged")
    except AssertionError as exc:
        print(f"[9] atomicity: VIOLATION: {exc}")
        fail.append("atomicity")
    try:
        print(f"[10] bounds registry: {check_bounds_registry()} checks (band table, K.6, widenedMask bit 6, accepts, snapshot and terms hashes, retired field 13)")
    except AssertionError as exc:
        print(f"[10] bounds registry: VIOLATION: {exc}")
        fail.append("bounds registry")
    print("MODEL CHECKS PASSED" if not fail else "FAILED: " + ", ".join(fail))
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
