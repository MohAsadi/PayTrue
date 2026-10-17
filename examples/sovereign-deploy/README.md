# Deploy your own contracts (sovereign deployment), locally

```bash
python -I spec/toolchain/fetch_toolchain.py       # once: the pinned Foundry and solc, verified by SHA-256
python -I scripts/devnet.py --once                # a throwaway local chain, Permit2, the 12 PayTrue contracts, a manifest
cat deployments/local-31337.json
python -I scripts/validate_deployment.py deployments/local-31337.json
```

What happens: the pinned `anvil` starts; Permit2 is installed at its canonical address through the deterministic deployment proxy with the creation code and salt recorded by the Permit2 rebuild;
`contracts/script/Deploy.s.sol` runs with `PAYTRUE_*` variables; the 12 created addresses are read from the broadcast and written to a manifest that is validated.

For a real chain, use the same script with your own parameters and **your own governance**: [contract deployments](../../docs/contracts-deployments.md). Do not deploy this to a chain that holds real value:
the contracts are not audited and the protocol is not frozen. `deployments/example-sovereign-31337.json` is a committed copy of one such local run.
