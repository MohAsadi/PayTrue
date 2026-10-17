#!/usr/bin/env python3
"""Static loop audit of the Solidity sources: every loop is annotated with its bound, every bound is a named constant with a recorded
value, and no loop that is not bounded by such a constant is reachable from a state-changing entry point.

    python -I spec/tools/loop_audit.py            audit, write evidence/implementation/loop-audit.json, exit 1 on any violation
    python -I spec/tools/loop_audit.py --list     list every loop with its annotation (or the lack of one)

How it works
  * The sources of foundry/src (the reference model and the generated types library) are compiled to an AST with the pinned solc (0.8.24).
  * Every `for`, `while` and `do` loop must be preceded (within three lines) by a comment
        // loop-bound: <CLASS> | <expression> | <why the bound holds>
    CLASS is one of
        FIXED      a literal in the loop header (checked: the header contains `< <number>` with that number)
        TOKENS     at most MAX_TOKENS_PER_MANDATE (PC-11): terms are refused above it (TermsShape) and the arrays have that many slots
        EXPOSED    at most MAX_EXPOSED_TOKENS_PER_ROUTER (PC-18): the exposure list is capped by predicate X2
        BATCH      at most MAX_BATCH (PC-04): the entry point refuses more
        SIGNERS    at most MAX_SIGNERS_PER_SET (proposed PC-19): the entry point refuses more
        WITNESS_BATCH  at most MAX_WITNESS_BATCH (2: merchant and fee) transfers in the Permit2 batch witness
        ORACLE     iterates over history that grows without a bound (generations, routers ever proposed) and is therefore allowed only in
                   functions that no state-changing entry point can reach; the audit checks that by the call graph
        EXTERNAL   the same rule for a loop in a model of an external contract (Permit2's lockdown: the caller chooses the array)
  * The call graph is built from the AST (internal, library and typed external calls). A function that is part of a recursive cycle fails.
  * For every external or public function the audit computes an upper bound of loop iterations: bound(loop) * (1 + cost(body)), summed
    over the statements, with the cost of a callee added at the call site. The number is a bound of iterations, not of gas; the gas of
    the worst cases is measured by test/LoopBounds.t.sol.
Exit code 0 only when: every loop is annotated and consistent, every named bound equals the value in config/pc_records.json (or is
marked proposed there), no ORACLE loop is reachable from a state-changing function, and there is no recursion.
"""
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "foundry" / "src"
SOLC = ROOT / "toolchain" / "solc" / "solc-0.8.24.exe"
OUT = ROOT / "evidence" / "implementation" / "loop-audit.json"
PROFILES = {
    # the reference model of spec/foundry
    "model": dict(src=ROOT / "foundry" / "src", out=ROOT / "evidence" / "implementation" / "loop-audit.json",
                  where={"TOKENS": "ContainModel.sol", "EXPOSED": "MigrationModel.sol", "BATCH": "TimeModel.sol", "SIGNERS": "SignerSetModel.sol",
                         "WITNESS_BATCH": "FastPayTypes.sol"},
                  scope="foundry/src (the reference model and the generated types library); the production contracts carry the same annotations and pass the same audit (profile contracts)"),
    # the actual FastPay contracts: the shared bounds are generated from eip712/types.json into FastPayTypes.sol
    "contracts": dict(src=ROOT.parent / "contracts" / "src", out=ROOT / "evidence" / "implementation" / "loop-audit-contracts.json",
                      where={"TOKENS": "FastPayTypes.sol", "EXPOSED": "FastPayTypes.sol", "BATCH": "FastPayTypes.sol", "SIGNERS": "FastPayTypes.sol",
                             "WITNESS_BATCH": "FastPayTypes.sol"},
                      scope="contracts/src (the actual FastPay contracts and the generated types library)"),
}
PROFILE = "model"


def use_profile(name):
    """Point the audit at a source tree: the model (default) or the actual contracts."""
    global SRC, OUT, PROFILE
    PROFILE = name
    SRC = PROFILES[name]["src"]
    OUT = PROFILES[name]["out"]
    for cls, where in PROFILES[name]["where"].items():
        sym, _, rec = CLASSES[cls]
        CLASSES[cls] = (sym, where, rec)


ANNOT = re.compile(r"//\s*loop-bound:\s*([A-Z_]+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*$")

# class -> (constant symbol, where it is defined in the source, configuration record)
CLASSES = {
    "TOKENS": ("MAX_TOKENS_PER_MANDATE", "ContainModel.sol", "PC-11"),
    "EXPOSED": ("MAX_EXPOSED_TOKENS_PER_ROUTER", "MigrationModel.sol", "PC-18"),
    "BATCH": ("MAX_BATCH", "TimeModel.sol", "PC-04"),
    "SIGNERS": ("MAX_SIGNERS_PER_SET", "SignerSetModel.sol", "PC-19"),
    "WITNESS_BATCH": ("MAX_WITNESS_BATCH", "FastPayTypes.sol", "none: 10 section 8 question 2 (merchant and fee), generated from eip712/types.json"),
}
UNBOUNDED = ("ORACLE", "EXTERNAL")
MOCK_CONTRACTS = ("Permit2Mock",)  # models of external systems; their entry points are not FastPay entry points


def compile_ast():
    files = sorted(p for p in SRC.rglob("*.sol"))
    inp = {"language": "Solidity", "sources": {str(p.relative_to(SRC)).replace("\\", "/"): {"content": p.read_text(encoding="utf-8")} for p in files},
           "settings": {"outputSelection": {"*": {"": ["ast"]}}}}
    r = subprocess.run([str(SOLC), "--standard-json"], input=json.dumps(inp), capture_output=True, text=True, check=False)
    out = json.loads(r.stdout)
    errs = [e for e in out.get("errors", []) if e["severity"] == "error"]
    if errs:
        sys.exit("solc: " + errs[0]["formattedMessage"])
    return out, {k: v["content"] for k, v in inp["sources"].items()}


def constants(texts):
    """Numeric value of every `constant` of the sources: {symbol: value}."""
    vals = {}
    for path, t in texts.items():
        for m in re.finditer(r"\bconstant\s+([A-Z][A-Z0-9_]*)\s*=\s*([0-9_]+)\s*;", t):
            vals[(path, m.group(1))] = int(m.group(2).replace("_", ""))
    return vals


class Audit:
    def __init__(self):
        self.out, self.texts = compile_ast()
        self.funcs = {}      # id -> dict(name, contract, vis, mut, path, node)
        self.byid = {}
        self.loops = []      # dict(path, line, kind, header, annotation, function)
        self.fn_cost = {}
        self.calls = {}
        self.consts = constants(self.texts)
        self.override = {}   # constant symbol -> value (to evaluate the bounds at the ends of a safe range)
        self.paths = {v["id"]: k for k, v in self.out["sources"].items()}
        self._collect()

    # ------------------------------------------------------------------------------------------ AST helpers
    def _line(self, path, offset):
        return self.texts[path].count("\n", 0, offset) + 1

    def _collect(self):
        for path, su in self.out["sources"].items():
            for node in su["ast"]["nodes"]:
                if node["nodeType"] == "ContractDefinition":
                    for n in node["nodes"]:
                        if n["nodeType"] == "FunctionDefinition":
                            self.funcs[n["id"]] = dict(name=n["name"] or n["kind"], contract=node["name"], contractKind=node["contractKind"],
                                                       vis=n["visibility"], mut=n["stateMutability"], path=path, node=n, kind=n["kind"],
                                                       selector=n.get("functionSelector"))
        # a call through an interface runs the implementation: map the body-less function of an interface to the functions of the contracts
        # that have the same selector (the typed external calls of the contracts go through interfaces)
        self.impl = {}
        by_sel = {}
        for fid, f in self.funcs.items():
            if f["contractKind"] == "contract" and f["selector"] and f["node"].get("body"):
                by_sel.setdefault(f["selector"], []).append(fid)
        for fid, f in self.funcs.items():
            if f["contractKind"] == "interface" and f["selector"] in by_sel:
                self.impl[fid] = by_sel[f["selector"]]
        for fid, f in self.funcs.items():
            if f["node"].get("body"):
                self._scan(fid, f["node"]["body"], f["path"])

    def _scan(self, fid, node, path):
        """Collect the loops of function `fid` and the calls it makes (with the loops that enclose each call)."""
        f = self.funcs[fid]
        f.setdefault("loops", [])
        f.setdefault("calls", [])

        def walk(n, stack):
            if isinstance(n, dict):
                nt = n.get("nodeType")
                if nt in ("ForStatement", "WhileStatement", "DoWhileStatement"):
                    start = int(n["src"].split(":")[0])
                    line = self._line(path, start)
                    lines = self.texts[path].split("\n")
                    header = lines[line - 1].strip()
                    ann = None
                    for k in range(1, 4):
                        if line - 1 - k >= 0:
                            m = ANNOT.search(lines[line - 1 - k])
                            if m:
                                ann = (m.group(1), m.group(2), m.group(3))
                                break
                    loop = dict(path=path, line=line, kind=nt, header=header, annotation=ann, function=f"{f['contract']}.{f['name']}", fid=fid)
                    self.loops.append(loop)
                    f["loops"].append(loop)
                    for k, v in n.items():
                        walk(v, stack + [loop] if k in ("body", "condition", "loopExpression", "initializationExpression") else stack)
                    return
                if nt == "FunctionCall" and n.get("kind") == "functionCall":
                    ref = n["expression"].get("referencedDeclaration")
                    if ref is not None and ref in self.funcs:
                        for target in self.impl.get(ref, [ref]):
                            f["calls"].append((target, list(stack)))
                for v in n.values():
                    walk(v, stack)
            elif isinstance(n, list):
                for v in n:
                    walk(v, stack)
        walk(node, [])

    # ------------------------------------------------------------------------------------------ bounds
    def bound_of(self, loop):
        ann = loop["annotation"]
        if ann is None:
            return None, "no annotation"
        cls, expr, why = ann
        if cls == "FIXED":
            m = re.search(r"(?:<|<=)\s*([0-9]+)", loop["header"])
            if not m:
                return None, "FIXED loop without a numeric literal in its header"
            n = int(m.group(1)) + (1 if "<=" in loop["header"] else 0)
            if str(int(m.group(1))) not in expr.replace(" ", "") and expr.strip() != m.group(1):
                return None, f"FIXED annotation '{expr}' does not mention the literal {m.group(1)}"
            return n, None
        if cls in UNBOUNDED:
            return None, None
        if cls in CLASSES:
            sym, where, _ = CLASSES[cls]
            hit = [v for (p, s), v in self.consts.items() if s == sym and p.endswith(where)]
            if not hit:
                return None, f"constant {sym} not found in {where}"
            return self.override.get(sym, hit[0]), None
        return None, f"unknown class {cls}"

    def cost(self, fid, visiting=()):
        """Upper bound of loop iterations executed by one call of function `fid`; None if it contains an ORACLE loop or recursion."""
        if fid in self.fn_cost:
            return self.fn_cost[fid]
        if fid in visiting:
            raise RecursionError(self.funcs[fid]["contract"] + "." + self.funcs[fid]["name"])
        f = self.funcs[fid]
        total = 0
        # loops of this function that are not nested in another loop of the same function carry the cost of their bodies via `calls`
        nested = {}
        for loop in f.get("loops", []):
            b, err = self.bound_of(loop)
            loop["bound"] = b
            loop["error"] = err
        # iterations of the function's own loops: product of the nesting bounds, computed from source order and brace nesting
        total += self._own_iterations(f)
        for ref, stack in f.get("calls", []):
            callee = self.cost(ref, visiting + (fid,))
            if callee is None:
                self.fn_cost[fid] = None
                return None
            mult = 1
            for lp in stack:
                if lp["bound"] is None:
                    self.fn_cost[fid] = None
                    return None
                mult *= lp["bound"]
            total += mult * callee
        if any(lp["annotation"] and lp["annotation"][0] in UNBOUNDED for lp in f.get("loops", [])):
            self.fn_cost[fid] = None
            return None
        self.fn_cost[fid] = total
        return total

    def _own_iterations(self, f):
        """Sum over the loops of the function of the product of the bounds of the loops that enclose it (inner loops multiply)."""
        loops = f.get("loops", [])
        total = 0
        for lp in loops:
            if lp["bound"] is None:
                continue
            mult = lp["bound"]
            # enclosing loops: those of the same function whose source range contains this one
            for other in loops:
                if other is lp or other["bound"] is None:
                    continue
                if other["line"] < lp["line"] and self._contains(f, other, lp):
                    mult *= other["bound"]
            total += mult
        return total

    def _contains(self, f, outer, inner):
        # find the AST node of `outer` and test whether `inner`'s start offset lies in its range
        key = (outer["path"], outer["line"], outer["kind"])
        rng = self._ranges.get(key)
        if rng is None:
            return False
        return rng[0] <= self._offset(inner) < rng[1]

    def _offset(self, loop):
        lines = self.texts[loop["path"]].split("\n")
        return sum(len(x) + 1 for x in lines[:loop["line"] - 1]) + (len(lines[loop["line"] - 1]) - len(lines[loop["line"] - 1].lstrip()))

    def build_ranges(self):
        self._ranges = {}

        def walk(n, path):
            if isinstance(n, dict):
                if n.get("nodeType") in ("ForStatement", "WhileStatement", "DoWhileStatement"):
                    s, l, _ = (int(x) for x in n["src"].split(":"))
                    self._ranges[(path, self._line(path, s), n["nodeType"])] = (s, s + l)
                for v in n.values():
                    walk(v, path)
            elif isinstance(n, list):
                for v in n:
                    walk(v, path)
        for path, su in self.out["sources"].items():
            walk(su["ast"], path)

    # ------------------------------------------------------------------------------------------ reachability
    def reachable(self, fid):
        seen, stack = set(), [fid]
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            for ref, _ in self.funcs[x].get("calls", []):
                stack.append(ref)
        return seen

    def run(self):
        self.build_ranges()
        problems = []
        for lp in self.loops:
            if lp["annotation"] is None:
                problems.append(f"{lp['path']}:{lp['line']}: loop without a `// loop-bound:` annotation: {lp['header']}")
        loops_report = []
        for fid, f in self.funcs.items():
            for lp in f.get("loops", []):
                b, err = self.bound_of(lp)
                lp["bound"] = b
                if err and lp["annotation"] is not None:
                    problems.append(f"{lp['path']}:{lp['line']}: {err}")
        entries = []
        for fid, f in self.funcs.items():
            if f["contractKind"] != "contract" or f["kind"] not in ("function",) or f["vis"] not in ("external", "public"):
                continue
            if f["contract"] in MOCK_CONTRACTS:
                continue
            changing = f["mut"] in ("nonpayable", "payable")
            reach = self.reachable(fid)
            oracle = [lp for r in reach for lp in self.funcs[r].get("loops", []) if lp["annotation"] and lp["annotation"][0] in UNBOUNDED]
            unannotated = [lp for r in reach for lp in self.funcs[r].get("loops", []) if lp["annotation"] is None]
            try:
                c = self.cost(fid)
            except RecursionError as e:
                problems.append(f"recursion through {e}")
                c = None
            entry = dict(contract=f["contract"], function=f["name"], stateChanging=changing, path=f["path"],
                         loopsReachable=sum(len(self.funcs[r].get("loops", [])) for r in reach), iterationBound=c,
                         oracleLoopsReachable=[f"{o['path']}:{o['line']}" for o in oracle])
            if changing and (oracle or unannotated):
                problems.append(f"{f['contract']}.{f['name']} is state-changing and reaches an unbounded or unannotated loop: " +
                                ", ".join(f"{o['path']}:{o['line']}" for o in oracle + unannotated))
            if changing and c is None and not oracle and not unannotated:
                problems.append(f"{f['contract']}.{f['name']}: no iteration bound could be computed")
            entries.append(entry)
        for lp in self.loops:
            loops_report.append(dict(file=lp["path"], line=lp["line"], function=lp["function"], statement=lp["kind"], header=lp["header"],
                                     boundClass=lp["annotation"][0] if lp["annotation"] else None,
                                     boundExpression=lp["annotation"][1] if lp["annotation"] else None,
                                     why=lp["annotation"][2] if lp["annotation"] else None,
                                     boundValue=lp.get("bound")))
        return problems, loops_report, entries


def record_values():
    """{symbol: (proposed value, hard minimum, hard maximum, record id)} from config/pc_records.json."""
    d = json.loads((ROOT / "config" / "pc_records.json").read_text(encoding="utf-8"))
    out = {}
    for r in d["records"]:
        for q in r["proposal"].get("quantities", []):
            out[q["symbol"]] = (q["value"], q.get("hardMin"), q.get("hardMax"), r["id"])
    return out


def entries_at(a, override):
    """Iteration bounds of the state-changing entry points with the named constants replaced by `override`."""
    a.override = override
    a.fn_cost = {}
    for lp in a.loops:
        lp.pop("bound", None)
    _, _, entries = a.run()
    a.override = {}
    a.fn_cost = {}
    return {(e["contract"], e["function"]): e["iterationBound"] for e in entries}


def main(argv):
    if "--project" in argv:
        use_profile(argv[argv.index("--project") + 1])
    a = Audit()
    problems, loops, entries = a.run()
    recs = record_values()
    at_max = {}
    defs = {}
    for (p, sy), v in a.consts.items():
        defs.setdefault(sy, set()).add(v)
    for sy, vals in defs.items():
        if sy in {c[0] for c in CLASSES.values()} and len(vals) > 1:
            problems.append(f"{sy} is defined with different values in different files: {sorted(vals)}")
    for cls, (sym, where, rec) in CLASSES.items():
        src = next((v for (p, s), v in a.consts.items() if s == sym and p.endswith(where)), None)
        if sym in recs:
            if recs[sym][0] != src:
                problems.append(f"{sym}: the source says {src}, the proposal of {recs[sym][3]} says {recs[sym][0]}")
            at_max[sym] = recs[sym][2]
    hard = entries_at(a, {k: v for k, v in at_max.items() if v is not None})
    problems2, _, _ = a.run()
    for e in entries:
        e["iterationBoundAtHardMaxOfTheSafeRange"] = hard.get((e["contract"], e["function"]))
    if "--list" in argv:
        for lp in loops:
            print(f"{lp['file']}:{lp['line']:>4}  {lp['function']:<46} {str(lp['boundClass']):<8} {str(lp['boundValue']):<5} {lp['header'][:70]}")
        print(f"{len(loops)} loops; {len(problems)} problems")
        for p in problems:
            print("  PROBLEM", p)
        return 1 if problems else 0
    consts = {CLASSES[c][0]: next((v for (p, s), v in a.consts.items() if s == CLASSES[c][0]), None) for c in CLASSES}
    consts_hard = {s: recs[s][2] for s in at_max if recs[s][2] is not None}
    report = dict(schema=1, tool="tools/loop_audit.py", solc="0.8.24", profile=PROFILE, scope=PROFILES[PROFILE]["scope"], constants=consts,
                  recordedBounds={c: CLASSES[c][2] for c in CLASSES}, safeRangeHardMax=consts_hard, loops=loops, entryPoints=sorted(entries, key=lambda e: (e["contract"], e["function"])),
                  problems=problems, verdict="PASS" if not problems else "FAIL")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8", newline="\n")
    for e in report["entryPoints"]:
        if e["stateChanging"]:
            print(f"  {e['contract']}.{e['function']:<28} loops reachable {e['loopsReachable']:>3}  iteration bound {e['iterationBound']:>5}   at the hard maximum of the safe range {e['iterationBoundAtHardMaxOfTheSafeRange']}")
    print(f"{len(loops)} loops, {len(problems)} problems -> {report['verdict']} ({OUT.relative_to(ROOT)})")
    for p in problems:
        print("  PROBLEM", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
