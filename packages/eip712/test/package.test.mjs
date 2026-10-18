// SPDX-License-Identifier: Apache-2.0
// Tests the BUILT package (dist/) against the golden vectors that Python wrote and that Solidity reproduces, and runs the original TypeScript test too.
import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const pkgDir = new URL("../", import.meta.url);
execFileSync(process.execPath, [fileURLToPath(new URL("scripts/build.mjs", pkgDir))], { stdio: "pipe" });
const lib = await import(new URL("dist/index.js", pkgDir));
const golden = JSON.parse(readFileSync(new URL("dist/data/golden-vectors.json", pkgDir), "utf8"));

test("the built package exports the encoder and the generated types, and the import specifiers are plain .js", () => {
  for (const name of ["keccak256", "hashStruct", "typeHash", "encodeType", "domainSeparator", "digest", "tag", "permit2WitnessHash", "snapshotHash", "witnessTypeString"]) {
    assert.equal(typeof lib[name], "function", name);
  }
  assert.equal(lib.types.STATUS, "PROPOSED");
  for (const f of ["encoder.js", "types.generated.js", "index.js"]) assert.ok(!/\.ts["']/.test(readFileSync(new URL(`dist/${f}`, pkgDir), "utf8")), f);
});

test("Keccak-256 known answers", () => {
  assert.equal(lib.hex(lib.keccak256(new Uint8Array())), "0xc5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470");
  assert.equal(lib.hex(lib.keccak256(lib.utf8("abc"))), "0x4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45");
  assert.equal(lib.hex(lib.keccak256(lib.utf8("transfer(address,uint256)"))).slice(0, 10), "0xa9059cbb");
});

test("every domain separator, type string, type hash, struct hash and digest equals the golden vector", () => {
  const chainId = BigInt(golden.chainId);
  for (const [name, d] of Object.entries(golden.domains)) {
    assert.equal(lib.hex(lib.domainSeparator(name, chainId, d.verifyingContract)), d.separator, `domain ${name}`);
  }
  let n = 0;
  for (const [name, g] of Object.entries(golden.structs)) {
    assert.equal(lib.encodeType(name), g.encodeType, `${name} encodeType`);
    assert.equal(lib.hex(lib.typeHash(name)), g.typeHash, `${name} typeHash`);
    assert.equal(lib.types.TYPEHASHES[name], g.typeHash, `${name} generated constant`);
    assert.equal(lib.hex(lib.hashStruct(name, g.value)), g.hashStruct, `${name} hashStruct`);
    if (g.digest !== undefined) {
      const d = golden.domains[g.domain];
      assert.equal(lib.hex(lib.digest(lib.domainSeparator(g.domain, chainId, d.verifyingContract), lib.hashStruct(name, g.value))), g.digest, `${name} digest`);
    }
    n += 1;
  }
  assert.ok(n >= 14, `expected at least 14 structs, saw ${n}`);
});

test("the hashed tags and the bounds are those of the single source", () => {
  const types = JSON.parse(readFileSync(new URL("dist/data/types.json", pkgDir), "utf8"));
  assert.deepEqual({ ...lib.types.TAGS }, types.tags);
  assert.deepEqual({ ...lib.types.BOUNDS }, Object.fromEntries(Object.entries(types.bounds).map(([k, v]) => [k, v.value])));
  assert.equal(lib.types.DOMAINS.mandates.name, types.domains.mandates.name);
});

test("an array above its bound and a missing field are refused", () => {
  const terms = golden.structs.MandateTerms.value;
  const tooMany = Array.from({ length: lib.types.BOUNDS.MAX_TOKENS_PER_MANDATE + 1 }, () => terms.tokens[0]);
  assert.throws(() => lib.hashStruct("MandateTerms", { ...terms, tokens: tooMany }));
  const { [Object.keys(golden.structs.RevokeMandate.value)[0]]: _omitted, ...rest } = golden.structs.RevokeMandate.value;
  assert.throws(() => lib.hashStruct("RevokeMandate", rest));
});

test("the wallet payloads ship with the package and are valid JSON", () => {
  assert.ok(existsSync(new URL("dist/data/typed-data/RevokeMandate.json", pkgDir)));
  const payload = JSON.parse(readFileSync(new URL("dist/data/typed-data/RevokeMandate.json", pkgDir), "utf8"));
  assert.equal(payload.primaryType, "RevokeMandate");
});

test("the original TypeScript test of the specification still passes on the same sources", () => {
  const out = execFileSync(process.execPath, ["--experimental-strip-types", "--no-warnings", fileURLToPath(new URL("../../spec/eip712/test-eip712.ts", pkgDir))], { encoding: "utf8" });
  assert.match(out, /checks passed/);
});
