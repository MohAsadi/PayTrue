# Contract deployments: canonical and sovereign

## Two kinds

| | Sovereign | Canonical |
|---|---|---|
| Who deploys | **You**, from your own account | The PayTrue project |
| Who holds the roles | You: your governance (a timelock in production), your guardian (stop-only), your risk authority, your executors, your quote signers | The project's governance |
| Who vouches for it | Nobody but you | The project, after an approved protocol freeze and audits |
| Exists today | **Yes**: anyone can create one | **No.** None exists, and none can be declared until protocol freeze is approved and audits are done |
| Manifest `kind` | `sovereign` | `canonical` (the validator refuses it without a freeze approval and audit references) |

The contracts do not know which kind they are. They contain **no hard-coded address of any PayTrue party** and no URL: every link is a constructor argument. A sovereign deployment is
therefore not a fork or a variant; it is the same bytecode with your arguments.

## Deploying your own

`contracts/script/Deploy.s.sol` deploys one system on one chain in the one order that makes the cyclic links work (the manager, the usage ledger, the gateway and the migration queue
point at each other through immutable addresses, so the manager's address is predicted from the deployer's nonce). It ends by checking that the links are mutual and reverts otherwise.

```bash
# the parameters: there are NO defaults
export PAYTRUE_PERMIT2=0x...            # the Permit2 of that chain: verify it against spec/evidence/permit2/pin.json
export PAYTRUE_GOVERNANCE=0x...         # a timelock in production
export PAYTRUE_GUARDIAN=0x...           # stop-only
export PAYTRUE_RISK_AUTHORITY=0x...
export PAYTRUE_MAX_QUOTE_TTL=...        # PC-06, immutable ceiling
export PAYTRUE_MAX_BAND_WIDTH_BPS=...   # PC-07, immutable ceiling
export PAYTRUE_QUOTE_SET_GRACE=...      # PC-08
export PAYTRUE_FEE_CEILING_BPS=...      # PC-05: no value is proposed; this is yours to decide
export PAYTRUE_FEE_BPS=...
export PAYTRUE_FEE_RECIPIENT=0x...
python -I spec/toolchain/forge.py --project contracts script script/Deploy.s.sol:Deploy --sig "run()" --rpc-url "$RPC" --broadcast
```

The earlier `FASTPAY_*` names of the same variables are still read when the `PAYTRUE_*` one is unset. The values of PC-05 to PC-08 are constants **no one has approved**; the specification's
configuration records (`spec/18-configuration-records.md`) show the proposals and the reasoning, not decisions.

The script is **deployment code, not a deployment**: it records no address anywhere, holds no role for itself and leaves no owner. After it runs, the registries are empty: the router
refuses a payment until governance has registered a router version, an executor, a merchant, a token with its policy, and (for quoted payments) a signer set. The role-by-role sequence the
tests use is `_deploySystem` in `contracts/test/helpers/Base.sol`.

## The manifest

Write down what you deployed so that your configuration and your tooling can read it ([`deployments/`](../deployments/README.md)):

```bash
python -I scripts/validate_deployment.py deployments/your-deployment.json
```

`PAYTRUE_DEPLOYMENT_FILE` points your configuration at it ([configuration](configuration.md)).

## Verified end to end, locally

`python -I scripts/devnet.py --once` starts the pinned anvil, installs Permit2 at its canonical address through the deterministic deployment proxy with the creation code and salt the Permit2
rebuild recorded, runs `Deploy.s.sol` with `PAYTRUE_*` variables, reads the 12 created addresses from the broadcast, writes a manifest and validates it. That run was made on 2026-10-17 with
Foundry v1.8.5. **No public chain was used**, so gas, nonces, provider behaviour and Permit2 identity on a real chain are untested by this path (the fork tests cover Permit2 on Ethereum,
Base and Arbitrum One for the suites, not the deployment script).

## Rules for a sovereign operator

1. Use the **frozen compiler settings** (`contracts/frozen-settings.json`); a different compiler or optimizer is a different bytecode and none of the evidence applies to it.
2. Check the Permit2 address of your chain against the pin; do not trust an address you did not verify.
3. Keep **governance behind a timelock** and the guardian **stop-only**; do not give an executor a governance role.
4. **There is no upgrade path.** A fix is a new deployment and a migration (`spec/12-router-lifecycle-and-migration.md`); plan for it.
5. The contracts are **not audited** and protocol freeze is not approved. Do not put real funds behind a deployment you made from this repository today.
