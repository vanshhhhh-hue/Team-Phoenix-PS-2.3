# Phoenix Study - AI Study Companion
Repository: https://github.com/vanshhhhh-hue/Team-Phoenix-PS-2.3.git
One owner, one PC, one checkout. This replaces the lab-only product scope.

## Original problem and product
Students receive the same lecture pace despite different gaps; generic chat gives answers too quickly.
Build personalised study from uploaded notes: quizzes, Socratic hints, flashcards and weak-topic feedback.
Users: school/college students. Coaching/teacher views are possible later; teacher dashboard is a bonus.
Original statement: parent prompts/research-to-build-prompt.md, section A.
The narrowed misconception-lab brief is a supporting-module specification, not the product boundary.

## Main screens and demo
1. Dashboard: see study material, due cards and recommended next actions.
2. Library: upload a text-based PDF/TXT/MD or paste notes; create a titled study pack.
3. Verify its summary, source excerpts, topics, questions and cards came from the uploaded material.
4. Quiz: answer new items, request up to two hints, then see grading, explanation and quoted source.
5. Insights: view topic correctness and assistance; repeat practice without inflating first-response analytics.
6. Revision: recall a flashcard, reveal it and rate recall to schedule the next review.
7. Reload: locally saved study material, answers and schedules remain; export/import a study backup.
8. Optional supporting module: open the authored algebra Misconception Lab, then return to the main app.

## Scope
- MUST: material upload/pasted notes, library and transparent extraction limits.
- MUST: Gemini-generated source-grounded MCQs, hints, explanations, topics and flashcards when API works.
- MUST: automatic labelled local extractive fallback when key/service/content validation fails.
- MUST: adaptive question selection, saved attempts, weak-topic heatmap and recommended learning path.
- MUST: due flashcards with explicit recall scheduling; persistent local study state and backup restore.
- MUST: retain tested algebra lab as a supporting workspace, not default home or only content source.
- SHOULD: concise, responsive dashboard and source-evidence inspection.
- BONUS / CUT-FIRST: teacher/class dashboard, OCR, accounts, embeddings infrastructure, public deployment.

## Implementation and commands
Python 3.14.6, Streamlit 1.66.1 and pypdf 6.21.4; one process, no separate REST backend.
app.py dispatches study_app.py (default) and lab_app.py (supporting lab).
study.py handles sources, adaptive quizzes, cards and atomic local persistence.
ai_provider.py sends selected excerpts only to Gemini via its official HTTPS endpoint.
Existing engine.py/workflow.py/ledger.py and data/packs.json continue powering the lab.
data/demo-notes.md is an original biology sample; tests/ covers study and lab flows.
Private runtime data: .local/study.json (ignored); credentials: .env (ignored).
Setup: `python -m venv .venv`; `.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt`.
Run: `.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8501`.
Open http://127.0.0.1:8501; use Start-Lab.cmd as the retained launcher filename.
Verify: `.\.venv\Scripts\python.exe scripts/verify.py`; `.\.venv\Scripts\python.exe -m pip check`.
Environment: GEMINI_API_KEY (or existing API_KEY); optional GEMINI_MODEL.
Live model tested: gemini-flash-lite-latest. No browser-side key or credentials in exports.

## Decisions and limits
[refinement] The owner's correction restores the original uploaded-material study product.
[refinement] User authorised Gemini using the existing .env and a local fallback if it fails.
[refinement] Live generation returned six grounded questions, six cards and three topics on biology notes.
[refinement] Local fallback is extractive recall practice, not a local LLM or equivalent-quality AI tutoring.
[refinement] PDF limit 10 MB / 60 pages; extracted text limit 100,000 characters; no OCR.
[refinement] A bare syllabus cannot support explanations it does not contain; add teaching notes for grounded quizzes.
[refinement] Adaptive selection and spacing are transparent heuristics, not validated cognitive models.
[refinement] Local study state persists across refresh; the legacy lab retains its separate export/session behavior.
[refinement] No public URL requirement has been established; preserve the local-only deployment decision.
