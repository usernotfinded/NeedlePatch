# Example: Replace A Tuple Item

## Goal

Change one tuple value inside a unique loop header.

## Original Code

```python
for hie_lite_enabled in (False, True):
    run_case(hie_lite_enabled)
```

## Normal Diff

```diff
-for hie_lite_enabled in (False, True):
+for hie_lite_enabled in (False,):
     run_case(hie_lite_enabled)
```

## NeedlePatch Command

```bash
needle replace-inside file.py \
  --within "for hie_lite_enabled in (False, True):" \
  --old "(False, True)" \
  --new "(False,)"
```

## Result

```python
for hie_lite_enabled in (False,):
    run_case(hie_lite_enabled)
```

## When This Can Help

This can be useful when only one tuple element changes and the full line is unique.

## When It Is Not Better

Use a normal diff if the loop body or nearby control flow also changes.
