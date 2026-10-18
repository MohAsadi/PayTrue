# PayTrue documentation

PayTrue is an open-source toolkit for **non-custodial crypto payments**: smart contracts, a typed-data encoder, a client SDK and the specification they follow. You run it
yourself, on your own infrastructure, under your own domain. **PayTrue Cloud is optional and nothing here requires it.**

> **Status: pre-alpha.** Nothing in this repository is audited, the protocol is not frozen, no wallet has been tested, and no production payment service exists yet.
> Read [open-source readiness](open-source-readiness.md) for the precise state of every part before you build on it.

## Start here

| You are... | Read |
|---|---|
| Evaluating PayTrue | [Architecture](architecture.md), [open-source readiness](open-source-readiness.md) |
| A developer who wants to try it | [Getting started](getting-started.md), then [headless use](headless.md) |
| An operator who wants to host it | [Self-hosting](self-hosting.md), [domains](domains.md), [contract deployments](contracts-deployments.md), [production](production-deployment.md) |
| Embedding it in another site | [Embedding](embedding.md) |
| A contributor | [CONTRIBUTING](../CONTRIBUTING.md), [packages and releases](packages-and-releases.md), [evidence policy](evidence-policy.md) |
| A security researcher | [SECURITY](../SECURITY.md), [production](production-deployment.md) (known gaps) |
| A lawyer or a packager | [Licensing](licensing.md), [THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES.md), [trademark](../TRADEMARK.md), [rename impact](rename-impact.md) |

## Map

| Document | What it answers |
|---|---|
| [Getting started](getting-started.md) | How do I run the tests, the example and a local devnet in ten minutes? |
| [Architecture](architecture.md) | What is in this repository, which part is real, and how do the parts depend on each other? |
| [Self-hosting](self-hosting.md) | What can I host today, what can I not, and what does PayTrue never ask me to depend on? |
| [Domains](domains.md) | A path on my existing domain, my own subdomain, or separate hosts: how, and what are the trade-offs? |
| [Embedding](embedding.md) | How do I put the checkout in my own frontend, and what is verified? |
| [Headless use](headless.md) | How do I use the API, the SDK and signed webhooks without any PayTrue user interface? |
| [Configuration](configuration.md) | Every environment variable (generated from the code). |
| [Contract deployments](contracts-deployments.md) | Canonical versus sovereign deployments, the manifest, the deployment script. |
| [Production deployment](production-deployment.md) | What would have to be true before real money moves, and a reference topology. |
| [Packages and releases](packages-and-releases.md) | Which packages exist, how they are versioned, and how a release is made. |
| [Licensing](licensing.md) | Which license applies to what, and how third-party licenses fit. |
| [Rename impact](rename-impact.md) | PayTrue versus the working name FastPay, and the identifiers that must not be renamed blindly. |
| [Evidence policy](evidence-policy.md) | What evidence is public, generated or private, and how it is kept. |
| [PayTrue Cloud boundary](cloud-boundary.md) | What "optional" means and how it is enforced. |
| [Open-source readiness](open-source-readiness.md) | The gap analysis: every category, before and after, and the remaining blockers. |

The **specification** (`spec/`) is the source of truth for the protocol, with its own index at `spec/README.md`. It uses the working name FastPay; see
[rename impact](rename-impact.md).

## Conventions

- **Proposed** means written down for review and not approved by anyone. **Specified** means a document defines it and no code implements it.
- Nothing here claims a wallet is supported: no wallet-lab evidence exists.
- Commands run from the repository root. Node 22.13 or later builds the EIP-712 package; the SDK, configuration and development stub need Node 18 or later.
