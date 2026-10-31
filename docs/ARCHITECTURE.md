# Architecture

Phoenix is a single-process Streamlit application with separate presentation, domain, provider, and persistence modules. The uploaded-material workflow is the primary product surface.

## Module responsibilities

| Modules in src/phoenix | Responsibility |
| --- | --- |
| study_app, nlm_app, debugger_app, lab_app | Streamlit pages and user actions |
| study, study_flow, content_quality, followups | Source ingestion, pack lifecycle, practice, recall, quality checks |
| workspace, learning_events, journey, navigation | Material selection, derived reports, progress, validated routes |
| ai_provider | Server-side Gemini requests and structured response boundary |
| storage, schema_v6 | State validation, migrations, revision checks, locks, atomic checkpoints, restore |
| nlm, nlm_visuals, experiments, debugger* | Bounded authored sample lessons and targeted support |
| engine, workflow, ledger | Supporting algebra workspace |
| demo | Fresh validated User 1 state for each demo session |

## Data flow

1. Extract text from PDF/TXT/Markdown or pasted notes and preview the selected sections.
2. Generate and validate a source-grounded pack, or provide the labelled extractive fallback.
3. Record first answers separately from hints, retries, and subsequent checks.
4. Derive reports from saved evidence and card schedules.
5. In local mode, commit validated state with identity/revision checks. In demo mode, update only the session state.

No browser-supplied code is evaluated. Provider requests happen before storage locks. Secrets are excluded from study exports.

## Runtime modes

`PHOENIX_MODE=demo` loads the committed fictional fixture into each independent Streamlit session. No personal checkpoint is opened, restored, or modified by the demo UI. Backup restore controls are available only in persistent mode. A new session starts from the fixture.

`PHOENIX_MODE=local` uses `.local/study.json`, or `PHOENIX_DATA_DIR/study.json`. Schema versions 2–5 migrate to v6. Atomic writes retain recovery checkpoints. Multiple tabs use revision checks, but this remains one shared owner's workspace, not a multi-tenant storage system.

Internal learner identifiers such as `My learning` remain stable to preserve legacy records and routes. User 1 is the display identity of the fictional demo, not an authentication principal.

The authored sample pack is loaded from `samples/users/user-1/nlm-v1.json`. Existing algebra exercise definitions remain under `data/`. Historical owner data is never copied into the sample fixture.

See [the state contract](engineering/API_CONTRACT.md) for operation signatures and validation invariants.

## Physics student/teacher showcase

Default demo mode dispatches to `showcase_app.py`. `showcase.py` loads and validates the version-2
fixture, derives shared student/teacher selectors and records new first answers without rewriting
original correctness on supported retry. `physics_practice.py` owns the five-to-fifteen-item queue.
`showcase_app.py` renders Dashboard, Library, Quiz, Flash Cards, Insights and Teacher Dashboard.

The dataset under `samples/users/user-1/physics/` contains eight readable note files, 88 computed
questions and six explicitly synthetic student histories. The build script has no network access
and never loads personal checkpoints. Error-label mappings correspond to the distractor formula;
teacher reports still describe them as potential explanations, not certain diagnoses.

The showcase is held in independent Streamlit session state under `physics_data`, `physics_round`,
and `physics_cards`. Teacher/student navigation reads the same cohort object. No fixture is written
back on interaction. `workspace_view=Uploads` opens the existing study application with an empty
session-only study state; its original domain schema stays unchanged. Local mode still runs the
original persistent app. The teacher roster is demonstration functionality, not tenant isolation.

Current extension: three attempts per quiz question, with non-revealing concept/approach support
before the last attempt; a maximum of 15 questions; 24 concept/relation/pitfall flip cards with
mnemonics; class-wide teacher heatmaps, confusion patterns and ranked intervention plans before
the roster. Individual reports also include scoped plans. The authored bank has 11 variants per
chapter. Plans use transparent error/affected-student/recency weights and prefer unseen exit checks.
