// SPDX-License-Identifier: Apache-2.0
// Builds the @paytrue/eip712 package from its single source, spec/eip712 (types.json and the generated TypeScript). Nothing is copied by hand and nothing is
// committed: dist/ is ignored by Git and is recreated here (`npm run build`, and automatically before `npm pack`).
//
// Needs Node 22.13 or later (it uses node:module's stripTypeScriptTypes, so the build has no dependency on the TypeScript compiler). The built package runs on Node 18+.
import { cpSync, mkdirSync, readFileSync, rmSync, writeFileSync, existsSync } from "node:fs";
import { stripTypeScriptTypes } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const pkg = join(here, "..");
const spec = join(pkg, "..", "..", "spec", "eip712");
const dist = join(pkg, "dist");

if (typeof stripTypeScriptTypes !== "function") {
  console.error("This build needs Node 22.13 or later (node:module.stripTypeScriptTypes).");
  process.exit(1);
}
if (!existsSync(join(spec, "types.json"))) {
  console.error(`source not found: ${spec}`);
  process.exit(1);
}

rmSync(dist, { recursive: true, force: true });
mkdirSync(join(dist, "data"), { recursive: true });

const sources = [
  ["fastpay-types.generated.ts", "types.generated.js"],
  ["fastpay-eip712.ts", "encoder.js"],
];
const rename = new Map([
  ["./fastpay-types.generated.ts", "./types.generated.js"],
  ["./fastpay-eip712.ts", "./encoder.js"],
]);
for (const [from, to] of sources) {
  let code = readFileSync(join(spec, from), "utf8");
  code = stripTypeScriptTypes(code, { mode: "strip" });
  for (const [a, b] of rename) code = code.replaceAll(`"${a}"`, `"${b}"`);
  if (/\.ts["']/.test(code)) throw new Error(`${to}: an import still names a .ts file`);
  writeFileSync(join(dist, to), `// SPDX-License-Identifier: Apache-2.0\n// BUILT by packages/eip712/scripts/build.mjs from spec/eip712/${from}; do not edit.\n${code}`);
}
writeFileSync(join(dist, "index.js"), '// SPDX-License-Identifier: Apache-2.0\nexport * from "./encoder.js";\nexport * as types from "./types.generated.js";\n');

// the data files the encoder is specified by
cpSync(join(spec, "types.json"), join(dist, "data", "types.json"));
cpSync(join(spec, "golden-vectors.json"), join(dist, "data", "golden-vectors.json"));
cpSync(join(spec, "typed-data"), join(dist, "data", "typed-data"), { recursive: true });
cpSync(join(pkg, "src", "index.d.ts"), join(dist, "index.d.ts"));
console.log(`built ${dist}`);
