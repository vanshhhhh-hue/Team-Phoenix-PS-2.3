# Misconception Lab
Repository: https://github.com/vanshhhhh-hue/Team-Phoenix-PS-2.3.git
One owner and active agent, one PC, one checkout. No integration repository or stage.

## Problem and solution
Students can repeat a faulty algebra rule despite seeing a correct answer.
Let a student select a rule, expose its failure numerically, repair it, and try new problems.
Target: students practising elementary algebra; a single-student local hackathon demo.
Pitch: Find the rule behind your mistake. Test it. Repair it. Check it on a new problem.

## Two-minute demo
1. Debug Lab: choose 3x+2 for 3(x+2), then “multiply only the first term”; record a candidate.
2. Predict agreement and run the bench. Search may pick x=0; manually choose x=1 to show 9 versus 5.
3. Change x and observe computed results; select the correct rule and structured explanation.
4. Verify repair at three values; open Transfer Challenge and answer new symbolic and area items.
5. Repair Ledger shows original rule, counterexample, repair, assistance, transfer and next-day review.
6. Export progress, reset demo, import it and recover the same evidence and schedule.

## Scope
- MUST: Debug Lab, Transfer Challenge, Repair Ledger; no-key mode labelled Built-in rule engine.
- MUST: distribution first, then square-of-sum and negative-bracket packs through the same UI.
- MUST: ambiguous-evidence probe, Cause unclear, correct-answer route, two hints and worked explanation.
- MUST: two unassisted transfer checks; assisted work cannot pass the unassisted gate.
- MUST: deduplicated attempts, explicit transitions, review scheduling, validated JSON export/import, reset.
- SHOULD: concise presentation and an explicitly labelled future-review preview.
- CUT-FIRST: optional model paraphrase, visual polish, then additional families if schedule forces a partial MVP.
- EXCLUDE: arbitrary notes/PDF ingestion, chatbot, accounts, database, analytics, free-text equation parsing.

## Stack and planned structure
Python 3.14.6 + Streamlit 1.66.1: one process for UI/domain functions, no bespoke HTTP API.
Built-in json/datetime/unittest: no paid service or GPU; explicit progress export is persistence.
Root: app.py, engine.py, workflow.py, ledger.py; data/packs.json; tests/test_core.py.
Optional llm_adapter.py only after offline completion and usable credentials.
Docs at root; prompts/FULLSTACK_AGENT.md; scripts/verify.py.
Implementation present: all four Python modules, 3 packs, 24 questions, 6 hints, core/UI tests, README.

## Local commands (PowerShell, from repository root)
Tools: Git, Python 3.14.6 (already installed and tested), browser.
Create environment if needed: `python -m venv .venv`
Install: `.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt`
Start: `.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8501`
Open http://localhost:8501; UI and domain logic run in the same Streamlit process.
Verify: `.\.venv\Scripts\python.exe scripts/verify.py` (no running server required).
Health while running: `Invoke-WebRequest http://localhost:8501/_stcore/health`
No separate frontend build. Verification includes compile, core tests and recorded browser walkthrough.
Required environment variables: none. Optional provider variables are deferred until a provider is chosen.

## Decisions and assumptions
[planning] Use the later algebra build brief over the earlier probability research prototype.
[planning] Seven implementation hours, feature freeze at six; supersedes generic ten-hour template.
[planning] Local demo sufficient unless official requirements establish deployment or live AI obligations.
[planning] No account or automatic durable storage; session state plus explicit JSON export/import.
[planning] Evidence labels describe this check only; no mastery, proven retention or novelty claims.
[planning] Official judging weights, compulsory uploads/live AI and submission rules remain unverified.
[planning] Numerical first counterexample follows [0,1,-1,2,-2,3,-3], not a forced x=1.
[implementation] Streamlit 1.66.1 installed and tested on Python 3.14.6; dependencies locked after pip check.
[implementation] Optional AI omitted without credentials; no-key functionality is complete.
[implementation] Browser safety automation could not establish URL; AppTest UI journeys and health are verified.
