"""Dependency-free CLI. Everything runs locally, reads local files and writes only to stdout."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from .core import MAX_CASE_BYTES, evaluate

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = {"case": "case.schema.json", "corpus": "handoff-corpus.schema.json", "report": "evidence-report.schema.json"}


def _unique_keys(pairs):
    """Reject JSON with duplicate keys rather than silently accepting a rewrite."""
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _reject_constant(value):
    raise ValueError(f"invalid JSON number: {value}")


def read_case_file(path: Path):
    """Read only a bounded file, refusing ambiguous JSON key overwrites."""
    with path.open('rb') as stream:
        raw = stream.read(MAX_CASE_BYTES + 1)
    if len(raw) > MAX_CASE_BYTES:
        raise ValueError("case exceeds input file size limit")
    return json.loads(raw.decode('utf-8'), object_pairs_hook=_unique_keys,
                      parse_constant=_reject_constant)


def _read_bounded(path: Path) -> bytes:
    with path.open('rb') as stream:
        raw = stream.read(MAX_CASE_BYTES + 1)
    if len(raw) > MAX_CASE_BYTES:
        raise ValueError("input exceeds file size limit")
    return raw


def _schema_errors(value, name: str) -> list[dict[str, str]]:
    from .schema import validate
    schema = json.loads((ROOT / "contracts" / SCHEMAS[name]).read_text(encoding="utf-8"))
    return validate(value, schema)


def _emit(value) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _load_corpus_case(case_id: str, file: Path | None):
    """Return (split, case) from the packaged corpus or from a corpus-format file."""
    from .corpus import CorpusError, find_case, load_bytes
    if file is None:
        return find_case(case_id)
    doc = load_bytes(_read_bounded(file))
    for case in doc["cases"]:
        if case["case_id"] == case_id:
            return doc["split"], case
    raise CorpusError(f"case not found in {file.name}: {case_id}")


def _corpus_command(args) -> int:
    from . import baselines, corpus
    if args.corpus_command == "validate":
        out = {}
        for split, name in corpus.SPLITS.items():
            doc = corpus.load_split(split)
            if doc is None:
                out[split] = {"status": "NOT_PROVIDED"}
                continue
            raw = (corpus.CORPUS_DIR / name).read_bytes()
            out[split] = {"status": "VALID", "cases": len(doc["cases"]), "sha256": hashlib.sha256(raw).hexdigest(),
                          "human_reviewed": sum(corpus.is_human_reviewed(c) for c in doc["cases"])}
        _emit(out)
        return 0
    if args.corpus_command == "tune":
        _emit(baselines.tune_rule_based(corpus.load_split("dev")))
        return 0
    if args.corpus_command == "snapshot":
        from .benchmark import snapshot
        _emit(snapshot())
        return 0
    if args.corpus_command in ("kit", "template", "compile", "agreement"):
        from . import labeling
        from .intake import parse_json_strict
        if args.corpus_command == "kit":
            _emit(labeling.blind_form(corpus.load_split(args.split)))
        elif args.corpus_command == "template":
            _emit(labeling.independent_template())
        elif args.corpus_command == "compile":
            _emit(labeling.compile_form(parse_json_strict(_read_bounded(args.form))))
        else:
            human = corpus.load_bytes(_read_bounded(args.human))
            _emit(labeling.agreement(corpus.load_split(args.candidate), human))
        return 0
    doc = corpus.load_split(args.split)
    if doc is None:
        _emit({"split": args.split, "status": "NOT_PROVIDED",
               "note": "No file for this split. Human labels and independent cases must come from a person who has "
                       "not seen the baselines or the candidates; see research/HUMAN_LABELING_PROCEDURE_V1_4.md."})
        return 3
    if args.corpus_command == "sheet":
        sys.stdout.write(corpus.review_sheet(doc, blind=args.blind))
        return 0
    result = baselines.run_baselines(doc)
    if args.summary_only:
        result = {k: v for k, v in result.items() if k != "rows"}
    _emit(result)
    return 0


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(prog="python -m ddlab", description="Structured decision drift testbed (synthetic)")
    cmd = parser.add_subparsers(dest="command", required=True)
    ev = cmd.add_parser("evaluate", help="Evaluate a local structured JSON case")
    ev.add_argument("file", type=Path)
    ev.add_argument("--strict-schema", action="store_true",
                    help="V1.4: strict intake and contracts/case.schema.json before evaluating")
    ev.add_argument("--policy", type=Path,
                    help="V1.4.1: operator-supplied authorization policy file (default: contracts/authorization-policy.json)")
    cmd.add_parser("policy", help="V1.4.1: print the packaged authorization policy and its digest")
    pack = cmd.add_parser("proofpack", help="V1.4.1: per-result evidence pack (source, passage, decision, change, rule, result, uncertainty, validation)")
    pack.add_argument("--format", choices=["json", "md"], default="json")
    bench = cmd.add_parser("benchmark", help="Run packaged synthetic scenarios")
    bench.add_argument("--suite", choices=["quickstart"], default="quickstart")
    cmd.add_parser("radar", help="Display curated technology decision radar")
    challenge = cmd.add_parser("challenge", help="Run 100 generated synthetic controls (10 archetypes x 10 contexts)")
    challenge.add_argument("--summary-only", action="store_true", help="Hide per-case results")
    val = cmd.add_parser("validate", help="V1.4: strict intake plus JSON schema check of a local file")
    val.add_argument("file", type=Path)
    val.add_argument("--schema", choices=sorted(SCHEMAS), default="case")
    corp = cmd.add_parser("corpus", help="V1.4: synthetic unstructured-handoff corpus and trivial baselines")
    corp_cmd = corp.add_subparsers(dest="corpus_command", required=True)
    corp_cmd.add_parser("validate", help="Validate every packaged split and print file digests")
    corp_cmd.add_parser("tune", help="Reproduce the dev-only threshold search of the rule-based baseline")
    corp_cmd.add_parser("snapshot", help="Print the deterministic results snapshot for all splits")
    kit = corp_cmd.add_parser("kit", help="V1.4.1: print a blind label form (no titles, no candidate labels)")
    kit.add_argument("--split", choices=["dev", "heldout"], default="heldout")
    corp_cmd.add_parser("template", help="V1.4.1: print an empty form for new, independent cases")
    comp = corp_cmd.add_parser("compile", help="V1.4.1: turn a completed label form into a corpus file (stdout)")
    comp.add_argument("form", type=Path)
    agree = corp_cmd.add_parser("agreement", help="V1.4.1: compare human labels with the candidate labels")
    agree.add_argument("--human", type=Path, required=True, help="Corpus file produced by 'corpus compile'")
    agree.add_argument("--candidate", choices=["dev", "heldout"], default="heldout")
    sheet = corp_cmd.add_parser("sheet", help="Print a Markdown review sheet for a human labeller")
    sheet.add_argument("--split", choices=["dev", "heldout", "heldout-human", "independent-heldout"], default="dev")
    sheet.add_argument("--blind", action="store_true", help="Hide candidate labels for independent labelling")
    base = corp_cmd.add_parser("baselines", help="Run the three baselines on one split")
    base.add_argument("--split", choices=["dev", "heldout", "heldout-human", "independent-heldout"], default="dev")
    base.add_argument("--summary-only", action="store_true", help="Hide per-case rows")
    for name, text in (("recover", "V1.4: reconfirmation checklist for one corpus case"),
                       ("report", "V1.4: unsigned synthetic evidence report for one corpus case")):
        sub = cmd.add_parser(name, help=text)
        sub.add_argument("case_id")
        sub.add_argument("--file", type=Path, help="Corpus-format JSON file instead of the packaged corpus")
        if name == "report":
            sub.add_argument("--format", choices=["json", "md"], default="json")
            sub.add_argument("--include-text", action="store_true",
                             help="Also include the redacted, clipped conversation text (off by default)")
    args = parser.parse_args()
    if args.command == "evaluate":
        try:
            if args.strict_schema:
                from .intake import parse_json_strict
                case = parse_json_strict(_read_bounded(args.file))
                errors = _schema_errors(case, "case")
                if errors:
                    shown = "; ".join(f"{e['path']} [{e['keyword']}]" for e in errors[:5])
                    raise ValueError(f"SCHEMA_VIOLATION ({len(errors)}): {shown}")
            else:
                case = read_case_file(args.file)
            policy = None
            if args.policy is not None:
                from .policy import load_policy
                policy = load_policy(args.policy)
            report = evaluate(case, policy)
        except (ValueError, OSError, UnicodeDecodeError, RecursionError, OverflowError) as exc:
            print(f"INPUT_ERROR: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["verdict"] == "PASS" else 1
    if args.command == "radar":
        print((ROOT / "docs" / "technology-radar.json").read_text(encoding="utf-8"))
        return 0
    if args.command == "challenge":
        from .challenge import run_challenge
        report = run_challenge()
        if args.summary_only:
            report = {k: v for k, v in report.items() if k != 'cases'}
        print(json.dumps(report, indent=2))
        return 0 if report["matched"] == report["total"] else 1
    if args.command == "benchmark":
        results = []
        for path in sorted((ROOT / "examples").glob("*.json")):
            case = json.loads(path.read_text(encoding="utf-8"))
            report = evaluate(case)
            results.append({"case": case["case_id"], "expected": case.get("expected_verdict"),
                            "actual": report["verdict"], "correct": report["verdict"] == case.get("expected_verdict")})
        report = {"suite": args.suite, "type": "synthetic fixtures only",
                  "total": len(results), "passed": sum(row["correct"] for row in results), "cases": results}
        print(json.dumps(report, indent=2))
        return 0 if results and all(row["correct"] for row in results) else 1
    try:
        if args.command == "policy":
            from .policy import load_policy, policy_digest
            policy = load_policy()
            _emit({"policy": policy, "sha256": policy_digest(policy), "source": "contracts/authorization-policy.json",
                   "note": "Operator-side simulation policy. Never read from an analysed case. Authenticates nobody."})
            return 0
        if args.command == "proofpack":
            from .proofpack import build, render_markdown as render_pack
            pack = build()
            if args.format == "md":
                sys.stdout.write(render_pack(pack))
            else:
                _emit(pack)
            return 0
        if args.command == "validate":
            from .intake import parse_json_strict
            errors = _schema_errors(parse_json_strict(_read_bounded(args.file)), args.schema)
            _emit({"schema": SCHEMAS[args.schema], "valid": not errors, "violations": errors})
            return 0 if not errors else 1
        if args.command == "corpus":
            return _corpus_command(args)
        if args.command in ("recover", "report"):
            from .evidence import build_report, render_checklist, render_markdown
            split, case = _load_corpus_case(args.case_id, args.file)
            report = build_report(case, split, include_text=getattr(args, "include_text", False))
            if args.command == "recover":
                sys.stdout.write(render_checklist(report))
            elif args.format == "md":
                sys.stdout.write(render_markdown(report))
            else:
                _emit(report)
            return 0
    except (ValueError, OSError, RecursionError, OverflowError) as exc:
        print(f"INPUT_ERROR: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
