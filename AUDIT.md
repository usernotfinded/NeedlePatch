# NeedlePatch Audit

Date: 2026-05-05

Scope: read-only security and quality review of the local repository. No source
code was changed. The audit covered Python package metadata, CLI file handling,
tests, GitHub Actions, tracked files, ignored files, and basic local static
checks.

## Summary

NeedlePatch is a small Python CLI with no declared runtime dependencies and a
focused implementation. I did not find command injection, network exposure,
unsafe deserialization, eval/exec usage, or secret material in the working tree.

The main risks are in the threat model around editing attacker-controlled paths,
CI hardening, dependency reproducibility, and repository hygiene.

## Findings

### Medium: CLI follows arbitrary paths and symlinks

File: `src/needlepatch/cli.py`

Relevant lines:

- `Path(args.file)` is accepted directly in the edit handlers.
- `read_file()` uses `path.read_text(...)`.
- `write_file()` uses `path.write_text(...)`.

Impact: any caller can point `needle` at an absolute path, a path outside the
current repository, or a symlink. For a normal local editor CLI this is expected
behavior, but NeedlePatch is positioned as a safer tool for AI coding agents. In
that context, a malicious or compromised workspace could steer an agent toward
editing files outside the intended project, especially through symlinks.

Evidence:

- `src/needlepatch/cli.py:181`
- `src/needlepatch/cli.py:214`
- `src/needlepatch/cli.py:271`
- `src/needlepatch/cli.py:303`
- `src/needlepatch/cli.py:334`
- `src/needlepatch/cli.py:509`
- `src/needlepatch/cli.py:526`

Suggested mitigation: define the intended trust boundary. If the tool is meant
to be safe for agent use inside a workspace, consider rejecting symlinks,
rejecting absolute paths by default, resolving paths against an allowed root,
or adding an explicit unsafe flag for out-of-root edits.

### Medium: Writes are non-atomic and can leave partial files

File: `src/needlepatch/cli.py`

Relevant lines:

- `finish_edit()` calls `write_file()` after constructing the full updated
  string.
- `write_file()` uses `Path.write_text()`.

Impact: if the process is interrupted during `Path.write_text()`, the target can
be truncated or partially written. This matters because the tool is intended to
make precise edits while minimizing accidental damage.

Evidence:

- `src/needlepatch/cli.py:424`
- `src/needlepatch/cli.py:426`
- `src/needlepatch/cli.py:526`
- `src/needlepatch/cli.py:528`

Suggested mitigation: write to a temporary file in the same directory, flush and
fsync it, then atomically replace the original. Preserve file mode and ownership
where relevant.

### Medium: CI runs repository code without explicit token hardening

File: `.github/workflows/ci.yml`

Relevant lines:

- The workflow runs on `pull_request`.
- The workflow has no top-level `permissions`.
- `actions/checkout` uses default credential persistence.
- The job installs and runs code from the PR.

Impact: tests execute untrusted or semi-trusted pull request code. Without
explicit `permissions: contents: read` and without disabling checkout credential
persistence, the blast radius depends on repository settings and PR origin. This
is especially relevant if future CI steps add publishing, labels, comments, or
other write-capable tokens.

Evidence:

- `.github/workflows/ci.yml:3`
- `.github/workflows/ci.yml:5`
- `.github/workflows/ci.yml:18`
- `.github/workflows/ci.yml:19`
- `.github/workflows/ci.yml:26`
- `.github/workflows/ci.yml:30`

Suggested mitigation: set top-level read-only permissions and use
`persist-credentials: false` for checkout unless credentials are actually needed.

### Low: GitHub Actions are pinned by mutable tags, not immutable SHAs

File: `.github/workflows/ci.yml`

Relevant lines:

- `actions/checkout@v4`
- `actions/setup-python@v5`

Impact: first-party GitHub action tags are common, but they are still mutable
references. Pinning to full commit SHAs reduces supply-chain risk and improves
reproducibility.

Evidence:

- `.github/workflows/ci.yml:19`
- `.github/workflows/ci.yml:22`

Suggested mitigation: pin actions to known commit SHAs and update them
intentionally.

### Low: Development dependencies are not pinned or locked

File: `pyproject.toml`

Relevant lines:

- `pytest` is declared without a version range.
- Build backend uses `setuptools>=68` without an upper bound or lock.

Impact: local and CI environments can resolve different dependency versions over
time. This is not an immediate vulnerability because the package declares no
runtime dependencies, but it weakens reproducibility and can introduce future
test or build instability.

Evidence:

- `pyproject.toml:2`
- `pyproject.toml:17`
- `pyproject.toml:18`
- `pyproject.toml:19`

Suggested mitigation: maintain a lock file or constraints file for CI/dev tools,
and periodically refresh it with an advisory scan.

### Low: No dependency advisory scan is configured

Files:

- `pyproject.toml`
- `.github/workflows/ci.yml`

Impact: the current package has no runtime dependencies, so the immediate
dependency attack surface is small. Still, build and dev tooling can carry
supply-chain risk, and CI currently does not run `pip-audit`, Dependabot, OSV
Scanner, or an equivalent advisory check.

Evidence:

- `pyproject.toml:15`
- `pyproject.toml:17`
- `.github/workflows/ci.yml:26`
- `.github/workflows/ci.yml:30`

Suggested mitigation: add an advisory scan for dev/build dependencies or enable
Dependabot security updates.

### Low: Large files can cause memory or CPU exhaustion

File: `src/needlepatch/cli.py`

Relevant lines:

- The whole file is read into memory.
- Match counting scans the whole string.
- Dry-run diff generation builds a full unified diff in memory.

Impact: a caller can point the CLI at a very large file and cause high memory or
CPU usage. This is mostly a local denial-of-service risk.

Evidence:

- `src/needlepatch/cli.py:169`
- `src/needlepatch/cli.py:182`
- `src/needlepatch/cli.py:215`
- `src/needlepatch/cli.py:272`
- `src/needlepatch/cli.py:304`
- `src/needlepatch/cli.py:335`
- `src/needlepatch/cli.py:537`
- `src/needlepatch/cli.py:538`

Suggested mitigation: enforce a configurable maximum file size, or add a warning
and explicit override for large files.

### Low: Terminal output can include unescaped filenames and errors

File: `src/needlepatch/cli.py`

Relevant lines:

- Human-readable errors print exception text directly.
- Diff headers include the path directly.

Impact: malicious filenames or OS error messages containing terminal control
characters can make logs misleading or affect terminal display. JSON output is
safer because `json.dumps` escapes strings.

Evidence:

- `src/needlepatch/cli.py:145`
- `src/needlepatch/cli.py:515`
- `src/needlepatch/cli.py:521`
- `src/needlepatch/cli.py:542`
- `src/needlepatch/cli.py:543`
- `src/needlepatch/cli.py:583`
- `src/needlepatch/cli.py:612`

Suggested mitigation: sanitize control characters in human output, or document
that automation should prefer `--json`.

### Low: Tracked `.DS_Store` files and missing ignore rule

Files:

- `.DS_Store`
- `src/.DS_Store`
- `src/needlepatch/.DS_Store`
- `.gitignore`

Impact: `.DS_Store` files are tracked and `.gitignore` does not ignore them.
These files are not usually a direct vulnerability, but they create repository
noise and can leak local folder metadata.

Evidence:

- `git ls-files` reports `.DS_Store`, `src/.DS_Store`, and
  `src/needlepatch/.DS_Store`.
- `.gitignore:1` through `.gitignore:4` do not include `.DS_Store`.

Suggested mitigation: remove tracked `.DS_Store` files from Git and add
`.DS_Store` to `.gitignore`.

### Low: Case mismatch between Git index and filesystem

File: `ROADMAP.md` / `roadmap.md`

Impact: Git tracks `roadmap.md`, while the local filesystem shows `ROADMAP.md`
and `core.ignorecase=true`. This can create confusing diffs or checkout behavior
across macOS, Linux, and CI environments.

Evidence:

- `git ls-files` reports `roadmap.md`.
- `ls` reports `ROADMAP.md`.
- `git config core.ignorecase` reports `true`.

Suggested mitigation: normalize the filename casing with an explicit Git rename.

## Positive Checks

- No runtime dependencies are declared in `pyproject.toml`.
- No obvious secrets were found by local pattern search.
- No `eval`, `exec`, `shell=True`, `os.system`, network clients, or unsafe
  deserialization were found in source code.
- No symlinks or executable files were present in the working tree outside Git
  internals.
- `pytest -q` passed: 41 tests.
- `ruff check .` passed.
- `python -m compileall -q src tests benchmarks` passed.

## Tooling Notes

- `pip-audit`, `bandit`, and `semgrep` were not installed in the active Python
  environment, so I did not run those scanners.
- `python -m pip check` was run, but the output reflects the broad active
  user-level Python environment rather than an isolated project environment.
  I did not treat those unrelated package conflicts as NeedlePatch findings.

