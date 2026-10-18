# Examples

Each example runs offline against the **development stub** (in memory, no wallet, no chain, no money). They use the packages by relative path; in your own project you import `@paytrue/sdk` and
`@paytrue/config` by name once they are published (they are not yet).

| Example | Shows | Run | Verified |
|---|---|---|---|
| [`headless-node`](headless-node/README.md) | Your server creates a session, verifies signed webhooks, deduplicates and orders them, and fulfils once on `completed` | `node examples/headless-node/index.mjs` | Runs; the CI workflow runs it |
| [`embed-iframe`](embed-iframe/README.md) | **Experimental.** Your site frames the hosted checkout; messages are accepted only from the exact origin, frame and shape | `node examples/embed-iframe/server.mjs` | Run in a real browser: the allowed origin received the messages, another origin was blocked by `frame-ancestors` |
| [`same-domain-path`](same-domain-path/README.md) | PayTrue under `/paytrue` of a site you already serve, behind Caddy or nginx | follow the README | The application side is tested; the proxy files are **not run** by this repository's checks |
| [`sovereign-deploy`](sovereign-deploy/README.md) | Deploy your own contracts on a local chain and read the manifest | `python -I scripts/devnet.py --once` | Run end to end with the pinned anvil and forge |

No example needs an account, a key you do not generate, or a network connection (the sovereign example needs the one-time toolchain fetch).
