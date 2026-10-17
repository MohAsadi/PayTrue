#!/usr/bin/env python3
"""Reference EIP-712 encoder and Keccak-256 for the FastPay protocol vectors (revision 0.4).

Pure Python, no dependencies. It exists so that the normative encodings in documents 11, 12 and 17 have reproducible test
vectors that the Solidity implementation and the backend must both reproduce. Illustrative addresses only; no production values.

Covers:
  * PriceQuote v1 (document 11 section 4): all fifteen fields, domain, type hash, struct hash, digest
  * identifiers independent of router version: lineageId, mandateId, cycleId, paymentId (document 12 section 4)
  * account pins (document 17): EXTCODEHASH of a 7702 designator, the plain-EOA sentinel, the pin predicate;
    revision 0.5: the seven-field AccountPin typed struct, ACCOUNT_PIN_TYPEHASH, three example pins and their hashStruct
  * MigrationSnapshot hash and the containment predicate (document 12 section 5.3)

Run:  python -I spec/tools/eip712_vectors.py          (prints every vector and self-checks)
"""
import sys

# ---------------------------------------------------------------- Keccak-256 (original Keccak padding 0x01, not SHA3)
_RC = [0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000, 0x000000000000808B,
       0x0000000080000001, 0x8000000080008081, 0x8000000000008009, 0x000000000000008A, 0x0000000000000088,
       0x0000000080008009, 0x000000008000000A, 0x000000008000808B, 0x800000000000008B, 0x8000000000008089,
       0x8000000000008003, 0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
       0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008]
_ROT = [[0, 36, 3, 41, 18], [1, 44, 10, 45, 2], [62, 6, 43, 15, 61], [28, 55, 25, 21, 56], [27, 20, 39, 8, 14]]
_M = (1 << 64) - 1


def _rol(x, n):
    n %= 64
    return ((x << n) | (x >> (64 - n))) & _M if n else x


def _keccak_f(a):
    for rc in _RC:
        c = [a[x][0] ^ a[x][1] ^ a[x][2] ^ a[x][3] ^ a[x][4] for x in range(5)]
        d = [c[(x - 1) % 5] ^ _rol(c[(x + 1) % 5], 1) for x in range(5)]
        a = [[a[x][y] ^ d[x] for y in range(5)] for x in range(5)]
        b = [[0] * 5 for _ in range(5)]
        for x in range(5):
            for y in range(5):
                b[y][(2 * x + 3 * y) % 5] = _rol(a[x][y], _ROT[x][y])
        a = [[b[x][y] ^ ((~b[(x + 1) % 5][y]) & b[(x + 2) % 5][y]) for y in range(5)] for x in range(5)]
        a[0][0] ^= rc
    return a


def keccak256(data: bytes) -> bytes:
    rate = 136
    msg = bytearray(data) + b"\x01"
    while len(msg) % rate:
        msg += b"\x00"
    msg[-1] |= 0x80
    a = [[0] * 5 for _ in range(5)]
    for off in range(0, len(msg), rate):
        block = msg[off:off + rate]
        for i in range(rate // 8):
            a[i % 5][i // 5] ^= int.from_bytes(block[8 * i:8 * i + 8], "little")
        a = _keccak_f(a)
    return b"".join(a[i % 5][i // 5].to_bytes(8, "little") for i in range(4))


# ---------------------------------------------------------------- ABI / EIP-712 helpers
def u(n: int) -> bytes:
    assert 0 <= n < 1 << 256
    return n.to_bytes(32, "big")


def addr(h: str) -> bytes:
    h = h.lower().removeprefix("0x")
    assert len(h) == 40
    return bytes(12) + bytes.fromhex(h)


def b32(h) -> bytes:
    if isinstance(h, bytes):
        assert len(h) == 32
        return h
    h = h.removeprefix("0x")
    assert len(h) == 64
    return bytes.fromhex(h)


def hx(b: bytes) -> str:
    return "0x" + b.hex()


def tag(s: str) -> bytes:
    """Domain-separation tag: keccak256 of an ASCII string (a bytes32 constant in the contracts)."""
    return keccak256(s.encode())


DOMAIN_TYPE = "EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
QUOTE_TYPE = ("PriceQuote(bytes32 paymentId,address payer,address token,uint256 amountIn,uint16 currency,"
              "uint256 priceE18,uint64 issuedAt,uint64 validAfter,uint64 validUntil,uint256 nonce,"
              "uint32 signerSetVersion,uint64 registryVersion,uint32 boundsVersion,bytes32 routeHash,"
              "bytes32 priceSourceSetHash)")
QUOTE_FIELDS = ["paymentId", "payer", "token", "amountIn", "currency", "priceE18", "issuedAt", "validAfter", "validUntil",
                "nonce", "signerSetVersion", "registryVersion", "boundsVersion", "routeHash", "priceSourceSetHash"]

TAG_LINEAGE = "fastpay.lineage.v1"
TAG_MANDATE = "fastpay.mandate.v1"
TAG_CYCLE = "fastpay.cycle.v1"
TAG_ROUTE_DIRECT = "fastpay.route.direct.v1"
TAG_SNAPSHOT = "fastpay.migration.snapshot.v1"
TAG_PIN_EOA = "fastpay.pin.eoa.v1"
KECCAK_EMPTY = keccak256(b"")


def domain_separator(name, version, chain_id, verifying):
    return keccak256(keccak256(DOMAIN_TYPE.encode()) + keccak256(name.encode()) + keccak256(version.encode())
                     + u(chain_id) + addr(verifying))


def quote_struct_hash(q):
    return keccak256(keccak256(QUOTE_TYPE.encode()) + b32(q["paymentId"]) + addr(q["payer"]) + addr(q["token"])
                     + u(q["amountIn"]) + u(q["currency"]) + u(q["priceE18"]) + u(q["issuedAt"]) + u(q["validAfter"])
                     + u(q["validUntil"]) + u(q["nonce"]) + u(q["signerSetVersion"]) + u(q["registryVersion"])
                     + u(q["boundsVersion"]) + b32(q["routeHash"]) + b32(q["priceSourceSetHash"]))


def digest(domain_sep: bytes, struct_hash: bytes) -> bytes:
    return keccak256(b"\x19\x01" + domain_sep + struct_hash)


# identifiers: none of them contains a router address, a router version or a mandate generation
def lineage_id(chain_id, mandate_manager, customer, merchant_id, subscription_ref, creation_nonce):
    return keccak256(tag(TAG_LINEAGE) + u(chain_id) + addr(mandate_manager) + addr(customer) + b32(merchant_id)
                     + b32(subscription_ref) + u(creation_nonce))


def mandate_id(lineage, generation):
    return keccak256(tag(TAG_MANDATE) + b32(lineage) + u(generation))


def cycle_id(lineage, cycle_index):
    return keccak256(tag(TAG_CYCLE) + b32(lineage) + u(cycle_index))


def payment_id_recurring(chain_id, mandate_manager, lineage, cycle):
    return keccak256(u(chain_id) + addr(mandate_manager) + b32(lineage) + b32(cycle))


def payment_id_pay_once(chain_id, router_registry, merchant_id, order_id):
    return keccak256(u(chain_id) + addr(router_registry) + b32(merchant_id) + b32(order_id))


def route_hash_direct(chain_id, token):
    return keccak256(tag(TAG_ROUTE_DIRECT) + u(chain_id) + addr(token))


def fiat_value_minor(amount_in, price_e18, token_decimals):
    """ceil(amountIn * priceE18 / (10^decimals * 1e18)) -- rounds UP, never down."""
    num = amount_in * price_e18
    den = 10 ** token_decimals * 10 ** 18
    return -(-num // den)


# ---------------------------------------------------------------- account pins (document 17)
def designator_code(delegate: str) -> bytes:
    """The 23-byte account code of an EIP-7702 delegated account: 0xef0100 || delegate."""
    return bytes.fromhex("ef0100") + bytes.fromhex(delegate.lower().removeprefix("0x"))


def designator_hash(delegate: str) -> bytes:
    """EXTCODEHASH of a delegated account (it hashes the designator, not the delegate's code)."""
    return keccak256(designator_code(delegate))


PIN_EOA = tag(TAG_PIN_EOA)


# ---------------------------------------------------------------- the AccountPin typed struct (document 17 section 5.1, revision 0.5)
ACCOUNT_PIN_TYPE = ("AccountPin(uint8 accountMode,bytes32 accountCodeHash,address delegate,bytes32 delegateCodeHash,"
                    "bytes32 implementationFamily,uint32 pinVersion,uint8 signatureMode)")
ACCOUNT_PIN_FIELDS = ["accountMode", "accountCodeHash", "delegate", "delegateCodeHash", "implementationFamily", "pinVersion",
                      "signatureMode"]
ACCOUNT_PIN_TYPEHASH = keccak256(ACCOUNT_PIN_TYPE.encode())
ZERO_ADDRESS = "0x" + "00" * 20
TEST_DELEGATE_D1 = "0x" + "ab" * 20
TEST_DELEGATE_D2 = "0x" + "cd" * 20
TEST_DELEGATE_CODE_HASH = keccak256(b"fastpay-test-delegate-code-v1")
TEST_ACCOUNT_CODE_HASH = keccak256(b"fastpay-test-account-code-v1")
TEST_FAMILY_DELEGATOR = keccak256(b"test-wallet/delegator/1")
TEST_FAMILY_ACCOUNT = keccak256(b"test-wallet/account/1")


def pin_struct_hash(pin) -> bytes:
    """hashStruct(AccountPin): keccak256(typeHash ‖ the seven fields, each one 32-byte word)."""
    return keccak256(ACCOUNT_PIN_TYPEHASH + u(pin["accountMode"]) + b32(pin["accountCodeHash"]) + addr(pin["delegate"])
                     + b32(pin["delegateCodeHash"]) + b32(pin["implementationFamily"]) + u(pin["pinVersion"]) + u(pin["signatureMode"]))


def example_pins():
    """The three example pins of document 17 section 9 (ACP-TV-25): plain EOA, 7702 delegate D1, ERC-4337 account."""
    zero = bytes(32)
    return {
        "pinEoa": dict(accountMode=1, accountCodeHash=tag(TAG_PIN_EOA), delegate=ZERO_ADDRESS, delegateCodeHash=zero,
                       implementationFamily=zero, pinVersion=1, signatureMode=1),
        "pin7702": dict(accountMode=2, accountCodeHash=designator_hash(TEST_DELEGATE_D1), delegate=TEST_DELEGATE_D1,
                        delegateCodeHash=TEST_DELEGATE_CODE_HASH, implementationFamily=TEST_FAMILY_DELEGATOR, pinVersion=1,
                        signatureMode=2),
        "pin4337": dict(accountMode=3, accountCodeHash=TEST_ACCOUNT_CODE_HASH, delegate=ZERO_ADDRESS, delegateCodeHash=zero,
                        implementationFamily=TEST_FAMILY_ACCOUNT, pinVersion=1, signatureMode=2),
    }


def pin_ok(extcodehash: bytes, pin: bytes) -> bool:
    """PIN_OK(h, pin): the account's EXTCODEHASH still matches what the customer pinned.
    EXTCODEHASH is 0 for an account that does not exist or is empty, and keccak256('') for an existing account without code."""
    if pin == PIN_EOA:
        return extcodehash == bytes(32) or extcodehash == KECCAK_EMPTY
    return extcodehash == pin


# ---------------------------------------------------------------- migration snapshot (document 12 section 5.3)
INF = 1 << 256


def eff(x):
    """Effective cap: 0 means 'no cap in this family' and compares as infinity."""
    return INF if x == 0 else x


def contained(succ, snap):
    """Containment of a migration successor in the snapshot of its predecessor: every comparison is <= on an effective cap."""
    why = []
    if succ["expiresAt"] > snap["expiresAt"]:
        why.append("expiry")
    for k in ("merchantId", "recipientPolicy", "subscriptionRef", "periodSeconds", "currency"):
        if succ[k] != snap[k]:
            why.append(k)
    if not set(succ["tokens"]) <= set(snap["tokens"]):
        why.append("tokenScope")
    for t in succ["tokens"]:
        if t not in snap["tokens"]:
            continue
        for f in ("perPaymentMax", "totalMax", "dayMax", "weekMax", "thirtyDayMax", "periodMax"):
            if eff(succ["caps"][t][f]) > eff(snap["caps"][t][f]):
                why.append(f"cap:{t}:{f}")
    for f in ("fiatPerPaymentMax", "fiatTotalMax", "fiatDayMax", "fiatWeekMax", "fiatThirtyDayMax", "fiatPeriodMax"):
        if eff(succ[f]) > eff(snap[f]):
            why.append(f)
    if succ["maxQuoteAge"] > snap["maxQuoteAge"]:
        why.append("maxQuoteAge")
    if succ["boundsVersion"] != snap["boundsVersion"]:      # K.6: the band of a version never changes (ADR-020), so a migration keeps the version
        why.append("boundsVersion")
    if eff(succ["maxChargesPerPeriod"]) > eff(snap["maxChargesPerPeriod"]):
        why.append("maxChargesPerPeriod")
    if succ["minInterval"] < snap["minInterval"]:
        why.append("minInterval")
    if succ["maxFeeBps"] > snap["maxFeeBps"]:
        why.append("maxFeeBps")
    if succ["extensionsHash"] != bytes(32) or snap["extensionsHash"] != bytes(32):
        why.append("extensionsHash")
    return (not why), why


_TYPES_DOC = None


def types_doc():
    """eip712/types.json, the single source of every type string and of the snapshot encoding (loaded once)."""
    global _TYPES_DOC
    if _TYPES_DOC is None:
        import json
        import pathlib
        _TYPES_DOC = json.loads((pathlib.Path(__file__).resolve().parent.parent / "eip712" / "types.json").read_text(encoding="utf-8"))
    return _TYPES_DOC


def _field_type(struct, name):
    for s in types_doc()["structs"]:
        if s["name"] == struct:
            for t, n in s["fields"]:
                if n == name:
                    return t
    raise KeyError(f"{struct}.{name}")


def _word_of(t, v):
    """One 32-byte word of a value of the EIP-712 atomic type `t` (hex strings or bytes for addresses and bytes32, int or decimal string for uints)."""
    if t == "address":
        return addr(v if isinstance(v, str) else "0x" + v.hex())
    if t.startswith("bytes"):
        return b32(v)
    return u(int(v))


def snapshot_words(lineage_id, predecessor_id, generation, customer, terms):
    """The words of the migration snapshot hash, in the order of eip712/types.json snapshotEncoding.words. `terms` is a value of the
    MandateTerms struct (field names of types.json; tokens is a list of TokenTerms values; fiat a FiatTerms value)."""
    spec = types_doc()["snapshotEncoding"]
    args = {"lineageId": ("bytes32", lineage_id), "predecessorId": ("bytes32", predecessor_id), "generation": ("uint32", generation),
            "customer": ("address", customer)}
    tok_fields = spec["tokenWords"]
    toks = terms["tokens"]
    digests = {"tokens": keccak256(b"".join(_word_of("address", x["token"]) for x in toks)),
               "capTable": keccak256(b"".join(b"".join(_word_of("address" if f == "token" else "uint256", x[f]) for f in tok_fields) for x in toks))}
    out = []
    for _name, src in spec["words"]:
        kind, _, field = src.partition(":")
        if kind == "tag":
            out.append(tag(TAG_SNAPSHOT))
        elif kind == "arg":
            t, v = args[field]
            out.append(_word_of(t, v))
        elif kind == "terms":
            out.append(_word_of(_field_type("MandateTerms", field), terms[field]))
        elif kind == "terms.fiat":
            out.append(_word_of(_field_type("FiatTerms", field), terms["fiat"][field]))
        elif kind == "digest":
            out.append(digests[field])
        else:
            raise ValueError(src)
    return out


def snapshot_hash(lineage_id, predecessor_id, generation, customer, terms):
    """keccak256 of the snapshot words (eip712/types.json snapshotEncoding; document 12 section 5.3.2)."""
    return keccak256(b"".join(snapshot_words(lineage_id, predecessor_id, generation, customer, terms)))


def permit2_usable(amount, expiration, now):
    """Permit2 AllowanceTransfer.transferFrom reverts when block.timestamp > expiration (AllowanceExpired) or when the amount
    is insufficient. An allowance is therefore usable iff amount > 0 and now <= expiration. uint160.max is unlimited."""
    return amount > 0 and now <= expiration


def self_check():
    assert keccak256(b"").hex() == "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"
    assert keccak256(b"abc").hex() == "4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45"
    assert keccak256(b"transfer(address,uint256)")[:4].hex() == "a9059cbb"
    assert keccak256(b"x" * 200).hex() == keccak256(b"x" * 200).hex()          # multi-block path executes
    assert fiat_value_minor(49_990_000, 100 * 10 ** 18, 6) == 4999
    assert fiat_value_minor(10_000_001, 1001 * 10 ** 17, 6) == 1002
    assert fiat_value_minor(1, 1, 6) == 1                                       # tiny values round up
    assert len(designator_code("0x" + "ab" * 20)) == 23
    # pin predicate: both encodings of "no code" satisfy the EOA pin; a designator does not
    assert pin_ok(bytes(32), PIN_EOA) and pin_ok(KECCAK_EMPTY, PIN_EOA)
    assert not pin_ok(designator_hash("0x" + "ab" * 20), PIN_EOA)
    assert pin_ok(designator_hash("0x" + "ab" * 20), designator_hash("0x" + "ab" * 20))
    assert not pin_ok(designator_hash("0x" + "cd" * 20), designator_hash("0x" + "ab" * 20))
    assert not pin_ok(bytes(32), designator_hash("0x" + "ab" * 20))
    # Permit2 boundary: usable in the block whose timestamp equals the stored expiration, unusable one second later
    assert permit2_usable(1, 100, 100) and not permit2_usable(1, 100, 101) and not permit2_usable(0, 100, 50)
    # router independence: identifiers contain no router
    L = lineage_id(1, "0x" + "22" * 20, "0x" + "44" * 20, b"\x01" * 32, b"\x02" * 32, 7)
    assert cycle_id(L, 3) == cycle_id(L, 3) and cycle_id(L, 3) != cycle_id(L, 4)
    # AccountPin: the type string is the one of document 17 section 5.1; each of the seven fields moves the struct hash
    assert ACCOUNT_PIN_TYPE.count(",") == 6 and ACCOUNT_PIN_TYPE.startswith("AccountPin(") and " " in ACCOUNT_PIN_TYPE
    pins = example_pins()
    hashes = {k: pin_struct_hash(p) for k, p in pins.items()}
    assert len(set(hashes.values())) == 3
    base = pins["pin7702"]
    for field in ACCOUNT_PIN_FIELDS:
        changed = dict(base)
        val = base[field]
        if isinstance(val, int):
            changed[field] = val ^ 1
        elif isinstance(val, str):                       # an address given as hex text: flip the last nibble
            changed[field] = val[:-1] + ("0" if val[-1] != "0" else "1")
        else:                                            # bytes32: flip the last bit
            changed[field] = val[:-1] + bytes([val[-1] ^ 1])
        assert pin_struct_hash(changed) != hashes["pin7702"], field
    assert pins["pin7702"]["accountCodeHash"] == designator_hash(TEST_DELEGATE_D1)


VECTOR = dict(
    chainId=84532,
    router="0x1111111111111111111111111111111111111111",
    routerB="0x1212121212121212121212121212121212121212",
    mandateManager="0x2222222222222222222222222222222222222222",
    customer="0x4444444444444444444444444444444444444444",
    merchantId="0x" + "aa" * 32,
    subscriptionRef="0x" + "bb" * 32,
    creationNonce=7,
    cycleIndex=1,
    quote=dict(
        payer="0x4444444444444444444444444444444444444444",
        token="0x5555555555555555555555555555555555555555",
        amountIn=49_990_000, currency=840, priceE18=100 * 10 ** 18,
        issuedAt=1_800_000_000, validAfter=1_800_000_000, validUntil=1_800_000_120,
        nonce=424242, signerSetVersion=3, registryVersion=12, boundsVersion=1,
    ),
    tokenDecimals=6,
)


def quote_vector():
    v = VECTOR
    lin = lineage_id(v["chainId"], v["mandateManager"], v["customer"], v["merchantId"], v["subscriptionRef"], v["creationNonce"])
    cyc = cycle_id(lin, v["cycleIndex"])
    pid = payment_id_recurring(v["chainId"], v["mandateManager"], lin, cyc)
    q = dict(v["quote"], paymentId=hx(pid), routeHash=hx(route_hash_direct(v["chainId"], v["quote"]["token"])),
             priceSourceSetHash=hx(keccak256(b"fastpay-test-source-set-v1")))
    ds = domain_separator("FastPay Quote", "1", v["chainId"], v["router"])
    sh = quote_struct_hash(q)
    dg = digest(ds, sh)
    ds_b = domain_separator("FastPay Quote", "1", v["chainId"], v["routerB"])
    return dict(lineageId=hx(lin), mandateId0=hx(mandate_id(lin, 0)), cycleId=hx(cyc), paymentId=hx(pid),
                routeHash=q["routeHash"], priceSourceSetHash=q["priceSourceSetHash"],
                domainTypeHash=hx(keccak256(DOMAIN_TYPE.encode())), priceQuoteTypeHash=hx(keccak256(QUOTE_TYPE.encode())),
                domainSeparator=hx(ds), structHash=hx(sh), digest=hx(dg), digestOnRouterB=hx(digest(ds_b, sh)),
                fiatValueMinor=fiat_value_minor(q["amountIn"], q["priceE18"], v["tokenDecimals"]))


def pin_vectors():
    d1, d2 = "0x" + "ab" * 20, "0x" + "cd" * 20
    out = dict(keccakEmpty=hx(KECCAK_EMPTY), pinEOA=hx(PIN_EOA), designatorCodeD1=hx(designator_code(d1)),
               designatorHashD1=hx(designator_hash(d1)), designatorHashD2=hx(designator_hash(d2)))
    # revision 0.5: the typed struct (document 17 section 5.1)
    pins = example_pins()
    out.update(accountPinTypeHash=hx(ACCOUNT_PIN_TYPEHASH), testDelegateCodeHash=hx(TEST_DELEGATE_CODE_HASH),
               testAccountCodeHash=hx(TEST_ACCOUNT_CODE_HASH), familyDelegator=hx(TEST_FAMILY_DELEGATOR),
               familyAccount=hx(TEST_FAMILY_ACCOUNT), pinHashEoa=hx(pin_struct_hash(pins["pinEoa"])),
               pinHash7702=hx(pin_struct_hash(pins["pin7702"])), pinHash4337=hx(pin_struct_hash(pins["pin4337"])))
    return out


TYPED_FAMILIES = ("perPaymentMax", "dayMax", "weekMax", "thirtyDayMax", "periodMax", "totalMax")      # the order of TokenTerms (eip712/types.json)


def typed_terms_of_snapshot(d):
    """The typed MandateTerms value (field names of eip712/types.json) of a snapshot dictionary of this module: the flat shape that
    `contained` reads (tokens, caps by token, fiatPerPaymentMax ... fiatTotalMax, minInterval). Used to hash a snapshot."""
    return dict(merchantId=d["merchantId"], recipientPolicy=d["recipientPolicy"], subscriptionRef=d["subscriptionRef"],
                periodSeconds=d["periodSeconds"], anchorStartsAt=d.get("anchorStartsAt", 0), expiresAt=d["expiresAt"],
                tokens=[dict(token=t, **{f: d["caps"][t][f] for f in TYPED_FAMILIES}) for t in d["tokens"]],
                fiat=dict(currency=d["currency"], perPaymentMaxMinor=d["fiatPerPaymentMax"], dayMaxMinor=d["fiatDayMax"],
                          weekMaxMinor=d["fiatWeekMax"], thirtyDayMaxMinor=d["fiatThirtyDayMax"], periodMaxMinor=d["fiatPeriodMax"],
                          totalMaxMinor=d["fiatTotalMax"], maxQuoteAge=d["maxQuoteAge"], boundsVersion=d["boundsVersion"]),
                maxChargesPerPeriod=d["maxChargesPerPeriod"], minIntervalSeconds=d["minInterval"], maxFeeBps=d["maxFeeBps"],
                extensionsHash=d["extensionsHash"])


def snapshot_reference():
    """The predecessor snapshot of document 12 section 5.3.4 and a successor that is contained in it (flat dictionaries). The
    lineage, predecessor, generation and customer of the dictionary are the arguments of the snapshot hash."""
    t1, t2 = "0x" + "55" * 20, "0x" + "66" * 20
    zero = bytes(32)
    pred = dict(lineageId="0x" + "77" * 32, predecessorId="0x" + "78" * 32, generation=0, customer="0x" + "44" * 20,
                expiresAt=1_900_000_000, merchantId="0x" + "aa" * 32, recipientPolicy="0x" + "01" * 32, subscriptionRef="0x" + "bb" * 32,
                periodSeconds=2_592_000, anchorStartsAt=1_800_000_000, currency=840, tokens=[t1, t2],
                caps={t1: dict(perPaymentMax=51_020_409, totalMax=612_244_908, dayMax=0, weekMax=0, thirtyDayMax=51_020_409, periodMax=0),
                      t2: dict(perPaymentMax=51_020_409, totalMax=612_244_908, dayMax=0, weekMax=0, thirtyDayMax=51_020_409, periodMax=0)},
                fiatPerPaymentMax=5000, fiatTotalMax=60000, fiatDayMax=0, fiatWeekMax=0, fiatThirtyDayMax=5000, fiatPeriodMax=0,
                maxQuoteAge=120, boundsVersion=1, maxChargesPerPeriod=1, minInterval=86_400,
                maxFeeBps=100, extensionsHash=zero)
    import copy
    ok = copy.deepcopy(pred)
    ok["tokens"] = [t1]
    ok["caps"] = {t1: dict(perPaymentMax=40_000_000, totalMax=500_000_000, dayMax=0, weekMax=0, thirtyDayMax=40_000_000, periodMax=0)}
    ok["expiresAt"] = 1_850_000_000
    ok["fiatTotalMax"] = 50000
    ok["maxFeeBps"] = 50                                    # K.6: the narrower successor keeps the bounds version of the predecessor
    return pred, ok


def snapshot_vector():
    import copy
    import pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))        # python -I does not put the script directory on the path
    from eip712_types import Registry, load                                  # imported here: eip712_types imports this module
    pred, ok = snapshot_reference()
    typed = typed_terms_of_snapshot(pred)
    out = {"snapshotHash": hx(snapshot_hash(pred["lineageId"], pred["predecessorId"], pred["generation"], pred["customer"], typed)),
           "termsHash": hx(Registry(load()).hash_struct("MandateTerms", typed)),
           "contained(narrower)": contained(ok, pred)}
    t1 = pred["tokens"][0]
    cases = {
        "longer expiry": ("expiresAt", pred["expiresAt"] + 1), "other merchant": ("merchantId", "0x" + "ac" * 32),
        "higher fee cap": ("maxFeeBps", 101), "bounds version +1": ("boundsVersion", pred["boundsVersion"] + 1),
        "bounds version -1": ("boundsVersion", pred["boundsVersion"] - 1), "faster cadence": ("minInterval", 3600),
        "non-zero extensions": ("extensionsHash", b"\x01" * 32), "more charges per period": ("maxChargesPerPeriod", 2),
        "higher fiat total": ("fiatTotalMax", 60001), "removed fiat total cap (0 = none)": ("fiatTotalMax", 0),
    }
    for name, (k, val) in cases.items():
        s = copy.deepcopy(ok)
        s[k] = val
        out["rejects " + name] = contained(s, pred)
    s = copy.deepcopy(ok)
    s["tokens"] = [t1, "0x" + "99" * 20]
    s["caps"]["0x" + "99" * 20] = s["caps"][t1]
    out["rejects extra token"] = contained(s, pred)
    s = copy.deepcopy(ok)
    s["caps"][t1]["perPaymentMax"] = pred["caps"][t1]["perPaymentMax"] + 1
    out["rejects higher per-payment cap"] = contained(s, pred)
    return out


def main():
    self_check()
    print("== PriceQuote v1")
    for k, val in quote_vector().items():
        print(f"{k:22s} {val}")
    print("== account pins")
    for k, val in pin_vectors().items():
        print(f"{k:22s} {val}")
    print("== migration snapshot and containment")
    for k, val in snapshot_vector().items():
        print(f"{k:42s} {val}")
    print("self-check: ok")


if __name__ == "__main__":
    sys.exit(main())
