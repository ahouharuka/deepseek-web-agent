from __future__ import annotations

import difflib
import re
from pathlib import Path
from typing import Any


DEFAULT_MAX_CHARS = 20_000
MAX_READ_BYTES = 1_000_000
MAX_SEARCH_RESULTS = 100
DENIED_PARTS = {
    ".git", ".venv", ".browser-profile", "logs", "node_modules", "__pycache__",
    ".ssh", ".aws", ".azure", ".gnupg", ".kube", ".docker",
}
DENIED_NAMES = {
    ".env", ".netrc", ".npmrc", ".pypirc", "credentials", "credentials.json",
    "secrets", "secrets.json", "id_rsa", "id_ed25519",
}
DENIED_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".kdbx"}
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
)


def resolve_in_workspace(workspace: Path, raw_path: object) -> Path:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValueError("path 必须是非空字符串")
    requested = Path(raw_path)
    if requested.is_absolute() or ".." in requested.parts:
        raise ValueError("路径必须是工作区内不含 .. 的相对路径")
    unresolved = workspace.resolve() / requested
    ensure_no_symlink_path(workspace, unresolved)
    candidate = unresolved.resolve()
    try:
        candidate.relative_to(workspace.resolve())
    except ValueError as exc:
        raise ValueError("路径超出工作区") from exc
    ensure_path_allowed(workspace, candidate)
    return candidate


def ensure_path_allowed(workspace: Path, candidate: Path) -> None:
    relative = candidate.relative_to(workspace.resolve())
    parts = {part.casefold() for part in relative.parts}
    name = candidate.name.casefold()
    if parts & DENIED_PARTS or name in DENIED_NAMES or name.startswith(".env.") or candidate.suffix.casefold() in DENIED_SUFFIXES:
        raise ValueError(f"安全策略拒绝访问敏感路径：{relative}")


def ensure_no_symlink_path(workspace: Path, candidate: Path) -> None:
    """Reject links so the checked path cannot redirect between policy and I/O."""
    root = workspace.resolve()
    relative = candidate.relative_to(root)
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"安全策略拒绝访问符号链接：{relative}")


def list_files(workspace: Path, arguments: dict[str, Any]) -> list[dict[str, Any]]:
    _only_keys(arguments, {"path", "recursive"})
    target = resolve_in_workspace(workspace, arguments.get("path"))
    recursive = arguments.get("recursive", False)
    if not isinstance(recursive, bool):
        raise ValueError("recursive 必须是布尔值")
    if not target.is_dir():
        raise ValueError(_missing_path_message(workspace, arguments.get("path"), "目录"))
    items = target.rglob("*") if recursive else target.iterdir()
    result: list[dict[str, Any]] = []
    for item in sorted(items, key=lambda p: str(p).lower()):
        try:
            ensure_path_allowed(workspace, item.resolve())
        except ValueError:
            continue
        result.append({"path": str(item.relative_to(workspace)), "type": "directory" if item.is_dir() else "file"})
        if len(result) >= 1000:
            break
    return result


def read_file(workspace: Path, arguments: dict[str, Any]) -> dict[str, Any]:
    _only_keys(arguments, {"path", "max_chars"})
    target = resolve_in_workspace(workspace, arguments.get("path"))
    max_chars = arguments.get("max_chars", DEFAULT_MAX_CHARS)
    if not isinstance(max_chars, int) or not 1 <= max_chars <= 100_000:
        raise ValueError("max_chars 必须是 1 到 100000 之间的整数")
    if not target.is_file():
        raise ValueError(_missing_path_message(workspace, arguments.get("path"), "文件"))
    ensure_no_symlink_path(workspace, target)
    if target.stat().st_size > MAX_READ_BYTES:
        raise ValueError(f"文件超过 {MAX_READ_BYTES} 字节，拒绝读取")
    text = target.read_text(encoding="utf-8")
    if contains_likely_secret(text):
        raise ValueError("文件内容疑似包含密钥或私钥，拒绝发送给模型")
    return {"text": text[:max_chars], "truncated": len(text) > max_chars}


def search_text(workspace: Path, arguments: dict[str, Any]) -> list[dict[str, Any]]:
    _only_keys(arguments, {"query", "path"})
    query = arguments.get("query")
    if not isinstance(query, str) or not query:
        raise ValueError("query 必须是非空字符串")
    target = resolve_in_workspace(workspace, arguments.get("path", "."))
    candidates = [target] if target.is_file() else target.rglob("*")
    results: list[dict[str, Any]] = []
    for file_path in candidates:
        if not file_path.is_file() or file_path.stat().st_size > 1_000_000:
            continue
        try:
            ensure_path_allowed(workspace, file_path.resolve())
            ensure_no_symlink_path(workspace, file_path)
        except ValueError:
            continue
        try:
            file_text = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if contains_likely_secret(file_text):
            continue
        lines = file_text.splitlines()
        for line_number, line in enumerate(lines, start=1):
            if query.casefold() in line.casefold():
                results.append({"path": str(file_path.relative_to(workspace)), "line": line_number, "text": line[:500]})
                if len(results) >= MAX_SEARCH_RESULTS:
                    return results
    return results


def get_file_info(workspace: Path, arguments: dict[str, Any]) -> dict[str, Any]:
    _only_keys(arguments, {"path"})
    target = resolve_in_workspace(workspace, arguments.get("path"))
    if not target.exists():
        raise ValueError(_missing_path_message(workspace, arguments.get("path"), "路径"))
    stat = target.stat()
    return {
        "path": str(target.relative_to(workspace)),
        "type": "directory" if target.is_dir() else "file",
        "size": stat.st_size,
        "modified_ns": stat.st_mtime_ns,
    }


def _only_keys(arguments: dict[str, Any], allowed: set[str]) -> None:
    extra = set(arguments) - allowed
    if extra:
        raise ValueError(f"存在不允许的参数：{sorted(extra)}")


def _missing_path_message(workspace: Path, raw_path: object, expected_type: str) -> str:
    requested = raw_path if isinstance(raw_path, str) else ""
    candidates = []
    for path in workspace.rglob("*"):
        try:
            ensure_path_allowed(workspace, path.resolve())
        except ValueError:
            continue
        candidates.append(str(path.relative_to(workspace)))
        if len(candidates) >= 5000:
            break
    matches = difflib.get_close_matches(requested, candidates, n=3, cutoff=0.45)
    suffix = f"；你是否想使用：{matches}" if matches else ""
    return f"目标不是已有{expected_type}：{requested!r}{suffix}。必须复制候选中的完整相对路径，不得自行改写。"


def contains_likely_secret(text: str) -> bool:
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)
