# Release Checklist

Before publishing:

- `python3 -m pip install -r requirements-dev.txt`
- `python3 -m pytest -q`
- `ruff check .`
- `python3 -m pip_audit -r constraints-dev.txt`
- `needle --help`
- `needle --version`
- `python3 benchmarks/compare_micro_edits.py`
- `python3 benchmarks/compare_micro_edits.py --json`
- `git diff --check`
- verify README examples
- verify smoke test
- verify license exists
- verify CHANGELOG is updated
