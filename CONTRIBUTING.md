# Contributing

Thank you for improving DeepSeek Web Agent.

## Development setup

```bash
python -m venv .venv
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

## Pull requests

- Keep changes narrowly scoped.
- Add tests for protocol, policy, path, tool, and browser-adapter changes.
- Never commit `.browser-profile`, logs, credentials, or real user/project data.
- Preserve the rule that model instructions cannot expand local permissions.
- Avoid arbitrary shell execution; new runners must construct fixed argument arrays and use `shell=False`.
- Document user-visible flags and security implications.

Browser UI changes should document the accessibility or DOM signal used by the adapter and fail safely when that signal is absent.
