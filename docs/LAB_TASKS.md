> Historical lab-only checkpoint. Current product scope is in root PROJECT.md.

# Sequential tasks
Owner of every row: the project owner and currently active coding agent. One IN-PROGRESS maximum.
Times are elapsed implementation hours; planning pack is prepared before that clock starts.

| ID | Area | Priority | Depends on | Exact scope | Done when | Check | Status |
|---|---|---|---|---|---|---|---|
| T01 | Setup | P0 | — | Verify Python environment, install Streamlit, freeze tested dependency, minimal entry point and README | Local app starts with documented commands | pip check; Streamlit health returns ok | DONE |
| T02 | Backend | P0 | T01 | Distribution content, bounded evaluators, startup validator, counterexample search | Correct and faulty templates produce known values; invalid pack rejected | unittest evaluator/validation cases incl 9 vs 5 and search at zero | DONE |
| T03 | Full-stack | P0 | T02 | Prediction, reason, ambiguity probe, test bench with input control | Different evidence takes correct branches and real numbers change | Rendered UI (AppTest): faulty/matching, conflict, correct routes; core branch tests | DONE |
| T04 | Full-stack | P0 | T03 | Distribution repair, two hints, worked explanation, explicit transitions and tokens | Correct repair tested at three values; rerun cannot duplicate | Core transition/dedup tests; AppTest UI repeated submission | DONE |
| T05 | Verification | P0 | T04 | Working-flow checkpoint, completed before hour three | Actual Streamlit script runs prediction through repair | AppTest observed x=1 original 9/faulty 5; repair and changed input pass | DONE |
| T06 | Full-stack | P0 | T05 | Two distribution transfer items, assistance tracking, locked grading | New symbolic and area items gate unassisted success | Core tests for all outcomes/help; AppTest UI two-item completion | DONE |
| T07 | Full-stack | P0 | T06 | One ledger record/family, events, recommendation, due reviews | +1/+3/+7 scheduling, failure reopens, preview cannot pass | Injected-clock tests; AppTest UI ledger evidence and future preview | DONE |
| T08 | Full-stack | P0 | T07 | Size-limited validated export/import and reset | Round trip preserves evidence; invalid import preserves current state | Domain import/round-trip/bad data tests; AppTest UI reset; browser file dialog unverified | DONE |
| T09 | Full-stack | P0 | T08 | Square and negative packs via same engine/UI with authored questions | Both families complete debugger, transfer and ledger | Parameterized core tests; AppTest UI both journeys | DONE |
| T10 | UI | P2 | T09 | Resolve optional-AI branch: no credentials supplied, retain canonical no-key mode | All three features work without provider access; live AI honestly omitted | Full AppTest journey with network connection attempts forced to fail passes | DONE |
| T11 | Verification | P0 | T09 | Feature freeze at hour six; no-key regression and startup checks | Critical tests pass; no dependency on model or network during use | scripts/verify.py; pip check; health; AppTest UI offline loop | DONE |
| T12 | Verification | P0 | T11 | Rehearse demo actions through automated UI, README and fallback, check commit contents | Actual results and browser limits recorded; startup documented | AppTest UI walkthrough/reset; domain import; git diff --check; see VERIFICATION.md | DONE |

Cut order: T10 optional AI -> extra polish -> T09 additional families only if necessary and disclose partial scope.
Never cut all three features from distribution. Deployment is excluded unless official rules require it.
If deployment becomes required, amend this table with the verified platform and acceptance check.

Verification evidence: see VERIFICATION.md. Desktop browser automation was stopped by URL-identification safety checks; rendered Streamlit AppTest journeys substitute for that walkthrough. Optional model integration is intentionally omitted, not claimed tested.
