# Verification evidence — 30 October 2026

Environment: Windows, Python 3.14.6, Streamlit 1.66.1. Local address: http://127.0.0.1:8501.

## Executed checks

| Check | Result | Observed evidence |
|---|---|---|
| `python scripts/verify.py --planning` | PASS | Required planning files exist and line limits pass |
| `.\.venv\Scripts\python.exe -m pip check` | PASS | No broken requirements found |
| `.\.venv\Scripts\python.exe -X utf8 scripts/verify.py` | PASS | Modules compile; 29 tests pass |
| `.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8501` | PASS | Server started on 127.0.0.1:8501 |
| `Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8501/_stcore/health` | PASS | HTTP 200, response `ok` |

The first PowerShell health attempt without `-UseBasicParsing` failed inside Windows PowerShell's
HTML parser (`Object reference not set to an instance of an object`). The corrected command above succeeds.
Streamlit AppTest reports the documented bare-mode `missing ScriptRunContext` warning; no app exceptions occurred.

## Connected demo journey

These observations come from Streamlit's actual application script and rendered-widget AppTest API,
not a custom mocked UI. Test: `test_complete_actual_ui_all_families`.

| PROJECT action | Result | Observation |
|---|---|---|
| Select faulty answer and reason | PASS | Distribution advances through locked prediction to rule test |
| Run x=1 counterexample | PASS | Distribution 9 vs 5; square 9 vs 5; negative bracket -3 vs 1 |
| Change numerical input | PASS | Slider x=2 changes displayed metric values through evaluators |
| Submit repaired rule and explanation | PASS | REPAIR_VERIFIED and three numerical regression checks |
| Two unseen transfer checks | PASS | First correctness withheld; both correct unassisted -> transfer_passed |
| Open ledger and schedule review | PASS | Navigation reaches ledger; next check = submission time + 1 day |
| Export and restore | PASS (domain boundary) | Exact JSON round-trip for all three families; malformed data rejected |
| Reset demo | PASS (rendered UI) | Clears evidence, returns to PREDICT |
| Browser download/upload dialog | UNVERIFIED | Native browser walkthrough unavailable; import/export functions tested |

## Additional tests

- Correct-answer path, conflicting answer/reason, unclear evidence, guided example and corroborating probe.
- Duplicate submit no-op, stale token rejection, atomic validation and preservation of partial state on navigation.
- Correct repair requires both rule and explanation; hint cap and help-use recording.
- Symbolic failure, representation failure, assisted transfer, and already-seen transfer treated as practice.
- Due review: answer plus reason required; +3 then +7 day schedule using injected clocks.
- Failed or assisted delayed review reopens while preserving history; recommendation prioritizes it.
- Future preview does not mutate evidence and does not reveal the actual delayed question.
- Import rejects bad versions, unknown IDs, duplicate attempts, invalid times/types, inconsistent links,
  fabricated numerical counterexamples, absent schedules and oversized files.
- A full rendered UI journey succeeds while `socket.create_connection` is forced to fail.

## Limits

Desktop Computer Use stopped because it could not reliably establish the current browser URL.
No manual browser visual pass, screenshot, recording, or real browser file-dialog test is claimed.
AppTest covers rendered UI logic; it does not establish visual layout or browser-download behavior.
Optional live model paraphrasing is omitted without provider credentials. No live API smoke test is claimed.
No public deployment was required or performed. No separate frontend build exists for this Streamlit app.
Numerical regression and engineering reliability are tested; instructor validation and learning outcomes are not.

Git checkpoint: initial implementation da8abbd was pushed successfully to origin/main.
Staged whitespace check passed; credential-pattern scan found no matches.
Final regression includes ledger transfer-answer display and hiding pending grades across navigation.
