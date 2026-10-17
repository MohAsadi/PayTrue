#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""A local PayTrue devnet: a pinned `anvil` chain, Permit2 at its canonical address, and the PayTrue contracts deployed by contracts/script/Deploy.s.sol.

    python -I scripts/devnet.py                  start the chain, deploy, write deployments/local-31337.json, keep running (Ctrl+C stops it)
    python -I scripts/devnet.py --once           deploy and exit (the chain stops with the script)
    python -I scripts/devnet.py --port 8546 --manifest deployments/local-31337.json

It uses only the pinned toolchain (spec/toolchain, fetched with `python -I spec/toolchain/fetch_toolchain.py`) and the evidence of the Permit2 rebuild.
It touches no network. The accounts are the unlocked accounts of anvil; no private key is read or written. The fee values below are DEVNET values: the fee
ceiling (PC-05) has no proposed value, and nothing here is a recommendation.
"""
import argparse
import datetime
import importlib.util
import json
import os
import pathlib
import platform
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
TC = ROOT / "spec" / "toolchain"
PROXY = "0x4e59b44847b379578588920ca78fbf26c0b4956c"
# the runtime code of the deterministic deployment proxy; its keccak256 is checked against the hash the Permit2 rebuild recorded for the real chains
PROXY_RUNTIME = "7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffe03601600081602082378035828234f58015156039578182fd5b8082525050506014600cf3"
CONTRACTS = ["RouterRegistry", "TokenPolicyRegistry", "SignerSetRegistry", "MerchantRegistry", "ExecutorRegistry", "FeeController", "UsageLedger",
             "SuccessorValidator", "MandateGateway", "MigrationQueue", "MandateManager", "PaymentRouter"]


def keccak(data: bytes) -> str:
    spec = importlib.util.spec_from_file_location("v", ROOT / "spec" / "tools" / "eip712_vectors.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return "0x" + mod.keccak256(data).hex()


def rpc(url, method, params=None):
    req = urllib.request.Request(url, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        out = json.loads(r.read())
    if "error" in out:
        raise RuntimeError(f"{method}: {out['error']}")
    return out["result"]


def wait_receipt(url, tx):
    for _ in range(100):
        r = rpc(url, "eth_getTransactionReceipt", [tx])
        if r:
            if r.get("status") != "0x1":
                raise RuntimeError(f"transaction {tx} failed")
            return r
        time.sleep(0.1)
    raise RuntimeError(f"no receipt for {tx}")


def stop(proc):
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--port", type=int, default=8545)
    ap.add_argument("--host", default="127.0.0.1", help="the interface anvil listens on; use 0.0.0.0 only inside a container whose published port is bound to 127.0.0.1")
    ap.add_argument("--chain-id", type=int, default=31337)
    ap.add_argument("--once", action="store_true", help="deploy, write the manifest and stop the chain")
    ap.add_argument("--manifest", default=None, help="where to write the manifest (default: deployments/local-<chain id>.json)")
    args = ap.parse_args()

    verify = subprocess.run([sys.executable, "-I", str(TC / "fetch_toolchain.py"), "--verify"], capture_output=True, text=True)
    if verify.returncode:
        sys.exit("the pinned toolchain is missing or does not verify: run  python -I spec/toolchain/fetch_toolchain.py\n" + verify.stdout + verify.stderr)
    win = platform.system().lower() == "windows"
    anvil = TC / "bin" / ("anvil.exe" if win else "anvil")
    url = f"http://127.0.0.1:{args.port}"
    log = tempfile.NamedTemporaryFile(prefix="paytrue-anvil-", suffix=".log", delete=False)
    proc = subprocess.Popen([str(anvil), "--host", args.host, "--port", str(args.port), "--chain-id", str(args.chain_id), "--silent"], stdout=log, stderr=subprocess.STDOUT)
    try:
        for _ in range(100):
            try:
                if int(rpc(url, "eth_chainId"), 16) == args.chain_id:
                    break
            except Exception:
                time.sleep(0.1)
        else:
            sys.exit(f"anvil did not answer on {url} (log: {log.name})")
        accounts = rpc(url, "eth_accounts")
        if len(accounts) < 5:
            sys.exit("anvil returned fewer than 5 accounts")
        deployer, governance, guardian, risk, fee_recipient = accounts[:5]

        # the deterministic deployment proxy, then Permit2 through it with the salt and creation code the rebuild recorded
        if rpc(url, "eth_getCode", [PROXY, "latest"]) in ("0x", "0x0"):
            if keccak(bytes.fromhex(PROXY_RUNTIME)) != json.loads((ROOT / "spec/evidence/permit2/rebuild.json").read_text())["deployerProxy"]["1"]["code"]["keccak256"]:
                sys.exit("the proxy runtime code does not match the recorded hash: refusing to install it")
            rpc(url, "anvil_setCode", [PROXY, "0x" + PROXY_RUNTIME])
        rebuild = json.loads((ROOT / "spec/evidence/permit2/rebuild.json").read_text(encoding="utf-8"))
        salt = rebuild["create2"]["salt"][2:]
        creation = (ROOT / "spec/evidence/permit2/permit2-creation-code.hex").read_text().strip().removeprefix("0x")
        permit2 = rebuild["create2"]["canonicalAddress"]
        if rpc(url, "eth_getCode", [permit2, "latest"]) in ("0x", "0x0"):
            tx = rpc(url, "eth_sendTransaction", [{"from": deployer, "to": PROXY, "data": "0x" + salt + creation, "gas": hex(12_000_000)}])
            wait_receipt(url, tx)
        code = rpc(url, "eth_getCode", [permit2, "latest"])
        if (len(code) - 2) // 2 != rebuild["runtimeCodeLength"]:
            sys.exit(f"Permit2 at {permit2} has {(len(code) - 2) // 2} bytes, expected {rebuild['runtimeCodeLength']}")
        print(f"Permit2 deployed at its canonical address {permit2} ({rebuild['runtimeCodeLength']} bytes of runtime code)")

        env = dict(os.environ, PAYTRUE_PERMIT2=permit2, PAYTRUE_GOVERNANCE=governance, PAYTRUE_GUARDIAN=guardian, PAYTRUE_RISK_AUTHORITY=risk,
                   PAYTRUE_MAX_QUOTE_TTL="300", PAYTRUE_MAX_BAND_WIDTH_BPS="500", PAYTRUE_QUOTE_SET_GRACE="300", PAYTRUE_FEE_CEILING_BPS="100",
                   PAYTRUE_FEE_BPS="50", PAYTRUE_FEE_RECIPIENT=fee_recipient)
        for k in [k for k in env if k.startswith("FASTPAY_")]:
            del env[k]
        cmd = [sys.executable, "-I", str(TC / "forge.py"), "--project", "contracts", "script", "script/Deploy.s.sol:Deploy", "--sig", "run()", "--rpc-url", url,
               "--broadcast", "--unlocked", "--sender", deployer]
        done = subprocess.run(cmd, env=env, capture_output=True, text=True, cwd=str(ROOT))
        if done.returncode:
            sys.exit("forge script failed:\n" + done.stdout[-3000:] + done.stderr[-3000:])
        broadcast = json.loads((ROOT / "contracts" / "broadcast" / "Deploy.s.sol" / str(args.chain_id) / "run-latest.json").read_text(encoding="utf-8"))
        found = {t["contractName"]: t["contractAddress"] for t in broadcast["transactions"] if t.get("transactionType") == "CREATE" and t.get("contractName") in CONTRACTS}
        missing = [c for c in CONTRACTS if c not in found]
        if missing:
            sys.exit(f"the deployment did not create: {missing}")

        manifest = {
            "schema": "paytrue.deployment/1",
            "kind": "sovereign",
            "label": f"local anvil devnet, chain {args.chain_id}",
            "chainId": args.chain_id,
            "deployedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "permit2": permit2,
            "contracts": {name: found[name] for name in CONTRACTS},
            "roles": {"deployer": deployer, "governance": governance, "guardian": guardian, "riskAuthority": risk, "feeRecipient": fee_recipient},
            "compiler": {"solc": "0.8.24", "evm": "cancun", "optimizerRuns": 200},
            "notes": "A throwaway local deployment: anvil's unlocked accounts hold every role, the fee values are devnet values (PC-05 has no proposed value) and nothing here is audited or approved.",
        }
        target = pathlib.Path(args.manifest) if args.manifest else ROOT / "deployments" / f"local-{args.chain_id}.json"
        if not target.is_absolute():
            target = ROOT / target
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        check = subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / "validate_deployment.py"), str(target)], capture_output=True, text=True)
        print(check.stdout.strip())
        if check.returncode:
            sys.exit("the manifest it wrote does not validate")
        print(f"MandateManager {found['MandateManager']}\nPaymentRouter  {found['PaymentRouter']}")
        print(f"manifest: {target}")
        print("for the configuration:\n  PAYTRUE_CHAIN_IDS=%d\n  PAYTRUE_RPC_URLS_%d=%s\n  PAYTRUE_DEPLOYMENT_FILE=%s" % (args.chain_id, args.chain_id, url, os.path.relpath(target, ROOT).replace(os.sep, "/")))
        if args.once:
            return 0
        print("devnet running; Ctrl+C stops it.")
        try:
            while proc.poll() is None:
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        return 0
    finally:
        stop(proc)
        log.close()
        try:
            os.unlink(log.name)
        except OSError:
            pass


if __name__ == "__main__":
    sys.exit(main())
