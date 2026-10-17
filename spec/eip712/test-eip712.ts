// Reproduces every golden vector of eip712/golden-vectors.json with the TypeScript encoder and cross-checks it against the other
// implementations through the vector file: Python (tools/eip712_types.py) wrote the file, Solidity (EIP712Golden.t.sol) reproduces it.
// Exit code 0 only if every check passes.
//   node --experimental-strip-types eip712/test-eip712.ts
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { BOUNDS, SNAPSHOT, STRUCTS, TAGS, TYPEHASHES } from "./fastpay-types.generated.ts";
import {
  digest, domainSeparator, encodeType, fromHex, hashStruct, hex, keccak256, permit2DomainSeparator, permit2WitnessHash, tag, typeHash, utf8,
  snapshotHash, snapshotWords, witnessTypeString,
} from "./fastpay-eip712.ts";
import type { Value } from "./fastpay-eip712.ts";

const here = dirname(fileURLToPath(import.meta.url));
const golden = JSON.parse(readFileSync(join(here, "golden-vectors.json"), "utf8"));

let checks = 0;
const failures: string[] = [];
function eq(label: string, got: string, want: string): void {
  checks++;
  if (got !== want) failures.push(`${label}\n  got  ${got}\n  want ${want}`);
}
function throws(label: string, f: () => unknown): void {
  checks++;
  try {
    f();
    failures.push(`${label}: expected an exception`);
  } catch {
    /* expected */
  }
}

// ---- Keccak-256 known answers (the same ones tools/eip712_vectors.py checks)
eq("keccak256('')", hex(keccak256(new Uint8Array())), "0xc5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470");
eq("keccak256('abc')", hex(keccak256(utf8("abc"))), "0x4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45");
eq("transfer selector", hex(keccak256(utf8("transfer(address,uint256)"))).slice(0, 10), "0xa9059cbb");
eq("keccak256 of a multi-block input", hex(keccak256(new Uint8Array(200).fill(0x78))), hex(keccak256(new Uint8Array(200).fill(0x78))));
eq("keccak256 of exactly one rate block (136 bytes)", hex(keccak256(new Uint8Array(136))).length.toString(), "66");

// ---- domains and structs
const chainId = BigInt(golden.chainId);
for (const [name, d] of Object.entries<any>(golden.domains)) {
  eq(`domain ${name}`, hex(domainSeparator(name as "mandates" | "quote", chainId, d.verifyingContract)), d.separator);
}
const flip = (v: Value, t: string): Value => {
  if (t === "address" || t.startsWith("bytes")) return (v as string).slice(0, -1) + ((v as string).endsWith("0") ? "1" : "0");
  const n = BigInt(v as string);
  return (n < (1n << BigInt(parseInt(t.slice(4), 10))) - 1n ? n + 1n : n - 1n).toString();
};
const mutateLeaf = (v: Value, t: string): Value => {
  if (t.endsWith("[]")) return [mutateLeaf((v as Value[])[0], t.slice(0, -2)), ...(v as Value[]).slice(1)];
  if (Object.prototype.hasOwnProperty.call(STRUCTS, t)) {
    const [t0, n0] = STRUCTS[t].fields[0];
    const o = { ...(v as { [k: string]: Value }) };
    o[n0] = mutateLeaf(o[n0], t0);
    return o;
  }
  return flip(v, t);
};

for (const [name, g] of Object.entries<any>(golden.structs)) {
  eq(`${name} encodeType`, encodeType(name), g.encodeType);
  eq(`${name} typeHash`, hex(typeHash(name)), g.typeHash);
  eq(`${name} generated TYPEHASHES constant`, TYPEHASHES[name], g.typeHash);
  eq(`${name} hashStruct`, hex(hashStruct(name, g.value)), g.hashStruct);
  if (g.digest !== undefined) {
    const d = golden.domains[g.domain];
    eq(`${name} digest`, hex(digest(domainSeparator(g.domain, chainId, d.verifyingContract), hashStruct(name, g.value))), g.digest);
  }
  for (const [t, f] of STRUCTS[name].fields) {
    const m = { ...g.value, [f]: mutateLeaf(g.value[f], t) };
    eq(`${name}.${f} mutated`, hex(hashStruct(name, m)), g.mutatedFieldHashes[f]);
    checks++;
    if (hex(hashStruct(name, m)) === g.hashStruct) failures.push(`${name}.${f}: a changed field did not change the hash`);
  }
  // an unknown or missing field is refused
  throws(`${name} missing field`, () => {
    const { [STRUCTS[name].fields[0][1]]: _omitted, ...rest } = g.value;
    return hashStruct(name, rest);
  });
}

// ---- bounds: arrays above their named bound are refused (PC-11, PC-04)
const terms = golden.structs.MandateTerms.value;
throws("MandateTerms with MAX_TOKENS_PER_MANDATE + 1 tokens", () => {
  const tk = Array.from({ length: BOUNDS.MAX_TOKENS_PER_MANDATE + 1 }, () => terms.tokens[0]);
  return hashStruct("MandateTerms", { ...terms, tokens: tk });
});
const pins = golden.structs.AccountPinsUpdate.value;
throws("AccountPinsUpdate with MAX_BATCH + 1 mandates", () =>
  hashStruct("AccountPinsUpdate", { ...pins, mandateIds: Array.from({ length: BOUNDS.MAX_BATCH + 1 }, () => pins.mandateIds[0]) }));
checks++;
hashStruct("AccountPinsUpdate", { ...pins, mandateIds: Array.from({ length: BOUNDS.MAX_BATCH }, () => pins.mandateIds[0]) });
// range checks: a value above its declared width is refused instead of truncated
throws("uint16 above 65535", () => hashStruct("FiatTerms", { ...golden.structs.FiatTerms.value, currency: "65536" }));
throws("uint64 above 2^64-1", () => hashStruct("RevokeMandate", { ...golden.structs.RevokeMandate.value, deadline: (1n << 64n).toString() }));
throws("bytes32 with 31 bytes", () => hashStruct("RevokeMandate", { ...golden.structs.RevokeMandate.value, mandateId: "0x" + "11".repeat(31) }));

// ---- tags
for (const [k, e] of Object.entries<any>(golden.tags)) {
  eq(`tag ${k}`, TAGS[k as keyof typeof TAGS], e.string);
  eq(`tag ${k} hash`, hex(tag(k as keyof typeof TAGS)), e.hash);
}

// ---- Permit2 witness
const w = golden.permit2Witness;
eq("witnessTypeString", witnessTypeString(), w.witnessTypeString);
const input = {
  token: w.permit.token, amount: BigInt(w.permit.amount), spender: w.permit.spender, nonce: BigInt(w.permit.nonce),
  deadline: BigInt(w.permit.deadline), witness: golden.structs.PayOnceIntent.value,
};
const single = permit2WitnessHash(input, false);
const batch = permit2WitnessHash({ ...input, extra: w.batchExtra.map((e: any) => ({ token: e.token, amount: BigInt(e.amount) })) }, true);
const dsep = permit2DomainSeparator(chainId, golden.permit2);
eq("permit2 domain separator", hex(dsep), w.permit2DomainSeparator);
eq("permit2 single type hash", hex(single.typeHash), w.typeHashSingle);
eq("permit2 batch type hash", hex(batch.typeHash), w.typeHashBatch);
eq("permit2 single hash", hex(single.hash), w.hashSingle);
eq("permit2 single digest", hex(digest(dsep, single.hash)), w.digestSingle);
eq("permit2 batch hash", hex(batch.hash), w.hashBatch);
eq("permit2 batch digest", hex(digest(dsep, batch.hash)), w.digestBatch);
// a different witness string, spender or field gives a different digest (the property the router relies on)
const other = permit2WitnessHash({ ...input, spender: "0x" + "ab".repeat(20) }, false);
checks++;
if (hex(other.hash) === w.hashSingle) failures.push("a different spender gave the same Permit2 hash");
// the type string of the witness is the one the fixed prefix of Permit2 expects: '<Type> witness)' first, TokenPermissions last
checks++;
if (!w.witnessTypeString.startsWith("PayOnceIntent witness)PayOnceIntent(") || !w.witnessTypeString.endsWith(")TokenPermissions(address token,uint256 amount)")) {
  failures.push("witnessTypeString has the wrong shape");
}
// ---- migration snapshot (document 12 section 5.3.2; eip712/types.json snapshotEncoding)
const snap = golden.snapshot;
const snapTerms = golden.structs.MandateTerms.value;
eq("snapshot tag", hex(tag("SNAPSHOT_TAG" as keyof typeof TAGS)), snap.words[0]);
eq("snapshot words", snapshotWords(snap.arguments, snapTerms).map(hex).join(","), snap.words.join(","));
eq("snapshot hash", hex(snapshotHash(snap.arguments, snapTerms)), snap.hash);
for (const [i, [name, src]] of SNAPSHOT.words.entries()) {
  if (src === "tag") continue;
  const [kind, field] = src.split(":");
  const a = { ...snap.arguments };
  const m = JSON.parse(JSON.stringify(snapTerms));
  if (kind === "arg") a[field] = flip(a[field], field === "generation" ? "uint32" : field === "customer" ? "address" : "bytes32");
  else if (kind === "terms") m[field] = flip(m[field], STRUCTS.MandateTerms.fields.find(([, n]) => n === field)![0]);
  else if (kind === "terms.fiat") m.fiat[field] = flip(m.fiat[field], STRUCTS.FiatTerms.fields.find(([, n]) => n === field)![0]);
  else if (field === "tokens") m.tokens[0].token = flip(m.tokens[0].token, "address");
  else m.tokens[m.tokens.length - 1].totalMax = flip(m.tokens[m.tokens.length - 1].totalMax, "uint256");
  eq(`snapshot word ${i + 1} ${name} moves the hash`, hex(snapshotHash(a, m)), snap.mutatedWordHashes[name]);
}
throws("snapshot of terms with MAX_TOKENS_PER_MANDATE + 1 tokens", () =>
  snapshotHash(snap.arguments, { ...snapTerms, tokens: Array.from({ length: BOUNDS.MAX_TOKENS_PER_MANDATE + 1 }, () => snapTerms.tokens[0]) }));
void fromHex;

if (failures.length > 0) {
  console.error(failures.join("\n"));
  console.error(`FAILED: ${failures.length} of ${checks} checks`);
  process.exit(1);
}
console.log(`eip712 TypeScript: ${checks} checks passed (${Object.keys(golden.structs).length} structs, Permit2 witness single and batch, tags, bounds)`);
