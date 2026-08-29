from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from tools.readonly import get_file_info, list_files, read_file, search_text
from tools.runner import preview_run_tests, run_tests
from tools.write import (
    apply_text_patch,
    create_text_file,
    preview_create_text_file,
    preview_replace_line,
    preview_text_patch,
    replace_line,
)


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    readonly: bool
    execute: Callable[[dict[str, Any]], Any]
    preview: Callable[[dict[str, Any]], str] | None = None
    approval_label: str = "执行文件写入"


class ToolRegistry:
    def __init__(self, tools: list[Tool]):
        self._tools = {tool.name: tool for tool in tools}

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"未知工具：{name}") from exc

    def describe(self) -> list[dict[str, Any]]:
        return [
            {"name": tool.name, "description": tool.description, "readonly": tool.readonly}
            for tool in self._tools.values()
        ]


def build_readonly_registry(workspace: Path) -> ToolRegistry:
    return ToolRegistry(
        [
            Tool("list_files", "列出目录。参数：path、recursive（可选）", True, lambda a: list_files(workspace, a)),
            Tool("read_file", "读取 UTF-8 文本文件。参数：path、max_chars（可选）", True, lambda a: read_file(workspace, a)),
            Tool("search_text", "在文本文件中搜索。参数：query、path（可选）", True, lambda a: search_text(workspace, a)),
            Tool("get_file_info", "获取文件元数据。参数：path", True, lambda a: get_file_info(workspace, a)),
        ]
    )


def build_coding_registry(workspace: Path) -> ToolRegistry:
    readonly = build_readonly_registry(workspace)
    tools = list(readonly._tools.values())
    tools.append(
        Tool(
            "replace_line",
            "安全替换单行。参数：path、line_number（从1开始）、expected、replacement",
            False,
            lambda a: replace_line(workspace, a),
            lambda a: preview_replace_line(workspace, a),
            "执行文件写入",
        )
    )
    tools.append(
        Tool(
            "apply_text_patch",
            "精确替换文本。参数：path、old_text、new_text；old_text 必须恰好出现一次",
            False,
            lambda a: apply_text_patch(workspace, a),
            lambda a: preview_text_patch(workspace, a),
        )
    )
    tools.append(
        Tool(
            "create_text_file",
            "创建新的 UTF-8 文本文件。参数：path、content；禁止覆盖已有文件",
            False,
            lambda a: create_text_file(workspace, a),
            lambda a: preview_create_text_file(workspace, a),
            "创建新文件",
        )
    )
    tools.append(
        Tool(
            "run_tests",
            "运行白名单测试。参数：runner（仅 python_unittest）、path（测试目录）",
            False,
            lambda a: run_tests(workspace, a),
            lambda a: preview_run_tests(workspace, a),
            "执行测试代码",
        )
    )
    return ToolRegistry(tools)
