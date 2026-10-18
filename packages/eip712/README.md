# @paytrue/eip712

The EIP-712 typed-data encoder of PayTrue: domain separators, type strings, type hashes, struct hashes, the Permit2 witness and the migration snapshot, with the type definitions, the golden
vectors and the wallet payloads. No dependencies (the Keccak-256 implementation is part of the encoder).

> **The type set is a proposal and is not frozen.** No wallet has signed any of these messages. Pre-alpha; not published to npm (`"private": true`).
> Do not rename the domain names or tags in the source to rebrand the project: [rename impact](../../docs/rename-impact.md).

This package is **generated from one source**: `spec/eip712/types.json`. `npm run build` copies the encoder and the generated types from `spec/eip712`, strips the TypeScript types with
Node's own `module.stripTypeScriptTypes` (so there is no compiler dependency), and writes `dist/`. Nothing in `dist/` is committed.

```js
import { hashStruct, domainSeparator, digest, hex, types } from "@paytrue/eip712";

const separator = domainSeparator("mandates", 8453n, "0x...");   // the verifying contract is your deployment's MandateManager
const structHash = hashStruct("RevokeMandate", { /* fields of types.STRUCTS.RevokeMandate */ });
console.log(hex(digest(separator, structHash)));
```

`@paytrue/eip712/types.json`, `/golden-vectors.json` and `/typed-data/*` expose the data files.

```bash
node scripts/build.mjs                 # needs Node 22.13+
node --test "test/*.test.mjs"          # runs the BUILT package against the golden vectors, and the original TypeScript test
```

The golden vectors were written by the Python implementation and are reproduced by the TypeScript and both Solidity implementations (`python -I spec/tools/eip712_crosscheck.py`).

License: Apache-2.0.
