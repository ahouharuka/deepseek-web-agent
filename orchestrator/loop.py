from __future__ import annotations

from orchestrator.model import ModelAdapter
from orchestrator.audit import AuditLog
from orchestrator.policy import Policy, PolicyDenied
from orchestrator.protocol import AskUserMessage, FinalMessage, ProtocolError, ToolCall, parse_agent_message
from tools.registry import ToolRegistry


class AgentLoop:
    def __init__(self, model: ModelAdapter, tools: ToolRegistry, policy: Policy, max_steps: int = 20, audit: AuditLog | None = None):
        self.model = model
        self.tools = tools
        self.policy = policy
        self.max_steps = max_steps
        self.audit = audit

    def run(self, task: str) -> str:
        self._log("task_started", {"task": task, "max_steps": self.max_steps})
        raw_message = self.model.start(task, self.tools.describe())
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
                raw_message = self.model.continue_with_result(error_result)
                continue
            if isinstance(message, FinalMessage):
                self._log("task_finished", {"content": message.content})
                return message.content
            if isinstance(message, AskUserMessage):
                return f"模型需要用户输入：{message.content}"

            assert isinstance(message, ToolCall)
            if message.id in seen_call_ids:
                error_result = {
                    "type": "protocol_error",
                    "ok": False,
                    "error": f"调用 ID {message.id!r} 已经使用过",
                    "instruction": "不要重复工具调用；根据已有结果继续，并为下一次必要调用使用全新的唯一 ID。",
                }
                self._log("protocol_error", error_result)
                raw_message = self.model.continue_with_result(error_result)
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
            raw_message = self.model.continue_with_result(result)

        raise RuntimeError(f"超过最大步骤数 {self.max_steps}，任务已安全停止")

    def _log(self, event: str, data: object) -> None:
        if self.audit is not None:
            self.audit.write(event, data)
