# Refined product tasks
Owner: project owner and active coding agent. The lab-only checklist is archived in docs/LAB_TASKS.md.
User authorised continuous execution of this refined study-product scope.

| ID | Area | Priority | Depends on | Exact scope | Done when | Check | Status |
|---|---|---|---|---|---|---|---|
| R01 | Setup | P0 | - | Restore original product scope and preserve algebra checkpoint | Main product is Study Companion, lab is supporting | PROJECT.md and FULLSTACK_AGENT.md agree | DONE |
| R02 | Backend | P0 | R01 | PDF/TXT/MD/pasted-text ingestion and source chunks | Limits enforced, real PDF text extracted | test_pdf_text_extraction_and_scan_error; bad upload tests | DONE |
| R03 | Backend | P0 | R02 | Gemini structured study packs and source references | Real generation succeeds and quotes match source | Actual API smoke: 6 questions/6 cards/3 topics; grounding tests | DONE |
| R04 | Backend | P0 | R03 | Labelled local fallback and duplicate-material handling | No key/quota/bad output preserves useful source-based practice | Provider-failure, malformed-evidence and dedup tests | DONE |
| R05 | UI | P0 | R04 | Main dashboard and material library | User can paste/upload notes and inspect pack/source | Streamlit upload-to-library test via pasted notes | DONE |
| R06 | Full-stack | P0 | R05 | Adaptive quiz, hint ladder, explanations and citations | Real uploaded questions grade once and record assistance | End-to-end quiz/hints test; duplicate/atomic grading tests | DONE |
| R07 | Full-stack | P0 | R06 | Topic heatmap, learning path and unseen-first selection | Repeat questions cannot inflate first-response rates | Adaptive and analytics tests; rendered Insights | DONE |
| R08 | Full-stack | P0 | R07 | Flashcards, reveal, recall ratings and due dates | Future previews cannot be completed early | Injected-clock scheduling and actual revision UI test | DONE |
| R09 | Full-stack | P0 | R08 | Atomic local save, backup export/import and validation | Reload and round trip preserve state; rejected backup preserves old file | Persistence/import tests | DONE |
| R10 | Full-stack | P0 | R09 | Supporting algebra lab and return navigation | Existing lab works and main app remains default | 29 legacy tests plus root navigation test | DONE |
| R11 | Verification | P0 | R10 | Regression, dependency/health checks and credential exclusion | All checks pass with actual evidence | scripts/verify.py; pip check; HTTP health; Git checks | DONE |
| R12 | Verification | P0 | R11 | Refresh docs, archive source and push checkpoint | User receives runnable refined app and accurate limitations | README, HANDOFF, source archive, Git push | DONE |

Cut order: bonus teacher dashboard -> OCR -> external infrastructure -> cosmetic polish.
Do not cut uploaded-material study to preserve only the algebra demo.
