# Physics showcase contract — current demo entry point

Default demo mode now dispatches root app.py to src/phoenix/showcase_app.py. Local mode retains
all schema-v6 contracts below. This change adds no fields to personal study checkpoints.

`showcase.load_showcase()` validates the version-2 synthetic fixture in
samples/users/user-1/physics/showcase.json (eight chapters, 88 questions, six profiles).
The original v6 personal checkpoint schema is unchanged. An active v1 showcase session upgrades
its bank/chapters while retaining its student history. Prior two-attempt rounds are copied by
`upgrade_round`; an old two-error solution stage becomes approach, allowing the third attempt.

`start_round` begins five distinct concepts. `respond` allows answer/hint/approach stages and
records at most three responses per item with attempt=1/2/3. A wrong response transitions to
hint, then approach, then solution; any correct response transitions to feedback. `advance`
is allowed only from feedback/solution and inserts an unused same-concept item after an initial
error, up to MAX_QUESTIONS=15. Eleven variants per concept support a full chain plus remaining
core items. First correctness stays immutable; retries do not increase first-answer counts.

`record_response` appends first records once and retains separate support_attempts and latest
retry_correct. It tracks hint_used, approach_used and solution_used independently. Student and
teacher selectors use the same session cohort. Recall ratings remain session-only.

`physics_teaching.guided_approach` returns the principle, three method steps and a check without
interpolating the computed result. `worked_explanation` adds calculation, expected answer and
chosen-error correction. `recall_cards` returns 24 cards across concept/relation/pitfall kinds.
`physics_cards.flashcard_html` escapes every content field and supplies a static HTML/CSS/JS
flip control embedded through st.iframe, with aria state, keyboard support and reduced motion.
No upload, provider HTML or remote asset is embedded in that frame.

`teaching_report(data, student_ids=None)` aggregates per-topic counts, affected learners, recent
five-answer errors and distractor patterns. Priority score = .60*error_rate + .25*affected_share
+ .15*recent_error_rate. Zero-error topics are omitted from plans; no-data counts do not divide
by zero. Each plan includes topic-specific counterstrategy, 3/7/5-minute teaching steps, a
3-minute exit check and a 2-minute next-step review. Checks prefer questions with no recorded
exposure in the selected cohort; exhausted banks are labelled review checks. No mastery or
certain diagnosis is inferred. Class analysis precedes the roster; individual reports use the
same selector scoped to one student. Class and individual plans can be exported.

Showcase state remains in physics_* Streamlit session keys. No-auth Teacher Dashboard is a
product demonstration, not a tenant database; synthetic provenance is retained in docs/exports.
`workspace_view=Uploads` opens an empty nonpersistent study workspace. Private checkpoints are
not loaded or modified by showcase interactions. No deployment is authorised by this update.

# Repository layout and demo runtime

Application modules are now under `src/phoenix/`; root `app.py` configures their import path.
Authored Newton material is `samples/users/user-1/nlm-v1.json`; the biology source fixture is
`samples/users/user-1/demo-notes.md`. No data schema or operation signature changed in this reorganisation.
Default `PHOENIX_MODE=demo` initialises a validated fictional User 1 fixture per Streamlit session.
It sets `study_persist=False`; UI commits update that session only. Persistent restore/rollover
controls are not rendered in demo mode. Reset loads a fresh fixture. No private checkpoint is opened.
`PHOENIX_MODE=local` retains the existing v6 persistence contract below. `PHOENIX_DATA_DIR`
may override `.local`; process environment configuration is required for runtime settings.
The obsolete presentation-only hard-coded sample overview has been removed. All displayed
User 1 scores now derive from ordinary sample activity through existing report selectors.

# In-process contract - Phoenix
No custom REST API; browser connects to Streamlit on 127.0.0.1:8501.
Historical algebra operations are preserved in docs/LAB_API_CONTRACT.md and their existing modules.

## Current reliability contract — schema v6 (31 October 2026)

This section supersedes older persistence/navigation descriptions below. Historical domain
collections and old Newton event replay remain compatible; no original grade is rewritten.

### Storage
`storage.read_workspace(path) -> LoadResult(status,state,code,checkpoints)` returns ready only
with a validated checkpoint. Missing files install a new UUID/revision-0 workspace. v2–v5
migrate purely, validate, retain the original bytes as `.previous`, then install revision 1.
Failures preserve the original file; startup recovery renders before ordinary study pages.
`workspace_busy` has a retry path. Corrupt originals can be downloaded as recovery files.

`transact(path,workspace_id,expected_revision,command_id,operation,now,payload_hash=...)`
returns `CommitResult(status,state,revision,message)`: committed/already_applied/conflict/
rejected/io_error. A SHA-256 command-payload fingerprint is required. A stable sibling `.lock`
uses an in-process RLock plus msvcrt byte locking on Windows (flock on Unix), bounded to 3 s.
Identity/revision and receipts are checked inside the lock before running the operation.
Same-token/same-payload retries precede revision rejection; changed payloads are rejected.
Receipts retain the last 256 commands. Durable answer/rating/support tokens guard older retries.

`commit_snapshot(path,base,updated,now,command_id)` is the transitional CAS adapter for existing
pure domain operations. It never merges a stale snapshot. Callers install only its returned
canonical state. `study.save_state` is a compatibility adapter returning that canonical state;
production UI commits use storage directly. First answers, source content, original question
content, saved pack descriptors and existing activity-event prefixes cannot be rewritten.
Only explicit scoped demo/debugger history resets may remove their corresponding activity data.

Writes validate and serialize UTF-8 once for installation, enforce 8 MiB, write beside the
checkpoint, flush/fsync, retain a validated `.previous`, then replace atomically. Generation
and network calls run before acquiring a storage lock. Failure never announces Saved.
`storage_usage` reports bytes/limit/fraction/level (80% warning, 95% critical).

`prepare_restore(path,backup_bytes,now) -> RestorePreview` validates first and binds immutable
backup bytes/hash, current-file hash, workspace identity/revision, counts and known save date.
`apply_restore(path,preview_id,expected_revision,now)` accepts its process-local UUID (or the
preview object for adapters), rechecks exact hashes/revision under lock, preserves `.pre-restore`,
and installs a fresh workspace UUID/revision 0. Undo previews that retained checkpoint through
the same path. The UI clears volatile reveal/widget/feedback caches after successful replacement.
Export/start-new-workspace uses a validated full backup and explicit replacement confirmation.

### Exact additive namespaces
Every top-level v6 field is closed; legacy fields remain documents/quizzes/attempts/cards/reviews/
nlm/debugger/practice_events. Additional fields are:

* `workspace_id`: canonical UUID; `revision`: nonnegative integer; `last_saved_at`: aware ISO
  timestamp, or null only at revision 0 before installation.
* `material_meta`: existing material ID -> `{visibility:active|history|archived,title:null|string
  (1–100),active_pack:null|pack-version ID}`. Renaming never edits original source titles.
* `pack_versions`: max 200 immutable descriptors. Exact fields: id,document_id,version,mode,
  kind (ordinary|independent),origin_item_id (null or source-local original question),summary,
  topics,question_ids,card_ids,source_ids,selected_source_ids,requested_count,
  requested_difficulty,created_at,quality. Content bodies remain canonical in documents/cards.
  Counts apply per version (3–20 items); aggregate storage retains the 8 MiB limit.
  Selected IDs describe the requested source scope; source_ids describe assessed question
  references. Provider sampling is at most 18 excerpts/24,000 characters. Historical requested
  settings are null; migration does not establish historical API coverage or human review.
* `quality`: exact source_references (`validated`), local_keys (`validated` or `not independently
  verified`), semantic_review (`not performed` or `passed`), authored_review (false),
  question_count,card_count. Generated semantic review is fallible and never authored review.
* `activity_events`: max 30,000. Exact id,learner,material_id,activity_id,item_id,kind,value,at.
  `present`: null value; a round reserves its item presentations atomically before prompts.
  Repeated ordinary presentations are allowed across rounds; independent IDs cannot be reused.
  `hint`: integer level 1 then 2, current unanswered upload item only, before first-answer time.
  `experiment`: lesson context; value `{version:1,parameters,prediction:0|1,explanation,result}`.
  `debugger_experiment`: exact repair-case context; value `{version:1,parameters,prediction,result}`.
  Parameters/results are recomputed with bounded scenario-v1 models; explanation <=4,000 chars.
  These observations never contribute objective grades or independent-check success.
* `item_status`: uploaded question/card ID -> `{status:disputed|quarantined|retired,reason,
  feedback,at}`; max 5,000. Reasons: answer seems wrong/ambiguous choices/missing source support/
  explanation unclear/other; feedback <=1,000. New selection and actionable metrics exclude
  flagged items; raw historical grades remain visible. In-progress responses are practice only.
* `drafts`: max 100 exact `{learner,material_id,activity_id,item_id,text,updated_at}` records;
  text 1–4,000 chars. Context must be an owned quiz item, Newton-session concept item or card
  (`activity_id=cards`). Explicit saving/clearing is ungraded; conflicts retain safe widget input.
* `preferences`: only use_ai (bool), last_material (validated material ID), last_context
  (max one validated NavigationTarget per supported learner), source_preview. Source preview
  exact fields: title,filename,count,difficulty,text,chunks; extraction limits/references apply.
  This durable staged source is removed only on successful promotion or explicit cancellation.
* `command_receipts`: max 256 exact `{id,hash,revision}` records; token <=100 chars, SHA-256 hash,
  committed revision positive and no greater than checkpoint revision. No request bodies/secrets.

Imports recompute original answer keys, support replay, card schedules and all references.
Old missing assistance remains unknown; recorded historical hint_count values remain unchanged.

### Commands, navigation and selectors
`NavigationTarget` has page,material_id,learner,activity_kind,activity_id,topic_id,item_id,card_view.
Pages are the five primary destinations. Learners: My learning/Demo Learner A/Demo Learner B.
Activity kinds: lesson/upload_quiz/newton_session/repair/cards/report/null. Queues: due/new/preview.
Targets validate learner/source/session/card ownership. Queued targets apply before widget creation.
Safe URL context contains only route labels and opaque IDs, including exact quiz/session IDs.
Legacy aliases and subordinate Newton destinations map into primary navigation; no second Newton
navigation bar remains. Invalid links visibly fall back to Library. Demo context is secondary.

`study_flow.upload_activity_view(state,quiz_id)` separates scoring_complete/recovery_complete,
current item/phase, pending support, first attempt/latest retry, help stages, solution and resume
route/result summary. Finished scoring with unfinished recovery resumes recovery after refresh.
`show_hint` persists before display; production `submit_answer` derives hints from that stream.
`answer_question` remains a low-level compatibility adapter for historical callers.
Wrong-first automatic recovery is derived durably from its saved attempt; retries/acknowledgements
append practice events. First, latest and stage-specific help are displayed separately.

`workspace.card_queue` supplies both upload/Newton counts and items. New = never reviewed;
due = reviewed and due_at <= injected now; upcoming = reviewed and future. Preview cannot
reschedule early. Again/Hard/Good/Easy intervals remain unchanged and imports replay them.
`pending_tasks` separates unfinished/due/upcoming/blocked work. `recommend_next` returns executable
validated targets, including uploaded recovery, source-local weak topics and exact saved cases.
`report` keeps first answers, recovery, fresh checks, delayed checks and self-rated cards separate;
identical prompts regenerated within a source remain repeated evidence. Topic names are human labels.

`regenerate_document` appends globally unique questions/cards and a new immutable version;
old keys, cards/schedules and reports remain resolvable. New rounds use the active version.
`followups.build_followup` requests changed-source examples without sending learner answers/history.
Source validation, a second semantic/equivalence review, same-topic and lexical novelty gates must
all pass; otherwise no independent pack is promoted. Eligible generated packs are labelled as
fallible generated checks. Help excludes independent passes; exhaustion never becomes success.

`nlm.event` writes continue_v2/transfer_v2/delayed_v2 with the chosen target ID, selected from
all globally unused eligible items before mutation. Historical unversioned events keep old replay.
Scenario-v1 experiments cover all 12 concepts with meaningful inputs, SI outputs/assumptions,
structured saved predictions and matching textual alternatives. Changed controls invalidate reveal.

`ai_provider.connection_check` checks the configured model's generateContent capability; it does
not claim generation/quota readiness. Actual generation and independent automated review are
separate calls. Only sampled source excerpts and bounded content are sent; never learner history.
The explicit live smoke script uses synthetic notes only and writes no learner checkpoint.

## Source ingestion and pack generation (study.py)
extract_upload(filename, bytes) -> (text, chunks): PDF/TXT/MD, 10 MiB, PDF <=60 pages,
80-100,000 extracted characters. Encrypted, scanned/empty and malformed PDFs fail readably.
Chunk: {id, text, page: int|null, section}. IDs are local to a document; citations use these IDs.
add_document(state, title, filename, bytes, count=6, difficulty='mixed', use_ai=True, now=None)
-> (new_state, document_id, provenance_message). title <=100 chars, max20 documents, count3..10.
Normalised text hash deduplicates repeated uploads. No duplicate pack or progress loss.
Document fields: id, title, filename, text, chunks, summary, topics, questions, mode, created_at.
Question: id, prompt, topic, options[4 distinct strings], correct_index[0..3], difficulty,
hints[2], explanation, source_chunk_id, evidence_quote. Difficulty easy/medium/hard.
validate_pack verifies types, bounds, references and verbatim source quotes. It is not semantic proof.
build_pack falls back to local_pack after provider, schema or source-grounding failure.
Local mode creates missing-word questions from source statements; it is labelled extractive practice.

## Gemini boundary (ai_provider.py)
settings reads GEMINI_API_KEY or existing API_KEY from process environment / ignored .env.
Optional GEMINI_MODEL; default gemini-flash-lite-latest, verified by an actual generation call.
Secrets are repr-hidden, never stored in study state, never sent in query strings or user-visible errors.
_request uses fixed https://generativelanguage.googleapis.com/v1beta/ and x-goog-api-key header.
Generation posts models/{model}:generateContent with JSON response schema, timeout35s.
At most18 source excerpts /24,000 characters are sent; raw files are not uploaded to provider storage.
Generated content: summary, topics, questions, cards. Each item cites a provided chunk and verbatim quote.
ProviderError messages are sanitised. Missing key, quota, unavailable model, timeout, bad JSON or invalid
content uses local mode. No AI response can execute code or change scoring/scheduling logic.
User opts for AI via the sidebar toggle; building a pack then sends excerpts to Google.

## Quiz and feedback
start_quiz(state, document_id, count=5, adaptive=True, now=None) -> (state, quiz_id).
An existing unfinished quiz resumes. Unseen items come first, then weaker topic first-response rates.
Quiz: id, document_id, question_ids, completed, created_at. Max10 items; no foreign questions.
answer_question(state, quiz_id, question_id, selected_index, hint_count, token, now=None) -> state.
Answers follow quiz order; one per question/run. Duplicate token is a no-op; stale input is rejected.
Attempt: id, quiz_id, question_id, selected_index, correct, hint_count, answered_at.
Question keys determine grading; hints are generated once with the pack, not on each rerun.
Correctness, explanation and cited quote appear after answering. At most two hints are recorded.
topic_stats(state, optional document_id) uses only the first response per unique question.
Assistance is reported separately; repeated questions are labelled practice.
recommendations(state, now) returns due reviews, weak-topic practice and unfinished/new quiz actions.

## Flash Cards and persistence
Card: id, front, back, topic, source_chunk_id, evidence_quote, document_id, due_at, step, review_count.
grade_card(state, card_id, rating, token, now=None) -> state. Only due cards are writable.
Again -> +10min/reset; Hard -> +1 day; Good ->1/3/7/14 days; Easy skips a step, max14 days.
Review: id, card_id, rating, reviewed_at. Duplicate review tokens do not reschedule twice.
All dates are timezone-aware ISO8601. The clock is injected in core tests.
Historical schema_version=5 (migrated to v6 on load): documents, quizzes, attempts, cards, reviews, nlm, debugger, practice_events; no credentials or lab state.
export_state -> JSON including extracted notes. import_state validates all references and grading,
closed field sets, unique IDs, timestamps and review counts; max8 MiB.
load_state/save_state use ignored .local/study.json, validating before atomic replacement.
No login or multiuser isolation: one local student workspace. Tests disable persistence or use temp paths.
DomainError(code, message) reports invalid_input/content/progress/transition; UI preserves current data.

## Main UI boundary
app.py dispatches study_app.py by default. workspace_view='Lab' opens lab_app.py with a back button.
Main navigation: Dashboard, Library, Quiz, Flash Cards, Insights. Dashboard is the default. NLM lives in Library; debugger repairs are subordinate to Quiz. Lab maintains its separate session/export.
A study backup does not include the lab's evidence, and the UI labels the exports separately.

## Authored Newton pack and schema migration

`nlm.load_pack()` reads/validates `data/nlm-v1.json` (pack ID nlm-jee-2026, version1, syllabus2026).
Content includes concepts, prerequisites, misconception candidates, MCQs, recall cards, visual templates,
source provenance and closed-schema question scenes. Broken IDs, cyclic dependencies, bad keys,
unsupported visual families, malformed graph points and broken follow-ups are rejected.
`scripts/build_nlm.py` reproducibly builds authored JSON and never reads or writes learner progress.
Built-in packs never call Gemini. They are labelled authored; the uploaded-material provider/fallback
contract above remains unchanged. Full banks and learner history are not sent to any model.

`study.migrate_state(data)` adds `nlm.empty_progress()` to schema-v2 data and increments schema_version.
It then adds an empty debugger namespace to v3 and increments to v4; v3/v4 browser sessions migrate too. Schema v4 then migrates to v5 with an empty practice_events list.
`import_state` validates the migrated result before replacement; existing browser v2 sessions migrate too.
The v3 nlm namespace is `{pack_version:1, installed:bool, sessions:[], reviews:[]}`.
`nlm.install(state)` validates the pack and sets installed idempotently without reseeding progress.

`nlm.start(state, primary_question_id, learner='My learning', now=None) -> (state, session_id)`.
An unfinished matching question/learner resumes. Session fields: id, learner, question_id, created_at,
events. Event fields: id, action, answer, at, revision. Revisions are monotonically increasing from0.
`nlm.event(state, sid, action, answer=None, token, revision, now=None) -> state`.
Duplicate tokens are no-ops; stale revisions and invalid transitions fail without mutating input.
Actions: answer, hint, probe, solution, continue, transfer, delayed. Answers are MCQ indices0..3;
probe values concept/calculation/uncertain are learner self-report, not a validated diagnosis.

`nlm.view(session)` replays events deterministically. States: UNANSWERED, HINT_1, HINT_2,
FIRST_RESPONSE (correct primary response), SOLUTION, FOLLOW_UP, REMEDIATION, RECAP, COMPLETE,
TRANSFER, DELAYED_REVIEW. First response and each retry are retained as separate response records;
retry submission moves directly from the displayed hint into the next grade, without an extra click.
One wrong response automatically gives hint1; second wrong gives hint2; third wrong reveals solution.
An explicit solution request requires at least one hint. Correct primary response or solution routes
to its separately authored follow-up. Correct follow-up schedules review at+1day; transfer is separate.
Failed fresh checks show prerequisite remediation; after two failures, recap and scheduled retry.
Delayed review is writable only when due, uses an unused related question and is independently graded.

`nlm.validate_progress` replays all events on import, and recomputes recall schedules and references.
`nlm.insights(progress, learner=None)` separates first correctness, pre-answer help, hints, retries,
solution reveal, follow-up, transfer, delayed review and uncertain candidates. Repeat primary items
are flagged practice, not new first-response evidence. No mastery or learning-gain metric is inferred.
`nlm.review_card` records open-recall self-ratings with the existing Again/Hard/Good/Easy intervals;
reveals are session UI only and never increment statistics. Future cards cannot be rated early.
`nlm.reset_demo` accepts only Demo Learner A/B and removes that namespace’s sessions/reviews;
normal learning and uploaded records cannot be reset through this operation.

Visuals are code templates with finite bounded inputs. Question scenes expose only provided graph
points or geometry, not computed answers. Lesson reveal requires prediction and changing parameters
invalidates it. No model HTML/code is executed. Backups reference the installed pack version and
need the matching bundled content; authored pack content itself is not duplicated into each export.

## History-aware debugger v1 / schema v4

debugger namespace: {content_version:1, history:{learner:bool}, episodes:[]}.
Learners are My learning, Demo Learner A/B; these are local namespaces, not accounts.
Episode: {id,learner,topic,origin,created_at,events}; topics motion/mass/upload. origin is null for reviewed
topics, or {document_id,question_id} for an uploaded source review. Imported source references are checked.
Event: {id,action,value,at,revision}. All dates require offsets; IDs are unique; events replay monotonically.
Content/version mismatch is rejected. Limits: 200 episodes, 200 events/episode, existing total 8 MiB boundary.

debugger.start(state,topic,learner='My learning',now=None,origin=None) -> (new_state,episode_id).
An unfinished matching episode resumes; a reviewed new episode records its starting item presentation.
debugger.event(state,sid,action,value,token,revision,now) -> new_state; duplicate tokens are no-ops, stale
revisions reject. Public actions: next, answer, help, repair, alternate, review, disagree, feedback,
source_complete. answer value={option:int,confidence:sure/unsure/guessing/not given}.
review value=transfer/delayed/retry; delayed requires its actual due date. Alternate accepts a reviewed
topic-appropriate hypothesis or unclear; automatic repair accepts no caller-supplied diagnosis.
The event boundary creates present/repair decisions containing reason_code, evidence_ids and policy/content
versions. Referenced evidence must exist, belong to the learner, and not be dated after the decision.
debugger.view(episode) replays grades, phase, probe budget, assistance, repair and independent outcomes.
Two probes maximum per episode; solution help marks that answer assisted; independent assistance reopens
the repair. Immediate follow-up, transfer and delayed grades remain separate. Delayed success uses +3 then
+7 days after the first +1-day check; failure uses +1 day. Future questions are not presented early.
Previously presented probe/follow-up/transfer/delayed families cannot be reused across that learner's
debugger episodes. Exhaustion never becomes a pass. Primary/teach items can repeat as practice.

learning_events.normalize_evidence reads study, Newton and debugger records without mutating originals.
Old exposure/confidence are unknown; old calculation tags are not diagnostic. Concept mappings are explicit.
learner_model.build_learner_summary(state,learner,now,episode_id) rebuilds evidence and support counts.
With history disabled only the current episode informs support; exposure filtering still spans saved episodes.
Eligible cause evidence: first unassisted family responses, primary/probe, last 30 days / 10 relevant outcomes.
Supported candidate requires two supporting families including a probe; opposing evidence yields mixed.
Old evidence with no recent observation means needs_recheck. No probability or permanent learner label.
Support outcomes count first unassisted checks after interventions; they do not prove causal effectiveness.

debugger.set_history returns updated per-learner preference. debugger.delete_history removes only that
learner's debugger episodes and disables earlier-history use; original study/Newton records are untouched.
There is no persisted derived profile to become stale. Scoped deletion also removes debugger exposures.
source_retrieval.retrieve_repair_sources(state,document_id,query,limit=3) returns keyword-ranked source
chunks with real document/chunk/page references. No cross-document concept identity is inferred.
Uploaded source reviews do not run reviewed diagnosis or award independent-check status.
No debugger history is transmitted to Gemini; no new external dependency or model training is introduced.

## Phoenix material facade and reports (changes_3)
workspace.materials(state) returns stable references, authored/uploaded kind, version and active/history visibility.
Authored identity authored:nlm-jee-2026 references the original pack and progress, without a fabricated upload.
The inspected Cell Energy document is historical only when BOTH its original ID and created_at match the
explicit HISTORICAL_DOCUMENTS mapping. This is reversible presentation metadata; records are not rewritten.
New uploads, including new biology uploads, remain active. Historical material is selectable via Show historical materials.
One selected-material widget scopes Library/Quiz/Flash Cards/Insights and live Dashboard. URL page/material/lesson/
repair context restores validated selections after refresh; unknown values fall back safely. Old Revision,
Newton’s Laws and Debugger navigation values resolve to the five destinations without deleting saved work.
workspace.report is read-only, rebuilding normalized original evidence; sample_overview is isolated presentation data.
First accuracy uses first nonrepeat starting/practice responses, excluding subsequent checks and retries.
Topic weakness requires >=3 first responses and accuracy <70%; otherwise evidence is insufficient.
Date/topic filters scope outcome counts; current card schedules and pending work remain material-wide.
Quiz reports retain whole-round denominators. Additional authored/debugger detail is explicitly all-time.
Cross-subject records retain document namespaces and never become Newton concept diagnoses.

## Persisted upload support / schema v5
practice_events adds {id,quiz_id,question_id,action,value,at,revision}. Actions: retry, solution, finish.
practice_view replays a wrong first response into hint1; first failed retry gives hint2; second retry exposes
worked explanation. Explicit solution is available after hint1. Correct retries remain assisted recovery.
practice_event enforces sequential revisions, duplicate tokens, bounded retries and monotonic timestamps.
Original attempts and quiz grading remain unchanged. Pending support resumes before advancing on reload.
Imports replay support and reject malformed events before replacement; schema v2/v3/v4 collections are preserved.
Uploaded packs do not yet generate independent equivalent variants: UI states the limitation and labels next
items ordinary practice. Source review keeps reviewed diagnostic coverage distinct. No request on rerun.
NLM transitions to checks reject a target already presented/answered in another session for the same learner;
finite bank exhaustion stays explicit. Existing saved sessions replay unchanged and repeated evidence stays excluded.
Flash Cards preserves IDs and intervals; authored due/new/preview modes prevent early rescheduling.
Reviewed diagrams and source links appear on recall reveal. Generated cards retain provenance and quotations.
assets/phoenix-logo.jpeg is the supplied original; runtime has no dependency on Downloads.
Start-Phoenix-Study.cmd, study_* identifiers and phoenix-study-backup.json remain compatibility aliases.

## Topic journey and uploaded lesson context
journey.UNITS defines four ordered NLM units covering all 12 concepts exactly once.
journey.journey(state, learner) derives per-concept stages, resumable/unseen primary IDs and
linked notes from existing progress; it never writes state or invents completion evidence.
journey.note_sections(state, concept_id) returns up to four phrase-matched uploaded sections
with document/chunk/page identity. This is labelled reading context, not a diagnosis or
semantic validation. Uploaded notes retain their own generated quiz/card packs and evidence.
Dashboard/Library topic actions install idempotently and start/resume the selected concept.
Lesson controls are scoped to the reviewed visual family; unrelated visual selection is removed.
No schema migration or new provider request is introduced; stored uploads/progress are preserved.
