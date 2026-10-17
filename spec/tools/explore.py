#!/usr/bin/env python3
"""Exhaustive explorations of the migration state machine over tools/protocol_model.py (revision 0.5).

Three finite domains (document 12 section 5.5, "Executable model"):
  CONFIG_SINGLE    one lineage A, token t1, two routers, allowances t1@R1 and t1@R2 in {none, bounded}: the single-lineage machine
                   (grant, lockdown, re-grant, revoke, activate)
  CONFIG_SHARED_X  two lineages A and B of one customer, both on token t1, sharing the Permit2 allowance (t1, R1)
  CONFIG_SHARED_Y  as X, and lineage B also uses token t2 (so t1 is shared and t2 is B's alone)

A state is a key of 4-bit nibbles (layout in tools/scenario_vm.py: registry codes, lineage states, allowance values, then the derived
exposure counts, the AuthRouters bits and the can-charge bits). `explore` is a breadth-first search over keys; every transition
rebuilds a fresh world from the source key (World.build_state), applies one action (World.act) and observes the result
(World.observe), so the model is the only authority on what happens. The checks (a)..(g) of the specification run on every
reachable state and transition. The same tables are exported to Foundry and replayed on the Solidity model.
"""
import collections
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import protocol_model as M  # noqa: E402
import scenario_vm as S  # noqa: E402

ID_MASK = (1 << 32) - 1                      # nibbles 0..7 identify a state; the rest is derived

# (config) -> dict(name, has_b, t2, actions, registry1, init)
_COMMON_REG = ["DEPR_STD", "DEPR_SEC", "DISABLE0", "SUNSET_R1"]


def _acts(*kinds_params):
    out = []
    for a, (k, p) in S.ACTIONS.items():
        if (k, p) in kinds_params:
            out.append(a)
    return out


def _all(kind):
    return [a for a, (k, _p) in S.ACTIONS.items() if k == kind]


CONFIGS = {
    S.CONFIG_SINGLE: dict(
        name="single lineage", has_b=False, t2=False,
        actions=_acts(("GRANT_B", (1, 0)), ("GRANT_B", (1, 1)), ("LOCK", (1, 0)), ("LOCK", (1, 1)), ("REVOKE", (0,)), ("SUCC", (0, 0))),
        init=dict(r1=S.RG_ACTIVE, r2=S.RG_ACTIVE, a=S.LS_LIVE_R1, b=S.LS_DONE, av=[S.AV_BOUNDED, S.AV_NONE, S.AV_NONE, S.AV_NONE])),
    S.CONFIG_SHARED_X: dict(
        name="shared allowance, B on t1", has_b=True, t2=False,
        actions=_acts(("GRANT_B", (1, 0)), ("GRANT_U", (1, 0)), ("GRANT_B", (1, 1)), ("LOCK", (1, 0)), ("LOCK", (1, 1)),
                      ("EXPIRE_ALLOW", (1, 0)), ("DEPR_STD", ()), ("DEPR_SEC", ()), ("DISABLE", (0,)), ("EXPIRE_B", ()),
                      ("CHARGE", (0, 0, 1, 1)), ("CHARGE", (0, 1, 1, 1)), ("CHARGE", (1, 0, 1, 1)), ("CHARGE", (1, 1, 1, 1)),
                      ("CHARGE", (1, 0, 1, 100)), ("CHARGE", (1, 1, 1, 100)),
                      ("SUCC", (0, 0)), ("SUCC", (0, 1)), ("SUCC", (1, 0)), ("SUCC", (1, 1)),
                      ("REVOKE", (0,)), ("REVOKE", (1,)), ("RETIRE", (1,))),
        init=dict(r1=S.RG_ACTIVE, r2=S.RG_ACTIVE, a=S.LS_LIVE_R1, b=S.LS_LIVE_R1, av=[S.AV_BOUNDED, S.AV_NONE, S.AV_NONE, S.AV_NONE])),
    S.CONFIG_SHARED_Y: dict(
        name="shared allowance, B on t1 and t2", has_b=True, t2=True,
        actions=_acts(("GRANT_B", (1, 0)), ("GRANT_U", (1, 0)), ("GRANT_B", (2, 0)), ("GRANT_U", (2, 0)), ("LOCK", (1, 0)),
                      ("LOCK", (2, 0)), ("EXPIRE_ALLOW", (1, 0)), ("DEPR_SEC", ()), ("DISABLE", (0,)),
                      ("CHARGE", (0, 0, 1, 1)), ("CHARGE", (1, 0, 1, 1)), ("CHARGE", (1, 0, 2, 1)),
                      ("SUCC", (0, 0)), ("SUCC", (0, 1)), ("SUCC", (1, 0)), ("SUCC", (1, 1)),
                      ("REVOKE", (0,)), ("REVOKE", (1,))),
        init=dict(r1=S.RG_ACTIVE, r2=S.RG_ACTIVE, a=S.LS_LIVE_R1, b=S.LS_LIVE_R1,
                  av=[S.AV_BOUNDED, S.AV_BOUNDED, S.AV_BOUNDED, S.AV_BOUNDED])),
}


def initial_key(config):
    i = CONFIGS[config]["init"]
    k = i["r1"] | i["r2"] << 4 | i["a"] << 8 | i["b"] << 12
    for n, v in enumerate(i["av"]):
        k |= v << (16 + 4 * n)
    return k


def nib(key, i):
    return (key >> (4 * i)) & 0xF


def enabled(config, key, action):
    """Which actions are offered in a state (the domain of the exploration; the rest of the model's behavior is exercised by the
    scenario vectors and the fuzz tests)."""
    cfg = CONFIGS[config]
    if action not in cfg["actions"]:
        return False
    kind, p = S.ACTIONS[action]
    r1, r2, sa, sb = nib(key, 0), nib(key, 1), nib(key, 2), nib(key, 3)
    av = [nib(key, 4 + i) for i in range(4)]
    if kind == "GRANT_B":
        return av[(p[0] - 1) * 2 + p[1]] != S.AV_BOUNDED
    if kind == "GRANT_U":
        return av[(p[0] - 1) * 2 + p[1]] != S.AV_UNLIM
    if kind == "LOCK":
        return av[(p[0] - 1) * 2 + p[1]] != S.AV_NONE
    if kind == "EXPIRE_ALLOW":
        return av[(p[0] - 1) * 2 + p[1]] == S.AV_BOUNDED
    if kind in ("DEPR_STD", "DEPR_SEC"):
        return r1 == S.RG_ACTIVE and r2 == S.RG_ACTIVE
    if kind == "DISABLE":
        reg = r1 if p[0] == 0 else r2
        return reg in (S.RG_ACTIVE, S.RG_DEPR_STD, S.RG_DEPR_SEC)
    if kind == "SUNSET_R1":
        return r1 in (S.RG_DEPR_STD, S.RG_DEPR_SEC)
    if kind == "EXPIRE_B":
        return sb == S.LS_LIVE_R1
    if kind == "EXPIRE_A":
        return sa in (S.LS_LIVE_R1, S.LS_LIVE_R2)
    lineage = {0: sa, 1: sb}
    if kind in ("CHARGE", "SUCC", "REVOKE", "RETIRE"):
        L = p[0]
        if L == 1 and not cfg["has_b"]:
            return False
        st = lineage[L]
        if kind == "RETIRE":
            return st in (S.LS_EXP_R1, S.LS_EXP_R2)
        return st != S.LS_DONE
    return True


class Violation(AssertionError):
    pass


def spec_mode(reg, router):
    """Mode(R) read straight from the table of document 12 section 5.3.1, independent of the (possibly mutated) registry code."""
    st = reg.st(router)
    if st == M.ST_ACTIVE or (st == M.ST_DEPRECATED and reg.reason.get(router, 0) == M.REASON_STANDARD):
        return M.MODE_NORMAL
    return M.MODE_EMERGENCY


def _check_state(w: S.World, config, where):
    """(e) the exposure index equals the recomputed count of recorded-active mandates and is never below the true live count."""
    c = S.customer_addr(0)
    rec = w.mgr.exposure_recomputed()
    true = w.mgr.exposure_true_live()
    for r in (0, 1):
        for t in (1, 2):
            key = (c, S.router_addr(r), M.token_addr(t))
            have = w.mgr.live_count(*key)
            if have != rec.get(key, 0):
                raise Violation(f"{where}: live{key} = {have} but the recorded-active mandates number {rec.get(key, 0)} (I-MIG-10)")
            if have < true.get(key, 0):
                raise Violation(f"{where}: live{key} = {have} is below the true live count {true.get(key, 0)} (I-MIG-10)")
        exposed = set(w.mgr.exposed_list(c, S.router_addr(r)))
        want = set(k[2] for k, n in rec.items() if k[1] == S.router_addr(r) and n > 0)
        if exposed != want:
            raise Violation(f"{where}: Exposed set differs from the tokens with a non-zero count (I-MIG-10)")
    if len(set(w.mgr.exposed_list(c, S.router_addr(0)))) > M.MAX_EXPOSED_TOKENS_PER_ROUTER:
        raise Violation(f"{where}: more than MAX_EXPOSED_TOKENS_PER_ROUTER exposed")


def step(config, key, action, mut=0, check=False):
    """One transition. Returns (outcome_id, outcome_arg, next_key). With check=True the specification's postconditions are asserted
    (they hold for the unmutated model; a mutant is expected to violate some of them, which is reported as a Violation)."""
    w = S.World(mut)
    w.build_state(config, key)
    kind, p = S.ACTIONS[action]
    where = f"{S.action_label(action)} from {key & ID_MASK:#010x}"
    if check:
        _check_state(w, config, "source " + where)
        before_p2 = w.p2.snapshot()
        before_digest = w._digest(p[0] if kind == "SUCC" else -1)
        before_obs = w.observe(config)
        before_live = {(r, t): w.mgr.live_count(S.customer_addr(0), S.router_addr(r), M.token_addr(t)) for r in (0, 1) for t in (1, 2)}
        if kind == "SUCC":
            L0 = w.mgr.lineages[w.lineage[p[0]]]
            P0 = w.mgr.mandates[L0.active]
            rold = 0 if P0.router == S.router_addr(0) else 1
            tokens_old = list(P0.terms.tokens)
            gen_before = P0.generation
            exposed_old = list(w.mgr.exposed_list(S.customer_addr(0), S.router_addr(rold)))
            mode_old = spec_mode(w.reg, S.router_addr(rold))
            allow_old = {t: w.p2.get(S.customer_addr(0), t, S.router_addr(rold)) for t in tokens_old}
    sel, arg = 0, 0
    try:
        w.act(config, action)
    except M.Revert as r:
        sel, arg = M.ERROR_ID[r.name], r.arg
        kind = M.ERROR_BY_ID[sel][3]
        if kind == "token":
            arg = arg - 0x7000                                     # compare token arguments as slots, like the vectors
        elif kind != "none":
            arg = S.ANY_ARG                                        # a plain number (an expiration, an amount) is not compared in a table
    nxt = w.observe(config)
    if check:
        where2 = where + f" -> {nxt & ID_MASK:#010x}"
        _check_state(w, config, "target " + where2)
        for slot in (0, 1):
            bits = (nxt >> (48 + 2 * slot)) & 3
            if bin(bits).count("1") > 1:
                raise Violation(f"{where2}: lineage {slot} has authority on two routers (I-MIG-8)")
        if kind == "SUCC":
            ok = sel == 0
            sib_slot = 1 - p[0]
            if ok:
                if w.p2.snapshot() != before_p2:
                    raise Violation(f"{where2}: a successful activation changed Permit2 state (I-MIG-11, Post6)")
                if w._digest(p[0]) != before_digest:
                    raise Violation(f"{where2}: a successful activation changed a sibling or a registry (I-MIG-11)")
                L = w.mgr.lineages[w.lineage[p[0]]]
                if w.mgr.mandates[L.active].generation != gen_before + 1 or P0.status != M.MS_REVOKED:
                    raise Violation(f"{where2}: Post1 violated")
                c = S.customer_addr(0)
                for t in tokens_old:
                    live_after = w.mgr.live_count(c, S.router_addr(rold), t)
                    a = w.p2.get(c, t, S.router_addr(rold))
                    if p[1] == M.NORMAL:
                        if live_after == 0 and M.usable(a.amount, a.expiration, w.clock.now):
                            raise Violation(f"{where2}: Post3N violated: no live mandate uses the token but the old allowance is usable")
                        if live_after > 0 and a.amount >= M.UINT160_MAX:
                            raise Violation(f"{where2}: Post3N violated: unbounded residual for a sibling")
                if p[1] == M.NORMAL:
                    if mode_old != M.MODE_NORMAL:
                        raise Violation(f"{where2}: kind NORMAL accepted on an EMERGENCY-mode router (R3)")
                    for t in tokens_old:
                        if before_live[(rold, t - 0x7000)] > 1 and allow_old[t].amount >= M.UINT160_MAX:
                            raise Violation(f"{where2}: unbounded residual accepted for a shared token")
                    # (f) Claim 4: the sibling's ability to charge is unchanged by a NORMAL activation
                    if sib_slot == 1 and not CONFIGS[config]["has_b"]:
                        pass
                    elif ((nxt >> 52) >> (2 * sib_slot)) & 3 != ((before_obs >> 52) >> (2 * sib_slot)) & 3:
                        raise Violation(f"{where2}: Claim 4 violated: a NORMAL activation changed the sibling's ability to charge")
                if p[1] == M.EMERGENCY:
                    for t in exposed_old:
                        a = w.p2.get(c, t, S.router_addr(rold))
                        if M.usable(a.amount, a.expiration, w.clock.now):
                            raise Violation(f"{where2}: Post3E violated: an exposed token's old allowance is still usable")
            else:
                if p[1] == M.NORMAL and mode_old == M.MODE_EMERGENCY and sel == 0:
                    raise Violation(f"{where2}: NORMAL accepted on an EMERGENCY router")
    return sel, arg, nxt


def explore(config, mut=0, check=False, max_states=200000):
    """Breadth-first search from the initial state. Returns dict(states=[keys], transitions=[(src, action, dst, sel, arg)], ...)."""
    start = initial_key(config)
    w = S.World(mut)
    w.build_state(config, start)
    start = w.observe(config)                         # the full observation of the initial state
    index = {start & ID_MASK: 0}
    keys = [start]
    transitions = []
    queue = collections.deque([0])
    max_auth = 0
    while queue:
        si = queue.popleft()
        key = keys[si]
        for action in sorted(CONFIGS[config]["actions"]):
            if not enabled(config, key, action):
                continue
            sel, arg, nxt = step(config, key, action, mut, check)
            di = index.get(nxt & ID_MASK)
            if di is None:
                if len(keys) >= max_states:
                    raise RuntimeError("state space too large")
                di = index[nxt & ID_MASK] = len(keys)
                keys.append(nxt)
                queue.append(di)
            elif keys[di] != nxt:
                raise Violation(f"the derived part of state {nxt & ID_MASK:#x} is not a function of its identity: "
                                f"{keys[di]:#x} versus {nxt:#x}")
            transitions.append((si, action, di, sel, arg))
            for slot in (0, 1):
                max_auth = max(max_auth, bin((nxt >> (48 + 2 * slot)) & 3).count("1"))
    return dict(config=config, states=keys, transitions=transitions, max_auth=max_auth)


if __name__ == "__main__":
    import time
    for cfg in (S.CONFIG_SINGLE, S.CONFIG_SHARED_X, S.CONFIG_SHARED_Y):
        t = time.time()
        r = explore(cfg, check=True)
        print(f"config {cfg} ({CONFIGS[cfg]['name']}): {len(r['states'])} states, {len(r['transitions'])} transitions, "
              f"max routers with authority {r['max_auth']}, {time.time() - t:.1f}s")
