"""Start Phoenix on the first available local port without stopping other apps."""
from pathlib import Path
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def available_port():
    for port in range(8501, 8521):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind(('127.0.0.1', port))
            except OSError:
                continue
            return port
    raise RuntimeError('Ports 8501–8520 are occupied. Close an unused server and try again.')


if __name__ == '__main__':
    port = available_port()
    print(f'Phoenix: open http://127.0.0.1:{port} — press Ctrl+C to stop.', flush=True)
    try:
        raise SystemExit(subprocess.call([
            sys.executable, '-m', 'streamlit', 'run', str(ROOT / 'app.py'),
            '--server.address', '127.0.0.1', '--server.port', str(port),
        ], cwd=ROOT))
    except KeyboardInterrupt:
        pass
