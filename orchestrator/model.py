from __future__ import annotations

from typing import Any, Protocol


class ModelAdapter(Protocol):
    def start(self, task: str, tool_descriptions: list[dict[str, Any]]) -> object: ...

    def continue_with_result(self, result: dict[str, Any]) -> object: ...


class DemoModel:
    """A deterministic adapter used to test the orchestration loop."""

    def __init__(self) -> None:
        self._started = False

    def start(self, task: str, tool_descriptions: list[dict[str, Any]]) -> object:
        self._started = True
        return {
            "type": "tool_call",
            "id": "demo_001",
            "tool": "list_files",
            "arguments": {"path": ".", "recursive": False},
        }

    def continue_with_result(self, result: dict[str, Any]) -> object:
        if not self._started:
            raise RuntimeError("DemoModel 尚未开始任务")
        if result.get("ok"):
            count = len(result.get("content", []))
            return {"type": "final", "content": f"已成功读取工作区，共发现 {count} 个条目。"}
        return {"type": "final", "content": f"工具执行失败：{result.get('error', '未知错误')}"}
