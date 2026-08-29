from __future__ import annotations

import subprocess
import sys
import os
from pathlib import Path
from typing import Any

from tools.readonly import resolve_in_workspace


MAX_OUTPUT_CHARS = 30_000
TIMEOUT_SECONDS = 120
SAFE_ENV_NAMES = {"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "TMPDIR", "LANG", "LC_ALL"}


def _prepare(workspace: Path, arguments: dict[str, Any]) -> tuple[list[str], Path]:
    if set(arguments) != {"runner", "path"}:
        raise ValueError("run_tests 只接受 runner 和 path")
    if arguments["runner"] != "python_unittest":
        raise ValueError("runner 不在白名单中；当前仅允许 python_unittest")
    target = resolve_in_workspace(workspace, arguments["path"])
    if not target.is_dir():
        raise ValueError("测试路径必须是已有目录")
    relative = str(target.relative_to(workspace)) or "."
    command = [sys.executable, "-m", "unittest", "discover", "-s", relative, "-v"]
    return command, workspace


def preview_run_tests(workspace: Path, arguments: dict[str, Any]) -> str:
    command, cwd = _prepare(workspace, arguments)
    return f"工作目录：{cwd}\n固定命令：{' '.join(command)}\n超时：{TIMEOUT_SECONDS} 秒"


def run_tests(workspace: Path, arguments: dict[str, Any]) -> dict[str, Any]:
    command, cwd = _prepare(workspace, arguments)
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT_SECONDS,
            shell=False,
            env=_sanitized_environment(),
        )
        stdout = completed.stdout
        stderr = completed.stderr
        return {
            "exit_code": completed.returncode,
            "passed": completed.returncode == 0,
            "stdout": stdout[:MAX_OUTPUT_CHARS],
            "stderr": stderr[:MAX_OUTPUT_CHARS],
            "truncated": len(stdout) > MAX_OUTPUT_CHARS or len(stderr) > MAX_OUTPUT_CHARS,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "exit_code": None,
            "passed": False,
            "stdout": _as_text(exc.stdout)[:MAX_OUTPUT_CHARS],
            "stderr": _as_text(exc.stderr)[:MAX_OUTPUT_CHARS],
            "truncated": False,
            "timed_out": True,
        }


def _as_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value


def _sanitized_environment() -> dict[str, str]:
    environment = {name: value for name, value in os.environ.items() if name.upper() in SAFE_ENV_NAMES}
    environment.update({"PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"})
    return environment
