// SPDX-License-Identifier: Apache-2.0
// Writes (or checks) the configuration table of the root README.md from the schema of @paytrue/config, so the reference can never drift from the code.
// The table lives between two marker comments in README.md; nothing else in the README is touched.
//
//   node packages/config/scripts/generate-config-doc.mjs           write the table
//   node packages/config/scripts/generate-config-doc.mjs --check   exit 1 if the README differs
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { ENV_SCHEMA, GROUPS } from "../src/schema.js";

export const START = "<!-- config-reference:start -->";
export const END = "<!-- config-reference:end -->";

const cell = (s) => String(s ?? "").replaceAll("|", "\\|").replaceAll("\n", " ");

/** The Markdown between the markers: one collapsed section with one table per group. */
export function renderConfigBlock() {
  const out = [
    "<details>",
    "<summary>Every environment variable (generated from <code>packages/config/src/schema.js</code>; do not edit by hand)</summary>",
    "",
  ];
  for (const [group, title] of Object.entries(GROUPS)) {
    out.push(`#### ${title}`, "", "| Variable | Default | Required | Description |", "|---|---|---|---|");
    for (const v of ENV_SCHEMA.filter((x) => x.group === group)) {
      const name = `\`${v.name}\`${v.secret ? " (secret)" : ""}`;
      out.push(`| ${name} | ${cell(v.default ?? "none")} | ${cell(v.requiredWhen ?? "no")} | ${cell(v.description)} |`);
    }
    out.push("");
  }
  out.push("</details>");
  return out.join("\n");
}

/** README text with the block between the markers replaced; throws when a marker is missing. */
export function withConfigBlock(readme) {
  const text = readme.replace(/\r\n/g, "\n");
  const a = text.indexOf(START);
  const b = text.indexOf(END);
  if (a < 0 || b < a) throw new Error(`README.md needs the markers ${START} and ${END}, in that order`);
  return `${text.slice(0, a + START.length)}\n${renderConfigBlock()}\n${text.slice(b)}`;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const target = new URL("../../../README.md", import.meta.url);
  const current = readFileSync(target, "utf8").replace(/\r\n/g, "\n");
  const next = withConfigBlock(current);
  if (process.argv.includes("--check")) {
    if (current !== next) {
      console.error("The configuration table of README.md is not up to date: run `node packages/config/scripts/generate-config-doc.mjs`");
      process.exit(1);
    }
    console.log("The configuration table of README.md is up to date");
  } else {
    writeFileSync(target, next);
    console.log("wrote the configuration table of README.md");
  }
}
