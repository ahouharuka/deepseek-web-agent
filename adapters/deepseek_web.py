from __future__ import annotations

import json
import secrets
import time
from pathlib import Path
from typing import Any

from orchestrator.prompts import build_initial_prompt, build_result_prompt


class DeepSeekWebError(RuntimeError):
    pass


class DeepSeekWebModel:
    """Drive DeepSeek's web UI through a dedicated local browser profile."""

    URL = "https://chat.deepseek.com/"
    INPUT_PLACEHOLDER = "给 DeepSeek 发送消息"

    def __init__(
        self,
        profile_dir: Path,
        browser_executable: Path,
        timeout_ms: int = 120_000,
        keep_open: bool = False,
        reasoning: bool = False,
    ):
        self.profile_dir = profile_dir.resolve()
        self.browser_executable = browser_executable.resolve()
        self.timeout_ms = timeout_ms
        self.keep_open = keep_open
        self.reasoning = reasoning
        self._playwright = None
        self._context = None
        self._page = None
        self._seen_response_texts: set[str] = set()

    def __enter__(self) -> "DeepSeekWebModel":
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise DeepSeekWebError("缺少 Playwright；请先安装 requirements.txt") from exc

        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = sync_playwright().start()
        self._context = self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.profile_dir),
            executable_path=str(self.browser_executable),
            headless=False,
            viewport={"width": 1200, "height": 850},
        )
        self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
        self._page.goto(self.URL, wait_until="domcontentloaded", timeout=self.timeout_ms)
        self._wait_for_chat_input()
        self._configure_reasoning()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self.keep_open and self._page is not None:
            input("任务已结束；按 Enter 关闭独立浏览器。")
        if self._context is not None:
            self._context.close()
        if self._playwright is not None:
            self._playwright.stop()

    def start(self, task: str, tool_descriptions: list[dict[str, Any]]) -> object:
        return self._send_and_parse(build_initial_prompt(task, tool_descriptions))

    def continue_with_result(self, result: dict[str, Any]) -> object:
        return self._send_and_parse(build_result_prompt(result))

    def _wait_for_chat_input(self) -> None:
        assert self._page is not None
        locator = self._page.get_by_placeholder(self.INPUT_PLACEHOLDER, exact=False)
        try:
            locator.wait_for(state="visible", timeout=10_000)
        except Exception:
            print("请在打开的浏览器窗口中登录 DeepSeek；登录后程序会自动继续。")
            locator.wait_for(state="visible", timeout=300_000)

    def _configure_reasoning(self) -> None:
        assert self._page is not None
        label = self._page.get_by_text("深度思考", exact=True)
        if label.count() != 1:
            raise DeepSeekWebError("无法唯一定位 DeepSeek 的“深度思考”开关")
        toggle = label.locator("xpath=..")
        current = toggle.get_attribute("aria-pressed")
        desired = "true" if self.reasoning else "false"
        if current not in {"true", "false"}:
            raise DeepSeekWebError("无法读取“深度思考”开关状态")
        if current != desired:
            toggle.click()
            self._page.wait_for_timeout(300)
            if toggle.get_attribute("aria-pressed") != desired:
                raise DeepSeekWebError("“深度思考”开关未切换到请求的状态")

    def _send_and_parse(self, prompt: str) -> object:
        turn_token = secrets.token_hex(12)
        marked_prompt = _with_turn_marker(prompt, turn_token)
        text = self._send_and_wait(marked_prompt, turn_token)
        try:
            return parse_marked_json_response(text, turn_token)
        except DeepSeekWebError as first_error:
            repair_token = secrets.token_hex(12)
            repair_prompt = (
                "你上一条回复不是有效 JSON。不要改变语义，不要重新执行或重复声称执行工具；"
                "只把上一条回复改写成一个语法正确的 JSON 对象，字符串内部的双引号必须转义。"
                "必须放在一个 ```json 代码块中，代码块外禁止额外文字。\n\n上一条回复：\n" + text
            )
            repaired = self._send_and_wait(_with_turn_marker(repair_prompt, repair_token), repair_token)
            try:
                return parse_marked_json_response(repaired, repair_token)
            except DeepSeekWebError as second_error:
                raise DeepSeekWebError("DeepSeek 连续两次返回无效 JSON，任务已停止") from second_error

    def _send_and_wait(self, prompt: str, turn_token: str) -> str:
        assert self._page is not None
        input_box = self._page.get_by_placeholder(self.INPUT_PLACEHOLDER, exact=False)
        response_locator = self._page.locator("p, pre")
        visible_before = {
            text.strip() for text in response_locator.all_inner_texts() if _looks_like_json(text)
        }
        self._seen_response_texts.update(visible_before)
        input_box.fill(prompt)
        input_box.press("Enter")
        self._page.wait_for_timeout(500)
        if input_box.input_value().strip():
            buttons = input_box.locator("xpath=..").get_by_role("button")
            if buttons.count() == 0:
                raise DeepSeekWebError("消息未提交，而且无法定位发送按钮")
            buttons.last.click()

        deadline = time.monotonic() + self.timeout_ms / 1000
        last_text = ""
        stable_since = time.monotonic()
        while time.monotonic() < deadline:
            text = select_new_json_candidate(
                response_locator.all_inner_texts(), self._seen_response_texts, turn_token
            )
            if text and text != last_text:
                last_text = text
                stable_since = time.monotonic()
            elif text and time.monotonic() - stable_since >= 1.5:
                self._seen_response_texts.add(text)
                return text
            time.sleep(0.25)
        raise DeepSeekWebError("等待 DeepSeek 回复超时")


def parse_json_response(text: str) -> object:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            stripped = "\n".join(lines[1:-1])
            if stripped.lstrip().startswith("json"):
                stripped = stripped.lstrip()[4:].lstrip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise DeepSeekWebError(f"DeepSeek 回复不是有效 JSON：{text[:300]}") from exc


def select_new_json_candidate(texts: list[str], baseline: set[str], turn_token: str | None = None) -> str:
    for text in reversed(texts):
        stripped = text.strip()
        marker_matches = turn_token is None or turn_token in stripped
        if _looks_like_json(stripped) and stripped not in baseline and marker_matches:
            return stripped
    return ""


def parse_marked_json_response(text: str, expected_turn: str) -> object:
    value = parse_json_response(text)
    if not isinstance(value, dict) or value.get("_turn") != expected_turn:
        raise DeepSeekWebError("DeepSeek 回复缺少当前回合标识")
    cleaned = dict(value)
    del cleaned["_turn"]
    return cleaned


def _with_turn_marker(prompt: str, turn_token: str) -> str:
    return (
        prompt
        + "\n\n本轮唯一标识为 "
        + turn_token
        + "。你输出的 JSON 对象必须额外包含字段 \"_turn\":\""
        + turn_token
        + "\"。这是本轮回复的一部分，不得省略或改写。"
    )


def _looks_like_json(text: str) -> bool:
    stripped = text.strip()
    return stripped.startswith("{") or stripped.startswith("```json") or stripped.startswith("```\n{")
