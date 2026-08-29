from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


class ProtocolError(ValueError):
    pass


@dataclass(frozen=True)
class ToolCall:
    type: Literal["tool_call"]
    id: str
    tool: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class FinalMessage:
    type: Literal["final"]
    content: str


@dataclass(frozen=True)
class AskUserMessage:
    type: Literal["ask_user"]
    content: str


AgentMessage = ToolCall | FinalMessage | AskUserMessage


def parse_agent_message(value: object) -> AgentMessage:
    if not isinstance(value, dict):
        raise ProtocolError("模型消息必须是 JSON 对象")

    message_type = value.get("type")
    if message_type == "tool_call":
        expected = {"type", "id", "tool", "arguments"}
        _require_exact_keys(value, expected)
        call_id = _nonempty_string(value["id"], "id")
        tool = _nonempty_string(value["tool"], "tool")
        arguments = value["arguments"]
        if not isinstance(arguments, dict):
            raise ProtocolError("arguments 必须是对象")
        return ToolCall(type="tool_call", id=call_id, tool=tool, arguments=arguments)

    if message_type in {"final", "ask_user"}:
        _require_exact_keys(value, {"type", "content"})
        content = _nonempty_string(value["content"], "content")
        if message_type == "final":
            return FinalMessage(type="final", content=content)
        return AskUserMessage(type="ask_user", content=content)

    raise ProtocolError(f"未知消息类型: {message_type!r}")


def _require_exact_keys(value: dict[str, Any], expected: set[str]) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ProtocolError(f"字段不匹配；缺少={missing}，多余={extra}")


def _nonempty_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProtocolError(f"{field} 必须是非空字符串")
    return value.strip()
