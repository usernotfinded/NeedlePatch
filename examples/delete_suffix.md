# Example: Delete A Suffix

## Goal

Remove one exact suffix from a specific line.

## Original Code

```python
import llm  # noqa: E402
```

## Normal Diff

```diff
-import llm  # noqa: E402
+import llm
```

## NeedlePatch Command

```bash
needle delete file.py \
  --within "import llm  # noqa: E402" \
  --text "  # noqa: E402"
```

## Result

```python
import llm
```

## When This Can Help

This can be more scoped than deleting a generic suffix globally because `--within` limits the edit to one exact context.

## When It Is Not Better

Use a normal diff if many suffixes are being removed or the surrounding import block is changing.
