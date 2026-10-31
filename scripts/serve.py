"""Hosted Streamlit entry point. Does not deploy or provision infrastructure."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    port = int(os.environ.get('PORT', '8501'))
    if not 1 <= port <= 65535:
        raise ValueError('PORT must be between 1 and 65535.')
    os.environ.setdefault('PHOENIX_MODE', 'demo')
    return subprocess.call([
        sys.executable, '-m', 'streamlit', 'run', str(ROOT / 'app.py'),
        '--server.address=0.0.0.0', f'--server.port={port}',
        '--server.headless=true', '--browser.gatherUsageStats=false',
    ], cwd=ROOT)


if __name__ == '__main__':
    raise SystemExit(main())
