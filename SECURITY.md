# Security policy

## Supported status

This repository is an experimental prototype. It has not received a professional security audit and should not be used unattended or with sensitive production repositories.

## Data flow

When the model requests `read_file` or `search_text`, selected source content or matching lines may be sent to DeepSeek through the web chat. Tool results are also written to local JSONL audit logs in plaintext.

Do not expose workspaces containing credentials, private keys, personal data, customer data, proprietary code you are not authorized to transmit, or regulated information.

## Built-in controls

- Filesystem paths are resolved and constrained to the selected workspace.
- Common secret-bearing paths and file extensions are denied.
- A small set of likely token/private-key patterns is blocked before transmission.
- Writes show a diff or creation preview and require approval.
- Test execution uses a fixed argument array with `shell=False`.
- There is no arbitrary shell, delete, dependency-install, or network tool.
- Model messages are schema checked and duplicate call IDs are rejected.

These controls are incomplete. Secret detection can miss credentials or produce false positives. Treat model output, skills, source files, webpages, and test output as untrusted data.

## Reporting a vulnerability

Please open a GitHub security advisory rather than a public issue when a report could expose credentials, bypass details, or user data. Include a minimal reproduction and affected version or commit. Never include real secrets.
