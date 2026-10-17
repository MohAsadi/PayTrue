#!/usr/bin/env python3
"""Random predecessor snapshots, successors, lineage states and payments for the monotone-authority lemma (document 12 section 5.3.3),
and the flat word encoding shared with the Solidity test helper spec/foundry/test/helpers/TermsCodec.sol (revision 0.5).

The generators are the ones tools/model_checks.py has always used (moved here so that the check and the exporter draw from the same
distribution); the encoding is new. Snapshots here are dictionaries with token names "T1".."T3" and merchants "M" / "M2".
"""
import copy
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import eip712_vectors as V  # noqa: E402
import protocol_model as M  # noqa: E402

FAMILIES = ("perPaymentMax", "dayMax", "weekMax", "thirtyDayMax", "periodMax", "totalMax")
FIAT = ("fiatPerPaymentMax", "fiatDayMax", "fiatWeekMax", "fiatThirtyDayMax", "fiatPeriodMax", "fiatTotalMax")
TOKENS = ["T1", "T2", "T3"]
USED_FAMILIES = ("dayMax", "weekMax", "thirtyDayMax", "periodMax", "totalMax")
FIAT_USED = ("fiatDayMax", "fiatWeekMax", "fiatThirtyDayMax", "fiatPeriodMax", "fiatTotalMax")


def rnd_cap(rng, lo=1, hi=1000):
    return 0 if rng.random() < 0.2 else rng.randint(lo, hi)


def rnd_snapshot(rng):
    toks = rng.sample(TOKENS, rng.randint(1, 3))
    return dict(
        lineageId="L", predecessorId="P", generation=0, expiresAt=rng.randint(100, 1000), merchantId="M", recipientPolicy="R",
        subscriptionRef="S", periodSeconds=100, currency=840, tokens=sorted(toks),
        caps={t: {f: rnd_cap(rng) for f in FAMILIES} for t in toks},
        **{f: rnd_cap(rng, 1, 500) for f in FIAT},
        maxQuoteAge=rng.randint(10, 300), boundsVersion=rng.randint(0, 5),
        maxChargesPerPeriod=rng.choice([0, 1, 2, 3]), minInterval=rng.choice([0, 10, 100]), maxFeeBps=rng.randint(0, 200),
        extensionsHash=bytes(32))


def mutate(rng, s, intensity=1):
    """Random successor: each field changes with some probability, in either direction."""
    n = copy.deepcopy(s)

    def bump(x, lo=0):
        return max(lo, x + rng.choice([-3, -1, 0, 0, 0, 1, 3]))
    if rng.random() < 0.4:
        n["expiresAt"] = bump(n["expiresAt"])
    if rng.random() < 0.15:
        n["merchantId"] = rng.choice(["M", "M2"])
    keep = [t for t in n["tokens"] if rng.random() < 0.85] or n["tokens"][:1]
    if rng.random() < 0.1:
        extra = [t for t in TOKENS if t not in keep]
        if extra:
            keep = keep + [extra[0]]
            n["caps"][extra[0]] = {f: rnd_cap(rng) for f in FAMILIES}
    n["tokens"] = sorted(keep)
    n["caps"] = {t: n["caps"][t] for t in n["tokens"]}
    for t in n["tokens"]:
        for f in FAMILIES:
            if rng.random() < 0.3:
                n["caps"][t][f] = rng.choice([0, bump(n["caps"][t][f])])
    for f in FIAT:
        if rng.random() < 0.3:
            n[f] = rng.choice([0, bump(n[f])])
    if rng.random() < 0.3:
        n["maxQuoteAge"] = bump(n["maxQuoteAge"], 1)
    if rng.random() < 0.3:
        n["boundsVersion"] = bump(n["boundsVersion"])
    if rng.random() < 0.3:
        n["maxChargesPerPeriod"] = rng.choice([0, 1, 2, 3])
    if rng.random() < 0.3:
        n["minInterval"] = bump(n["minInterval"])
    if rng.random() < 0.3:
        n["maxFeeBps"] = bump(n["maxFeeBps"])
    if rng.random() < 0.03:
        n["extensionsHash"] = b"\x01" * 32
    return n


def rnd_state(rng):
    return dict(used={t: {f: rng.randint(0, 600) for f in USED_FAMILIES} for t in TOKENS},
                fiatUsed={f: rng.randint(0, 300) for f in FIAT_USED},
                chargesInPeriod=rng.randint(0, 3))


def rnd_payment(rng, snap):
    return dict(token=rng.choice(TOKENS), a=rng.randint(1, 1100), tau=rng.randint(50, 1100), merchant=rng.choice(["M", "M", "M2"]),
                fiat=rng.choice([None, rng.randint(1, 600)]), age=rng.randint(1, 320), price=rng.randint(85, 115),
                sinceLast=rng.choice([0, 5, 10, 50, 100, 200]), feeBps=rng.randint(0, 210))


# ----------------------------------------------------------------------------------------------------------------- encoding
TERMS_WORDS = 41
STATE_WORDS = 21
PAYMENT_WORDS = 10
TUPLE_WORDS = 4 + 2 * TERMS_WORDS + STATE_WORDS + PAYMENT_WORDS          # flags, mask, succAcc, predAcc, succ, pred, state, payment


def _tok_word(t):
    if isinstance(t, str) and t.startswith("0x"):
        return int(t, 16)
    return M.token_addr(int(t[1:]))


def _word(x):
    """A snapshot field as a word: bytes32 and hex strings by value; a short name ("M", "R2") as its ASCII bytes."""
    if isinstance(x, bytes):
        return int.from_bytes(x, "big")
    if isinstance(x, str):
        if x.startswith("0x"):
            return int(x, 16)
        return int.from_bytes(x.encode(), "big")
    return x


def terms_words(snap):
    """The 41 words of a snapshot dictionary: expiresAt, merchantId, recipientPolicy, subscriptionRef, periodSeconds, anchorStartsAt,
    currency, nTokens, three token addresses, 3 x 6 caps (perPayment, total, day, week, thirtyDay, period), 6 fiat caps (same
    order), maxQuoteAge, boundsVersion, maxChargesPerPeriod, minInterval, maxFeeBps, extensionsHash."""
    toks = sorted(snap["tokens"], key=_tok_word)
    w = [snap["expiresAt"], _word(snap["merchantId"]), _word(snap["recipientPolicy"]), _word(snap["subscriptionRef"]),
         snap["periodSeconds"], snap.get("anchorStartsAt", 0), snap["currency"], len(toks)]
    w += [_tok_word(t) for t in toks] + [0] * (3 - len(toks))
    for i in range(3):
        if i < len(toks):
            c = snap["caps"][toks[i]]
            w += [c["perPaymentMax"], c["totalMax"], c["dayMax"], c["weekMax"], c["thirtyDayMax"], c["periodMax"]]
        else:
            w += [0] * 6
    w += [snap["fiatPerPaymentMax"], snap["fiatTotalMax"], snap["fiatDayMax"], snap["fiatWeekMax"], snap["fiatThirtyDayMax"],
          snap["fiatPeriodMax"]]
    w += [snap["maxQuoteAge"], snap["boundsVersion"], snap["maxChargesPerPeriod"], snap["minInterval"], snap["maxFeeBps"],
          _word(snap["extensionsHash"])]
    assert len(w) == TERMS_WORDS
    return w


def terms_from_snapshot(snap) -> "M.Terms":
    """The protocol_model.Terms object with the same content as a snapshot dictionary (tokens as addresses)."""
    toks = sorted(snap["tokens"], key=_tok_word)
    t = M.Terms(expiresAt=snap["expiresAt"], merchantId=_word(snap["merchantId"]), recipientPolicy=_word(snap["recipientPolicy"]),
                subscriptionRef=_word(snap["subscriptionRef"]), periodSeconds=snap["periodSeconds"],
                anchorStartsAt=snap.get("anchorStartsAt", 0), currency=snap["currency"], maxQuoteAge=snap["maxQuoteAge"],
                boundsVersion=snap["boundsVersion"], maxChargesPerPeriod=snap["maxChargesPerPeriod"],
                minInterval=snap["minInterval"], maxFeeBps=snap["maxFeeBps"], extensionsHash=_word(snap["extensionsHash"]))
    for tok in toks:
        a = _tok_word(tok)
        t.tokens.append(a)
        c = snap["caps"][tok]
        t.caps[a] = [c["perPaymentMax"], c["totalMax"], c["dayMax"], c["weekMax"], c["thirtyDayMax"], c["periodMax"]]
    t.fiat = [snap["fiatPerPaymentMax"], snap["fiatTotalMax"], snap["fiatDayMax"], snap["fiatWeekMax"], snap["fiatThirtyDayMax"],
              snap["fiatPeriodMax"]]
    return t


def state_words(state):
    w = []
    for t in TOKENS:
        w += [state["used"][t][f] for f in USED_FAMILIES]
    w += [state["fiatUsed"][f] for f in FIAT_USED]
    w.append(state["chargesInPeriod"])
    assert len(w) == STATE_WORDS
    return w


def payment_words(p):
    w = [int(p["token"][1:]), p["a"], p["tau"], _word(p["merchant"]), 0 if p["fiat"] is None else 1, p["fiat"] or 0, p["age"],
         p["price"], p["sinceLast"], p["feeBps"]]
    assert len(w) == PAYMENT_WORDS
    return w


def tuple_words(succ, pred, state=None, payment=None):
    """[flags, expectedMask, succAccepts, predAccepts, succ terms, pred terms, state, payment]; flags bit 0 = a payment is evaluated.
    The expectations come from the Python model: the containment mask of protocol_model.contained_mask and protocol_model.accepts."""
    mask = M.contained_mask(terms_from_snapshot(succ), terms_from_snapshot(pred))
    if state is None:
        return [0, mask, 0, 0] + terms_words(succ) + terms_words(pred) + [0] * (STATE_WORDS + PAYMENT_WORDS)
    sa = int(M.accepts(succ, state, payment))
    pa = int(M.accepts(pred, state, payment))
    return [1, mask, sa, pa] + terms_words(succ) + terms_words(pred) + state_words(state) + payment_words(payment)


# ----------------------------------------------------------------------------------------------------------------- clause witnesses
def witness_base():
    """The predecessor of the clause necessity check (the same as in tools/model_checks.py of revision 0.4)."""
    pred = rnd_snapshot(__import__("random").Random(7))
    pred.update(tokens=["T1", "T2"], caps={t: dict({f: 100 for f in FAMILIES}, perPaymentMax=50) for t in ("T1", "T2")}, expiresAt=500,
                merchantId="M", maxQuoteAge=60, boundsVersion=1, maxChargesPerPeriod=2, minInterval=50, maxFeeBps=100)
    for f in FIAT:
        pred[f] = 200
    return pred


def witness_cases():
    """For each clause K.x: a successor that violates only that clause, and a payment (in a stated lineage state) that the successor
    accepts and the predecessor rejects. Returns [(label, successor, predecessor, state, payment)]."""
    pred = witness_base()

    def state(**over):
        s = dict(used={tk: {f: 0 for f in USED_FAMILIES} for tk in TOKENS}, fiatUsed={f: 0 for f in FIAT_USED}, chargesInPeriod=0)
        for k, v in over.items():
            if k == "total":
                s["used"]["T1"]["totalMax"] = v
            elif k == "thirty":
                s["used"]["T1"]["thirtyDayMax"] = v
            elif k == "fiatTotal":
                s["fiatUsed"]["fiatTotalMax"] = v
            else:
                s[k] = v
        return s

    def pay(**over):
        p = dict(token="T1", a=10, tau=100, merchant="M", fiat=10, age=10, price=100, sinceLast=100, feeBps=10)
        p.update(over)
        return p

    cases = [
        ("K.1 expiry", lambda s: s.update(expiresAt=501), state(), pay(tau=500)),
        ("K.2 merchant", lambda s: s.update(merchantId="M2"), state(), pay(merchant="M2")),
        ("K.3 token scope", lambda s: (s["tokens"].append("T3"), s["caps"].update({"T3": {f: 100 for f in FAMILIES}})), state(), pay(token="T3")),
        ("K.4 per-payment cap", lambda s: s["caps"]["T1"].update(perPaymentMax=51), state(), pay(a=51)),
        ("K.4 total cap", lambda s: s["caps"]["T1"].update(totalMax=101), state(total=91), pay(a=10)),
        ("K.4 window cap removed", lambda s: s["caps"]["T1"].update(thirtyDayMax=0), state(thirty=95), pay(a=10)),
        ("K.5 fiat total", lambda s: s.update(fiatTotalMax=201), state(fiatTotal=195), pay(fiat=6)),
        ("K.5 quote age", lambda s: s.update(maxQuoteAge=61), state(), pay(age=61)),
        ("K.6 bounds", lambda s: s.update(boundsVersion=2), state(), pay(price=105)),     # version 2 = [95, 105], version 1 = [98, 102]
        ("K.7 charges per period", lambda s: s.update(maxChargesPerPeriod=3), state(chargesInPeriod=2), pay()),
        ("K.7 interval", lambda s: s.update(minInterval=49), state(), pay(sinceLast=49)),
        ("K.8 fee cap", lambda s: s.update(maxFeeBps=101), state(), pay(feeBps=101)),
        ("K.9 extensions", lambda s: s.update(extensionsHash=b"\x01" * 32), state(), pay()),
    ]
    out = []
    for label, change, st, p in cases:
        succ = copy.deepcopy(pred)
        change(succ)
        out.append((label, succ, copy.deepcopy(pred), st, p))
    return out
