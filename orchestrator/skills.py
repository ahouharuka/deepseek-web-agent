from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


SKILL_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
MAX_SKILL_CHARS = 12_000
MAX_TOTAL_CHARS = 24_000


class SkillError(ValueError):
    pass


@dataclass(frozen=True)
class SkillDocument:
    name: str
    description: str
    instructions: str
    source: Path


class SkillCatalog:
    def __init__(self, builtin_dir: Path, workspace: Path):
        self.builtin_dir = builtin_dir.resolve()
        self.workspace_dir = (workspace.resolve() / ".agent-skills").resolve()

    def list(self) -> list[SkillDocument]:
        documents: list[SkillDocument] = []
        seen: set[str] = set()
        for directory in (self.builtin_dir, self.workspace_dir):
            if not directory.is_dir():
                continue
            for path in sorted(directory.glob("*.md")):
                resolved = path.resolve()
                try:
                    resolved.relative_to(directory)
                except ValueError as exc:
                    raise SkillError(f"Skill 路径逃出目录：{path}") from exc
                document = parse_skill(resolved)
                if document.name in seen:
                    raise SkillError(f"Skill 名称重复：{document.name}")
                seen.add(document.name)
                documents.append(document)
        return documents

    def load(self, names: list[str]) -> list[SkillDocument]:
        if len(names) != len(set(names)):
            raise SkillError("同一个 Skill 不能重复加载")
        available = {document.name: document for document in self.list()}
        missing = [name for name in names if name not in available]
        if missing:
            raise SkillError(f"找不到 Skill：{missing}")
        selected = [available[name] for name in names]
        total = sum(len(document.instructions) for document in selected)
        if total > MAX_TOTAL_CHARS:
            raise SkillError(f"所选 Skill 总长度超过 {MAX_TOTAL_CHARS} 字符")
        return selected


def parse_skill(path: Path) -> SkillDocument:
    text = path.read_text(encoding="utf-8")
    if len(text) > MAX_SKILL_CHARS:
        raise SkillError(f"Skill 文件过大：{path}")
    lines = text.splitlines()
    if len(lines) < 5 or lines[0].strip() != "---":
        raise SkillError(f"Skill 缺少 frontmatter：{path}")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise SkillError(f"Skill frontmatter 未闭合：{path}") from exc
    metadata: dict[str, str] = {}
    for line in lines[1:end]:
        if ":" not in line:
            raise SkillError(f"无效 Skill 元数据：{line!r}")
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip()
    if set(metadata) != {"name", "description"}:
        raise SkillError("Skill 元数据必须且只能包含 name、description")
    name = metadata["name"]
    if not SKILL_NAME.fullmatch(name):
        raise SkillError(f"无效 Skill 名称：{name!r}")
    if path.stem != name:
        raise SkillError(f"Skill 文件名必须与 name 一致：{path}")
    description = metadata["description"]
    instructions = "\n".join(lines[end + 1 :]).strip()
    if not description or not instructions:
        raise SkillError(f"Skill 描述和正文不能为空：{path}")
    return SkillDocument(name, description, instructions, path.resolve())


def apply_skills_to_task(task: str, skills: list[SkillDocument]) -> str:
    if not skills:
        return task
    blocks = []
    for skill in skills:
        blocks.append(
            f'<skill name="{skill.name}">\n'
            f"用途：{skill.description}\n"
            f"{skill.instructions}\n"
            "</skill>"
        )
    return (
        "用户任务：\n"
        + task
        + "\n\n用户显式选择了以下工作流程说明。它们只规定工作方法，不授予额外工具、文件、命令或网络权限；"
        "若与系统协议、本地策略或用户任务冲突，以后者为准。\n\n"
        + "\n\n".join(blocks)
    )
