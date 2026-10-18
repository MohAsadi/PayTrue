# Getting started

Ten minutes, no accounts, no network beyond cloning the repository. You will run the package tests, an end-to-end example and a local chain with the PayTrue contracts deployed.

## What you need

| Tool | Version | For |
|---|---|---|
| Git | any recent | cloning |
| Node.js | 22.13 or later (18 or later is enough for everything except building `@paytrue/eip712`) | packages, examples |
| Python | 3.10 or later (3.12 is what the checks were run with) | the specification tools and the devnet |
| Docker with Compose | optional | the compose quickstart |

```bash
git clone https://github.com/MohAsadi/PayTrue.git
cd PayTrue
```

## 1. The packages and an example (offline)

```bash
node --test "packages/config/test/*.test.mjs"
node --test "packages/sdk/test/*.test.mjs"
node --test "packages/eip712/test/*.test.mjs"      # builds the package first; needs Node 22.13+
node --test "packages/devserver/test/*.test.mjs"
node examples/headless-node/index.mjs
```

The example starts the **development stub** (in memory, no wallet, no chain), creates a checkout session through the SDK, receives signed webhooks, and fulfils the
order once, on `completed`. It is the shortest way to see the API and the webhook rules working. [Headless use](headless.md) explains each step.

## 2. A local chain with the contracts deployed

The contracts are built and tested with a pinned toolchain (Foundry v1.8.5, solc 0.8.24), fetched and verified by SHA-256:

```bash
python -I spec/toolchain/fetch_toolchain.py          # downloads from github.com and binaries.soliditylang.org, verifies every hash; about 150 MB
python -I scripts/devnet.py --once                   # starts anvil, deploys Permit2 and the PayTrue contracts, writes deployments/local-31337.json
```

Without `--once` the chain keeps running (Ctrl+C stops it). The manifest lists the addresses; `scripts/validate_deployment.py` checks it. All roles are held by
anvil's unlocked accounts: this is a throwaway chain, not a template for a real deployment ([contract deployments](contracts-deployments.md)).

To run the contract tests:

```bash
python -I spec/toolchain/forge.py --project contracts test
```

## 3. Docker Compose (optional, unverified)

```bash
docker compose -f deploy/compose/compose.yaml up --build
```

This builds two local images (a devnet and the development stub) and publishes them on `127.0.0.1` only. The compose file is validated with `docker compose config`; the
images have not been built by this repository's checks. If a host port is taken, set `PAYTRUE_DEVSERVER_PORT` or `PAYTRUE_DEVNET_PORT`.

## 4. The checks of the specification

```bash
python -I spec/tools/check_all.py                    # 21 consistency checks of the specification, the contracts and their evidence
python -I scripts/repo_hygiene.py --history          # file sizes, secrets, licenses, vendored trees, protected identifiers
python -I scripts/check_docs.py                      # every relative link in the public documents resolves
```

## Where next

- Use the API from your own server: [headless use](headless.md).
- Run PayTrue under your own domain: [domains](domains.md).
- Deploy your own contracts: [contract deployments](contracts-deployments.md).
- Understand what is and is not built: [architecture](architecture.md), [open-source readiness](open-source-readiness.md).

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `listen EACCES ... 8080` | Some systems (Windows with Hyper-V or Docker) reserve ranges of ports. Set `PAYTRUE_LISTEN_PORT` and `PAYTRUE_PUBLIC_ORIGIN` to a free port |
| `toolchain not fetched` | Run `python -I spec/toolchain/fetch_toolchain.py` first |
| `PAYTRUE_ENV=production` refuses to start the stub | By design: the stub is not a payment server |
| The EIP-712 package test fails on build | The build needs Node 22.13 or later (`module.stripTypeScriptTypes`) |
