# NeedlePatch

**Safe shell commands for tiny text edits by AI coding agents.**

NeedlePatch is a small, dumb, stateless CLI tool that helps AI coding agents avoid rewriting whole lines, blocks, or functions when the intended change is only a few characters.

It is designed for micro-edits like:

- changing `True` to `False`
- changing a number
- appending text
- inserting one short line
- deleting one exact token or line
- replacing a tiny piece of text inside a unique context

NeedlePatch is **not** a replacement for `apply_patch`, Aider, Cursor, Codex, Claude Code, or normal diffs.

It is a fast path for edits that are too small to justify a full patch.

---

## Why?

AI coding agents often generate large patches for very small edits.

Example:

```diff
- from scripts.check_generation_quality import max_repeated_ngram_ratio, repeated_ngram_ratio
+ from scripts.check_generation_quality import max_repeated_ngram_ratio, repeated_ngram_ratio  # noqa: E402
```

With NeedlePatch, the agent can express the edit directly:

```bash
needle append scripts/benchmark_local_baseline.py \
  --match "from scripts.check_generation_quality import max_repeated_ngram_ratio, repeated_ngram_ratio" \
  --text "  # noqa: E402"
```

The goal is not to replace diffs.

The goal is to make tiny edits explicit, safe, and less noisy.

---

## Core idea

NeedlePatch edits files using exact text matching.

By default:

```text
0 matches  -> fail
1 match    -> edit
2+ matches -> fail
```

This makes the tool conservative by design.

If the target is ambiguous, NeedlePatch refuses to edit.

---

## Scope

Use NeedlePatch for tiny edits of **1–2 lines**.

Good use cases:

* append a small suffix
* replace one boolean
* replace one number
* replace one string
* edit one tuple/list/array element
* insert one short line
* delete one exact line or token
* replace a small piece of text inside a known context

Bad use cases:

* refactors
* large logic changes
* function rewrites
* multi-file edits
* formatting entire files
* semantic code transformations
* cases that require AST or type analysis

For larger edits, use `apply_patch`, a normal diff, or your coding agent’s native editing system.

---

# Commands

NeedlePatch provides a small set of shell commands for precise micro-edits.

The goal is not to replace `apply_patch` or normal diffs. The goal is to give AI coding agents safer commands for tiny edits where rewriting a whole line, block, or function would be unnecessary and token-consuming.

```bash
needle view             -> inspect exact text
needle replace          -> replace unique exact text
needle inside           -> replace tiny text inside a unique context
needle append           -> add suffix after a match
needle after            -> add a new line/block after a match
needle delete           -> remove exact text
```

Core safety rule:

```text
0 matches  -> fail
1 match    -> edit
2+ matches -> fail
````

If NeedlePatch cannot identify exactly one target, it refuses to edit.

---

## Command overview

| Command                 | What it does                                             | Best for                                             |
| ----------------------- | -------------------------------------------------------- | ---------------------------------------------------- |
| `needle view`           | Shows a section of a file with line numbers              | Letting the AI inspect exact text before editing     |
| `needle replace`        | Replaces one exact text block with another               | Simple exact substitutions                           |
| `needle inside` | Replaces a small text only inside a larger exact context | Boolean/number/string changes inside a specific line |
| `needle append`         | Adds text after a matched string                         | Adding suffixes like `# noqa`, comments, flags       |
| `needle after`   | Inserts a new line/block after a matched string          | Adding one short line after a known anchor           |
| `needle delete`         | Deletes exact text                                       | Removing one token, suffix, line, or small block     |

---

# 1. `needle view`

## What it does

`needle view` prints a section of a file with line numbers.

It does not modify anything.

## Why it exists

AI agents need exact text before they can safely use `replace`, `append`, or `delete`.

Instead of reading a whole file, the agent can inspect only the relevant section.

## Example

```bash
needle view scripts/benchmark_local_baseline.py --from 20 --to 30
```

Example output:

```text
21 | import llm  # noqa: E402
22 | import retrieval  # noqa: E402
23 | from scripts.check_generation_quality import max_repeated_ngram_ratio, repeated_ngram_ratio
24 | from scripts.runtime_utils import (
25 |     SCENARIO_STATUSES,
26 |     STATUS_INVALID_OUTPUT,
```

## Use when

Use `view` when the AI needs to:

* inspect the exact current text;
* copy a precise match;
* verify indentation;
* avoid editing based on outdated assumptions.

---

# 2. `needle replace`

## What it does

`needle replace` replaces one exact text with another exact text.

It is the most basic edit command.

## Example

```bash
needle replace config.py \
  --old "timeout = 30" \
  --new "timeout = DEFAULT_TIMEOUT"
```

Before:

```python
timeout = 30
```

After:

```python
timeout = DEFAULT_TIMEOUT
```

## Use when

Use `replace` when the old text is already unique in the file.

Good cases:

```text
timeout = 30
debug_enabled = True
VERSION = "0.1.0"
```

## Avoid when

Avoid `replace` if the old text may appear multiple times.

Example:

```python
enabled = True
```

This could appear in many places. In that case, prefer `replace-inside`.

---

# 3. `needle inside`

## What it does

`needle inside` finds a larger exact context, then replaces a smaller exact text only inside that context.

This is the most important NeedlePatch command.

## Example

```bash
needle inside config.py \
  --within "debug_enabled = True" \
  --old "True" \
  --new "False"
```

Before:

```python
debug_enabled = True
```

After:

```python
debug_enabled = False
```

## Why it exists

Sometimes the text to change is too generic.

Example:

```text
True
```

Replacing `True` globally would be dangerous.

So the agent says:

```text
inside this exact line/context, replace only this tiny part
```

## Another example

```bash
needle inside scripts/benchmark_local_baseline.py \
  --within "for hie_lite_enabled in (False, True):" \
  --old "(False, True)" \
  --new "(False,)"
```

Before:

```python
for hie_lite_enabled in (False, True):
```

After:

```python
for hie_lite_enabled in (False,):
```

## Use when

Use `inside` for:

* changing `True` to `False`;
* changing a number;
* changing a string;
* editing tuple/list/array items;
* replacing one argument;
* changing one operator;
* editing a small token inside a known line.

## Difference from `replace`

`replace` changes this:

```text
old text -> new text
```

`replace` changes this:

```text
inside this larger context:
    old text -> new text
```

So `replace` is safer when the target is small or common.

---

# 4. `needle append`

## What it does

`needle append` adds text immediately after a matched string.

It does not replace the matched string. It keeps it and adds more text after it.

## Example

```bash
needle append scripts/benchmark_local_baseline.py \
  --match "from scripts.check_generation_quality import max_repeated_ngram_ratio, repeated_ngram_ratio" \
  --text "  # noqa: E402"
```

Before:

```python
from scripts.check_generation_quality import max_repeated_ngram_ratio, repeated_ngram_ratio
```

After:

```python
from scripts.check_generation_quality import max_repeated_ngram_ratio, repeated_ngram_ratio  # noqa: E402
```

## Use when

Use `append` for adding a suffix:

* `# noqa: E402`
* `# type: ignore`
* `;`
* `,`
* inline comments
* small flags
* small trailing text

## Difference from `replace`

With `replace`, the AI must provide both the old and new full text:

```bash
needle replace file.py \
  --old "from x import y" \
  --new "from x import y  # noqa: E402"
```

With `append`, the AI only says:

```bash
needle append file.py \
  --match "from x import y" \
  --text "  # noqa: E402"
```

This makes the edit intent clearer:

```text
find this text and add this suffix
```

---

# 5. `needle after`

## What it does

`needle after` inserts new text after a matched string.

Unlike `append`, it is normally used to add a new line or small block after an anchor.

## Example

```bash
needle after app.py \
  --match "init_config()" \
  --text "validate_config()"
```

Before:

```python
init_config()
run_app()
```

After:

```python
init_config()
validate_config()
run_app()
```

## Use when

Use `after` when you need to add:

* one short line;
* one import;
* one function call;
* one small guard;
* one comment line;
* one config entry after a known anchor.

## Difference from `append`

`append` adds text directly after the matched text on the same line:

```python
import llm
```

becomes:

```python
import llm  # noqa: E402
```

`after` adds a new line/block after the matched text:

```python
init_config()
```

becomes:

```python
init_config()
validate_config()
```

So:

```text
append       = same-line suffix
after        = new line/block after anchor
```

---

# 6. `needle delete`

## What it does

`needle delete` removes exact text from a file.

## Example

```bash
needle delete app.py \
  --text "  # noqa: E402"
```

Before:

```python
import llm  # noqa: E402
```

After:

```python
import llm
```

## Safer example with context

```bash
needle delete app.py \
  --within "import llm  # noqa: E402" \
  --text "  # noqa: E402"
```

This means:

```text
inside this exact context, delete this smaller text
```

## Use when

Use `delete` for:

* removing one suffix;
* removing one exact line;
* removing one comment;
* removing one argument;
* removing one small token;
* deleting a small repeated-looking edit inside a specific context.

## Avoid when

Avoid deleting generic text without context.

Bad:

```bash
needle delete file.py --text "True"
```

Better:

```bash
needle delete file.py \
  --within "debug_enabled = True" \
  --text "True"
```

---

# Common flags

## `--within`

Restricts an edit to a specific exact context.

Useful for avoiding accidental edits when the target text appears multiple times.

Example:

```bash
needle replace-inside file.py \
  --within "debug_enabled = True" \
  --old "True" \
  --new "False"
```

## `--dry-run`

Shows what would change without modifying the file.

Example:

```bash
needle append file.py \
  --match "from x import y" \
  --text "  # noqa: E402" \
  --dry-run
```

Expected output:

```diff
- from x import y
+ from x import y  # noqa: E402
```

Use `--dry-run` before risky edits.

## `--json`

Prints machine-readable output for AI agents.

Example success:

```json
{
  "status": "ok",
  "command": "append",
  "file": "file.py",
  "matches": 1,
  "changed_lines": 1,
  "changed_bytes": 13
}
```

Example error:

```json
{
  "status": "error",
  "reason": "multiple_matches",
  "matches": 3,
  "hint": "Use --within with a larger exact context."
}
```

---

# How to choose the right command

## If you only need to inspect text

Use:

```bash
needle view
```

## If you want to replace a unique exact phrase

Use:

```bash
needle replace
```

## If you want to change a tiny piece inside a specific line/context

Use:

```bash
needle replace-inside
```

Best command for booleans, numbers, strings, tuple items, and arguments.

## If you want to add a suffix on the same line

Use:

```bash
needle append
```

Best command for `# noqa`, `# type: ignore`, commas, semicolons, and inline comments.

## If you want to add a new line after an existing line

Use:

```bash
needle insert-after
```

## If you want to remove exact text

Use:

```bash
needle delete
```

Use `--within` if the text may appear more than once.

---

# Practical examples

## Add `# noqa: E402`

```bash
needle append file.py \
  --match "import llm" \
  --text "  # noqa: E402"
```

Before:

```python
import llm
```

After:

```python
import llm  # noqa: E402
```

---

## Change `True` to `False`

```bash
needle replace-inside file.py \
  --within "debug_enabled = True" \
  --old "True" \
  --new "False"
```

Before:

```python
debug_enabled = True
```

After:

```python
debug_enabled = False
```

---

## Change a tuple

```bash
needle replace-inside file.py \
  --within "for hie_lite_enabled in (False, True):" \
  --old "(False, True)" \
  --new "(False,)"
```

Before:

```python
for hie_lite_enabled in (False, True):
```

After:

```python
for hie_lite_enabled in (False,):
```

---

## Insert a validation call

```bash
needle insert-after app.py \
  --match "init_config()" \
  --text "validate_config()"
```

Before:

```python
init_config()
run_app()
```

After:

```python
init_config()
validate_config()
run_app()
```

---

## Delete a suffix

```bash
needle delete file.py \
  --within "import llm  # noqa: E402" \
  --text "  # noqa: E402"
```

Before:

```python
import llm  # noqa: E402
```

After:

```python
import llm
```

---

## Examples

### View a file section

```bash
needle view scripts/benchmark_local_baseline.py --from 20 --to 30
```

Example output:

```text
21 | import llm  # noqa: E402
22 | import retrieval  # noqa: E402
23 | from scripts.check_generation_quality import max_repeated_ngram_ratio, repeated_ngram_ratio
24 | from scripts.runtime_utils import (
25 |     SCENARIO_STATUSES,
26 |     STATUS_INVALID_OUTPUT,
```

---

### Append text to a unique match

```bash
needle append scripts/benchmark_local_baseline.py \
  --match "from scripts.check_generation_quality import max_repeated_ngram_ratio, repeated_ngram_ratio" \
  --text "  # noqa: E402"
```

Before:

```python
from scripts.check_generation_quality import max_repeated_ngram_ratio, repeated_ngram_ratio
```

After:

```python
from scripts.check_generation_quality import max_repeated_ngram_ratio, repeated_ngram_ratio  # noqa: E402
```

---

### Replace text inside a unique context

```bash
needle replace-inside scripts/benchmark_local_baseline.py \
  --within "for hie_lite_enabled in (False, True):" \
  --old "(False, True)" \
  --new "(False,)"
```

Before:

```python
for hie_lite_enabled in (False, True):
```

After:

```python
for hie_lite_enabled in (False,):
```

---

### Toggle a boolean

```bash
needle replace-inside config.py \
  --within "debug_enabled = True" \
  --old "True" \
  --new "False"
```

Before:

```python
debug_enabled = True
```

After:

```python
debug_enabled = False
```

---

### Replace exact text

```bash
needle replace config.py \
  --old "timeout = 30" \
  --new "timeout = DEFAULT_TIMEOUT"
```

Before:

```python
timeout = 30
```

After:

```python
timeout = DEFAULT_TIMEOUT
```

---

### Insert a line after a unique match

```bash
needle insert-after app.py \
  --match "init_config()" \
  --text "validate_config()"
```

Before:

```python
init_config()
run_app()
```

After:

```python
init_config()
validate_config()
run_app()
```

---

### Delete exact text

```bash
needle delete app.py \
  --text "  # noqa: E402"
```

Before:

```python
import llm  # noqa: E402
```

After:

```python
import llm
```

For safer deletion, use a context:

```bash
needle delete app.py \
  --within "import llm  # noqa: E402" \
  --text "  # noqa: E402"
```

---

## Dry run

Every edit command supports `--dry-run`.

```bash
needle append file.py \
  --match "from x import y" \
  --text "  # noqa: E402" \
  --dry-run
```

Example output:

```diff
- from x import y
+ from x import y  # noqa: E402
```

No file is changed.

---

## JSON output

Every command supports `--json`.

```bash
needle append file.py \
  --match "from x import y" \
  --text "  # noqa: E402" \
  --json
```

Example success:

```json
{
  "status": "ok",
  "command": "append",
  "file": "file.py",
  "matches": 1,
  "changed_lines": 1,
  "changed_bytes": 13
}
```

Example error:

```json
{
  "status": "error",
  "reason": "multiple_matches",
  "matches": 3,
  "hint": "Use --within with a larger exact context."
}
```

---

## Safety model

NeedlePatch is intentionally conservative.

### Match uniqueness

NeedlePatch refuses to edit unless the target is unique.

```text
0 matches  -> error
1 match    -> edit
2+ matches -> error
```

### Exact text only

NeedlePatch does not use regex by default.

The MVP is exact string matching only.

This makes commands easier for AI agents to generate safely.

### Context support

For ambiguous edits, use `--within`.

Example:

```bash
needle replace-inside file.py \
  --within "debug_enabled = True" \
  --old "True" \
  --new "False"
```

This tells NeedlePatch:

> Find this exact context, then replace this smaller piece only inside it.

---

## Exit codes

Suggested exit codes:

```text
0 -> success
1 -> generic error
2 -> no match
3 -> multiple matches
4 -> invalid arguments
5 -> file read/write error
```

---

## Intended AI agent policy

Use NeedlePatch only for tiny edits.

Recommended policy for `AGENTS.md` or similar agent instruction files:

````md
# NeedlePatch policy

Use NeedlePatch for tiny edits only.

Prefer NeedlePatch when changing:
- one boolean
- one number
- one string
- one import suffix
- one short line
- one exact token
- one tuple/list/array item
- one small piece of text inside a unique context

Do not use NeedlePatch for:
- refactors
- multi-line logic changes
- function rewrites
- large patches
- formatting entire files

For larger edits, use apply_patch or a normal diff.

After using NeedlePatch, always inspect the result with:

```bash
git diff
````

---

## Comparison

NeedlePatch is not meant to replace existing editing systems.

| Tool / approach | Best for |
|---|---|
| `apply_patch` / unified diff | normal code edits and multi-line changes |
| Aider edit formats | LLM-native repository editing |
| IDE editor APIs | integrated editor workflows |
| `sed` / `perl` | powerful manual text processing |
| NeedlePatch | tiny, safe, exact micro-edits by AI agents |

NeedlePatch is closer to a safer, AI-friendly `sed` than to a full coding assistant.

---

## Design principles

1. **Dumb by design**  
   No AI, no AST, no LSP, no background server.

2. **Shell-first**  
   Any AI agent with shell access can use it.

3. **Exact matching**  
   No regex in the MVP.

4. **Fail fast**  
   Ambiguous edits are rejected.

5. **Small scope**  
   Optimized for 1–2 line edits.

6. **Diff visible**  
   The user or agent should always be able to inspect what changed.

7. **Machine-readable output**  
   `--json` makes it easier for agents to recover from errors.

---

## Install

TODO.

Possible future installation methods:

```bash
pip install needlepatch
````

or:

```bash
cargo install needlepatch
```

or:

```bash
brew install needlepatch
```

---

## Development status

Early MVP.

This project should be treated as an experiment.

The main question is:

> Are shell-level micro-edit commands actually useful for AI coding agents, or are normal diffs already good enough?

The project should continue only if real-world testing shows that NeedlePatch reduces noisy rewrites, improves safety, or makes tiny edits easier for agents to express.

---

## Validation plan

Before expanding the project, test NeedlePatch on at least 20 real micro-edit cases.

Measure:

* command length vs normal diff length
* success rate
* no-match rate
* multiple-match rate
* changed lines
* changed bytes
* whether an AI agent can use it from instructions only

NeedlePatch should stay small unless the data proves it is useful.

---

## Non-goals

NeedlePatch will not try to:

* understand code semantically
* parse ASTs
* integrate deeply with IDEs
* replace coding agents
* replace patch formats
* handle complex refactors
* become a background service
* become a general automation framework

---

## One-line summary

**NeedlePatch is a tiny CLI that helps AI coding agents make safe one-line and token-level edits without rewriting whole blocks.**

