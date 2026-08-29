from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.readonly import contains_likely_secret


MAX_LOG_STRING_CHARS = 2_000
SENSITIVE_FIELDS = {
    "task", "text", "content", "stdout", "stderr", "old_text", "new_text",
    "replacement", "expected", "question", "answer",
    "error",
}


class AuditLog:
    def __init__(self, log_dir: Path):
        log_dir.mkdir(parents=True, exist_ok=True)
        _restrict_permissions(log_dir, 0o700)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        self.path = log_dir / f"task-{stamp}.jsonl"
        self.path.touch(exist_ok=False)
        _restrict_permissions(self.path, 0o600)

    def write(self, event: str, data: Any) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "data": _sanitize(data),
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def _sanitize(value: Any, field: str | None = None) -> Any:
    if field in SENSITIVE_FIELDS:
        if isinstance(value, str):
            return {"redacted": True, "characters": len(value)}
        return "[redacted]"
    if isinstance(value, dict):
        return {str(key): _sanitize(item, str(key)) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value[:100]]
    if isinstance(value, str):
        if contains_likely_secret(value):
            return "[redacted: likely secret]"
        if len(value) > MAX_LOG_STRING_CHARS:
            return value[:MAX_LOG_STRING_CHARS] + f"… [truncated {len(value) - MAX_LOG_STRING_CHARS} chars]"
    return value


def _restrict_permissions(path: Path, mode: int) -> None:
    try:
        os.chmod(path, mode)
    except OSError:
        pass
