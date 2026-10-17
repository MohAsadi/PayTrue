# Architecture

## What is in the repository

| Path | What it is | State |
|---|---|---|
| `contracts/` | The Solidity contracts (Foundry project): a mandate manager split into five contracts, a payment router, registries, and a deployment script. Tested against the reference model's vectors and against the real Permit2 on forks | Implemented, tested, **not audited**; the constants are proposals; protocol freeze is not approved |
| `packages/config` | `@paytrue/config`: reads and validates the `PAYTRUE_*` environment and derives URLs for any layout | Implemented, tested |
| `packages/sdk` | `@paytrue/sdk`: a client for the proposed checkout API, webhook verification, event ordering, experimental embedding helpers. No dependencies, no default host | Implemented, tested; targets a **proposed** API |
| `packages/eip712` | `@paytrue/eip712`: the EIP-712 encoder, built from `spec/eip712`. No dependencies | Implemented, tested against the golden vectors; the types are a proposal |
| `packages/devserver` | A **development stub** of the checkout API: in memory, no wallet, no chain. For examples, SDK tests and proxy layouts | Implemented, tested; **never a payment server** |
| `spec/` | The specification (documents 01 to 19), the Python tools that check it, the reference model, the recorded evidence, the pinned toolchain's lock | The source of truth. Draft |
| `deploy/` | Reverse-proxy layouts (Caddy, nginx), Dockerfiles and a compose quickstart | Written; proxies and images **not run** by this repository's checks |
| `deployments/` | The manifest format for contract deployments, and an example | Format validated by `scripts/validate_deployment.py` |
| `examples/` | A headless example and an experimental embedding example | Both run and were verified |
| `scripts/` | The local devnet, the hygiene checks, the documentation link check, the manifest validator | Implemented |
| `docs/` | This documentation | Written |

## What does **not** exist

There is no production checkout service, no wallet-connection layer, no orchestrator, no ledger, no risk engine and no user interface other than the development stub's
placeholder page. They are specified in `spec/` and in the proposed API and event catalogs (`spec/checkout/`). The SDK talks to that proposed API; the stub implements a small
part of it in memory so that the SDK, the examples and the reverse-proxy layouts can be exercised. **A real operator cannot yet host PayTrue's payment flow end to end**:
[self-hosting](self-hosting.md) says exactly what can be hosted today.

## The parts and how they depend on each other

```text
 your server ──SDK──▶ checkout API ──▶ checkout session ──▶ hosted checkout page ──▶ customer's wallet
 (merchant)           (proposed;          (specified)         (specified; the stub      │ typed-data signature
                       stubbed in memory)                      has a placeholder)       ▼
                                                                                  contracts (PaymentRouter, MandateManager, ...)
                                                                                   on a chain you chose, deployed by you
```

- **Non-custodial.** Funds move from the customer's wallet to the merchant's registered address in one transaction through the router, which holds no tokens.
  No PayTrue component holds a customer key, a seed phrase or customer funds (specification decisions CSD-01 and CSD-04).
- **No hard-coded PayTrue address.** No contract names an address of its own; every link is a constructor argument. No file of the code, the deployment files or the examples names a
  PayTrue-hosted domain (checked by `scripts/repo_hygiene.py`).
- **Permit2.** The contracts call the Permit2 of the chain through an interface. They do not import Permit2 source.

## Dependency direction inside the repository

| From | To | Note |
|---|---|---|
| `packages/*` | nothing | They have no runtime dependency at all. The development stub imports its sibling packages by relative path |
| `packages/eip712` | `spec/eip712` | The encoder is **generated** from `types.json` there; the package build copies and strips types, it does not fork the code |
| `contracts/` | `spec/foundry/lib/forge-std`, `spec/foundry/vectors`, `spec/eip712`, `spec/evidence/permit2` | A known limitation: the contracts' tests read vectors and the Permit2 fixture from `spec/`. Consuming `contracts/src` from another project needs only forge-std |
| `spec/tools` | `contracts/`, `spec/foundry`, `spec/toolchain` | The checks build and read the contracts. They need the fetched toolchain |
| `scripts/devnet.py` | `spec/toolchain`, `spec/evidence/permit2`, `contracts/` | Uses the pinned anvil and forge |

## Single sources and generated files

`spec/eip712/types.json` is the single source of every EIP-712 type string, domain, tag and loop bound. The Solidity libraries (two projects), the TypeScript, the golden vectors, the wallet
payloads and the type documentation are **generated** from it by `spec/tools/export_eip712.py`; `python -I spec/tools/check_all.py` fails when any of them is out of date.
`.env.example` and `docs/configuration.md` are generated from `packages/config/src/schema.js` and are checked by the package tests.

## Reading order for the protocol

`spec/README.md` is the index. The decision records are in `spec/06-initial-architecture.md`; the checkout session and wallet connection are in `spec/19-checkout-session-and-wallet-connect-profile.md`;
the freeze readiness is printed by `python -I spec/tools/freeze_readiness.py` (it says NOT READY today).
