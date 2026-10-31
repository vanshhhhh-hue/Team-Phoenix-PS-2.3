"""Separate-process storage regression helper; only caller-supplied temporary paths."""
from pathlib import Path
import json
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1] / 'src' / 'phoenix'))
from storage import commit_snapshot,workspace_lock

if __name__=='__main__':
    if sys.argv[1]=='--hold':
        path,ready,release=sys.argv[2:]
        with workspace_lock(path):
            Path(ready).write_text('locked')
            deadline=time.monotonic()+10
            while not Path(release).exists():
                if time.monotonic()>deadline:raise TimeoutError('Hold was not released.')
                time.sleep(.02)
        raise SystemExit(0)
    path,base_file,updated_file,gate_file=sys.argv[1:]
    deadline=time.monotonic()+10
    while not Path(gate_file).exists():
        if time.monotonic()>deadline:raise TimeoutError('Probe gate did not open.')
        time.sleep(.02)
    result=commit_snapshot(path,json.loads(Path(base_file).read_text()),json.loads(Path(updated_file).read_text()))
    print(json.dumps(dict(status=result.status,revision=result.revision)))
