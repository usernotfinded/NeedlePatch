# Example: Append `# noqa`

## Goal

Add a short import suffix without rewriting the whole line manually.

## Original Code

```python
import llm
```

## Normal Diff

```diff
-import llm
+import llm  # noqa: E402
```

## NeedlePatch Command

```bash
needle append file.py \
  --match "import llm" \
  --text "  # noqa: E402"
```

## Result

```python
import llm  # noqa: E402
```

## When This Can Help

This can be clearer when the edit is only a suffix and the matched text is unique.

## When It Is Not Better

Use a normal diff if several nearby imports are changing or the import line is not unique.
