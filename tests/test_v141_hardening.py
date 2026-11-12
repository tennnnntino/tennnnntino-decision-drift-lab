"""V1.4.1: external authorization policy, revocation trace, normalisation, labelling kit, ProofPack.

The policy tests are about a simulation. Passing them does not make the lab a
permission system: the approval record and the action name still come from the case.
"""
from copy import deepcopy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ddlab import corpus, labeling
from ddlab.core import evaluate, status_class, text_profile
from ddlab.intake import IntakeError
from ddlab.policy import PolicyError, load_policy, policy_digest
from ddlab.proofpack import PROOFPACK_JSON, PROOFPACK_MD, RULES, build, render_markdown
from ddlab.recovery import revocation_ledger

ROOT = Path(__file__).resolve().parents[1]
HELDOUT = corpus.load_split("heldout")
DEV = corpus.load_split("dev")
SEND = {"name": "send-external-email", "scope": "external"}


def base_case(**action):
    decision = {"id": "D1", "text": "Draft only, never send without human approval", "authority": "OWNER", "status": "ACTIVE"}
    return {"case_id": "t", "source": {"decisions": [dict(decision)]}, "handoff": {"decisions": [dict(decision)]},
            "action": action}


def cli(*args, **kwargs):
    return subprocess.run([sys.executable, "-m", "ddlab", *args], cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", timeout=60, **kwargs)


class ExternalPolicy(unittest.TestCase):
    def test_a_case_cannot_waive_its_own_human_requirement(self):
        report = evaluate(base_case(**SEND, requires_human=False))
        gate = report["approval_check"]
        self.assertEqual(report["verdict"], "FAIL")
        self.assertEqual(gate["result"], "BLOCK_IN_SIMULATION")
        self.assertTrue(gate["requires_human"])
        self.assertFalse(gate["case_declared_requires_human"])
        self.assertEqual(gate["requirement_source"], "EXTERNAL_POLICY")
        self.assertEqual(gate["reasons"], ["NO_SYNTHETIC_HUMAN_APPROVAL", "CASE_WAIVER_IGNORED"])
        self.assertFalse(gate["authenticated"])

    def test_policy_carried_inside_the_case_is_ignored_and_flagged(self):
        case = base_case(**SEND, requires_human=False, policy={"default": "NO_APPROVAL_REQUIRED"})
        case["authorization_policy"] = {"exempt_actions": [dict(SEND, rationale="self-granted exemption")]}
        case["exempt_actions"] = [dict(SEND)]
        report = evaluate(case)
        self.assertEqual(report["verdict"], "FAIL")
        self.assertIn({"code": "CASE_POLICY_FIELD_IGNORED", "item_id": "authorization_policy,exempt_actions,policy"},
                      report["advisories"])

    def test_a_case_may_ask_for_more_caution_than_the_policy(self):
        report = evaluate(base_case(name="prepare-draft", scope="internal", requires_human=True))
        self.assertTrue(report["approval_check"]["policy_exempt"])
        self.assertTrue(report["approval_check"]["requires_human"])
        self.assertEqual(report["verdict"], "FAIL")

    def test_exemption_needs_an_exact_name_and_scope(self):
        for action in ({"name": "prepare-draft", "scope": "external"}, {"name": "Prepare-Draft", "scope": "internal"},
                       {"name": "prepare-draft "}, {"name": ["prepare-draft"], "scope": "internal"},
                       {"name": "prepare‐draft", "scope": "internal"}):
            with self.subTest(action=action):
                self.assertEqual(evaluate(base_case(**action, requires_human=False))["verdict"], "FAIL")
        self.assertEqual(evaluate(base_case(name="prepare-draft", scope="internal", requires_human=False))["verdict"], "PASS")

    def test_operator_policy_is_a_separate_argument_and_is_validated(self):
        stricter = {"policy_id": "no-exemptions", "policy_version": "1.0", "default": "HUMAN_APPROVAL_REQUIRED", "exempt_actions": []}
        draft = base_case(name="prepare-draft", scope="internal", requires_human=False)
        self.assertEqual(evaluate(draft)["verdict"], "PASS")
        report = evaluate(draft, stricter)
        self.assertEqual(report["verdict"], "FAIL")
        self.assertEqual(report["approval_check"]["policy_id"], "no-exemptions")
        self.assertEqual(report["policy_sha256"], policy_digest(stricter))
        for broken in ({**stricter, "default": "NO_APPROVAL_REQUIRED"}, {**stricter, "exempt_actions": [{"name": "x"}]},
                       {**stricter, "surprise": True}, {"policy_id": "x"}, [], "not-a-policy"):
            with self.subTest(policy=broken), self.assertRaises(PolicyError):
                evaluate(draft, broken)
        twice = {**stricter, "exempt_actions": [{"name": "a", "scope": "b", "rationale": "duplicate entry one"},
                                                 {"name": "a", "scope": "b", "rationale": "duplicate entry two"}]}
        with self.assertRaisesRegex(PolicyError, "twice"):
            evaluate(draft, twice)

    def test_evaluation_never_changes_the_policy_or_the_case(self):
        policy, case = load_policy(), base_case(**SEND, requires_human=False)
        before = json.dumps(policy, sort_keys=True), json.dumps(case, sort_keys=True)
        evaluate(case)
        self.assertEqual(before, (json.dumps(policy, sort_keys=True), json.dumps(case, sort_keys=True)))

    def test_cli_policy_file_and_fail_closed_loading(self):
        with tempfile.TemporaryDirectory() as folder:
            strict = Path(folder) / "strict.json"
            strict.write_text(json.dumps({"policy_id": "no-exemptions", "policy_version": "1.0",
                                          "default": "HUMAN_APPROVAL_REQUIRED", "exempt_actions": []}), encoding="utf-8")
            broken = Path(folder) / "broken.json"
            broken.write_text('{"policy_id":"x","policy_id":"y"}', encoding="utf-8")
            default = cli("evaluate", "examples/customer_followup.json")
            tightened = cli("evaluate", "examples/customer_followup.json", "--policy", str(strict))
            refused = cli("evaluate", "examples/customer_followup.json", "--policy", str(broken))
        self.assertEqual(default.returncode, 0, default.stderr)
        self.assertEqual(tightened.returncode, 1)
        self.assertIn("CASE_WAIVER_IGNORED", tightened.stdout)
        self.assertEqual(refused.returncode, 2)
        self.assertIn("DUPLICATE_KEY", refused.stderr)
        shown = json.loads(cli("policy").stdout)
        self.assertEqual(shown["sha256"], policy_digest(load_policy()))
        self.assertIn("Authenticates nobody", shown["note"])

    def test_report_states_what_the_policy_does_not_cover(self):
        report = evaluate(base_case(**SEND, requires_human=True,
                                    human_approval={"approved": True, "actor_type": "HUMAN", **{"scope": "external", "action": "send-external-email"}}))
        self.assertEqual(report["approval_check"]["result"], "ALLOW_IN_SIMULATION")
        self.assertFalse(report["approval_check"]["authenticated"])
        self.assertTrue(any("not authenticated" in text for text in report["limitations"]))


class DeterminismAndNormalisation(unittest.TestCase):
    def test_report_digest_does_not_depend_on_the_hash_seed(self):
        facts = [{"id": f"F{i}", "text": f"estimate {i}", "status": "TO_CONFIRM"} for i in (7, 3, 9, 1, 5, 8, 2, 6, 4)]
        case = {"case_id": "order", "source": {"facts": facts}, "handoff": {"facts": [dict(f, status="FACT") for f in facts]},
                "action": {"name": "prepare-draft", "scope": "internal"}}
        script = "import json,sys; from ddlab.core import evaluate; print(evaluate(json.load(sys.stdin))['report_sha256'])"
        digests = set()
        for seed in ("0", "1", "2", "3", "4", "5"):
            proc = subprocess.run([sys.executable, "-c", script], cwd=ROOT, input=json.dumps(case), capture_output=True,
                                  text=True, timeout=30, env=dict(os.environ, PYTHONHASHSEED=seed))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            digests.add(proc.stdout.strip())
        self.assertEqual(len(digests), 1)

    def test_status_vocabulary(self):
        self.assertEqual(status_class("REVOKED"), ("REVOKED", True))
        self.assertEqual(status_class(" revoked\t"), ("REVOKED", False))
        self.assertEqual(status_class("in force"), ("ACTIVE", False))
        self.assertEqual(status_class("To-Confirm"), ("UNCERTAIN", False))
        self.assertEqual(status_class("archived"), (None, True))
        self.assertEqual(status_class(None), (None, True))
        self.assertEqual(status_class("RΕVOKED"), (None, True), "a look-alike letter is not an alias")

    def test_text_profile_is_a_hint_and_says_when_it_cannot_judge(self):
        dropped = text_profile("Draft only, never send without approval", "Draft and send with approval")
        self.assertTrue(dropped["negation_changed"])
        self.assertFalse(dropped["formatting_only"])
        self.assertTrue(text_profile("Budget is 400", "Budget is 4,000")["numbers_changed"])
        self.assertTrue(text_profile("Do not send.", "do not send")["formatting_only"])
        other_script = text_profile("不要发送", "发送")
        self.assertTrue(other_script["non_ascii_content"])
        self.assertFalse(other_script["formatting_only"])

    def test_paraphrase_still_fails_but_carries_a_profile(self):
        case = base_case(name="prepare-draft", scope="internal")
        case["handoff"]["decisions"][0]["text"] = "Prepare a draft only; do not send it unless a human approves"
        report = evaluate(case)
        self.assertEqual(report["verdict"], "FAIL")
        profile = report["decisions"]["changes"][0]["text_profile"]
        self.assertFalse(profile["negation_changed"])
        self.assertGreater(profile["shared_tokens"], 0)


class RevocationTrace(unittest.TestCase):
    def test_structured_ledger_keeps_the_revoked_item_itself(self):
        case = base_case(name="prepare-draft", scope="internal", requires_human=False)
        revoked = {"id": "D2", "text": "Send the reminder to everyone", "authority": "OWNER", "status": "REVOKED"}
        case["source"]["decisions"].append(revoked)
        report = evaluate(case)
        self.assertEqual(report["revocation_ledger"],
                         [{"id": "D2", "source_status": "REVOKED", "handoff_state": "NOT_CARRIED", "source_item": revoked}])
        codes = [f["code"] for f in report["findings"]]
        self.assertEqual(codes, ["DECISIONS_MISSING", "REVOKED_DECISION_TRACE_LOST"])
        case["handoff"]["decisions"].append(dict(revoked))
        self.assertEqual(evaluate(case)["revocation_ledger"][0]["handoff_state"], "CARRIED_AS_REVOKED")
        self.assertEqual(evaluate(case)["verdict"], "PASS")

    def test_every_revoked_corpus_decision_has_a_ledger_entry_with_valid_spans(self):
        revoked = 0
        for case in DEV["cases"] + HELDOUT["cases"]:
            ledger = {e["item_id"]: e for e in revocation_ledger(case)}
            texts = {t["turn"]: t["text"].encode("utf-8") for t in case["source"]["turns"]}
            for item in case["items"]:
                if item["source_status"] != "REVOKED":
                    self.assertNotIn(item["item_id"], ledger)
                    continue
                revoked += 1
                entry = ledger[item["item_id"]]
                for ref in [entry["statement_ref"], *entry["revocation_refs"]]:
                    self.assertEqual(texts[ref["turn"]][ref["start_byte"]:ref["end_byte"]].decode("utf-8"), ref["excerpt"])
                self.assertEqual(entry["ambiguity"] is not None, item["handoff_outcome"] == "NOT_CARRIED_OK")
        self.assertEqual(revoked, 7)

    def test_not_carried_is_flagged_everywhere_but_not_counted_as_drift(self):
        for case_id in ("HD-07", "HH-04"):
            _, case = corpus.find_case(case_id)
            self.assertFalse(case["expected_drift"])
            self.assertEqual(corpus.derive_ambiguities(case), ["REVOKED_DECISION_TRACE_LOST"])
            entry = revocation_ledger(case)[0]
            self.assertEqual(entry["trace"], "NO_VERBATIM_TRACE_IN_HANDOFF")
            self.assertIn("Confirm with the owner", entry["ambiguity"])
            self.assertIn("AMBIGUOUS: not carried", cli("recover", case_id).stdout)


def filled_form(doc, target="heldout-human"):
    """Test-only: re-express the candidate labels as a completed form. No person filled this in."""
    form = labeling.blind_form(doc)
    form["target_split"] = target
    form["labeller"] = {"label": "test-fixture-not-a-person", "date": "2026-01-01",
                        "independence": {"has_read_baseline_code": False, "has_seen_candidate_labels": False,
                                         "wrote_these_cases": target == "independent-heldout"}}
    by_id = {c["case_id"]: c for c in doc["cases"]}
    for entry in form["cases"]:
        case = by_id[entry["case_id"]]
        for item in case["items"]:
            refs = {role: [{"turn": e["turn"], "quote": e["excerpt"]} for e in item["evidence"] if e["role"] == role]
                    for role in ("statement", "superseded", "revocation", "qualification")}
            entry["items"].append({
                "item_id": item["item_id"], "kind": item["kind"], "status": item["source_status"],
                "authority": item["authority"], "authority_bearing": item["authority_bearing"],
                "statement": refs["statement"][0], "superseded": refs["superseded"], "revocation": refs["revocation"],
                "qualification": refs["qualification"], "outcome": item["handoff_outcome"],
                "handoff_quote": item["handoff_evidence"]["excerpt"] if item["handoff_evidence"] else None,
                "handoff_authority": item["handoff_authority"]})
        entry["introduced"] = [{"item_id": x["item_id"], "kind": x["kind"], "handoff_quote": x["handoff_evidence"]["excerpt"],
                                "note": x["note"]} for x in case["introduced"]]
    return form


class LabellingKit(unittest.TestCase):
    def test_blind_form_reveals_no_label_and_no_title(self):
        form = labeling.blind_form(HELDOUT)
        flat = json.dumps(form, ensure_ascii=False)
        for case in HELDOUT["cases"]:
            self.assertNotIn(case["title"], flat)
            self.assertNotIn(case["labeling_note"], flat)
        self.assertTrue(all(entry["items"] == [] and entry["introduced"] == [] for entry in form["cases"]))
        self.assertNotIn("expected_findings", flat)
        self.assertNotIn("CANDIDATE", flat)
        self.assertEqual(len(form["cases"]), 12)

    def test_packaged_kit_files_match_the_generators(self):
        kit = ROOT / "research" / "labeling-kit"
        self.assertEqual(json.loads((kit / "heldout-blind-form.json").read_text(encoding="utf-8")), labeling.blind_form(HELDOUT))
        self.assertEqual(json.loads((kit / "independent-case-template.json").read_text(encoding="utf-8")),
                         labeling.independent_template())

    def test_no_human_label_file_is_packaged(self):
        self.assertFalse((corpus.CORPUS_DIR / "heldout-human.json").exists())
        self.assertFalse((corpus.CORPUS_DIR / "independent-heldout.json").exists())

    def test_compiler_computes_spans_and_records_an_unauthenticated_review(self):
        compiled = labeling.compile_form(filled_form(HELDOUT))
        self.assertEqual(compiled["split"], "heldout-human")
        self.assertIn("unauthenticated", compiled["provenance"]["independence"])
        for mine, theirs in zip(compiled["cases"], HELDOUT["cases"]):
            self.assertEqual(mine["items"], theirs["items"])
            self.assertEqual(mine["expected_findings"], theirs["expected_findings"])
            self.assertEqual(mine["review"]["state"], "HUMAN_REVIEWED")
            self.assertEqual(mine["label_state"], "HUMAN_REVIEWED_UNAUTHENTICATED")
            self.assertEqual(mine["title"], theirs["title"])

    def test_compiler_refuses_incomplete_non_blind_or_altered_forms(self):
        def broken(change, target="heldout-human"):
            form = filled_form(HELDOUT, target)
            change(form)
            return form

        def no_labeller(form):
            form["labeller"]["label"] = None

        def saw_candidates(form):
            form["labeller"]["independence"]["has_seen_candidate_labels"] = True

        def read_code(form):
            form["labeller"]["independence"]["has_read_baseline_code"] = True

        def unanswered(form):
            form["labeller"]["independence"]["wrote_these_cases"] = None

        def altered_text(form):
            form["cases"][0]["handoff"] += " Extra sentence."

        def dropped_case(form):
            form["cases"].pop()

        def ambiguous_quote(form):
            form["cases"][0]["items"][0]["statement"]["quote"] = "e"

        def unlabelled(form):
            form["cases"][0]["items"] = []

        def missing_field(form):
            del form["cases"][0]["items"][0]["outcome"]

        for change, message in ((no_labeller, "labeller.label"), (saw_candidates, "not blind"), (read_code, "not blind"),
                                (unanswered, "independence questions"), (altered_text, "differs from the packaged"),
                                (dropped_case, "exactly the cases"), (ambiguous_quote, "must occur exactly once"),
                                (unlabelled, "no item was labelled"), (missing_field, "malformed or incomplete")):
            with self.subTest(case=message), self.assertRaisesRegex(labeling.LabelFormError, message):
                labeling.compile_form(broken(change))
        with self.assertRaisesRegex(labeling.LabelFormError, "at least 20 cases"):
            form = filled_form(HELDOUT, "independent-heldout")
            form["data_rights"] = "My own fiction, written for this corpus; it may be used here."
            labeling.compile_form(form)
        with self.assertRaisesRegex(labeling.LabelFormError, "EXAMPLE placeholder"):
            template = labeling.independent_template()
            template["labeller"] = filled_form(HELDOUT, "independent-heldout")["labeller"]
            template["data_rights"] = "My own fiction, written for this corpus; it may be used here."
            template["cases"] = template["cases"] * 20
            labeling.compile_form(template)

    def test_independent_set_of_twenty_compiles(self):
        form = filled_form(DEV, "independent-heldout")
        form["source_split"], form["source_text_sha256"] = None, None
        form["data_rights"] = "Test fixture only: text copied from the packaged dev split to exercise the compiler."
        form["cases"] = form["cases"][:20]
        for entry, case in zip(form["cases"], DEV["cases"]):
            entry["domain"], entry["title"] = case["domain"], case["title"]
        compiled = labeling.compile_form(form)
        self.assertEqual((compiled["split"], len(compiled["cases"])), ("independent-heldout", 20))
        self.assertEqual(compiled["provenance"]["authoring"], "FICTIONAL_HUMAN_WRITTEN_AND_LABELLED")

    def test_agreement_report_counts_and_disclaims(self):
        human = labeling.compile_form(filled_form(HELDOUT))
        same = labeling.agreement(HELDOUT, human)
        self.assertEqual(same["case_level_agreement"], {"agree": 12, "of": 12})
        self.assertEqual(same["cohen_kappa_case_level"], 1.0)
        self.assertEqual(same["items"]["matched"], same["items"]["same_outcome"])
        self.assertIn("Not accuracy", same["meaning"])
        self.assertFalse(same["human_review"]["authenticated"])
        differing = deepcopy(human)
        target = next(c for c in differing["cases"] if c["case_id"] == "HH-04")
        target["expected_findings"], target["expected_drift"] = ["DECISIONS_MISSING"], True
        other = labeling.agreement(HELDOUT, differing)
        self.assertEqual(other["case_level_drift"]["human_only_drift"], 1)
        self.assertEqual(other["case_level_agreement"], {"agree": 11, "of": 12})
        self.assertLess(other["cohen_kappa_case_level"], 1.0)

    def test_human_labels_unlock_the_confusion_matrix(self):
        from ddlab import baselines
        run = baselines.run_baselines(labeling.compile_form(filled_form(HELDOUT)))
        self.assertEqual(run["label_review"], {"human_reviewed": 12, "not_reviewed": 0})
        matrix = run["baselines"]["exact_text"]["confusion_matrix"]
        self.assertEqual(sum(matrix.values()), 12)
        self.assertEqual(matrix["false_negative"], 1)  # HH-06, with the fixture's copy of the candidate labels

    def test_cli_kit_compile_agreement_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            form_path, human_path = Path(folder) / "form.json", Path(folder) / "human.json"
            form_path.write_text(json.dumps(filled_form(HELDOUT), ensure_ascii=False), encoding="utf-8")
            compiled = cli("corpus", "compile", str(form_path))
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            human_path.write_text(compiled.stdout, encoding="utf-8")
            report = cli("corpus", "agreement", "--human", str(human_path))
            self.assertEqual(report.returncode, 0, report.stderr)
            self.assertEqual(json.loads(report.stdout)["case_level_agreement"], {"agree": 12, "of": 12})
            empty = cli("corpus", "compile", str(ROOT / "research" / "labeling-kit" / "heldout-blind-form.json"))
        self.assertEqual(empty.returncode, 2)
        self.assertIn("labeller.label", empty.stderr)
        self.assertEqual(json.loads(cli("corpus", "kit").stdout), labeling.blind_form(HELDOUT))


class ProofPack(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = build()

    def test_packaged_files_are_reproduced_exactly(self):
        self.assertEqual(json.loads(PROOFPACK_JSON.read_text(encoding="utf-8")), self.pack)
        self.assertEqual(PROOFPACK_MD.read_text(encoding="utf-8"), render_markdown(self.pack))

    def test_every_row_answers_the_eight_questions(self):
        fields = ("source", "exact_passage", "decision", "detected_change", "rules_applied", "result", "uncertainty",
                  "human_validation")
        ids = [row["result_id"] for row in self.pack["rows"]]
        self.assertEqual(len(ids), len(set(ids)))
        for row in self.pack["rows"]:
            with self.subTest(row=row["result_id"]):
                for field in fields:
                    self.assertTrue(row[field] or row[field] == [], field)
                self.assertTrue(row["exact_passage"])
                self.assertTrue(row["uncertainty"], "every result states what the method cannot tell")
                self.assertTrue(set(row["rules_applied"]) <= set(RULES))
                self.assertIn("file_sha256", row["source"])

    def test_counts_and_absence_of_human_validation(self):
        summary = self.pack["summary"]
        self.assertEqual(summary["by_category"], {"corpus-item": 115, "corpus-introduced": 4, "corpus-case": 37, "engine-probe": 28})
        self.assertEqual(summary["rows_with_recorded_human_validation"], 0)
        self.assertTrue(all(row["human_validation"]["state"] == "NONE" for row in self.pack["rows"]))
        self.assertFalse(self.pack["attestation"]["signed"])
        self.assertEqual(summary["corpus_items_recoverable_verbatim"] + summary["corpus_items_owner_reconfirmation"], 115)

    def test_corpus_rows_point_at_the_exact_passage(self):
        texts = {(split, c["case_id"], t["turn"]): t["text"].encode("utf-8")
                 for split, doc in (("dev", DEV), ("heldout", HELDOUT)) for c in doc["cases"] for t in c["source"]["turns"]}
        checked = 0
        for row in self.pack["rows"]:
            if row["category"] != "corpus-item":
                continue
            src = row["source"]
            passage = texts[(src["split"], src["case_id"], src["turn"])][src["start_byte"]:src["end_byte"]].decode("utf-8")
            self.assertEqual(passage, row["exact_passage"])
            checked += 1
        self.assertEqual(checked, 115)

    def test_a_recorded_review_shows_up_as_unauthenticated(self):
        from ddlab.proofpack import _validation
        human = labeling.compile_form(filled_form(HELDOUT))
        seen = _validation(human["cases"][0])
        self.assertEqual(seen["state"], "RECORDED_UNAUTHENTICATED")
        self.assertEqual(seen["reviewer_label"], "test-fixture-not-a-person")
        self.assertEqual(_validation(HELDOUT["cases"][0])["state"], "NONE")

    def test_cli_proofpack(self):
        self.assertEqual(json.loads(cli("proofpack").stdout), self.pack)
        self.assertIn("Rows with a recorded human validation: **0**", cli("proofpack", "--format", "md").stdout)


class StrictPathStillRejectsHiddenCharacters(unittest.TestCase):
    def test_policy_file_goes_through_strict_intake(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "p.json"
            path.write_bytes(b'{"policy_id":"x\\u202e","policy_version":"1.0","default":"HUMAN_APPROVAL_REQUIRED","exempt_actions":[]}')
            with self.assertRaises(IntakeError):
                load_policy(path)


if __name__ == "__main__":
    unittest.main()
