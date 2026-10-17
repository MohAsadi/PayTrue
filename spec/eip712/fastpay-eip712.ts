// Generic EIP-712 encoder for the FastPay typed data (revision 0.5.0): the TypeScript implementation that the backend and the portal
// share. Self-contained: Keccak-256 is implemented here with BigInt (Node's crypto offers SHA3-256, which pads differently), so it
// has no dependency to pin. Types come from fastpay-types.generated.ts, which tools/export_eip712.py writes from eip712/types.json.
//
// Run the test:  node --experimental-strip-types eip712/test-eip712.ts   (Node 22.18 or later runs it without the flag)
import { BOUNDS, DOMAIN_TYPE, DOMAINS, PERMIT2_WITNESS, SNAPSHOT, STRUCTS, TAGS } from "./fastpay-types.generated.ts";

// ---------------------------------------------------------------------------------------------------- Keccak-256
const MASK = (1n << 64n) - 1n;
const RC: bigint[] = [
  0x0000000000000001n, 0x0000000000008082n, 0x800000000000808an, 0x8000000080008000n, 0x000000000000808bn, 0x0000000080000001n,
  0x8000000080008081n, 0x8000000000008009n, 0x000000000000008an, 0x0000000000000088n, 0x0000000080008009n, 0x000000008000000an,
  0x000000008000808bn, 0x800000000000008bn, 0x8000000000008089n, 0x8000000000008003n, 0x8000000000008002n, 0x8000000000000080n,
  0x000000000000800an, 0x800000008000000an, 0x8000000080008081n, 0x8000000000008080n, 0x0000000080000001n, 0x8000000080008008n,
];
const RHO = [1, 3, 6, 10, 15, 21, 28, 36, 45, 55, 2, 14, 27, 41, 56, 8, 25, 43, 62, 18, 39, 61, 20, 44];
const PI = [10, 7, 11, 17, 18, 3, 5, 16, 8, 21, 24, 4, 15, 23, 19, 13, 12, 2, 20, 14, 22, 9, 6, 1];

function rol(x: bigint, n: number): bigint {
  const s = BigInt(n);
  return ((x << s) | (x >> (64n - s))) & MASK;
}

function keccakF(a: bigint[]): void {
  for (let round = 0; round < 24; round++) {
    const c: bigint[] = [0n, 0n, 0n, 0n, 0n];
    for (let x = 0; x < 5; x++) c[x] = a[x] ^ a[x + 5] ^ a[x + 10] ^ a[x + 15] ^ a[x + 20];
    for (let x = 0; x < 5; x++) {
      const d = c[(x + 4) % 5] ^ rol(c[(x + 1) % 5], 1);
      for (let y = 0; y < 25; y += 5) a[y + x] ^= d;
    }
    let cur = a[1];
    for (let t = 0; t < 24; t++) {
      const j = PI[t];
      const tmp = a[j];
      a[j] = rol(cur, RHO[t]);
      cur = tmp;
    }
    for (let y = 0; y < 25; y += 5) {
      const row = a.slice(y, y + 5);
      for (let x = 0; x < 5; x++) a[y + x] = row[x] ^ (~row[(x + 1) % 5] & MASK & row[(x + 2) % 5]);
    }
    a[0] ^= RC[round];
  }
}

export function keccak256(data: Uint8Array): Uint8Array {
  const rate = 136;
  const padded = new Uint8Array(Math.ceil((data.length + 1) / rate) * rate);
  padded.set(data);
  padded[data.length] ^= 0x01;
  padded[padded.length - 1] ^= 0x80;
  const a: bigint[] = new Array(25).fill(0n);
  for (let off = 0; off < padded.length; off += rate) {
    for (let i = 0; i < rate / 8; i++) {
      let lane = 0n;
      for (let b = 7; b >= 0; b--) lane = (lane << 8n) | BigInt(padded[off + 8 * i + b]);
      a[i] ^= lane;
    }
    keccakF(a);
  }
  const out = new Uint8Array(32);
  for (let i = 0; i < 4; i++) for (let b = 0; b < 8; b++) out[8 * i + b] = Number((a[i] >> BigInt(8 * b)) & 0xffn);
  return out;
}

// ---------------------------------------------------------------------------------------------------- bytes helpers
export type Value = string | number | bigint | boolean | Value[] | { [k: string]: Value };

const enc = new TextEncoder();
export const utf8 = (s: string): Uint8Array => enc.encode(s);

export function concat(...parts: Uint8Array[]): Uint8Array {
  const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
  let o = 0;
  for (const p of parts) {
    out.set(p, o);
    o += p.length;
  }
  return out;
}

export function hex(b: Uint8Array): string {
  return "0x" + Array.from(b, (x) => x.toString(16).padStart(2, "0")).join("");
}

export function fromHex(h: string): Uint8Array {
  const s = h.startsWith("0x") ? h.slice(2) : h;
  if (s.length % 2 !== 0 || /[^0-9a-fA-F]/.test(s)) throw new Error(`bad hex: ${h}`);
  const out = new Uint8Array(s.length / 2);
  for (let i = 0; i < out.length; i++) out[i] = parseInt(s.slice(2 * i, 2 * i + 2), 16);
  return out;
}

export function u256(n: bigint): Uint8Array {
  if (n < 0n || n >= 1n << 256n) throw new Error(`uint256 out of range: ${n}`);
  return fromHex(n.toString(16).padStart(64, "0"));
}

const word = (b: Uint8Array): Uint8Array => concat(new Uint8Array(32 - b.length), b);

// ---------------------------------------------------------------------------------------------------- EIP-712
const isStruct = (t: string): boolean => Object.prototype.hasOwnProperty.call(STRUCTS, t);
const base = (t: string): string => (t.endsWith("[]") ? t.slice(0, -2) : t);

function structString(name: string): string {
  return `${name}(` + STRUCTS[name].fields.map(([t, n]) => `${t} ${n}`).join(",") + ")";
}

function deps(name: string): string[] {
  const seen = new Set<string>();
  const walk = (n: string): void => {
    for (const [t] of STRUCTS[n].fields) {
      const b = base(t);
      if (isStruct(b) && !seen.has(b) && b !== name) {
        seen.add(b);
        walk(b);
      }
    }
  };
  walk(name);
  return [...seen].sort();
}

export function encodeType(name: string): string {
  return structString(name) + deps(name).map(structString).join("");
}

export const typeHash = (name: string): Uint8Array => keccak256(utf8(encodeType(name)));

function encodeAtomic(t: string, v: Value): Uint8Array {
  if (t === "address") {
    const b = fromHex(v as string);
    if (b.length !== 20) throw new Error(`address length: ${v}`);
    return word(b);
  }
  if (t === "bool") return u256(v ? 1n : 0n);
  if (t.startsWith("bytes")) {
    const n = parseInt(t.slice(5), 10);
    const b = fromHex(v as string);
    if (b.length !== n) throw new Error(`${t} length: ${v}`);
    return concat(b, new Uint8Array(32 - n));
  }
  if (t.startsWith("uint")) {
    const bits = BigInt(parseInt(t.slice(4), 10));
    const n = BigInt(v as string | number | bigint);
    if (n < 0n || n >= 1n << bits) throw new Error(`${t} out of range: ${v}`);
    return u256(n);
  }
  throw new Error(`unsupported type ${t}`);
}

function encodeValue(t: string, v: Value): Uint8Array {
  if (t.endsWith("[]")) return keccak256(concat(...(v as Value[]).map((x) => encodeValue(t.slice(0, -2), x))));
  if (isStruct(t)) return hashStruct(t, v as { [k: string]: Value });
  return encodeAtomic(t, v);
}

export function hashStruct(name: string, value: { [k: string]: Value }): Uint8Array {
  const def = STRUCTS[name];
  const have = Object.keys(value).sort().join(",");
  const want = def.fields.map(([, n]) => n).sort().join(",");
  if (have !== want) throw new Error(`${name}: fields ${have} != ${want}`);
  // every array that is hashed is bounded (the generator refuses an unbounded array), so hashing is O(bound)
  for (const [f, bound] of Object.entries(def.boundedArrays)) {
    const len = (value[f] as Value[]).length;
    const max = (BOUNDS as Record<string, number>)[bound];
    if (len > max) throw new Error(`${name}.${f}: ${len} entries exceed ${bound} = ${max}`);
  }
  return keccak256(concat(typeHash(name), ...def.fields.map(([t, n]) => encodeValue(t, value[n]))));
}

export function domainSeparator(domain: keyof typeof DOMAINS, chainId: bigint, verifyingContract: string): Uint8Array {
  const d = DOMAINS[domain];
  return keccak256(
    concat(keccak256(utf8(DOMAIN_TYPE)), keccak256(utf8(d.name)), keccak256(utf8(d.version)), u256(chainId), encodeAtomic("address", verifyingContract)),
  );
}

export const digest = (separator: Uint8Array, structHash: Uint8Array): Uint8Array => keccak256(concat(Uint8Array.of(0x19, 0x01), separator, structHash));

export function tag(name: keyof typeof TAGS): Uint8Array {
  return keccak256(utf8(TAGS[name]));
}

// ---------------------------------------------------------------------------------------------------- Permit2 witness
export function witnessTypeString(): string {
  return `${PERMIT2_WITNESS.witness} ${PERMIT2_WITNESS.witnessField})` + structString(PERMIT2_WITNESS.witness) + PERMIT2_WITNESS.tokenPermissions;
}

export function permit2DomainSeparator(chainId: bigint, permit2: string): Uint8Array {
  return keccak256(concat(keccak256(utf8(PERMIT2_WITNESS.domainType)), keccak256(utf8(PERMIT2_WITNESS.domainName)), u256(chainId), encodeAtomic("address", permit2)));
}

export interface WitnessInput {
  token: string;
  amount: bigint;
  spender: string;
  nonce: bigint;
  deadline: bigint;
  witness: { [k: string]: Value };
  extra?: Array<{ token: string; amount: bigint }>;
}

/** hashStruct of PermitWitnessTransferFrom (single) or PermitBatchWitnessTransferFrom (when `batch`), as Permit2's PermitHash computes it. */
export function permit2WitnessHash(input: WitnessInput, batch: boolean): { typeHash: Uint8Array; hash: Uint8Array } {
  const stub = batch ? PERMIT2_WITNESS.stubBatch : PERMIT2_WITNESS.stubSingle;
  const th = keccak256(utf8(stub + witnessTypeString()));
  const tpType = keccak256(utf8(PERMIT2_WITNESS.tokenPermissions));
  const tp = (token: string, amount: bigint): Uint8Array => keccak256(concat(tpType, encodeAtomic("address", token), u256(amount)));
  const permitted = batch ? keccak256(concat(tp(input.token, input.amount), ...(input.extra ?? []).map((e) => tp(e.token, e.amount)))) : tp(input.token, input.amount);
  const w = hashStruct(PERMIT2_WITNESS.witness, input.witness);
  return { typeHash: th, hash: keccak256(concat(th, permitted, encodeAtomic("address", input.spender), u256(input.nonce), u256(input.deadline), w)) };
}

// ---------------------------------------------------------------------------------------------------- migration snapshot
export interface SnapshotArgs {
  lineageId: string;
  predecessorId: string;
  generation: number | string | bigint;
  customer: string;
}

const fieldType = (struct: string, name: string): string => {
  const f = STRUCTS[struct].fields.find(([, n]) => n === name);
  if (f === undefined) throw new Error(`${struct}.${name}`);
  return f[0];
};

/** The words of termsSnapshotHash in the order of eip712/types.json snapshotEncoding.words (one 32-byte value each). */
export function snapshotWords(args: SnapshotArgs, terms: { [k: string]: Value }): Uint8Array[] {
  const tokens = terms.tokens as Array<{ [k: string]: Value }>;
  if (tokens.length > BOUNDS.MAX_TOKENS_PER_MANDATE) throw new Error("too many tokens");
  const digests: { [k: string]: Uint8Array } = {
    tokens: keccak256(concat(...tokens.map((x) => encodeAtomic("address", x.token)))),
    capTable: keccak256(concat(...tokens.map((x) => concat(...SNAPSHOT.tokenWords.map((f) => encodeAtomic(f === "token" ? "address" : "uint256", x[f])))))),
  };
  const argType: { [k: string]: string } = { lineageId: "bytes32", predecessorId: "bytes32", generation: "uint32", customer: "address" };
  return SNAPSHOT.words.map(([, src]) => {
    const [kind, field] = src.split(":");
    if (kind === "tag") return tag("SNAPSHOT_TAG" as keyof typeof TAGS);
    if (kind === "arg") return encodeAtomic(argType[field], (args as unknown as { [k: string]: Value })[field]);
    if (kind === "terms") return encodeAtomic(fieldType("MandateTerms", field), terms[field]);
    if (kind === "terms.fiat") return encodeAtomic(fieldType("FiatTerms", field), (terms.fiat as { [k: string]: Value })[field]);
    return digests[field];
  });
}

export const snapshotHash = (args: SnapshotArgs, terms: { [k: string]: Value }): Uint8Array => keccak256(concat(...snapshotWords(args, terms)));
