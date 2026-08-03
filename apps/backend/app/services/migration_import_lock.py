"""Dependency-free bounded O_EXCL coordinator lock."""
from __future__ import annotations
import json, os, socket, time
from datetime import datetime, timezone
from pathlib import Path
from app.models.memory_migration_import import ImportDiagnosticCode, MemoryMigrationImportError
from app.services.migration_import_paths import resolve_migration_import_lock_path

class MigrationImportLock:
    def __init__(self, path: Path | None=None, timeout: float=2.0, poll_interval: float=.02):
        self.path=path or resolve_migration_import_lock_path(); self.timeout=timeout; self.poll_interval=poll_interval; self._owned=False
    def acquire(self, operation_identity: str="startup"):
        self.path.parent.mkdir(parents=True, exist_ok=True); deadline=time.monotonic()+self.timeout
        data=json.dumps({"owner_pid":os.getpid(),"created_at":datetime.now(timezone.utc).isoformat(),"operation_identity":operation_identity,"host":socket.gethostname()}).encode()
        while True:
            try:
                fd=os.open(self.path, os.O_CREAT|os.O_EXCL|os.O_WRONLY)
                with os.fdopen(fd,"wb") as f: f.write(data); f.flush(); os.fsync(f.fileno())
                self._owned=True; return self
            except FileExistsError:
                if time.monotonic()>=deadline: raise MemoryMigrationImportError(ImportDiagnosticCode.LOCK_UNAVAILABLE,"migration import lock is unavailable")
                time.sleep(self.poll_interval)
    def release(self):
        if self._owned:
            try: self.path.unlink(); self._owned=False
            except OSError as exc: raise MemoryMigrationImportError(ImportDiagnosticCode.LOCK_RELEASE_FAILURE,"migration import lock release failed") from exc
    def __enter__(self): return self.acquire()
    def __exit__(self, *_): self.release()
