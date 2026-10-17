"""EXPLORATORY critical-path Monte Carlo schedule model at work-package level (revision 0.5).

Nothing here is a commitment. The model makes the constraints of the plan explicit and re-runnable; every parameter is an assumption.

Three roadmap tiers (revision 0.5), each simulated as its own scoped network (`net(scope)`, `simulate(..., scope=)`, `results(..., scope=)`):
  TRI  testnet reference implementation: a SEPARATE network built from TRI_SCOPE = {epic id: fraction of that epic's person-weeks}; no audit,
       no mainnet, no merchant platform. Its gates are G_FREEZE (TRI-1), G_TRI2, G_TRI3 and G_TRI4 (TRI-4).
  PMB  private mainnet beta: the full network pruned to the ANCESTORS of G_BETA (RG-010); work after the beta no longer competes for squads.
  GA   full GA platform: the full network (public beta, GA, then post-GA v1.1 and v2.0).
Tiers nest: the GA network contains the PMB network; TRI is a reduced-fraction network of the same epics and does not contain any of PMB's
work beyond its fractions.

What it schedules
  * Every gating epic becomes up to three work packages (WPs): B build (implementation, research task, compliance control),
    A assurance (security, test, observability) and R readiness (migration requirement, operational readiness, evidence), sized by the
    epic's story-type weights (stories.py). Release gates, external waits (audits, counsel, pen test, observation periods) and
    audit support are further nodes.
  * Dependencies are EXPLICIT and TYPED with lags (no global overlap rule):
      FS  successor starts after the predecessor finishes (+ lag)
      SS  successor starts after the predecessor starts (+ lag)
      FF  successor finishes after the predecessor finishes (+ lag)
    Lags are weeks, derived at build time as a fraction of the predecessor's nominal duration; the rule that chose each edge is
    recorded in jira/dependencies.csv (`python -I schedule_model.py --edges`).
  * A squad works one WP at a time at the capacity of a hiring ramp (list scheduling, longest remaining path first). Capacity not used
    when a squad has nothing ready is lost.
  * External waits are random variables (triangular). Output: P50 / P75 / P90 weeks for each release gate, criticality of each epic
    and WP, squad sensitivity. Deterministic for a fixed seed.

Non-gating epics (iteration reserves, data warehouse, extra locales, continuous security work, cost optimisation) are not scheduled:
they are assumed to use capacity that gating work leaves free (`NON_GATING_NOTE`).
"""
import csv
import heapq
import json
import math
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import model  # noqa: E402
import stories  # noqa: E402

STATUS = "EXPLORATORY"
FOCUS = model.FOCUS
N_RUNS = 3000
SEED = 20261013
S = model.SQUADS
HC = dict(model.SQUAD_HC)
HERE = pathlib.Path(__file__).resolve().parent

# ---- capacity assumptions ------------------------------------------------------------------------------------------
R0_GENERAL = 0.30        # fraction of final squad strength available at week 0 (15 of 50 founding)
R0_PRIORITY = 0.55       # Protocol, Chain and Quality are hired first
T_RAMP = (30, 45, 70)    # weeks to full strength, triangular (low, mode, high)
G_FACTOR = (0.90, 1.00, 1.45)   # run-wide effort factor (positive correlation between nodes)
N_FACTOR = (0.90, 1.00, 1.35)   # per node-and-squad effort factor

# ---- dependency rules (lags are fractions of the predecessor's nominal duration unless stated) -----------------------
INTRA_B_TO_A = ("SS", 0.40)      # assurance may start when 40% of the build has started producing (SS lag = 0.4 x nominal build duration)
INTRA_B_TO_A_FF = 1.0            # ... and cannot finish less than 1 week after the build finishes (FF, weeks)
INTRA_B_TO_R = ("SS", 0.70)      # readiness work starts late in the build
CROSS_DECISION = ("FS", 0.0)     # the predecessor produces a decision, finding or evidence: FS
CROSS_BUILD = ("SS", 0.50)       # the predecessor produces an interface: SS at 50% of its nominal build duration
CROSS_ASSURE_FF = 0.0            # assurance of the successor cannot finish before assurance of the predecessor (FF, weeks)
DECISION_PROFILES = {"research", "program", "compliance"}
# explicit overrides: (predecessor epic, successor epic) -> (type, lag fraction)
EDGE_OVERRIDE = {
    ("EPIC-P0-PROTOSPEC", "EPIC-P1-CONTRACTS"): ("FS", 0.0),     # contract code does not start before the specification set is complete
    ("EPIC-P1-CONTRACTS", "EPIC-P1-AUDITPREP"): ("FS", 0.0),     # the audit package needs the finished contracts
    ("EPIC-P1-CORE", "EPIC-P1-LEDGER"): ("SS", 0.30),            # the ledger schema can start once the core skeleton exists
    ("EPIC-P2-SUBS", "EPIC-P2-LOAD"): ("SS", 0.60),              # load tests need working subscriptions
    ("EPIC-P2-RECON", "EPIC-P3-RECONPROD"): ("FS", 0.0),         # production reconciliation follows the testnet reconciliation work
    ("EPIC-P3-CANARY", "EPIC-P3-TUNE"): ("SS", 0.40),            # tuning begins while the canary is running
}

# ---- who does the work when it is not only the owner squad (ASSUMPTION; editable) -----------------------------------
SPLIT = {
    "EPIC-P0-SOURCES": {"PROTO": 0.7, "QA": 0.3}, "EPIC-P0-PLANNER": {"PROTO": 0.6, "CORE": 0.4},
    "EPIC-P0-TOKENLAB": {"PROTO": 0.5, "QA": 0.5},
    "EPIC-P1-QUOTE": {"CHAIN": 0.5, "CORE": 0.5}, "EPIC-P1-CHAINGW": {"CHAIN": 0.6, "CORE": 0.4},
    "EPIC-P1-SIGNER": {"CHAIN": 0.6, "PLAT": 0.4}, "EPIC-P1-DELEGATION": {"CORE": 0.7, "PROTO": 0.3},
    "EPIC-P1-MANDATE": {"CORE": 0.7, "PROTO": 0.3}, "EPIC-P1-TOKENREG": {"PROTO": 0.5, "CORE": 0.5},
    "EPIC-P1-MIGRATION": {"PROTO": 0.4, "CORE": 0.6}, "EPIC-P1-PAYONCE": {"PROTO": 0.6, "CORE": 0.2, "CHECK": 0.2},
    "EPIC-P1-REVOKE": {"PROTO": 0.5, "CHECK": 0.3, "QA": 0.2},
    "EPIC-P2-RISKCON": {"CHECK": 0.5, "CORE": 0.3, "COMP": 0.2}, "EPIC-P2-COMPLIANCE": {"COMP": 0.5, "CORE": 0.5},
    "EPIC-P2-COMPOPS": {"COMP": 0.6, "CORE": 0.4}, "EPIC-P3-LIMITS": {"COMP": 0.4, "CORE": 0.6},
    "EPIC-P4-FRAUD": {"COMP": 0.4, "CORE": 0.6}, "EPIC-P4-MERCHANTOPS": {"COMP": 0.6, "DEVX": 0.2, "CORE": 0.2},
    "EPIC-P4-V11PREP": {"PROTO": 0.7, "QA": 0.3},
    "EPIC-P5-GA": {"LEAD": 0.4, "PROD": 0.2, "DEVX": 0.2, "COMP": 0.2},
    "EPIC-P5-RELREADY": {"LEAD": 0.5, "PLAT": 0.25, "DEVX": 0.25},
    "EPIC-P3-CANARY": {"PROD": 0.4, "CHECK": 0.3, "CORE": 0.3},
    "EPIC-P2-PENTEST": {"PLAT": 0.6, "CORE": 0.4},
}

# ---- network definition --------------------------------------------------------------------------------------------
P0, P1, P2, P3, P4, P5, P6, P7 = ("EPIC-P%d-" % i for i in range(8))
ids = lambda pre, *names: [pre + n for n in names]

GATING = (
    ids(P0, "DOCS", "SOURCES", "TOKENLAB", "PLANNER", "PROTO", "THREAT", "LEGAL", "DESIGN", "PRODUCT", "INFRA", "HIRING", "AUDITSEL", "PROTOSPEC")
    + ids(P1, "CONTRACTS", "PAYONCE", "FLAGS", "QUOTE", "MIGRATION", "DELEGATION", "FORK", "CORE", "LEDGER", "CHAINGW", "SIGNER", "MANDATE",
          "TOKENREG", "SECPROG", "AUDITPREP", "OBS", "REVOKE")
    + ids(P2, "ORCH", "CHECKOUT", "PORTAL", "MERCHANT", "COMPLIANCE", "DEVDOC", "RUNBOOKS", "TESTNET", "SUBS", "SANDBOX", "RISKCON", "LOAD",
          "REFUNDS", "LEGALPACK", "A11YL10N", "DEPLOYPREP", "RECON", "PORTALS", "COMPOPS", "SUPPORTPREP", "MIGSVC")
    + ids(P3, "DEPLOY", "CANARY", "LIMITS", "IRDR", "BOUNTY", "SUPPORT", "RECONPROD", "LEGALGO", "TUNE", "T1START", "TOKENOPS", "MIGDRILL")
    + ids(P4, "CHAINS", "T1", "BOUNTYPUB", "SCALE", "FRAUD", "MERCHANTOPS", "COMPEXP", "DRDRILLS", "MIGGAME", "V11PREP")
    + ids(P5, "GA", "OPSMAT", "DOCS", "DRILLS", "SLALEGAL", "SUPPORT247", "RELREADY")
    + ids(P6, "ROUTERV11", "ADAPTER", "CONVBACKEND", "TOKENLABSTABLE", "QUOTEPAIRS", "OPTIN", "COMPLV11", "OPSV11", "FLAGROLLOUT")
    + ids(P7, "ROUTERV2", "GENCONV", "ORACLE", "TOKENLABGEN", "USAGE", "TOPUP", "SPLITS", "COMPLV2", "MIGCAMP")
)
NON_GATING_NOTE = ("EPIC-P2-DOGFOOD, EPIC-P3-ITERATE, EPIC-P4-ITERATE, EPIC-P4-I18N, EPIC-P4-DATA, EPIC-P4-SECCONT, EPIC-P5-PERFCOST, "
                   "EPIC-P6-REPEAT/VARSUBS/CHAINS2/BAU, EPIC-P7-WHITELABEL/PARTNERAPI/BAU")

TOKEN = {"RG-001": "G_RG001", "RG-002": "G_RG002", "RG-005": "G_RG005", "RG-011": "G_PUBBETA", "RG-012": "G_GA", "RG-013": "G_RG013",
         "RG-016": "G_FREEZE", "OD-001": "L_OD001"}
REPLACE = {
    P4 + "CHAINS": ["G_RG005"],
    P4 + "V11PREP": ["G_BETA"],
    P6 + "ROUTERV11": [P4 + "V11PREP", "G_PUBBETA"],
    P3 + "DEPLOY": ["G_RG005", "G_RG006", P2 + "DEPLOYPREP"],
    P7 + "ORACLE": ["G_RG013"], P7 + "COMPLV2": ["G_RG013"],
    P7 + "TOKENLABGEN": [P6 + "TOKENLABSTABLE"],
    P7 + "MIGCAMP": ["N_V20_AUDIT_DONE", P2 + "MIGSVC"],
    P6 + "FLAGROLLOUT": ["N_V11_AUDIT_DONE", "N_ADAPTER_AUDIT_DONE", P6 + "CONVBACKEND", P6 + "TOKENLABSTABLE", P6 + "OPTIN"],
}
ADD = {
    P1 + "FORK": ["G_FREEZE"], P1 + "TOKENREG": ["G_FREEZE"], P1 + "DELEGATION": ["G_FREEZE"],
    P2 + "DEPLOYPREP": ["G_CONTRACT_FREEZE"], P2 + "TESTNET": ["G_RG002"],
    P5 + "DOCS": ["G_RG002"],
    P3 + "CANARY": ["G_BETA"], P3 + "SUPPORT": ["G_BETA"], P3 + "TOKENOPS": ["G_BETA"], P3 + "MIGDRILL": ["G_BETA"],
    P3 + "RECONPROD": ["G_BETA"], P3 + "T1START": ["G_RG002"],
    P4 + "BOUNTYPUB": ["G_BETA"], P4 + "COMPEXP": ["G_RG002"],
    P5 + "RELREADY": ["G_PUBBETA"], P5 + "GA": ["G_PUBBETA"],
}
PHASE_DEFAULT = {"P1": "G_FREEZE", "P2": "G_RG001", "P3": "G_BETA", "P4": "G_BETA", "P5": "G_BETA", "P6": "G_GA", "P7": "G_RG013"}

P2_FEATURES = ids(P2, "ORCH", "CHECKOUT", "PORTAL", "MERCHANT", "SUBS", "REFUNDS", "RECON", "MIGSVC", "PORTALS", "SANDBOX", "DEVDOC",
                  "RISKCON", "RUNBOOKS", "SUPPORTPREP")
P1_ALL = ids(P1, "CONTRACTS", "PAYONCE", "FLAGS", "QUOTE", "MIGRATION", "DELEGATION", "FORK", "CORE", "LEDGER", "CHAINGW", "SIGNER",
             "MANDATE", "TOKENREG", "SECPROG", "AUDITPREP", "OBS", "REVOKE")
P0_ALL = ids(P0, "DOCS", "SOURCES", "TOKENLAB", "PLANNER", "PROTO", "THREAT", "LEGAL", "DESIGN", "PRODUCT", "INFRA", "HIRING", "AUDITSEL", "PROTOSPEC")

# Tier 1 scope: fraction of each epic's person-weeks that belongs to the testnet reference implementation. ASSUMPTIONS, editable inputs that
# need approval; an epic that is not listed is not in tier 1. The wallet lab (EPIC-P0-WALLETLAB) enters through W_LAB_MIN and W_LAB_REST.
TRI_SCOPE = {
    P0 + "SOURCES": 1.0, P0 + "TOKENLAB": 1.0, P0 + "PLANNER": 1.0, P0 + "PROTO": 1.0, P0 + "PROTOSPEC": 1.0, P0 + "THREAT": 0.5, P0 + "INFRA": 0.5,
    P1 + "CONTRACTS": 1.0, P1 + "PAYONCE": 1.0, P1 + "MIGRATION": 1.0, P1 + "DELEGATION": 1.0, P1 + "FORK": 1.0, P1 + "REVOKE": 1.0,
    P1 + "QUOTE": 0.6, P1 + "TOKENREG": 0.6, P1 + "CHAINGW": 0.35, P1 + "SIGNER": 0.4,
    P2 + "DEPLOYPREP": 0.6, P2 + "TESTNET": 0.5,
}

# special (non-epic) nodes: id -> (kind, deps, spec).  kinds: lead(a,m,b[,n]) | mix | gate(a,m,b) | work{fractions of epics} | extra{squad: pw}
# A dependency on an epic means: FS from every work package of that epic ("EPIC-X:BA" = build and assurance packages only; design and
# feature-complete gates need the work and its tests, not the readiness paperwork; release gates need all three groups).
SPECIAL = {
    "L_LEGAL_MEMO": ("lead", [], (7, 11, 19)),
    "L_OD001": ("lead", ["L_LEGAL_MEMO"], (2, 4, 10)),
    "W_LAB_MIN": ("work", [], {P0 + "WALLETLAB": 0.7}),            # the freeze subset EVL-01…10 of document 16 is taken to be 70% of the lab epic
    "W_LAB_REST": ("work", ["W_LAB_MIN"], {P0 + "WALLETLAB": 0.3}),
    # v0.5: three explicit pre-freeze waits (ASSUMPTIONS, ranges are triangular low / mode / high in weeks)
    "L_COUNSEL_NOTICE": ("lead", [], (6, 10, 18)),                                       # counsel view on migration notice duties (RP-26); blocks PC-01/02; starts at week 0
    "L_PERMIT2_E2": ("lead", [P0 + "SOURCES:B"], (1, 2, 4)),                             # second-reviewer sign-off at E2 of the pinned Permit2 review
    "L_PC_APPROVAL": ("lead", [P0 + "PROTOSPEC:BA", "W_LAB_MIN"], (1, 2, 5)),             # approval rounds of the individually approved production-blocking constants
    "G_FREEZE": ("gate", [x + ":BA" for x in (P0 + "SOURCES", P0 + "PROTOSPEC", P0 + "PLANNER", P0 + "PROTO", P0 + "TOKENLAB")]
                 + ["W_LAB_MIN", "L_COUNSEL_NOTICE", "L_PERMIT2_E2", "L_PC_APPROVAL"], (1, 2, 3)),
    "G_RG001": ("gate", ["G_FREEZE", "W_LAB_REST"] + P0_ALL, (1, 2, 4)),
    "G_CONTRACT_FREEZE": ("gate", [x + ":BA" for x in ids(P1, "CONTRACTS", "PAYONCE", "REVOKE", "MIGRATION", "TOKENREG", "AUDITPREP", "FORK")], (1, 2, 3)),
    "G_RG002": ("gate", ["G_CONTRACT_FREEZE"] + [x + ":BA" for x in P1_ALL], (1, 2, 4)),
    "L_AUDIT_AVAIL": ("lead", ["G_CONTRACT_FREEZE"], (0, 4, 14)),
    "L_AUDIT_RUN": ("lead", ["L_AUDIT_AVAIL"], (8, 11, 16, 2)),
    "W_AUDIT_SUPPORT": ("work", ["G_CONTRACT_FREEZE"], {P2 + "AUDIT": 0.4}),
    "W_REMEDIATE": ("work", ["L_AUDIT_RUN"], {P2 + "AUDIT": 0.6}),
    "L_REREVIEW": ("lead", ["W_REMEDIATE"], (2, 3, 5)),
    "G_RG005": ("gate", ["L_REREVIEW", "W_AUDIT_SUPPORT"], (0.5, 1, 2)),
    "G_FEATURE_COMPLETE": ("gate", [x + ":BA" for x in P2_FEATURES] + ["G_RG002"], (0, 0.5, 1)),
    "L_PENTEST": ("lead", ["G_FEATURE_COMPLETE"], (4, 6, 10)),
    "W_PENTEST_SUPPORT": ("work", ["G_FEATURE_COMPLETE"], {P2 + "PENTEST": 0.4}),
    "W_PENTEST_FIX": ("work", ["L_PENTEST"], {P2 + "PENTEST": 0.6}),
    "L_PENTEST_RETEST": ("lead", ["W_PENTEST_FIX"], (1, 2, 4)),
    "G_RG006": ("gate", ["L_PENTEST_RETEST", "W_PENTEST_SUPPORT", P1 + "SECPROG", P2 + "DEPLOYPREP"], (0.5, 1, 2)),
    "W_WALLET_E3": ("extra", ["G_RG002", P1 + "DELEGATION", P2 + "CHECKOUT"], {"QA": 24}),
    "L_WALLET_FIX": ("lead", ["W_WALLET_E3"], (2, 4, 10)),
    "G_RG003": ("gate", ["L_WALLET_FIX"], (0.5, 1, 2)),
    "L_CHAIN_EVID": ("lead", ids(P1, "CHAINGW", "SIGNER", "QUOTE"), (6, 10, 18)),
    "G_RG004": ("gate", ["L_CHAIN_EVID"], (0.5, 1, 2)),
    "L_RECON_TESTNET": ("lead", ids(P2, "RECON", "SUBS", "REFUNDS", "TESTNET"), (2, 3, 5)),
    "G_RG007": ("gate", ["L_RECON_TESTNET"], (0.5, 1, 2)),
    "G_RG009": ("gate", ids(P2, "LOAD", "RUNBOOKS", "SUPPORTPREP") + [P3 + "IRDR"], (0.5, 1, 2)),
    "L_LICENSE": ("mix", ["L_OD001"], (0.5, (8, 16, 30), (30, 52, 90))),
    "L_GOLIVE": ("lead", ["L_LICENSE"], (3, 5, 10)),
    "G_RG008": ("gate", ["L_GOLIVE"] + ids(P2, "COMPLIANCE", "COMPOPS", "LEGALPACK", "A11YL10N") + [P3 + "LEGALGO"], (0.5, 1, 2)),
    "G_BETA": ("gate", [P3 + "DEPLOY", "G_RG003", "G_RG004", "G_RG006", "G_RG007", "G_RG008", "G_RG009", P3 + "LIMITS", P3 + "BOUNTY"], (1, 2, 4)),
    "L_BETA_STABILITY": ("lead", ["G_BETA"], (6, 8, 14)),
    "L_BOUNTYPUB": ("lead", ["G_BETA", P3 + "BOUNTY"], (8, 12, 20)),
    "G_PUBBETA": ("gate", ["L_BETA_STABILITY", "L_BOUNTYPUB"] + ids(P3, "MIGDRILL", "RECONPROD", "CANARY", "SUPPORT", "TUNE", "TOKENOPS")
                  + ids(P4, "T1", "BOUNTYPUB", "CHAINS", "FRAUD", "MERCHANTOPS"), (1, 2, 4)),
    "L_SLO8": ("lead", ["G_PUBBETA"], (8, 10, 16)),
    "G_GA": ("gate", ["L_SLO8", "G_PUBBETA"] + ids(P5, "GA", "OPSMAT", "DOCS", "DRILLS", "SLALEGAL", "SUPPORT247", "RELREADY")
             + ids(P4, "COMPEXP", "SCALE", "DRDRILLS", "MIGGAME"), (2, 3, 6)),
    "L_V11_AUDIT_AVAIL": ("lead", [P6 + "ROUTERV11"], (0, 3, 10)),
    "L_V11_AUDIT_RUN": ("lead", ["L_V11_AUDIT_AVAIL"], (6, 9, 14)),
    "W_V11_AUDIT_SUPPORT": ("work", [P6 + "ROUTERV11"], {P6 + "AUDITV11": 0.5}),
    "W_V11_REMEDIATE": ("work", ["L_V11_AUDIT_RUN"], {P6 + "AUDITV11": 0.5}),
    "L_V11_REREVIEW": ("lead", ["W_V11_REMEDIATE"], (2, 3, 5)),
    "N_V11_AUDIT_DONE": ("gate", ["L_V11_REREVIEW", "W_V11_AUDIT_SUPPORT"], (0, 0.5, 1)),
    "L_ADAPTER_AUDIT": ("lead", [P6 + "ADAPTER"], (6, 11, 20)),
    "W_ADAPTER_AUDIT": ("work", [P6 + "ADAPTER"], {P6 + "ADAPTERAUDIT": 1.0}),
    "N_ADAPTER_AUDIT_DONE": ("gate", ["L_ADAPTER_AUDIT", "W_ADAPTER_AUDIT"], (0, 0.5, 1)),
    "G_RG013": ("gate", ["G_GA", "N_V11_AUDIT_DONE", "N_ADAPTER_AUDIT_DONE"] + ids(P6, "FLAGROLLOUT", "OPSV11", "COMPLV11", "QUOTEPAIRS"), (1, 2, 4)),
    "L_V20_AUDIT": ("lead", [P7 + "ROUTERV2", P7 + "GENCONV"], (10, 15, 24)),
    "W_V20_AUDIT": ("work", [P7 + "ROUTERV2", P7 + "GENCONV"], {P7 + "AUDITV2": 1.0}),
    "N_V20_AUDIT_DONE": ("gate", ["L_V20_AUDIT", "W_V20_AUDIT"], (0, 0.5, 1)),
    "L_V20_NOTICE": ("lead", ["N_V20_AUDIT_DONE"], (26, 26, 30)),
    "G_RG014": ("gate", ["L_V20_NOTICE", "G_RG013"] + ids(P7, "MIGCAMP", "USAGE", "TOPUP", "SPLITS", "COMPLV2", "ORACLE", "TOKENLABGEN"), (1, 2, 4)),
    # ---- tier 1 (testnet reference implementation) gates; these nodes exist only in the TRI network (TRI-1 is G_FREEZE) --------------------
    # TRI-2: contracts complete on fork. Same epics as G_CONTRACT_FREEZE without the audit package (no audit in this tier); build and assurance
    #        packages (the vector suites, fork tests and the Foundry fuzz, invariant and mutation suites are assurance work of these epics).
    "G_TRI2": ("gate", [x + ":BA" for x in ids(P1, "CONTRACTS", "PAYONCE", "REVOKE", "MIGRATION", "TOKENREG", "FORK")], (1, 2, 3)),
    # TRI-3: the wallet lab complete (freeze subset W_LAB_MIN = EVL-01..10, then W_LAB_REST: Compatibility Register v0) and the planner paths
    #        (two independent implementations pass all vectors, including the migration, Pay Once and account-policy vectors added in phase 1).
    "G_TRI3": ("gate", ["W_LAB_MIN", "W_LAB_REST"] + [x + ":BA" for x in (P0 + "PLANNER", P1 + "DELEGATION", P1 + "MIGRATION", P1 + "PAYONCE")], (1, 2, 3)),
    # TRI-4: testnet reference exit: both previous gates and ALL work packages (build, assurance and readiness) of every epic in TRI_SCOPE, which
    #        includes the testnet deployment and rehearsal (lifecycle, signer-rotation and emergency-removal drills, account-change re-verification
    #        drill) and the reduced quote, signer and chain-gateway work. Nothing in the tier is work that no gate waits for.
    "G_TRI4": ("gate", ["G_TRI2", "G_TRI3"] + list(TRI_SCOPE), (1, 2, 4)),
}

# ---- roadmap tiers (revision 0.5) -------------------------------------------------------------------------------------
TIER_ORDER = ("TRI", "PMB", "GA")

TRI_ONLY = ("G_TRI2", "G_TRI3", "G_TRI4")                       # nodes that exist only in the TRI network
TRI_SPECIAL = ("L_COUNSEL_NOTICE", "L_PERMIT2_E2", "L_PC_APPROVAL", "W_LAB_MIN", "W_LAB_REST", "G_FREEZE") + TRI_ONLY
TRI_MAP = {"G_CONTRACT_FREEZE": "G_TRI2", "G_RG002": "G_TRI2"}  # an epic that waits for a full-network gate waits for the tier-1 analogue
PMB_TOP = "G_BETA"                                              # tier 2 = the ancestors of this node in the full network

SCEN_MAIN = ("as_organized", "recommended", "recommended_contractors")          # the three scenarios published for every tier
SCEN_ALL = ("as_organized", "as_organized_contractors", "recommended", "recommended_contractors", "recommended_partner", "recommended_own_licence")

# (milestone id, label, node). The three tiers repeat the earlier milestones so that every table is complete.
_PMB_MS = [("Protocol freeze (RG-016)", "G_FREEZE"), ("Phase 0 exit (RG-001)", "G_RG001"), ("Contract audit freeze (audits start)", "G_CONTRACT_FREEZE"),
           ("Phase 1 exit; testnet alpha (RG-002, R3)", "G_RG002"), ("Audits complete (RG-005)", "G_RG005"), ("Security testing (RG-006)", "G_RG006"),
           ("Wallet evidence (RG-003)", "G_RG003"), ("Chain evidence (RG-004)", "G_RG004"), ("Reconciliation (RG-007)", "G_RG007"),
           ("Legal go-live (RG-008)", "G_RG008"), ("Load and operations (RG-009)", "G_RG009"), ("Private beta go (RG-010)", "G_BETA")]
_GA_MS = _PMB_MS + [("Public beta go (RG-011)", "G_PUBBETA"), ("GA go (RG-012)", "G_GA"),
                    ("v1.1 conversion enablement (RG-013), post-GA", "G_RG013"), ("v2.0 enablement (RG-014, indicative), post-GA", "G_RG014")]
TIERS = {
    "TRI": dict(name="Tier 1: testnet reference implementation", top="G_TRI4", scenarios=SCEN_MAIN,
                milestones=[("TRI-1", "Protocol freeze (RG-016)", "G_FREEZE"),
                            ("TRI-2", "Contracts complete on fork (vectors and Foundry suites green)", "G_TRI2"),
                            ("TRI-3", "Wallet-lab Compatibility Register v0 complete; two planner implementations pass all vectors", "G_TRI3"),
                            ("TRI-4", "Testnet reference exit (deployed on a public testnet and rehearsed)", "G_TRI4")]),
    "PMB": dict(name="Tier 2: private mainnet beta", top=PMB_TOP, scenarios=SCEN_MAIN,
                milestones=[(f"PMB-{i}", lab, nid) for i, (lab, nid) in enumerate(_PMB_MS, 1)]),
    "GA": dict(name="Tier 3: full GA platform", top="G_GA", scenarios=SCEN_ALL,
               milestones=[(f"GA-{i}", lab, nid) for i, (lab, nid) in enumerate(_GA_MS, 1)]),
}


# ---- network construction ---------------------------------------------------------------------------------------------
def epic_squads(e):
    sp = SPLIT.get(e["id"])
    if sp:
        return {S[k]: v for k, v in sp.items()}
    return {e["squad"]: 1.0}


def nominal(node):
    """Nominal duration in weeks at full strength (no ramp, no factors)."""
    if node["kind"] == "wp":
        return max((w / (HC[sq] * FOCUS) for sq, w in node["work"].items()), default=0.0)
    s = node["spec"]
    if node["kind"] == "mix":
        return 0.5 * s[1][1] + 0.5 * s[2][1]
    return s[1]


def ancestors(edges, top):
    """All nodes from which `top` can be reached through the edge list (any edge type), including `top`."""
    preds = {}
    for p, s, *_ in edges:
        preds.setdefault(s, []).append(p)
    keep, stack = {top}, [top]
    while stack:
        n = stack.pop()
        for p in preds.get(n, ()):
            if p not in keep:
                keep.add(p)
                stack.append(p)
    return keep


def build(scope="GA"):
    """Returns (nodes, edges, dropped) of the scoped network. Node: kind, work, spec, epic, grp. Edge: (pred, succ, type, lag_weeks, rule).
    GA: the full network. PMB: the full network pruned to the ancestors of PMB_TOP. TRI: a separate network of the epics in TRI_SCOPE
    with scaled work, the tier-1 special nodes and the tier-1 gates."""
    if scope not in TIERS:
        raise SystemExit(f"unknown scope {scope!r}")
    if scope == "PMB":
        nodes, edges, dropped = build("GA")
        keep = ancestors(edges, PMB_TOP)
        return ({n: v for n, v in nodes.items() if n in keep}, [e for e in edges if e[0] in keep and e[1] in keep], dropped)
    tri = scope == "TRI"
    by_id = {e["id"]: e for e in model.EPICS}
    epic_frac = dict(TRI_SCOPE) if tri else {eid: 1.0 for eid in GATING}
    special = {k: SPECIAL[k] for k in TRI_SPECIAL} if tri else {k: v for k, v in SPECIAL.items() if k not in TRI_ONLY}
    for eid in epic_frac:
        if eid not in by_id:
            raise SystemExit(f"scope {scope}: unknown epic {eid}")
        if eid not in GATING:
            raise SystemExit(f"scope {scope}: {eid} is not a gating epic")
    nodes, edges, dropped = {}, [], set()
    epic_wps = {}

    def add_wp(nid, work, epic=None, grp=None):
        nodes[nid] = dict(kind="wp", work=work, spec=None, epic=epic, grp=grp)

    # epics -> work packages (work scaled by the scope fraction)
    for eid in GATING:
        if eid not in epic_frac:
            continue
        e = by_id[eid]
        sq = epic_squads(e)
        wps = {}
        for g, share in stories.wp_shares(e).items():
            nid = f"{eid}#{g}"
            add_wp(nid, {s: e["pw"] * epic_frac[eid] * share * x for s, x in sq.items()}, eid, g)
            wps[g] = nid
        epic_wps[eid] = wps
    # special nodes
    for nid, (kind, deps, spec) in special.items():
        if kind in ("work", "extra"):
            w = {}
            if kind == "work":
                for eid, frac in spec.items():
                    for s, x in epic_squads(by_id[eid]).items():
                        w[s] = w.get(s, 0.0) + by_id[eid]["pw"] * x * frac
            else:
                for k, v in spec.items():
                    w[S[k]] = w.get(S[k], 0.0) + v
            add_wp(nid, w)
        else:
            nodes[nid] = dict(kind=kind, work=None, spec=spec, epic=None, grp=None)
    dur = {n: nominal(v) for n, v in nodes.items()}

    def edge(p, s, typ, lag, rule):
        edges.append((p, s, typ, round(lag, 3), rule))

    # intra-epic edges
    for eid, wps in epic_wps.items():
        b, a, r = wps.get("B"), wps.get("A"), wps.get("R")
        if b and a:
            edge(b, a, INTRA_B_TO_A[0], INTRA_B_TO_A[1] * dur[b], "intra B->A")
            edge(b, a, "FF", INTRA_B_TO_A_FF, "intra B->A finish")
        if b and r:
            edge(b, r, INTRA_B_TO_R[0], INTRA_B_TO_R[1] * dur[b], "intra B->R")
        if a and r:
            edge(a, r, "FF", 0.0, "intra A->R finish")
    def in_scope(d):
        return d in epic_wps or d in special

    def scoped(eid, deps):
        """Tier 1 only: keep a dependency that exists in the TRI network, map a full-network gate to its tier-1 analogue, drop the rest."""
        out = []
        for d in deps:
            d = TRI_MAP.get(d, d)
            if in_scope(d):
                if d not in out:
                    out.append(d)
            else:
                dropped.add((eid, d))
        return out

    # epic dependencies (data deps, REPLACE, ADD, phase default)
    for eid in GATING:
        if eid not in epic_frac:
            continue
        e = by_id[eid]
        if eid in REPLACE:
            deps = list(REPLACE[eid])
        else:
            deps = []
            for tok in str(e["deps"]).split(";"):
                tok = tok.strip()
                if not tok or tok == "-":
                    continue
                key = tok.split()[0]
                if key.startswith("EPIC-"):
                    if key in GATING:
                        deps.append(key)
                    else:
                        dropped.add((eid, key))
                elif key in TOKEN:
                    deps.append(TOKEN[key])
                else:
                    dropped.add((eid, key))
        for d in ADD.get(eid, []):
            if d not in deps:
                deps.append(d)
        if tri:
            deps = scoped(eid, deps)
        if not deps and e["phase"] in PHASE_DEFAULT:
            deps = [PHASE_DEFAULT[e["phase"]]]
            if tri:
                deps = scoped(eid, deps)
        sb = epic_wps[eid].get("B")
        sa = epic_wps[eid].get("A")
        for d in deps:
            if d in epic_wps:
                x = by_id[d]
                xb, xa = epic_wps[d].get("B"), epic_wps[d].get("A")
                if (d, eid) in EDGE_OVERRIDE:
                    typ, frac = EDGE_OVERRIDE[(d, eid)]
                    edge(xb, sb, typ, frac * dur[xb], f"override {d}->{eid}")
                elif x["profile"] in DECISION_PROFILES:
                    edge(xb, sb, CROSS_DECISION[0], CROSS_DECISION[1] * dur[xb], f"cross: {x['profile']} predecessor -> FS")
                else:
                    edge(xb, sb, CROSS_BUILD[0], CROSS_BUILD[1] * dur[xb], f"cross: {x['profile']} predecessor -> SS")
                    if xa and sa:
                        edge(xa, sa, "FF", CROSS_ASSURE_FF, "cross: assurance finish")
            elif d in special:
                edge(d, sb, "FS", 0.0, "gate or wait -> epic")
            else:
                raise SystemExit(f"{eid}: unknown dependency {d}")
    # special-node dependencies
    for nid, (kind, deps, spec) in special.items():
        for d in deps:
            d, _, groups = d.partition(":")
            if d in epic_wps:
                for g, wp in epic_wps[d].items():
                    if groups and g not in groups:
                        continue
                    rule = {"": "epic complete -> gate or work", "BA": "epic build and assurance complete -> gate",
                            "B": "epic build package complete -> gate or wait"}[groups]
                    edge(wp, nid, "FS", 0.0, rule)
            elif d in special:
                edge(d, nid, "FS", 0.0, "node -> node")
            else:
                raise SystemExit(f"{nid}: unknown dependency {d} in scope {scope}")
    for p, s, typ, lag, rule in edges:
        if p not in nodes or s not in nodes:
            raise SystemExit(f"edge references unknown node: {p} -> {s}")
    # drop duplicate edges (same pair and type keep the largest lag)
    best = {}
    for p, s, typ, lag, rule in edges:
        k = (p, s, typ)
        if k not in best or lag > best[k][3]:
            best[k] = (p, s, typ, lag, rule)
    edges = sorted(best.values())
    if tri:
        # every tier-1 node must lead to the tier-1 exit: scoped work that no gate waits for would silently be costless to the dates
        orphans = sorted(set(nodes) - ancestors(edges, TIERS["TRI"]["top"]))
        if orphans:
            raise SystemExit("tier 1 nodes that no gate waits for: " + ", ".join(orphans[:12]))
    return nodes, edges, dropped


_NETS = {}


def net(scope="GA"):
    """The scoped network with its precomputed adjacency (cached per scope)."""
    if scope not in _NETS:
        nodes, edges, dropped = build(scope)
        start_in = {n: [] for n in nodes}      # n -> [(pred, type, lag)] for FS and SS
        ff_in = {n: [] for n in nodes}         # n -> [(pred, lag)]
        out_fs = {n: [] for n in nodes}
        out_ss = {n: [] for n in nodes}
        for p, s, typ, lag, _ in edges:
            if typ == "FF":
                ff_in[s].append((p, lag))
            else:
                start_in[s].append((p, typ, lag))
                (out_fs if typ == "FS" else out_ss)[p].append((s, lag))
        order = _topo(nodes, edges)
        tail = _tails(nodes, edges, order)
        for _, _, nid in TIERS[scope]["milestones"]:
            if nid not in nodes:
                raise SystemExit(f"milestone node {nid} is not in the {scope} network")
        _NETS[scope] = dict(scope=scope, nodes=nodes, edges=edges, dropped=dropped, start_in=start_in, ff_in=ff_in, out_fs=out_fs, out_ss=out_ss,
                            order=order, tail=tail)
    return _NETS[scope]


def _topo(nodes, edges):
    indeg = {n: 0 for n in nodes}
    kids = {n: [] for n in nodes}
    for p, s, *_ in edges:
        indeg[s] += 1
        kids[p].append(s)
    out, stack = [], sorted(n for n, d in indeg.items() if d == 0)
    while stack:
        n = stack.pop()
        out.append(n)
        for c in kids[n]:
            indeg[c] -= 1
            if indeg[c] == 0:
                stack.append(c)
    if len(out) != len(nodes):
        raise SystemExit("dependency cycle among: " + ", ".join(sorted(set(nodes) - set(out))[:12]))
    return out


def _tails(nodes, edges, order):
    """Longest remaining path from the start of a node (used only to prioritise squad queues)."""
    d = {n: nominal(v) for n, v in nodes.items()}
    succ = {n: [] for n in nodes}
    for p, s, typ, lag, _ in edges:
        succ[p].append((s, typ, lag))
    tail = {}
    for n in reversed(order):
        t = d[n]
        for s, typ, lag in succ[n]:
            if typ == "FS":
                t = max(t, d[n] + lag + tail[s])
            elif typ == "SS":
                t = max(t, lag + tail[s])
        tail[n] = t
    return tail


# ---- mechanics -----------------------------------------------------------------------------------------------------------
def _g(t, r0, T):
    """Cumulative capacity fraction of a squad with a linear ramp r0 -> 1 over T weeks (per unit of full-strength rate)."""
    if t <= T:
        return r0 * t + (1 - r0) * t * t / (2 * T)
    return r0 * T + (1 - r0) * T / 2 + (t - T)


def _solve(start, work, k_base, r0, T, k_fast=0.0):
    """End time when `work` person-weeks have been done starting at `start`."""
    if k_fast == 0.0:
        target = _g(start, r0, T) + work / k_base
        gT = _g(T, r0, T)
        if target <= gT:
            a = (1 - r0) / (2 * T)
            if a == 0:
                return target / r0
            return (-r0 + math.sqrt(r0 * r0 + 4 * a * target)) / (2 * a)
        return T + (target - gT)
    lo, hi = start, start + 600
    base = k_base * _g(start, r0, T) + k_fast * start + work
    for _ in range(40):
        mid = (lo + hi) / 2
        if k_base * _g(mid, r0, T) + k_fast * mid >= base:
            hi = mid
        else:
            lo = mid
    return hi


def tri(rng, a, m, b):
    return rng.triangular(a, b, m)


FIRST_BOOST = 1000.0       # weeks added to the queue priority of the nodes a scenario names in `first` (queue-rule sensitivity)
_FIRST = {}


def _first_nodes(scope, prefixes):
    """Nodes of the scoped network whose id starts with one of `prefixes` (served first in a squad queue); empty when `prefixes` is None."""
    if not prefixes:
        return frozenset()
    key = (scope, tuple(prefixes))
    if key not in _FIRST:
        _FIRST[key] = frozenset(n for n in net(scope)["nodes"] if n.startswith(tuple(prefixes)))
    return _FIRST[key]


def one_run(rng, scen, trace=None, scope="GA"):
    N = net(scope)
    nodes, tail = N["nodes"], N["tail"]
    start_in, ff_in, out_fs, out_ss = N["start_in"], N["ff_in"], N["out_fs"], N["out_ss"]
    T = tri(rng, *T_RAMP)
    gf = tri(rng, *G_FACTOR)
    hc_scen = scen.get("hc", {})
    fast = scen.get("fast_extra", {})
    prio = scen.get("priority", model.PRIORITY_SQUADS)
    first = _first_nodes(scope, scen.get("first"))     # staffing rule of the queue-rule sensitivity only; empty for every published scenario
    unmet = {n: len(start_in[n]) for n in nodes}
    rel_t, drv = {}, {}
    start_t, done_t, fin_t = {}, {}, {}
    ff_left, ff_waiters = {}, {}
    parts = {}
    free = {sq: 0.0 for sq in HC}
    last = {sq: None for sq in HC}
    queue = {sq: [] for sq in HC}
    events = []
    seq = [0]

    def push(t, kind, n, extra=None):
        seq[0] += 1
        heapq.heappush(events, (t, seq[0], kind, n, extra))

    def start(n, t):
        if n in start_t:
            return
        start_t[n] = t
        for s, lag in out_ss[n]:
            push(t + lag, "sat", s, n)

    def release(n, t):
        v = nodes[n]
        drv[n] = rel_t.get(n, (0.0, None))[1]
        k = v["kind"]
        if k == "wp":
            if not v["work"]:
                start(n, t)
                work_done(n, t)
                return
            parts[n] = dict(left=len(v["work"]), best=t)
            for sq, w in v["work"].items():
                seq[0] += 1
                heapq.heappush(queue[sq], (-(tail[n] + (FIRST_BOOST if n in first else 0.0)), seq[0], n, w, t))
        else:
            start(n, t)
            if k == "lead":
                s = v["spec"]
                reps = s[3] if len(s) > 3 else 1
                d = max(tri(rng, *s[:3]) for _ in range(reps))
            elif k == "mix":
                p, a, b = v["spec"]
                if scen.get("license") == "partner":
                    p = 1.0
                elif scen.get("license") == "own":
                    p = 0.0
                d = tri(rng, *(a if rng.random() < p else b))
            else:
                d = tri(rng, *v["spec"])
            push(t + d, "wd", n)

    def work_done(n, t):
        done_t[n] = t
        pend = [(p, lag) for p, lag in ff_in[n] if p not in fin_t]
        if pend:
            ff_left[n] = len(pend)
            for p, _ in pend:
                ff_waiters.setdefault(p, []).append(n)
        else:
            finalize(n, t)

    def finalize(n, t):
        fin, who = t, None
        for p, lag in ff_in[n]:
            if fin_t[p] + lag > fin:
                fin, who = fin_t[p] + lag, p
        if who is not None:
            drv[n] = who
        if fin > t + 1e-12:
            push(fin, "fin", n)
        else:
            finish(n, t)

    def finish(n, t):
        fin_t[n] = t
        for s, lag in out_fs[n]:
            push(t + lag, "sat", s, n)
        for w in ff_waiters.pop(n, []):
            ff_left[w] -= 1
            if ff_left[w] == 0:
                finalize(w, done_t[w])

    def sat(n, t, pred):
        unmet[n] -= 1
        if n not in rel_t or t >= rel_t[n][0]:
            rel_t[n] = (t, pred)
        if unmet[n] == 0:
            release(n, rel_t[n][0])

    def launch(t):
        for sq in HC:
            while free[sq] <= t and queue[sq]:
                _, _, n, w, rdy = heapq.heappop(queue[sq])
                r0 = R0_PRIORITY if sq in prio else R0_GENERAL
                e = _solve(t, w * gf * tri(rng, *N_FACTOR), hc_scen.get(sq, HC[sq]) * FOCUS, r0, T, fast.get(sq, 0) * FOCUS)
                if trace is not None:
                    trace.append((sq, n, rdy, t, e))
                waited = t > rdy + 1e-9
                free[sq] = e
                start(n, t)
                push(e, "part", n, (sq, last[sq] if waited and last[sq] else None))
                last[sq] = n

    for n in N["order"]:
        if unmet[n] == 0:
            release(n, 0.0)
    t = 0.0
    while True:
        launch(t)
        if not events:
            break
        t = events[0][0]
        while events and events[0][0] <= t + 1e-12:
            et, _, kind, n, extra = heapq.heappop(events)
            if kind == "sat":
                sat(n, et, extra)
            elif kind == "part":
                pt = parts[n]
                pt["left"] -= 1
                if et >= pt["best"]:
                    pt["best"] = et
                    if extra[1] is not None:
                        drv[n] = extra[1]
                if pt["left"] == 0:
                    work_done(n, pt["best"])
            elif kind == "wd":
                work_done(n, et)
            else:
                finish(n, et)
        launch(t)
    return fin_t, drv


def percentile(xs, q):
    xs = sorted(xs)
    k = (len(xs) - 1) * q
    f, c = math.floor(k), math.ceil(k)
    return xs[f] if f == c else xs[f] + (xs[c] - xs[f]) * (k - f)


# squad sizes found by `rebalance()` (greedy search, total 50, floors in FLOORS); set after running `python -I schedule_model.py rebalance`
RECOMMENDED_HC = {"Leadership and Program": 4, "Product and Design": 4, "Protocol and Contracts": 8, "Payments Core": 11,
                  "Chain Infrastructure": 3, "Checkout and Merchant Experience": 4, "Platform, SRE and Security Engineering": 6,
                  "Quality": 3, "Compliance, Risk and Privacy": 3, "DevEx, Support and Partnerships": 4}
RECOMMENDED_PRIORITY = sorted(set(model.PRIORITY_SQUADS) | {"Payments Core"})


def make_scenarios():
    rec = dict(RECOMMENDED_HC or HC)
    pr = set(RECOMMENDED_PRIORITY)
    return {
        "as_organized": dict(label="As organized in document 07 (squad sizes fixed); licensing mixed", hc={}, fast_extra={}),
        "as_organized_contractors": dict(label="As organized + 3 protocol and 2 core contractors from week 0 (outside the 50)",
                                         hc={}, fast_extra={"Protocol and Contracts": 3, "Payments Core": 2}),
        "recommended": dict(label="Recommended: squad sizes rebalanced (still 50), Payments Core hired first; licensing mixed",
                            hc=rec, priority=pr, fast_extra={}),
        "recommended_contractors": dict(label="Recommended + 7 contractors from week 0 outside the 50 (3 core, 2 protocol, 2 platform)",
                                        hc=rec, priority=pr, fast_extra={"Payments Core": 3, "Protocol and Contracts": 2, "Platform, SRE and Security Engineering": 2}),
        "recommended_partner": dict(label="Recommended; licensing through a licensed partner", hc=rec, priority=pr, license="partner", fast_extra={}),
        "recommended_own_licence": dict(label="Recommended; own licence", hc=rec, priority=pr, license="own", fast_extra={}),
        # queue-rule sensitivity (not a published scenario of the tier tables): every Phase 0 package and the wallet-lab nodes are served first
        "recommended_p0_first": dict(label="Recommended, with every Phase 0 package served first in a squad queue (a staffing rule; sensitivity only)",
                                     hc=rec, priority=pr, fast_extra={}, first=("EPIC-P0-", "W_LAB")),
    }


_SC = {}


def scenarios():
    if not _SC:
        _SC.update(make_scenarios())
    return _SC


def simulate(scen, n=N_RUNS, seed=SEED, keys=None, scope="GA"):
    """n Monte Carlo runs of the scoped network. Returns (end times by node, criticality by epic, criticality by work package); the critical
    chain is traced back from the tier's top gate (G_TRI4, G_BETA or G_GA)."""
    nodes = net(scope)["nodes"]
    top = TIERS[scope]["top"]
    keys = list(nodes) if keys is None else keys
    rng = random.Random(seed)
    ends = {k: [] for k in keys}
    crit_epic = {}
    crit_wp = {}
    for _ in range(n):
        fin, drv = one_run(rng, scen, scope=scope)
        for k in keys:
            ends[k].append(fin[k])
        cur, seen, bases = top, set(), set()
        while cur and cur not in seen:      # squad-queue drivers can in rare cases form a loop; stop at the first repeat
            seen.add(cur)
            bases.add(cur.split("#")[0])
            crit_wp[cur] = crit_wp.get(cur, 0) + 1
            cur = drv.get(cur)
        for b in bases:
            crit_epic[b] = crit_epic.get(b, 0) + 1
    return ends, crit_epic, crit_wp


def freeze_drivers(scen_key, scope, n=1000):
    """Share (percent) of runs in which each prerequisite is the one that determines the finish of G_FREEZE (the driver recorded by one_run)."""
    rng = random.Random(SEED)
    cnt = {}
    for _ in range(n):
        _, drv = one_run(rng, scenarios()[scen_key], scope=scope)
        d = drv.get("G_FREEZE")
        cnt[d] = cnt.get(d, 0) + 1
    return {k: round(v / n * 100, 1) for k, v in sorted(cnt.items(), key=lambda x: (-x[1], str(x[0])))}


def aggregate_only_ga():
    """What an org-wide person-week total says: all GA-scope effort over total org capacity with the same ramp; no queues, no waits."""
    total = sum(e["pw"] for e in model.EPICS if e["phase"] in {"P0", "P1", "P2", "P3", "P4", "P5"})
    return _solve(0.0, total, 50 * FOCUS, R0_GENERAL, T_RAMP[1]), total


def squad_load():
    demand = {sq: 0.0 for sq in HC}
    for e in model.EPICS:
        if e["phase"] not in {"P0", "P1", "P2", "P3", "P4", "P5"}:
            continue
        for sq, share in epic_squads(e).items():
            demand[sq] += e["pw"] * share
    return [(sq, HC[sq], d, d / (HC[sq] * FOCUS)) for sq, d in demand.items()]


def tier_work(scope):
    """Person-weeks of work in the scoped network by squad (work packages and special work nodes; waits and gates carry no work)."""
    w = {sq: 0.0 for sq in HC}
    for v in net(scope)["nodes"].values():
        for sq, x in (v["work"] or {}).items():
            w[sq] += x
    return w


def results(scen_keys=("as_organized",), n=N_RUNS, scope="GA"):
    """P50 / P75 / P90 (weeks from the start of Phase 0) of every milestone node of the tier, by scenario."""
    out = {}
    mnodes = [nid for _, _, nid in TIERS[scope]["milestones"]]
    for k in scen_keys:
        ends, ce, cw = simulate(scenarios()[k], n=n, keys=mnodes, scope=scope)
        out[k] = dict(ms={nid: tuple(round(percentile(ends[nid], q)) for q in (0.5, 0.75, 0.9)) for nid in mnodes},
                      crit_epic=ce, crit_wp=cw, n=n)
    return out


def sensitivity(extra=2, n=1000):
    keys = ["G_CONTRACT_FREEZE", "G_RG002", "G_BETA", "G_GA"]
    base = simulate(dict(hc={}, fast_extra={}), n=n, keys=keys)[0]
    b = {k: percentile(base[k], 0.5) for k in keys}
    rows = []
    for sq in HC:
        r = simulate(dict(hc={}, fast_extra={sq: extra}), n=n, keys=keys)[0]
        rows.append((sq, {k: percentile(r[k], 0.5) - b[k] for k in keys}))
    return b, rows


FLOORS = {"Leadership and Program": 4, "Product and Design": 4, "Protocol and Contracts": 6, "Payments Core": 8,
          "Chain Infrastructure": 3, "Checkout and Merchant Experience": 3, "Platform, SRE and Security Engineering": 4,
          "Quality": 3, "Compliance, Risk and Privacy": 3, "DevEx, Support and Partnerships": 2}


def _mean_ga(hc, prio, n, seed=SEED):
    ends, _, _ = simulate(dict(hc=hc, fast_extra={}, priority=prio), n=n, seed=seed, keys=["G_GA"])
    return sum(ends["G_GA"]) / n


def rebalance(max_moves=12, n=600, log=print):
    """Greedy search over squad sizes (total fixed at 50, per-squad floors) minimising the mean GA date; Payments Core is hired first."""
    prio = set(model.PRIORITY_SQUADS) | {"Payments Core"}
    hc = dict(HC)
    cur = _mean_ga(hc, prio, n)
    log(f"start mean GA W{cur:.1f}")
    for it in range(max_moves):
        gain, loss = {}, {}
        for sq in hc:
            gain[sq] = cur - _mean_ga(dict(hc, **{sq: hc[sq] + 1}), prio, n)
            if hc[sq] > FLOORS[sq]:
                loss[sq] = _mean_ga(dict(hc, **{sq: hc[sq] - 1}), prio, n) - cur
        best = None
        for r in sorted(gain, key=gain.get, reverse=True)[:3]:
            for d in sorted(loss, key=loss.get):
                if d == r:
                    continue
                trial = dict(hc, **{r: hc[r] + 1, d: hc[d] - 1})
                val = _mean_ga(trial, prio, n)
                if val < cur - 0.3 and (best is None or val < best[0]):
                    best = (val, trial, r, d)
                break
        if best is None:
            log("no further improving move")
            break
        cur, hc = best[0], best[1]
        log(f"move 1 from {best[3]} to {best[2]} -> mean GA W{cur:.1f}")
    return hc, prio


def input_hash():
    import hashlib

    def part(scope):
        N = net(scope)
        return dict(nodes={n: dict(kind=v["kind"], spec=repr(v["spec"]), work={k: round(x, 3) for k, x in (v["work"] or {}).items()})
                           for n, v in sorted(N["nodes"].items())},
                    edges=[list(e[:4]) for e in N["edges"]])

    blob = json.dumps(dict(
        scopes={sc: part(sc) for sc in TIER_ORDER},
        tiers={sc: dict(top=t["top"], scenarios=list(t["scenarios"]), milestones=[list(m) for m in t["milestones"]]) for sc, t in TIERS.items()},
        tri_scope=TRI_SCOPE, tri_map=TRI_MAP,
        params=dict(R0_GENERAL=R0_GENERAL, R0_PRIORITY=R0_PRIORITY, T_RAMP=T_RAMP, G_FACTOR=G_FACTOR, N_FACTOR=N_FACTOR, FOCUS=FOCUS,
                    N_RUNS=N_RUNS, SEED=SEED, HC=HC, REC=RECOMMENDED_HC, PRIO=RECOMMENDED_PRIORITY),
        scen=make_scenarios()),
        sort_keys=True, default=lambda o: sorted(o) if isinstance(o, (set, frozenset)) else str(o))
    return hashlib.sha256(blob.encode()).hexdigest()


def edge_stats(scope="GA"):
    N = net(scope)
    by_type = {}
    by_rule = {}
    for _, _, typ, _, rule in N["edges"]:
        by_type[typ] = by_type.get(typ, 0) + 1
        key = rule.split(" ")[0] if rule.startswith("override") else rule
        by_rule[(typ, key)] = by_rule.get((typ, key), 0) + 1
    return by_type, by_rule


def graph_info(scope):
    N = net(scope)
    by_type, _ = edge_stats(scope)
    work = tier_work(scope)
    return dict(nodes=len(N["nodes"]), wps=sum(1 for v in N["nodes"].values() if v["kind"] == "wp"), edges=len(N["edges"]), by_type=by_type,
                work_pw=round(sum(work.values()), 1), work_by_squad={sq: round(x, 1) for sq, x in work.items()})


def write_edges(path):
    """Every dependency of the three networks. The GA rows are the full network (tiers `PMB;GA` for an edge that is also in the pruned
    private-beta network, `GA` otherwise); the TRI rows are the separate tier-1 network (its lags come from the scaled durations)."""
    G, P, T = net("GA"), net("PMB"), net("TRI")
    in_pmb = {(p, s, typ) for p, s, typ, _, _ in P["edges"]}
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["predecessor", "successor", "type", "lag_weeks", "rule", "predecessor_nominal_weeks", "tiers"])
        for N, tiers_of in ((G, lambda p, s, typ: "PMB;GA" if (p, s, typ) in in_pmb else "GA"), (T, lambda p, s, typ: "TRI")):
            dur = {n: nominal(v) for n, v in N["nodes"].items()}
            for p, s, typ, lag, rule in N["edges"]:
                w.writerow([p, s, typ, f"{lag:.2f}", rule, f"{dur[p]:.2f}", tiers_of(p, s, typ)])


def write_results(path, log=print):
    out = dict(status=STATUS, hash=input_hash(), n_runs=N_RUNS, seed=SEED, recommended="recommended", scenarios={}, tiers={},
               graph=graph_info("GA"))
    for k, sc in scenarios().items():
        out["scenarios"][k] = dict(label=sc["label"], hc={sq: sc.get("hc", {}).get(sq, HC[sq]) for sq in HC},
                                   priority=sorted(sc.get("priority", model.PRIORITY_SQUADS)))
    for tier in TIER_ORDER:
        T = TIERS[tier]
        log(f"tier {tier}: {len(T['scenarios'])} scenarios x {N_RUNS} runs ...")
        res = results(tuple(T["scenarios"]), scope=tier)
        td = dict(name=T["name"], top=T["top"], milestones=[dict(id=i, label=lab, node=nid) for i, lab, nid in T["milestones"]],
                  graph=graph_info(tier), dropped=sorted([list(x) for x in net(tier)["dropped"]]), scenarios={})
        for k, v in res.items():
            ce = sorted(v["crit_epic"].items(), key=lambda x: -x[1])
            cw = sorted(v["crit_wp"].items(), key=lambda x: -x[1])
            td["scenarios"][k] = dict(ms={nid: list(vals) for nid, vals in v["ms"].items()},
                                      crit={n: round(c / N_RUNS * 100, 1) for n, c in ce[:40]},
                                      crit_wp={n: round(c / N_RUNS * 100, 1) for n, c in cw[:40]})
        out["tiers"][tier] = td
    # queue-rule sensitivity: the recommended squads with every Phase 0 package served first (see `first` in make_scenarios)
    log("queue-rule sensitivity ...")
    out["queue_rule"] = {}
    for tier in TIER_ORDER:
        r = results(("recommended_p0_first",), scope=tier)["recommended_p0_first"]
        out["queue_rule"][tier] = dict(label=scenarios()["recommended_p0_first"]["label"], ms={nid: list(v) for nid, v in r["ms"].items()})
    log("freeze drivers ...")
    out["freeze_drivers"] = {tier: {k: freeze_drivers(k, tier) for k in SCEN_MAIN} for tier in TIER_ORDER}
    ga, tot = aggregate_only_ga()
    out["aggregate"] = dict(ga=round(ga, 1), pw=tot)
    out["squad_load"] = [list(r) for r in squad_load()]
    log("sensitivity ...")
    base, rows = sensitivity()
    out["sensitivity"] = dict(baseline=base, rows=[[sq, d] for sq, d in rows])
    pathlib.Path(path).write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


def load_data():
    import data_p0, data_p1, data_p2, data_p3_p5, data_post  # noqa: F401
    import revisions_v03
    import revisions_v04
    import revisions_v05
    revisions_v03.apply()
    revisions_v04.apply()
    revisions_v05.apply()


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "rebalance":
    load_data()
    hc, prio = rebalance()
    print("RESULT", {k: v for k, v in hc.items()}, "sum", sum(hc.values()), "priority", sorted(prio))
elif __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "--write":
    load_data()
    write_edges(HERE / "dependencies.csv")
    write_results(HERE / "schedule_results.json")
    print("wrote dependencies.csv and schedule_results.json")
elif __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "--edges":
    load_data()
    write_edges(HERE / "dependencies.csv")
    print("wrote dependencies.csv")
elif __name__ == "__main__":
    # quick look: python -I schedule_model.py [TRI|PMB|GA] [runs]; every tier with 800 runs by default
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    load_data()
    tiers = [a for a in sys.argv[1:] if a in TIERS] or list(TIER_ORDER)
    runs = next((int(a) for a in sys.argv[1:] if a.isdigit()), 800)
    for tier in tiers:
        T = TIERS[tier]
        N = net(tier)
        bt, br = edge_stats(tier)
        print(f"\n######## {T['name']} ({tier}): {len(N['nodes'])} nodes; {len(N['edges'])} edges {bt}; work {sum(tier_work(tier).values()):.0f} pw")
        r = results(tuple(T["scenarios"]), n=runs, scope=tier)
        for k, v in r.items():
            print(f"\n== {k}: {scenarios()[k]['label']}")
            for mid, lab, nid in T["milestones"]:
                p50, p75, p90 = v["ms"][nid]
                print(f"  {mid:7s} {lab[:60]:60s} P50 W{p50:>4}  P75 W{p75:>4}  P90 W{p90:>4}")
