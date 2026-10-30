# Misconception Lab

**Find the rule behind your mistake. Test it. Repair it. Check it on a new problem.**

A local Streamlit application with exactly three connected features:

- **Debug Lab:** predict, explain your rule, inspect a calculated counterexample, and repair the rule.
- **Transfer Challenge:** a symbolic problem and a different representation, graded from authored keys.
- **Repair Ledger:** evidence timelines, assistance tracking, due reviews, and progress export/import.

Supports incomplete distribution, square of a sum, and negative brackets. All features work without
an API key, internet access after installation, accounts, a database, or a GPU.

## Run on this PC

Open PowerShell in `C:\Users\VICTUS\Desktop\MNIT\Team-Phoenix-PS-2.3`:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8501
```

Open [Misconception Lab](http://127.0.0.1:8501). Keep the terminal running; Ctrl+C stops the server.
The development server may already be running on port 8501. Use it rather than starting a duplicate.
You can also double-click `Start-Lab.cmd` after setup.

## Fresh setup

Tested on Windows with Python **3.14.6** and Streamlit **1.66.1**. Python 3.12 is not required on this PC.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8501
```

`requirements-lock.txt` records the tested environment. `requirements.txt` pins the direct dependency;
on another supported Python version, use it if a transitive lock is incompatible, then verify again.
No environment variables or `.env` loading are needed. Only official PyPI packages are installed.

## Verify

```powershell
.\.venv\Scripts\python.exe scripts/verify.py
.\.venv\Scripts\python.exe -m pip check
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8501/_stcore/health
```

The first command compiles application modules and runs core plus Streamlit AppTest tests without a
running server. Health requires a running server and should return HTTP 200 with `ok`.
Streamlit has no separate frontend production build. The app starts directly from `app.py`.

## Two-minute demo

1. Select **Distribute to every term** in Debug Lab. Choose `3x + 2`, lock the prediction,
   then select “Multiply only the first term inside the bracket.”
2. The deterministic search first chooses x=0. Enter x=1, predict agreement, and run:
   the original is **9** and the rewrite **5**. Move the input to see fresh calculations.
3. Choose the repaired rule `a(x+b) = ax+ab` and the explanation that every term is multiplied.
   The original and corrected rewrite agree at three regression inputs.
4. In Transfer Challenge choose `5t + 15`, then `4y + 12`, without requesting help.
5. Open the ledger: inspect the candidate rule, breaking example, repair, transfer results,
   and next-day review. A future preview is only a worked-example rehearsal, not a completed review.
6. Export progress, reset the demo, and import the downloaded JSON to restore the evidence.

## Progress and review rules

Session state survives Streamlit reruns and navigation, but can be lost on refresh or restart.
Export JSON explicitly before closing. Import validates the complete file before replacing progress;
invalid files preserve the current session. Maximum import size: **1 MiB**. Export contains no credentials.
Exports retain submitted attempts and ledger evidence; an unfinished question or unsubmitted form is not restored.
After import, a new lab can be started while earlier evidence remains in the ledger.

Reviews are due one day after unassisted transfer passes, then three days after the first successful
delayed check, then seven days after later successes. Failure or assistance reopens the issue.
Scheduling uses timezone-aware timestamps; dates display in IST. Tests inject time instead of changing
the PC clock. The small three-item delayed bank is reused after three successes.

Help during transfer prevents that attempt passing the unassisted gate. Repeating an already graded
transfer question is labelled practice and cannot masquerade as a fresh unseen check.
The original failure and help use stay in history after later success. One ledger record is kept per family.

## Evidence boundaries and exclusions

The app displays **Built-in rule engine** and **No live AI**. Optional model paraphrasing is omitted:
no provider or credentials were supplied, and the full offline product is complete without it.
There is no arbitrary PDF/notes ingestion, general chatbot, account system, custom REST backend, or deployment.
This narrows the broader uploaded-notes problem to an authored algebra module; do not pitch arbitrary-subject coverage.

An answer and reason support a candidate rule, not a certain diagnosis. Ambiguous evidence gets a probe
or “Cause unclear”; correct reasoning can go straight to transfer. Numerical agreements are regression
checks, not universal mathematical proofs. Transfer and delayed outcomes describe those checks only.
No claim of mastery, learning improvement, diagnostic validity, or academic novelty has been established.
The seed mathematics is authored and regression-checked; there has been no independent instructor review or learner study.

## Files

`app.py` renders the UI; `engine.py` evaluates templates and validates content; `workflow.py` owns
transitions and deduplication; `ledger.py` owns records, scheduling and progress validation.
`data/packs.json` contains 3 families, 24 questions, and 6 hints. Tests are in `tests/`.
Start future coding work from `HANDOFF.md` and `TASKS.md`. See `VERIFICATION.md` for actual check evidence.
