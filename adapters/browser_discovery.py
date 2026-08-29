from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def find_browser_executable(explicit: Path | None = None) -> Path:
    if explicit is not None:
        candidate = explicit.expanduser().resolve()
        if candidate.is_file():
            return candidate
        raise ValueError(f"找不到指定浏览器：{candidate}")

    candidates: list[Path] = []
    configured = os.environ.get("DEEPSEEK_AGENT_BROWSER")
    if configured:
        candidates.append(Path(configured).expanduser())

    for command in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge"):
        resolved = shutil.which(command)
        if resolved:
            candidates.append(Path(resolved))

    if sys.platform == "win32":
        candidates.extend(
            [
                Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
                Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
                Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
            ]
        )
    elif sys.platform == "darwin":
        candidates.extend(
            [
                Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
                Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
            ]
        )

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise ValueError("未找到 Chrome/Edge；请使用 --browser 或 DEEPSEEK_AGENT_BROWSER 指定可执行文件")
