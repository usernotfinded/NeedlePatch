# Example: Toggle A Boolean

## Goal

Change one boolean inside a specific line.

## Original Code

```python
debug_enabled = True
```

## Normal Diff

```diff
-debug_enabled = True
+debug_enabled = False
```

## NeedlePatch Command

```bash
needle replace-inside file.py \
  --within "debug_enabled = True" \
  --old "True" \
  --new "False"
```

## Result

```python
debug_enabled = False
```

## When This Can Help

This can be clearer when the token is generic, such as `True`, and the context makes the target unique.

## When It Is Not Better

Use a normal diff if the surrounding logic also changes or the exact context is unstable.
