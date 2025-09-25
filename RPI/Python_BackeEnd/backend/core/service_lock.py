from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Lock as ThreadLock

LOCK_TTL_SECONDS = 30  # jak dlouho zámek drží bez heartbeat
_lock_guard = ThreadLock()

@dataclass
class ServiceLock:
    owner_id: str
    acquired_at: datetime
    expires_at: datetime

_service_lock: ServiceLock | None = None

def _now():
    return datetime.utcnow()

def _status_locked() -> dict:
    """Volat jen když je _lock_guard UŽ držený."""
    global _service_lock
    if _service_lock and _service_lock.expires_at > _now():
        return {
            "locked": True,
            "owner_id": _service_lock.owner_id,
            "expires_at": _service_lock.expires_at.isoformat()
        }
    else:
        _service_lock = None
        return {"locked": False}

def get_status() -> dict:
    with _lock_guard:
        return _status_locked()

def acquire(owner_id: str) -> dict:
    """Získání zámku, když je volno nebo zámek expiroval."""
    global _service_lock
    print(f"Trying to acquire lock for owner_id={owner_id}")
    with _lock_guard:
        if _service_lock and _service_lock.expires_at > _now() and _service_lock.owner_id != owner_id:
            print(f"Lock is busy, owned by {_service_lock.owner_id} until {_service_lock.expires_at}")
            return {"ok": False, "reason": "busy", **_status_locked()}
        # volno nebo reentry stejným klientem
        _service_lock = ServiceLock(owner_id=owner_id, acquired_at=_now(), expires_at=_now() + timedelta(seconds=LOCK_TTL_SECONDS))
        print(f"Lock acquired by {owner_id} until {_service_lock.expires_at}")
        return {"ok": True, **_status_locked()}

def heartbeat(owner_id: str) -> dict:
    """Prodluž život zámku, jen když vlastní stejný owner."""
    global _service_lock
    with _lock_guard:
        if not _service_lock or _service_lock.owner_id != owner_id:
            return {"ok": False, "reason": "not_owner", **_status_locked()}
        _service_lock.expires_at = _now() + timedelta(seconds=LOCK_TTL_SECONDS)
        return {"ok": True, **_status_locked()}

def release(owner_id: str) -> dict:
    global _service_lock
    with _lock_guard:
        if _service_lock and _service_lock.owner_id == owner_id:
            _service_lock = None
            return {"ok": True, "locked": False}
        return {"ok": False, "reason": "not_owner", **_status_locked()}
