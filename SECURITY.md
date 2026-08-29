# Security policy

## Supported status

This repository is an experimental prototype. It has not received a professional security audit and should not be used unattended or with sensitive production repositories.

## Data flow

When the model requests `read_file` or `search_text`, selected source content or matching lines may be sent to DeepSeek through the web chat. Audit logs are local JSONL files. Content-bearing fields are redacted and long strings are truncated, but metadata such as paths and tool names remains visible.

Do not expose workspaces containing credentials, private keys, personal data, customer data, proprietary code you are not authorized to transmit, or regulated information.

## Built-in controls

- Filesystem paths are resolved and constrained to the selected workspace.
- Common secret-bearing paths and file extensions are denied.
- Common private-key, GitHub, AWS, Google, Slack, OpenAI-style, and JWT token patterns are blocked before transmission.
- Symbolic-link paths and files larger than the read limit are rejected.
- Writes show a diff or creation preview and require approval.
- Python-file and test execution use fixed argument arrays with `shell=False` and a reduced environment that omits common credential variables.
- There is no arbitrary shell, delete, dependency-install, or network tool.
- Model messages are schema checked and duplicate call IDs are rejected.

These controls are incomplete. Secret detection can miss credentials or produce false positives. Treat model output, skills, source files, webpages, and test output as untrusted data.

## Important residual risks

- Python files and tests are executable local code. They can still read files, write files, or use the network with the permissions of the current OS user. Only approve `run_python_file` or `run_tests` for a workspace you trust.
- `--yes` approves all read-only calls, not just the first path requested. A prompt injection in source text may influence later model requests, although local path and secret rules still apply.
- Secret detection is heuristic and cannot guarantee that every credential or personal datum is recognized.
- Files can change between preview and execution if another process edits the workspace concurrently. Avoid running the agent alongside untrusted writers.

## Reporting a vulnerability

Please open a GitHub security advisory rather than a public issue when a report could expose credentials, bypass details, or user data. Include a minimal reproduction and affected version or commit. Never include real secrets.
