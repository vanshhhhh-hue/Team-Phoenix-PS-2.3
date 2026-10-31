"""Disposable User 1 workspace; sample records never replace local user data."""
from pathlib import Path
from study import import_state

SAMPLE_PATH = Path(__file__).resolve().parents[2] / 'samples/users/user-1/workspace.json'


def load_demo():
    # Parse and validate afresh for each browser session, never share a mutable cache.
    return import_state(SAMPLE_PATH.read_text(encoding='utf-8'))
