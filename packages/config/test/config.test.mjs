// SPDX-License-Identifier: Apache-2.0
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  ConfigError, ENV_SCHEMA, apiUrl, checkoutSessionUrl, cookieAttributes, joinPath, loadConfig, normalizeBasePath, parseOrigin, routeOf,
} from "../src/index.js";
import { renderEnvExample } from "../scripts/generate-env-example.mjs";

const SESSION = "cs_abcdefghijklmnopqrstuvwxyz";
const PROD = {
  PAYTRUE_ENV: "production",
  PAYTRUE_PUBLIC_ORIGIN: "https://pay.example.com",
  PAYTRUE_CHAIN_IDS: "8453",
  PAYTRUE_RPC_URLS_8453: "https://rpc-a.example.org,https://rpc-b.example.net",
  PAYTRUE_DEPLOYMENT_FILE: "deployments/sovereign-8453.json",
};

test("development defaults work with an empty environment and point at nothing hosted", () => {
  const cfg = loadConfig({});
  assert.equal(cfg.env, "development");
  assert.equal(cfg.publicOrigin, "http://localhost:8080");
  assert.equal(cfg.basePath, "/");
  assert.equal(checkoutSessionUrl(cfg, SESSION), `http://localhost:8080/c/${SESSION}`);
  assert.equal(apiUrl(cfg, "checkout/sessions"), "http://localhost:8080/v1/checkout/sessions");
  assert.deepEqual(cfg.chains.map((c) => c.id), [31337]);
  assert.equal(cfg.cloud.enabled, false);
  assert.equal(cfg.cloud.baseUrl, undefined);
  assert.equal(cfg.cspFrameAncestors, "'none'");
  assert.deepEqual(cfg.session, { minSeconds: 600, defaultSeconds: 1800, maxSeconds: 86400 });
});

test("a path on an existing domain, a subdomain and a dedicated host build the right URLs", () => {
  const path = loadConfig({ ...PROD, PAYTRUE_BASE_PATH: "paytrue/" });
  assert.equal(path.basePath, "/paytrue");
  assert.equal(checkoutSessionUrl(path, SESSION), `https://pay.example.com/paytrue/c/${SESSION}`);
  assert.equal(apiUrl(path, "/checkout/sessions"), "https://pay.example.com/paytrue/v1/checkout/sessions");

  const sub = loadConfig({ ...PROD, PAYTRUE_PUBLIC_ORIGIN: "https://checkout.example.com" });
  assert.equal(checkoutSessionUrl(sub, SESSION), `https://checkout.example.com/c/${SESSION}`);

  const split = loadConfig({
    ...PROD,
    PAYTRUE_PUBLIC_ORIGIN: "https://shop.example.com",
    PAYTRUE_BASE_PATH: "/paytrue",
    PAYTRUE_CHECKOUT_ORIGIN: "https://checkout.example.com",
    PAYTRUE_CHECKOUT_BASE_PATH: "/",
    PAYTRUE_API_ORIGIN: "https://api.example.com",
    PAYTRUE_API_BASE_PATH: "/payments",
  });
  assert.equal(checkoutSessionUrl(split, SESSION), `https://checkout.example.com/c/${SESSION}`);
  assert.equal(apiUrl(split, "checkout/sessions"), "https://api.example.com/payments/v1/checkout/sessions");
  assert.equal(split.cookie.path, "/");
});

test("base paths are normalised and unsafe ones are refused", () => {
  assert.equal(normalizeBasePath(""), "/");
  assert.equal(normalizeBasePath("/"), "/");
  assert.equal(normalizeBasePath("pay"), "/pay");
  assert.equal(normalizeBasePath("/a/b///"), "/a/b");
  for (const bad of ["/a//b", "/a/../b", "/a/./b", "/a b", "/a?x=1", "/a#f", "/a\\b"]) assert.throws(() => normalizeBasePath(bad), bad);
  assert.equal(joinPath("/a/", "/b", "c/"), "/a/b/c");
  assert.equal(joinPath("/", ""), "/");
});

test("an origin has no path, query, fragment or credentials", () => {
  assert.equal(parseOrigin("https://Example.com:8443"), "https://example.com:8443");
  for (const bad of ["https://example.com/paytrue", "https://example.com?x", "https://u:p@example.com", "ftp://example.com", "example.com"]) assert.throws(() => parseOrigin(bad), bad);
});

test("routeOf maps a request path to the route inside PayTrue, with or without a stripping proxy", () => {
  const kept = loadConfig({ ...PROD, PAYTRUE_BASE_PATH: "/paytrue" });
  assert.equal(routeOf(kept, "/paytrue/v1/checkout/sessions"), "/v1/checkout/sessions");
  assert.equal(routeOf(kept, "/paytrue"), "/");
  assert.equal(routeOf(kept, "/elsewhere/v1"), null);
  assert.equal(routeOf(kept, "/paytrueX/v1"), null);
  const stripped = loadConfig({ ...PROD, PAYTRUE_BASE_PATH: "/paytrue", PAYTRUE_PROXY_STRIPS_BASE_PATH: "true" });
  assert.equal(routeOf(stripped, "/v1/checkout/sessions"), "/v1/checkout/sessions");
});

test("production refuses http, local addresses, missing origin, and fewer than two RPC hosts", () => {
  assert.doesNotThrow(() => loadConfig(PROD));
  const expectProblem = (env, fragment) => {
    try {
      loadConfig(env);
      assert.fail("expected a ConfigError");
    } catch (e) {
      assert.ok(e instanceof ConfigError, String(e));
      assert.ok(e.problems.some((p) => p.includes(fragment)), `${fragment} not in ${JSON.stringify(e.problems)}`);
    }
  };
  expectProblem({ ...PROD, PAYTRUE_PUBLIC_ORIGIN: undefined }, "PAYTRUE_PUBLIC_ORIGIN is required");
  expectProblem({ ...PROD, PAYTRUE_PUBLIC_ORIGIN: "http://pay.example.com" }, "must be https");
  expectProblem({ ...PROD, PAYTRUE_PUBLIC_ORIGIN: "https://localhost" }, "local address");
  expectProblem({ ...PROD, PAYTRUE_RPC_URLS_8453: "https://rpc-a.example.org" }, "at least two RPC URLs");
  expectProblem({ ...PROD, PAYTRUE_RPC_URLS_8453: "https://rpc-a.example.org/a,https://rpc-a.example.org/b" }, "distinct hosts");
  expectProblem({ ...PROD, PAYTRUE_RPC_URLS_8453: undefined }, "PAYTRUE_RPC_URLS_8453 is required");
  expectProblem({ ...PROD, PAYTRUE_CHAIN_IDS: undefined }, "PAYTRUE_CHAIN_IDS is required");
  expectProblem({ ...PROD, PAYTRUE_DEPLOYMENT_FILE: undefined }, "PAYTRUE_DEPLOYMENT_FILE is required");
  expectProblem({ PAYTRUE_ENV: "staging" }, "PAYTRUE_ENV");
});

test("all problems are reported together", () => {
  try {
    loadConfig({ PAYTRUE_ENV: "production" });
    assert.fail("expected a ConfigError");
  } catch (e) {
    assert.ok(e.problems.length >= 3, JSON.stringify(e.problems));
  }
});

test("Cloud is off by default, has no default URL, and needs an explicit one when enabled", () => {
  assert.equal(loadConfig(PROD).cloud.enabled, false);
  assert.throws(() => loadConfig({ ...PROD, PAYTRUE_CLOUD_ENABLED: "true" }), /PAYTRUE_CLOUD_BASE_URL is required/);
  const on = loadConfig({ ...PROD, PAYTRUE_CLOUD_ENABLED: "true", PAYTRUE_CLOUD_BASE_URL: "https://cloud.example.net/" });
  assert.equal(on.cloud.baseUrl, "https://cloud.example.net");
  const stray = loadConfig({ ...PROD, PAYTRUE_CLOUD_BASE_URL: "https://cloud.example.net" });
  assert.equal(stray.cloud.enabled, false);
  assert.ok(stray.warnings.some((w) => w.includes("Cloud stays off")));
});

test("frame ancestors: empty means none, wildcards are refused, origins are normalised", () => {
  assert.equal(loadConfig(PROD).cspFrameAncestors, "'none'");
  const cfg = loadConfig({ ...PROD, PAYTRUE_ALLOWED_FRAME_ANCESTORS: "https://shop.example.com, https://www.example.com", PAYTRUE_COOKIE_SAMESITE: "lax" });
  assert.deepEqual([...cfg.frameAncestors], ["https://shop.example.com", "https://www.example.com"]);
  assert.equal(cfg.cspFrameAncestors, "https://shop.example.com https://www.example.com");
  assert.throws(() => loadConfig({ ...PROD, PAYTRUE_ALLOWED_FRAME_ANCESTORS: "*" }), /must not contain/);
  assert.throws(() => loadConfig({ ...PROD, PAYTRUE_ALLOWED_FRAME_ANCESTORS: "http://shop.example.com" }), /https in production/);
  const strict = loadConfig({ ...PROD, PAYTRUE_ALLOWED_FRAME_ANCESTORS: "https://shop.example.com" });
  assert.ok(strict.warnings.some((w) => w.includes("SameSite=strict")));
});

test("the cookie follows the checkout origin and its attributes are built from the configuration", () => {
  const cfg = loadConfig({ ...PROD, PAYTRUE_BASE_PATH: "/paytrue", PAYTRUE_COOKIE_DOMAIN: ".example.com" });
  assert.equal(cfg.cookie.domain, "example.com");
  assert.equal(cfg.cookie.path, "/paytrue");
  assert.equal(cookieAttributes(cfg, { maxAgeSeconds: 60 }), "HttpOnly; Path=/paytrue; SameSite=Strict; Secure; Domain=example.com; Max-Age=60");
  assert.throws(() => loadConfig({ ...PROD, PAYTRUE_COOKIE_DOMAIN: "other.org" }), /parent domain/);
  assert.throws(() => loadConfig({ PAYTRUE_COOKIE_SAMESITE: "none" }), /needs production/);
  assert.doesNotThrow(() => loadConfig({ ...PROD, PAYTRUE_COOKIE_SAMESITE: "none" }));
  assert.throws(() => loadConfig({ ...PROD, PAYTRUE_COOKIE_SAMESITE: "sideways" }), /strict, lax or none/);
});

test("session lifetimes are ordered and are integers", () => {
  assert.throws(() => loadConfig({ PAYTRUE_SESSION_LIFETIME_MIN_SECONDS: "2000" }), /MIN <= DEFAULT <= MAX/);
  assert.throws(() => loadConfig({ PAYTRUE_SESSION_LIFETIME_MAX_SECONDS: "1000" }), /MIN <= DEFAULT <= MAX/);
  assert.throws(() => loadConfig({ PAYTRUE_SESSION_LIFETIME_DEFAULT_SECONDS: "abc" }), /integer/);
  assert.equal(loadConfig({ PAYTRUE_SESSION_LIFETIME_DEFAULT_SECONDS: "900", PAYTRUE_SESSION_LIFETIME_MIN_SECONDS: "300" }).session.defaultSeconds, 900);
});

test("secrets are not serialised and are readable on demand only", () => {
  const cfg = loadConfig({ ...PROD, PAYTRUE_WEBHOOK_SECRET: "whsec_example_value", PAYTRUE_API_KEY: "key_example_value" }); // hygiene: allow-secret (dummy values)
  assert.equal(cfg.webhook.secretConfigured, true);
  assert.equal(cfg.secret("webhook"), "whsec_example_value");
  const json = JSON.stringify(cfg);
  assert.ok(!json.includes("whsec_example_value") && !json.includes("key_example_value"));
  assert.throws(() => cfg.secret("other"));
  assert.equal(Object.isFrozen(cfg), true);
});

test("session URLs require a session id and APIs need no scheme games", () => {
  const cfg = loadConfig({});
  assert.throws(() => checkoutSessionUrl(cfg, "x"), /session id/);
  assert.throws(() => checkoutSessionUrl(cfg, "cs_../../etc"), /session id/);
});

test(".env.example is exactly what the schema renders", () => {
  const file = readFileSync(new URL("../../../.env.example", import.meta.url), "utf8").replace(/\r\n/g, "\n");
  assert.equal(file, renderEnvExample());
});

test("docs/configuration.md is exactly what the schema renders", async () => {
  const { renderConfigDoc } = await import("../scripts/generate-config-doc.mjs");
  const file = readFileSync(new URL("../../../docs/configuration.md", import.meta.url), "utf8").replace(/\r\n/g, "\n");
  assert.equal(file, renderConfigDoc());
});

test("every runtime variable of the schema is read by the loader and no variable is listed twice", () => {
  const source = readFileSync(new URL("../src/index.js", import.meta.url), "utf8");
  const names = ENV_SCHEMA.map((v) => v.name);
  assert.equal(new Set(names).size, names.length);
  for (const v of ENV_SCHEMA.filter((x) => x.group === "runtime")) {
    const key = v.name.replace("<chainId>", "");
    assert.ok(source.includes(key), `${v.name} is in the schema but not read by the loader`);
  }
  for (const m of source.matchAll(/"(PAYTRUE_[A-Z_]+)"/g)) assert.ok(names.includes(m[1]) || names.some((n) => n.startsWith(m[1])), `${m[1]} is read but not in the schema`);
});

test("no source file of the package names a PayTrue-hosted service", () => {
  const dir = fileURLToPath(new URL("../src/", import.meta.url));
  for (const f of readdirSync(dir)) {
    if (!statSync(join(dir, f)).isFile()) continue;
    assert.ok(!/paytrue\.(me|com|io|app|dev|cloud)/i.test(readFileSync(join(dir, f), "utf8")), f);
  }
});
