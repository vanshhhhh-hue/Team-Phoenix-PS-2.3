# Continue Phoenix Study - full AI Study Companion
Repository: https://github.com/vanshhhhh-hue/Team-Phoenix-PS-2.3.git
One repository, PC and owner. Read AGENTS.md, AGENT_RULES.md, PROJECT.md, TASKS.md and HANDOFF.md.
Read API_CONTRACT.md before application/data changes; git status and git log -5 --oneline before edits.
The user has already authorised continuous development. Do not ask to begin or to proceed between tasks.
The product is uploaded-material learning, NOT an algebra-only lab.
Core: PDF/TXT/MD/pasted notes -> grounded study pack -> adaptive quiz/hints -> weak topics -> spaced cards.
Keep Dashboard, Library, Quiz, Revision and Insights as the main app. Algebra lab is supporting navigation.
The owner explicitly restored the original problem statement; old no-upload restrictions are superseded.
Use existing Python/Streamlit/pypdf implementation in this checkout; no second repository or rewrite by default.
Gemini key is in ignored .env as API_KEY; provider confirmed by owner. Never print/read its value into output.
Use official Gemini endpoint via server-side ai_provider.py. Model gemini-flash-lite-latest has passed smoke testing.
Keep labelled local extractive fallback when Gemini is missing, unavailable, rate-limited or invalid.
AI generates content; deterministic code validates references, grades answers and schedules revision.
Never claim source quoting validates answer semantics or that local cloze questions equal live AI quality.
Save study state atomically in ignored .local; exports include notes/progress but never secrets.
Retain separate legacy lab evidence and its tests. Do not restart completed lab work.
Continue next unblocked task; work across UI/domain/persistence as needed. Keep one task IN-PROGRESS.
Do not stop at files, milestones, failing tests or routine blockers. Diagnose, fix, verify and continue.
Try supported alternatives; never fake completion, bypass access controls or discard user changes.
Ask only for an indispensable external action after all independent work is finished.
Update operations, callers, tests and contracts together. Record actual check results before DONE.
Commit verified changes and push meaningful checkpoints when access permits.
Use PowerShell/cross-platform commands; preserve tested dependency pins and key exclusions.
No OCR, teacher dashboard, login or public hosting unless explicitly added to scope.
Rewrite HANDOFF.md before stopping with current state, failures and exact next action.
