# Contributing

Thanks for helping test NeedlePatch. Please keep changes small and grounded in real micro-edit cases.

## Local checks

Run tests with:

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pytest -q
ruff check .
python3 -m pip_audit -r constraints-dev.txt
```

## Guidelines

- Keep runtime dependencies at zero unless strongly justified.
- Do not add new commands without real-world examples.
- Do not add AST, LSP, regex, server behavior, plugins, aliases, config files, or backup systems without opening a discussion first.
- Preserve the exact-match and unique-match safety model.
- Keep claims conservative: NeedlePatch is useful only for some tiny edits, not as a replacement for normal diffs or `apply_patch`.
