# Local demo fallback
1. From this checkout use Python 3.14.6; `.venv` is already installed on this PC.
2. Fresh PC: `python -m venv .venv`; `.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt`.
3. `.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8501`.
4. Open http://localhost:8501 and use built-in rule engine mode; no model API needed.
5. Follow PROJECT.md demo actions; export progress before resetting or refreshing.
6. Dependencies must already be installed for disconnected startup.
7. Browser recording/screenshots: not created; core and rendered UI test evidence is in VERIFICATION.md.
