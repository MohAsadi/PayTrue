# Deployment manifests

A manifest names the contract addresses of **one deployment on one chain**. Configuration reads it through `PAYTRUE_DEPLOYMENT_FILE`
([docs/configuration.md](../docs/configuration.md)); [docs/contracts-deployments.md](../docs/contracts-deployments.md) explains the two kinds.

| Kind | Meaning | Exists today |
|---|---|---|
| `sovereign` | You deployed the contracts yourself, under your own governance, guardian and signers. Nobody else vouches for it. | Yes: any operator can create one with `contracts/script/Deploy.s.sol` |
| `canonical` | A deployment maintained by the PayTrue project. | **No.** The validator refuses it unless it carries an approved protocol freeze and audit references; the freeze is not approved. |

```bash
python -I scripts/validate_deployment.py deployments/example-sovereign-31337.json
python -I scripts/devnet.py --once          # write deployments/local-31337.json from a throwaway local chain
```

`local-*.json` files are ignored by Git. `example-sovereign-31337.json` is the real output of the local devnet and is committed as an example: its addresses are
those of a throwaway anvil chain and mean nothing anywhere else.

## Fields

| Field | Notes |
|---|---|
| `schema` | `paytrue.deployment/1` |
| `kind` | `sovereign` or `canonical` |
| `label` | A human name for this deployment |
| `chainId`, `deployedAt` | The chain and an RFC 3339 UTC time |
| `permit2` | The Permit2 contract of that chain. Verify it against the pinned record before you rely on it |
| `contracts` | The 12 contracts of one system: `RouterRegistry`, `TokenPolicyRegistry`, `SignerSetRegistry`, `MerchantRegistry`, `ExecutorRegistry`, `FeeController`, `UsageLedger`, `SuccessorValidator`, `MandateGateway`, `MigrationQueue`, `MandateManager`, `PaymentRouter` |
| `roles` | `deployer`, `governance`, `guardian`, `riskAuthority`, `feeRecipient` |
| `compiler` | The frozen settings the contracts were built with: solc 0.8.24, cancun, 200 optimizer runs |
| `freezeApproval`, `audits` | Required for `canonical` only. A `sovereign` manifest must not claim a freeze approval |
