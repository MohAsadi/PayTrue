# Wallet-lab kit (not evidence)

This directory prepares the wallet lab ([15](../../15-wallet-lab-matrix.md)); it holds **no run result**. The lab needs real wallets, real accounts and named people, and those cannot be produced by a script. What a script can do is make a run easy to perform and impossible to forge silently, and that is all this kit does.

**Status: 0 of 10 EVL run sets exist. No run record has been created, signed or simulated.** `freeze_readiness.py` condition C-2 reads `../wallet-lab/` (empty) and stays unmet.

## What is here

| Item | Purpose |
|---|---|
| [people.json](people.json) | Register of the people who may sign a run record: name → the Ethereum address of the account they sign with. **Empty.** A person is added by a human (the QA Lead) with the date and the registrar's name; no tool adds one |
| [../../eip712/typed-data/](../../eip712/typed-data) | The exact `eth_signTypedData_v4` payload of every FastPay message (activation, successor authorization, pin updates, revoke, pause, resume, reduce, quote) and of the Pay Once witness under Permit2 (single and batch). Use them for WL-16 (activation prompt), WL-17 (successor authorization), WL-19 (`revokeBySig`), WL-27 (Pay Once witness display). Values are illustrative; the digests are fixed by the golden vectors |
| [../templates/run-record.template.json](../templates/run-record.template.json) | The run record to fill: it now also carries `typedDataSignatures` and `signatures` |
| [../../tools/wallet_lab_verify.py](../../tools/wallet_lab_verify.py) | Checks the signatures of a run record and of the typed data a wallet signed |
| [../../tools/secp256k1_min.py](../../tools/secp256k1_min.py) | The ECDSA recovery it uses; its recovery is checked against the EVM's `ecrecover` on signatures in the golden vectors |

## How a run becomes a signed record

1. **Run the test** of [15 §3](../../15-wallet-lab-matrix.md) with a real wallet (the build, platform, account type and chain are part of the record). For WL-16, WL-17, WL-19 and WL-27 sign the payload file named above in the wallet and keep the signature the wallet returns; take the screenshot of the prompt.
2. **Write the record** from the template under `evidence/wallet-lab/EVL-nn/<runId>.json`; put every raw artifact beside it and fill `raw[].sha256`. For each typed-data signature add `{"payload": "<file>", "account": "<0x…>", "signature": "<0x…>"}` to `typedDataSignatures`. An account that is a smart contract answers through ERC-1271: add `"scheme": "erc1271"` and `"onChainCheck"` with the recorded `isValidSignature` call result (this cannot be verified offline).
3. **Print the message to sign:** `python -I spec/tools/wallet_lab_verify.py --message <record.json>` prints `fastpay-wallet-lab-run-record:v1:<sha256 of the record without its signatures>`.
4. **Sign it twice, in two wallets:** the tester with `personal_sign` in their own wallet, then the reviewer (a different person, a different address) after reading the record and the artifacts. Put both signatures in `signatures.tester` and `signatures.reviewer`.
5. **Verify:** `python -I spec/tools/wallet_lab_verify.py --all`. `freeze_readiness.py` counts a record only if this verification passes (condition C-2): registered people, valid signatures, different signers, matching artifact checksums.

A record is never edited after signing (the hash would change); a new run is a new record.

## What this kit does not do

* It does not run a wallet, a browser or a chain.
* It does not decide a result: PASS, FAIL and INCONCLUSIVE are the lab's findings.
* It does not register people, hold keys or sign for anyone. The self-test (`wallet_lab_verify.py --selftest`) uses throw-away keys derived from fixed strings and writes nothing to `../wallet-lab/`.
