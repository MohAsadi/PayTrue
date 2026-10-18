# Security policy

PayTrue handles money, so security reports are taken seriously. **Please do not report a vulnerability in a public issue, discussion or pull request.**

## Status of the project: read this first

PayTrue is **pre-alpha**. The contracts are **not audited**, the protocol is **not frozen**, no wallet has been tested, and no production payment service exists. Do not put real funds
behind anything built from this repository today ([production deployment](docs/production-deployment.md)). A finding is still valuable: this is the time to find it.

## How to report

Use GitHub's **private vulnerability reporting**:
<https://github.com/MohAsadi/PayTrue/security/advisories/new>

> **Owner action:** private vulnerability reporting must be enabled in the repository settings (Settings, Code security, Private vulnerability reporting). Until it is, the link above does
> not work. No other contact address is published here, and none will be invented: if the link does not work, open a public issue that says only "I have a security report; how can I send it
> privately?" and **no details**.

Please include: what is affected (a contract and function, a package, a script, a document), how to reproduce it (a failing test, a transaction sequence, a request), the impact you believe it
has, the commit you tested, and whether you want credit.

## What happens next

These are aims, not guarantees; the project is maintained by volunteers.

| Step | Aim |
|---|---|
| Acknowledge your report | within 7 days |
| First assessment (accepted, needs more information, out of scope) | within 14 days |
| Fix or mitigation, and an agreed disclosure date | depends on severity; we prefer **coordinated disclosure** and will agree a date with you (90 days is the default ceiling) |
| Credit | in the advisory and the changelog, if you want it |

There is **no bug bounty**.

## Scope

In scope:

- The contracts in `contracts/src` (including their libraries and interfaces) and the deployment script.
- `packages/config`, `packages/sdk`, `packages/eip712`.
- The tools that produce or check evidence (`spec/tools`), the scripts in `scripts/`, the reverse-proxy and container files in `deploy/`.
- The specification, where a *design* flaw would let someone take, lock or misdirect funds (a threat model, a missing guard, a replay across domains).
- A secret, a private key or personal data committed to the repository or its history.

Out of scope:

- **The development stub** (`packages/devserver`). It is deliberately insecure and in memory; it refuses to run in production. Do not report that it has no real security.
- Findings that need a modified or malicious build that nobody would deploy, or a compromised developer machine.
- Third-party code (Foundry, solc, Permit2, forge-std, your wallet): report it upstream. If PayTrue's *use* of it is wrong, that is in scope.
- Volumetric denial of service, social engineering, physical attacks, and automated scanner output without a demonstrated impact.
- Open decisions that the specification already lists as open (`spec/16-freeze-decision-report.md`, `spec/19-...` section 23).

## Safe harbor

We will not pursue action against anyone who researches in good faith: on a **local chain or testnet you control**, on **your own deployment**, against **your own accounts**; who does not access or
change data that is not theirs; who does not test third-party systems; and who gives us reasonable time before disclosure. Do not test with real funds that are not yours. This is a statement of
intent by the maintainers, not a legal contract, and it does not bind third parties.

## Secrets in the repository

If you find a secret, a key or personal data in the repository or its history, report it as above. The owner will rotate the secret first; **history is not rewritten without the owner's explicit
decision**, because it breaks every clone. The repository is checked by `python -I scripts/repo_hygiene.py --history`, and GitHub secret scanning and push protection should be enabled by the owner.

## For operators

Your deployment's security is yours: keep governance behind a timelock and the guardian stop-only, keep one key class per key, use at least two independent RPC providers, and pin and verify the
toolchain. [Self-hosting](docs/self-hosting.md) and [contract deployments](docs/contracts-deployments.md) list what you are responsible for.
