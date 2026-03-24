"""Append-only audit trail for session actions.

Each session writes a .jsonl file (one JSON object per line) to output/audit/.
Lines are hash-chained: every entry includes a SHA-256 of the previous entry
so casual tampering (editing/deleting lines) is detectable.
"""
import hashlib
import json
import os
from datetime import datetime, timezone

from logger_config import get_logger

logger = get_logger(__name__)

_AUDIT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "audit")


class AuditLogger:
    """Hash-chained, append-only audit log for a single session."""

    def __init__(self, serial_number: str, technician: str, mode: int,
                 workflow_name: str = None, description: str = None):
        os.makedirs(_AUDIT_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_serial = self._safe(serial_number)
        filename = f"audit_{safe_serial}_{ts}.jsonl"
        self._path = os.path.join(_AUDIT_DIR, filename)
        self._prev_hash = "0" * 64  # genesis hash
        self._file = open(self._path, "a", encoding="utf-8")

        self._serial = serial_number
        self._technician = technician
        self._workflow = workflow_name
        self._mode = mode

        self.log("session_start", {
            "mode": mode,
            "description": description or "",
            "workflow": workflow_name,
        })

    # -- public API --

    def log(self, event: str, details: dict = None):
        """Write one audit entry and flush immediately."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "serial_number": self._serial,
            "technician": self._technician,
            "workflow": self._workflow,
            "details": details or {},
            "prev_hash": self._prev_hash,
        }
        line = json.dumps(entry, ensure_ascii=False)
        self._prev_hash = hashlib.sha256(line.encode("utf-8")).hexdigest()
        try:
            self._file.write(line + "\n")
            self._file.flush()
        except Exception:
            logger.warning("Failed to write audit entry", exc_info=True)

    def close(self):
        """Write session_end and close the file."""
        try:
            self.log("session_end")
            self._file.close()
        except Exception:
            logger.warning("Failed to close audit log", exc_info=True)

    # -- helpers --

    @staticmethod
    def _safe(name: str) -> str:
        return "".join(c if c.isalnum() or c in "-_" else "_" for c in (name or "unknown"))


def verify_audit_file(path: str) -> bool:
    """Verify the hash chain of an audit .jsonl file.

    Returns True if every line's prev_hash matches the SHA-256 of the
    preceding line (or the genesis hash for the first line).
    """
    prev = "0" * 64
    try:
        with open(path, "r", encoding="utf-8") as f:
            for lineno, raw in enumerate(f, 1):
                raw = raw.rstrip("\n")
                entry = json.loads(raw)
                if entry.get("prev_hash") != prev:
                    logger.warning("Audit chain broken at line %d in %s", lineno, path)
                    return False
                prev = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    except Exception:
        logger.warning("Failed to verify audit file %s", path, exc_info=True)
        return False
    return True
