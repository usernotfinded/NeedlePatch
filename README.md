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

## Why

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

## Commands

MVP commands:

```bash
needle view
needle replace
needle replace-inside
needle append
needle insert-after
needle delete
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

## License

TODO.

Recommended:

```text
MIT
```

or:

```text
Apache-2.0
```

---

## One-line summary

**NeedlePatch is a tiny CLI that helps AI coding agents make safe one-line and token-level edits without rewriting whole blocks.**

