# Governance

## Today

PayTrue has **one maintainer and owner: [@MohAsadi](https://github.com/MohAsadi)**. There is no foundation, no company behind this repository's name that is stated here, and no committee.
This page says how decisions are made now and how that is meant to grow. It describes the **project**; it has nothing to do with the on-chain governance roles of a deployment
(governance, guardian, risk authority), which each operator holds for their own contracts ([contract deployments](docs/contracts-deployments.md)).

## Roles

| Role | Who | Can |
|---|---|---|
| Owner | @MohAsadi | Everything below; changes the license, the trademark policy and this document; adds and removes maintainers; enables repository settings |
| Maintainer | Added by the owner after a sustained record of good changes and reviews | Review and merge pull requests, triage issues, cut releases, handle security reports |
| Contributor | Anyone | Open issues and pull requests; review |

## How decisions are made

| Kind of change | Decision |
|---|---|
| Code, documentation, tests, examples | A maintainer who did not write it approves; the checks of [CONTRIBUTING](CONTRIBUTING.md) pass. Lazy consensus: if nobody objects within a reasonable time, a maintainer may merge |
| A protocol rule, a type, a constant, a contract invariant | Starts as a change to the specification under the review rules recorded there; a `SECURITY-CRITICAL`, `FINANCIAL-CONTROL` or `PRIVACY-CRITICAL` item needs a named reviewer from Security |
| **An approval** (protocol freeze, a production-blocking constant, an EIP-712 fingerprint, a wallet-lab record, a release gate) | **Only a named human, in the record that the specification defines, with the evidence it names.** No tool, no bot and no assistant approves anything, and a passing check is never an approval |
| License, trademark, governance, this repository's name | The owner |
| A security report | The maintainers, in private, as [SECURITY](SECURITY.md) describes |
| A release | A maintainer, after the release checks ([packages and releases](docs/packages-and-releases.md)) |

`main` is protected: nobody, the owner included, pushes to it directly; changes arrive by pull request (an owner action to configure in the repository settings).

## Becoming a maintainer

Sustained, good-quality contributions and reviews; knowledge of the area; agreement with this document and the code of conduct. The owner invites; the other maintainers are consulted.
A maintainer who is inactive for a long time or who breaks the code of conduct can be moved to emeritus by the owner.

## Conflicts

Disagreements about a change are settled in the pull request. If they are not, the owner decides and writes down the reason.

## Changing this document

By pull request, approved by the owner.
