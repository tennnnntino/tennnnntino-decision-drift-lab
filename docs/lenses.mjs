/* STATIC SELF-REVIEW — NOT VOTES BY REAL EXPERTS */
export const REVIEW = {
  "as_of": "2026-11-11",
  "review_type": "internal evidence-mapped checklist, not human expert consultation",
  "limitations": "Statuses refer to narrow repository artifacts; PASS does not mean production readiness.",
  "items": [
    {
      "id": "E01",
      "discipline": "Evolvable architecture",
      "status": "NOT_TESTED",
      "justification": "Modular boundaries exist; maintainability under change has not been measured.",
      "evidence": "ddlab/core.py"
    },
    {
      "id": "E02",
      "discipline": "Test-first engineering",
      "status": "PASS",
      "justification": "Regression tests include 10 hand-authored positive/negative fixtures.",
      "evidence": "tests/test_core.py"
    },
    {
      "id": "E03",
      "discipline": "Data reliability",
      "status": "FAIL",
      "justification": "JSON Schema is documented but not fully enforced by the Python evaluator.",
      "evidence": "contracts/case.schema.json"
    },
    {
      "id": "E04",
      "discipline": "Domain boundaries",
      "status": "PASS",
      "justification": "Commercial, support and release examples are kept separate from evaluator.",
      "evidence": "examples/"
    },
    {
      "id": "E05",
      "discipline": "Runtime simplicity",
      "status": "PASS",
      "justification": "Works with Python standard library, no model keys or database.",
      "evidence": "python -m ddlab benchmark"
    },
    {
      "id": "E06",
      "discipline": "Reliability engineering",
      "status": "PASS",
      "justification": "Negative paths for invalid input, duplicates and limits are tested.",
      "evidence": "tests/test_core.py"
    },
    {
      "id": "E07",
      "discipline": "Observability",
      "status": "PASS",
      "justification": "Reports separate findings, status and item IDs.",
      "evidence": "ddlab/core.py"
    },
    {
      "id": "E08",
      "discipline": "Agent threat modelling",
      "status": "NOT_TESTED",
      "justification": "Untrusted-text ingestion does not exist; an adversarial prompt corpus does not exist.",
      "evidence": "SECURITY.md"
    },
    {
      "id": "E09",
      "discipline": "Security architecture",
      "status": "FAIL",
      "justification": "Simulated approval is not identity authentication or access enforcement.",
      "evidence": "ddlab/core.py"
    },
    {
      "id": "E10",
      "discipline": "AI systems engineering",
      "status": "PASS",
      "justification": "Deterministic baseline clearly separates planned AI integration from implemented functionality.",
      "evidence": "docs/METHODOLOGY.md"
    },
    {
      "id": "E11",
      "discipline": "Evaluation science",
      "status": "PASS",
      "justification": "Exact formulas and null denominators are documented and tested.",
      "evidence": "tests/test_core.py"
    },
    {
      "id": "E12",
      "discipline": "Agent orchestration",
      "status": "NOT_TESTED",
      "justification": "No live LLM or provider adapter is implemented.",
      "evidence": "docs/technology-radar.json"
    },
    {
      "id": "E13",
      "discipline": "Evidence grounding",
      "status": "FAIL",
      "justification": "Source references are compared as strings; no provenance verifier is implemented.",
      "evidence": "ddlab/core.py"
    },
    {
      "id": "E14",
      "discipline": "Memory & handoff",
      "status": "PASS",
      "justification": "Revoked decisions and fact promotions are visible as negative cases.",
      "evidence": "examples/revoked_decision.json"
    },
    {
      "id": "E15",
      "discipline": "Model complexity",
      "status": "PASS",
      "justification": "No LLM required for baseline, reducing cost and unsupported claims.",
      "evidence": "ddlab/core.py"
    },
    {
      "id": "E16",
      "discipline": "Web performance",
      "status": "NOT_TESTED",
      "justification": "Web performance budgets and device-lab measurements are not established.",
      "evidence": "docs/style.css"
    },
    {
      "id": "E17",
      "discipline": "Human-centered UX",
      "status": "NOT_TESTED",
      "justification": "Manual visual desktop/mobile checks exist, but accessibility audit is not complete.",
      "evidence": "docs/index.html"
    },
    {
      "id": "E18",
      "discipline": "Developer experience",
      "status": "PASS",
      "justification": "CLI, quickstart and test commands use no extra runtime package.",
      "evidence": "README.md"
    },
    {
      "id": "E19",
      "discipline": "User-value discovery",
      "status": "NOT_TESTED",
      "justification": "Three operational scenarios are available, but no external user study proves value yet.",
      "evidence": "docs/index.html"
    },
    {
      "id": "E20",
      "discipline": "Product scalability",
      "status": "NOT_TESTED",
      "justification": "Runtime scales within fixture bounds; production scalability is not tested.",
      "evidence": "ddlab/core.py"
    }
  ]
};
