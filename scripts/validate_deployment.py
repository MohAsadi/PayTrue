#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Validate a PayTrue deployment manifest (standard library only).

    python -I scripts/validate_deployment.py deployments/sovereign.example.json [more files]

A manifest names the contract addresses of ONE deployment on ONE chain. Two kinds exist (README, section Deploy your own contracts):
  sovereign  an operator deployed the contracts under their own governance; PayTrue maintainers vouch for nothing.
  canonical  a PayTrue-maintained deployment. None exists. The schema refuses `canonical` unless it carries an approved protocol freeze and audit references:
             the freeze is not approved, so no valid canonical manifest can be written today.
"""
import json
import pathlib
import re
import sys

REQUIRED_CONTRACTS = ["RouterRegistry", "TokenPolicyRegistry", "SignerSetRegistry", "MerchantRegistry", "ExecutorRegistry", "FeeController", "UsageLedger",
                      "SuccessorValidator", "MandateGateway", "MigrationQueue", "MandateManager", "PaymentRouter"]
ADDRESS = re.compile(r"^0x[0-9a-fA-F]{40}$")
ROLES = ["deployer", "governance", "guardian", "riskAuthority", "feeRecipient"]


def validate(doc):
    problems = []
    if doc.get("schema") != "paytrue.deployment/1":
        problems.append('schema must be "paytrue.deployment/1"')
    kind = doc.get("kind")
    if kind not in ("sovereign", "canonical"):
        problems.append("kind must be sovereign or canonical")
    if not isinstance(doc.get("chainId"), int) or doc.get("chainId", 0) < 1:
        problems.append("chainId must be a positive integer")
    if not isinstance(doc.get("label"), str) or not doc.get("label"):
        problems.append("label is required (a human name for this deployment)")
    if not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", str(doc.get("deployedAt", ""))):
        problems.append("deployedAt must be an RFC 3339 UTC time such as 2026-10-17T12:00:00Z")
    if not ADDRESS.match(str(doc.get("permit2", ""))):
        problems.append("permit2 must be an address (the Permit2 of that chain)")
    contracts = doc.get("contracts")
    if not isinstance(contracts, dict):
        problems.append("contracts is required")
    else:
        for name in REQUIRED_CONTRACTS:
            if not ADDRESS.match(str(contracts.get(name, ""))):
                problems.append(f"contracts.{name} must be an address")
        extra = sorted(set(contracts) - set(REQUIRED_CONTRACTS))
        if extra:
            problems.append(f"unknown contracts: {extra}")
        addrs = [str(v).lower() for v in contracts.values()]
        if len(set(addrs)) != len(addrs):
            problems.append("two contracts share an address")
    roles = doc.get("roles")
    if not isinstance(roles, dict):
        problems.append("roles is required")
    else:
        for r in ROLES:
            if not ADDRESS.match(str(roles.get(r, ""))):
                problems.append(f"roles.{r} must be an address")
    comp = doc.get("compiler")
    if not isinstance(comp, dict) or comp.get("solc") != "0.8.24" or comp.get("evm") != "cancun" or comp.get("optimizerRuns") != 200:
        problems.append("compiler must record the frozen settings: solc 0.8.24, evm cancun, optimizerRuns 200")
    if kind == "canonical":
        fr = doc.get("freezeApproval")
        if not isinstance(fr, dict) or not fr.get("approvedBy") or not fr.get("date"):
            problems.append("a canonical deployment needs freezeApproval {approvedBy, date}: protocol freeze is not approved, so none can be valid today")
        if not doc.get("audits"):
            problems.append("a canonical deployment needs audits: a non-empty list of audit references")
    if kind == "sovereign" and doc.get("freezeApproval"):
        problems.append("a sovereign deployment must not claim a freeze approval")
    return problems


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    failed = 0
    for f in argv:
        try:
            doc = json.loads(pathlib.Path(f).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            print(f"FAIL {f}: {e}")
            failed += 1
            continue
        problems = validate(doc)
        if problems:
            failed += 1
            print(f"FAIL {f}")
            for p in problems:
                print("   ", p)
        else:
            print(f"ok   {f} ({doc['kind']}, chain {doc['chainId']}, {len(doc['contracts'])} contracts)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
