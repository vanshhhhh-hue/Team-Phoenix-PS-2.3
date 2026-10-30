# Verification - Phoenix Study refinement, 30 October 2026

Environment: Windows, Python3.14.6, Streamlit1.66.1, pypdf6.21.4.
The earlier algebra-only checkpoint is archived at docs/LAB_VERIFICATION.md.

## Automated checks actually executed

| Check | Result | Evidence |
|---|---|---|
| scripts/verify.py | PASS | All application modules compile; 42 tests pass |
| pip check | PASS | No broken requirements found |
| Planning check | PASS | Required files exist and line limits pass |
| Streamlit startup | PASS | Server starts on 127.0.0.1:8501 with new 10 MB upload limit |
| HTTP health | PASS | 200 and ok using Invoke-WebRequest -UseBasicParsing |

New tests exercise real PDF extraction, bad/encrypted/empty inputs, source citations, duplicate uploads,
AI provider/content failure fallback, deterministic grading, atomic submissions, unseen-first selection,
first-response-only analytics, revision scheduling, early-review rejection and atomic backup validation.
A rendered Streamlit journey covers pasted notes -> library -> five-item quiz -> hint/explanations
-> topic insights -> card reveal -> rating. Root app navigation enters/exits the supporting lab.
All 29 original algebra tests remain passing. Unit tests do not spend live API quota.
Expected warnings: Streamlit bare-mode ScriptRunContext warnings and pypdf's malformed-fixture warning.

## Live Gemini checks actually executed

The owner supplied the ignored .env key and confirmed Google Gemini / AI Studio.
Models endpoint authentication succeeded. gemini-2.5-flash-lite generation returned unavailable;
gemini-flash-lite-latest then succeeded and is the configured default.
A structured generation from the authored biology sample produced six questions, six cards and three
topics: Photosynthesis, Cellular Respiration, Transport Across Membranes. Verbatim evidence checks passed.
Only sanitised connection status/counts were printed. No key or raw provider error body was displayed.
Source quoting and JSON validation do not establish semantic answer correctness.

## Actual in-app browser observations

| Action | Result | Observed behavior |
|---|---|---|
| Open main app | PASS | Phoenix Study dashboard with five main destinations; lab is supporting |
| Build sample using Gemini | PASS | Library displays Gemini generated, six questions, three source sections |
| Request quiz hint | PASS | Leading hint appears without revealing grading |
| Submit an incorrect answer | PASS | Reviewed answer and verbatim source explanation shown; one hint recorded |
| Open Insights | PASS | Photosynthesis 0/1 first responses correct, one assisted; other topics unseen |
| Recall/reveal/rate flashcard | PASS | Good removes it from due queue: six due becomes five |
| Download backup | PASS | Browser downloaded phoenix-study-backup.json, approximately14 KB |
| Upload downloaded backup and restore | PASS | Dashboard retains one document, one response and five due cards |
| Refresh browser | PASS | Same saved counts recovered from local persistence |
| Actual material upload | PASS | File chooser accepted demo-notes.md; processing detected duplicate and preserved progress |
| Dashboard layout | PASS with adjustment | Narrow preview prompted two-column metrics and topic tiles |

Browser control is now working through the in-app browser; the previous desktop URL-identification issue
belongs to the historical lab checkpoint. A targeting error during upload QA was recovered by re-reading
the page and using the current semantic control; the successful duplicate-upload outcome was observed.
Preview saved at C:/Users/VICTUS/Desktop/MNIT/Phoenix-Study-preview.png (outside the source repository).
Local demo data is the authored biology sample and one deliberate QA response/review, not real learner results.

## Limits

No public deployment, OCR, account isolation, teacher/class dashboard or embeddings service is claimed.
Syllabus-only headings cannot support missing teaching explanations; source-based study needs explanatory material.
Local fallback provides extractive recall, not a local LLM. No learning-efficacy or diagnostic-validity claim.
Adaptive selection and spacing are transparent prototype heuristics. The main workspace persists locally;
the supporting legacy lab still uses its original separate export/session boundary.
