"""Local checkpoint transactions. Stable sibling locks work across Windows processes."""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import RLock
from time import monotonic, sleep
from uuid import uuid4
import hashlib
import json
import os
import tempfile
from engine import DomainError, require
from ledger import clock, stamp

_MUTEX = RLock()
RECEIPT_LIMIT = 256
_PREVIEWS = {}


@dataclass
class LoadResult:
    status: str
    state: dict | None = None
    code: str = ''
    checkpoints: tuple = ()


@dataclass
class CommitResult:
    status: str
    state: dict | None = None
    revision: int | None = None
    message: str = ''


@dataclass(frozen=True)
class RestorePreview:
    preview_id: str
    workspace_id: str
    revision: int
    current_hash: str
    backup_hash: str
    backup_bytes: bytes
    counts: dict
    current_counts: dict
    saved_at: str | None


def _hash(payload):
    return hashlib.sha256(payload).hexdigest()


def _encode(state):
    from study import export_state, MAX_STATE, validate_state
    validate_state(state)
    payload=export_state(state).encode('utf-8')
    require(len(payload)<=MAX_STATE,'Workspace exceeds 8 MiB. Export and start a new workspace.','capacity')
    return payload


@contextmanager
def workspace_lock(path, timeout=3):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    if not _MUTEX.acquire(timeout=timeout): raise TimeoutError('Workspace busy.')
    handle=None; acquired=False
    try:
        handle=open(path.with_suffix(path.suffix+'.lock'),'a+b')
        handle.seek(0,2)
        if handle.tell()==0: handle.write(b'0'); handle.flush()
        deadline=monotonic()+timeout
        while True:
            try:
                handle.seek(0)
                if os.name=='nt':
                    import msvcrt
                    msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
                else:
                    import fcntl
                    fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
                acquired=True; break
            except OSError:
                if monotonic()>=deadline: raise TimeoutError('Workspace busy.') from None
                sleep(.025)
        yield
    finally:
        if handle:
            if acquired:
                handle.seek(0)
                if os.name=='nt':
                    import msvcrt
                    msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
                else:
                    import fcntl
                    fcntl.flock(handle,fcntl.LOCK_UN)
            handle.close()
        _MUTEX.release()


def _atomic(path,payload):
    path=Path(path); temporary=None
    try:
        with tempfile.NamedTemporaryFile('wb',dir=path.parent,prefix=path.name+'.',suffix='.tmp',delete=False) as f:
            temporary=Path(f.name); f.write(payload); f.flush(); os.fsync(f.fileno())
        os.replace(temporary,path)
    finally:
        if temporary and temporary.exists(): temporary.unlink()


def _read(path):
    from study import import_state
    return import_state(Path(path).read_text(encoding='utf-8-sig'))


def _install(path,state,retain=True):
    payload=_encode(state)
    if retain and path.exists():
        _read(path)  # Never promote a corrupt original into the good checkpoint.
        _atomic(path.with_suffix(path.suffix+'.previous'),path.read_bytes())
    _atomic(path,payload)


def read_workspace(path):
    path=Path(path)
    try:
        with workspace_lock(path):
            if not path.exists():
                from study import new_state
                state=new_state(); state['last_saved_at']=stamp(clock())
                _install(path,state,False)
                return LoadResult('ready',state)
            state=_read(path)
            raw=json.loads(path.read_text(encoding='utf-8-sig'))
            if raw.get('schema_version')!=6:
                state['last_saved_at']=stamp(clock()); state['revision']=1
                _install(path,state)
            return LoadResult('ready',state)
    except TimeoutError:
        return LoadResult('recoverable_error',code='workspace_busy')
    except (DomainError,OSError,ValueError,UnicodeError):
        previous=path.with_suffix(path.suffix+'.previous')
        checkpoints=()
        try:
            if previous.exists(): _read(previous); checkpoints=(str(previous),)
        except (DomainError,OSError,ValueError,UnicodeError): pass
        return LoadResult('recoverable_error',code='checkpoint_unavailable',checkpoints=checkpoints)


def transact(path,workspace_id,expected_revision,command_id,operation,now=None,*,payload_hash=None):
    """Operation executes only against the locked canonical checkpoint; no network here."""
    path=Path(path); current=None
    try:
        require(type(command_id) is str and 0<len(command_id)<=100,'Invalid command token.')
        # Commands without a supplied payload fingerprint cannot safely be replayed.
        require(type(payload_hash) is str and len(payload_hash)==64 and all(c in '0123456789abcdef' for c in payload_hash),'Commands require a SHA-256 payload fingerprint.')
        fingerprint=payload_hash
        with workspace_lock(path):
            if path.exists(): current=_read(path)
            else:
                from study import new_state
                current=new_state(); current['workspace_id']=workspace_id
                require(expected_revision==0,'Workspace changed. Refresh and retry.')
            if current['workspace_id']!=workspace_id:
                return CommitResult('conflict',current,current['revision'],'The workspace was replaced. Refresh before submitting again.')
            receipt=next((r for r in current['command_receipts'] if r['id']==command_id),None)
            if receipt:
                if receipt['hash']!=fingerprint:
                    return CommitResult('rejected',current,current['revision'],'This action token was reused with different content.')
                return CommitResult('already_applied',current,current['revision'],'Already saved.')
            if current['revision']!=expected_revision:
                return CommitResult('conflict',current,current['revision'],'Another tab saved newer work. Your action was not applied; review your input and submit again.')
            updated=operation(deepcopy(current))
            # Restore is the explicit separate path for replacing historical evidence.
            for key in ('attempts','reviews','practice_events'):
                require(updated[key][:len(current[key])]==current[key],'Saved learning evidence cannot be rewritten by a command.')
            surviving_events=[]
            for event in current['activity_events']:
                demo_reset=event['learner'] in ('Demo Learner A','Demo Learner B') and not any(s['learner']==event['learner'] for s in updated['nlm']['sessions']) and not any(r['learner']==event['learner'] for r in updated['nlm']['reviews']) and not any(e['learner']==event['learner'] for e in updated['activity_events'])
                debugger_reset=event['kind']=='debugger_experiment' and updated['debugger']['history'].get(event['learner']) is False and not any(e['id']==event['activity_id'] for e in updated['debugger']['episodes'])
                if not(demo_reset or debugger_reset):surviving_events.append(event)
            require(updated['activity_events'][:len(surviving_events)]==surviving_events,'Saved exposure cannot be rewritten outside a scoped history reset.')
            require(updated['pack_versions'][:len(current['pack_versions'])]==current['pack_versions'],'Saved pack versions are immutable.')
            for old in current['quizzes']:
                new=next((q for q in updated['quizzes'] if q['id']==old['id']),None)
                require(new is not None and all(new[k]==old[k] for k in ('id','document_id','question_ids','created_at')) and (not old['completed'] or new['completed']),'Saved quiz identity and scoring completion cannot be rewritten.')
            for old in current['cards']:
                new=next((c for c in updated['cards'] if c['id']==old['id']),None)
                require(new is not None and all(new[k]==old[k] for k in ('id','front','back','topic','source_chunk_id','evidence_quote','document_id')) and new['review_count']>=old['review_count'],'Saved card content is immutable.')
            for namespace,key in [('nlm','sessions'),('debugger','episodes')]:
                for old in current[namespace][key]:
                    new=next((r for r in updated[namespace][key] if r['id']==old['id']),None)
                    if new is None:
                        allowed=old['learner'] in ('Demo Learner A','Demo Learner B') if namespace=='nlm' else updated['debugger']['history'].get(old['learner']) is False
                        require(allowed and not any(r['learner']==old['learner'] for r in updated[namespace][key]),'Saved activities can only be removed by a scoped history reset.')
                    else:require(all(new[k]==old[k] for k in old if k!='events') and new['events'][:len(old['events'])]==old['events'],'Saved activity events are immutable.')
            old_docs={d['id']:d for d in current['documents']}
            for did,old in old_docs.items():
                new=next((d for d in updated['documents'] if d['id']==did),None)
                require(new is not None and all(new[k]==old[k] for k in ('id','title','filename','text','chunks','summary','mode','created_at')) and new['questions'][:len(old['questions'])]==old['questions'],'Saved source content and questions are immutable.')
            require(updated['workspace_id']==workspace_id and updated['revision']==expected_revision,'Commands cannot replace storage identity.')
            moment=now or clock(); stamp(moment)
            require(current['last_saved_at'] is None or moment>=datetime.fromisoformat(current['last_saved_at']),'Save time cannot precede the previous checkpoint.')
            updated['revision']=expected_revision+1; updated['last_saved_at']=stamp(moment)
            updated['command_receipts']=(current['command_receipts']+[dict(id=command_id,hash=fingerprint,revision=updated['revision'])])[-RECEIPT_LIMIT:]
            _install(path,updated)
            return CommitResult('committed',updated,updated['revision'],'Saved locally.')
    except TimeoutError:
        return CommitResult('io_error',message='Workspace busy. Retry when the other save finishes.')
    except DomainError as exc:
        return CommitResult('rejected',current,current['revision'] if current else None,str(exc))
    except (KeyError,TypeError,AttributeError):
        return CommitResult('rejected',current,current['revision'] if current else None,'The workspace command was invalid. Existing work is unchanged.')
    except (OSError,ValueError,UnicodeError):
        return CommitResult('io_error',message='The save failed. The previous checkpoint has been preserved. Retry your action.')


def commit_snapshot(path,base,updated,now=None,command_id=None):
    """Safe transitional adapter for existing pure domain commands: never merges stale snapshots."""
    try:
        payload=deepcopy(updated)
        # The original identity/revision is checked under lock; never merge a stale snapshot.
        payload['workspace_id']=base['workspace_id']; payload['revision']=base['revision']
        fingerprint=_hash(_encode(payload))
        return transact(path,base['workspace_id'],base['revision'],command_id or str(uuid4()),
                        lambda current: payload,now,payload_hash=fingerprint)
    except DomainError as exc:
        return CommitResult('rejected',message=str(exc))
    except (KeyError,TypeError,ValueError):
        return CommitResult('rejected',message='Invalid workspace command. Existing data is unchanged.')


def _counts(s):
    return {k:len(s[k]) for k in ('documents','attempts','cards','quizzes')}


def prepare_restore(path,backup_bytes,now=None):
    from study import import_state
    require(type(backup_bytes) is bytes,'Choose a backup file.')
    backup=import_state(backup_bytes.decode('utf-8-sig'))
    path=Path(path)
    with workspace_lock(path):
        raw=path.read_bytes() if path.exists() else b''
        try: current=_read(path)
        except (DomainError,OSError,ValueError,UnicodeError): current=None
        preview=RestorePreview(str(uuid4()),current['workspace_id'] if current else '',current['revision'] if current else -1,
            _hash(raw),_hash(backup_bytes),backup_bytes,_counts(backup),_counts(current) if current else {},backup['last_saved_at'])
        _PREVIEWS[preview.preview_id]=preview
        while len(_PREVIEWS)>32:_PREVIEWS.pop(next(iter(_PREVIEWS)))
        return preview


def apply_restore(path,preview_id,expected_revision,now=None):
    """The preview object binds the exact bytes, current file hash and revision."""
    from study import import_state
    preview=_PREVIEWS.get(preview_id) if type(preview_id) is str else preview_id; path=Path(path)
    try:
        require(isinstance(preview,RestorePreview),'Prepare a restore preview first.')
        with workspace_lock(path):
            raw=path.read_bytes() if path.exists() else b''
            if expected_revision!=preview.revision or _hash(raw)!=preview.current_hash:
                return CommitResult('conflict',message='Workspace changed after preview. Preview the backup again.')
            require(_hash(preview.backup_bytes)==preview.backup_hash,'Backup changed after preview.')
            state=import_state(preview.backup_bytes.decode('utf-8-sig'))
            state['workspace_id']=str(uuid4()); state['revision']=0
            state['command_receipts']=[]; state['last_saved_at']=stamp(now or clock())
            payload=_encode(state)
            if raw: _atomic(path.with_suffix(path.suffix+'.pre-restore'),raw)
            _atomic(path,payload)
            return CommitResult('committed',state,0,'Backup restored. A recovery copy was retained.')
    except (DomainError,OSError,ValueError,UnicodeError,TimeoutError):
        return CommitResult('io_error',message='Restore failed. Existing data is unchanged.')


def storage_usage(state):
    from study import MAX_STATE
    size=len(_encode(state))
    return dict(bytes=size,limit=MAX_STATE,fraction=size/MAX_STATE,
                level='critical' if size/MAX_STATE>=.95 else 'warning' if size/MAX_STATE>=.8 else 'normal')
