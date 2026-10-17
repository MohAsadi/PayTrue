#!/usr/bin/env python3
"""Generic EIP-712 encoder driven by spec/eip712/types.json (revision 0.5.0).

Reference implementation number one of the FastPay typed data. The Solidity library (`FastPayTypes.sol`) and the TypeScript module are
generated from, or read, the same types.json, and must reproduce the golden vectors this module writes. Independent implementations of
the same rules: Python (this file), Solidity (generated), TypeScript (`eip712/fastpay-eip712.ts`), and Foundry's own `vm.eip712Hash*`
cheat codes (cross-check in `EIP712Types.t.sol`).

No dependencies; Keccak-256 comes from tools/eip712_vectors.py (self-checked against known vectors).
"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import eip712_vectors as V  # noqa: E402
import secp256k1_min as K  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
TYPES_PATH = ROOT / "eip712" / "types.json"

_ATOMIC = re.compile(r"^(address|bool|bytes32|bytes\d+|uint\d+|int\d+)$")


def load(path=TYPES_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class Registry:
    def __init__(self, doc):
        self.doc = doc
        self.structs = {s["name"]: s for s in doc["structs"]}
        assert len(self.structs) == len(doc["structs"]), "duplicate struct name"

    # ---- type strings
    def member(self, field):
        t, n = field
        return f"{t} {n}"

    def struct_string(self, name):
        s = self.structs[name]
        return f"{name}(" + ",".join(self.member(f) for f in s["fields"]) + ")"

    @staticmethod
    def base(t):
        return t[:-2] if t.endswith("[]") else t

    def deps(self, name):
        """Every struct type referenced (transitively) by `name`, excluding `name` itself."""
        seen = set()

        def walk(n):
            for t, _ in self.structs[n]["fields"]:
                b = self.base(t)
                if b in self.structs and b not in seen and b != name:
                    seen.add(b)
                    walk(b)
        walk(name)
        return seen

    def encode_type(self, name):
        """EIP-712 encodeType: the primary type, then every referenced type sorted by name."""
        return self.struct_string(name) + "".join(self.struct_string(d) for d in sorted(self.deps(name)))

    def type_hash(self, name):
        return V.keccak256(self.encode_type(name).encode())

    # ---- values
    def encode_atomic(self, t, v):
        if t == "address":
            return V.addr(v)
        if t == "bool":
            return V.u(1 if v else 0)
        if t.startswith("bytes"):
            n = int(t[5:])
            b = bytes.fromhex(v[2:] if isinstance(v, str) else v.hex())
            assert len(b) == n, (t, v)
            return b + bytes(32 - n)
        if t.startswith("uint"):
            bits = int(t[4:])
            n = int(v)
            assert 0 <= n < 1 << bits, f"{t} out of range: {v}"
            return V.u(n)
        raise ValueError(t)

    def encode_value(self, t, v):
        if t.endswith("[]"):
            b = t[:-2]
            return V.keccak256(b"".join(self.encode_value(b, x) for x in v))
        if t in self.structs:
            return self.hash_struct(t, v)
        assert _ATOMIC.match(t), t
        return self.encode_atomic(t, v)

    def hash_struct(self, name, value):
        fields = self.structs[name]["fields"]
        assert set(value) == {n for _, n in fields}, f"{name}: fields {sorted(value)} != {sorted(n for _, n in fields)}"
        return V.keccak256(self.type_hash(name) + b"".join(self.encode_value(t, value[n]) for t, n in fields))

    # ---- domains and digests
    def domain_separator(self, domain, chain_id, verifying):
        d = self.doc["domains"][domain]
        return V.domain_separator(d["name"], d["version"], chain_id, verifying)

    def digest(self, domain, chain_id, verifying, name, value):
        return V.digest(self.domain_separator(domain, chain_id, verifying), self.hash_struct(name, value))

    # ---- Permit2 witness
    def witness_type_string(self):
        w = self.doc["permit2Witness"]
        return f"{w['witness']} {w['witnessField']})" + self.struct_string(w["witness"]) + w["tokenPermissions"]

    def permit2_domain_separator(self, chain_id, permit2):
        w = self.doc["permit2Witness"]["domain"]
        return V.keccak256(V.keccak256(w["type"].encode()) + V.keccak256(w["name"].encode()) + V.u(chain_id) + V.addr(permit2))

    def permit2_witness_hash(self, token, amount, spender, nonce, deadline, witness_value, batch=False, extra=None):
        """hashStruct of PermitWitnessTransferFrom / PermitBatchWitnessTransferFrom as Permit2 computes it (PermitHash.sol)."""
        w = self.doc["permit2Witness"]
        stub = w["stubBatch"] if batch else w["stubSingle"]
        typehash = V.keccak256((stub + self.witness_type_string()).encode())
        tp_hash = V.keccak256(V.keccak256(w["tokenPermissions"].encode()) + V.addr(token) + V.u(amount))
        if batch:
            hashes = [tp_hash] + [V.keccak256(V.keccak256(w["tokenPermissions"].encode()) + V.addr(t) + V.u(a)) for t, a in (extra or [])]
            tp_hash = V.keccak256(b"".join(hashes))
        witness = self.hash_struct(w["witness"], witness_value)
        return V.keccak256(typehash + tp_hash + V.addr(spender) + V.u(nonce) + V.u(deadline) + witness), typehash, witness


# ---------------------------------------------------------------------------------------------------- golden vectors
CHAIN_ID = 84532
MANDATE_MANAGER = "0x2222222222222222222222222222222222222222"
ROUTER = "0x1111111111111111111111111111111111111111"
PERMIT2_VECTOR_ADDRESS = "0x000000000022D473030F116dDEE9F6B43aC78BA3"
T1, T2, T3 = "0x" + "55" * 20, "0x" + "66" * 20, "0x" + "77" * 20
CUSTOMER = "0x" + "44" * 20


def h32(s):
    return V.hx(V.keccak256(s.encode()))


def sample_values(reg):
    """One fully populated value of every struct. Illustrative addresses and amounts; no production value."""
    # Every leaf of one struct that has the same type gets a different value, so a swap of two fields in an implementation changes the hash.
    pin = dict(accountMode=2, accountCodeHash=V.hx(V.designator_hash(V.TEST_DELEGATE_D1)), delegate=V.TEST_DELEGATE_D1,
               delegateCodeHash=V.hx(V.TEST_DELEGATE_CODE_HASH), implementationFamily=V.hx(V.TEST_FAMILY_DELEGATOR), pinVersion=1,
               signatureMode=1)
    token = lambda a, k: dict(token=a, perPaymentMax=51_020_409 + k, dayMax=10_000_001 + k, weekMax=20_000_002 + k,
                              thirtyDayMax=30_000_003 + k, periodMax=40_000_004 + k, totalMax=612_244_908 + k)
    fiat = dict(currency=840, perPaymentMaxMinor=5000, dayMaxMinor=1001, weekMaxMinor=2002, thirtyDayMaxMinor=3003, periodMaxMinor=4004,
                totalMaxMinor=60000, maxQuoteAge=120, boundsVersion=3)
    terms = dict(merchantId="0x" + "aa" * 32, recipientPolicy="0x" + "01" * 32, subscriptionRef="0x" + "bb" * 32, periodSeconds=2_592_000,
                 anchorStartsAt=1_800_000_000, expiresAt=1_900_000_000, tokens=[token(T1, 0), token(T2, 100)], fiat=fiat,
                 maxChargesPerPeriod=4, minIntervalSeconds=86_400, maxFeeBps=100, extensionsHash="0x" + "00" * 32)
    narrower = dict(terms, tokens=[token(T1, 0)], expiresAt=1_850_000_000)
    d = 1_800_003_600
    return {
        "AccountPin": pin,
        "TokenTerms": token(T1, 1),
        "FiatTerms": fiat,
        "MandateTerms": terms,
        "ActivationTerms": dict(customer=CUSTOMER, router=ROUTER, routerCodeHash=h32("fastpay-test-router-v1"), routerVersion=1,
                                creationNonce=7, terms=terms, accountPin=pin, deadline=d),
        "SuccessorAuthorization": dict(customer=CUSTOMER, lineageId="0x" + "77" * 32, predecessorId="0x" + "78" * 32, kind=2,
                                       newTermsHash="0x" + "99" * 32, newRouter="0x1212121212121212121212121212121212121212",
                                       newRouterCodeHash=h32("fastpay-test-router-v2"), newRouterVersion=2,
                                       termsSnapshotHash="0x" + "98" * 32, widenedMask=5, accountPin=pin, deadline=d, nonce=5),
        "AccountPinUpdate": dict(customer=CUSTOMER, mandateId="0x" + "10" * 32, newPin=dict(pin, pinVersion=2), deadline=d, nonce=6),
        "AccountPinsUpdate": dict(customer=CUSTOMER, mandateIds=["0x" + "10" * 32, "0x" + "11" * 32, "0x" + "12" * 32],
                                  newPin=dict(pin, pinVersion=2), deadline=d, nonce=8),
        "RevokeMandate": dict(customer=CUSTOMER, mandateId="0x" + "10" * 32, deadline=d, nonce=9),
        "PauseMandate": dict(customer=CUSTOMER, mandateId="0x" + "10" * 32, deadline=d, nonce=10),
        "ResumeMandate": dict(customer=CUSTOMER, mandateId="0x" + "10" * 32, deadline=d, nonce=11),
        "ReduceMandate": dict(customer=CUSTOMER, mandateId="0x" + "10" * 32, oldTermsHash=V.hx(reg.hash_struct("MandateTerms", terms)),
                              newTermsHash=V.hx(reg.hash_struct("MandateTerms", narrower)), deadline=d, nonce=12),
        # the vector of document 11 section 4.6 has issuedAt = validAfter, which cannot detect a swap of the two fields (finding F-10);
        # the golden vector separates them by one second. self_check still reproduces the document's own vector.
        "PriceQuote": dict(_quote_value(), validAfter=V.VECTOR["quote"]["validAfter"] + 1),
        "PayOnceIntent": dict(paymentId="0x" + "21" * 32, merchantId="0x" + "aa" * 32, recipient="0x" + "31" * 20,
                              feeRecipient="0x" + "32" * 20, token=T1, grossAmountIn=50_000_000, merchantAmount=49_500_000,
                              feeAmount=500_000, payer=CUSTOMER, validUntil=1_800_000_300, termsHash="0x" + "22" * 32,
                              quoteHash="0x" + "00" * 32),
    }


def _quote_value():
    v = V.VECTOR
    q = V.quote_vector()
    return dict(paymentId=q["paymentId"], payer=v["quote"]["payer"], token=v["quote"]["token"], amountIn=v["quote"]["amountIn"],
                currency=v["quote"]["currency"], priceE18=v["quote"]["priceE18"], issuedAt=v["quote"]["issuedAt"],
                validAfter=v["quote"]["validAfter"], validUntil=v["quote"]["validUntil"], nonce=v["quote"]["nonce"],
                signerSetVersion=v["quote"]["signerSetVersion"], registryVersion=v["quote"]["registryVersion"],
                boundsVersion=v["quote"]["boundsVersion"], routeHash=q["routeHash"], priceSourceSetHash=q["priceSourceSetHash"])


def assert_distinct_leaves(reg, name, value):
    """Within one struct, no two atomic fields of the same type carry the same value (a swapped pair must change the hash)."""
    seen = {}
    for t, f in reg.structs[name]["fields"]:
        if t in reg.structs or t.endswith("[]"):
            continue
        key = (t, str(value[f]).lower())
        assert key not in seen, f"{name}: fields {seen[key]} and {f} are both {t} {value[f]}: the vector cannot detect a swap"
        seen[key] = f


def freeze_fingerprint(reg):
    """SHA-256 over every string that would be frozen: domain type, domains, every encodeType, the Permit2 witness strings, the tags, the
    bounds and the snapshot encoding words. Prose (notes, sources, status) is not part of it, so a note can change without a new approval,
    and a change of any string cannot."""
    doc = reg.doc
    body = {"domainType": doc["domainType"],
            "domains": {k: {"name": d["name"], "version": d["version"], "verifyingContract": d["verifyingContract"]} for k, d in doc["domains"].items()},
            "types": {s["name"]: reg.encode_type(s["name"]) for s in doc["structs"]},
            "witnessTypeString": reg.witness_type_string(),
            "permit2": {k: doc["permit2Witness"][k] for k in ("stubSingle", "stubBatch", "tokenPermissions")} | {"domain": doc["permit2Witness"]["domain"]},
            "tags": doc["tags"], "bounds": {k: b["value"] for k, b in doc["bounds"].items()},
            "snapshotWords": doc["snapshotEncoding"]["words"], "snapshotTokenWords": doc["snapshotEncoding"]["tokenWords"],
            "versioning": doc["versioning"]["rules"]}
    import hashlib
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _json_safe(x):
    if isinstance(x, dict):
        return {k: _json_safe(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_json_safe(v) for v in x]
    if isinstance(x, bytes):
        return V.hx(x)
    if isinstance(x, int) and not isinstance(x, bool):
        return str(x)
    return x


def golden_vectors(reg=None):
    reg = reg or Registry(load())
    doc = reg.doc
    values = sample_values(reg)
    out = {"schema": 1, "specVersion": doc["specVersion"], "status": doc["status"], "chainId": CHAIN_ID,
           "mandateManager": MANDATE_MANAGER, "router": ROUTER, "permit2": PERMIT2_VECTOR_ADDRESS,
           "domainTypeHash": V.hx(V.keccak256(doc["domainType"].encode())), "freezeFingerprintSha256": freeze_fingerprint(reg), "domains": {}, "structs": {}, "permit2Witness": {},
           "tags": {k: dict(string=s, hash=V.hx(V.keccak256(s.encode()))) for k, s in doc["tags"].items()},
           "snapshot": {}}
    for name, dom in doc["domains"].items():
        verifying = MANDATE_MANAGER if name == "mandates" else ROUTER
        out["domains"][name] = dict(name=dom["name"], version=dom["version"], verifyingContract=verifying,
                                    separator=V.hx(reg.domain_separator(name, CHAIN_ID, verifying)))
    for s in doc["structs"]:
        n = s["name"]
        assert_distinct_leaves(reg, n, values[n])
        entry = dict(domain=s["domain"], status=s["status"], encodeType=reg.encode_type(n), typeHash=V.hx(reg.type_hash(n)),
                     value=_json_safe(values[n]), hashStruct=V.hx(reg.hash_struct(n, values[n])))
        if s["domain"] in ("mandates", "quote"):
            verifying = MANDATE_MANAGER if s["domain"] == "mandates" else ROUTER
            entry["digest"] = V.hx(reg.digest(s["domain"], CHAIN_ID, verifying, n, values[n]))
        # field sensitivity: the struct hash of each single-field mutation (every field must move the hash)
        mutated = {}
        for t, fname in s["fields"]:
            m = _mutate(values[n], fname, t, reg)
            mutated[fname] = V.hx(reg.hash_struct(n, m))
        entry["mutatedFieldHashes"] = mutated
        assert len(set(mutated.values())) == len(mutated) and entry["hashStruct"] not in mutated.values(), n
        out["structs"][n] = entry
    # Permit2 witness (single and batch), spender = the router of the vector
    w = doc["permit2Witness"]
    wv = values[w["witness"]]
    dsep = reg.permit2_domain_separator(CHAIN_ID, PERMIT2_VECTOR_ADDRESS)
    perm = dict(token=wv["token"], amount=wv["grossAmountIn"], spender=ROUTER, nonce=0x1234, deadline=1_800_000_300)
    single, th_s, wit = reg.permit2_witness_hash(perm["token"], perm["amount"], perm["spender"], perm["nonce"], perm["deadline"], wv)
    batch, th_b, _ = reg.permit2_witness_hash(perm["token"], perm["amount"], perm["spender"], perm["nonce"], perm["deadline"], wv,
                                              batch=True, extra=[(T2, 7)])
    out["permit2Witness"] = dict(
        witnessTypeString=reg.witness_type_string(), stubSingle=w["stubSingle"], stubBatch=w["stubBatch"],
        typeStringSingle=w["stubSingle"] + reg.witness_type_string(), typeStringBatch=w["stubBatch"] + reg.witness_type_string(),
        typeHashSingle=V.hx(th_s), typeHashBatch=V.hx(th_b), tokenPermissionsTypeHash=V.hx(V.keccak256(w["tokenPermissions"].encode())),
        permit2DomainTypeHash=V.hx(V.keccak256(w["domain"]["type"].encode())),
        permit2DomainSeparator=V.hx(dsep), permit=_json_safe(perm), witnessHash=V.hx(wit),
        hashSingle=V.hx(single), digestSingle=V.hx(V.digest(dsep, single)),
        batchExtra=[dict(token=T2, amount="7")], hashBatch=V.hx(batch), digestBatch=V.hx(V.digest(dsep, batch)))
    # signatures: a fixed, public TEST key signs every digest; the EVM's ecrecover must return its address (EIP712Golden.t.sol), which
    # also validates the pure-Python recovery that tools/wallet_lab_verify.py uses on signatures made in real wallets
    priv = int.from_bytes(V.keccak256(b"fastpay-eip712-golden-test-key-v1"), "big") % K.N
    signer = K.address_of(K.public_key(priv))
    sigs = {}
    for n, e in out["structs"].items():
        if "digest" in e:
            v, r, s = K.sign(bytes.fromhex(e["digest"][2:]), priv)
            sigs[n] = dict(digest=e["digest"], v=v, r=f"0x{r:064x}", s=f"0x{s:064x}")
    out["signatures"] = dict(note="TEST key only (keccak256 of the ASCII string below, mod n); it protects nothing", keyDerivation="fastpay-eip712-golden-test-key-v1",
                             signer=signer, byStruct=sigs)
    # snapshot: the encoding of eip712/types.json snapshotEncoding, applied to the golden MandateTerms
    mt = values["MandateTerms"]
    args = dict(lineageId="0x" + "77" * 32, predecessorId="0x" + "78" * 32, generation=1, customer=CUSTOMER)
    words = V.snapshot_words(args["lineageId"], args["predecessorId"], args["generation"], args["customer"], mt)
    base = V.snapshot_hash(args["lineageId"], args["predecessorId"], args["generation"], args["customer"], mt)
    names = [w[0] for w in doc["snapshotEncoding"]["words"]]
    assert len(words) == len(names) == len(set(words)), "two words of the golden snapshot are equal: a swap would not be detected"
    mutated = {}
    for (name, src) in doc["snapshotEncoding"]["words"]:
        kind, _, field = src.partition(":")
        a2, m2 = dict(args), json.loads(json.dumps(_json_safe(mt)))
        if kind == "tag":
            continue
        if kind == "arg":
            a2[field] = _flip(a2[field], "uint32" if field == "generation" else "address" if field == "customer" else "bytes32")
        elif kind == "terms":
            m2[field] = _flip(m2[field], reg.structs["MandateTerms"]["fields"][[n for _, n in reg.structs["MandateTerms"]["fields"]].index(field)][0])
        elif kind == "terms.fiat":
            m2["fiat"][field] = _flip(m2["fiat"][field], dict((n, ty) for ty, n in reg.structs["FiatTerms"]["fields"])[field])
        elif field == "tokens":
            m2["tokens"][0]["token"] = _flip(m2["tokens"][0]["token"], "address")
        else:
            m2["tokens"][-1]["totalMax"] = _flip(m2["tokens"][-1]["totalMax"], "uint256")
        h = V.snapshot_hash(a2["lineageId"], a2["predecessorId"], a2["generation"], a2["customer"], m2)
        assert h != base, f"snapshot word {name} does not move the hash"
        mutated[name] = V.hx(h)
    assert len(set(mutated.values())) == len(mutated)
    out["snapshot"] = dict(tag=V.hx(V.tag(V.TAG_SNAPSHOT)), arguments=args, terms="structs.MandateTerms.value", words=[V.hx(w) for w in words],
                           wordNames=names, hash=V.hx(base), mutatedWordHashes=mutated)
    return out


def _mutate(value, field, t, reg):
    """A copy of `value` in which exactly one leaf below `field` differs (the first leaf of an array or nested struct)."""
    m = json.loads(json.dumps(value))
    m[field] = _mutate_leaf(m[field], t, reg)
    return m


def _mutate_leaf(v, t, reg):
    if t.endswith("[]"):
        return [_mutate_leaf(v[0], t[:-2], reg)] + v[1:]
    if t in reg.structs:
        n0, t0 = reg.structs[t]["fields"][0][1], reg.structs[t]["fields"][0][0]
        out = dict(v)
        out[n0] = _mutate_leaf(v[n0], t0, reg)
        return out
    return _flip(v, t)


def _flip(v, t):
    if t == "address":
        return v[:-1] + ("0" if v[-1] != "0" else "1")
    if t.startswith("bytes"):
        return v[:-1] + ("0" if v[-1] != "0" else "1")
    if t == "bool":
        return not v
    n = int(v)
    return str(n + 1 if n < (1 << int(t[4:])) - 1 else n - 1)


PERMIT2_SRC = ROOT / "toolchain" / "permit2-build" / "permit2" / "src"


def permit2_source_strings():
    """The type-string literals of the pinned Permit2 source (libraries/PermitHash.sol and the Permit2 domain), or None if the
    extracted tree is absent. Returned as a dict of literal -> True so a caller can test membership of what types.json claims."""
    ph = PERMIT2_SRC / "libraries" / "PermitHash.sol"
    ed = PERMIT2_SRC / "EIP712.sol"
    if not ph.exists() or not ed.exists():
        return None
    text = ph.read_text(encoding="utf-8") + "\n" + ed.read_text(encoding="utf-8")
    return {m: True for m in re.findall(r'"((?:[^"\\]|\\.)*)"', text)}


def check_permit2_source(reg):
    lits = permit2_source_strings()
    if lits is None:
        return False
    w = reg.doc["permit2Witness"]
    for key in ("tokenPermissions", "stubSingle", "stubBatch"):
        assert w[key] in lits, f"types.json permit2Witness.{key} is not a string literal of the pinned Permit2 source: {w[key]}"
    assert w["domain"]["type"] in lits or w["domain"]["type"].replace("EIP712Domain(", "EIP712Domain(") in lits, "Permit2 domain type"
    return True


def self_check(reg):
    # EIP-712 encodeType rules on the types of the documents
    assert reg.encode_type("AccountPin") == V.ACCOUNT_PIN_TYPE
    assert reg.encode_type("PriceQuote") == V.QUOTE_TYPE
    assert V.hx(reg.type_hash("AccountPin")) == V.hx(V.ACCOUNT_PIN_TYPEHASH)
    assert V.hx(reg.type_hash("PriceQuote")) == V.quote_vector()["priceQuoteTypeHash"]
    assert reg.encode_type("SuccessorAuthorization").endswith(")AccountPin(" + V.ACCOUNT_PIN_TYPE.split("(", 1)[1])
    # the nested types come in alphabetical order after the primary type
    assert reg.encode_type("ActivationTerms").split(")")[0].startswith("ActivationTerms(")
    names = re.findall(r"\)([A-Z][A-Za-z]+)\(", reg.encode_type("ActivationTerms"))
    assert names == sorted(names) == ["AccountPin", "FiatTerms", "MandateTerms", "TokenTerms"], names
    # the quote vector is the same under the generic encoder and under the dedicated one of tools/eip712_vectors.py
    q = _quote_value()
    qv = V.quote_vector()
    assert V.hx(reg.hash_struct("PriceQuote", q)) == qv["structHash"]
    assert V.hx(reg.digest("quote", V.VECTOR["chainId"], V.VECTOR["router"], "PriceQuote", q)) == qv["digest"]
    # the pins
    pv = V.pin_vectors()
    for k, hk in (("pinEoa", "pinHashEoa"), ("pin7702", "pinHash7702"), ("pin4337", "pinHash4337")):
        p = {a: (V.hx(b) if isinstance(b, bytes) else b) for a, b in V.example_pins()[k].items()}
        assert V.hx(reg.hash_struct("AccountPin", p)) == pv[hk], k
    # the Permit2 strings equal the ones in the source at the pinned commit (read from the verified extracted tree, when present)
    check_permit2_source(reg)
    assert reg.witness_type_string().startswith("PayOnceIntent witness)PayOnceIntent(") and reg.witness_type_string().endswith(
        ")TokenPermissions(address token,uint256 amount)")
    # sanity: every struct type string has no space after a comma, every member has a type and a name
    for s in reg.doc["structs"]:
        st = reg.struct_string(s["name"])
        assert ", " not in st and " ," not in st, st


# ---------------------------------------------------------------------------------------------------- wallet payloads (eth_signTypedData_v4)
def _members(reg, name):
    return [{"name": n, "type": ty} for ty, n in reg.structs[name]["fields"]]


def wallet_payload(reg, name, value, domain, chain_id, verifying):
    """The JSON a dapp passes to eth_signTypedData_v4 for message `name` of the mandates or quote domain."""
    d = reg.doc["domains"][domain]
    types = {"EIP712Domain": [{"name": "name", "type": "string"}, {"name": "version", "type": "string"},
                              {"name": "chainId", "type": "uint256"}, {"name": "verifyingContract", "type": "address"}]}
    for n in [name] + sorted(reg.deps(name)):
        types[n] = _members(reg, n)
    return {"types": types, "primaryType": name,
            "domain": {"name": d["name"], "version": d["version"], "chainId": str(chain_id), "verifyingContract": verifying},
            "message": _json_safe(value)}


def permit2_wallet_payload(reg, witness_value, token, amount, spender, nonce, deadline, chain_id, permit2, batch=False, extra=None):
    w = reg.doc["permit2Witness"]
    wn = w["witness"]
    primary = "PermitBatchWitnessTransferFrom" if batch else "PermitWitnessTransferFrom"
    permitted_t = "TokenPermissions[]" if batch else "TokenPermissions"
    types = {"EIP712Domain": [{"name": "name", "type": "string"}, {"name": "chainId", "type": "uint256"},
                              {"name": "verifyingContract", "type": "address"}],
             primary: [{"name": "permitted", "type": permitted_t}, {"name": "spender", "type": "address"},
                       {"name": "nonce", "type": "uint256"}, {"name": "deadline", "type": "uint256"}, {"name": w["witnessField"], "type": wn}],
             "TokenPermissions": [{"name": "token", "type": "address"}, {"name": "amount", "type": "uint256"}],
             wn: _members(reg, wn)}
    permitted = {"token": token, "amount": str(amount)}
    if batch:
        permitted = [permitted] + [{"token": tk, "amount": str(a)} for tk, a in (extra or [])]
    return {"types": types, "primaryType": primary,
            "domain": {"name": w["domain"]["name"], "chainId": str(chain_id), "verifyingContract": permit2},
            "message": {"permitted": permitted, "spender": spender, "nonce": str(nonce), "deadline": str(deadline),
                        w["witnessField"]: _json_safe(witness_value)}}


def payload_digest(payload):
    """EIP-712 digest of a wallet payload, computed from the payload alone (its own types, domain and message): a second path to the
    digest that does not use types.json, so a payload that drifted from the types is caught."""
    types = dict(payload["types"])
    dom_fields = types.pop("EIP712Domain")
    doc = {"structs": [{"name": n, "domain": "x", "fields": [[m["type"], m["name"]] for m in ms]} for n, ms in types.items()]}
    reg = Registry(doc)
    dom_type = "EIP712Domain(" + ",".join(f"{m['type']} {m['name']}" for m in dom_fields) + ")"
    enc = b""
    for m in dom_fields:
        v = payload["domain"][m["name"]]
        enc += V.keccak256(v.encode()) if m["type"] == "string" else reg.encode_atomic(m["type"], v)
    dsep = V.keccak256(V.keccak256(dom_type.encode()) + enc)
    return V.digest(dsep, reg.hash_struct(payload["primaryType"], payload["message"]))


def main():
    reg = Registry(load())
    self_check(reg)
    g = golden_vectors(reg)
    for n, e in g["structs"].items():
        print(f"{n:24s} typeHash {e['typeHash']}  hashStruct {e['hashStruct']}")
    print("witnessTypeString", g["permit2Witness"]["witnessTypeString"])
    print("typeHashSingle   ", g["permit2Witness"]["typeHashSingle"])
    print("typeHashBatch    ", g["permit2Witness"]["typeHashBatch"])
    print("self-check: ok")


if __name__ == "__main__":
    sys.exit(main())
