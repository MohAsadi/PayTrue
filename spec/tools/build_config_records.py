#!/usr/bin/env python3
"""Configuration records for the production-blocking constants PC-01...PC-19 (revision 0.5).

Data:       spec/config/pc_records.json   (the only place a record is edited)
Generated:  spec/18-configuration-records.md   (never edited by hand)

Run:   python -I spec/tools/build_config_records.py --write     regenerate document 18 from the JSON, deterministically
       python -I spec/tools/build_config_records.py --verify    run the checks below; exit code 1 on any failure
       python -I spec/tools/build_config_records.py             print the summary line only

Checks (--verify)
  [1] every PC id of 16 section 7 has a record, and where 16 states a number the record states the same number
      (the testnet values of 16 section 6 are compared too)
  [2] every required field of every record is present and non-empty (VALUE_PENDING is allowed for PC-05 only)
  [3] every numeric proposal lies inside [hardMin, hardMax], units are present, displays agree with the numbers
  [4] the cross-constraints hold on the proposals (executable predicates; testnet values are checked as warnings)
  [5] no record is APPROVED unless every approver slot has a name, a date and an evidence id; a slot that is not
      signed carries no name, date or evidence
  [6] every referenced identifier exists in spec/*.md (the ids of revision 0.5 that are still being created are
      whitelisted below); the generated document is excluded from the definitions
  [7] the generated document equals what --write would produce, and its markdown links resolve
  [8] drift between the records and the documents or the vector tool: warnings only (--strict makes them failures)
  [9] the type strings, tags and domains of PC-09 equal the ones of eip712/types.json (the single source)

Nothing here approves, audits or tests anything: it checks that the register is complete, consistent and honest about
its own state.
"""
import argparse
import ast
import importlib.util
import json
import operator
import pathlib
import re
import sys

sys.dont_write_bytecode = True
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

TOOLS = pathlib.Path(__file__).resolve().parent
SPEC = TOOLS.parent
DATA = SPEC / "config" / "pc_records.json"
DOC = SPEC / "18-configuration-records.md"
FOUNDRY_TEST = SPEC / "foundry" / "test" / "ConfigRecords.t.sol"

KINDS = [
    "immutable constructor argument",
    "compile-time constant",
    "immutable registry minimum",
    "immutable registry ceiling",
    "deployment configuration that is practically hard to change",
]
UNITS = ["seconds", "basis points", "count", "version"]
CHANGE_CLASSES = ["FCR", "RE-AUDIT", "REDEPLOY"]
STATUSES = ["PROPOSED", "APPROVED"]
DECISIONS = ["NOT SIGNED", "SIGNED"]
PROPOSAL_STATUSES = ["PROPOSED", "VALUE_PENDING"]
CISO = "Head of Security (CISO)"
GATE_ORDER = ["RG-016", "RG-002", "RG-003", "RG-004", "RG-005", "RG-006", "RG-007", "RG-008", "RG-009", "RG-010", "RG-015", "RG-011", "RG-012"]
LEVELS = ["QUOTED", "DERIVED", "EXPECTED", "NOT_SPECIFIED"]

# Identifiers that revision 0.5 creates in documents still being edited (they may be referenced before they are defined).
WHITELIST = ["OD-035", "ASM-034…036", "RISK-035…037", "PB-054…056", "ACP-TV-25…44", "MIG-TV-30…45", "CAP-TV-23…32", "FZ-26…32",
             "EVL-15", "WL-36…40",
             "FG-23…24"]     # defined in tools/freeze_fingerprints.py; document 14 carries them once its table has been rewritten (warning only until then)

# Constraints that must exist, whatever else the data holds (normalized text of the executable predicate).
REQUIRED_EXPRS = [
    "QUOTE_SET_GRACE >= MAX_QUOTE_TTL",
    "QUOTE_SET_GRACE <= 2 * MAX_QUOTE_TTL",
    "MIN_NOTICE_SECURITY <= MIN_NOTICE_STANDARD",
    "RETENTION >= MIN_NOTICE_STANDARD",
    "MAX_EXPOSED_TOKENS_PER_ROUTER >= MAX_TOKENS_PER_MANDATE",
    "MAX_EXPOSED_TOKENS_PER_ROUTER <= MAX_BATCH * MAX_TOKENS_PER_MANDATE",
    "TIMELOCK_MIN_DELAY >= 24 * 3600",
    "MIN_RECIPIENT_CHANGE_DELAY >= 48 * 3600",
    "DAY == 86400 and WEEK == 604800 and THIRTY_DAYS == 2592000",
]

BANNED = [r"\bis approved\b", r"\bare approved\b", r"\bhas been (?:audited|approved|tested)\b", r"\bwas (?:audited|tested)\b",
          r"\bhave been (?:audited|approved|tested)\b"]

# Names that must not appear in any record: identifiers a document has declared not to exist.
RETIRED_NAMES = {"PIN_SCHEMA": "17 §5.3 says no PIN_SCHEMA exists: the layout of AccountPin is its type string (PC-09)"}


# ------------------------------------------------------------------------------------------------ helpers
def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_MODS = {}


def mod(name):
    if name not in _MODS:
        _MODS[name] = load_module(name, TOOLS / f"{name}.py")
    return _MODS[name]


def keccak_hex(data: bytes) -> str:
    return "0x" + mod("eip712_vectors").keccak256(data).hex()


def read(path):
    return pathlib.Path(path).read_text(encoding="utf-8").replace("\r\n", "\n")


def load_data():
    return json.loads(DATA.read_text(encoding="utf-8"))


def nonempty(v):
    if v is None:
        return False
    if isinstance(v, str):
        return v.strip() != ""
    if isinstance(v, (list, dict)):
        return len(v) > 0
    return True


def walk_strings(o, path=""):
    if isinstance(o, str):
        yield path, o
    elif isinstance(o, dict):
        for k, v in o.items():
            yield from walk_strings(v, f"{path}.{k}" if path else k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk_strings(v, f"{path}[{i}]")


def fmt_int(n):
    return f"{n:,}"


def split_cells(line):
    parts = re.split(r"(?<!\\)\|", line.strip())
    return [c.strip() for c in parts[1:-1]] if len(parts) > 2 else []


def md_section(text, number):
    """Text of the level-2 section that starts with '## <number>.'"""
    lines = text.split("\n")
    out, on, in_code = [], False, False
    for ln in lines:
        if ln.startswith("```"):
            in_code = not in_code
        if not in_code and re.match(r"^##\s", ln):
            if on:
                break
            if re.match(rf"^##\s+{number}\.", ln):
                on = True
                continue
        if on:
            out.append(ln)
    return "\n".join(out)


def table_rows(section_text):
    rows = []
    for ln in section_text.split("\n"):
        if ln.startswith("|"):
            c = split_cells(ln)
            if c:
                rows.append(c)
    return rows


UNIT_SECONDS = {"day": 86400, "days": 86400, "hour": 3600, "hours": 3600, "h": 3600, "minute": 60, "minutes": 60, "second": 1,
                "seconds": 1, "s": 1}
STATED = re.compile(r"(?<![\w.])(\d[\d,]*)\s*(days?|hours?|minutes?|seconds?|bps|h|s)\b")


def numbers_in(text, allow_count=True):
    """Numbers with a unit in a free-text cell of document 16, as (kind, value); a leading unit-less integer is a count."""
    clean = text.replace("`", "")
    out = []
    for m in STATED.finditer(clean):
        n = int(m.group(1).replace(",", ""))
        u = m.group(2)
        out.append(("bps", n) if u == "bps" else ("seconds", n * UNIT_SECONDS[u]))
    if not out and allow_count:
        m = re.match(r"^\s*[≥≤<>~]?\s*(\d[\d,]*)\b(?!\s*§)", clean)
        if m:
            out.append(("count", int(m.group(1).replace(",", ""))))
    return out


def display_value(display, unit):
    """Parse a display such as '180 days' to its value in the base unit of `unit`; None if it cannot be parsed."""
    m = re.fullmatch(r"\s*(\d[\d,]*)\s*([A-Za-z ]*?)\s*(?:\(.*\))?\s*", display)
    if not m:
        return None
    n = int(m.group(1).replace(",", ""))
    w = m.group(2).strip().lower()
    if unit == "seconds":
        return n * UNIT_SECONDS[w] if w in UNIT_SECONDS else None
    if unit == "basis points":
        return n if w in ("bps", "basis points") else None
    if unit in ("count", "version"):
        return n if not any(w == k for k in UNIT_SECONDS) and w not in ("bps", "basis points") else None
    return None


# ------------------------------------------------------------------------------------------------ expressions
_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.FloorDiv: operator.floordiv}
_CMP = {ast.GtE: operator.ge, ast.LtE: operator.le, ast.Gt: operator.gt, ast.Lt: operator.lt, ast.Eq: operator.eq, ast.NotEq: operator.ne}


class Pending(Exception):
    pass


def eval_expr(expr, env):
    """Evaluate a predicate or arithmetic expression over named integers. Only names, integers, + - * //, comparisons,
    `and`, `or` are allowed; nothing else can be written in the data file."""
    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, int) and not isinstance(n.value, bool):
            return n.value
        if isinstance(n, ast.Name):
            if n.id not in env:
                raise KeyError(n.id)
            if env[n.id] is None:
                raise Pending(n.id)
            return env[n.id]
        if isinstance(n, ast.BinOp) and type(n.op) in _BIN:
            return _BIN[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.Compare):
            left = ev(n.left)
            for op, right_node in zip(n.ops, n.comparators):
                right = ev(right_node)
                if type(op) not in _CMP or not _CMP[type(op)](left, right):
                    return False
                left = right
            return True
        if isinstance(n, ast.BoolOp):
            vals = [ev(v) for v in n.values]
            return all(vals) if isinstance(n.op, ast.And) else any(vals)
        raise ValueError(f"expression element not allowed: {type(n).__name__}")
    return ev(ast.parse(expr, mode="eval"))


def norm_expr(e):
    return re.sub(r"\s+", " ", e.strip())


def production_env(data):
    env = {}
    for r in data["records"]:
        for q in r["proposal"]["quantities"]:
            env[q["symbol"]] = q.get("value")
    return env


def testnet_env(data):
    env = production_env(data)
    for r in data["records"]:
        for q in r["proposal"]["quantities"]:
            t = q.get("testnet")
            if t and t.get("value") is not None:
                env[q["symbol"]] = t["value"]
    return env


# ------------------------------------------------------------------------------------------------ document links and macros
def link_docs(text):
    """{11 §4.1} becomes [11 §4.1](11-dual-cap-model.md); {file:evidence/permit2/pin.json} becomes a link to that file.
    A document number without a file is an error; a missing file is caught by the link check of --verify."""
    def rep(m):
        files = sorted(SPEC.glob(f"{m.group(1)}-*.md"))
        if not files:
            raise ValueError(f"no document numbered {m.group(1)} (in {text[:60]!r})")
        return f"[{m.group(1)}{m.group(2) or ''}]({files[0].name})"
    text = re.sub(r"\{file:([^}\s]+)\}", lambda m: f"[{m.group(1)}]({m.group(1)})", text)
    return re.sub(r"\{(\d\d)((?: §[^}]*)?)\}", rep, text)


def expand_hash(cell, row):
    def rep(m):
        if m.group(1) == "hash":
            lit = row[int(m.group(2))].strip().strip("`")
        else:
            lit = m.group(2)
        return "`" + keccak_hex(lit.encode("utf-8")) + "`"
    return re.sub(r"\{\{(hash|hashof):([^}]*)\}\}", rep, cell)


def cell(text):
    return link_docs(str(text)).replace("\n", " ").replace("|", "\\|")


def para(text):
    return link_docs(str(text))


def present(v):
    return v if nonempty(v) else "—"


def fmt_quantity(q, which):
    """Display of the value, hardMin or hardMax of a quantity, with its base-unit number for durations."""
    if which == "value":
        v, d = q.get("value"), q.get("display")
    elif which == "hardMin":
        v, d = q.get("hardMin"), q.get("hardMinDisplay")
    else:
        v, d = q.get("hardMax"), q.get("hardMaxDisplay")
    if v is None:
        return d or "pending"
    if q["unit"] == "seconds" and not str(d).lower().endswith("seconds"):
        return f"{d} ({fmt_int(v)} s)"
    return str(d)


def role_list(roles):
    return "; ".join(roles)


def approval_names(r):
    out = []
    for a in r["approval"]:
        out.append(f"{a['role']}" + (" (veto)" if a.get("veto") else ""))
    return "; ".join(out)


# ------------------------------------------------------------------------------------------------ rendering
def counts(data):
    recs = data["records"]
    approved = sum(1 for r in recs if r["status"] == "APPROVED")
    pending = sum(1 for r in recs if r["proposal"]["status"] == "VALUE_PENDING")
    return len(recs), approved, len(recs) - approved, pending


def summary_line(data):
    n, a, p, v = counts(data)
    return f"records: {n}, approved: {a}, proposed: {p}, value-pending: {v}"


def render_record(r):
    L = []
    pid = r["id"]
    L.append(f"### {pid} — {cell(r['name'])}" + ("  (NEW IN 0.5)" if r.get("newIn05") else ""))
    L.append("")
    if r.get("newIn05"):
        L.append(para(r["newIn05Note"]))
        L.append("")
    p = r["proposal"]
    syms = ", ".join(f"`{s}`" for s in r["symbols"])
    prop_syms = r.get("proposedSymbols", [])
    documented = [s for s in r["symbols"] if s not in prop_syms]
    L.append("| Field | Value |")
    L.append("|---|---|")
    L.append(f"| **Symbols** | {cell(syms)} |")
    if prop_syms:
        if not documented:
            note = "all of them: no document names these identifiers (proposed by the author of this record)"
        elif len(documented) <= len(prop_syms):
            note = ("all except " + ", ".join(f"`{s}`" for s in documented)
                    + ": no document names the others (proposed by the author of this record)")
        else:
            note = ", ".join(f"`{s}`" for s in prop_syms) + ": no document names them (proposed by the author of this record)"
        L.append(f"| **Proposed identifiers** | {cell(note)} |")
    L.append(f"| **Kind** | {cell(r['kind'])}" + (f" ({cell(r['kindNote'])})" if r.get("kindNote") else "") + " |")
    L.append(f"| **Enforced in** | {cell(r['enforcedIn'])} |")
    if p["status"] == "VALUE_PENDING":
        L.append(f"| **Proposed value** | **VALUE_PENDING** — {cell(p['text'])} |")
    else:
        L.append(f"| **Proposed value** | {cell(p['text'])} |")
    L.append(f"| **Unit** | {cell(p['unitLabel'])} |")
    L.append(f"| **Testnet value** | {cell(r['testnet']['text'])} |")
    L.append(f"| **Accountable owner** | {cell(role_list(r['owner']))} |")
    L.append(f"| **Consulted** | {cell(role_list(r['consulted']))} |")
    L.append(f"| **Required approvers** | {cell(approval_names(r))} |")
    g = r["releaseGate"]
    L.append(f"| **Release gate** | {g['gate']}; latest {g['latest']}; evidence closes at {g['evidenceGate']} — {cell(g['why'])} |")
    cc = r["changeControl"]
    L.append(f"| **Change control** | {', '.join(cc['classes'])} — {cell(cc['text'])} |")
    L.append(f"| **Status** | **{r['status']}** |")
    L.append("")
    rt = r["rationale"]
    L.append(f"**Rationale.** {para(rt['why'])}")
    L.append("")
    L.append(f"**Failure it prevents.** {para(rt['prevents'])}")
    L.append("")
    L.append(f"**Mine, not a decision.** {para(rt['mine'])}")
    L.append("")
    if r.get("judgements"):
        L.append("**Judgements made in this record** (to be confirmed or reversed by the approvers):")
        L.append("")
        for j in r["judgements"]:
            L.append(f"- {para(j)}")
        L.append("")
    L.append("**Evidence required to decide.**")
    L.append("")
    ev = r["evidence"]
    for e in ev["existing"]:
        L.append(f"- {e['id']}: {para(e['note'])}")
    L.append(f"- To be produced: {para(ev['toProduce'])}")
    L.append("")
    sr = r["safeRange"]
    L.append("**Safe range.**")
    L.append("")
    qs = p["quantities"]
    if qs:
        L.append("| Quantity | Proposal | Hard minimum | Hard maximum | Unit |")
        L.append("|---|---|---|---|---|")
        for q in qs:
            L.append(f"| `{q['symbol']}` | {cell(fmt_quantity(q, 'value'))} | {cell(fmt_quantity(q, 'hardMin'))} | "
                     f"{cell(fmt_quantity(q, 'hardMax'))} | {q['unit']} |")
        L.append("")
    if sr.get("rule"):
        L.append(f"- Rule: {para(sr['rule'])}")
    L.append(f"- Too low: {para(sr['tooLow'])}")
    L.append(f"- Too high: {para(sr['tooHigh'])}")
    L.append(f"- Can governance move it later: {para(sr['governance'])}")
    L.append(f"- Place of the proposal in the range: {para(sr['position'])}")
    L.append("")
    L.append("**Cross-constraints.** " + ", ".join(r["crossConstraints"]) + " (section 3).")
    L.append("")
    ts = r["tests"]
    L.append("**Tests.**")
    L.append("")
    if ts["existing"]:
        L.append("- Existing: " + ", ".join(ts["existing"]))
    else:
        L.append("- Existing: none")
    if ts.get("pending"):
        L.append("- Being created in revision 0.5 (the mapping to this record is to be confirmed when the documents are final): "
                 + ", ".join(ts["pending"]))
    L.append(f"- Foundry test, one per record, in `spec/foundry/test/ConfigRecords.t.sol` (status: planned; no run result is recorded): `{r['plannedTest']}`")
    L.append(f"- Note: {para(ts['note'])}")
    L.append("")
    if r.get("openPoints"):
        L.append("**Open points.**")
        L.append("")
        for o in r["openPoints"]:
            L.append(f"- {para(o)}")
        L.append("")
    it = r.get("items")
    if it:
        L.append(f"**{cell(it['title'])}**")
        L.append("")
        L.append("| " + " | ".join(it["columns"]) + " |")
        L.append("|" + "---|" * len(it["columns"]))
        for row in it["rows"]:
            L.append("| " + " | ".join(cell(expand_hash(c, row)) for c in row) + " |")
        L.append("")
        if it.get("note"):
            L.append(para(it["note"]))
            L.append("")
    L.append("**Approval block** (a signature needs a name, a date and at least one evidence id from the Evidence Register):")
    L.append("")
    L.append("| Required approver | Veto | Decision | Name | Date | Evidence ids |")
    L.append("|---|---|---|---|---|---|")
    for a in r["approval"]:
        L.append(f"| {cell(a['role'])} | {'yes' if a.get('veto') else 'no'} | **{a['decision']}** | {present(a['name'])} | "
                 f"{present(a['date'])} | {present(', '.join(a['evidenceIds']))} |")
    L.append("")
    return L


def render(data):
    recs = data["records"]
    n, approved, proposed, pending = counts(data)
    L = []
    L.append("# 18 — Production Configuration Records")
    L.append("")
    L.append("| Field | Value |")
    L.append("|---|---|")
    L.append(f"| Artifact | {data['artifact']} |")
    L.append(f"| Version | {data['revision']} (new) |")
    L.append(f"| Date | {data['date']} |")
    pend_ids = ", ".join(r["id"] for r in recs if r["proposal"]["status"] == "VALUE_PENDING")
    L.append(f"| Status | DRAFT — **no record is approved.** {n} records: {approved} approved, {proposed} proposed, {pending} without a value "
             f"({pend_ids}, `VALUE_PENDING`). Nothing here is audited, legally reviewed or tested on any chain |")
    L.append("| Owner | Principal Blockchain Architect (accountable), Technical Program Manager (register) |")
    L.append("| Reviewers | Head of Security (CISO, veto), Head of Compliance, Solidity Lead, Risk Lead, Finance, Payments PM, QA Lead |")
    L.append("| Dependencies | [16](16-freeze-decision-report.md) §7 (the constants) and §6 (testnet values), [14](14-protocol-freeze-pack.md) §2 and §7 "
             "(fingerprints, change control), [08](08-production-blockers-and-release-gates.md) (gates), [11](11-dual-cap-model.md), "
             "[12](12-router-lifecycle-and-migration.md), [17](17-account-compatibility-policy.md), "
             "[03](03-assumptions-decisions-risks.md) (OD-016, OD-022, OD-023, OD-026, OD-027, OD-034), "
             "[config/pc_records.json](config/pc_records.json), [tools/build_config_records.py](tools/build_config_records.py) |")
    L.append("| Source of this file | **Generated.** Edit `config/pc_records.json`, then run `python -I spec/tools/build_config_records.py --write`; "
             "`--verify` fails if this file differs from the data |")
    L.append("| Definition of Done | Every production-blocking constant of [16](16-freeze-decision-report.md) §7, and the constant added in 0.5, has a record "
             "with an accountable owner, a unit, a rationale, the evidence required, a safe range, its tests and its release gate; no record "
             "is `APPROVED` unless every required approver has signed it with a name, a date and an evidence id; the verifier passes |")
    L.append("")
    L.append("**This register does not approve anything.** It turns each constant of [16](16-freeze-decision-report.md) §7 into a record that "
             "can be approved, one by one, by the people named in it. Today every record is `PROPOSED` and every signature slot is `NOT SIGNED`. "
             "A proposal is an unapproved number written down so that it can be reviewed; it is not a decision, and nothing in this "
             "workspace has been audited, legally reviewed, or tested on any wallet or chain.")
    L.append("")
    L.append("**Why 19 records.** The sponsor's correction named 17 production-blocking constants (PC-01…PC-17 of "
             "[16](16-freeze-decision-report.md) §7). The shared-allowance rework of [12 §5.3.1](12-router-lifecycle-and-migration.md) needs a bound on "
             "the exposure index (PC-18 `MAX_EXPOSED_TOKENS_PER_ROUTER`, new in 0.5), and the implementation of the quote-signer sets needs a bound on the "
             "members of a set (PC-19 `MAX_SIGNERS_PER_SET`, new in the implementation evidence), so the count has become **19**. The 17 original records keep "
             "their numbers; PC-04 was re-measured on the actual contracts (ADR-022).")
    L.append("")
    # --- 1 overview
    L.append("## 1. Overview")
    L.append("")
    L.append("| PC | Symbol | Proposal | Unit | Owner | Gate | Status |")
    L.append("|---|---|---|---|---|---|---|")
    for r in recs:
        p = r["proposal"]
        sym = r.get("overviewSymbol") or ", ".join(f"`{s}`" for s in r["symbols"])
        prop = p.get("overview") or p["text"]
        if p["status"] == "VALUE_PENDING":
            prop = "**VALUE_PENDING** (Finance, OD-016)"
        g = r["releaseGate"]
        L.append(f"| {r['id']} | {cell(sym)} | {cell(prop)} | {cell(p.get('overviewUnit') or p['unitLabel'])} | "
                 f"{cell(role_list(r['owner']))} | {g['gate']} (evidence {g['evidenceGate']}; latest {g['latest']}) | {r['status']} |")
    L.append("")
    # --- 2 rules
    L.append("## 2. Rules")
    L.append("")
    rules = [
        "**R-1 Approval.** A record is approved only by its own approval block: every required approver signs, and each signature carries a name, "
        "a date and at least one evidence id from the Evidence Register ([02](02-source-register.md)). A statement in a meeting, a value written in another "
        "document, a passing test on a testnet or an entry in this register is not an approval.",
        "**R-2 Veto.** The Head of Security (CISO) is a required approver of every record and holds a veto on all of them: all 18 constants are immutable or "
        "practically unchangeable parts of `SECURITY-CRITICAL` or `FINANCIAL-CONTROL` documents. A veto stands until withdrawn in writing "
        "([08](08-production-blockers-and-release-gates.md) §2, gate mechanics).",
        "**R-3 Status.** `PROPOSED` is the only status this file carries today. `APPROVED` is set only when every slot of the record is signed; "
        "the verifier rejects it otherwise. `VALUE_PENDING` is allowed for PC-05 only: no number is proposed for the fee ceiling.",
        "**R-4 Change after approval.** Changing an approved value is a change request, not an edit: a Freeze Change Request "
        "([14](14-protocol-freeze-pack.md) §7) once the freeze is approved, a re-audit of the affected contract once the audit has started, and "
        "a redeploy of the immutable contract. The field `changeControl` of each record says what the change costs. Editing the JSON file of a record "
        "that is `APPROVED` without a new signed block is a defect.",
        "**R-5 Testnet values are not evidence.** A `-testconst` build may differ from the audited source only in the constants of "
        "[16](16-freeze-decision-report.md) §6 (rule T-1); it is never promoted (T-2); the behavior that depends on each such constant is run "
        "once on a fork with the production value and a time warp before the audit starts (T-3). A test that passes with a testnet value says "
        "nothing about the production value.",
        "**R-6 Evidence.** The evidence listed in each record is what is required to decide, not what exists. Identifiers are those that exist in the "
        "specification; where nothing exists the record says so and names what must be produced. The verifier checks that every identifier exists; "
        "it cannot check what the evidence says.",
        "**R-7 Proposals and ranges.** Proposed values come from [16](16-freeze-decision-report.md) §7, [12](12-router-lifecycle-and-migration.md) §13 and OD-026, "
        "OD-027, OD-034 and are unapproved. The hard minimum and hard maximum of each record are the author's proposals for the approvers to confirm "
        "or change; they are not measurements. Parts of a record that are the author's own proposal are marked in its \"Mine, not a decision\" paragraph.",
        "**R-8 Gates.** Every constant is approved at the protocol freeze (RG-016) unless the record says its evidence arrives later. The audited bytecode "
        "carries the final values, so the audit freeze (RG-002, the code freeze of [08](08-production-blockers-and-release-gates.md) §2) is the latest "
        "moment; the audit completed at RG-005 covers those exact values. Where the evidence arrives after the audit freeze (counsel letters, rehearsals, "
        "unit economics) the record says so and the approval rests on a recorded risk acceptance; a negative result then costs a redeploy and a re-audit.",
        "**R-9 Not in this register.** `ROLLBACK_WINDOW` (governance-adjustable) and the backend-tunable values listed at the end of "
        "[16](16-freeze-decision-report.md) §7 are not production-blocking constants and have no record here.",
    ]
    for t in rules:
        L.append(para(t))
        L.append("")
    # --- 3 constraints
    L.append("## 3. Cross-constraints")
    L.append("")
    L.append("Each executable constraint is a predicate over the proposed numbers; `--verify` evaluates it on the production proposals (a failure is an "
             "error) and, for `both`, on the testnet values (a failure is a warning). Informative constraints are stated for the approvers and are not "
             "executable.")
    L.append("")
    env = production_env(data)
    tenv = testnet_env(data)
    L.append("| Constraint | Predicate or statement | Records | Scope | On the proposals | On the testnet values |")
    L.append("|---|---|---|---|---|---|")
    for c in data["constraints"]:
        if c.get("expr"):
            try:
                prod = "holds" if eval_expr(c["expr"], env) else "**violated**"
            except Pending:
                prod = "not evaluated (value pending)"
            try:
                test = "holds" if eval_expr(c["expr"], tenv) else "**violated**"
            except Pending:
                test = "not evaluated (value pending)"
            if c["scope"] == "production":
                test = "not applicable"
            stmt = f"`{c['expr']}` — {c['text']}"
        else:
            prod, test, stmt = "informative", "informative", c["text"]
        L.append(f"| {c['id']} | {cell(stmt)} | {', '.join(c['records'])} | {c['scope']} | {prod} | {test} |")
    L.append("")
    # --- 4 records
    L.append("## 4. Records")
    L.append("")
    for r in recs:
        L.extend(render_record(r))
    # --- 5 approval register
    L.append("## 5. Approval register")
    L.append("")
    L.append("Every slot of every record, in one table. A slot is changed only by editing the `approval` block of its record in the data file "
             "(R-1); this table follows.")
    L.append("")
    L.append("| PC | Required approver | Veto | Decision | Name | Date | Evidence ids |")
    L.append("|---|---|---|---|---|---|---|")
    for r in recs:
        for a in r["approval"]:
            L.append(f"| {r['id']} | {cell(a['role'])} | {'yes' if a.get('veto') else 'no'} | **{a['decision']}** | {present(a['name'])} | "
                     f"{present(a['date'])} | {present(', '.join(a['evidenceIds']))} |")
    L.append("")
    # --- 6 testnet
    L.append("## 6. Testnet values and the `-testconst` rule")
    L.append("")
    L.append("Only the constants of [16](16-freeze-decision-report.md) §6 may take a different value in a `-testconst` build. All other production-blocking "
             "constants keep their intended values on testnet ([14](14-protocol-freeze-pack.md) §4.5, rule 1).")
    L.append("")
    L.append("| PC | Production proposal | Testnet value |")
    L.append("|---|---|---|")
    for r in recs:
        p = r["proposal"]
        L.append(f"| {r['id']} | {cell(p.get('overview') or p['text'])} | {cell(r['testnet']['text'])} |")
    L.append("")
    # --- 7 verifier
    L.append("## 7. How to use the verifier")
    L.append("")
    L.append("```text")
    L.append("python -I spec/tools/build_config_records.py --write     regenerate this file from spec/config/pc_records.json")
    L.append("python -I spec/tools/build_config_records.py --verify    run the checks; exit code 1 if any fails (--strict: warnings fail too)")
    L.append("python -I spec/tools/build_config_records.py             print the summary line")
    L.append("```")
    L.append("")
    L.append("Checks: **[1]** every PC row of [16](16-freeze-decision-report.md) §7 has a record and the numbers agree (testnet values against §6); "
             "**[2]** every required field is present and non-empty; **[3]** every numeric proposal lies inside its safe range and every display agrees "
             "with its number; **[4]** the cross-constraints of section 3 hold; **[5]** no record is `APPROVED` without complete signatures; "
             "**[6]** every referenced identifier exists; **[7]** this file equals the generated text and its links resolve; **[8]** warnings for drift "
             "against the documents, the vector tool and the Foundry file.")
    L.append("")
    L.append("**To record an approval:** produce the evidence and register its `EV-` id; each approver fills `name`, `date`, `evidenceIds` and sets "
             "`decision` to `SIGNED` in the record's `approval` block; when every slot (including the CISO's) is signed set `status` to `APPROVED`; "
             "run `--write` and `--verify`. After the freeze a change is a Freeze Change Request (R-4).")
    L.append("")
    L.append("**What the verifier cannot do:** judge whether a value is right, read the content of evidence, or check anything on a chain. A passing run "
             "says the register is complete, consistent and honest about its state; it says nothing about the constants themselves.")
    L.append("")
    out = "\n".join(L)
    return re.sub(r"\n{3,}", "\n\n", out).rstrip("\n") + "\n"


# ------------------------------------------------------------------------------------------------ checks
def check_16(data):
    errs, warns = [], []
    t16 = read(SPEC / "16-freeze-decision-report.md")
    s7 = md_section(t16, 7)
    rows = table_rows(s7)
    if not rows:
        return ["cannot find the table of 16 section 7"], warns
    head = [c.lower() for c in rows[0]]

    def col(name, default):
        for i, h in enumerate(head):
            if name in h:
                return i
        return default
    ci_const, ci_prop, ci_owner = col("constant", 1), col("proposal", 2), col("owner", 6)
    recs = {r["id"]: r for r in data["records"]}
    seen = set()
    for row in rows:
        if not re.fullmatch(r"PC-\d\d", row[0]):
            continue
        pid = row[0]
        seen.add(pid)
        r = recs.get(pid)
        if not r:
            errs.append(f"{pid} is in 16 §7 but has no record")
            continue
        # the numbers are normally in the Proposal column; document 16 puts the window lengths of PC-10 in the Constant column
        stated = numbers_in(row[ci_prop]) + numbers_in(row[ci_const], allow_count=False)
        have = set()
        for q in r["proposal"]["quantities"]:
            if q.get("value") is not None:
                kind = {"seconds": "seconds", "basis points": "bps", "count": "count", "version": "count"}[q["unit"]]
                have.add((kind, q["value"]))
        for kind, n in stated:
            if (kind, n) not in have:
                errs.append(f"{pid}: 16 §7 states {n} ({kind}) but the record has {sorted(have) or 'no number'}")
        if r["proposal"]["status"] == "VALUE_PENDING" and stated:
            errs.append(f"{pid}: 16 §7 now states a number {stated} but the record is VALUE_PENDING")
        if not stated and r["proposal"]["status"] != "VALUE_PENDING" and have and pid not in ("PC-15",):
            warns.append(f"{pid}: 16 §7 states no number for the proposal; the record states {sorted(have)}")
        for sym in re.findall(r"`([A-Z][A-Z0-9_]{2,})`", row[ci_const]):
            known = set(r["symbols"]) | {s for s in re.findall(r"`([A-Z][A-Z0-9_]{2,})`", json.dumps(r.get("items", {})))}
            it = r.get("items") or {}
            if "Symbol" in it.get("columns", []):
                col_sym = it["columns"].index("Symbol")
                known |= {row[col_sym] for row in it["rows"]}
            if sym not in known:
                warns.append(f"{pid}: symbol `{sym}` of 16 §7 is not a symbol of the record")
        own = " + ".join(r["owner"]).lower()
        for part in re.split(r"\s*\+\s*", row[ci_owner].replace("/", "+")):
            if part and part.lower() not in own:
                warns.append(f"{pid}: owner '{part}' of 16 §7 is not among the record's owners {r['owner']}")
    for pid, r in recs.items():
        if pid not in seen and not r.get("newIn05"):
            errs.append(f"{pid} has a record but no row in 16 §7")
    for pid in sorted(set(recs) - seen):
        warns.append(f"{pid} is not (yet) in 16 §7 (flagged NEW IN 0.5 in the record)")
    # testnet values against 16 section 6
    s6 = table_rows(md_section(t16, 6))
    for r in data["records"]:
        sr = r["testnet"].get("sourceRow")
        if not sr:
            continue
        match = [row for row in s6 if len(row) >= 3 and sr.lower().replace("`", "") in row[0].lower().replace("`", "")]
        if not match:
            errs.append(f"{r['id']}: no row '{sr}' in 16 §6")
            continue
        qv = [q for q in r["proposal"]["quantities"] if q.get("testnet")]
        if qv:
            stated = numbers_in(match[0][2])
            want = qv[0]["testnet"]["value"]
            if not stated or stated[0][1] != want:
                errs.append(f"{r['id']}: testnet value {want} differs from 16 §6 ({match[0][2]!r})")
    # no row of 16 section 6 about a PC constant may be missing from the records
    return errs, warns


def check_fields(data):
    errs, warns = [], []
    for k in ["schema", "artifact", "revision", "date", "roles", "constraints", "records"]:
        if not nonempty(data.get(k)):
            errs.append(f"top-level field {k} is missing or empty")
    roles = data.get("roles", {})
    ids = [r.get("id") for r in data.get("records", [])]
    if len(set(ids)) != len(ids):
        errs.append("duplicate record ids")
    allsyms = {}
    alltests = {}
    cids = {c["id"] for c in data.get("constraints", [])}
    for c in data.get("constraints", []):
        for k in ("id", "text", "scope", "records"):
            if not nonempty(c.get(k)):
                errs.append(f"constraint {c.get('id')}: {k} is empty")
        if c.get("scope") not in ("production", "both", "informative"):
            errs.append(f"constraint {c.get('id')}: bad scope")
        if c.get("scope") != "informative" and not nonempty(c.get("expr")):
            errs.append(f"constraint {c.get('id')}: executable scope without expr")
        for pid in c.get("records", []):
            if pid not in ids:
                errs.append(f"constraint {c.get('id')}: unknown record {pid}")
    for r in data.get("records", []):
        pid = r.get("id", "?")

        def need(path, v):
            if not nonempty(v):
                errs.append(f"{pid}: required field {path} is missing or empty")
        for k in ["name", "kind", "enforcedIn", "symbols", "plannedTest", "owner", "consulted", "crossConstraints", "status"]:
            need(k, r.get(k))
        if r.get("kind") not in KINDS:
            errs.append(f"{pid}: kind {r.get('kind')!r} is not one of {KINDS}")
        p = r.get("proposal", {})
        for k in ["text", "status", "unitLabel"]:
            need(f"proposal.{k}", p.get(k))
        if p.get("status") not in PROPOSAL_STATUSES:
            errs.append(f"{pid}: proposal.status must be one of {PROPOSAL_STATUSES}")
        if p.get("status") == "VALUE_PENDING" and pid != "PC-05":
            errs.append(f"{pid}: VALUE_PENDING is allowed for PC-05 only")
        if pid == "PC-05" and p.get("status") != "VALUE_PENDING":
            errs.append("PC-05: the value is undecided (OD-016); the record must be VALUE_PENDING")
        if "quantities" not in p:
            errs.append(f"{pid}: proposal.quantities is missing (an empty list is allowed)")
        need("testnet.text", r.get("testnet", {}).get("text"))
        for k in ["why", "prevents", "mine"]:
            need(f"rationale.{k}", r.get("rationale", {}).get(k))
        ev = r.get("evidence", {})
        need("evidence.toProduce", ev.get("toProduce"))
        if not ev.get("existing") and not str(ev.get("toProduce", "")).lower().startswith("none yet"):
            errs.append(f"{pid}: no existing evidence ids, so evidence.toProduce must start with 'none yet'")
        for e in ev.get("existing", []):
            if not nonempty(e.get("id")) or not nonempty(e.get("note")):
                errs.append(f"{pid}: an evidence entry lacks id or note")
        for k in ["tooLow", "tooHigh", "governance", "position"]:
            need(f"safeRange.{k}", r.get("safeRange", {}).get(k))
        ts = r.get("tests", {})
        need("tests.note", ts.get("note"))
        if not ts.get("existing") and not ts.get("pending") and not str(ts.get("note", "")).lower().startswith("none yet"):
            errs.append(f"{pid}: no existing or pending tests, so tests.note must start with 'none yet'")
        g = r.get("releaseGate", {})
        for k in ["gate", "latest", "evidenceGate", "why"]:
            need(f"releaseGate.{k}", g.get(k))
        for k in ("gate", "latest", "evidenceGate"):
            if g.get(k) and not re.fullmatch(r"RG-\d{3}", g[k]):
                errs.append(f"{pid}: releaseGate.{k} is not a gate id")
        if g.get("evidenceGate") in GATE_ORDER and g.get("latest") in GATE_ORDER:
            if GATE_ORDER.index(g["evidenceGate"]) > GATE_ORDER.index(g["latest"]) and "risk acceptance" not in g.get("why", "").lower():
                errs.append(f"{pid}: the evidence closes at {g['evidenceGate']}, after the latest approval gate {g['latest']}, "
                            "but releaseGate.why does not mention the risk acceptance")
        cc = r.get("changeControl", {})
        need("changeControl.text", cc.get("text"))
        if not cc.get("classes") or any(c not in CHANGE_CLASSES for c in cc.get("classes", [])):
            errs.append(f"{pid}: changeControl.classes must be a non-empty subset of {CHANGE_CLASSES}")
        if "openPoints" not in r:
            errs.append(f"{pid}: openPoints is missing (an empty list is allowed)")
        if r.get("status") not in STATUSES:
            errs.append(f"{pid}: status must be one of {STATUSES}")
        for role in r.get("owner", []) + r.get("consulted", []):
            if role not in roles:
                errs.append(f"{pid}: role {role!r} is not in the role vocabulary")
        ap = r.get("approval", [])
        if len(ap) < 2:
            errs.append(f"{pid}: at least two required approvers")
        if not any(a.get("role") == CISO and a.get("veto") for a in ap):
            errs.append(f"{pid}: the {CISO} must be a required approver with a veto")
        for a in ap:
            if a.get("role") not in roles:
                errs.append(f"{pid}: approver role {a.get('role')!r} is not in the role vocabulary")
            if a.get("decision") not in DECISIONS:
                errs.append(f"{pid}: approval decision must be one of {DECISIONS}")
            for k in ("name", "date", "evidenceIds"):
                if k not in a:
                    errs.append(f"{pid}: approval slot of {a.get('role')} lacks {k}")
        for x in r.get("crossConstraints", []):
            if x not in cids:
                errs.append(f"{pid}: unknown constraint {x}")
            else:
                c = next(c for c in data["constraints"] if c["id"] == x)
                if pid not in c["records"]:
                    errs.append(f"{pid} lists constraint {x}, which does not list {pid}")
        for q in p.get("quantities", []):
            for k in ("symbol", "unit", "display"):
                if not nonempty(q.get(k)):
                    errs.append(f"{pid}: a quantity lacks {k}")
            if q.get("symbol") not in r.get("symbols", []):
                errs.append(f"{pid}: quantity symbol {q.get('symbol')} is not in symbols")
        pt = r.get("plannedTest", "")
        if pt:
            if not re.fullmatch(r"test_ConfigRange_[A-Z][A-Z0-9_]*", pt):
                errs.append(f"{pid}: plannedTest {pt!r} is not of the form test_ConfigRange_<NAME> with an upper-case name")
            if pt in alltests:
                errs.append(f"{pid}: plannedTest {pt} is also the planned test of {alltests[pt]} (one test per record)")
            alltests[pt] = pid
        for s in r.get("symbols", []):
            if not re.fullmatch(r"[A-Z][A-Z0-9_]*", s):
                errs.append(f"{pid}: symbol {s!r} is not an upper-case identifier (it is the name of a constant in the contracts)")
            if s in allsyms:
                errs.append(f"{pid}: symbol {s} is also a symbol of {allsyms[s]}")
            allsyms[s] = pid
        it = r.get("items")
        if it:
            if not nonempty(it.get("title")) or not nonempty(it.get("columns")) or not nonempty(it.get("rows")):
                errs.append(f"{pid}: items needs title, columns and rows")
            else:
                for row in it["rows"]:
                    if len(row) != len(it["columns"]) or any(not nonempty(c) for c in row):
                        errs.append(f"{pid}: an items row has an empty cell or the wrong width: {row[:1]}")
        for lvl in r.get("sourceChecks", []):
            if lvl.get("level") not in LEVELS:
                errs.append(f"{pid}: sourceChecks level {lvl.get('level')!r} is not one of {LEVELS}")
        for path, s in walk_strings(r):
            for name, why in RETIRED_NAMES.items():
                if name in s:
                    errs.append(f"{pid}: {path} mentions {name}, which does not exist ({why})")
        # no affirmative claim of approval, audit or test
        for path, s in walk_strings(r):
            for pat in BANNED:
                if re.search(pat, s, re.I):
                    errs.append(f"{pid}: {path} contains a claim of approval, audit or test ({pat})")
        # addresses must carry a valid EIP-55 checksum
        for path, s in walk_strings(r):
            for a in re.findall(r"0x[0-9a-fA-F]{40}\b", s):
                if a != a.lower() and a != "0x" + a[2:].upper() and not eip55_ok(a):
                    errs.append(f"{pid}: {path}: {a} is not a valid EIP-55 address")
        if pid == "PC-05":
            blob = json.dumps({k: v for k, v in r.items() if k not in ("approval",)})
            for m in re.finditer(r"(\d[\d,.]*)\s*(bps|basis points|%)", blob):
                errs.append(f"PC-05: a number appears in the record ({m.group(0)!r}); no value is proposed for the fee ceiling")
    return errs, warns


def eip55_ok(addr):
    a = addr[2:].lower()
    h = mod("eip712_vectors").keccak256(a.encode()).hex()
    want = "".join(c.upper() if int(h[i], 16) >= 8 else c for i, c in enumerate(a))
    return addr[2:] == want


def check_ranges(data):
    errs, warns = [], []
    env = production_env(data)
    for r in data["records"]:
        pid = r["id"]
        for q in r["proposal"]["quantities"]:
            sym, v, unit = q["symbol"], q.get("value"), q.get("unit")
            if unit not in UNITS:
                errs.append(f"{pid} {sym}: unit {unit!r} is not one of {UNITS}")
                continue
            if v is None:
                if not (pid == "PC-05" and r["proposal"]["status"] == "VALUE_PENDING"):
                    errs.append(f"{pid} {sym}: no numeric value")
                continue
            if not isinstance(v, int) or isinstance(v, bool):
                errs.append(f"{pid} {sym}: value must be an integer in the base unit")
                continue
            lo, hi = q.get("hardMin"), q.get("hardMax")
            if lo is None or hi is None:
                errs.append(f"{pid} {sym}: hardMin and hardMax are required for a numeric proposal")
                continue
            if not (lo <= v <= hi):
                errs.append(f"{pid} {sym}: proposal {v} is outside [{lo}, {hi}] {unit}")
            for key, expr_key in (("hardMin", "hardMinExpr"), ("hardMax", "hardMaxExpr")):
                if q.get(expr_key):
                    try:
                        got = eval_expr(q[expr_key], env)
                    except (KeyError, Pending, ValueError) as e:
                        errs.append(f"{pid} {sym}: {expr_key} cannot be evaluated ({e})")
                        continue
                    if got != q[key]:
                        errs.append(f"{pid} {sym}: {key} is {q[key]} but {expr_key} '{q[expr_key]}' gives {got}")
            for val, disp, label in ((v, q.get("display"), "value"), (lo, q.get("hardMinDisplay"), "hardMin"),
                                     (hi, q.get("hardMaxDisplay"), "hardMax")):
                if not nonempty(disp):
                    errs.append(f"{pid} {sym}: {label} has no display text")
                    continue
                dv = display_value(disp, unit)
                if dv is None:
                    errs.append(f"{pid} {sym}: cannot read the {label} display {disp!r} as {unit}")
                elif dv != val:
                    errs.append(f"{pid} {sym}: {label} display {disp!r} is {dv} but the number is {val}")
            t = q.get("testnet")
            if t:
                dv = display_value(t.get("display", ""), unit)
                if dv != t.get("value"):
                    errs.append(f"{pid} {sym}: testnet display {t.get('display')!r} does not equal {t.get('value')}")
    return errs, warns


def check_constraints(data):
    errs, warns = [], []
    env, tenv = production_env(data), testnet_env(data)
    present = {norm_expr(c["expr"]) for c in data["constraints"] if c.get("expr")}
    for e in REQUIRED_EXPRS:
        if e not in present:
            errs.append(f"required constraint is missing: {e}")
    for c in data["constraints"]:
        if not c.get("expr"):
            continue
        try:
            ok = eval_expr(c["expr"], env)
        except Pending as e:
            warns.append(f"{c['id']}: not evaluated, value of {e} pending")
            continue
        except (KeyError, ValueError, SyntaxError) as e:
            errs.append(f"{c['id']}: cannot evaluate '{c['expr']}' ({e})")
            continue
        if not ok:
            errs.append(f"{c['id']}: violated on the proposals: {c['expr']}")
        if c["scope"] == "both":
            try:
                if not eval_expr(c["expr"], tenv):
                    warns.append(f"{c['id']}: violated on the testnet values (16 §6): {c['expr']}")
            except Pending:
                pass
    return errs, warns


def check_approvals(data):
    errs, warns = [], []
    for r in data["records"]:
        pid = r["id"]
        signed = 0
        for a in r["approval"]:
            who = f"{pid} {a['role']}"
            if a["decision"] == "SIGNED":
                signed += 1
                if not nonempty(a.get("name")):
                    errs.append(f"{who}: SIGNED without a name")
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(a.get("date", ""))):
                    errs.append(f"{who}: SIGNED without a date (YYYY-MM-DD)")
                if not a.get("evidenceIds"):
                    errs.append(f"{who}: SIGNED without an evidence id")
                for e in a.get("evidenceIds", []):
                    if not re.fullmatch(r"EV-(?:P\d{2}|\d{3})", e):
                        errs.append(f"{who}: {e} is not an evidence id (EV-...)")
            else:
                if nonempty(a.get("name")) or nonempty(a.get("date")) or a.get("evidenceIds"):
                    errs.append(f"{who}: NOT SIGNED but name, date or evidence is filled in")
        if r["status"] == "APPROVED" and signed != len(r["approval"]):
            errs.append(f"{pid}: status APPROVED but only {signed} of {len(r['approval'])} slots are signed")
        if r["status"] == "APPROVED" and r["proposal"]["status"] == "VALUE_PENDING":
            errs.append(f"{pid}: APPROVED while the value is pending")
        if r["status"] == "PROPOSED" and signed == len(r["approval"]):
            warns.append(f"{pid}: every slot is signed but the status is still PROPOSED")
    return errs, warns


def referenced_ids(data):
    c = mod("check_all")
    refs, ranges = set(), set()
    for r in data["records"]:
        for path, s in walk_strings(r):
            if re.match(r"(symbols|proposedSymbols)\[", path):
                continue
            refs.update(c.ID.findall(s))
            for a, b, e in c.RANGE.findall(s):
                w = len(b)
                for n in range(int(b), int(e) + 1):
                    ranges.add(f"{a}{n:0{w}d}")
    for cons in data["constraints"]:
        for path, s in walk_strings(cons):
            refs.update(c.ID.findall(s))
    return refs | ranges


def expand_whitelist():
    out = set()
    for w in WHITELIST:
        m = re.fullmatch(r"(.+?-)(\d+)(?:…(\d+))?", w)
        a, b, e = m.group(1), m.group(2), m.group(3) or m.group(2)
        for n in range(int(b), int(e) + 1):
            out.add(f"{a}{n:0{len(b)}d}")
    return out


def defined_ids():
    """Identifiers defined in spec/*.md (table first cell, heading, or range) -- the generated document is excluded."""
    c = mod("check_all")
    defined = set()
    for f in sorted(SPEC.glob("*.md")):
        if f.name == DOC.name:
            continue
        text = read(f)
        for line in text.splitlines():
            if line.startswith("|"):
                cells = line.split("|")
                first = cells[1] if len(cells) > 2 else ""
                defined.update(c.ID.findall(first))
            h = re.match(r"^#{2,4}\s+(.*)", line)
            if h:
                defined.update(c.ID.findall(h.group(1)))
        for a, b, e in c.RANGE.findall(text):
            w = len(b)
            for n in range(int(b), int(e) + 1):
                defined.add(f"{a}{n:0{w}d}")
                defined.add(f"{a}{n}")
    return defined


def check_ids(data):
    errs, warns = [], []
    c = mod("check_all")
    refs = referenced_ids(data)
    defined = defined_ids() | expand_whitelist() | {r["id"] for r in data["records"]}
    for i in sorted(refs):
        if i not in defined and not c.IGNORE.match(i):
            errs.append(f"{i} is referenced but defined in no document")
    pend = sorted(i for i in refs if i in expand_whitelist() and i not in defined_ids())
    if pend:
        warns.append("referenced but not yet defined (whitelisted for revision 0.5): " + ", ".join(pend))
    return errs, warns


def check_doc(data):
    errs, warns = [], []
    try:
        want = render(data)
    except (ValueError, KeyError) as e:
        return [f"cannot render the document: {e!r}"], warns
    if not DOC.exists():
        errs.append(f"{DOC.name} does not exist: run --write")
    elif read(DOC) != want:
        errs.append(f"{DOC.name} is not up to date with {DATA.name}: run --write")
    for m in re.finditer(r"\]\(([^)#\s]+)(#[^)]*)?\)", want):
        tgt = m.group(1)
        if not tgt.startswith("http") and not (SPEC / tgt).exists():
            errs.append(f"the document links to a file that does not exist: {tgt}")
    return errs, warns


def norm_ws(s):
    s = re.sub(r"\s+", " ", s)
    return s.replace(", ", ",").replace("( ", "(").replace(" )", ")")


def check_pin_json(r):
    """The per-chain rows of PC-13 against the recorded Permit2 pin (evidence/permit2/pin.json): address, length, masked hash, offsets."""
    out = []
    path = SPEC / r["pinJson"]
    if not path.exists():
        return [f"{r['id']}: {r['pinJson']} does not exist: the Permit2 rows cannot be compared"]
    pin = json.loads(path.read_text(encoding="utf-8"))
    chains = {str(k): v for k, v in pin.get("chains", {}).items()}
    for row in r["items"]["rows"]:
        cid = row[1]
        if cid not in chains:
            out.append(f"{r['id']}: chain {cid} is not in {r['pinJson']}")
            continue
        if row[2].strip("`").lower() != pin.get("address", "").lower():
            out.append(f"{r['id']}: address of chain {cid} differs from {r['pinJson']}")
        if row[3].replace(",", "") != str(pin.get("runtimeCodeLength")):
            out.append(f"{r['id']}: code length of chain {cid} differs from {r['pinJson']} ({pin.get('runtimeCodeLength')})")
        if row[4].strip("`").lower().removeprefix("0x") != chains[cid].get("maskedCodeHash", "").lower():
            out.append(f"{r['id']}: masked code hash of chain {cid} differs from {r['pinJson']}")
        offs = pin.get("immutableOffsets", {})
        if str(offs.get("chainId")) not in row[5] or str(offs.get("domainSeparator")) not in row[5]:
            out.append(f"{r['id']}: immutable offsets of chain {cid} differ from {r['pinJson']} ({offs})")
    return out


def check_drift(data):
    """Warnings: the records against the documents, the vector tool and the Foundry file. A string that must equal the vector
    tool is an error if it does not (the tool is the reference)."""
    errs, warns = [], []
    texts = {}

    def doc(nn):
        if nn not in texts:
            f = sorted(SPEC.glob(f"{nn}-*.md"))
            texts[nn] = norm_ws(read(f[0])) if f else ""
        return texts[nn]
    allmd = "\n".join(read(f) for f in sorted(SPEC.glob("*.md")) if f.name != DOC.name)
    ev = mod("eip712_vectors")
    for r in data["records"]:
        for s in r["symbols"]:
            if s not in allmd and s not in r.get("proposedSymbols", []):
                warns.append(f"{r['id']}: symbol {s} appears in no document and is not listed as a proposed identifier")
        for sc in r.get("sourceChecks", []):
            if sc.get("tool"):
                want = getattr(ev, sc["tool"], None)
                if want is None or sc["text"] != want:
                    errs.append(f"{r['id']}: '{sc['label']}' differs from tools/eip712_vectors.py ({sc['tool']})")
            if sc["level"] in ("NOT_SPECIFIED", "DERIVED") or not sc["docs"]:
                continue
            needle = norm_ws(sc["text"])
            if not any(needle in doc(nn) for nn in sc["docs"]):
                kind = "expected text" if sc["level"] == "EXPECTED" else "quoted text"
                warns.append(f"{r['id']}: {kind} '{sc['label']}' is not in document(s) {', '.join(sc['docs'])}")
    for r in data["records"]:
        if r.get("pinJson"):
            warns.extend(check_pin_json(r))
    pairs = [("PIN_EOA", "0x" + ev.PIN_EOA.hex(), "17"), ("KECCAK_EMPTY", "0x" + ev.KECCAK_EMPTY.hex(), "17"),
             ("PriceQuote type hash", "0x" + ev.keccak256(ev.QUOTE_TYPE.encode()).hex(), "11")]
    for label, h, nn in pairs:
        if h not in doc(nn):
            warns.append(f"{label} {h} is not in document {nn} (vector block drift?)")
    if FOUNDRY_TEST.exists():
        src = FOUNDRY_TEST.read_text(encoding="utf-8")
        planned = {r["plannedTest"] for r in data["records"]}
        found = set(re.findall(r"function\s+(test_ConfigRange_[A-Za-z0-9_]+)\s*\(", src))
        for n in sorted(planned - found):
            warns.append(f"planned test {n} is not in {FOUNDRY_TEST.name}")
        for n in sorted(found - planned):
            warns.append(f"{FOUNDRY_TEST.name} has {n}, which no record plans")
    else:
        warns.append("spec/foundry/test/ConfigRecords.t.sol does not exist yet: the planned test names are unchecked")
    return errs, warns


def check_types(data):
    """PC-09 lists every EIP-712 string. Each one that eip712/types.json defines must be the same string: the file is the single source, and a record that
    quotes an older string (after the price pair left FiatTerms, ADR-020) would be a second, wrong source."""
    errs = []
    E = mod("eip712_types")
    reg = E.Registry(E.load())
    doc = reg.doc
    want = {s["symbol"]: reg.encode_type(s["name"]) for s in doc["structs"]}
    want["PAY_ONCE_WITNESS_TYPESTRING"] = reg.witness_type_string()
    want["PERMIT2_WITNESS_TRANSFER_FROM_TYPEHASH"] = doc["permit2Witness"]["stubSingle"] + reg.witness_type_string()
    want["PERMIT2_BATCH_WITNESS_TRANSFER_FROM_TYPEHASH"] = doc["permit2Witness"]["stubBatch"] + reg.witness_type_string()
    want.update(doc["tags"])
    for k, d in doc["domains"].items():
        want[k.upper() + "_DOMAIN_NAME"] = d["name"]
        want[k.upper() + "_DOMAIN_VERSION"] = d["version"]
    rec = next((r for r in data["records"] if r["id"] == "PC-09"), None)
    n = 0
    for row in (rec or {}).get("items", {}).get("rows", []):
        sym = row[1]
        if sym in want:
            n += 1
            if row[2].strip("`") != want[sym]:
                errs.append(f"PC-09 {sym}: the record says {row[2][:70]}... but eip712/types.json says {want[sym][:70]}...")
    if rec and n < 20:
        errs.append(f"PC-09: only {n} rows could be compared with eip712/types.json")
    return errs, []


CHECKS = [
    ("[1] 16 §7 rows have records, numbers agree", check_16),
    ("[2] required fields", check_fields),
    ("[3] proposals inside the safe range, units", check_ranges),
    ("[4] cross-constraints", check_constraints),
    ("[5] approvals", check_approvals),
    ("[6] referenced identifiers exist", check_ids),
    ("[7] generated document is up to date", check_doc),
    ("[8] drift against documents and tools (warnings)", check_drift),
    ("[9] PC-09 strings equal eip712/types.json", check_types),
]


def verify(strict=False):
    data = load_data()
    n_err = n_warn = 0
    for label, fn in CHECKS:
        errs, warns = fn(data)
        n_err += len(errs)
        n_warn += len(warns)
        state = "FAILED" if errs else ("ok" if not warns else "ok, with warnings")
        print(f"{label}: {state}")
        for e in errs:
            print("    ERROR", e)
        for w in warns:
            print("    WARN ", w)
    print(summary_line(data))
    print(f"warnings: {n_warn}")
    failed = n_err > 0 or (strict and n_warn > 0)
    print(f"RESULT: {'FAILED' if failed else 'ok'} ({n_err} errors, {n_warn} warnings{', strict' if strict else ''})")
    return 1 if failed else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--write", action="store_true", help="regenerate spec/18-configuration-records.md from the JSON")
    ap.add_argument("--verify", action="store_true", help="run all checks; exit 1 on any failure")
    ap.add_argument("--strict", action="store_true", help="with --verify: warnings are failures")
    ap.add_argument("--data", help="read another records file (for tests of the verifier); default spec/config/pc_records.json")
    args = ap.parse_args()
    if args.data:
        global DATA
        DATA = pathlib.Path(args.data).resolve()
    data = load_data()
    if args.write:
        text = render(data)
        DOC.write_bytes(text.encode("utf-8"))
        print(f"wrote {DOC.name} ({text.count(chr(10))} lines)")
        print(summary_line(data))
        return 0
    if args.verify:
        return verify(args.strict)
    print(summary_line(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
