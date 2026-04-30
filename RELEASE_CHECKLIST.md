# Release Checklist

Before publishing:

- `python3 -m pip install -e '.[dev]'`
- `python3 -m pytest`
- `needle --help`
- `needle --version`
- `python3 benchmarks/compare_micro_edits.py`
- `python3 benchmarks/compare_micro_edits.py --json`
- `git diff --check`
- verify README examples
- verify smoke test
- verify license exists
- verify CHANGELOG is updated
