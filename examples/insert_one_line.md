# Example: Insert One Line

## Goal

Insert one validation call after a known setup call.

## Original Code

```python
init_config()
run_app()
```

## Normal Diff

```diff
 init_config()
+validate_config()
 run_app()
```

## NeedlePatch Command

```bash
needle insert-after file.py \
  --match "init_config()" \
  --text "validate_config()"
```

## Result

```python
init_config()
validate_config()
run_app()
```

## When This Can Help

This can be clearer when exactly one short line is inserted after a unique anchor.

## When It Is Not Better

Use a normal diff if multiple lines, indentation changes, or surrounding logic changes are involved.
