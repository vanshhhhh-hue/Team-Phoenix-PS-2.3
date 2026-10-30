# Handoff
## Done
Phoenix Study implemented: uploads/pasted notes, Gemini/local packs, adaptive quiz/hints, heatmap/path, spaced cards.
Root default is Study Companion; tested algebra lab is supporting. Historical lab docs preserved under docs/LAB_*.
42 tests pass. Actual browser generation, answer/hint, insights, review, download/restore and refresh verified.
## Current task
Refined implementation complete; final Git checkpoint and source archive recorded in the chat.
## Files/functions being changed
None pending. app.py dispatch; study_app.py main UI; study.py domain/save; ai_provider.py Gemini.
## Broken/failing with exact error
No current app/test failures. Retired model returned unavailable; gemini-flash-lite-latest works.
An in-app browser targeting error was recovered; current browser walkthrough passes.
## Decisions
Original upload-based Study Companion controls scope, not the narrower algebra brief.
User confirmed Gemini and authorised .env API_KEY use. Never expose or commit it.
Actual Gemini generation produced 6 questions/6 cards/3 topics with source quotes.
Local fallback is labelled extractive practice. Local study checkpoint is ignored .local/study.json.
## Commands to run
`.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8501` or Start-Phoenix-Study.cmd.
Open http://127.0.0.1:8501 (running at handoff). `scripts/verify.py` runs all42 tests without live API calls.
## Checks actually performed
42 tests pass; pip check passes; HTTP200/ok. Actual Gemini and browser evidence in VERIFICATION.md.
Backup download/restore and refresh retain sample data; malformed state is rejected atomically.
## Next exact step
Use Library to upload the owner's actual course notes and take a quiz. No additional start permission needed.
Current saved demo is authored Cell Energy material plus one deliberate QA answer/review.
Teacher dashboard, OCR and public deployment remain outside current implemented scope.
