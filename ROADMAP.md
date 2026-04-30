# NeedlePatch Roadmap

NeedlePatch is a small, shell-first CLI for safe micro-edits by AI coding agents.

The goal is not to replace `apply_patch`, Aider, Cursor, Codex, Claude Code, or normal diffs.

The goal is narrower:

> Help AI coding agents avoid full-line or full-block rewrites when the intended edit is only a tiny text change.

NeedlePatch should stay small, dumb, stateless, and predictable.

---

## Current status

NeedlePatch is currently in **Tiny Core MVP** stage.

The first working version implements only the minimum needed to prove the safety model:

- exact string matching;
- unique-match requirement;
- dry-run support;
- JSON output for edit commands;
- clear exit codes;
- pytest coverage;
- no runtime dependencies.

---

## Implemented

### Packaging

- Python package: `needlepatch`
- CLI executable: `needle`
- Standard-library runtime only
- Optional dev dependency: `pytest`
- Editable install supported:

```bash
python3 -m pip install -e '.[dev]'
````

---

### Commands

The Tiny Core MVP implements:

```bash
needle view
needle replace
needle replace-inside
```

Deferred commands are documented but not yet implemented:

```bash
needle append
needle insert-after
needle delete
```

---

### `needle view`

Shows a 1-based inclusive line range from a file.

Example:

```bash
needle view file.py --from 10 --to 20
```

Purpose:

* inspect exact text before editing;
* help AI agents copy reliable context;
* avoid reading or rewriting whole files unnecessarily.

---

### `needle replace`

Replaces one exact text occurrence in a file.

Example:

```bash
needle replace file.py \
  --old "debug_enabled = True" \
  --new "debug_enabled = False"
```

Safety behavior:

```text
0 matches  -> fail
1 match    -> edit
2+ matches -> fail
```

Purpose:

* simple exact replacements;
* small one-line edits;
* baseline command for the tool.

---

### `needle replace-inside`

Replaces a small exact text only inside a larger exact context.

Example:

```bash
needle replace-inside file.py \
  --within "debug_enabled = True" \
  --old "True" \
  --new "False"
```

Purpose:

* change one boolean;
* change one number;
* change one string;
* edit tuple/list/array items;
* modify one token inside a unique line or small context.

This is the main NeedlePatch primitive.

---

## Safety model

NeedlePatch is conservative by design.

Default behavior:

```text
0 matches  -> fail
1 match    -> edit
2+ matches -> fail
```

NeedlePatch refuses ambiguous edits instead of guessing.

This is intentional.

---

## Exit codes

```text
0 -> success
1 -> generic error
2 -> no match
3 -> multiple matches
4 -> invalid arguments
5 -> file read/write error
```

---

## JSON output

Edit commands support `--json`.

The goal is to make NeedlePatch easy for AI agents and scripts to use.

Example success shape:

```json
{
  "status": "ok",
  "command": "replace",
  "file": "file.py",
  "matches": 1,
  "changed": true,
  "dry_run": false
}
```

Example error shape:

```json
{
  "status": "error",
  "command": "replace",
  "file": "file.py",
  "matches": 0,
  "reason": "no_match",
  "hint": "..."
}
```

---

## Verification

Tiny Core MVP verification:

```bash
python3 -m pip install -e '.[dev]'
python3 -m pytest
needle --help
git diff --check
```

Current test coverage includes:

* `view` inclusive line ranges;
* `replace` success;
* `replace` no-match failure;
* `replace` multiple-match failure;
* `replace-inside` success;
* missing context;
* duplicate context;
* missing inner text;
* duplicate inner text;
* dry-run behavior;
* JSON success and error output;
* documented exit codes.

---

# Next milestones

## Milestone 1: Complete micro-edit command set

Add the remaining planned commands:

```bash
needle append
needle insert-after
needle delete
```

### `needle append`

Append text after a unique match.

Example:

```bash
needle append file.py \
  --match "from x import y" \
  --text "  # noqa: E402"
```

Use cases:

* add `# noqa`;
* add `# type: ignore`;
* add trailing comments;
* add commas or semicolons;
* add small suffixes.

---

### `needle insert-after`

Insert one short line or block after a unique match.

Example:

```bash
needle insert-after file.py \
  --match "init_config()" \
  --text "validate_config()"
```

Use cases:

* insert one function call;
* insert one import;
* insert one guard line;
* insert one config line;
* insert one short comment.

---

### `needle delete`

Delete exact text.

Example:

```bash
needle delete file.py \
  --within "import llm  # noqa: E402" \
  --text "  # noqa: E402"
```

Use cases:

* remove one suffix;
* remove one exact token;
* remove one exact line;
* remove one tiny block.

---

## Milestone 2: Agent instruction files

Add ready-to-copy instruction files for AI coding agents.

Planned files:

```text
examples/AGENTS.md
examples/SKILL.md
```

Purpose:

* teach agents when to use NeedlePatch;
* prevent misuse for large edits;
* make the tool usable without model training.

Policy:

```text
Use NeedlePatch only for tiny edits of 1–2 lines.
Use normal diffs or apply_patch for larger changes.
```

---

## Milestone 3: Real-world examples

Add examples based on real micro-edits.

Planned examples:

```text
examples/append_noqa.md
examples/toggle_boolean.md
examples/replace_tuple_item.md
examples/insert_one_line.md
examples/delete_suffix.md
```

Each example should show:

* original code;
* desired change;
* normal diff;
* NeedlePatch command;
* result.

Goal:

* prove when NeedlePatch is useful;
* show when it is not useful;
* avoid overclaiming.

---

## Milestone 4: Benchmark script

Add a simple comparison script.

Possible file:

```text
benchmarks/compare_micro_edits.py
```

Measure:

* normal diff character count;
* NeedlePatch command character count;
* changed lines;
* changed bytes;
* success rate;
* no-match rate;
* multiple-match rate.

Important:

NeedlePatch should not claim token savings without measured examples.

---

## Milestone 5: GitHub feedback loop

Add issue templates for real-world cases.

Possible files:

```text
.github/ISSUE_TEMPLATE/bug_report.yml
.github/ISSUE_TEMPLATE/real_world_case.yml
```

The `real_world_case` template should ask for:

* original code;
* desired edit;
* normal diff;
* NeedlePatch command;
* whether the command was useful;
* whether the command was shorter or clearer than a diff.

---

# Possible future features

These are possible, but not guaranteed.

They should only be added if real usage proves they are needed.

---

## File-based arguments

Support reading long values from files:

```bash
needle replace file.py \
  --old-file /tmp/old.txt \
  --new-file /tmp/new.txt
```

Useful when:

* text contains quotes;
* text contains newlines;
* shell escaping becomes annoying;
* AI agents need safer command generation.

---

## `insert-before`

Possible command:

```bash
needle insert-before file.py \
  --match "return result" \
  --text "logger.info(result)"
```

Not part of the current core because `insert-after` is enough for initial testing.

---

## Optional backups

Possible flag:

```bash
needle replace file.py \
  --old "a" \
  --new "b" \
  --backup
```

This may be useful outside Git repositories.

For now, Git is expected to handle rollback.

---

## Better diff formatting

Improve human diff output while keeping JSON stable.

Possible improvements:

* show only small context;
* show changed byte count;
* show changed line count;
* make dry-run output easier to scan.

---

## Shell escaping guidance

Add documentation for safe quoting.

Examples:

```bash
needle replace file.py --old 'debug = True' --new 'debug = False'
```

and multiline-safe alternatives if file-based arguments are implemented.

---

# Non-goals

NeedlePatch should not become a large framework.

The following are intentionally out of scope:

* AI inside the tool;
* AST parsing;
* LSP integration;
* background server;
* IDE plugins;
* config-heavy workflows;
* semantic refactoring;
* multi-file automatic edits;
* regex-first editing;
* replacing `apply_patch`;
* replacing normal diffs;
* replacing coding agents.

NeedlePatch should stay useful because it is simple.

---

# Product philosophy

NeedlePatch should follow these rules:

1. **Tiny edits only**
   Optimized for one-line and token-level edits.

2. **Exact matching only by default**
   No guessing.

3. **Fail on ambiguity**
   If the target is not unique, refuse to edit.

4. **Shell-first**
   Any AI agent with shell access should be able to use it.

5. **No model training required**
   Agents should learn the tool from simple instructions.

6. **No background behavior**
   NeedlePatch only runs when called.

7. **Do not overclaim**
   It may reduce noisy rewrites in some micro-edit cases. It will not replace patch systems.

---

# Success criteria

NeedlePatch is worth continuing if real usage shows that it:

* reduces noisy full-line or full-block rewrites;
* makes tiny edits easier for AI agents to express;
* fails safely on ambiguous matches;
* produces clear diffs;
* works from shell instructions alone;
* is simpler than using a normal patch for some micro-edits.

NeedlePatch should be paused or reduced in scope if:

* commands are usually longer than normal diffs;
* agents ignore it and prefer `apply_patch`;
* most useful cases require AST or regex;
* multiple-match failures are too common;
* the tool becomes complex enough to lose its original purpose.

---

# Short-term priority

The next priority is not more architecture.

The next priority is:

```text
1. Add append, insert-after, and delete.
2. Add real-world examples.
3. Measure whether the tool is actually useful.
```

Until those are done, NeedlePatch should avoid adding advanced features.
