from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from orchestrator.protocol import ToolCall


class PolicyDenied(RuntimeError):
    pass


@dataclass(frozen=True)
class Policy:
    workspace: Path
    auto_approve_readonly: bool = False

    def authorize(
        self,
        call: ToolCall,
        readonly: bool,
        preview: str | None = None,
        approval_label: str = "执行高风险工具",
    ) -> None:
        if readonly and self.auto_approve_readonly:
            return
        if readonly:
            prompt = f"允许只读工具 {call.tool} 执行参数 {call.arguments}？[y/N] "
        else:
            print(f"\n即将{approval_label}，预览：")
            print(preview or "（无可用预览）")
            if call.tool in {"run_tests", "run_python_file"}:
                print("安全提示：即将运行工作区中的本机代码；即使命令固定，它仍可能访问文件或网络。仅运行你信任的工作区。")
            prompt = f"允许工具 {call.tool} {approval_label}？[y/N] "
        answer = input(prompt)
        if answer.strip().lower() not in {"y", "yes"}:
            raise PolicyDenied("用户拒绝了工具调用")
