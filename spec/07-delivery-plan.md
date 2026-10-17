# 07 — Phased Delivery Plan for a 50-Person Organization (revision 0.5)

| Field | Value |
|---|---|
| Artifact | FP-REL-001 (Parts A.8, A.15, I.6, K.1) |
| Version | 0.5.0 — the roadmap is split into **three tiers** (testnet reference implementation, private mainnet beta, full GA platform), each with its own scope, its own milestones and P50 / P75 / P90 for every milestone and for three scenarios (**exploratory**); v0.5 estimate overlay (+68 pw: shared-allowance migration, account-pin precision, Foundry export of the models, signer-set emergency removal, constants as approved records, pinned Permit2 review); three new explicit waits before the protocol freeze; (0.4: work-package schedule with FS, SS and FF dependencies, `program` restricted to coordination; 0.3: critical-path schedule, epic profiles; the v0.2 GA date is withdrawn) |
| Status | DRAFT — durations are planning estimates, not commitments; the model's inputs are assumptions; nothing here is approved, audited or tested |
| Owner | Technical Program Manager |
| Reviewers | VP Eng, Head of Product, Head of Security, Head of Compliance |
| Dependencies | [03](03-assumptions-decisions-risks.md) (OD-001, OD-008, OD-024…031; ASM-011, ASM-021, ASM-027, ASM-029), [08](08-production-blockers-and-release-gates.md), [09](09-capability-boundaries.md), [11](11-dual-cap-model.md), [12](12-router-lifecycle-and-migration.md), [14](14-protocol-freeze-pack.md), [16](16-freeze-decision-report.md), [17](17-account-compatibility-policy.md) |
| Definition of Done | Every tier has a scope definition (what is in it, what is not, which gates), a milestone list, and a P50/P75/P90 date for every milestone and for the three published scenarios, labeled exploratory, from a work-package model with typed dependencies whose assumptions (including the tier-1 scope fractions and the pre-freeze waits) are stated as editable inputs that need approval; the squads that bind the schedule and the external waits are named; every epic has a profile, an owner, dependencies, risk, estimate, acceptance criteria, evidence and release target, and the story types its profile requires; the generator's checks pass. |

## 1. Planning stance

- **The roadmap has three tiers, and each is its own plan (0.5).** (1) A **testnet reference implementation**: contracts, two independent planner implementations that pass all vectors, the wallet lab, the fork and Foundry suites, a minimal quote, signer and chain-gateway path for testnet, and a rehearsed testnet deployment; no audit, no mainnet, no merchant platform. (2) A **private mainnet beta**: everything that must be true before RG-010. (3) The **full GA platform**: public beta, GA and, after GA, v1.1 and v2.0. Each tier has its own scope, milestones and P50 / P75 / P90 (§3.1, §3.2). A sponsor who needs only the first tier should read only its table; a tier's date is never a promise about the next tier.
- **Estimates are first-order (assume ±40%).** The numbers below come from re-runnable code ([jira/schedule_model.py](jira/schedule_model.py), [jira/build_backlog.py](jira/build_backlog.py)); change an input and regenerate. The schedule is only as good as the inputs in §3.4, and the **tier-1 scope fractions and the three new pre-freeze waits are assumptions that need approval** (§3.4).
- **Capacity is not a schedule.** v0.1 and v0.2 compared an organization-wide person-week total with demand per phase and read the answer as a date. That view ignores that a squad works one thing at a time, that work depends on other work, and that audits, counsel and observation periods take elapsed time no matter how many people are available. v0.3 scheduled the dependency network of the backlog's gating epics with per-squad queues and external waits; v0.4 does it at **work-package level with explicit FS, SS and FF dependencies and lags** instead of a global overlap rule. **The aggregate view for the same scope still says GA is reachable around week 93; the critical-path P50 is far later (§3.2).** The difference is the finding, and every number in §3 is **exploratory**.
- **Security and legal gates are not compressible.** Audit, pen test, legal go-live, router-migration readiness and exercises are gates (RG-005, 006, 008, 009, 015), not tasks that slip silently.
- **No mainnet funds before RG-005.** Dogfood and partner sandbox run on testnets.
- **The plan is built on the version boundaries of [09](09-capability-boundaries.md):** v1.0 ships direct stablecoin settlement with **conversion code absent from Router v1**; v1.1 adds stablecoin conversion as a separately audited router version adopted by opt-in; v2.0 adds general-token conversion after audit and token-lab approval.
- **The backlog is a planning baseline, not implementation-complete.** See §6.3.

## 2. Organization: 50 people, ten squads

Outside the 50: general counsel and external counsel, finance, HR, executive leadership, external auditors and penetration testers, vendors (KYB/AML, RPC, cloud).

| Squad | HC (as organized) | Roles | Owns |
|---|---|---|---|
| Leadership and Program | 5 | Head of Product (1), VP Engineering (1), Head of Security / CISO (1), Technical Program Managers (2) | Direction, gates, risk, schedule |
| Product and Design | 7 | PM Payments and Protocol = *Principal PM* (1), PM Merchant and Platform (1), PM Customer and Wallet (1), Product Designers (2), Design Systems Lead (1), UX Researcher and Content Designer (1) | PRD, journeys, design system, microcopy, accessibility, localization |
| Protocol and Contracts | 7 | Principal Blockchain Architect (1), Solidity Engineers (3, one is *Solidity Lead*), Contract Security Engineers (2), Wallet Protocol / Account-Abstraction Engineer (1) | Parts C and D, planners, token lab, audits liaison |
| Payments Core | 8 | Backend Tech Lead = *Principal Backend Architect* (1), Backend Engineers (5), Ledger / Data Engineers (2) | `fastpay-core`, orchestrator, subscriptions, ledger, migration orchestrator, APIs |
| Chain Infrastructure | 3 | Chain Infra Lead (1), Engineers (2) | `chain-gateway`, `signer`, `quote-signer`, RPC strategy, finality |
| Checkout and Merchant Experience | 5 | Frontend / SDK Lead (1), Engineers (4) | Checkout, portal, dashboards, SDKs |
| Platform, SRE and Security Engineering | 5 | SRE Lead (1), SRE (2), Application Security (1), Detection Engineer (1) | Infrastructure, CI/CD, observability, detections |
| Quality | 3 | QA Lead (1), SDET / Wallet-Lab Engineers (2) | Test program, wallet and token labs |
| Compliance, Risk and Privacy | 4 | Head of Compliance (1), AML and Sanctions Analyst (1), *Risk Lead* (1), Privacy Lead / DPO (1) | KYB, AML, risk policy, limits, privacy |
| DevEx, Support and Partnerships | 3 | Technical Writer / DevRel (1), Support and Incident Operations Lead (1), Partnerships and Merchant Success (1) | Docs, support, partner onboarding |
| **Total** | **50** | | |

### 2.1 Headcount ramp (ASM-021)

A founding team of about 15 is assumed at week 1 (30% of final squad strength; 55% for the squads hired first) growing linearly to full strength in a median of 45 weeks (triangular 30–70 in the model). Six critical hires come first: Principal Blockchain Architect, 2× Contract Security Engineer, Wallet Protocol Engineer, Head of Compliance, Head of Security; contractors bridge gaps (RISK-011). The model treats capacity before a task starts as **lost**: a squad cannot bank idle weeks.

### 2.2 RACI (R responsible, A accountable, C consulted, I informed; one A per row)

| Deliverable family | Head of Product | VP Eng | CISO | Principal Architect | Squad leads | Head of Compliance | QA Lead | TPM |
|---|---|---|---|---|---|---|---|---|
| Vision, PRD, roadmap | A | C | C | C | R | C | I | C |
| Protocol and mandate specification; **protocol freeze (RG-016)** | I | C | C | A | R | I | C | I |
| Contract design and implementation | I | C | C | A | R | I | C | I |
| Audit and pen-test program | I | C | A | R | C | I | C | R |
| Backend platform and ledger | I | A | C | C | R | C | C | I |
| Infrastructure and SRE | I | A | C | I | R | I | C | I |
| Key management and governance | I | C | A | R | C | C | I | I |
| Compliance, AML, privacy | C | I | C | I | C | A | I | I |
| Wallet and token labs, test program | I | C | C | C | R | I | A | C |
| Conversion enablement (v1.1+: C1, C2, rollout switch) | C | C | A | R | R | C | C | I |
| Router lifecycle and migration campaigns | C | C | C | A | R | C | C | R |
| Incident response — security | I | C | A | C | R | C | I | I |
| Incident response — availability | I | A | C | C | R | I | I | I |
| Release gates (evidence assembly) | C | C | C | C | R | C | C | A→R* |

\* The TPM assembles evidence. **Go/no-go is accountable to the Head of Product** with required sign-offs from VP Eng, CISO and Head of Compliance. **CISO has a unilateral no-go on RG-005, RG-006, RG-013, RG-014, RG-016; Head of Compliance on RG-008, RG-013 (legal items), RG-015 (notice duties).**

### 2.3 Squad shape: where the schedule is bound (OD-031)

The squad sizes above follow roles, not demand. The model shows that demand is unevenly spread: the squads that own the contract and core-platform path carry far more work, in full-strength weeks, than the others (table in §3.3). A greedy search over squad sizes (total fixed at 50, a floor per squad, Payments Core hired first) moves people out of Product and Design, Leadership, Compliance and Checkout toward Payments Core, Protocol and Contracts, Platform and DevEx (table in §3.3) and shortens the schedule noticeably; it is labeled **recommended** in the tables. The search was run on the full network under the v0.4 estimates and was **not repeated in 0.5**, so the recommended sizes are not tuned for the v0.5 estimates or for tiers 1 and 2. It is a statement about where the constraint is, not an organization design: it ignores non-gating work (iteration reserves, the data warehouse, extra locales), and cutting Product and Design is risky for that reason. Alternatives that act on the same constraint are contractors on the contract and core path and moving scope out of v1.0. The recommended shape also has costs the model does not charge for: fewer people in Product and Design, Leadership, Compliance and Checkout for the non-gating work and for the readiness paperwork of each phase; Phase 0 exit has a heavy upper tail in both shapes, and in 0.5 the queueing effect behind it reaches the later tiers (§3.5). **The decision belongs to the VP Engineering and Head of Product (OD-031).**

## 3. Schedule

### 3.1 The three roadmap tiers, and how to read the schedule

**All results in this section are EXPLORATORY. Nothing in it is a commitment.** Weeks count from the start of Phase 0. **P50** is the week by which half of the model runs have reached the milestone, **P75** three quarters, **P90** nine tenths. A date is a statement about the model's inputs; it improves only when inputs are replaced by measurements (hiring dates, audit quotes, counsel timelines). A milestone that is not a release gate of [08](08-production-blockers-and-release-gates.md) (TRI-2, TRI-3, TRI-4) is a model milestone: reaching it approves nothing.

The sponsor's instruction of revision 0.5 (item 6) is to split the roadmap into three tiers and to give P50 / P75 / P90 for each milestone. Each tier is simulated **as its own network**, so a tier competes only with its own work for the squads; the tiers nest (the tier-3 network contains the tier-2 network, which is its set of ancestors of RG-010) except that tier 1 is a reduced-fraction network of the same epics (§3.4).

**Tier 1 — testnet reference implementation (`TRI`).**

- *Scope.* The contracts (dual-cap mandates and the consume path, Pay Once, lineage migration with `activateSuccessor` in NORMAL and EMERGENCY mode and the on-chain exposure index, the account pin, the revocation primitives, the quote-signer registry with tombstones); the **reference planner**, with two independent implementations that pass every vector; the **wallet lab** (the freeze subset EVL-01…10 first, then the rest of Compatibility Register v0); the fork and Foundry suites exported from the Python models (vectors, fuzz, invariant, mutation, integer width, timestamp boundary, shared allowance); a **minimal** quote service, signer and chain gateway for testnet use; and a **rehearsed testnet deployment**. It is modeled as a separate network built from the fraction table `TRI_SCOPE` of §3.4.
- *Not in it.* Any audit; any mainnet deployment; any merchant platform (checkout, portal beyond what the rehearsals need, merchant console, SDKs, public API); the orchestrator, subscriptions, ledger, reconciliation and refunds; licensing, KYB and AML operations; fraud and risk controls; support operations; public beta, GA and everything after.
- *Gates.* RG-016 (protocol freeze) is the only release gate of document 08 inside it. TRI-2 to TRI-4 are defined here and are not gates.
- *Milestones.* **TRI-1** protocol freeze (RG-016; the prerequisites of [14](14-protocol-freeze-pack.md) and [16](16-freeze-decision-report.md), plus the three waits of §3.4). **TRI-2** contracts complete on fork: all MIG-TV, RV-T, ZP-T, CAP-TV and ACP-TV vectors and the Foundry fuzz, invariant and mutation suites green. **TRI-3** wallet-lab Compatibility Register v0 complete (EVL-01…10, then the rest of the lab epic) and two independent planner implementations pass all vectors. **TRI-4** testnet reference exit: deployed on a public testnet and rehearsed (router deprecate, migrate and sunset; quote-signer rotation and emergency-removal drills; the account-change re-verification drill).

**Tier 2 — private mainnet beta (`PMB`).**

- *Scope.* The existing network pruned to the packages from which RG-010 can be reached: the protocol freeze, the build and the testnet alpha (RG-002), the contract audit freeze, the two audits (RG-005), the penetration test (RG-006), wallet evidence on the real build (RG-003), chain evidence (RG-004), testnet reconciliation (RG-007), legal go-live (RG-008), load and operations readiness (RG-009), and the mainnet deployment and limits of the beta (R6 in §7). Direct stablecoin settlement only.
- *Not in it.* Public-beta work (additional chains, fraud and merchant operations, T1 surfaces, the public bounty), GA readiness, v1.1 and v2.0, and any package that no gate on the way to RG-010 waits for. Post-beta work no longer competes for squads in this tier's simulation.
- *Gates.* RG-016, RG-001, RG-002, RG-005, RG-006, RG-003, RG-004, RG-007, RG-008, RG-009 and RG-010 (milestones PMB-1 to PMB-12).

**Tier 3 — full GA platform (`GA`).**

- *Scope.* The full network: tier 2, then the public beta (RG-011), sustained SLOs and GA readiness (RG-012), including the migration-readiness evidence for RG-015, and, **after GA and labeled post-GA**, v1.1 conversion enablement (RG-013) and v2.0 (RG-014, indicative). The table repeats the earlier milestones so that it is complete.
- *Not in it.* Nothing that is planned. Non-gating epics (iteration reserves, the data warehouse, extra locales, continuous security work, cost optimisation, white label, partner API) are assumed in all three tiers to use capacity that gating work leaves free.
- *Gates.* RG-016, RG-001 to RG-012, RG-015 readiness; post-GA RG-013 and RG-014.

Size of each tier's network (generated):

<!-- BEGIN:TIERS -->
| Tier | Top gate | Nodes | Work packages | Typed dependencies (FS / SS / FF) | Work in the network (pw) | Share of the GA network | Scenarios simulated |
|---|---|---|---|---|---|---|---|
| Tier 1 — testnet reference implementation (TRI) | TRI-4 (G_TRI4) | 66 | 59 | 210 (116 / 47 / 47) | 451 | 13% | 3 |
| Tier 2 — private mainnet beta (PMB) | PMB-12 (G_BETA) | 183 | 155 | 531 (263 / 135 / 133) | 1394 | 41% | 3 |
| Tier 3 — full GA platform (GA) | GA-14 (G_GA) | 349 | 305 | 976 (445 / 267 / 264) | 3435 | 100% | 6 |

Tier 2 is the GA network pruned to the ancestors of G_BETA. Gating epics with no work package in it (42 epics, 1779 pw): P3-CANARY, P3-MIGDRILL, P3-RECONPROD, P3-SUPPORT, P3-T1START, P3-TOKENOPS, P3-TUNE, P4-BOUNTYPUB, P4-CHAINS, P4-COMPEXP, P4-DRDRILLS, P4-FRAUD, P4-MERCHANTOPS, P4-MIGGAME, P4-SCALE, P4-T1, P4-V11PREP, P5-DOCS, P5-DRILLS, P5-GA, P5-OPSMAT, P5-RELREADY, P5-SLALEGAL, P5-SUPPORT247, P6-ADAPTER, P6-COMPLV11, P6-CONVBACKEND, P6-FLAGROLLOUT, P6-OPSV11, P6-OPTIN, P6-QUOTEPAIRS, P6-ROUTERV11, P6-TOKENLABSTABLE, P7-COMPLV2, P7-GENCONV, P7-MIGCAMP, P7-ORACLE, P7-ROUTERV2, P7-SPLITS, P7-TOKENLABGEN, P7-TOPUP, P7-USAGE. Epics with only some packages in it (20): the R package (readiness) is not simulated for P1-AUDITPREP, P1-CONTRACTS, P1-CORE, P1-FLAGS, P1-FORK, P1-LEDGER, P1-MANDATE, P1-MIGRATION, P1-OBS, P1-PAYONCE, P1-REVOKE, P1-TOKENREG, P2-DEVDOC, P2-MERCHANT, P2-MIGSVC, P2-ORCH, P2-PORTAL, P2-PORTALS, P2-RISKCON, P2-SANDBOX. A package that no gate on the way to RG-010 waits for (typically readiness paperwork) is therefore not simulated in tier 2, although it competes for squads in the GA network. 

Tier 1 is a separate network of the epics in `TRI_SCOPE` with scaled work (§3.4); epics not listed there are not in it. Epics not scheduled in any tier (non-gating): EPIC-P2-DOGFOOD, EPIC-P3-ITERATE, EPIC-P4-ITERATE, EPIC-P4-I18N, EPIC-P4-DATA, EPIC-P4-SECCONT, EPIC-P5-PERFCOST, EPIC-P6-REPEAT/VARSUBS/CHAINS2/BAU, EPIC-P7-WHITELABEL/PARTNERAPI/BAU.
<!-- END:TIERS -->

### 3.2 Results by tier (generated)

<!-- BEGIN:SCHEDULE -->
**EXPLORATORY — not a commitment.** Three roadmap tiers, each a Monte Carlo over its own network at work-package level (sizes in §3.1): 3,000 runs per scenario, seed 20261013. P50 / P75 / P90 are the weeks (from the start of Phase 0) by which that fraction of runs has reached the milestone; the inputs are the assumptions of §3.4. Tiers 1 and 2 are simulated for the three scenarios below; tier 3 for six (the table after the three tiers). Each tier is simulated alone and competes only with its own work for the squads, so a tier's dates are neither the sum nor the continuation of another tier's.

Headline: the last milestone of each tier (P50 / P75 / P90):

| Tier | Last milestone | As organized | Recommended squads | Recommended + 7 contractors |
|---|---|---|---|---|
| Tier 1 — testnet reference implementation (TRI) | TRI-4 Testnet reference exit (deployed on a public testnet and rehearsed) | W84 / W90 / W96 | **W76** / W82 / W88 | W66 / W71 / W75 |
| Tier 2 — private mainnet beta (PMB) | PMB-12 Private beta go (RG-010) | W149 / W162 / W173 | **W134** / W148 / W158 | W112 / W123 / W136 |
| Tier 3 — full GA platform (GA) | GA-14 GA go (RG-012) | W211 / W228 / W245 | **W181** / W198 / W213 | W161 / W175 / W190 |

**Tier 1 — testnet reference implementation (TRI)** — P50 / P75 / P90 by scenario:

| ID | Milestone | As organized (P50 / P75 / P90) | Recommended squads (P50 / P75 / P90) | Recommended + 7 contractors (P50 / P75 / P90) |
|---|---|---|---|---|
| TRI-1 | Protocol freeze (RG-016) | W33 / W36 / W38 | **W32** / W34 / W36 | W29 / W31 / W33 |
| TRI-2 | Contracts complete on fork (vectors and Foundry suites green) | W69 / W74 / W79 | **W63** / W68 / W72 | W55 / W59 / W63 |
| TRI-3 | Wallet-lab Compatibility Register v0 complete; two planner implementations pass all vectors | W77 / W83 / W88 | **W71** / W76 / W81 | W61 / W66 / W70 |
| TRI-4 | Testnet reference exit (deployed on a public testnet and rehearsed) | W84 / W90 / W96 | **W76** / W82 / W88 | W66 / W71 / W75 |

**Tier 2 — private mainnet beta (PMB)** — P50 / P75 / P90 by scenario:

| ID | Milestone | As organized (P50 / P75 / P90) | Recommended squads (P50 / P75 / P90) | Recommended + 7 contractors (P50 / P75 / P90) |
|---|---|---|---|---|
| PMB-1 | Protocol freeze (RG-016) | W33 / W36 / W38 | **W32** / W34 / W36 | W29 / W32 / W34 |
| PMB-2 | Phase 0 exit (RG-001) | W74 / W79 / W85 | **W66** / W72 / W78 | W37 / W42 / W63 |
| PMB-3 | Contract audit freeze (audits start) | W74 / W79 / W84 | **W68** / W73 / W77 | W59 / W63 / W67 |
| PMB-4 | Phase 1 exit; testnet alpha (RG-002, R3) | W97 / W105 / W112 | **W84** / W92 / W98 | W63 / W70 / W79 |
| PMB-5 | Audits complete (RG-005) | W107 / W114 / W120 | **W100** / W106 / W112 | W89 / W94 / W99 |
| PMB-6 | Security testing (RG-006) | W135 / W146 / W155 | **W113** / W123 / W132 | W92 / W99 / W107 |
| PMB-7 | Wallet evidence (RG-003) | W121 / W131 / W140 | **W107** / W117 / W126 | W93 / W100 / W108 |
| PMB-8 | Chain evidence (RG-004) | W74 / W80 / W100 | **W74** / W86 / W96 | W81 / W87 / W92 |
| PMB-9 | Reconciliation (RG-007) | W140 / W152 / W162 | **W126** / W138 / W148 | W103 / W114 / W126 |
| PMB-10 | Legal go-live (RG-008) | W81 / W89 / W96 | **W77** / W85 / W94 | W75 / W83 / W93 |
| PMB-11 | Load and operations (RG-009) | W147 / W159 / W170 | **W132** / W145 / W156 | W109 / W121 / W134 |
| PMB-12 | Private beta go (RG-010) | W149 / W162 / W173 | **W134** / W148 / W158 | W112 / W123 / W136 |

**Tier 3 — full GA platform (GA)** — P50 / P75 / P90 by scenario:

| ID | Milestone | As organized (P50 / P75 / P90) | Recommended squads (P50 / P75 / P90) | Recommended + 7 contractors (P50 / P75 / P90) |
|---|---|---|---|---|
| GA-1 | Protocol freeze (RG-016) | W33 / W36 / W38 | **W32** / W34 / W36 | W29 / W31 / W33 |
| GA-2 | Phase 0 exit (RG-001) | W73 / W79 / W85 | **W66** / W72 / W77 | W37 / W42 / W62 |
| GA-3 | Contract audit freeze (audits start) | W73 / W79 / W84 | **W67** / W73 / W77 | W59 / W63 / W67 |
| GA-4 | Phase 1 exit; testnet alpha (RG-002, R3) | W97 / W106 / W112 | **W83** / W91 / W98 | W63 / W70 / W78 |
| GA-5 | Audits complete (RG-005) | W108 / W116 / W122 | **W101** / W107 / W113 | W89 / W94 / W99 |
| GA-6 | Security testing (RG-006) | W136 / W146 / W156 | **W113** / W124 / W132 | W92 / W99 / W107 |
| GA-7 | Wallet evidence (RG-003) | W121 / W131 / W140 | **W106** / W116 / W125 | W93 / W101 / W107 |
| GA-8 | Chain evidence (RG-004) | W74 / W80 / W92 | **W74** / W87 / W96 | W81 / W87 / W92 |
| GA-9 | Reconciliation (RG-007) | W140 / W152 / W162 | **W126** / W138 / W147 | W103 / W114 / W125 |
| GA-10 | Legal go-live (RG-008) | W81 / W88 / W96 | **W78** / W85 / W94 | W76 / W83 / W94 |
| GA-11 | Load and operations (RG-009) | W147 / W159 / W170 | **W132** / W145 / W156 | W109 / W121 / W133 |
| GA-12 | Private beta go (RG-010) | W149 / W161 / W173 | **W134** / W147 / W158 | W112 / W123 / W135 |
| GA-13 | Public beta go (RG-011) | W166 / W179 / W191 | **W150** / W164 / W174 | W133 / W145 / W155 |
| GA-14 | GA go (RG-012) | W211 / W228 / W245 | **W181** / W198 / W213 | W161 / W175 / W190 |
| GA-15 | v1.1 conversion enablement (RG-013), post-GA | W226 / W245 / W262 | **W206** / W224 / W239 | W181 / W196 / W210 |
| GA-16 | v2.0 enablement (RG-014, indicative), post-GA | W320 / W344 / W367 | **W292** / W315 / W334 | W258 / W277 / W293 |

Tier 3 under all six scenarios (the two licensing scenarios change only the legal path):

| Scenario | Protocol freeze P50 | Phase 1 exit P50 | Private beta P50 | GA P50 | GA P75 | GA P90 |
|---|---|---|---|---|---|---|
| As organized in document 07 (squad sizes fixed); licensing mixed | W33 | W97 | W149 | W211 | W228 | W245 |
| As organized + 3 protocol and 2 core contractors from week 0 (outside the 50) | W29 | W69 | W121 | W183 | W200 | W216 |
| Recommended: squad sizes rebalanced (still 50), Payments Core hired first; licensing mixed | W32 | W83 | W134 | W181 | W198 | W213 |
| Recommended + 7 contractors from week 0 outside the 50 (3 core, 2 protocol, 2 platform) | W29 | W63 | W112 | W161 | W175 | W190 |
| Recommended; licensing through a licensed partner | W32 | W83 | W134 | W181 | W198 | W213 |
| Recommended; own licence | W32 | W83 | W134 | W181 | W198 | W213 |
<!-- END:SCHEDULE -->

### 3.3 Where the schedule is bound (generated)

<!-- BEGIN:LOAD -->
| Squad | Headcount (as organized) | Headcount (recommended) | Tier 1 network work (pw) | Tier 2 network work (pw) | Tier 3 network work (pw) | GA-scope demand, all P0-P5 epics (pw) | Full-strength weeks of that demand, as organized |
|---|---|---|---|---|---|---|---|
| Leadership and Program | 5 | 4 | 0 | 24 | 88 | 88 | 25 |
| Product and Design | 7 | 4 | 0 | 54 | 119 | 277 | 56 |
| Protocol and Contracts | 7 | 8 | 258 | 358 | 1017 | 511 | 104 |
| Payments Core | 8 | 11 | 75 | 409 | 839 | 583 | 104 |
| Chain Infrastructure | 3 | 3 | 25 | 56 | 130 | 56 | 27 |
| Checkout and Merchant Experience | 5 | 4 | 8 | 109 | 249 | 249 | 71 |
| Platform, SRE and Security Engineering | 5 | 6 | 11 | 103 | 346 | 402 | 115 |
| Quality | 3 | 3 | 74 | 141 | 157 | 133 | 63 |
| Compliance, Risk and Privacy | 4 | 3 | 0 | 95 | 300 | 230 | 82 |
| DevEx, Support and Partnerships | 3 | 4 | 0 | 44 | 190 | 190 | 91 |
| **Total** | | | **451** | **1394** | **3435** | | |

Network work counts the work packages and special work nodes each tier simulates (including audit-support, pen-test and wallet-E3 work); the GA-scope column sums all epics of phases P0-P5, scheduled or not.

Sensitivity (tier 3, as organized): change in P50 (weeks) when two people join one squad at full strength from week 0 (baseline P50: contract audit freeze W73, Phase 1 exit W97, private beta W148, GA W209); noise is about ±1.5 weeks:

| Squad (+2 people) | Audit freeze | Phase 1 exit | Private beta | GA |
|---|---|---|---|---|
| Leadership and Program | -0.0 | +0.1 | +0.0 | +1.1 |
| Product and Design | +0.1 | +0.1 | +0.1 | +0.5 |
| Protocol and Contracts | -11.2 | -15.5 | -15.2 | -14.8 |
| Payments Core | +0.0 | -4.3 | -4.7 | -5.2 |
| Chain Infrastructure | +0.0 | -0.4 | +0.1 | +0.3 |
| Checkout and Merchant Experience | -0.2 | +0.2 | +0.2 | +0.2 |
| Platform, SRE and Security Engineering | +0.0 | -0.4 | -0.4 | -0.7 |
| Quality | -5.9 | -4.5 | -7.9 | -8.6 |
| Compliance, Risk and Privacy | +0.1 | -0.3 | -0.5 | +0.1 |
| DevEx, Support and Partnerships | -0.2 | -0.5 | -0.5 | -2.6 |
<!-- END:LOAD -->

### 3.4 The model, its inputs and its limits (generated parameters)

<!-- BEGIN:MODEL -->
**Status of every number in this section: EXPLORATORY.** The model is a tool for seeing which constraints bind, not a forecast.

| Parameter | Value |
|---|---|
| Hiring ramp, final strength reached in (weeks, triangular low / mode / high) | 30 / 45 / 70 |
| Start-up strength: share of final squad strength at week 0 (general / squads hired first) | 0.3 / 0.55 |
| Squads hired first (recommended scenario adds Payments Core) | Chain Infrastructure / Protocol and Contracts / Quality |
| Focus factor (meetings, support, review) | 0.7 |
| Run-wide effort factor (low / mode / high) | 0.9 / 1.0 / 1.45 |
| Per work package and squad effort factor (low / mode / high) | 0.9 / 1.0 / 1.35 |
| Runs per scenario | 3,000 |
| Graph, tier 1 (TRI) | 66 nodes (59 work packages), 210 typed dependencies (116 FS, 47 SS, 47 FF) |
| Graph, tier 2 (PMB) | 183 nodes (155 work packages), 531 typed dependencies (263 FS, 135 SS, 133 FF) |
| Graph, tier 3 (GA) | 349 nodes (305 work packages), 976 typed dependencies (445 FS, 267 SS, 264 FF) |

**Scoped networks (revision 0.5).** The model runs three networks. Tier 3 (GA) is the full network. Tier 2 (PMB) is the full network pruned to the ancestors of G_BETA (any dependency type), so work after the private-beta decision no longer competes for squads in that simulation. Tier 1 (TRI) is a separate network: the epics of `TRI_SCOPE` with their person-weeks scaled by the stated fraction, the wallet lab through its two special nodes, the tier-1 gates G_TRI2 to G_TRI4 and G_FREEZE; a dependency on a gate or epic outside the tier is dropped, except that a wait for the audit freeze or the testnet-alpha gate becomes a wait for G_TRI2 (`TRI_MAP`). The simulation core is the same for all three and is deterministic for a fixed seed; the same seed and run count are used for every tier. The squad sizes of the 'recommended' scenario were found for tier 3 under the v0.4 estimates and were not searched again, so they are not tuned for tiers 1 and 2.

**Work packages.** Every gating epic is split by its story types into up to three packages: **B** build (implementation, research task, compliance control, program action), **A** assurance (security, test, observability) and **R** readiness (migration requirement, operational readiness, evidence and sign-off), sized by the story-type weights. Squads do the packages of the epics they own (shares for epics that span squads are in `SPLIT`).

**Dependency types and lags.** Each dependency is explicit; none is a global rule. FS: the successor starts after the predecessor finishes (+ lag). SS: the successor starts after the predecessor starts (+ lag). FF: the successor finishes after the predecessor finishes (+ lag). A lag is in weeks, computed once as a fraction of the predecessor's nominal duration. The rules (every edge, with its rule, is in [jira/dependencies.csv](jira/dependencies.csv)):

| Edge | Type | Lag | Rule |
|---|---|---|---|
| build → assurance, same epic | SS and FF | SS 40% of the build's nominal duration; FF 1 week | Tests and reviews start while the build is under way and finish after it |
| build → readiness, same epic | SS | 70% of the build's nominal duration | Readiness work starts late in the build |
| assurance → readiness, same epic | FF | 0 | Readiness cannot finish before the assurance finishes |
| predecessor epic of profile research, program or compliance → successor build | FS | 0 | A decision, finding or evidence is needed whole |
| any other predecessor epic → successor build | SS | 50% of the predecessor build's nominal duration | The successor consumes an interface once half of it exists |
| predecessor assurance → successor assurance | FF | 0 | A successor's tests cannot finish before the predecessor's |
| epic → gate or wait | FS | 0 | A gate needs the work; design gates (freeze, audit freeze, Phase 1 exit, feature complete) need build and assurance packages, release gates need all three |
| gate or wait → epic | FS | 0 | An epic does not start before the gate it depends on |

Explicit overrides: P0-PROTOSPEC → P1-CONTRACTS FS; P1-CONTRACTS → P1-AUDITPREP FS; P1-CORE → P1-LEDGER SS +30%; P2-SUBS → P2-LOAD SS +60%; P2-RECON → P3-RECONPROD FS; P3-CANARY → P3-TUNE SS +40%.

External waits and reviews (weeks, triangular low / mode / high; random per run):

| Wait | Meaning | Low / mode / high |
|---|---|---|
| L_LEGAL_MEMO | Counsel perimeter memo (RP-09) | 7 / 11 / 19 |
| L_OD001 | Decision on OD-001 after the memo | 2 / 4 / 10 |
| L_COUNSEL_NOTICE | Counsel view on router-migration notice duties (RP-26); freeze-blocking for PC-01 and PC-02 (UX-16) | 6 / 10 / 18 |
| L_PERMIT2_E2 | Second-reviewer sign-off at E2 of the pinned Permit2 source review (PR-01 to PR-16) | 1 / 2 / 4 |
| L_PC_APPROVAL | Approval rounds for the individually approved production-blocking constants (PC-01 to PC-18) | 1 / 2 / 5 |
| L_AUDIT_AVAIL | Wait for audit slots after the contract audit freeze | 0 / 4 / 14 |
| L_AUDIT_RUN | Two audits in parallel: the later of two draws | 8 / 11 / 16 (max of 2 draws) |
| L_REREVIEW | Re-review by the finding firm after remediation | 2 / 3 / 5 |
| L_PENTEST | Penetration test and red team after feature complete | 4 / 6 / 10 |
| L_PENTEST_RETEST | Retest after fixes | 1 / 2 / 4 |
| L_WALLET_FIX | Wallet-lab fixes and retest after the E3 runs | 2 / 4 / 10 |
| L_CHAIN_EVID | Chain evidence: finality observation and chaos tests | 6 / 10 / 18 |
| L_RECON_TESTNET | Testnet reconciliation observation (14 consecutive days plus slack) | 2 / 3 / 5 |
| L_LICENSE | Licensing: licensed-partner route or own licence (mixture) | 50%: 8 / 16 / 30; otherwise 30 / 52 / 90 |
| L_GOLIVE | Go-live review and filings after the licence route is in place | 3 / 5 / 10 |
| L_BETA_STABILITY | Private-beta stability (four consecutive weeks of matched reconciliation, no Sev-1) | 6 / 8 / 14 |
| L_BOUNTYPUB | Public bug bounty and contest or extended review | 8 / 12 / 20 |
| L_SLO8 | Sustained SLOs after the public beta decision | 8 / 10 / 16 |
| L_V11_AUDIT_AVAIL | v1.1: wait for audit slots | 0 / 3 / 10 |
| L_V11_AUDIT_RUN | v1.1: Router v1.1 audit run | 6 / 9 / 14 |
| L_V11_REREVIEW | v1.1: re-review | 2 / 3 / 5 |
| L_ADAPTER_AUDIT | v1.1: adapter audit | 6 / 11 / 20 |
| L_V20_AUDIT | v2.0: audit of the general route class and oracle verifier | 10 / 15 / 24 |
| L_V20_NOTICE | v2.0: minimum notice before a router sunset | 26 / 26 / 30 |

Gate reviews add a short random time after their last prerequisite: G_FREEZE 1/2/3, G_RG001 1/2/4, G_CONTRACT_FREEZE 1/2/3, G_RG002 1/2/4, G_RG005 0.5/1/2, G_FEATURE_COMPLETE 0/0.5/1, and similar for the others (see `SPECIAL` in the model).

**What the model does:** schedules the work packages with the typed dependencies above; gives each squad a capacity curve and a queue (one package at a time, longest remaining path first); adds the waits; reports when each gate is first reached, over many random draws. **What it does not:** model non-gating work (EPIC-P2-DOGFOOD, EPIC-P3-ITERATE, EPIC-P4-ITERATE, EPIC-P4-I18N, EPIC-P4-DATA, EPIC-P4-SECCONT, EPIC-P5-PERFCOST, EPIC-P6-REPEAT/VARSUBS/CHAINS2/BAU, EPIC-P7-WHITELABEL/PARTNERAPI/BAU), assumed to use capacity that gating work leaves free; model people moving between squads or part-time sharing; model hiring beyond the ramp; know the real audit calendar or counsel's timeline; account for scope cuts. A queue discipline that favours the longest path can delay small readiness packages of an early phase, which gives some gates a heavy upper tail (Phase 0 exit in every scenario without extra contractors); with the v0.5 estimates this effect also lies on the chain to the private beta and to GA in a large share of runs (the criticality tables and the queue-rule sensitivity of section 3.5 show how large), so the tier-2 and tier-3 dates contain queueing that a staffing rule would remove. Every one of these is a reason the dates depend on the inputs. The two scenarios that matter most for a decision are the squad shape (OD-031) and the contractor option.
<!-- END:MODEL -->

#### 3.4.1 Tier-1 scope fractions, tier-1 gates and the new pre-freeze waits (ASSUMPTIONS that need approval)

Tier 1 is built from the table below: each listed epic contributes the stated **fraction** of its v0.5 person-weeks, and the wallet lab enters through the special nodes `W_LAB_MIN` (the freeze subset EVL-01…10, taken to be 70% of the lab epic) and `W_LAB_REST` (the other 30%). Every epic that is not listed is out of tier 1. **The fractions are a proposal and are ASSUMPTIONS: the model cannot know how much of the quote service, signer, chain gateway, token registry, testnet operations and deployment preparation a reference implementation needs.** They are editable inputs; approval is requested from the Principal Architect (what a testnet reference implementation needs) and the Head of Product (what the sponsor means by it). Nothing in this table is approved.

<!-- BEGIN:TRISCOPE -->
| Epic | Name | Owner squad | v0.5 estimate (pw) | Fraction in tier 1 (**ASSUMPTION**) | Tier 1 work (pw) |
|---|---|---|---|---|---|
| EPIC-P0-INFRA | Cloud decision and landing-zone skeleton | Platform, SRE and Security Engineering | 6 | 0.50 | 3.0 |
| EPIC-P0-PLANNER | Planner reference implementations and golden vectors (recurring, Pay Once, caps) | Protocol and Contracts | 13 | 1.00 | 13.0 |
| EPIC-P0-PROTO | Fork prototype (spike): mandate lineage, router, quote verification, Pay Once witness | Protocol and Contracts | 13 | 1.00 | 13.0 |
| EPIC-P0-PROTOSPEC | Protocol specification set and freeze pack (mandate lineage, payment, Pay Once, dual cap and quote schema, router lifecycle, delegation revalidation, contracts D.1) | Protocol and Contracts | 30 | 1.00 | 30.0 |
| EPIC-P0-SOURCES | Source verification and research-plan execution (RP-01..08, 13..15, 22, 23, 25) | Protocol and Contracts | 19 | 1.00 | 19.0 |
| EPIC-P0-THREAT | Threat model v1 and security requirements | Platform, SRE and Security Engineering | 8 | 0.50 | 4.0 |
| EPIC-P0-TOKENLAB | Token behavior lab v0 (RP-07) including primary revocation-flow checks (EV-P11) | Protocol and Contracts | 6 | 1.00 | 6.0 |
| EPIC-P0-WALLETLAB (through W_LAB_MIN, then W_LAB_REST) | Wallet compatibility lab v0 (RP-05, RP-06, RP-21, RP-25) | Quality | 24 | 1.00 | 24.0 |
| EPIC-P1-CHAINGW | chain-gateway: multi-RPC quorum, indexer, broadcaster, finality, delegation reads | Chain Infrastructure | 38 | 0.35 | 13.3 |
| EPIC-P1-CONTRACTS | Core contracts v0.9 and Foundry suites (Router v1 without conversion code; mandate lineage; dual caps) | Protocol and Contracts | 126 | 1.00 | 126.0 |
| EPIC-P1-DELEGATION | Account Compatibility Policy engine: modes, on-chain pin, inspection, revalidation, re-verification | Payments Core | 35 | 1.00 | 35.0 |
| EPIC-P1-FORK | Mainnet-fork harness and token-lab integration | Quality | 24 | 1.00 | 24.0 |
| EPIC-P1-MIGRATION | Router lifecycle and lineage migration: orchestrator foundations, successor authorization builder, MigrationPlan, rehearsal harness | Protocol and Contracts | 27 | 1.00 | 27.0 |
| EPIC-P1-PAYONCE | Pay Once protocol (SignatureTransfer witness, entrypoints, planner paths PO-1..PO-6, orchestration) | Protocol and Contracts | 21 | 1.00 | 21.0 |
| EPIC-P1-QUOTE | Quote service, quote-signer deployable and price-bound configuration | Chain Infrastructure | 38 | 0.60 | 22.8 |
| EPIC-P1-REVOKE | Primary revocation flows: portal and SDK flows, plan validator, per-token verification (EV-P11) | Protocol and Contracts | 13 | 1.00 | 13.0 |
| EPIC-P1-SIGNER | signer service with HSM and policy engine (executor and charge-signer key classes) | Chain Infrastructure | 24 | 0.40 | 9.6 |
| EPIC-P1-TOKENREG | Token registry service and console, price bounds, quote-signer set, drift watchers | Protocol and Contracts | 27 | 0.60 | 16.2 |
| EPIC-P2-DEPLOYPREP | Mainnet deployment tooling, ceremony and migration rehearsal (absence proof, lineage lifecycle) | Protocol and Contracts | 27 | 0.60 | 16.2 |
| EPIC-P2-TESTNET | Public testnet alpha operations | Quality | 30 | 0.50 | 15.0 |
| **Total** | 20 epics | | **549** | | **451.1** |

The fractions are editable inputs (`TRI_SCOPE` in [jira/schedule_model.py](jira/schedule_model.py)); changing one changes tier 1 only. Every gating epic not listed (79 of 99, counting the wallet-lab epic that the model schedules through its special nodes) is out of tier 1. The generator rejects a fraction outside (0, 1] and an epic that no tier-1 gate waits for.

Gates of the three networks that this revision adds or changes, with their explicit prerequisites (FS from every listed package; `(build, assurance)` means the readiness package is not needed):

| Gate | Milestone | Waits for | Review time after the last prerequisite (weeks, low / mode / high) |
|---|---|---|---|
| G_FREEZE | TRI-1 Protocol freeze (RG-016) | P0-SOURCES (build, assurance), P0-PROTOSPEC (build, assurance), P0-PLANNER (build, assurance), P0-PROTO (build, assurance), P0-TOKENLAB (build, assurance), W_LAB_MIN, L_COUNSEL_NOTICE, L_PERMIT2_E2, L_PC_APPROVAL | 1 / 2 / 3 |
| G_TRI2 | TRI-2 Contracts complete on fork (vectors and Foundry suites green) | P1-CONTRACTS (build, assurance), P1-PAYONCE (build, assurance), P1-REVOKE (build, assurance), P1-MIGRATION (build, assurance), P1-TOKENREG (build, assurance), P1-FORK (build, assurance) | 1 / 2 / 3 |
| G_TRI3 | TRI-3 Wallet-lab Compatibility Register v0 complete; two planner implementations pass all vectors | W_LAB_MIN, W_LAB_REST, P0-PLANNER (build, assurance), P1-DELEGATION (build, assurance), P1-MIGRATION (build, assurance), P1-PAYONCE (build, assurance) | 1 / 2 / 3 |
| G_TRI4 | TRI-4 Testnet reference exit (deployed on a public testnet and rehearsed) | G_TRI2, G_TRI3 and all packages of every one of the 19 epics of `TRI_SCOPE` | 1 / 2 / 4 |

New explicit waits before the protocol freeze (all three also feed G_FREEZE in tiers 2 and 3; every range is an **ASSUMPTION** that needs a named owner and approval):

| Wait | Meaning | Starts | Low / mode / high (weeks) | Why this range |
|---|---|---|---|---|
| L_COUNSEL_NOTICE | Counsel view on router-migration notice duties (RP-26); freeze-blocking for PC-01 and PC-02 (UX-16) | week 0 (no prerequisite) | 6 / 10 / 18 | Counsel is engaged in week 1 and a written view on notice duties across the launch jurisdictions is a multi-week task; it blocks only the two notice constants, but those are freeze-blocking |
| L_PERMIT2_E2 | Second-reviewer sign-off at E2 of the pinned Permit2 source review (PR-01 to PR-16) | after P0-SOURCES (build) | 1 / 2 / 4 | A second reviewer reads the pinned source after the first review is built; one to four weeks of availability and rework, no external vendor assumed |
| L_PC_APPROVAL | Approval rounds for the individually approved production-blocking constants (PC-01 to PC-18) | after P0-PROTOSPEC (build, assurance) and W_LAB_MIN | 1 / 2 / 5 | Each constant is approved by its named owner after the specification and the lab subset exist; rounds of questions and a second round for contested values |

Which prerequisite determines the finish of the protocol freeze, as a share of 1,000 runs per row (a prerequisite that is not listed never determined it; `#A` is the assurance package of an epic). This shows how much each new wait matters **in this generation**, not how much it could matter:

| Network | Scenario | Prerequisites that determine the freeze |
|---|---|---|
| Tier 1 (TRI) | As organized | EPIC-P0-TOKENLAB#A 100.0% |
| Tier 1 (TRI) | Recommended squads | EPIC-P0-TOKENLAB#A 99.7%, L_PC_APPROVAL 0.3% |
| Tier 1 (TRI) | Recommended + 7 contractors | EPIC-P0-TOKENLAB#A 95.9%, L_PC_APPROVAL 4.1% |
| Tier 2 (PMB) | As organized | EPIC-P0-TOKENLAB#A 100.0% |
| Tier 2 (PMB) | Recommended squads | EPIC-P0-TOKENLAB#A 99.9%, L_PC_APPROVAL 0.1% |
| Tier 2 (PMB) | Recommended + 7 contractors | EPIC-P0-TOKENLAB#A 96.3%, L_PC_APPROVAL 3.7% |
| Tier 3 (GA) | As organized | EPIC-P0-TOKENLAB#A 100.0% |
| Tier 3 (GA) | Recommended squads | EPIC-P0-TOKENLAB#A 99.8%, L_PC_APPROVAL 0.2% |
| Tier 3 (GA) | Recommended + 7 contractors | EPIC-P0-TOKENLAB#A 95.7%, L_PC_APPROVAL 4.3% |
<!-- END:TRISCOPE -->

The three new waits make the freeze date honest about what it depends on: before revision 0.5 the model let the freeze follow the last work package plus a gate review. They feed `G_FREEZE` in all three tiers (so TRI-1, PMB-1 and GA-1 contain them). `L_COUNSEL_NOTICE` is counsel's written view on the notice duties for router migration (RP-26); it blocks the freeze only for the two notice constants PC-01 and PC-02 (UX-16 in [16](16-freeze-decision-report.md)), so it is a wait that starts in week 1 and is tied to no work package. `L_PERMIT2_E2` is the second reviewer's sign-off at E2 of the pinned Permit2 review (PR-01…PR-16), after the build package of `EPIC-P0-SOURCES`. `L_PC_APPROVAL` is the set of approval rounds for the production-blocking constants PC-01…PC-18, each approved individually, after the specification (`EPIC-P0-PROTOSPEC`, build and assurance) and the freeze subset of the wallet lab. Every range is an assumption with no data behind it; a named owner for each is part of the approval requested above. **With these ranges none of the three waits changes a freeze date in this generation:** the table above shows that the token-lab assurance package determines the freeze in 96% or more of the runs and the approval rounds in at most about 4%, and a diagnostic run without the three waits (not a generated table) gives the same P50, P75 and P90 for the protocol freeze with the recommended squads. They are stated because they are real prerequisites, and they would bind if the work got faster (the contractor scenario comes closest) or if the ranges were longer.

### 3.5 Critical paths per tier (qualitative, then generated)

**Tier 1 — testnet reference implementation.**

1. **Specification and freeze (TRI-1):** critical hires → the specification set, the pinned Permit2 review and the planner and token-lab work → three explicit waits that run beside the work (counsel's view on notice duties, the second reviewer's E2 sign-off, the approval rounds of the production-blocking constants) and the freeze subset of the wallet lab (EVL-01…10) → RG-016. A wait binds the freeze only when it finishes after all the work that feeds the freeze; the table at the end of §3.4.1 shows how often each of them does in this generation.
2. **Contracts on fork (TRI-2):** contracts built by the Protocol and Contracts squad (the largest single epic, +16 pw in 0.5) together with Pay Once, migration, revocation, the token registry and the Foundry suites exported from the Python models → all vectors and suites green. The Protocol and Contracts squad binds this path.
3. **Lab and planners (TRI-3):** the rest of the wallet lab (Quality squad) and the account-policy engine, migration and Pay Once planner paths in both planner implementations.
4. **Testnet deployment and rehearsal (TRI-4):** deployment preparation and testnet operation after TRI-2 → the rehearsals (router deprecate, migrate and sunset; quote-signer rotation and emergency-removal drills; account-change re-verification drill) → the reduced quote, signer and chain-gateway work.

**Tier 2 — private mainnet beta (the paths of tier 1, and in addition):**

5. **Contracts and audit:** the path of item 2 → contract audit freeze → two audits in parallel (slot wait, run, remediation, re-review) → RG-005 → mainnet deployment ceremony. Audit slots are booked in P0 (`EPIC-P0-AUDITSEL`) because ASM-011 assumes a long lead time.
6. **Platform:** chain gateway, signers, quote-signer, orchestrator → Phase 1 exit and testnet alpha → platform completion (subscriptions, refunds, reconciliation, migration service, risk console) → feature complete → pen test, fix, retest → RG-006.
7. **Wallet evidence:** lab harness and discovery in P0 (minimum rows for the freeze) → E3 re-runs on the real build during alpha → fixes and retest → RG-003.
8. **Legal:** counsel engaged in week 1 → perimeter memo → OD-001 → licensing or partner path → go-live review → RG-008. It is the longest single external wait, but in every published scenario of this generation the P90 of legal go-live (PMB-10) comes before the P50 of the private beta go (PMB-12), and the licensing scenarios of §3.2 leave the GA date unchanged, so it is not on the critical path here.
9. **Chain evidence:** chain fact sheets → `chain-gateway` with quorum and finality → chaos tests → RG-004.
10. **Financial controls:** ledger, reconciliation and refunds → 14 days of matched reconciliation on testnet → RG-007.
11. **Load and operations:** load tests, runbooks, support preparation and the incident-response and disaster-recovery exercise → RG-009.

**Tier 3 — full GA platform (after the private beta):**

12. **After the private beta:** four consecutive weeks of matched reconciliation and no Sev-1 → public-beta prerequisites (additional chains, fraud and merchant operations, T1 surfaces, public bounty) → RG-011 → sustained SLOs → GA readiness → RG-012.
13. **Migration readiness:** protocol specified (P0) → hooks audited → testnet lifecycle rehearsal (`EPIC-P2-DEPLOYPREP`, in tiers 1 and 2) → mainnet canary drill (`EPIC-P3-MIGDRILL`) → communications game day (`EPIC-P4-MIGGAME`) → RG-015 before any router deprecation.
14. **v1.1 (post-GA):** readiness dossier (`EPIC-P4-V11PREP`) → Router v1.1 build → its own audit and the adapter audit → opt-in migration → RG-013.

Criticality tables (generated): the share of runs in which an epic or gate lies on the chain that determines the tier's last milestone, by scenario. They show which epic to staff or de-scope first; they are not a forecast.

<!-- BEGIN:CRITICALITY -->
**Tier 1 — testnet reference implementation (TRI)** — share of runs in which an epic (any of its work packages) or a gate lies on the chain that determines TRI-4 (G_TRI4); columns: As organized | Recommended squads | Recommended + 7 contractors:

| Epic or gate | As organized | Recommended squads | Recommended + 7 contractors |
|---|---|---|---|
| EPIC-P1-REVOKE | 100% | 100% | 100% |
| EPIC-P0-PROTOSPEC | 100% | 100% | 85% |
| EPIC-P1-MIGRATION | 100% | 100% | 100% |
| G_TRI4 | 100% | 100% | 100% |
| W_LAB_MIN | 100% | 100% | 100% |
| EPIC-P1-PAYONCE | 100% | 100% | 100% |
| EPIC-P1-TOKENREG | 100% | 100% | 100% |
| EPIC-P0-SOURCES | 100% | 100% | 100% |
| EPIC-P1-CONTRACTS | 100% | 100% | 100% |
| EPIC-P0-TOKENLAB | 100% | 100% | 97% |
| EPIC-P0-PROTO | 100% | 100% | 82% |
| EPIC-P0-PLANNER | 100% | 100% | 82% |

Work packages most often on the recommended critical chain: G_TRI4 100%, EPIC-P1-REVOKE#A 100%, EPIC-P1-REVOKE#B 100%, EPIC-P1-PAYONCE#A 100%, EPIC-P1-TOKENREG#B 100%, EPIC-P1-MIGRATION#A 100%, EPIC-P1-PAYONCE#B 100%, EPIC-P1-MIGRATION#B 100%.

**Tier 2 — private mainnet beta (PMB)** — share of runs in which an epic (any of its work packages) or a gate lies on the chain that determines PMB-12 (G_BETA); columns: As organized | Recommended squads | Recommended + 7 contractors:

| Epic or gate | As organized | Recommended squads | Recommended + 7 contractors |
|---|---|---|---|
| G_BETA | 100% | 100% | 100% |
| EPIC-P2-TESTNET | 99% | 99% | 98% |
| W_WALLET_E3 | 99% | 99% | 98% |
| EPIC-P2-LOAD | 99% | 99% | 98% |
| EPIC-P1-FLAGS | 99% | 99% | 98% |
| G_RG009 | 98% | 99% | 98% |
| EPIC-P0-TOKENLAB | 89% | 73% | 22% |
| EPIC-P0-PROTOSPEC | 89% | 73% | 22% |
| EPIC-P0-PROTO | 89% | 73% | 22% |
| EPIC-P0-PLANNER | 89% | 73% | 22% |
| EPIC-P1-TOKENREG | 89% | 73% | 22% |
| EPIC-P1-CONTRACTS | 89% | 73% | 22% |

Work packages most often on the recommended critical chain: G_BETA 100%, EPIC-P2-LOAD#A 99%, EPIC-P2-TESTNET#R 99%, EPIC-P2-TESTNET#A 99%, W_WALLET_E3 99%, EPIC-P2-TESTNET#B 99%, EPIC-P2-LOAD#B 99%, EPIC-P1-FLAGS#A 99%.

**Tier 3 — full GA platform (GA)** — share of runs in which an epic (any of its work packages) or a gate lies on the chain that determines GA-14 (G_GA); columns: As organized | Recommended squads | Recommended + 7 contractors:

| Epic or gate | As organized | Recommended squads | Recommended + 7 contractors |
|---|---|---|---|
| G_GA | 100% | 100% | 100% |
| EPIC-P5-RELREADY | 100% | 100% | 56% |
| EPIC-P3-TUNE | 35% | 95% | 0% |
| EPIC-P4-SCALE | 35% | 95% | 0% |
| EPIC-P5-OPSMAT | 35% | 95% | 0% |
| EPIC-P3-CANARY | 0% | 86% | 0% |
| EPIC-P2-TESTNET | 58% | 63% | 46% |
| EPIC-P2-LOAD | 58% | 63% | 46% |
| W_WALLET_E3 | 58% | 63% | 46% |
| EPIC-P1-FLAGS | 58% | 63% | 46% |
| G_BETA | 59% | 62% | 46% |
| G_RG009 | 56% | 62% | 45% |

Work packages most often on the recommended critical chain: G_GA 100%, EPIC-P5-RELREADY#R 100%, EPIC-P5-RELREADY#A 100%, EPIC-P5-RELREADY#B 100%, EPIC-P4-SCALE#R 95%, EPIC-P5-OPSMAT#R 95%, EPIC-P5-OPSMAT#A 95%, EPIC-P4-SCALE#A 95%.
<!-- END:CRITICALITY -->

**A queueing effect that the tier-2 and tier-3 tables contain.** In each squad's queue the model serves the package with the longest remaining path first, and a squad works on one package at a time. A small readiness package of Phase 0 (in the tier-2 criticality table: the packages of `EPIC-P0-TOKENLAB`, `EPIC-P0-PLANNER`, `EPIC-P0-PROTO` and `EPIC-P0-PROTOSPEC`, which belong to the Protocol and Contracts squad) can therefore wait behind long Phase 1 packages of the same squad. Phase 0 exit (RG-001) waits for it, and the Phase 1 platform epics (`EPIC-P1-CORE` and everything that depends on it) wait for RG-001. In an organization someone would serve such a package first; the model does not. The table below isolates the effect by changing only that rule (the recommended squads in both columns):

<!-- BEGIN:QUEUERULE -->
| Tier and milestone | Model queue rule: longest remaining path first (P50 / P75 / P90) | Phase 0 packages served first (P50 / P75 / P90) | Difference at P50 (weeks) |
|---|---|---|---|
| TRI-4 Testnet reference exit (deployed on a public testnet and rehearsed) | W76 / W82 / W88 | W76 / W82 / W88 | +0 |
| PMB-2 Phase 0 exit (RG-001) | W66 / W72 / W78 | W37 / W39 / W42 | -29 |
| PMB-4 Phase 1 exit; testnet alpha (RG-002, R3) | W84 / W92 / W98 | W72 / W77 / W82 | -12 |
| PMB-12 Private beta go (RG-010) | W134 / W148 / W158 | W119 / W129 / W137 | -15 |
| GA-2 Phase 0 exit (RG-001) | W66 / W72 / W77 | W37 / W39 / W42 | -29 |
| GA-12 Private beta go (RG-010) | W134 / W147 / W158 | W119 / W129 / W137 | -15 |
| GA-14 GA go (RG-012) | W181 / W198 / W213 | W167 / W180 / W192 | -14 |

Both columns use the recommended squads. The first column is the published tier table. The second changes one thing in the model: a Phase 0 package, and the wallet-lab nodes, are served before any other package when a squad becomes free (`first` in the `recommended_p0_first` scenario of `make_scenarios`). It is a sensitivity on the staffing rule, **not** a published scenario, and it changes no number in §3.2.
<!-- END:QUEUERULE -->

How to read it. Tier 1 is not affected: its network has no Phase 0 exit gate. For tiers 2 and 3 the effect is large: the alternative rule brings Phase 0 exit forward by the number of weeks in the last column and the Phase 1 exit, the private beta and GA forward by a smaller but still large number, because the effect is on the chain that decides them in a large share of runs (criticality tables above). **With Phase 0 packages served first, the tier-3 GA P50 equals the v0.4 value (W167) and the private beta P50 is within a week of v0.4 (W118), although the protocol freeze and the contract audit freeze are later than in v0.4 (recommended squads, P50: freeze W27 → W32, contract audit freeze W60 → about W68): the v0.5 additions delay the contract path, but after the private beta the dates are bound by the operations chain, and the queueing effect is what moves them in the published tables.** The queue rule was one of the model choices listed for approval in 0.4 and is unchanged in 0.5; the published tables use it. Whether Phase 0 packages should be served first is a staffing decision (compare OD-031) that has not been taken; until it is, read the first column as the published number and the second as the alternative. The sensitivity is not tuned: it moves every Phase 0 package, not only the packages that gate RG-001, and it can delay other milestones (in this generation chain evidence, RG-004, is later under it).

### 3.6 What would invalidate this plan

| Trigger | Effect | Response |
|---|---|---|
| The contract path (Protocol and Contracts, Payments Core) is not staffed as assumed or critical hires slip | The freeze and everything after it move roughly one-for-one | OD-031: contractors, transfers, narrower scope |
| Counsel concludes FastPay needs a licence not obtainable in time | Private beta cannot begin in the chosen jurisdiction | Licensed-partner route (OD-001 c), or relocate the launch jurisdiction |
| Wallet lab shows < 2 target wallets with usable typed-data or batching, or most delegates lack working ERC-1271 (ASM-025) | Activation consent and transport assumptions fail | Restrict launch wallets; lean on `msg.sender` flows; redesign consent surfaces |
| Audit slots, duration or findings volume are worse than the model's ranges | The audit stage dominates | Book slots in P0; reserve remediation capacity; consider the contest earlier |
| Audit finds a design-level flaw in the three-layer model, the dual-cap model or the lineage migration | Re-architecture of contracts and re-audit | Protocol freeze change control ([14 §7](14-protocol-freeze-pack.md)); schedule reserve |
| Revalidation (RP-28) produces too many false pauses, or primary revocation flows fail for a listed token | Re-verification flows and token eligibility change | Parameters in [13 §7](13-eip7702-delegation-inspection.md); delist the token |
| Router migration response rate far below ASM-028 | Longer notice or fewer router versions | Adjust OD-026; keep ≤2 live routers |
| Sponsor reverses the version boundaries (for example conversion in v1.0) | Material re-plan: audit scope, RG-013 earlier | Re-run the model |
| The tier-1 scope fractions of §3.4.1 are wrong: a reference implementation needs more of the quote service, signer, chain gateway or testnet operations than proposed, or an orchestrator for scheduled charges (no orchestrator epic is in tier 1) | Tier 1 dates move; tiers 2 and 3 do not | Edit `TRI_SCOPE`, regenerate, and have the table approved |
| Counsel's view on notice duties (RP-26), the second reviewer's E2 sign-off of the Permit2 review or the approval rounds of the constants take longer than the ranges of §3.4.1 | The protocol freeze (TRI-1, PMB-1, GA-1) and every milestone after it move roughly one-for-one | Start counsel earlier; approve constants in parallel as their evidence arrives; name an owner for each wait |
| The pinned Permit2 source review or the fork tests contradict an E1 claim (RISK-034) | A predicate of the migration or revocation flows changes; the contract and planner vectors and the Foundry suites are redone | Change control of [14 §7](14-protocol-freeze-pack.md); schedule reserve on the Protocol and Contracts squad |
| The v0.5 additions on the contract path (shared-allowance migration, account pin, signer-set removal, Foundry export; +68 pw in total, first order ±40%) cost more than estimated | Protocol and Contracts binds TRI-2 and the audit freeze, so the slip is nearly one-for-one on tiers 1 to 3 | OD-031: contractors, transfers, narrower scope |
| The queue effect described in §3.5 is removed (or confirmed) by a different staffing rule | Phase 0 exit and everything gated by it move; the tier-2 and tier-3 dates move with it | Decide the staffing rule, then re-run the model |

## 4. Version boundaries mapped to the schedule

| Version | Scope summary (exact table in [09 §2](09-capability-boundaries.md)) | Gates to enable | Tier and milestones (§3.2) |
|---|---|---|---|
| v1.0 | Direct stablecoin settlement ON; **conversion code absent from Router v1**; Pay Once and FastPay recurring; dual caps with signed quotes; router lifecycle and lineage migration; delegation revalidation; 18 surfaces | RG-016, RG-001…RG-012, RG-015 readiness | Tier 1 (TRI-1 to TRI-4) is the reference implementation of its protocol on a testnet and is not a release; tier 2 (PMB-1 to PMB-12) is the private beta of v1.0, ending at RG-010; tier 3 (GA-1 to GA-14) is the public beta and GA, ending at RG-012 |
| v1.1 | Router v1.1 + `ConversionPolicyRegistry` + stable-pair adapter, adopted by opt-in; stablecoin conversion behind conditions C1, C2 and a rollout switch; S06, S08; Ethereum L1, BNB Smart Chain | RG-013 | Tier 3, **post-GA** (GA-15) |
| v2.0 | General-token conversion after audit and token-lab approval; oracle-bound fiat caps; S09, S10, S11, S24, S25; Router v2 and migration | RG-014, RG-015 | Tier 3, **post-GA**, indicative (GA-16) |

Gate dates for each tier and version are in §3.2. The tier-3 network includes the post-GA work, so v1.1 and v2.0 compete with the end of the GA work for squads in the tier-3 simulation; the tier-1 and tier-2 networks do not include it.

## 5. Re-estimates after the v0.3, v0.4 and v0.5 corrections

The seven corrections of 2026-10-13 changed scope (swap code absent from Router v1, lineage migration, per-charge delegation revalidation, the quote schema and cap classes, the profile rule, revocation flows) and the way time is estimated (critical path). Revision 0.4 added the Account Compatibility Policy, the exact migration predicates, the complete quote schema and the pinned Permit2 review. **Revision 0.5 adds 68 pw** in six causes (shared-allowance migration, account-pin precision, the Foundry export and its suites, signer-set emergency removal, the constants as individually approved records, the pinned Permit2 commit and bytecode comparison), adds three explicit waits before the protocol freeze, and splits the roadmap into three tiers. Person-week demand and schedule are reported separately. **Every v0.5 increase is an ESTIMATE (first order, ±40%) assigned to the epics that carry the work; none is a measurement.**

### 5.1 Result (generated)

<!-- BEGIN:DELTA -->
| Plan | v1.0 GA demand (pw) | Schedule (weeks from the start of Phase 0) | Basis |
|---|---|---|---|
| v0.1 | 2357 | GA W102 | Aggregate capacity |
| v0.2 | 2665 | GA W108 | Aggregate capacity (per-phase headcount) |
| v0.3 | 2601 | GA P50 W173 (recommended squads) in the v0.3 model | Critical path with a uniform 50% overlap rule (superseded) |
| v0.4 | 2651 | GA P50 W167 / P75 W183 / P90 W198 (recommended squads); P50 W198 as organized (one network ending at GA) | Critical path at work-package level with FS/SS/FF dependencies and lags; one network (superseded by the three tiers) |
| **v0.5 (this revision)** | **2719** | **EXPLORATORY, recommended squads, P50 / P75 / P90:** testnet reference exit (TRI-4) W76 / W82 / W88; private beta go (PMB-12) W134 / W148 / W158; GA go (GA-14) W181 / W198 / W213 | Three scoped networks (§3.1); the v0.5 estimates below; three new pre-freeze waits |
| Change in demand, v0.4 → v0.5 | +68 (+2.6%) | | |

v0.4 → v0.5, by cause (ESTIMATES, first order, ±40%; the cause letters are defined for this revision only):

| Cause | Meaning | Change in v1.0 GA demand (pw) |
|---|---|---|
| S | Shared-allowance migration: on-chain exposure index, normal and emergency modes, sibling handling | +17 |
| A | Account pin precision: struct, delegate-code check, signature-mode gating, pin version, signature-capability invalidation | +20 |
| V | Foundry export of the Python models; fuzz, invariant, mutation, integer-width, timestamp-boundary and shared-allowance suites | +14 |
| K | Signer-set emergency removal: tombstones, set stop, bounded rotation grace | +8 |
| C | Production-blocking constants as individually approved configuration records | +3 |
| P | Permit2 pinned commit, deployed-bytecode comparison and pinned source review | +6 |
| | **Total** | **+68** |

v0.4 → v0.5, by epic (every epic whose estimate changed):

| Epic | v0.4 → v0.5 (pw) | Causes |
|---|---|---|
| EPIC-P1-CONTRACTS | 110 → 126 (+16) | S +6, A +5, K +2, V +3 |
| EPIC-P0-PROTOSPEC | 19 → 30 (+11) | S +2, A +2, V +3, K +1, C +3 |
| EPIC-P1-FORK | 17 → 24 (+7) | V +6, P +1 |
| EPIC-P1-DELEGATION | 30 → 35 (+5) | A +5 |
| EPIC-P0-SOURCES | 15 → 19 (+4) | P +4 |
| EPIC-P0-WALLETLAB | 20 → 24 (+4) | A +4 |
| EPIC-P1-MIGRATION | 23 → 27 (+4) | S +4 |
| EPIC-P1-QUOTE | 35 → 38 (+3) | K +3 |
| EPIC-P2-MIGSVC | 32 → 35 (+3) | S +3 |
| EPIC-P0-PLANNER | 11 → 13 (+2) | S +1, A +1 |
| EPIC-P1-REVOKE | 11 → 13 (+2) | V +1, P +1 |
| EPIC-P1-TOKENREG | 25 → 27 (+2) | K +2 |
| EPIC-P2-PORTAL | 25 → 27 (+2) | A +2 |
| EPIC-P1-AUDITPREP | 14 → 15 (+1) | V +1 |
| EPIC-P1-SIGNER | 23 → 24 (+1) | A +1 |
| EPIC-P3-MIGDRILL | 16 → 17 (+1) | S +1 |

Post-GA scope (v1.1 and v2.0): 1308 pw in v0.2 → 1438 pw in v0.3 → 1452 pw in v0.4 → 1452 pw in v0.5 (no v0.5 change).

Earlier revisions, compactly. v0.3 → v0.4, by cause:

| Cause | Meaning | Change in v1.0 GA demand (pw) |
|---|---|---|
| A | Account Compatibility Policy: modes, on-chain account pin, re-verification | +21 |
| M | Migration snapshot, containment mask, exact successor predicates, router-independent cycle identity | +11 |
| Q | PriceQuote v1 completed: fifteen fields, signer sets, key rotation, non-override proof | +9 |
| R | Revocation primitives proved on forks; pinned Permit2 source review | +6 |
| W | Wallet-lab evidence for the account modes | +3 |
| | **Total** | **+50** |

Largest changes in v0.4: EPIC-P6-ROUTERV11 60 → 70 (+10); EPIC-P1-CONTRACTS 101 → 110 (+9); EPIC-P1-DELEGATION 22 → 30 (+8); EPIC-P1-QUOTE 31 → 35 (+4); EPIC-P2-AUDIT 65 → 69 (+4); EPIC-P6-AUDITV11 40 → 44 (+4); EPIC-P0-PROTOSPEC 16 → 19 (+3); EPIC-P0-WALLETLAB 17 → 20 (+3).

v0.2 → v0.3, by cause: S -76; L +22; D +20; Q +4; P -34; M +0; total -64 (S swap and conversion code absent from Router v1; L lineage, successor activation and primary revocation flows; D delegation revalidation; Q quote schema and cap classes; P epic profiles; M other).

Profile changes in v0.4 (the `program` profile is restricted to coordination; no estimate changed): 11 epics moved out of `program` (EPIC-P0-DOCS to infrastructure; EPIC-P2-TESTNET to infrastructure; EPIC-P2-DOGFOOD to feature; EPIC-P2-SUPPORTPREP to feature; EPIC-P3-CANARY to infrastructure; EPIC-P3-SUPPORT to infrastructure; EPIC-P3-TOKENOPS to compliance; EPIC-P5-SUPPORT247 to infrastructure; EPIC-P6-FLAGROLLOUT to infrastructure; EPIC-P6-BAU to infrastructure; EPIC-P7-BAU to infrastructure).

Removed in v0.3: EPIC-P1-CONVBOUND (18 pw, cause S). Added in v0.3: EPIC-P1-REVOKE (8 pw); EPIC-P6-ROUTERV11 (60 pw); EPIC-P6-AUDITV11 (40 pw); EPIC-P6-OPTIN (30 pw).
<!-- END:DELTA -->

### 5.2 How to read the change

- **Demand barely moves; the schedule moves a lot.** The corrections add some work (lineage, revalidation, quote schema, revocation flows) and remove some (conversion plumbing from v1.0, story types that do not apply). The large schedule change comes from the method: the earlier date assumed that an organization-wide capacity total could be spent on any work at any time.
- **Conversion code leaves v1.0.** The v1.0 audit scope is smaller and sharper; the cost reappears as the Router v1.1 epics after GA (`EPIC-P6-ROUTERV11`, `EPIC-P6-AUDITV11`, `EPIC-P6-OPTIN`). That is the price of making the boundary a code boundary instead of a flag.
- **The profile rule removes work that never applied** (for example observability for a research epic) and adds an evidence-and-sign-off story where the profile needs one.
- **v0.4 adds about 50 pw of work** (Account Compatibility Policy and the on-chain pin, exact migration predicates and the snapshot, the fifteen-field quote with key rotation, revocation fork tests, a pinned Permit2 review, wallet-lab runs for the account modes) and moves 11 epics out of `program` without changing their estimates. The schedule moves because of the work-package method as much as because of the added work; the v0.3 uniform 50% overlap rule is gone.
- **v0.5 adds 68 pw, all of it on the contract and assurance side** (generated table above): shared-allowance migration +17, account-pin precision +20, the Foundry export and its suites +14, signer-set emergency removal +8, the constants as individually approved records +3, the pinned Permit2 commit and bytecode comparison +6. The largest increases are `EPIC-P1-CONTRACTS` (+16), `EPIC-P0-PROTOSPEC` (+11) and `EPIC-P1-FORK` (+7). All are estimates, first order, ±40%.
- **The tier split changes what a date means, not what is built.** The first tier asks when a reference implementation could be exercised on a public testnet and needs about 13% of the work of the GA network (§3.1); the second asks when a private beta could start; the third when GA could. Each is its own simulation, so none of the three tables is a transformation of another.
- **Where the schedule moves in 0.5 (recommended squads).** The protocol freeze moves from W27 (v0.4, P50) to W32 and the contract audit freeze from W60 to W67 (tier 3) or W68 (tier 2), because the specification, source-review, planner and wallet-lab estimates grew and the contract epic grew by 16 pw; the three new waits do not move the freeze in this generation (§3.4.1). The private beta (W118 → W134) and GA (W167 → W181) move by more than the freeze does, and that extra movement is the queueing effect described in §3.5, triggered by the added Phase 0 and contract-path work: with Phase 0 packages served first, the private beta and GA P50 return to their v0.4 values (W119 and W167). **Which of the two columns of the §3.5 table is the better estimate is a staffing decision that has not been taken.**
- **The v0.2 GA week (W108) is withdrawn.** It equals roughly the dependency-and-wait floor of the network with unlimited staffing; it cannot be reached with squads of the stated size.

## 6. Epics, stories and capacity

All epics and stories are generated from [jira/build_backlog.py](jira/build_backlog.py), which also produces [jira/backlog.csv](jira/backlog.csv). Estimates are person-weeks (pw) for epics and person-days for stories.

### 6.1 Capacity vs demand (aggregate view; generated)

<!-- BEGIN:CAPACITY -->
| Phase | Weeks (recommended P50) | Avg headcount | Capacity (pw) | Demand (pw) | Utilization in the window | Cumulative utilization | Check |
|---|---|---|---|---|---|---|---|
| P0 Foundations and validation | W1-W66 (66) | 40 | 1857 | 161 | 9% | 9% | OK |
| P1 Build alpha (to contract audit freeze) | W67-W83 (17) | 50 | 595 | 539 | 91% | 29% | OK |
| P2 Platform completion, alpha, audits, sandbox | W84-W134 (51) | 50 | 1785 | 675 | 38% | 32% | OK |
| P3 Private mainnet beta | W135-W150 (16) | 50 | 560 | 415 | 74% | 37% | OK |
| P4 Public beta | W151-W169 (19) | 50 | 665 | 598 | 90% | 44% | OK |
| P5 GA readiness (v1.0) | W170-W181 (12) | 50 | 420 | 331 | 79% | 46% | OK |
| **v1.0 GA total (P0-P5)** | W1-W181 | | **5882** | **2719** | **46%** | | |
| P6 v1.1: stablecoin conversion enablement, repeat and variable billing | W182-W206 (25) | 50 | 875 | 638 | 73% | 50% | OK |
| P7 v2.0: general-token conversion, Router v2, new surfaces (indicative) | W207-W292 (86) | 50 | 3010 | 814 | 27% | 43% | OK |

Utilization is demand over the capacity of the whole organization. The phase windows are cut at the P50 dates of the gates, but epics start from their own dependencies, so work of a later phase is often done inside an earlier window; the **cumulative** column removes that boundary effect and is the one the check uses (above 90% the plan would need more capacity than exists). Low utilization shows where work is bound by one squad or by an external wait. Aggregate-capacity-only view: 2719 pw of GA-scope work over a 50-person organization on the same hiring ramp finishes at about W93; the exploratory critical-path view in section 3 gives W211 (P50, as organized) and W181 (P50, recommended).
<!-- END:CAPACITY -->

Capacity = average headcount (median hiring ramp, recommended squad sizes) × weeks × 0.70 focus factor. Demand excludes external vendor time (audit firms, pen testers). **This table is a plausibility check on the schedule, not a schedule**: low utilization shows where the work is bound by a squad or a wait rather than by organization-wide capacity. Post-GA phases include reserved sustaining capacity (`EPIC-P6-BAU`, `EPIC-P7-BAU`).

### 6.2 Epic profiles and definition of done

Revision 0.2 required six story types in every epic. That forced security, observability and migration stories into epics where they have no meaning (a source review has nothing to observe or migrate). Revision 0.3 gave each epic one of nine **profiles**; the profile says which story types are **required**, which are **optional** (kept when the epic has real content for them) and which **do not apply** (not created, not estimated). The generator rejects an epic that lacks a required type or carries one that does not apply. The eight requested profiles are feature, protocol, research, security, data, compliance, infrastructure and migration; the ninth, **program**, is kept at the sponsor's instruction (OD-030) **and restricted in v0.4 to coordination work**: staffing, procurement, gate-evidence assembly and release planning. Delivery work that had been filed under `program` (alpha operations, canary rollout, support operations, registry operations, staged enablement, sustaining engineering, CI tooling, dogfood, support tooling) moved to the profile that owns it.

<!-- BEGIN:PROFILES -->
| Profile | Required story types | Optional (kept when the epic has content) | Not applicable | Why | Epics | Stories |
|---|---|---|---|---|---|---|
| feature | IMP, SEC, OBS, TST, OPS | MIG | EVD | User-visible or service capability: build, secure, observe, test, operate; migration only where state or APIs are touched | 37 | 287 |
| protocol | IMP, SEC, OBS, TST, MIG, EVD | OPS | — | Contracts, planners, specs: interface/versioning and audit evidence are mandatory; events and errors are the observability | 13 | 135 |
| research | IMP, EVD | SEC, TST, OPS | OBS, MIG | Questions answered with evidence; no runtime to observe or migrate | 8 | 59 |
| security | SEC, OBS, TST, OPS, EVD | IMP, MIG | — | Assessments, audits, tooling: review, attack tests, detection, response, evidence | 12 | 99 |
| data | IMP, SEC, OBS, TST, MIG, OPS | EVD | — | Stores and pipelines: privacy and access, data-quality tests, backfill and schema migration, ownership | 4 | 33 |
| compliance | IMP, TST, OPS, EVD | SEC, OBS, MIG | — | Controls and legal work: control design, counsel or regulator sign-off, dry-run testing, staffing and escalation | 13 | 105 |
| infrastructure | IMP, SEC, OBS, TST, OPS | MIG, EVD | — | Platform and operations: hardening, observability, DR and chaos tests, runbooks; promotion/rollback where applicable | 21 | 169 |
| migration | IMP, SEC, OBS, TST, MIG, OPS | EVD | — | Moving customers or data between versions: tooling, consent integrity, funnel metrics, rehearsal, rollback, communications | 6 | 54 |
| program | IMP, OPS, EVD | SEC, TST | OBS, MIG | COORDINATION ONLY: staffing, procurement and contracting of vendors, gate-evidence assembly and sign-off meetings, release, rollback and communication planning, status and risk reporting. Delivery work (code, tooling, tests, audits, controls, operations, migrations) belongs to the feature, protocol, security, data, compliance, infrastructure and migration profiles and is prohibited here (checked by the generator) | 4 | 25 |

Story-type codes: IMP implementation (shown as *Research task*, *Compliance control* or *Program action* for those profiles), SEC security, OBS observability, TST test, MIG migration requirement, OPS operational readiness, EVD evidence and sign-off.

**The `program` profile is coordination only.** Allowed: P0-HIRING (staffing); P0-AUDITSEL (procurement and contracting of audit and pen-test vendors); P5-GA (assembly of gate evidence and the go/no-go meeting); P5-RELREADY (release, rollback and communication plans). Prohibited: any delivery work that belongs to the feature, protocol, security, data, compliance, infrastructure or migration profiles. The generator fails if a program epic is not in the allowed list or if its implementation stories use delivery vocabulary (code, tooling, deploy, drill, runbook, rollout, KYB, AML, migration execution, monitoring, support operations and similar). Epics moved out of `program` in v0.4: 11.

Effects of the profile rule: research and program epics (12) carry no observability or migration stories; 78 evidence-and-sign-off stories exist. In the current data every optional type has real content, so all optional stories are kept.
<!-- END:PROFILES -->

Each story type has a standard definition of done, refined by profile where the meaning differs (research: sources at E2 and a second reviewer; compliance: a control exercised in a dry run and reviewed by counsel or the compliance officer; data: quality, reconciliation and replay tests; infrastructure: fault-injection or recovery tests and rehearsed rollback; protocol: vectors and invariants; migration: rehearsal including interruption and rollback). The definitions live in `build_backlog.py` (`DOD`, `DOD_BY`) and are written into every story's acceptance criteria; epic-specific detail is appended. The days of an epic are shared among its stories by fixed weights, normalized over the types the profile includes. The split is a planning convention. Acceptance thresholds marked PROPOSAL are open for the owners to change at the phase planning gate.

### 6.3 What the backlog is, and is not

<!-- BEGIN:STORYSTATS -->
| Story type | Stories | Person-days |
|---|---|---|
| Implementation | 322 | 10083 |
| Security | 118 | 2008 |
| Observability | 106 | 1507 |
| Test | 118 | 3619 |
| Migration requirement | 106 | 1121 |
| Operational readiness | 118 | 1613 |
| Evidence and sign-off | 78 | 904 |
| **Total** | **966** | **20855** |

Stories by profile and type:

| Profile | Epics | IMP | SEC | OBS | TST | MIG | OPS | EVD |
|---|---|---|---|---|---|---|---|---|
| feature | 37 | 102 | 37 | 37 | 37 | 37 | 37 | — |
| protocol | 13 | 57 | 13 | 13 | 13 | 13 | 13 | 13 |
| research | 8 | 27 | 8 | — | 8 | — | 8 | 8 |
| security | 12 | 27 | 12 | 12 | 12 | 12 | 12 | 12 |
| data | 4 | 9 | 4 | 4 | 4 | 4 | 4 | 4 |
| compliance | 13 | 27 | 13 | 13 | 13 | 13 | 13 | 13 |
| infrastructure | 21 | 46 | 21 | 21 | 21 | 21 | 21 | 18 |
| migration | 6 | 18 | 6 | 6 | 6 | 6 | 6 | 6 |
| program | 4 | 9 | 4 | — | 4 | — | 4 | 4 |

Coverage check (enforced by the generator): all **118** epics satisfy their profile (required story types present, none that do not apply) and carry acceptance criteria; each epic's story-days sum to its estimate.

**Status of the backlog: a planning baseline, not implementation-complete.** Every epic is decomposed to story level so that the work its profile requires is visible, but stories in later phases are coarse. They are split, re-estimated and re-sequenced at each phase planning gate; acceptance thresholds marked PROPOSAL are open to change; estimates are first-order (±40%).
<!-- END:STORYSTATS -->

### 6.4 Epic list

<!-- BEGIN:EPICS -->
#### P0 — Foundations and validation (W1-W66, recommended P50) — v1.0

| Epic | Name | Profile | Owner squad | pw (v0.2 → v0.5) | Depends on | Risk | Acceptance (epic) | Target | Stories |
|---|---|---|---|---|---|---|---|---|---|
| EPIC-P0-DOCS | Specification governance and traceability | infrastructure | Leadership and Program | 5 → 4 | - | L: tooling adoption | Artifact-header lint blocks a PR that omits any header field; the RTM covers 100% of drafted MVP requirements; the weekly traceability check is green three weeks running. | RG-001 | 8 |
| EPIC-P0-SOURCES | Source verification and research-plan execution (RP-01..08, 13..15, 22, 23, 25) | research | Protocol and Contracts | 13 → 15 → 19 | - | M: primary sources contradict tool summaries | Every design-load-bearing claim in Parts C and D is at evidence level E2 or higher; EV-P01, EV-P02, EV-P06, EV-P10 and EV-P11 closed; contradictions logged as CF items. The pinned Permit2 source review of [16 §5] (PR-01…PR-16) is complete at E2 with the commit SHA recorded, and the freeze subset of fork tests (RV-T01, 02, 04, 05, 07, 11 on a plain EOA, and MIG-TV-22) reproduces its claims; the full RV-T and ZP-T suites follow in `EPIC-P1-REVOKE`. The Permit2 commit is pinned (SHA recorded); the deployed bytecode on each launch chain is compared with the pinned build with the immutables masked and any chain that differs is excluded, not assumed equal; the source review answers PR-01…PR-16 at E2 with a second reviewer's sign-off. | RG-001 | 10 |
| EPIC-P0-WALLETLAB | Wallet compatibility lab v0 (RP-05, RP-06, RP-21, RP-25) | research | Quality | 17 → 20 → 24 | EPIC-P0-SOURCES | H: wallets differ from documentation (RISK-004, RISK-027) | At least 8 wallet/account-type combinations probed on at least 3 testnets with raw wallet_getCapabilities output stored; delegate address, code hash, ERC-1271 behavior and revert path captured for every wallet that upgrades accounts; Compatibility Register v0 published; Trust Wallet row filled by observation, not inference. Run records exist for each account mode (plain EOA, verified 7702 delegation, ERC-4337 account, ERC-1271 wallet) per claimed wallet, meeting the evidence list EVL-01…EVL-10 of [16 §9] (the freeze subset). The per-mode runs also cover account-pin precision: the delegate code hash and implementation family per wallet, which signature modes each wallet supports (signature-mode gating), and what a wallet or delegate version change does to the pin and to signature capability (WL-36…40, evidence EVL-15). | RG-001 (v0); RG-003 (final) | 10 |
| EPIC-P0-TOKENLAB | Token behavior lab v0 (RP-07) including primary revocation-flow checks (EV-P11) | research | Protocol and Contracts | 7 → 6 | EPIC-P0-PROTO | M: token behavior surprises | Launch-candidate stablecoins on 2 chains tested for 12 behavior classes and for the primary revocation flows (token approve(0), Permit2 lockdown and approve(...,0,0)); registry seed produced; listing criteria written. | RG-001 | 6 |
| EPIC-P0-PLANNER | Planner reference implementations and golden vectors (recurring, Pay Once, caps) | protocol | Protocol and Contracts | 10 → 9 → 11 → 13 | EPIC-P0-SOURCES | M: ambiguity in canonical input | Two independent implementations pass TV-01..TV-26, TV-PO-1..TV-PO-12, CAP-TV-01..CAP-TV-13 and DRV-01..DRV-25 byte-for-byte; a differential fuzz of 100,000 random inputs yields zero divergences; the quote digest vector of document 11 section 4.6 is reproduced. Vectors ACP-TV-01…24 and planner vectors TV-27…TV-30 (account mode gating, pin in the plan, refusal for UNKNOWN_CODE) pass in both implementations (planner 1.3.0). The planner computes siblings (live mandates of the same customer on the same router and token), never emits a lockdown that would unfund a sibling in NORMAL mode, sizes the new router's shared allowance for the sum of the migrated lineages, and emits the seven-field account pin; MIG-TV-30…45 and ACP-TV-25…44 pass in both implementations. | RG-001 | 12 |
| EPIC-P0-PROTO | Fork prototype (spike): mandate lineage, router, quote verification, Pay Once witness | research | Protocol and Contracts | 14 → 13 | EPIC-P0-SOURCES | M: spike code mistaken for production code | On a mainnet fork: activation by batch and by legacy path, one charge, gasless revoke, router paused while revoke still works, a successor mandate on a second router with lineage counters preserved and the old permission required to be unusable, a quote-verified charge, a Pay Once witness transfer; per-step gas recorded; all code tagged SPIKE and kept out of the production repository; no conversion code written. | RG-001 | 7 |
| EPIC-P0-THREAT | Threat model v1 and security requirements | security | Platform, SRE and Security Engineering | 8 | - | M: incomplete threat coverage | The 31 prompt-section-18 threats plus quote-signer compromise, migration phishing, delegation drift and revalidation abuse each have all template fields; the top 10 by risk have named tests; an external reviewer has signed off. | RG-001 | 8 |
| EPIC-P0-LEGAL | Regulatory perimeter, consent and notice constraints, name clearance (RP-09..12, RP-20, RP-26) | compliance | Compliance, Risk and Privacy | 5 | - | H: licensing outcome (RISK-009) | Counsel memo covers Q-01..Q-20 for each candidate jurisdiction (Q-03 on conversion is answered for v1.1 planning and is not on the v1.0 critical path); OD-001 is decided or deferred with reasons and a date; notice-duty guidance for router migration delivered; trademark report delivered. | RG-001 | 9 |
| EPIC-P0-DESIGN | Design foundations and flows (activation, Pay Once, dual-cap consent, router-specific authorization, delegation display and re-verification) | feature | Product and Design | 15 → 16 | EPIC-P0-PLANNER | M: consent comprehension | Flows exist for planner paths A-D, refusal, PO-1..PO-6, dual-cap consent, router-specific successor authorization, delegation display and DELEGATION_UNVERIFIED re-verification; component specs pass WCAG 2.2 AA checks; RTL variants for checkout; a usability test with 8 participants shows at least 80% state both limits and how to revoke (PROPOSAL). | RG-001 | 8 |
| EPIC-P0-PRODUCT | PRD for the v1.0 surfaces, KPI tree, unit economics, merchant interviews | research | Product and Design | 10 | EPIC-P0-PROTO | M: weak merchant demand signal | 20 merchant interviews logged; the PRD for the 14 MVP surfaces covers all 25 section-7 fields; OD-024 signed; unit economics use fork-measured gas for conversion-off and conversion-on scenarios. | RG-001 | 7 |
| EPIC-P0-INFRA | Cloud decision and landing-zone skeleton | infrastructure | Platform, SRE and Security Engineering | 6 | - | M: HSM capability gaps | RP-15 comparison complete; ADR-012 finalized; accounts and IAM baseline in IaC; CI builds signed with provenance; no long-lived deploy credentials; an HSM proof of concept signs a secp256k1 test transaction under both the executor and the quote key classes. | RG-001 | 8 |
| EPIC-P0-HIRING | Critical-role hiring and ramp to 18 | program | Leadership and Program | 4 | - | H: scarce talent (RISK-011) | Six critical roles filled or contractors engaged by W6; headcount 18 by W12. | RG-001 | 6 |
| EPIC-P0-AUDITSEL | Audit and pen-test vendor selection (v1.0 scope: no conversion code) | program | Leadership and Program | 3 | - | M: slot availability (ASM-011) | RFIs sent to at least 4 firms; the v1.0 contract scope is priced and the later Router v1.1 scope is priced separately (ASM-027); two audit firms contracted with slots from the planned freeze week; pen-test vendor shortlisted. | RG-001 | 6 |
| EPIC-P0-PROTOSPEC | Protocol specification set and freeze pack (mandate lineage, payment, Pay Once, dual cap and quote schema, router lifecycle, delegation revalidation, contracts D.1) | protocol | Protocol and Contracts | 14 → 16 → 19 → 30 | EPIC-P0-SOURCES | M: specification gaps surface late | Part C and D specifications exist for MandateManager (lineage, three pause bits), PaymentRouter v1 (both protocols, no conversion code), RouterRegistry, TokenPolicyRegistry, QuoteVerifier, MerchantRegistry, ExecutorRegistry, FeeController, RefundManager and EmergencyGuardian with storage, roles, events, errors and invariants; the protocol freeze checklist of document 14 is complete and reviewed by Security and Solidity; the quote vector is reproduced by two implementations. The Account Compatibility Policy ([17]) with its modes, permissions, on-chain account pin and update path; the migration snapshot, containment mask and exact `activateSuccessor` predicates ([12 §5.3]); router-independent lineage, mandate and cycle identifiers; `PriceQuote` v1 with fifteen fields and key-rotation rules ([11 §4]); and the freeze-decision report ([16]) leave no unowned item. The specification set also contains: the NORMAL and EMERGENCY modes of `activateSuccessor` with the on-chain exposure index per (customer, router, token) and the sibling rules ([12 §5.3]); the seven-field `AccountPin` with the `EXTCODEHASH` checks of the account and of the delegate, the signature-mode gate, the pin version and the invalidation of signature capability ([17]); the signer-set emergency-removal rules (immediate tombstone for a compromised signer, set stop by the guardian, retired-set grace bounded by `QUOTE_SET_GRACE`) ([11 §4.7]); the export rules that turn the Python vectors and models into Foundry suites; and each production-blocking constant PC-01…PC-18 as a configuration record (owner, unit, rationale, evidence, safe range, test, release gate, approval block) ready for approval one by one ([16 §7]). | RG-001 | 16 |

#### P1 — Build alpha (to contract audit freeze) (W67-W83, recommended P50) — v1.0

| Epic | Name | Profile | Owner squad | pw (v0.2 → v0.5) | Depends on | Risk | Acceptance (epic) | Target | Stories |
|---|---|---|---|---|---|---|---|---|---|
| EPIC-P1-CONTRACTS | Core contracts v0.9 and Foundry suites (Router v1 without conversion code; mandate lineage; dual caps) | protocol | Protocol and Contracts | 108 → 101 → 110 → 126 | RG-016 (protocol freeze); EPIC-P0-PROTOSPEC; EPIC-P0-PROTO | H: logic bug (RISK-001) | Every invariant in 06 section 4.1 has an invariant or property test; the invariant suite runs at least 1,000,000 calls with zero violations; branch coverage at least 95% on core contracts; static analysis has no unresolved high findings; the absence checks of 09 section 7 pass (no conversion selectors, call targets within the allowlist, no tx.origin); the quote digest and type hashes equal the vector of document 11; role-matrix and fee-ceiling tests pass. Account pin: `consume` reverts `AccountCodeChanged` unless PIN_OK holds, and `updateAccountPin` needs customer authority and never changes a cap. `activateSuccessor` implements exactly the predicates of 12 §5.3, computes the migration snapshot on chain, requires `widenedMask` to equal the computed mask (zero for a migration) and emits the snapshot hash. Lineage, mandate and cycle identifiers contain no router address. `PriceQuote` v1 has the fifteen fields of 11 §4 and checks Q1…Q20; the non-override properties of 11 §4.8 hold under an adversarial signer. `activateSuccessor` has two modes. NORMAL (router still trusted): the old Permit2 allowance may remain only while a sibling mandate of the same customer still relies on the router, and must be zero or expired for a token once no sibling uses it. EMERGENCY (router disabled, sunset, retired or security-deprecated): every token of every mandate of the customer on that router has an unusable allowance first. An on-chain exposure index counts live mandates per (customer, router, token). The `AccountPin` is the seven-field struct; `consume` checks `EXTCODEHASH` of the account and of the delegate; signature capability is bound to the pin and revoked when the delegate, the implementation, the wallet version or the code hash changes. The quote-signer registry supports an immediate tombstone (a compromised signer has no grace and is never registrable again), honors a retired signer set only for quotes issued before retirement and for at most `QUOTE_SET_GRACE`, and lets the guardian stop a whole set. The Foundry suites exported from the Python models (vectors, fuzz, invariant, mutation, integer width, timestamp boundary, shared allowance) run in CI. | RG-002 | 19 |
| EPIC-P1-PAYONCE | Pay Once protocol (SignatureTransfer witness, entrypoints, planner paths PO-1..PO-6, orchestration) | protocol | Protocol and Contracts | 22 → 21 | EPIC-P0-PROTOSPEC; EPIC-P1-CONTRACTS | M: wallet signature rendering (ASM-006) | TV-PO-1..TV-PO-12 pass; I-PO-NOSTANDING and I-PO-WITNESS hold on fork; Pay Once code has no reference to MandateManager or AllowanceTransfer; recurring code has none to SignatureTransfer. | RG-002 | 9 |
| EPIC-P1-FLAGS | Rollout-switch service with two-person enabling and fail-closed evaluation (a flag is not a security boundary) | feature | Payments Core | 14 → 10 | EPIC-P1-CORE | M: misconfiguration (RISK-028) | Enabling a flag needs two approvers and evidence ids; disabling needs one; every change is audited and evented; an unreachable service evaluates to false; flags are evaluated at plan and execution time; documentation and UI never describe a flag as a protection. | RG-002 | 7 |
| EPIC-P1-QUOTE | Quote service, quote-signer deployable and price-bound configuration | feature | Chain Infrastructure | 30 → 31 → 35 → 38 | EPIC-P0-INFRA; EPIC-P1-CONTRACTS | H: quote-signer compromise (RISK-025) | Quotes follow PriceQuote v1 exactly (document 11 section 4): validity predicate Q1-Q20, ECDSA-only signers, TTL at most the registry maximum; the quote-signer holds a separate HSM key class and refuses out-of-policy requests; quote issuance p95 under 500 ms; the digest vector is reproduced by the backend. The quote service issues the fifteen-field `PriceQuote` v1 with nonce, signer-set version, registry version, route hash and price-source-set hash; key rotation follows 11 §4.7 (overlap, grace, emergency removal). A compromised signer is removed by an immediate tombstone with no grace period; a retired signer set is honored only for quotes issued before retirement and for at most `QUOTE_SET_GRACE`; the guardian can stop a whole set; the service stops requesting signatures from a tombstoned or stopped set at its next refresh. | RG-002 | 10 |
| EPIC-P1-MIGRATION | Router lifecycle and lineage migration: orchestrator foundations, successor authorization builder, MigrationPlan, rehearsal harness | migration | Protocol and Contracts | 18 → 20 → 23 → 27 | EPIC-P1-CONTRACTS; EPIC-P0-PROTOSPEC | H: stranded mandates (RISK-026) | MigrationPlan steps S1 (grant new), S2 (revoke old), S3 (activate successor) are produced and verified for ATOMIC_BATCH, MIXED and TX_SEQUENCE; MIG-TV-01..18 pass on a fork; the router-specific authorization renders named fields in the lab wallets. The plans reproduce the atomic and legacy flows of 12 §5.4 with the predicate truth tables, show the widened mask to the customer, and treat the shared Permit2 allowance (all of the customer's lineages on the old router) explicitly. The planners compute siblings, never emit a lockdown that would unfund a sibling in NORMAL mode, size the new router's shared allowance for the sum of the migrated lineages, and in EMERGENCY mode make every token of every mandate of the customer on the old router unusable first; the orchestrator holds siblings instead of failing their charges. | RG-002 | 11 |
| EPIC-P1-DELEGATION | Account Compatibility Policy engine: modes, on-chain pin, inspection, revalidation, re-verification | feature | Payments Core | 16 → 22 → 30 → 35 | EPIC-P0-WALLETLAB | H: unknown or hostile delegates (RISK-027) | Every plan carries a delegation record under 5 minutes old; every unattended charge attempt passes the revalidation of document 13 section 7 or is blocked; DRV-01..DRV-25 pass; the policy table reproduces on synthetic delegates; DELEGATION_UNVERIFIED pauses and clears as specified; pre-flight aborts on a code-hash change. The engine classifies every connected account into one of five modes with the detection predicates of [17 §2], applies the permission matrix of [17 §3], builds the account pin for the plan, detects a wallet-managed upgrade after activation, and drives re-verification (customer-signed pin update); ACP-TV-01…24 pass. The engine builds the seven-field account pin (the account code hash is the delegation designator hash for 7702 accounts), compares the delegate code hash and implementation family, gates signature modes per account mode and pin version, and treats a change of delegate, implementation, wallet version or code hash as an invalidation of signature capability that routes the customer to re-verification; ACP-TV-25…44 pass. | RG-003 | 14 |
| EPIC-P1-FORK | Mainnet-fork harness and token-lab integration | infrastructure | Quality | 18 → 16 → 17 → 24 | EPIC-P0-TOKENLAB | M: fork flakiness | CI runs the full suite on forks of 2 chains nightly; token-lab results gate registry listings and conversion approvals. The Foundry suites exported from the Python models (vectors, fuzz, invariant, mutation, integer width, timestamp boundary, shared allowance) run in CI on forks of 2 chains together with the fork tests of the Permit2 freeze subset at the pinned commit; the export tool is the only source of these tests. | RG-002 | 10 |
| EPIC-P1-CORE | fastpay-core foundations: tenancy, auth, API gateway, idempotency, outbox/inbox, audit logs | feature | Payments Core | 38 | RG-001 | M: tenant isolation defects | A tenant-fuzz test finds zero cross-tenant reads or writes; every mutating endpoint requires an idempotency key and replays return identical responses; an outbox/inbox chaos test shows exactly-once effect. | RG-002 | 8 |
| EPIC-P1-LEDGER | Ledger service, chart of accounts, core scenarios incl. fiat valuation and conversion scaffolding | data | Payments Core | 34 → 31 | EPIC-P1-CORE | H: financial correctness (RISK-016) | The database forbids UPDATE and DELETE on postings; property tests show debits equal credits per journal and asset over 1,000,000 random journals; scenarios direct payment, platform fee, failed payment, full refund, reorg reversal, reconciliation adjustment pass; fiat values are stored in minor units; replay of fork chain data reconciles at 100%; conversion journals are specified but not implemented before v1.1. | RG-002 | 9 |
| EPIC-P1-CHAINGW | chain-gateway: multi-RPC quorum, indexer, broadcaster, finality, delegation reads | feature | Chain Infrastructure | 36 → 38 | RP-04; RP-22 | H: RISK-008, RISK-015 | A chaos suite (lying RPC, lagging provider, 10,000 simulated reorgs) shows zero false FINALIZED; the nonce manager recovers from an injected stuck nonce; quorum disagreement yields UNKNOWN, never a charge; account code, nonce and balance reads are quorum-backed and a pre-charge observation API meets p95 under 1.5 s (PROPOSAL). | RG-004 | 8 |
| EPIC-P1-SIGNER | signer service with HSM and policy engine (executor and charge-signer key classes) | feature | Chain Infrastructure | 20 → 22 → 23 → 24 | EPIC-P0-INFRA | H: key compromise (RISK-005) | A 200-case policy test: every out-of-policy intent is refused (wrong contract, wrong selector, value not zero, over ceiling, rate limit, missing or invalid quote on a fiat-capped charge, missing or stale revalidation stamp on an unattended charge); the key ceremony is rehearsed; signing disables itself on policy-engine failure. Signer policy refuses an unattended charge whose account-policy stamp is missing, older than 60 seconds, or computed for a different pin. Signer policy also refuses an unattended charge whose account-policy stamp names a signature mode that the pin does not allow. | RG-006 | 8 |
| EPIC-P1-MANDATE | Mandate service, capability service, planner integration, cap derivation | feature | Payments Core | 32 → 34 → 36 | EPIC-P0-PLANNER; EPIC-P1-CONTRACTS; EPIC-P1-DELEGATION | M: wallet divergence from the lab | The production planner passes every golden vector; activation sessions resume after a tab close (SV-03); verification V1-V4 gates ACTIVE (SV-02); token caps are derived from fiat caps per 11 section 7 (CAP-TV-01..03); mandate revisions and router bindings are tracked. | RG-002 | 9 |
| EPIC-P1-TOKENREG | Token registry service and console, price bounds, quote-signer set, drift watchers | feature | Protocol and Contracts | 26 → 23 → 25 → 27 | EPIC-P0-TOKENLAB | H: RISK-007 | Registry entries contain every field in prompt section 10 that v1 uses plus price bounds; a SWAP_ONLY listing is rejected in v1; the bytecode/implementation watcher detects a simulated proxy upgrade within 2 blocks and auto-blocks the token. The registry stores signer tombstones (never re-registrable), the set-stop flag and the end of the retired-set grace; every change is evented, and emergency removal and set stop take effect immediately. | RG-004 | 10 |
| EPIC-P1-SECPROG | Secure SDLC and CI security | security | Platform, SRE and Security Engineering | 18 | EPIC-P0-INFRA | M: tooling noise | SAST, SCA, secret scanning, container scanning and IaC scanning gate merges; dependencies pinned; SBOM generated and artifacts signed with provenance; branch protection and code owners enforced. | RG-006 | 8 |
| EPIC-P1-AUDITPREP | Audit readiness package (Router v1 without conversion code, registries, quote verification, lineage migration) | security | Protocol and Contracts | 16 → 13 → 14 → 15 | EPIC-P1-CONTRACTS | M: freeze slips | Package includes specs, invariants, threat model, deployment scripts, test evidence, the absence-check report and the external-call allowlist; an internal pre-audit review has no open high findings; code freeze at the planned freeze week. The audit package includes the generated Foundry suites with the instructions to regenerate them from the Python vectors, the mutation report with its surviving mutants, and the integer-width and timestamp-boundary results. | RG-002 | 8 |
| EPIC-P1-OBS | Observability baseline, SLOs, on-call v0 | infrastructure | Platform, SRE and Security Engineering | 18 | EPIC-P0-INFRA | M: log leakage | Correlation ids on 100% of sampled traces; a redaction test proves signatures, permit payloads, quote signatures and keys never appear in logs; SLO dashboards live; the paging path is tested. | RG-009 | 8 |
| EPIC-P1-REVOKE | Primary revocation flows: portal and SDK flows, plan validator, per-token verification (EV-P11) | security | Protocol and Contracts | 8 → 11 → 13 (new in 0.3) | EPIC-P0-TOKENLAB; EPIC-P1-CONTRACTS | M: token quirks (RISK-031) | Token approve(0), Permit2 lockdown and approve(...,0,0), invalidateNonces and MandateManager revoke/revokeBySig work for every listed token and chain on forks; the plan validator rejects any plan with a zero-amount permit step while the experimental flag is off; the portal and SDK expose the primary flows with accurate cost and gas wording. The primary revocation flow (token approve zero, `Permit2.lockdown`, `invalidateNonces`) passes the fork tests RV-T01…RV-T12 of [05 §2.1] at the pinned commit, including accounts that are plain EOAs, 7702-delegated and contract accounts; the zero-amount signed permit stays disabled until ZP-T01…ZP-T08 and the wallet-lab runs pass. RV-T and ZP-T are exported to Foundry and run at the pinned Permit2 commit and against the deployed bytecode with the immutables masked on each launch chain; the case of a lockdown that would unfund a sibling mandate is a named test. | RG-004 | 10 |

#### P2 — Platform completion, alpha, audits, sandbox (W84-W134, recommended P50) — v1.0

| Epic | Name | Profile | Owner squad | pw (v0.2 → v0.5) | Depends on | Risk | Acceptance (epic) | Target | Stories |
|---|---|---|---|---|---|---|---|---|---|
| EPIC-P2-ORCH | Payment orchestrator, token selection, fallback state machine, reconciliation | feature | Payments Core | 38 | EPIC-P1-CHAINGW; EPIC-P1-SIGNER; EPIC-P1-QUOTE; EPIC-P1-FLAGS | H: double charge | State-machine tests cover every allowed and prohibited transition in 06 section 3.2; a chaos test with timeouts at each step produces zero second-token charges while UNKNOWN; the on-chain once-per-cycle race test passes; quotes are acquired and re-acquired correctly before submission; delegation revalidation precedes quoting and signing of every unattended attempt and a failure never falls back to another token. | RG-007 | 8 |
| EPIC-P2-CHECKOUT | Hosted checkout, wallet connection, activation and Pay Once flows, SDK v0 | feature | Checkout and Merchant Experience | 46 | EPIC-P0-DESIGN; EPIC-P1-MANDATE; EPIC-P1-PAYONCE | M: wallet quirks | Checkout works on every wallet rated SUPPORTED in the Compatibility Register on testnets; no opaque-signature requests (lint); dual-cap consent shows both numbers; delegation notice uses approved wording; WCAG 2.2 AA automated checks pass; strict CSP with no third-party scripts. | RG-006 | 8 |
| EPIC-P2-PORTAL | Customer mandate portal v0 (limits, usage, revoke, delegation status and re-verification, migration prompts) | feature | Checkout and Merchant Experience | 22 → 23 → 25 → 27 | EPIC-P1-MANDATE; EPIC-P1-MIGRATION | M: stale chain state shown to customer | A customer can view both cap families and usage, pause, revoke (gasless via revokeBySig), request Permit2 lockdown by transaction, see delegation status and re-verify after a DELEGATION_UNVERIFIED pause, and complete a lineage migration; revoke takes effect on chain in the next block and the portal shows chain-verified status. The portal shows the account mode and pin status, offers re-verification after an account change, and signs the pin update. The portal shows the full pin (mode, delegate, delegate code hash, implementation family, pin version, signature mode), says in plain words what a pin update changes and that it never changes a cap, and shows when and why signature capability was invalidated. | RG-006 | 8 |
| EPIC-P2-MERCHANT | Merchant service, dashboard v0, API keys, webhooks v0 (including router and migration events) | feature | Payments Core | 34 → 33 | EPIC-P1-CORE | M: webhook SSRF and replay | Scoped, hashed, rotatable API keys; webhook HMAC with replay window and secret rotation; SSRF tests pass; dashboard shows payments, mandates, keys, webhook logs and migration status for the merchant's customers. | RG-006 | 8 |
| EPIC-P2-COMPLIANCE | KYB workflow and sanctions screening integration | compliance | Compliance, Risk and Privacy | 20 → 19 | EPIC-P0-LEGAL; OD-001 | H: RISK-020 | A merchant cannot go live without KYB approval; sanctions screening runs on merchants and settlement recipients; the manual-review queue works end to end. | RG-008 | 8 |
| EPIC-P2-DEVDOC | API reference and developer docs v0 | feature | DevEx, Support and Partnerships | 8 | EPIC-P2-MERCHANT | L: docs drift | Every endpoint has an example and error list; the sandbox quickstart works from scratch in under 30 minutes (timed test); docs state the persistent nature of delegation and the dual-cap limits accurately. | RG-002 | 7 |
| EPIC-P2-RUNBOOKS | Runbook stubs RB-001..RB-032 and detection backlog (RB-033 conversion kill switch arrives with v1.1) | infrastructure | Platform, SRE and Security Engineering | 10 | EPIC-P1-OBS | L: stubs stay stubs | 32 stubs each with trigger, detection, severity and owner (including RB-031 migration campaign and RB-032 emergency router disablement); the detection backlog is mapped to the section-23 list, to delegation revalidation outcomes and to router lifecycle changes. | RG-009 | 8 |
| EPIC-P2-TESTNET | Public testnet alpha operations | infrastructure | Quality | 34 → 30 | RG-002 | M: low tester participation | At least 100 external testers; activation completion at least 90% on wallets rated SUPPORTED (PROPOSAL); zero fund-loss defects; every defect triaged within 2 business days; Compatibility Register updated from alpha data. | R3 | 8 |
| EPIC-P2-AUDIT | Two parallel audits (Router v1 without conversion code, registries, quote verification, lineage migration), remediation, re-review | security | Protocol and Contracts | 72 → 65 → 69 | EPIC-P1-AUDITPREP | H: findings volume (RISK-012, RISK-024) | All critical and high findings fixed and re-reviewed by the finding firm; medium and low triaged with written rationale; final reports archived; the audit scope statement lists in-scope and out-of-scope contracts and states that no conversion code exists in v1.0; RG-005 criteria met. The audit scope statement is the function-level list of [16 §8] (including the account pin, the successor predicates and the fifteen-field quote). | RG-005 | 9 |
| EPIC-P2-PENTEST | Penetration test and red-team exercises (app, API, cloud, signer, quote-signer, frontend) | security | Platform, SRE and Security Engineering | 22 | EPIC-P1-SECPROG | M: late findings | App, API, cloud, signer and quote-signer pen test complete; a red-team exercise on the frontend and signers; no open critical or high findings. | RG-006 | 8 |
| EPIC-P2-SUBS | Fixed subscription engine, dunning, grace, price-change consent | feature | Payments Core | 44 | EPIC-P2-ORCH | H: RISK-008 | Each cycle has a unique id; retry storms cannot produce two successful charges; dunning and grace are configurable; a price change requires a new customer consent (mandate revision) with both caps re-derived; windows follow 30-day anchored semantics. | R3 | 8 |
| EPIC-P2-DOGFOOD | Internal dogfood on testnets | feature | Product and Design | 16 → 14 | EPIC-P2-SUBS | L | One full lifecycle (activate, 6 cycles, pause, resume, revoke, refund, and one router migration by successor mandate) per supported path with ledger reconciliation at 100%. | R4 | 7 |
| EPIC-P2-SANDBOX | Partner sandbox and developer portal | feature | DevEx, Support and Partnerships | 26 | EPIC-P2-DEVDOC | M: partner capacity | 3-5 design partners complete a test-mode integration; API v1 candidate frozen; feedback logged and triaged. | R5 | 7 |
| EPIC-P2-RISKCON | Risk, admin, incident consoles (basic), detection rules v1, limit engine | feature | Compliance, Risk and Privacy | 44 → 42 | EPIC-P2-COMPLIANCE | M: privilege creep | Risk can pause a mandate, merchant, token and set the delegation pause bit, and cannot widen authority (tested); the admin console cannot change on-chain customer authority; the P1 subset of section-23 detections, including quote-signer and revalidation rules, is implemented with alert routing tested; the limit engine enforces BACKEND_ONLY controls with two-approver loosening. | RG-006 | 8 |
| EPIC-P2-LOAD | Load, soak and chaos testing | infrastructure | Quality | 32 | EPIC-P2-SUBS | M: test environment fidelity | Sustained 3x expected beta peak for 24 hours with SLOs met; chaos scenarios (RPC lies, DB failover, queue backlog, quote-signer outage, flag-service outage) pass without double charge or lost event. | RG-009 | 8 |
| EPIC-P2-REFUNDS | Merchant-push refunds and refund accounting | feature | Payments Core | 16 | EPIC-P1-LEDGER; OD-007 | M: refund funding model (OD-007) | Full and partial refund flows post correct journals; a refund cannot exceed the original payment; a duplicate refund request is idempotent; refunds do not restore cap usage. | RG-007 | 7 |
| EPIC-P2-LEGALPACK | Terms, consent copy, privacy notice, DPIA, notice templates, legal sign-off pack | compliance | Compliance, Risk and Privacy | 24 → 23 | EPIC-P0-LEGAL | H: RISK-009, RISK-010, RISK-017 | Counsel signs consent and disclosure copy per jurisdiction, including dual-cap, delegation, router-specific authorization and migration-notice keys; DPIA completed; data-subject request process tested end to end. | RG-008 | 8 |
| EPIC-P2-A11YL10N | Accessibility and localization completion | feature | Product and Design | 28 | EPIC-P2-CHECKOUT | M | An independent WCAG 2.2 AA audit has no open A or AA failures on checkout and portal; RTL and launch locales pass visual and string tests; consent and migration copy back-translated and checked. | RG-008 | 7 |
| EPIC-P2-DEPLOYPREP | Mainnet deployment tooling, ceremony and migration rehearsal (absence proof, lineage lifecycle) | protocol | Protocol and Contracts | 28 → 27 | EPIC-P1-CONTRACTS | H: RISK-001 | The deployment script produces a signed manifest (including the absence-check result) and verifies bytecode against the audited build on forks of 2 chains; governance and guardian multisig plus timelock are rehearsed on testnet; a full router deprecate-migrate-sunset-retire cycle using successor mandates is rehearsed (PB-006). | RG-006 | 9 |
| EPIC-P2-RECON | Reconciliation and settlement reports (testnet) | data | Payments Core | 22 | EPIC-P1-LEDGER | H: RISK-016 | Daily reconciliation compares chain events, ledger, quotes and webhooks with zero unexplained differences over 14 consecutive testnet days. | RG-007 | 8 |
| EPIC-P2-PORTALS | Customer portal v1 and merchant dashboard v1 | feature | Checkout and Merchant Experience | 18 | EPIC-P2-PORTAL | L | Receipts, renewal reminders at 14/7/1 days, funding-readiness warnings, delegation status history, payment export. | R5 | 7 |
| EPIC-P2-COMPOPS | AML monitoring tooling, case management, KYB operations | compliance | Compliance, Risk and Privacy | 32 → 31 | EPIC-P2-COMPLIANCE | M | Transaction-monitoring rules produce alerts into a case queue; every case has SLA timers; the audit trail is immutable. | RG-008 | 8 |
| EPIC-P2-SUPPORTPREP | Support tooling and playbooks | feature | DevEx, Support and Partnerships | 16 → 15 | EPIC-P2-RUNBOOKS | L | Playbooks for all 19 support scenarios in prompt section 24, plus migration, delegation and conversion-disabled scenarios, tested by role-play. | RG-009 | 7 |
| EPIC-P2-MIGSVC | Migration orchestrator, campaign tooling, cohorts, notices and customer/merchant communications | migration | Payments Core | 30 → 32 → 35 | EPIC-P1-MIGRATION; EPIC-P2-PORTAL; EPIC-P2-MERCHANT | H: stranded mandates (RISK-026) | Campaigns can be created, staged by cohort, halted and closed; notices follow the 12 section 10 schedule with per-mandate tracking; merchant digests and webhooks are produced; metrics show stranded and unmigrated counts; the dry-run report lists every mandate with next charge date and prompt status. The campaign engine computes siblings per customer and router, holds sibling mandates (no failed charge and no dunning) while a migration is in flight, sequences the lockdown after the last sibling has moved in NORMAL mode, and switches to the EMERGENCY flow when the router is disabled, sunset, retired or security-deprecated. | RG-015 | 10 |

#### P3 — Private mainnet beta (W135-W150, recommended P50) — v1.0

| Epic | Name | Profile | Owner squad | pw (v0.2 → v0.5) | Depends on | Risk | Acceptance (epic) | Target | Stories |
|---|---|---|---|---|---|---|---|---|---|
| EPIC-P3-DEPLOY | Mainnet deployment ceremony (Router v1, no conversion code) | protocol | Protocol and Contracts | 28 → 26 | RG-005; EPIC-P2-DEPLOYPREP | H: RISK-001 | Contracts are deployed on Base and Arbitrum One from the signed manifest; bytecode is verified by two independent parties; deployer privileges are renounced; timelock and multisig configured; contracts verified on explorers (PB-012); the manifest records the absence-check result: no conversion selectors, no conversion contract (PB-040). | RG-010 | 9 |
| EPIC-P3-CANARY | Canary then design-partner rollout | infrastructure | Product and Design | 66 → 62 | EPIC-P3-DEPLOY | H: first real funds | Weeks 1-2 internal funds only; then at most 10 KYB-approved partners under limits; every payment reconciled; no unexplained difference; direct stablecoin settlement only. | R6 | 9 |
| EPIC-P3-LIMITS | Beta limits and circuit breakers (class R) with dual-cap alignment | compliance | Compliance, Risk and Privacy | 28 → 27 | EPIC-P2-RISKCON | H: limit bypass | Per-mandate, per-customer, per-merchant and global limits enforced; a breaker trips at 50% of limit and pauses new charges; limit changes need two approvers; quote refusals and band hits feed risk dashboards. | RG-010 | 8 |
| EPIC-P3-IRDR | Incident response and disaster recovery exercises | infrastructure | Platform, SRE and Security Engineering | 24 | EPIC-P2-LOAD | M | Tabletop plus live exercise for executor key compromise, RPC disagreement, quote-signer compromise and a hostile delegate; a restore drill meets RPO at most 1 minute and RTO at most 30 minutes (PROPOSAL); post-mortems closed. | RG-009 | 8 |
| EPIC-P3-BOUNTY | Private bug bounty (scope: contracts, lineage migration, quote verification, delegation revalidation) | security | Leadership and Program | 14 → 13 | RG-005 | M | Scope, rules and rewards published to invited researchers; triage SLA of 2 business days; first 30 days reviewed. | RG-010 | 8 |
| EPIC-P3-SUPPORT | Support operations and status page | infrastructure | DevEx, Support and Partnerships | 26 → 24 | EPIC-P2-SUPPORTPREP | M | Tiered support live with on-call escalation; status page live; customer and merchant communication templates (incl. migration and emergency) approved. | RG-009 | 8 |
| EPIC-P3-RECONPROD | Production reconciliation and settlement reporting | data | Payments Core | 18 | EPIC-P2-RECON | H | 28 consecutive days of 100% matched reconciliation including quote and fiat-valuation checks (public beta exit criterion). | RG-011 | 8 |
| EPIC-P3-LEGALGO | Legal go-live review | compliance | Compliance, Risk and Privacy | 22 → 21 | EPIC-P2-LEGALPACK | H: licensing | Written counsel confirmation for each launch jurisdiction covering consent, notices, delegation wording and router-specific authorizations (no conversion is offered in v1.0); licences or partner agreements in place. | RG-008 | 8 |
| EPIC-P3-TUNE | Alert and detection tuning | infrastructure | Platform, SRE and Security Engineering | 26 | EPIC-P3-CANARY | L | False-positive rate of paging alerts below 1 per on-call shift (PROPOSAL); detection rules v2 for observed patterns. | RG-011 | 8 |
| EPIC-P3-T1START | v1.0 surfaces build: embedded checkout, payment links, reporting (S02, S03, S23) | feature | Checkout and Merchant Experience | 62 | EPIC-P2-SUBS | M: iframe and postMessage hardening | S02, S03 and S23 pass security review and run in sandbox; not exposed to beta customers until P4; S08 is no longer in this epic (moved to v1.1). | RG-011 | 8 |
| EPIC-P3-TOKENOPS | Token registry operations, monitoring and conversion-approval process | compliance | Protocol and Contracts | 18 → 15 | EPIC-P1-TOKENREG | M | Weekly registry review; depeg and issuer-event playbooks exercised; revocation-flow evidence (EV-P11) refreshed for every listed token. | RG-004 | 8 |
| EPIC-P3-ITERATE | Beta feedback iteration (reserved capacity) | feature | Product and Design | 80 | - | M | Top beta issues by merchant impact closed; backlog groomed every 2 weeks. | RG-011 | 7 |
| EPIC-P3-MIGDRILL | Router migration live rehearsal (testnet to mainnet canary) | migration | Protocol and Contracts | 16 → 17 | EPIC-P2-DEPLOYPREP; EPIC-P2-MIGSVC | H: RISK-026 | A full lifecycle on a mainnet canary with internal accounts: register a candidate router, activate, deprecate with the minimum notice enforced, migrate through every partial state Q0..Q3 with successor mandates, sunset, and verify that a successor can still be created after sunset; zero stranded mandates; old permissions verified unusable before each successor activates. The drill includes a customer with two sibling mandates on the old router (NORMAL mode: the allowance stays until the last sibling has moved) and one EMERGENCY-mode run in which the router is disabled and every token of every mandate is made unusable first. | RG-015 | 9 |

#### P4 — Public beta (W151-W169, recommended P50) — v1.0

| Epic | Name | Profile | Owner squad | pw (v0.2 → v0.5) | Depends on | Risk | Acceptance (epic) | Target | Stories |
|---|---|---|---|---|---|---|---|---|---|
| EPIC-P4-CHAINS | Chain, wallet and token expansion for v1.0 (Optimism, Polygon) | protocol | Protocol and Contracts | 56 | RG-011 | H: new chain behavior | Each added chain has Permit2 bytecode evidence, a finality policy, token lab and wallet lab at E3 before enabling; chain-level pause tested; Ethereum L1 and BNB Smart Chain are not in this epic (v1.1). | RG-011 | 9 |
| EPIC-P4-T1 | Harden and complete v1.0 surfaces (S02, S03, S13, S23) | feature | Checkout and Merchant Experience | 48 | EPIC-P3-T1START | M | S02, S03, S13 and S23 meet section-7 acceptance criteria and pass pen test; S06 and S08 are no longer here (v1.1). | RG-011 | 8 |
| EPIC-P4-BOUNTYPUB | Public bug bounty and public contest or extended review | security | Leadership and Program | 22 | EPIC-P3-BOUNTY | M | Public program live; contest or extended review complete before the public-beta go decision (OD-019). | RG-011 | 8 |
| EPIC-P4-SCALE | Scale, performance and cost | infrastructure | Platform, SRE and Security Engineering | 64 | EPIC-P3-TUNE | M | SLOs met for 8 consecutive weeks at 3x launch volume; cost per payment within the unit-economics target. | RG-012 | 7 |
| EPIC-P4-FRAUD | Fraud risk engine v1 and AML monitoring v2 | compliance | Compliance, Risk and Privacy | 76 → 74 | EPIC-P2-COMPOPS | H | Fraud scores computed per payment with explainable features; manual review SLA met; precision and recall measured on beta data. | RG-012 | 8 |
| EPIC-P4-I18N | Additional locales | feature | Product and Design | 32 | EPIC-P2-A11YL10N | L | Each added locale passes string, RTL (where applicable) and consent back-translation checks. | RG-012 | 7 |
| EPIC-P4-MERCHANTOPS | Merchant underwriting at scale and merchant success | compliance | Compliance, Risk and Privacy | 44 → 42 | EPIC-P3-LIMITS | M | Tiered underwriting with automated KYB steps; limit tiers promoted by criteria, not by request. | RG-012 | 8 |
| EPIC-P4-DATA | Warehouse, product and financial analytics | data | Payments Core | 44 | EPIC-P3-RECONPROD | L | KPI-tree metrics available with documented definitions; PII minimization and retention enforced in the warehouse. | RG-012 | 8 |
| EPIC-P4-SECCONT | Continuous red team, access reviews, supply-chain hardening | security | Platform, SRE and Security Engineering | 40 | EPIC-P2-PENTEST | M | Quarterly access review complete; second pen test of new surfaces with no open critical or high findings. | RG-012 | 8 |
| EPIC-P4-COMPEXP | Additional jurisdictions and compliance expansion | compliance | Compliance, Risk and Privacy | 44 → 42 | OD-001 | H | Each new jurisdiction has written counsel confirmation before merchants there are enabled. | RG-012 | 8 |
| EPIC-P4-ITERATE | Public beta iteration (reserved capacity) | feature | Product and Design | 56 | - | M | Top beta issues by merchant impact closed; backlog groomed monthly. | RG-012 | 7 |
| EPIC-P4-DRDRILLS | DR drills, game days and migration-comms exercises | infrastructure | Platform, SRE and Security Engineering | 24 | EPIC-P3-IRDR | M | Quarterly game day executed; findings closed within 30 days. | RG-012 | 8 |
| EPIC-P4-MIGGAME | Migration campaign game day: customer and merchant communications at scale | migration | DevEx, Support and Partnerships | 14 | EPIC-P3-MIGDRILL; EPIC-P2-MIGSVC | M: RISK-026 | A simulated deprecation with 10,000 synthetic mandates: notices on schedule, merchant digests, support surge handled, phishing-imitation drill passed, emergency-disable communication within 1 hour for merchants and 24 hours for customers. | RG-015 | 8 |
| EPIC-P4-V11PREP | v1.1 readiness: Router v1.1 scope and plan, adapter selection, token-lab pair plans, peg and price-bound research, legal Q-03 | research | Protocol and Contracts | 36 → 40 | RG-011; RP-13; RP-14 | M | A written v1.1 plan: Router v1.1 and ConversionPolicyRegistry scope and audit plan, chosen stable-pair adapter design, pair list with lab plans, band proposals from historical depeg replay, counsel answer on Q-03, opt-in migration plan, and a staged rollout schedule. | RG-013 | 7 |

#### P5 — GA readiness (v1.0) (W170-W181, recommended P50) — v1.0

| Epic | Name | Profile | Owner squad | pw (v0.2 → v0.5) | Depends on | Risk | Acceptance (epic) | Target | Stories |
|---|---|---|---|---|---|---|---|---|---|
| EPIC-P5-GA | GA checklist closure (RG-012) | program | Leadership and Program | 84 → 80 | RG-011 | H: gate evidence gaps | Every GA prerequisite in prompt section 25 has evidence in the Release Gate Register; go/no-go signed by Head of Product, VP Engineering, CISO and Head of Compliance; the absence evidence for conversion code and the migration-readiness evidence are current. | RG-012 | 7 |
| EPIC-P5-OPSMAT | Operational maturity | infrastructure | Platform, SRE and Security Engineering | 54 | EPIC-P4-SCALE | M | Error budgets enforced; on-call load sustainable (at most 1 night page per week on average); quarterly DR proven. | RG-012 | 8 |
| EPIC-P5-DOCS | Public documentation, SLAs, migration guides and customer communications | feature | DevEx, Support and Partnerships | 32 | - | L | Public docs reviewed by legal; SLAs published; migration guides for router versions published. | RG-012 | 7 |
| EPIC-P5-DRILLS | Final IR, DR and chaos exercises | infrastructure | Platform, SRE and Security Engineering | 44 → 42 | EPIC-P4-DRDRILLS | M | Exercises on all Sev-1 runbooks completed in the 90 days before GA, including RB-032; open actions closed. | RG-009 | 8 |
| EPIC-P5-SLALEGAL | SLA, terms and merchant agreement finalization | compliance | Compliance, Risk and Privacy | 22 → 21 | EPIC-P4-COMPEXP | M | Counsel-approved final terms in every jurisdiction, including router-lifecycle notice terms. | RG-008 | 8 |
| EPIC-P5-SUPPORT247 | 24x7 support operations | infrastructure | DevEx, Support and Partnerships | 44 → 42 | EPIC-P3-SUPPORT | M | 24x7 coverage with documented escalation; median first-response time meets target. | RG-009 | 8 |
| EPIC-P5-PERFCOST | Performance and cost optimization | infrastructure | Platform, SRE and Security Engineering | 40 | EPIC-P4-SCALE | L | Cost per payment (gas sponsorship, RPC, signing, infrastructure) is at or below the target set in the unit-economics model at p90 gas prices, measured over 4 consecutive weeks of production traffic. | RG-012 | 7 |
| EPIC-P5-RELREADY | Release readiness | program | Leadership and Program | 22 → 20 | - | M | Release plan, rollback plan and communications ready; freeze period observed. | RG-012 | 6 |

#### P6 — v1.1: stablecoin conversion enablement, repeat and variable billing (W182-W206, recommended P50) — v1.1

| Epic | Name | Profile | Owner squad | pw (v0.2 → v0.5) | Depends on | Risk | Acceptance (epic) | Target | Stories |
|---|---|---|---|---|---|---|---|---|---|
| EPIC-P6-ADAPTER | First production stable-pair conversion adapter (route class STABLE) | protocol | Protocol and Contracts | 40 | EPIC-P4-V11PREP; EPIC-P6-ROUTERV11 | H: RISK-014, RISK-024 | The adapter takes typed parameters only, calls only registry-listed targets with fixed selectors, enforces minOut by balance delta and a price-impact cap, returns residue, and passes I-NOARB and I-ZEROBAL on forks with adversarial ordering; conversion through it is reachable only when conditions C1 and C2 hold (the router version contains conversion code and the registry has approved the adapter and the pair). | RG-013 | 8 |
| EPIC-P6-ADAPTERAUDIT | Independent audit of the stable-pair adapter and remediation | security | Protocol and Contracts | 36 | EPIC-P6-ADAPTER | H: audit findings (RISK-012) | A separate audit engagement covers the adapter and its integration; all critical and high findings are fixed and re-reviewed; final report archived; RG-013 criterion 1 met. | RG-013 | 8 |
| EPIC-P6-CONVBACKEND | Conversion backend: routing providers, simulation, price impact, depeg monitor, private submission, ledger journals, UX | feature | Payments Core | 70 | EPIC-P6-ROUTERV11; EPIC-P6-ADAPTER | H: conversion mistakes cost customers money | Routes are quoted, simulated across at least two RPC sources, compared with bands, executed with minOut, and reconciled; conversion journals post and balance on testnet for 14 consecutive days; customer copy explains token substitution; unexpected token selection is explainable in the portal. | RG-013 | 8 |
| EPIC-P6-TOKENLABSTABLE | Token-lab approvals for stable pairs (defines and issues labApprovalHash records) | research | Protocol and Contracts | 16 | EPIC-P4-V11PREP | M | Each approved pair has a labApprovalId with evidence for the 12 behavior classes, issuer-power review, depeg history, liquidity depth at maximum trade size and price-impact results; two approvers signed. | RG-013 | 6 |
| EPIC-P6-FLAGROLLOUT | Staged rollout of stable conversion (rollout switch R) and kill-switch drills | infrastructure | Product and Design | 24 | EPIC-P6-AUDITV11; EPIC-P6-ADAPTERAUDIT; EPIC-P6-CONVBACKEND; EPIC-P6-TOKENLABSTABLE; EPIC-P6-OPTIN | H: RISK-028 | Stages internal, one merchant, cohort, general availability each pass exit metrics and a hold period; conditions C1 (customers opted in to Router v1.1) and C2 (ConversionPolicyRegistry class open, adapter and pair registered) are verified at each stage; R is enabled by two approvers; the kill switch closes R in under 60 seconds and C2 via the guardian in the drill; R is never counted as a protection. | RG-013 | 8 |
| EPIC-P6-REPEAT | One-click repeat purchase (S06) | feature | Checkout and Merchant Experience | 36 | RG-012 | M | A mandate with merchant scope and per-purchase caps supports repeat purchases with one confirmation; both cap families apply; revoke and portal views work. | RG-011 | 7 |
| EPIC-P6-VARSUBS | Variable subscriptions (S08) | feature | Payments Core | 44 | RG-012 | M | Charges vary within the per-payment caps; notification threshold and price-change consent work; the customer sees both limits; disputes have a documented path. | RG-011 | 7 |
| EPIC-P6-CHAINS2 | Ethereum L1 and BNB Smart Chain onboarding | protocol | Protocol and Contracts | 60 | RG-012 | H: gas cost on L1; BNB wallet landscape | Each chain has E3 wallet and token evidence, finality policy, Permit2 verification and deployment; activation cost model documented for L1. | RG-011 | 8 |
| EPIC-P6-QUOTEPAIRS | PriceQuote v2 (route-bound) and pair-specific bands, peg monitoring | feature | Chain Infrastructure | 24 | EPIC-P4-V11PREP | M: RISK-025 | PriceQuote v2 uses its own domain version and type hash and cannot validate on Router v1; pair bands apply with intersection semantics; independent-source peg monitoring tightens off-chain limits automatically; false-rejection rate is within target in replay. | RG-013 | 7 |
| EPIC-P6-COMPLV11 | Compliance for conversion and variable billing | compliance | Compliance, Risk and Privacy | 30 | EPIC-P4-V11PREP | H: Q-03 | Counsel confirmation covers conversion in each jurisdiction where it is enabled; disclosures and consent copy updated; monitoring rules cover conversion patterns. | RG-013 | 8 |
| EPIC-P6-OPSV11 | Operations for v1.1: monitoring, runbooks, depeg and kill-switch drills | infrastructure | Platform, SRE and Security Engineering | 24 | EPIC-P6-FLAGROLLOUT | M | Conversion dashboards, alerts and RB-016/RB-033 drills complete; on-call trained. | RG-013 | 8 |
| EPIC-P6-BAU | GA operations and sustaining engineering (reserved capacity) | infrastructure | Leadership and Program | 90 | RG-012 | M | GA incident response, defect fixes, security patches and merchant requests handled within SLA while v1.1 proceeds. | RG-012 | 8 |
| EPIC-P6-ROUTERV11 | Router v1.1: typed conversion entrypoints, PriceQuote v2 verification, ConversionPolicyRegistry integration | protocol | Protocol and Contracts | 60 → 70 (new in 0.3) | EPIC-P4-V11PREP; RG-012 | H: new fund-moving logic (RISK-001, RISK-014) | Router v1.1 adds typed conversion entrypoints for Protocols A and B, PriceQuote v2 verification, minOut by balance delta, price-impact checks and residue return, and consults ConversionPolicyRegistry (class open, adapter code hash, pair approval hash); every v1 invariant still holds; I-NOARB holds (adapter targets only from the registry); it is registered through the lifecycle as a new version with its own domain. Includes the v1.1 `MandateManager`, which accepts the conversion consent in a non-zero extension field (a v1.0 manager refuses it), and reads cycle records from the previous manager through an immutable address; it is audited with the router. Adoption is a new mandate, not an `activateSuccessor` ([12 §5.7]). | RG-013 | 10 |
| EPIC-P6-AUDITV11 | Independent audit of Router v1.1 and ConversionPolicyRegistry, remediation, re-review | security | Protocol and Contracts | 40 → 44 (new in 0.3) | EPIC-P6-ROUTERV11 | H: findings volume (RISK-012) | A new-router-version audit (full review of changed and new paths, not only a diff) with no open critical or high findings; reports archived; RG-013 criterion 1 met. The audit scope includes the v1.1 `MandateManager` and the previous-manager lookup. | RG-013 | 8 |
| EPIC-P6-OPTIN | Opt-in migration to Router v1.1: campaign tooling, consent copy and rollout | migration | Payments Core | 30 (new in 0.3) | EPIC-P6-ROUTERV11; EPIC-P2-MIGSVC | M: response rate (ASM-028) | Customers can opt in to Router v1.1 with a router-specific successor authorization that states the new capability (conversion), its risks and the old permission revocation; customers who do nothing remain on Router v1 unchanged; new customers can start on Router v1.1; campaign metrics show opt-in rate and zero stranded mandates. Adoption is a new mandate in the v1.1 manager with caps equal to the old mandate's remaining headroom, the customer's conversion consent, and the old mandate and old router permission revoked ([12 §5.7]); it is never an `activateSuccessor`. | RG-013 | 8 |

#### P7 — v2.0: general-token conversion, Router v2, new surfaces (indicative) (W207-W292, recommended P50) — v2.0

| Epic | Name | Profile | Owner squad | pw (v0.2 → v0.5) | Depends on | Risk | Acceptance (epic) | Target | Stories |
|---|---|---|---|---|---|---|---|---|---|
| EPIC-P7-ROUTERV2 | Router v2 (multi-recipient settlement for splits, usage hooks) and registry registration | protocol | Protocol and Contracts | 90 | RG-013 | H: new fund-moving logic | Router v2 implements split settlement with I-MINOUT per recipient, all existing invariants, and the migration hooks; registered through the lifecycle with the minimum notice; no change to Router v1 behavior. | RG-014 | 9 |
| EPIC-P7-AUDITV2 | Two audits of Router v2 and conversion class GENERAL integration | security | Protocol and Contracts | 80 | EPIC-P7-ROUTERV2; EPIC-P7-GENCONV | H | Critical and high findings fixed and re-reviewed; GENERAL route class and oracle integration are in scope. | RG-014 | 8 |
| EPIC-P7-MIGCAMP | Router v1 to v2 migration campaign | migration | Payments Core | 60 | EPIC-P7-AUDITV2; EPIC-P2-MIGSVC | H: RISK-026 | Deprecation with the 180-day minimum notice; cohort-staged prompts; at least 90% migrated or reactivated before sunset; zero stranded mandates; old permissions revoked for migrated customers; rollback window honored. | RG-015 | 8 |
| EPIC-P7-GENCONV | General-token conversion: routes, adapters, backend, UX (route class GENERAL) | protocol | Protocol and Contracts | 90 | RG-013 | H: volatile assets | General routes pass per-token approvals, oracle-bounded quotes, MEV protections and kill-switch drills; enablement is per token and per scope. | RG-014 | 9 |
| EPIC-P7-ORACLE | Oracle-referenced price bounds for volatile tokens | protocol | Chain Infrastructure | 50 | OD-027 | H: RISK-025 | Oracle references with staleness and deviation limits are configured per token; quotes outside the oracle band revert; staleness handled fail-closed. | RG-014 | 8 |
| EPIC-P7-TOKENLABGEN | Token-lab approvals for general tokens | research | Protocol and Contracts | 40 | EPIC-P6-TOKENLABSTABLE | M | Each approved token passes manipulation-resistance analysis and an observation period; approvals recorded. | RG-014 | 6 |
| EPIC-P7-USAGE | Usage-based billing (S09) | feature | Payments Core | 44 | EPIC-P7-ROUTERV2 | M | Metered usage is verifiable and capped on chain; disputes have a path. | RG-014 | 7 |
| EPIC-P7-TOPUP | Auto top-up (S10) | feature | Payments Core | 36 | EPIC-P7-ROUTERV2 | M | Balance-triggered top-ups are capped, loop-protected and revocable. | RG-014 | 7 |
| EPIC-P7-SPLITS | Marketplace split payments (S11) | feature | Payments Core | 60 | EPIC-P7-ROUTERV2; EPIC-P7-COMPLV2 | H: compliance perimeter | Splits settle atomically to registered recipients with exact amounts and ledger journals; compliance sign-off for the perimeter. | RG-014 | 7 |
| EPIC-P7-WHITELABEL | White-label checkout (S24) | feature | Checkout and Merchant Experience | 36 | RG-012 | M | Brand isolation, custom domains and CSP are secure; anti-phishing rules hold. | RG-014 | 7 |
| EPIC-P7-PARTNERAPI | Partner platform API (S25) | feature | Payments Core | 48 | RG-012 | M | Platform/tenant hierarchy, delegated onboarding and scoped keys work; isolation tests pass. | RG-014 | 7 |
| EPIC-P7-COMPLV2 | Compliance for general conversion, splits and new jurisdictions | compliance | Compliance, Risk and Privacy | 40 | RG-013 | H | Counsel confirmation for general conversion and splits; monitoring rules updated. | RG-014 | 8 |
| EPIC-P7-BAU | Sustaining engineering and operations (reserved capacity) | infrastructure | Leadership and Program | 140 | RG-012 | M | Incidents, patches and merchant requests handled within SLA throughout v2.0 work. | RG-012 | 8 |

<!-- END:EPICS -->

## 7. Release phases: scope and gates (prompt §25)

All numeric limits are **PROPOSALS** for Risk and Finance to confirm. "Entry" and "exit" cite gates defined in [08](08-production-blockers-and-release-gates.md); dates are in §3.2. In every phase through GA, **conversion does not exist in the contracts**: direct stablecoin settlement only.

**Which tier each release phase belongs to (§3.1).**

| Release phase | Tier | Milestones that mark it (§3.2) |
|---|---|---|
| R1 Internal architecture validation | Tier 1 (testnet reference implementation) | TRI-1 (RG-016) |
| R2 Local and fork prototype | Tier 1, then tier 2 | TRI-2 and TRI-3 are reached inside it; its exit RG-002 is PMB-4 |
| R3 Public testnet alpha | Tier 1 for the first public-testnet deployment and rehearsal (TRI-4); tier 2 for the alpha program with external testers | TRI-4; PMB-4 |
| R4 Internal dogfood, R5 Partner sandbox | Tier 2 (prerequisites of RG-010; no mainnet funds before RG-005) | between PMB-4 and PMB-6 |
| R6 Private mainnet beta | Tier 2 | PMB-12 (RG-010) is its entry; its exit is RG-011 in tier 3 |
| R7 Public beta, R8 General availability | Tier 3 | GA-13 (RG-011), GA-14 (RG-012) |
| Post-GA (v1.1, v2.0) | Tier 3, labeled post-GA | GA-15 (RG-013), GA-16 (RG-014, indicative) |

### R1 — Internal architecture validation (P0) — tier 1
- **Chains / wallets / tokens:** none deployed; forks for research; wallet and token labs on testnets.
- **Merchants:** 20 interviews. **Contracts:** spike code only, discarded or rewritten under review; **no conversion code written**. **Audit:** none. **Legal:** perimeter memo; name clearance.
- **Entry:** funding and leadership in place; counsel engaged. **Exit: RG-016 (protocol freeze), then RG-001.** **Rollback:** pivot or stop.

### R2 — Local and fork prototype (P1) — tiers 1 and 2
- **Chains:** local and mainnet forks. **Tokens:** mocks plus fork tokens.
- **Contracts:** v0.x unaudited; invariant suites for all `I-*`; absence checks in CI. **Audit:** package prepared.
- **Entry:** RG-016, RG-001. **Exit: RG-002** (feature complete, audit freeze). **Rollback:** branch revert; flags off.

### R3 — Public testnet alpha (P2) — tier 1 (reference deployment) and tier 2 (alpha program)
- **Scope:** exactly the list in [14 §4](14-protocol-freeze-pack.md). **Chains:** Sepolia, Base Sepolia, Arbitrum Sepolia. **Wallets:** those with testnet lab evidence ([15](15-wallet-lab-matrix.md)). **Tokens:** test tokens. **Merchants:** test mode.
- **Contracts:** v0.9 on testnet, labeled unaudited. **Audit:** in progress. **Legal:** testnet terms.
- **Entry:** RG-002 and a minimum Compatibility Register. **Exit:** activation completion measured per wallet; no open critical defects; all scenarios of [14 §4.4](14-protocol-freeze-pack.md) pass. **Rollback:** redeploy new testnet contracts.

### R4 — Internal dogfood (P2) — tier 2
- **Chains:** testnets (no mainnet funds before RG-005). **Exit:** one full subscription lifecycle per supported path, including one router migration by successor mandate, with ledger reconciliation at 100%.

### R5 — Partner sandbox (P2) — tier 2
- **Merchants:** 3–5 design partners in test mode. **Exit:** integration complete; API v1 candidate frozen; webhook behavior verified. **Rollback:** sandbox reset.

### R6 — Private mainnet beta (P3) — tier 2 (entry RG-010)
- **Chains:** Base and Arbitrum One. **Wallets:** E3-passed list only. **Tokens:** two stablecoins per chain. **Merchants:** ≤10 KYB'd design partners. **Settlement: direct stablecoin only; absence of conversion code proven by the deployment manifest (PB-040).**
- **Limits (PROPOSAL):** per mandate ≤ 250 settlement units per period; per customer ≤ 1,000 per day; per merchant ≤ 10,000 per day; global ≤ 50,000 per day; automatic breakers at 50% of each (class `BACKEND_ONLY`, [11](11-dual-cap-model.md)).
- **Contracts:** audited Router v1 with signed manifest, bytecode verified (PB-001). **Audit:** RG-005 closed. **Monitoring:** 24×7 paging for payment and security alerts. **Support:** business hours + on-call. **Legal:** RG-008.
- **Entry: RG-010.** **Exit:** 4 consecutive weeks of 100% reconciliation; no Sev-1; IR and DR exercises passed; private bounty live; migration drill complete → **RG-011** (public beta). **Rollback:** guardian pauses recurring and/or Pay Once; merchant kill-switch; fall back to sandbox; customers keep full exit.

### R7 — Public beta (P4) — tier 3
- **Chains:** + Optimism, Polygon. **Merchants:** open onboarding with underwriting tiers. **Surfaces:** + S02, S03, S13, S23. **Conversion:** does not exist. **Bounty:** public, plus contest or extended review (OD-019).
- **Exit: RG-012 prerequisites** and sustained SLOs for ≥8 weeks. **Rollback:** tier limits lowered; chain-level pause; token delisting runbook.

### R8 — General availability (P5) — tier 3
- All gates closed; 24×7 support; public status page; SLAs published; bug bounty live; migration protocol rehearsed and RG-015 evidence current. **Exit: RG-012.**

### Post-GA — tier 3, labeled post-GA
- **v1.1:** Router v1.1 and `ConversionPolicyRegistry` built and independently audited; adapter audited; opt-in migration (RG-015); stablecoin conversion enabled in stages under RG-013 (conditions C1 and C2 first, the rollout switch last); Ethereum and BNB; S06, S08.
- **v2.0 (indicative):** general-token conversion under RG-014; Router v2; migration campaign under RG-015.

## 8. Jira import notes

- File: [jira/backlog.csv](jira/backlog.csv), UTF-8, comma-separated, all fields quoted.
- Map on import: `Issue id` → Issue id, `Parent` → Parent (story → epic by `Issue id`), `Epic Name` → Epic Name, `Original Estimate` → Original Estimate (epics in weeks, stories in days; adjust if your Jira defines a week differently from 5 days), `Labels` → Labels (includes `profile_<name>`), `Component/s` → Component/s.
- Additional columns `Story Type` (shown as *Research task*, *Compliance control* or *Program action* for the implementation stories of those profiles), `Epic Profile`, `Owner Role`, `Dependencies`, `Risk`, `Acceptance Criteria`, `Evidence`, `Release Target`, `Phase`, `Scope Version`, `Estimate Change` can be mapped to custom fields; the same content is **also written into the Description**, so nothing is lost if they are not mapped. Migration requirements and operational-readiness tasks appear both as stories and in the epic Description when the profile includes them.
- The Jira workflow must enforce the requirement template: a story cannot move to *Ready* without acceptance criteria and test method (`EPIC-P0-DOCS`). Profile compliance is checked by `build_backlog.py --check`, not by Jira.
