from __future__ import annotations

import os
import queue
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from adapters.browser_discovery import find_browser_executable
from adapters.deepseek_web import DeepSeekWebModel
from orchestrator.audit import AuditLog
from orchestrator.loop import AgentLoop
from orchestrator.policy import Policy
from orchestrator.reasoning import resolve_reasoning
from orchestrator.skills import SkillCatalog, apply_skills_to_task
from tools.registry import build_coding_registry


APP_NAME = "DeepSeek Web Agent"
STOP = object()


def resource_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def app_data_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    path = base / "DeepSeekWebAgent"
    path.mkdir(parents=True, exist_ok=True)
    return path


class DesktopApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("920x700")
        self.root.minsize(760, 580)
        self.task_queue: queue.Queue[object] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.session_active = False
        self.running_task = False

        self.workspace_var = tk.StringVar()
        self.skill_var = tk.StringVar(value="无")
        self.reasoning_var = tk.StringVar(value="auto")
        self.readonly_var = tk.BooleanVar(value=True)
        self.max_steps_var = tk.IntVar(value=15)
        self.status_var = tk.StringVar(value="请选择项目目录并输入任务。")

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=16)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(4, weight=1)

        ttk.Label(outer, text=APP_NAME, font=("Segoe UI", 18, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(outer, text="DeepSeek 网页负责规划，本地程序在你选择的目录中执行受限操作。", foreground="#555").grid(row=1, column=0, sticky="w", pady=(2, 14))

        settings = ttk.LabelFrame(outer, text="项目与运行设置", padding=12)
        settings.grid(row=2, column=0, sticky="ew")
        settings.columnconfigure(1, weight=1)
        ttk.Label(settings, text="项目目录").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.workspace_entry = ttk.Entry(settings, textvariable=self.workspace_var)
        self.workspace_entry.grid(row=0, column=1, sticky="ew")
        self.browse_button = ttk.Button(settings, text="选择…", command=self._choose_workspace)
        self.browse_button.grid(row=0, column=2, padx=(8, 0))

        options = ttk.Frame(settings)
        options.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        ttk.Label(options, text="工作流程").pack(side="left")
        self.skill_combo = ttk.Combobox(options, textvariable=self.skill_var, values=("无", "code-explainer", "python-bugfix"), state="readonly", width=18)
        self.skill_combo.pack(side="left", padx=(6, 18))
        ttk.Label(options, text="深度思考").pack(side="left")
        self.reasoning_combo = ttk.Combobox(options, textvariable=self.reasoning_var, values=("auto", "on", "off"), state="readonly", width=8)
        self.reasoning_combo.pack(side="left", padx=(6, 18))
        self.readonly_check = ttk.Checkbutton(options, text="自动批准只读操作", variable=self.readonly_var)
        self.readonly_check.pack(side="left", padx=(0, 18))
        ttk.Label(options, text="最大步骤").pack(side="left")
        self.steps_spin = ttk.Spinbox(options, from_=1, to=50, textvariable=self.max_steps_var, width=5)
        self.steps_spin.pack(side="left", padx=(6, 0))

        task_frame = ttk.LabelFrame(outer, text="给 Agent 的指令", padding=12)
        task_frame.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        task_frame.columnconfigure(0, weight=1)
        self.task_text = tk.Text(task_frame, height=5, wrap="word", font=("Segoe UI", 10))
        self.task_text.grid(row=0, column=0, columnspan=3, sticky="ew")
        self.task_text.insert("1.0", "先查看项目目录和必要文件，然后完成任务；修改后请验证结果。")
        self.send_button = ttk.Button(task_frame, text="开始会话并发送", command=self._send_task)
        self.send_button.grid(row=1, column=1, sticky="e", pady=(10, 0))
        self.stop_button = ttk.Button(task_frame, text="结束会话", command=self._stop_session, state="disabled")
        self.stop_button.grid(row=1, column=2, sticky="e", padx=(8, 0), pady=(10, 0))

        output_frame = ttk.LabelFrame(outer, text="运行过程", padding=8)
        output_frame.grid(row=4, column=0, sticky="nsew", pady=(12, 0))
        output_frame.rowconfigure(0, weight=1)
        output_frame.columnconfigure(0, weight=1)
        self.output = scrolledtext.ScrolledText(output_frame, state="disabled", wrap="word", font=("Consolas", 10))
        self.output.grid(row=0, column=0, sticky="nsew")
        ttk.Label(outer, textvariable=self.status_var).grid(row=5, column=0, sticky="w", pady=(8, 0))

    def _choose_workspace(self) -> None:
        selected = filedialog.askdirectory(title="选择 Agent 可以访问的项目目录")
        if selected:
            self.workspace_var.set(selected)

    def _send_task(self) -> None:
        task = self.task_text.get("1.0", "end").strip()
        if not task:
            messagebox.showwarning(APP_NAME, "请输入任务。")
            return
        if not self.session_active:
            workspace = Path(self.workspace_var.get().strip()).expanduser()
            if not workspace.is_dir():
                messagebox.showerror(APP_NAME, "请选择一个已有的项目目录。")
                return
            try:
                max_steps = int(self.max_steps_var.get())
            except (TypeError, ValueError):
                messagebox.showerror(APP_NAME, "最大步骤必须是 1 到 50 的整数。")
                return
            if not 1 <= max_steps <= 50:
                messagebox.showerror(APP_NAME, "最大步骤必须是 1 到 50。")
                return
            config = {
                "workspace": workspace.resolve(),
                "skill": None if self.skill_var.get() == "无" else self.skill_var.get(),
                "reasoning": self.reasoning_var.get(),
                "readonly": self.readonly_var.get(),
                "max_steps": max_steps,
            }
            self.session_active = True
            self._lock_settings(True)
            self.worker = threading.Thread(target=self._session_worker, args=(config,), daemon=True)
            self.worker.start()
        if self.running_task:
            messagebox.showinfo(APP_NAME, "当前任务仍在运行，请等待完成或回答弹窗中的问题。")
            return
        self.running_task = True
        self.status_var.set("任务已提交，正在等待 DeepSeek…")
        self._append(f"\n你：{task}\n")
        self.task_queue.put(task)
        self.task_text.delete("1.0", "end")

    def _session_worker(self, config: dict[str, object]) -> None:
        workspace = config["workspace"]
        assert isinstance(workspace, Path)
        try:
            skill_names = [config["skill"]] if config["skill"] else []
            catalog = SkillCatalog(resource_root() / "agent_skills", workspace)
            skills = catalog.load(skill_names)
            browser = find_browser_executable()
            state = app_data_dir()
            audit = AuditLog(state / "logs")
            tools = build_coding_registry(workspace)
            policy = Policy(
                workspace,
                auto_approve_readonly=bool(config["readonly"]),
                approver=self._approve_tool,
            )
            first_task = self.task_queue.get()
            if first_task is STOP:
                return
            assert isinstance(first_task, str)
            reasoning = resolve_reasoning(str(config["reasoning"]), skill_names, first_task)
            self._append_from_worker("正在打开专用浏览器。首次使用时，请在浏览器中登录 DeepSeek。\n")
            with DeepSeekWebModel(
                state / "browser-profile",
                browser,
                timeout_ms=240_000 if reasoning else 120_000,
                reasoning=reasoning,
            ) as model:
                task: object = first_task
                while task is not STOP:
                    assert isinstance(task, str)
                    try:
                        prepared = apply_skills_to_task(task, skills)
                        result = AgentLoop(
                            model,
                            tools,
                            policy,
                            max_steps=int(config["max_steps"]),
                            audit=audit,
                            user_input=self._ask_user,
                        ).run(prepared)
                        self._append_from_worker(f"\nAgent：{result}\n")
                        self.root.after(0, self._task_finished)
                    except Exception as exc:
                        self._append_from_worker(f"\n错误：{type(exc).__name__}: {exc}\n")
                        self.root.after(0, self._task_finished)
                    task = self.task_queue.get()
        except Exception as exc:
            self._append_from_worker(f"\n无法启动会话：{type(exc).__name__}: {exc}\n")
        finally:
            self.root.after(0, self._session_stopped)

    def _approve_tool(self, call, readonly: bool, preview: str | None, label: str) -> bool:
        warning = ""
        if call.tool in {"run_tests", "run_python_file"}:
            warning = "\n\n安全提示：即将运行项目中的本机代码，它可能访问文件或网络。"
        details = preview or f"参数：{call.arguments}"
        return bool(self._sync_ui(lambda: self._approval_dialog(f"是否允许：{label}？", details + warning)))

    def _approval_dialog(self, title: str, details: str) -> bool:
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry("720x480")
        dialog.transient(self.root)
        dialog.grab_set()
        result = {"value": False}
        ttk.Label(dialog, text=title, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=14, pady=(14, 8))
        text = scrolledtext.ScrolledText(dialog, wrap="none", font=("Consolas", 9))
        text.pack(fill="both", expand=True, padx=14)
        text.insert("1.0", details)
        text.configure(state="disabled")
        buttons = ttk.Frame(dialog)
        buttons.pack(fill="x", padx=14, pady=14)
        def finish(value: bool) -> None:
            result["value"] = value
            dialog.destroy()
        ttk.Button(buttons, text="拒绝", command=lambda: finish(False)).pack(side="right")
        ttk.Button(buttons, text="允许", command=lambda: finish(True)).pack(side="right", padx=(0, 8))
        dialog.protocol("WM_DELETE_WINDOW", lambda: finish(False))
        self.root.wait_window(dialog)
        return result["value"]

    def _ask_user(self, prompt: str) -> str:
        return str(self._sync_ui(lambda: self._text_question(prompt)))

    def _text_question(self, prompt: str) -> str:
        dialog = tk.Toplevel(self.root)
        dialog.title("Agent 需要你的回答")
        dialog.geometry("620x300")
        dialog.transient(self.root)
        dialog.grab_set()
        ttk.Label(dialog, text=prompt, wraplength=580, justify="left").pack(fill="x", padx=16, pady=(16, 10))
        entry = tk.Text(dialog, height=6, wrap="word")
        entry.pack(fill="both", expand=True, padx=16)
        result = {"value": ""}
        def submit() -> None:
            result["value"] = entry.get("1.0", "end").strip()
            dialog.destroy()
        ttk.Button(dialog, text="提交回答", command=submit).pack(anchor="e", padx=16, pady=14)
        dialog.protocol("WM_DELETE_WINDOW", submit)
        self.root.wait_window(dialog)
        return result["value"]

    def _sync_ui(self, callback):
        done = threading.Event()
        box = {}
        def run():
            try:
                box["value"] = callback()
            finally:
                done.set()
        self.root.after(0, run)
        done.wait()
        return box.get("value")

    def _append(self, text: str) -> None:
        self.output.configure(state="normal")
        self.output.insert("end", text)
        self.output.see("end")
        self.output.configure(state="disabled")

    def _append_from_worker(self, text: str) -> None:
        self.root.after(0, lambda: self._append(text))

    def _task_finished(self) -> None:
        self.running_task = False
        self.status_var.set("任务结束。可以继续输入下一项任务，或结束会话。")
        self.send_button.configure(text="发送下一项任务")

    def _stop_session(self) -> None:
        if self.running_task:
            messagebox.showinfo(APP_NAME, "当前任务完成后会结束会话。")
        self.task_queue.put(STOP)
        self.status_var.set("正在结束会话…")

    def _session_stopped(self) -> None:
        while True:
            try:
                self.task_queue.get_nowait()
            except queue.Empty:
                break
        self.session_active = False
        self.running_task = False
        self._lock_settings(False)
        self.status_var.set("会话已结束。")
        self.send_button.configure(text="开始会话并发送")

    def _lock_settings(self, locked: bool) -> None:
        state = "disabled" if locked else "normal"
        self.workspace_entry.configure(state=state)
        self.browse_button.configure(state=state)
        self.skill_combo.configure(state="disabled" if locked else "readonly")
        self.reasoning_combo.configure(state="disabled" if locked else "readonly")
        self.readonly_check.configure(state=state)
        self.steps_spin.configure(state=state)
        self.stop_button.configure(state="normal" if locked else "disabled")

    def _on_close(self) -> None:
        if self.session_active and not messagebox.askyesno(APP_NAME, "关闭窗口会结束当前会话，确定吗？"):
            return
        self.task_queue.put(STOP)
        self.root.destroy()


def main() -> int:
    root = tk.Tk()
    try:
        ttk.Style(root).theme_use("vista" if sys.platform == "win32" else "clam")
    except tk.TclError:
        pass
    DesktopApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
