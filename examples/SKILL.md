# NeedlePatch Skill

Use NeedlePatch for tiny exact text edits by shell command.

## When To Use

- One boolean, number, or string change.
- One token inside a known context.
- One tuple/list item edit.
- One suffix such as `# noqa`.
- One short inserted line.
- One exact token or suffix deletion.

## When Not To Use

- Refactors.
- Large patches.
- Function rewrites.
- Formatting.
- Multi-file edits.
- Semantic changes that need AST, LSP, or type analysis.

## Safety Rule

```text
0 matches  -> fail
1 match    -> edit
2+ matches -> fail
```

NeedlePatch should fail instead of guessing.

## Examples

```bash
needle replace-inside file.py \
  --within "debug_enabled = True" \
  --old "True" \
  --new "False"
```

```bash
needle append file.py \
  --match "import llm" \
  --text "  # noqa: E402"
```

```bash
needle insert-after file.py \
  --match "init_config()" \
  --text "validate_config()"
```

```bash
needle delete file.py \
  --within "import llm  # noqa: E402" \
  --text "  # noqa: E402"
```

After using NeedlePatch, run:

```bash
git diff
```
