from __future__ import annotations

import argparse
import sys
from pathlib import Path

from orchestrator.loop import AgentLoop
from orchestrator.audit import AuditLog
from orchestrator.model import DemoModel
from orchestrator.policy import Policy
from orchestrator.skills import SkillCatalog, SkillError, apply_skills_to_task
from orchestrator.reasoning import resolve_reasoning
from tools.registry import build_coding_registry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="安全的本地 Agent 编排器")
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--demo", action="store_true", help="使用内置模拟模型跑通闭环")
    parser.add_argument("--web", action="store_true", help="通过独立浏览器连接 DeepSeek 网页")
    parser.add_argument("--browser", type=Path, help="Chrome 或 Edge 可执行文件路径")
    parser.add_argument("--keep-browser-open", action="store_true", help="任务结束后等待按 Enter 再关闭浏览器")
    parser.add_argument("--yes", action="store_true", help="自动批准只读工具调用")
    parser.add_argument("--skill", action="append", default=[], help="加载一个已注册 Skill，可重复指定")
    parser.add_argument("--list-skills", action="store_true", help="列出当前可用 Skill 后退出")
    parser.add_argument("--max-steps", type=int, default=10, help="最大 Agent 步骤数，范围 1-50")
    parser.add_argument("--reasoning", choices=("off", "on", "auto"), default="auto", help="DeepSeek 深度思考模式")
    parser.add_argument("task", nargs="?", default="列出工作区中的文件，然后简要报告。")
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    args = parse_args()
    workspace = args.workspace.resolve()
    if not 1 <= args.max_steps <= 50:
        raise SystemExit("--max-steps 必须在 1 到 50 之间")
    catalog = SkillCatalog(Path(__file__).resolve().parent / "agent_skills", workspace)
    try:
        if args.list_skills:
            for skill in catalog.list():
                print(f"{skill.name}: {skill.description} [{skill.source}]")
            return 0
        selected_skills = catalog.load(args.skill)
    except SkillError as exc:
        raise SystemExit(str(exc)) from exc
    task = apply_skills_to_task(args.task, selected_skills)
    reasoning = resolve_reasoning(args.reasoning, [skill.name for skill in selected_skills], args.task)
    policy = Policy(workspace=workspace, auto_approve_readonly=args.yes)
    tools = build_coding_registry(workspace)
    audit = AuditLog(Path("logs"))
    audit.write(
        "runtime_config",
        {
            "workspace": str(workspace),
            "skills": [skill.name for skill in selected_skills],
            "reasoning": reasoning,
            "max_steps": args.max_steps,
        },
    )
    if args.demo:
        result = AgentLoop(DemoModel(), tools, policy, max_steps=args.max_steps, audit=audit).run(task)
    elif args.web:
        from adapters.browser_discovery import find_browser_executable
        from adapters.deepseek_web import DeepSeekWebModel

        try:
            browser = find_browser_executable(args.browser)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        with DeepSeekWebModel(
            Path(".browser-profile"),
            browser,
            timeout_ms=240_000 if reasoning else 120_000,
            keep_open=args.keep_browser_open,
            reasoning=reasoning,
        ) as model:
            result = AgentLoop(model, tools, policy, max_steps=args.max_steps, audit=audit).run(task)
    else:
        raise SystemExit("请选择 --demo 或 --web")
    print(result)
    print(f"深度思考：{'开启' if reasoning else '关闭'}")
    print(f"审计日志：{audit.path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
