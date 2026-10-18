# Self-hosting

PayTrue is designed to run on **your** infrastructure, under **your** domain, against **your** chains, with **your** keys. This page says what that means today and what is missing.
Nothing here depends on `paytrue.me` or on any service operated by the PayTrue project, and a repository check keeps it that way
(`python -I scripts/repo_hygiene.py` fails if code, deployment files or examples name a PayTrue-hosted domain).

## What you can host today

| Level | What | Verified how |
|---|---|---|
| 0. Libraries | `@paytrue/config`, `@paytrue/sdk`, `@paytrue/eip712` in your own code | Package tests; `npm pack --dry-run`; the headless example |
| 1. Sovereign contracts | Deploy the PayTrue contracts on a chain of your choice with `contracts/script/Deploy.s.sol`, under your own governance, guardian, executors and signers | The script is tested on a local EVM and end to end on a local anvil chain with Permit2 at its canonical address (`scripts/devnet.py`). **Not tested on a public chain** |
| 2. Integration environment | The development stub, behind your reverse proxy, under a path, a subdomain or separate hosts; the SDK against it; signed webhooks | Tests of every layout; a real-browser check of the embedding example |
| 3. A production payment service | The hosted checkout, the wallet connection, the executor, reconciliation, the ledger | **Does not exist.** Specified in `spec/`; see [production](production-deployment.md) |

Level 3 is the blocker for the sentence "PayTrue can be self-hosted as a payment service". Until it is built, an operator can deploy the contracts and integrate against the
proposed API with the stub; an operator cannot take customer payments through a PayTrue-provided service.

## What "self-hosted" means here, precisely

- **No required hosted service.** Every address, origin and URL comes from your configuration ([configuration](configuration.md)). The SDK has no default base URL; the
  configuration loader has no default for Cloud and refuses to enable it without an explicit URL ([Cloud boundary](cloud-boundary.md)).
- **Your domain.** The layouts of [domains](domains.md) cover a path on a domain you already serve, your own subdomain, and separate hosts for the checkout and the API.
- **Your contracts.** A deployment is yours: your governance (a timelock in production), your guardian (stop-only), your executors, quote signers, merchants and token policy.
  Nobody else holds a role. The contracts have no proxy and no upgrade path; a new version is a new deployment ([contract deployments](contracts-deployments.md)).
- **Your keys.** No PayTrue component holds a customer key. The executor and quote-signer keys of the future service are yours; their separation is specified
  (`spec/04-context-and-trust-boundaries.md`, TM-10).
- **Your RPC providers.** Production configuration requires at least two RPC hosts per chain; nothing defaults to a public provider.

## Operator responsibilities (when the service exists)

| Area | You decide and run |
|---|---|
| Chains and Permit2 | Which chains; that the Permit2 address of each is the real one (the pinned record `spec/evidence/permit2/pin.json` shows how it was checked) |
| Governance | A timelock for widening actions, a guardian that can only stop, a risk authority |
| Keys | Executor, quote signers and webhook secrets, in a key-management system, one key class each |
| Domains and TLS | Your certificates, your proxy ([domains](domains.md)) |
| Merchants and tokens | Registry entries, recipients (a recipient change is delayed by design), token policy and price bounds |
| Operations | Monitoring, backups, incident response, support |
| Compliance | Whether your use needs a licence, KYB or counsel. Nothing in this repository is legal advice |

## What PayTrue will not do for you

It will not custody funds, create customer wallets, accept a seed phrase, or give you a deposit address that it controls (specification decisions CSD-04 and CSD-05).

## Checking your own deployment

```bash
python -I scripts/validate_deployment.py path/to/your-manifest.json     # the format
python -I scripts/repo_hygiene.py --history                              # on your fork, before you publish it
```
