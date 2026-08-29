from __future__ import annotations

from collections.abc import Callable

from orchestrator.model import ModelAdapter
from orchestrator.audit import AuditLog
from orchestrator.policy import Policy, PolicyDenied
from orchestrator.protocol import AskUserMessage, FinalMessage, ProtocolError, ToolCall, parse_agent_message
from tools.registry import ToolRegistry


class AgentLoop:
    def __init__(
        self,
        model: ModelAdapter,
        tools: ToolRegistry,
        policy: Policy,
        max_steps: int = 20,
        audit: AuditLog | None = None,
        user_input: Callable[[str], str] = input,
    ):
        self.model = model
        self.tools = tools
        self.policy = policy
        self.max_steps = max_steps
        self.audit = audit
        self.user_input = user_input

    def run(self, task: str) -> str:
        self._log("task_started", {"task": task, "max_steps": self.max_steps})
        try:
            raw_message = self.model.start(task, self.tools.describe())
        except Exception as exc:
            self._log("model_error", {"stage": "start", "error_type": type(exc).__name__, "error": str(exc)})
            raise
        seen_call_ids: set[str] = set()
        consecutive_protocol_errors = 0

        for _ in range(self.max_steps):
            self._log("model_message", raw_message)
            try:
                message = parse_agent_message(raw_message)
                consecutive_protocol_errors = 0
            except ProtocolError as exc:
                consecutive_protocol_errors += 1
                error_result = {
                    "type": "protocol_error",
                    "ok": False,
                    "error": str(exc),
                    "instruction": "不要执行任何动作；仅按规定的 tool_call、final 或 ask_user 格式重写上一条消息。",
                }
                self._log("protocol_error", error_result)
                if consecutive_protocol_errors > 2:
                    raise RuntimeError("模型连续三次违反消息协议，任务已安全停止") from exc
                raw_message = self._continue_model(error_result)
                continue
            if isinstance(message, FinalMessage):
                self._log("task_finished", {"content": message.content})
                return message.content
            if isinstance(message, AskUserMessage):
                print(f"\nAgent 需要你的补充信息：\n{message.content}")
                answer = self.user_input("你的回复：")
                user_result = {
                    "type": "user_response",
                    "question": message.content,
                    "answer": answer,
                }
                self._log("user_response", user_result)
                raw_message = self._continue_model(user_result)
                continue

            assert isinstance(message, ToolCall)
            if message.id in seen_call_ids:
                error_result = {
                    "type": "protocol_error",
                    "ok": False,
                    "error": f"调用 ID {message.id!r} 已经使用过",
                    "instruction": "不要重复工具调用；根据已有结果继续，并为下一次必要调用使用全新的唯一 ID。",
                }
                self._log("protocol_error", error_result)
                raw_message = self._continue_model(error_result)
                continue
            seen_call_ids.add(message.id)

            try:
                tool = self.tools.get(message.tool)
                preview = tool.preview(message.arguments) if tool.preview is not None else None
                self.policy.authorize(
                    message,
                    readonly=tool.readonly,
                    preview=preview,
                    approval_label=tool.approval_label,
                )
                content = tool.execute(message.arguments)
                result = {"type": "tool_result", "id": message.id, "ok": True, "content": content}
            except (KeyError, ValueError, OSError, PolicyDenied) as exc:
                result = {"type": "tool_result", "id": message.id, "ok": False, "error": str(exc)}

            self._log("tool_result", result)
            raw_message = self._continue_model(result)

        raise RuntimeError(f"超过最大步骤数 {self.max_steps}，任务已安全停止")

    def _log(self, event: str, data: object) -> None:
        if self.audit is not None:
            self.audit.write(event, data)

    def _continue_model(self, result: dict[str, object]) -> object:
        try:
            return self.model.continue_with_result(result)
        except Exception as exc:
            self._log(
                "model_error",
                {"stage": "continue", "error_type": type(exc).__name__, "error": str(exc)},
            )
            raise
