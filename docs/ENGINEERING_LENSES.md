# 20 engineering review lenses — public checklist

This is one **synthetic, cross-disciplinary design-review rubric**, not 20 live agents or copies of real people. Each lens asks one falsifiable question and requires a deliverable. No lens can approve a production release on behalf of a person.

| ID | Perspective | Review question | Required evidence |
|---|---|---|---|
| E01 | Evolvable architecture | Can a new capability be added without rewriting the core? | Stable module boundary + change test |
| E02 | Test-first engineering | Does each defect become a reproducible regression? | Failing-then-passing test |
| E03 | Data reliability | Is the canonical object schema stable and explicit? | Versioned schema + invalid-input tests |
| E04 | Domain boundaries | Are operational use cases separated from mechanisms? | Domain-to-code map |
| E05 | Runtime simplicity | Is the minimum deployable system understandable? | One-command local run |
| E06 | Reliability engineering | What happens when input or services fail? | Negative-path tests |
| E07 | Observability | Are failures explainable and measurable? | Structured findings and trace IDs |
| E08 | Agent threat modelling | Can untrusted text become instruction? | Defensive tests + clear trust boundary |
| E09 | Security architecture | Are identities, privileges and secrets actually protected? | Auth boundary review; absent = BLOCKED |
| E10 | AI systems engineering | Is the test meaningful without model theatrics? | Baseline plus limitations |
| E11 | Evaluation science | Is the metric reproducible and clearly defined? | Formula, denominators, labels, samples |
| E12 | Agent orchestration | Can external model providers be swapped safely? | Planned adapter contract; no false implementation claim |
| E13 | Evidence & retrieval | Can every important claim point to a source? | Evidence reference per record |
| E14 | Memory & handoff | Do corrections and revoked decisions survive transfers? | Targeted fixtures |
| E15 | Model complexity | Is AI used only when it adds measurable value? | Deterministic baseline first |
| E16 | Web performance | Is the interactive workbench usable on low-end devices? | Browser performance budget |
| E17 | Human-centered UX | Can users see a failure and its precise cause? | Readable mobile/keyboard workflow |
| E18 | Developer experience | Can external developers reproduce a run quickly? | Zero-secret setup and CLI docs |
| E19 | User value discovery | Which real task does this test help, now? | Three concrete operational cases |
| E20 | Product scalability | Can the demo evolve without coupling to private systems? | Ports/adapters roadmap and release boundaries |

Use an evidence-backed review status for each lens: `PASS / FAIL / NOT_TESTED / NOT_APPLICABLE`. No blanket 20/20 score. Approval is a human decision, not an average.
