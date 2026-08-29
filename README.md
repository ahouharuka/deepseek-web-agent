# DeepSeek Web Agent

An experimental, human-supervised coding agent that uses the DeepSeek web chat as its planning model and executes a small, policy-controlled toolset locally.

> [!WARNING]
> This is an unofficial research prototype, not affiliated with or endorsed by DeepSeek. It automates the public web interface, which may change without notice. Review the [security model](SECURITY.md) before using it with real code.

[中文说明](README.zh-CN.md)

## Where do I type the instruction?

Put the instruction at the end of the terminal command, inside quotes:

```bash
python main.py --web --workspace "/path/to/your/project" --yes "Explain this project. Do not modify files."
```

You do not need to paste it into DeepSeek yourself. The program opens a dedicated browser, sends the instruction, handles the JSON tool loop, and prints the final answer in the terminal. When a write or test run is requested, review the terminal preview and type `y` to approve it.

## What it does

```text
Your task
  -> local orchestrator sends tool definitions to DeepSeek Web
  -> DeepSeek returns one JSON tool request
  -> local policy validates the request
  -> a local tool runs inside the selected workspace
  -> the result is returned to DeepSeek
  -> repeat until DeepSeek returns final
```

The Python process is the agent runtime. No second local language model, Codex, or Claude Code is required.

Current tools:

- List directories, read UTF-8 text, search text, inspect file metadata.
- Replace one verified line or one uniquely matching text block.
- Create a new text file without overwriting an existing file.
- Run a fixed `python -m unittest discover` command without a shell.
- Load explicit reusable workflow skills.
- Toggle DeepSeek's **Deep Think** mode with `off`, `on`, or `auto`.

Writes and test execution require interactive approval. Read-only calls can be pre-approved with `--yes`.

## Requirements

- Python 3.11+
- Google Chrome or Microsoft Edge
- A DeepSeek web account
- Windows, macOS, or Linux (Windows is the most tested platform)

## Quick start

```bash
git clone https://github.com/ahouharuka/deepseek-web-agent.git
cd deepseek-web-agent
python -m venv .venv
```

Activate the environment and install dependencies:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

```bash
# macOS / Linux
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Run the unit tests and safe offline demo:

```bash
python -m unittest discover -s tests -v
python main.py --demo --workspace acceptance_project --yes
```

Run against DeepSeek Web:

```bash
python main.py --web --workspace /absolute/path/to/project --yes \
  "Explain this project. Stay read-only."
```

On first use, a dedicated browser profile opens. Sign in to DeepSeek in that window and leave it open; the agent continues after it detects the chat input.

## Common examples

Explain a project using a reusable skill:

```bash
python main.py --web --workspace /path/to/project --yes \
  --skill code-explainer \
  "Explain the entry points, modules, data flow, and tests."
```

Repair a Python unit-test failure:

```bash
python main.py --web --workspace /path/to/project --yes \
  --skill python-bugfix --reasoning auto --max-steps 20 \
  "Fix the failing tests. Do not modify tests. Use the smallest source patch and verify it."
```

Keep the dedicated browser open with `--keep-browser-open`. If discovery fails, pass `--browser /path/to/chrome` or set `DEEPSEEK_AGENT_BROWSER`.

## Skills and reasoning

```bash
python main.py --workspace /path/to/project --list-skills
```

Built-in skills live in `agent_skills/`. A workspace may provide `.agent-skills/<name>.md`. Skills are never loaded automatically and cannot grant tools, expand the workspace, bypass approval, or change local policy.

- `--reasoning off`: disable Deep Think.
- `--reasoning on`: enable Deep Think.
- `--reasoning auto`: enable it for `python-bugfix` and bug/debug tasks; disable it for simple reads and `code-explainer`.

## Security model

The workspace passed to `--workspace` is the filesystem boundary. Resolved paths outside it are rejected. The agent hides or denies common sensitive locations, `.env` files, key/certificate extensions, and several likely token/private-key patterns.

This is defense in depth, not a complete secret scanner. Source files successfully read by a tool are sent to DeepSeek through the web chat. Audit logs redact content-bearing fields but retain paths and tool metadata. Use a narrowly scoped, non-sensitive workspace.

See [SECURITY.md](SECURITY.md) for the threat model.

## Current limitations

- Only Python `unittest` is supported; there is no arbitrary shell tool.
- No delete, move, rename, dependency install, Git mutation, or network tool.
- Text reading expects UTF-8.
- Web selectors can break when DeepSeek changes its UI.
- Tasks cannot yet resume after a process restart.
- This prototype is not suitable for unattended use or sensitive production repositories.

## Audit logs

Every run writes JSON Lines records under `logs/`. Source-bearing fields are redacted and long values are truncated, while paths and tool metadata remain available for review. Protect or delete logs according to your retention policy. The directory is ignored by Git.

## Development

```bash
python -m unittest discover -s tests -v
```

Contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

## License

[MIT](LICENSE)
