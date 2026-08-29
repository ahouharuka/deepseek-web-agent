from __future__ import annotations


REASONING_KEYWORDS = ("修复", "调试", "bug", "测试失败", "根因", "复杂")


def resolve_reasoning(requested: str, skill_names: list[str], task: str) -> bool:
    if requested == "on":
        return True
    if requested == "off":
        return False
    if requested != "auto":
        raise ValueError(f"未知推理模式：{requested}")
    if "python-bugfix" in skill_names:
        return True
    if "code-explainer" in skill_names:
        return False
    folded = task.casefold()
    return any(keyword.casefold() in folded for keyword in REASONING_KEYWORDS)
