# Phoenix Study - AI Study Companion

A web app that turns **your uploaded material** into quizzes, guided practice, spaced-revision cards
and a view of weak topics. The algebra Misconception Lab is a supporting workspace, not the main product.
This corrects the earlier lab-only interpretation of the hackathon problem.

## What you can do

- Dashboard: see your material, due cards and recommended next steps.
- Library: upload a text-based PDF, TXT or Markdown file, or paste lecture notes.
- Gemini study packs: get a summary, topics, MCQs, two hints per question, explanations and flashcards.
- Quiz: unseen questions first, weak topics prioritized, deterministic grading and quoted source evidence.
- Insights: inspect a weak-topic heatmap and learning path based on first responses; repeats do not inflate it.
- Revision: reveal cards after recall, rate them, and review again on scheduled dates.
- Local save: notes, answers and schedules persist across refresh; export/import a complete study backup.
- Supporting lab: explore the tested authored algebra experiments, then return to the main study app.

## Run on this PC

Open PowerShell in this repository:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8501
```

Open [Phoenix Study](http://127.0.0.1:8501). You can also double-click `Start-Phoenix-Study.cmd`.
`Start-Lab.cmd` is retained as a compatible launcher; it also opens the new main app.
Keep the terminal running. Ctrl+C stops the server; use the already-running instance if port8501 is busy.

## Fresh setup

Tested with Python3.14.6, Streamlit1.66.1 and pypdf6.21.4 on Windows.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8501
```

For another supported Python version, use `requirements.txt` if the full transitive lock is incompatible,
then rerun verification. No Node.js, Docker, GPU or database service is required.

## Gemini and local fallback

The existing ignored `.env` file is read server-side. Its generic `API_KEY` is supported; the preferred
name is `GEMINI_API_KEY`. Optional `GEMINI_MODEL` defaults to `gemini-flash-lite-latest`.
See `.env.example` for names only. Never commit or share your real `.env`.

The user confirmed Google Gemini and authorised using the supplied key. An actual live smoke test
produced six questions, six cards and three topics from the included biology notes. The earlier
model name gemini-2.5-flash-lite was unavailable; the current Flash Lite alias worked.

With **Use Gemini when available** enabled, building a pack sends selected text excerpts to Google's
Gemini endpoint. It does not upload the raw file to provider storage. Keys stay server-side and do not
appear in backups, logs or UI. Disable the toggle to keep generation entirely local.
Missing credentials, quota, unavailable model, timeout, malformed output or bad source references cause
an automatic, labelled fallback. **Local fallback is extractive missing-word recall practice, not a local
LLM and not equivalent to AI-generated application questions.**

A source quote must be present in the uploaded text. This checks provenance, not that every generated
answer, distractor or explanation is semantically correct. Review the source; AI can make mistakes.

## Demo the full product

1. Open Dashboard, then Library. Upload your own notes or paste explanatory course material.
   Alternatively use **Build a pack from sample notes** on an empty dashboard.
2. Inspect the resulting material title, source excerpts, topics, summary and generation label.
3. Open Quiz and start an adaptive round. Try a wrong answer and a hint; inspect the explanation/source.
4. Finish the round, then open Insights to see topic-specific first-response results and recommendations.
5. Open Revision, recall a card, reveal its answer and choose Good. Its next review is scheduled.
6. Refresh: study data remains saved locally. Export the study backup and verify it can be restored.
7. Optionally open Misconception Lab from the sidebar; use **Back to Phoenix Study** to return.

## Data and limits

Upload maximum:10 MB. PDFs:60 pages maximum, text-based and unencrypted. Extracted text:80-100,000
characters. Up to20 documents; workspace/backup maximum8 MB. No OCR for scanned PDFs.
A bare syllabus cannot provide teaching explanations it does not contain; add fuller notes for grounded quizzes.

Study data saves atomically to `.local/study.json`, ignored by Git. Backups include extracted notes and
progress, so treat them as your own private study files. Corrupt or inconsistent backups are rejected
before replacing existing data. No account or multiuser isolation is provided on this one-PC demo.

Cards use transparent intervals: Again10 minutes; Hard1 day; Good1/3/7/14 days; Easy skips a step.
Future card previews cannot be submitted early. Self-ratings, first-response accuracy and small quiz
samples are limited evidence, not proof of mastery or measured learning improvement.
The legacy algebra lab keeps its original separate session/export system; study backups do not include it.

## Verify

```powershell
.\.venv\Scripts\python.exe scripts/verify.py
.\.venv\Scripts\python.exe -m pip check
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8501/_stcore/health
```

The first command compiles modules and runs study plus legacy lab tests without a running server or
live API calls. Health requires the running app and should return200/ok. See `VERIFICATION.md`.
Browser file-dialog and visual checks are separately reported; AppTest checks rendered UI logic.

## Scope decisions

Teacher/class dashboards, OCR, login, embedding infrastructure and public deployment are not included.
The core student flow uses uploaded content across subjects, not a fixed algebra-only question bank.
Historic lab-only documents are preserved under `docs/LAB_*`; current instructions are at repository root.
