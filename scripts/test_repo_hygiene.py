#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Tests of scripts/repo_hygiene.py: the checker must FAIL on what it exists to catch (a checker that has never failed proves nothing).

    python -I scripts/test_repo_hygiene.py
"""
import importlib.util
import pathlib
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent


def load():
    spec = importlib.util.spec_from_file_location("repo_hygiene", HERE / "repo_hygiene.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Case(unittest.TestCase):
    def setUp(self):
        self.mod = load()
        self.tmp = tempfile.TemporaryDirectory()
        self.mod.ROOT = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, rel, text="", binary=None):
        p = self.mod.ROOT / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if binary is not None:
            p.write_bytes(binary)
        else:
            p.write_text(text, encoding="utf-8")
        return rel

    def run_check(self, name, files):
        res = self.mod.Result()
        getattr(self.mod, name)(files, res)
        return res.rows

    def levels(self, rows):
        return {r["level"] for r in rows}

    # ---- secrets
    def test_secrets_are_found(self):
        samples = {
            "key.txt": "-----BEGIN " + "RSA PRIVATE KEY-----\nabc\n",
            "gh.md": "token ghp_" + "a" * 36,
            "aws.py": "k = 'AKIA" + "A" * 16 + "'",
            "stripe.json": '{"k": "sk_live_' + "a" * 24 + '"}',
            "priv.js": "const PRIVATE_KEY = '0x" + "ab" * 32 + "';",
            "rpc.js": "const u = 'https://mainnet.infura.io/v3/" + "a" * 32 + "';",
            "gen.py": "api_key = '" + "x" * 24 + "'",
        }
        for rel, text in samples.items():
            self.put(rel, text)
            self.assertEqual(self.levels(self.run_check("check_secrets", [rel])), {"FAIL"}, rel)

    def test_clean_files_and_marked_dummies_pass(self):
        self.put("a.py", "x = 1\n")
        self.put("typed.json", '{"token": "0x' + "55" * 20 + '"}')
        self.put("t.mjs", "const API_KEY = 'dummy_value_1234567890'; // hygiene: allow-secret (a dummy value)\n")
        for rel in ("a.py", "typed.json", "t.mjs"):
            self.assertEqual(self.levels(self.run_check("check_secrets", [rel])), {"PASS"}, rel)

    def test_an_unmarked_dummy_fails(self):
        self.put("t.mjs", "const API_KEY = '" + "dummy_value_1234567890" + "';\n")  # built in pieces so this file does not trip the scan it tests
        self.assertEqual(self.levels(self.run_check("check_secrets", ["t.mjs"])), {"FAIL"})

    # ---- encoding
    def test_utf16_bom_and_invalid_utf8_files_are_refused(self):
        self.put("README.md", binary="# PayTrue\n".encode("utf-16"))  # what `echo "# PayTrue" > README.md` writes in Windows PowerShell 5
        self.put("bom.md", binary=b"\xef\xbb\xbf# x\n")
        self.put("nul.txt", binary=b"a\x00b\n")
        self.put("latin1.md", binary="café\n".encode("latin-1"))
        for rel in ("README.md", "bom.md", "nul.txt", "latin1.md"):
            self.assertEqual(self.levels(self.run_check("check_encoding", [rel])), {"FAIL"}, rel)

    def test_utf8_files_and_listed_binaries_pass(self):
        self.put("ok.md", "# café · ok\n")
        self.put("a.json.gz", binary=b"\x1f\x8b\x08\x00binary")
        for rel in ("ok.md", "a.json.gz"):
            self.assertEqual(self.levels(self.run_check("check_encoding", [rel])), {"PASS"}, rel)

    def test_allow_listed_upstream_paths_are_skipped(self):
        up = self.mod.CONFIG["secretAllowPaths"][0]
        self.put(up + "StdChains.sol", "string x = 'https://sepolia.infura.io/v3/" + "a" * 32 + "';")
        self.assertEqual(self.levels(self.run_check("check_secrets", [up + "StdChains.sol"])), {"PASS"})

    # ---- spdx
    def test_spdx_rules(self):
        self.put("contracts/src/A.sol", "// SPDX-License-Identifier: Apache-2.0\npragma solidity 0.8.24;\n")
        self.put("contracts/src/B.sol", "// SPDX-License-Identifier: UNLICENSED\npragma solidity 0.8.24;\n")
        self.put("contracts/src/C.sol", "pragma solidity 0.8.24;\n")
        self.put("contracts/src/D.sol", "// SPDX-License-Identifier: AGPL-3.0-only\npragma solidity 0.8.24;\n")
        third = self.mod.CONFIG["thirdPartySourcePrefixes"][0]
        self.put(third + "E.sol", "// SPDX-License-Identifier: MIT OR Apache-2.0\n")
        self.put(third + "F.sol", "// SPDX-License-Identifier: GPL-3.0-or-later\n")
        self.assertEqual(self.levels(self.run_check("check_spdx", ["contracts/src/A.sol", third + "E.sol"])), {"PASS"})
        for rel in ("contracts/src/B.sol", "contracts/src/C.sol", "contracts/src/D.sol", third + "F.sol"):
            self.assertEqual(self.levels(self.run_check("check_spdx", [rel])), {"FAIL"}, rel)

    # ---- size, forbidden, vendored
    def test_size_limits(self):
        limit = self.mod.CONFIG["maxFileMiB"] * 1024 * 1024
        warn = self.mod.CONFIG["warnFileMiB"] * 1024 * 1024
        self.put("small.bin", binary=b"x" * 10)
        self.put("warn.bin", binary=b"x" * warn)
        self.put("huge.bin", binary=b"x" * limit)
        self.assertEqual(self.levels(self.run_check("check_size", ["small.bin"])), {"PASS"})
        self.assertIn("WARN", self.levels(self.run_check("check_size", ["warn.bin"])))
        self.assertIn("FAIL", self.levels(self.run_check("check_size", ["huge.bin"])))

    def test_forbidden_files(self):
        for rel in ("a/key.pem", "id_rsa", ".env", ".env.production", "tool.exe", "dump.zip", "wallet.keystore", "spec/evidence/wallet-lab/EVL-01/screen.png"):
            self.put(rel, "x")
            self.assertEqual(self.levels(self.run_check("check_forbidden", [rel])), {"FAIL"}, rel)
        self.put(".env.example", "# nothing secret\n")
        self.put("spec/evidence/wallet-lab/EVL-01/run-1.json", "{}")
        self.assertEqual(self.levels(self.run_check("check_forbidden", [".env.example", "spec/evidence/wallet-lab/EVL-01/run-1.json"])), {"PASS"})

    def test_vendored_and_build_output_are_refused(self):
        for rel in ("spec/toolchain/bin/forge.exe", "spec/toolchain/permit2-build/permit2/src/Permit2.sol", "contracts/out/A.json", "spec/toolchain/isolated/run/x"):
            self.assertEqual(self.levels(self.run_check("check_vendored", [rel])), {"FAIL"}, rel)
        self.assertEqual(self.levels(self.run_check("check_vendored", ["contracts/src/A.sol"])), {"PASS"})

    def test_a_hosted_domain_in_code_is_refused_but_docs_may_name_it(self):
        hosted = "paytrue" + ".me"  # built in pieces so this file does not trip the scan it tests
        self.put("packages/x/index.js", "const base = 'https://api." + hosted + "/v1';\n")
        self.put("examples/y.mjs", "fetch('https://paytrue" + ".io')\n")
        self.put("docs/cloud.md", "PayTrue Cloud might live at " + hosted + " one day\n")
        self.assertEqual(self.levels(self.run_check("check_hosts", ["packages/x/index.js"])), {"FAIL"})
        self.assertEqual(self.levels(self.run_check("check_hosts", ["examples/y.mjs"])), {"FAIL"})
        self.assertEqual(self.levels(self.run_check("check_hosts", ["docs/cloud.md"])), {"PASS"})

    def test_a_package_with_a_dependency_or_a_wrong_license_is_refused(self):
        import json
        base = {"name": "@x/y", "license": "Apache-2.0", "private": True, "description": "d", "repository": {}, "files": [], "exports": {}, "engines": {}}
        res = self.mod.Result()
        self.put("packages/ok/package.json", json.dumps(base))
        self.mod.check_packages(res)
        self.assertEqual(self.levels(res.rows), {"PASS"})
        for patch in ({"dependencies": {"left-pad": "1"}}, {"license": "MIT"}, {"private": False}):
            self.put("packages/ok/package.json", json.dumps({**base, **patch}))
            res = self.mod.Result()
            self.mod.check_packages(res)
            self.assertEqual(self.levels(res.rows), {"FAIL"}, patch)

    def test_the_protected_identifiers_check_fails_when_one_is_renamed(self):
        import shutil
        self.put("spec/tools/placeholder.txt", "")
        shutil.copy(HERE.parent / "spec" / "tools" / "eip712_vectors.py", self.mod.ROOT / "spec" / "tools" / "eip712_vectors.py")  # the check hashes with the repository's own Keccak
        for item in self.mod.CONFIG["protectedIdentifiers"]:
            for rel in item["mustAppearIn"]:
                self.put(rel, item["string"] + "\n")
        res = self.mod.Result()
        self.mod.check_protected(res)
        # every string appears in every file only because every file contains this one string; others are missing, so it must fail
        self.assertIn("FAIL", self.levels(res.rows))
        # now a complete tree: every file holds every string
        everything = "\n".join(i["string"] for i in self.mod.CONFIG["protectedIdentifiers"])
        for item in self.mod.CONFIG["protectedIdentifiers"]:
            for rel in item["mustAppearIn"]:
                self.put(rel, everything)
        res = self.mod.Result()
        self.mod.check_protected(res)
        self.assertEqual(self.levels(res.rows), {"PASS"})
        # rename one (what a blind find-and-replace does)
        victim = self.mod.CONFIG["protectedIdentifiers"][0]
        for rel in victim["mustAppearIn"]:
            self.put(rel, everything.replace(victim["string"], victim["string"].replace("FastPay", "PayTrue").replace("fastpay", "paytrue")))
        res = self.mod.Result()
        self.mod.check_protected(res)
        self.assertEqual(self.levels(res.rows), {"FAIL"})


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0], "-v"])
