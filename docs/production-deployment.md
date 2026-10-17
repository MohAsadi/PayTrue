# Production deployment

> **PayTrue is not ready for production, and this page does not describe a deployment that you can make today.** It states what would have to be true, what is missing, and the shape of
> the deployment the specification aims at. Do not put real funds behind anything built from this repository now.

## What blocks production (as recorded on 2026-10-17)

`python -I spec/tools/freeze_readiness.py` prints the state. It says **NOT READY, 1 of 11 conditions met**; the one that is met is that the test suites of the reference model and of the
contracts pass.

| Blocker | State |
|---|---|
| Protocol freeze (RG-016) | **Not approved.** Ten of eleven freeze conditions are unmet: companion artifacts reviewed, the wallet-lab evidence (0 of 10 run sets), the Permit2 review at E2 (no two named reviewers), the production-blocking constants approved (0 of 19), the freeze-blocking decisions and external facts closed, two independent planner implementations, audit scope and slots, the four sign-offs, and the EIP-712 type strings approved (wallet signatures and approvals are unmet) |
| Audits | None. The contracts are **not audited**; every test was written by the people who wrote the contracts |
| Wallet compatibility | **No wallet has been tested.** Every statement about a wallet or WalletConnect is unverified until wallet-lab evidence exists |
| The payment service | **Does not exist**: no hosted checkout with a wallet connection, no executor, no reconciliation, no ledger, no risk engine |
| Constants | All 19 production-blocking constants are *proposals* |
| Chains | Gas figures use the compiler's EVM schedule, not the chains' own accounting (Arbitrum's in particular); the per-transaction gas cap is an assumption |
| Legal | Licensing of the operator, KYB, consumer-protection and sanctions questions are open (`spec/03-assumptions-decisions-risks.md` lists them) and are the operator's |
| Canonical deployment | None exists |

## The shape the specification aims at

When the service exists, a production deployment is meant to look like this. Every part is configurable; none depends on a PayTrue-hosted service.

| Part | Intent |
|---|---|
| Origins | The hosted checkout on **its own subdomain** ([domains](domains.md), layout B); the merchant API on a private or allow-listed host (layout C) |
| TLS and headers | Your certificates; HSTS, `X-Content-Type-Options`, `Referrer-Policy: no-referrer`; a strict content security policy with no third-party script and no merchant code on the checkout origin; `frame-ancestors 'none'` unless you named an embedding origin |
| Chains | A short list you chose; **two or more independent RPC hosts per chain** (production configuration refuses fewer); your own node for critical reads is recommended |
| Contracts | A sovereign deployment ([contract deployments](contracts-deployments.md)): governance behind a timelock, a stop-only guardian, a risk authority, separate executor and quote-signer key classes in a key-management system |
| Secrets | Webhook secrets, API keys and signing keys in a secret store; none in Git, none in logs; rotation with an overlap |
| Webhooks | Delivered through an egress proxy that cannot reach internal ranges; signed, retried with backoff, deduplicated by event id |
| Observability | Alerts on the audit events of the session state machine, on `unknown` sessions that stay unresolved, on lease takeovers, on webhook failures, on each pause bit |
| Operations | Runbooks (the specification indexes RB-001 to RB-033), backups, incident response, an on-call owner, a way for customers to revoke (always available, never gated) |
| Release | Tagged releases, signed artifacts, pinned dependencies, a changelog ([packages and releases](packages-and-releases.md)) |

## A checklist for the first real deployment (not satisfiable today)

- [ ] Protocol freeze approved; the contracts you deploy are the frozen, audited bytecode (frozen compiler settings).
- [ ] Two independent audits of the contracts completed and their findings closed.
- [ ] The wallet lab has run for every wallet you will claim to support; a wallet without a passing record is not described as supported.
- [ ] Each of the 19 constants approved by its named approvers.
- [ ] A payment service exists and passed the acceptance criteria of `spec/19-checkout-session-and-wallet-connect-profile.md` (section 20) on a testnet.
- [ ] Penetration test of the hosted checkout, the webhook path and the key service.
- [ ] A recovery drill: removal of a compromised quote signer, a pause, a migration.
- [ ] Counsel has reviewed your operating model.

## If you find a problem

Do not open a public issue for a vulnerability: see [SECURITY](../SECURITY.md).
