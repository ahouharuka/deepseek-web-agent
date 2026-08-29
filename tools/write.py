from __future__ import annotations

import difflib
from pathlib import Path
from typing import Any

from tools.readonly import resolve_in_workspace


MAX_FILE_CHARS = 200_000
CREATE_EXTENSIONS = {".py", ".txt", ".md", ".json", ".yaml", ".yml", ".toml"}


def _prepare(workspace: Path, arguments: dict[str, Any]) -> tuple[Path, str, str]:
    allowed = {"path", "old_text", "new_text"}
    extra = set(arguments) - allowed
    missing = allowed - set(arguments)
    if extra or missing:
        raise ValueError(f"参数不匹配；缺少={sorted(missing)}，多余={sorted(extra)}")
    target = resolve_in_workspace(workspace, arguments["path"])
    if not target.is_file():
        raise ValueError("当前工具只能修改已有文本文件")
    old_text = arguments["old_text"]
    new_text = arguments["new_text"]
    if not isinstance(old_text, str) or not old_text:
        raise ValueError("old_text 必须是非空字符串")
    if not isinstance(new_text, str):
        raise ValueError("new_text 必须是字符串")
    original = target.read_text(encoding="utf-8")
    if len(original) > MAX_FILE_CHARS:
        raise ValueError("文件过大，拒绝修改")
    count = original.count(old_text)
    if count != 1:
        raise ValueError(f"old_text 必须恰好出现一次，实际出现 {count} 次")
    return target, original, original.replace(old_text, new_text, 1)


def preview_text_patch(workspace: Path, arguments: dict[str, Any]) -> str:
    target, original, updated = _prepare(workspace, arguments)
    return "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile=str(target),
            tofile=str(target),
        )
    )


def apply_text_patch(workspace: Path, arguments: dict[str, Any]) -> dict[str, Any]:
    target, original, updated = _prepare(workspace, arguments)
    target.write_text(updated, encoding="utf-8")
    return {"path": str(target.relative_to(workspace)), "changed": True, "characters_before": len(original), "characters_after": len(updated)}


def _prepare_create(workspace: Path, arguments: dict[str, Any]) -> tuple[Path, str]:
    if set(arguments) != {"path", "content"}:
        raise ValueError("create_text_file 只接受 path 和 content")
    target = resolve_in_workspace(workspace, arguments["path"])
    content = arguments["content"]
    if not isinstance(content, str):
        raise ValueError("content 必须是字符串")
    if len(content) > 100_000:
        raise ValueError("新文件内容超过 100000 字符")
    if target.suffix.lower() not in CREATE_EXTENSIONS:
        raise ValueError(f"不允许创建扩展名 {target.suffix!r} 的文件")
    if target.exists():
        raise ValueError("目标已经存在，拒绝覆盖")
    parent = target.parent
    if not parent.is_dir():
        raise ValueError("父目录不存在；当前工具不会自动创建目录")
    return target, content


def preview_create_text_file(workspace: Path, arguments: dict[str, Any]) -> str:
    target, content = _prepare_create(workspace, arguments)
    body = "".join(f"+{line}" for line in content.splitlines(keepends=True))
    return f"--- /dev/null\n+++ {target}\n{body}"


def create_text_file(workspace: Path, arguments: dict[str, Any]) -> dict[str, Any]:
    target, content = _prepare_create(workspace, arguments)
    with target.open("x", encoding="utf-8", newline="") as handle:
        handle.write(content)
    return {"path": str(target.relative_to(workspace)), "created": True, "characters": len(content)}


def _prepare_replace_line(workspace: Path, arguments: dict[str, Any]) -> tuple[Path, list[str], int, str]:
    if set(arguments) != {"path", "line_number", "expected", "replacement"}:
        raise ValueError("replace_line 只接受 path、line_number、expected、replacement")
    target = resolve_in_workspace(workspace, arguments["path"])
    if not target.is_file():
        raise ValueError("目标不是已有文件")
    line_number = arguments["line_number"]
    expected = arguments["expected"]
    replacement = arguments["replacement"]
    if not isinstance(line_number, int) or line_number < 1:
        raise ValueError("line_number 必须是从 1 开始的整数")
    if not isinstance(expected, str) or not isinstance(replacement, str):
        raise ValueError("expected 和 replacement 必须是字符串")
    if "\n" in expected or "\r" in expected or "\n" in replacement or "\r" in replacement:
        raise ValueError("replace_line 不允许换行符")
    lines = target.read_text(encoding="utf-8").splitlines(keepends=True)
    if line_number > len(lines):
        raise ValueError("line_number 超出文件范围")
    actual = lines[line_number - 1].rstrip("\r\n")
    if actual != expected:
        raise ValueError(f"目标行内容与 expected 不一致；实际为 {actual!r}")
    return target, lines, line_number - 1, replacement


def preview_replace_line(workspace: Path, arguments: dict[str, Any]) -> str:
    target, lines, index, replacement = _prepare_replace_line(workspace, arguments)
    original = "".join(lines)
    ending = "\r\n" if lines[index].endswith("\r\n") else "\n" if lines[index].endswith("\n") else ""
    updated_lines = list(lines)
    updated_lines[index] = replacement + ending
    return "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            "".join(updated_lines).splitlines(keepends=True),
            fromfile=str(target),
            tofile=str(target),
        )
    )


def replace_line(workspace: Path, arguments: dict[str, Any]) -> dict[str, Any]:
    target, lines, index, replacement = _prepare_replace_line(workspace, arguments)
    ending = "\r\n" if lines[index].endswith("\r\n") else "\n" if lines[index].endswith("\n") else ""
    lines[index] = replacement + ending
    target.write_text("".join(lines), encoding="utf-8", newline="")
    return {"path": str(target.relative_to(workspace)), "changed": True, "line_number": index + 1}
