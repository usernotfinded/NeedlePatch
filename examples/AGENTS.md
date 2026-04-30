# NeedlePatch Agent Instructions

NeedlePatch is for tiny, exact text edits only. Use it when the intended change is 1-2 lines and the target text can be matched exactly.

## Use NeedlePatch For

- Changing one boolean, number, or string.
- Editing one tuple, list, or array item.
- Adding a suffix such as `# noqa` or `# type: ignore`.
- Inserting one short line after a known anchor.
- Deleting one exact token, suffix, or line.

## Do Not Use NeedlePatch For

- Refactors.
- Large patches.
- Function rewrites.
- Formatting entire files.
- Multi-file edits.
- Changes that require AST, type, or semantic analysis.

Use normal diffs or `apply_patch` for larger changes.

## Command Choices

- Prefer `needle replace-inside` for token-level changes inside a known context.
- Prefer `needle append` for suffixes such as `# noqa`.
- Prefer `needle insert-after` for one short inserted line.
- Prefer `needle delete --within` for safe deletion inside a known context.

## Safety Workflow

1. Inspect exact text first when needed:

```bash
needle view file.py --from 10 --to 20
```

2. Run the smallest command that expresses the edit.

3. Always inspect the result:

```bash
git diff
```

If NeedlePatch reports multiple matches, add more context. If it reports no match, inspect the file again with `needle view` and retry with the exact current text.
