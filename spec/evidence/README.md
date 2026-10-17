# Evidence directory

Nothing in this directory is an approval. It holds the **recorded evidence** that [tools/freeze_readiness.py](../tools/freeze_readiness.py) reads to decide whether protocol freeze (RG-016) may be requested. A condition of [16 §1](../16-freeze-decision-report.md) is met only by files here (or by `config/pc_records.json`), never by prose in a document.

| Path | Holds | Today |
|---|---|---|
| `permit2/pin.json` | The pinned Permit2 commit and tag, the source blobs read, the deployed runtime code per chain (length, hash, immutables, masked hash), the selector audit, and what is **not** established. Gains `humanReview`, `rebuild` and `forkReport` objects when those exist | Pin and on-chain observations recorded 2026-10-16 by an automated session; `rebuild` (reproduced) and `forkReport` recorded from tool runs; `humanReview` **absent** |
| `wallet-lab/EVL-nn/*.json` (+ raw artifacts beside each record) | One run record per test × wallet × version × platform × account × chain, in the format of [15 §4](../15-wallet-lab-matrix.md): `runId`, `testId`, `evl`, `wallet`, `walletVersion`, `platform`, `accountType`, `chainId`, `startedAt`, `tester`, `reviewer` (a different person), `raw[]` (`name`, `sha256`; the file sits beside the record), `result`, `evidenceId` | **None** |
| `templates/run-record.template.json` | The empty run-record shape to copy (not counted by the checker); it also carries `typedDataSignatures` and `signatures` | Template |
| `wallet-lab-kit/` | The preparation of the wallet lab, not evidence: the register of the people who may sign a record (`people.json`, empty), the procedure ([README](wallet-lab-kit/README.md)); the verifier is [tools/wallet_lab_verify.py](../tools/wallet_lab_verify.py) | Kit only; **no run record exists** |
| `implementation/` | The implementation evidence of the 0.5.0 basis: [REPORT.md](implementation/REPORT.md) (generated), `findings.json`, `loop-audit.json`, `build-report.json` with ABI and storage snapshots, `fork-runs.json`, and the raw logs of the runs | Present; read by `impl_report.py` and `check_all.py` |
| `freeze_register.json` | Statuses of the freeze-blocking decisions (UD), facts (UX), planner implementations, audit engagements, the Foundry run report and the four sign-offs | All open |

Rules: a record is never edited after review (add a new one); an artifact's checksum must match; `tester` and `reviewer` differ **and both signed the record** (`tools/wallet_lab_verify.py`: registered people, EIP-191 signatures over the record hash); a PASS that feeds a safety flag is reviewed by a second person ([15 §4](../15-wallet-lab-matrix.md)). The checker counts only records that pass these rules.
