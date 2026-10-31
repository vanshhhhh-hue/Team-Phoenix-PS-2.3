# Deployment

Status: prepared for a hosted demo; no deployment has been performed. The owner will choose when and where to deploy.

## Runtime contract

- Python 3.14; install `requirements-lock.txt` in a clean environment.
- Start command: `python scripts/serve.py`.
- `PORT`: host-provided listening port, default 8501.
- `PHOENIX_MODE=demo`: independent session-only User 1 workspaces, no authentication required.
- Health endpoint: `GET /_stcore/health`, expected HTTP 200 and `ok`.
- WebSockets must be supported by the hosting proxy. Multiple replicas require sticky sessions.

For Streamlit-oriented hosting, select root `app.py` as the entry point. Set mode to `demo` in the host environment; the root requirements file contains the direct dependencies.

## Optional AI

Set `GEMINI_API_KEY` and `GEMINI_MODEL` in the host's secret environment. Do not upload a real `.env`, `.local`, local virtual environment, or backup. Demo fixtures are fictional and committed intentionally. AI starts disabled in the fixture; it can be enabled through Workspace settings. Provider quota, model access, and generation quality require a separate live check.

## Local hosted-command rehearsal

```powershell
$env:PHOENIX_MODE = "demo"
$env:PORT = "8502"
python scripts/serve.py
```

Open the app and check User 1 on Dashboard, Library, Quiz, Flash Cards, Insights, and Teacher Dashboard. Confirm a second browser session starts with the fixture and cannot see the first session's changes. Check reset and export, then verify `/_stcore/health`.

This command listens on all interfaces for hosting. Use `Start-Phoenix.cmd` for loopback-only development.

## Persistent use

Use `PHOENIX_MODE=local` only in a private, single-owner environment. Configure `PHOENIX_DATA_DIR` to a durable writable volume; do not use an ephemeral host disk for personal progress. This mode does not provide user accounts, access control, or cross-replica storage coordination.

## Release checks

Run `python scripts/verify.py`, `python -m pip check`, and `git diff --check`. Inspect staged files to exclude credentials and private data. Rehearse the hosted command and confirm health. Check representative desktop and narrow layouts and the live provider if AI will be enabled. Keep unverified accessibility and user-study claims separate from automated checks.

Official reference: [Streamlit deployment concepts](https://docs.streamlit.io/deploy/concepts).

The default hosted demo includes synthetic student/teacher profiles; this is documented in README and fixture provenance. The teacher dashboard has no authentication or real tenant separation. Deploy it only as the showcase.
