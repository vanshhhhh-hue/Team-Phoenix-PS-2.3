> Historical lab-only checkpoint. Current product scope is in root PROJECT.md.

# In-process application contract — version 1 (implemented)
No custom REST endpoints, authentication or CORS. Browser connects to Streamlit at localhost:8501.
Implemented in engine.py, workflow.py and ledger.py; app.py calls these operations directly.

## Content and evaluation
`load_packs(path) -> Content`: validate schema_version=1, globally unique question/hint IDs,
references, exactly one correct option per question, supported families/rules, bounded integer parameters.
Use top-level packs, questions and hints collections in data/packs.json.
Pack fields: id, title, parameters, original_template_id, faulty_rule_id, correct_rule_id,
diagnostic_question_id, reason_options, probe_question_id, canonical_explanation, hint_ids,
repair_question_id, transfer_question_ids (symbolic then representation), delayed_question_ids.
Display fields: subtitle, original_latex, faulty_latex, correct_latex, faulty_rule_latex,
correct_rule_latex, repair_reason. Diagnostic is a reference into the top-level question collection.
Question fields: id, role, prompt, optional latex, options[{id,text}], correct_option_id.
Question context: diagnostic/probe/repair/transfer/delayed. Two hints per family.
Reject bools as integers; parameters and interactive x are integers in -5..5.
Distribution excludes a=0/1 and b=0; square and negative bracket exclude b=0.
`evaluate(family_id, rule_kind, parameters, x) -> int`: original/faulty/correct, normal functions only.
`find_counterexample(family_id, parameters) -> Counterexample | None`: first mismatch in
[0,1,-1,2,-2,3,-3]; None means no counterexample in this set, never equivalence.
Counterexample: {x, original_value, rewritten_value}; family and rule IDs remain attached to its record.
Example: distribution, {a:3,b:2}, x=1 -> original=9, faulty=5, correct=9.
Search returns {x:0,original_value:6,rewritten_value:2}; repair regression inputs [-1,0,1].

## Workflow
`new_lab(family_id) -> lab`; `new_progress() -> progress`.
`submit_response(state, response, token, now, progress, content) -> (lab, progress)`:
deep-copy inputs, consume each displayed-question token once. Validation failure leaves inputs untouched.
`current_question(lab, content)` returns the authored question for the stage.
`request_help(lab, content)` returns a copied lab with a capped hint count (two hints, then explanation).
Attempt fields: attempt_id, question_id, selected_option_id, reason_id (nullable), context,
help_used (bool), submitted_at (timezone ISO 8601), session_id.
Lab includes family_id, stage, session_id, token, pending_answer, evidence, candidate, test_result,
help_counts, transfer_results, transfer_index, feedback and consumed_tokens; attempts live in progress.
PREDICT -> SELECT_REASON -> optional PROBE -> TEST_RULE -> INSPECT_CONTRADICTION
-> REPAIR_RULE -> TRANSFER -> LEDGER; navigation preserves the current stage.
Explicit intermediate stages: UNCLEAR, REPAIR_VERIFIED and TRANSFER_FEEDBACK.
PREDICT locks selected_option_id; SELECT_REASON supplies reason_id; PROBE supplies both.
TEST_RULE accepts integer x and boolean predict_equal. Navigation transitions use actions:
guided, repair, transfer and next. Repair accepts selected_option_id plus reason_id.
Transfer accepts selected_option_id; help is tracked by request_help, never a self-cleared checkbox.
Collect reason before correctness feedback; do not reveal answer while eliciting reasoning.
Matching faulty answer/reason -> candidate; conflict/unsure -> one authored probe.
Unresolved probe -> unclear and guided example. Correct answer with correct reason -> direct transfer.
Correct answer with faulty/unsure reason -> ambiguity probe, never a success badge or forced diagnosis.
Repair requires correct rule AND structured explanation; three numerical agreements alone are insufficient.
Two transfer items are different from diagnostic, probe and worked repair items.
Both correct, unassisted -> transfer_passed; symbolic failure -> needs practice;
symbolic success/representation failure -> needs transfer practice; any help -> assisted, no gate pass.
Lock submitted transfer results. Previously graded transfer questions are practice/assisted on retry.
Withhold the first item's correctness until both transfer answers are submitted.

## Ledger and scheduling
`record_event(progress, family_id, event) -> record`: mutate the copied progress; one record per family.
Earlier evidence is preserved; `original_rule_id` stays null unless a candidate rule was supported.
Record fields: record_id, family_id, status, original_rule_id, repaired_rule_id (nullable),
counterexample (nullable), attempt_ids, events, next_check_at (nullable), successful_delayed_checks.
Event fields: event_id, kind, occurred_at, attempt_id (nullable), details. Deduplicate by event_id.
Status: candidate/tested/repaired/transfer_passed/delayed_check_passed/reopened/unclear.
`review(progress, family_id, response, token, now, content, preview=False) -> progress`:
response has selected_option_id, reason_id, optional help_used and session_id; return a deep copy.
The due review needs a correct answer AND reason without help. First due +1 day after transfer;
first successful due review schedules +3 days; subsequent successes +7 days.
Failure -> reopened; preserve past events and clear next_check_at until repair and transfer pass again.
Preview before due date cannot change status, successful count or schedule.
UI previews show a worked-example rehearsal; actual delayed question remains hidden until due.
`recommend_next(progress, now) -> (family_id | None, action, page)`:
reopened, unresolved repair, due review, unattempted family.
Within each tier use content order for deterministic ties. Inject an aware clock in tests.

## Progress boundary and errors
`export_progress(state) -> str`: JSON {schema_version:1, attempts:[], records:[]} with no credentials.
`import_progress(text, content) -> progress`: max 1 MiB UTF-8; reject invalid JSON, versions,
unknown IDs, duplicate IDs, invalid references/statuses/dates and inconsistent event/attempt links.
Validate all data before replacing session state; never load objects with pickle or execute input.
Operation errors use `DomainError(code, message)`; UI shows readable text and preserves state.
Codes: invalid_content, invalid_input, invalid_transition, invalid_progress, oversized_progress.
Duplicate submission is a no-op with the existing result, not an extra attempt or exception.
Example invalid import: {"schema_version":99,"attempts":[],"records":[]} -> invalid_progress.
Example empty export: {"schema_version":1,"attempts":[],"records":[]}.
Reset requires an explicit UI action, clears learner state, and retains content.

## Optional model aid
Deferred provider: canonical explanation is always available. A paraphrase cannot alter state or keys.
Generated text is labelled unreviewed; absent key, timeout or malformed output uses canonical content.
No provider variables, endpoints or dependency are invented before credentials are selected.

Change log: implemented v1 — concrete signatures, referenced diagnostic questions, intermediate stages,
practice-only repeated transfer items, no-leak preview and closed-schema progress validation.
