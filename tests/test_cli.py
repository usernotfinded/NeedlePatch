from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def run_needle(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = (
        str(SRC)
        if not env.get("PYTHONPATH")
        else f"{SRC}{os.pathsep}{env['PYTHONPATH']}"
    )
    return subprocess.run(
        [sys.executable, "-m", "needlepatch.cli", *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_view_uses_inclusive_one_based_line_range(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("one\ntwo\nthree\nfour\n", encoding="utf-8")

    result = run_needle("view", str(target), "--from", "2", "--to", "3")

    assert result.returncode == 0
    assert result.stdout == "2 | two\n3 | three\n"
    assert result.stderr == ""


def test_replace_success(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("alpha beta gamma\n", encoding="utf-8")

    result = run_needle("replace", str(target), "--old", "beta", "--new", "BETA")

    assert result.returncode == 0
    assert target.read_text(encoding="utf-8") == "alpha BETA gamma\n"
    assert result.stdout == ""
    assert result.stderr == ""


def test_replace_allows_empty_new_value(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("alpha beta gamma\n", encoding="utf-8")

    result = run_needle("replace", str(target), "--old", " beta", "--new", "")

    assert result.returncode == 0
    assert target.read_text(encoding="utf-8") == "alpha gamma\n"


def test_replace_no_match_failure_does_not_modify_file(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("alpha beta\n", encoding="utf-8")

    result = run_needle("replace", str(target), "--old", "missing", "--new", "x")

    assert result.returncode == 2
    assert target.read_text(encoding="utf-8") == "alpha beta\n"
    assert "No exact match" in result.stderr


def test_replace_multiple_match_failure_does_not_modify_file(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("alpha beta beta\n", encoding="utf-8")

    result = run_needle("replace", str(target), "--old", "beta", "--new", "x")

    assert result.returncode == 3
    assert target.read_text(encoding="utf-8") == "alpha beta beta\n"
    assert "more specific" in result.stderr


def test_replace_inside_success(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("debug_enabled = True\nother = True\n", encoding="utf-8")

    result = run_needle(
        "replace-inside",
        str(target),
        "--within",
        "debug_enabled = True",
        "--old",
        "True",
        "--new",
        "False",
    )

    assert result.returncode == 0
    assert target.read_text(encoding="utf-8") == "debug_enabled = False\nother = True\n"


def test_replace_inside_missing_context(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("debug_enabled = True\n", encoding="utf-8")

    result = run_needle(
        "replace-inside",
        str(target),
        "--within",
        "missing = True",
        "--old",
        "True",
        "--new",
        "False",
    )

    assert result.returncode == 2
    assert target.read_text(encoding="utf-8") == "debug_enabled = True\n"


def test_replace_inside_duplicate_context(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("debug_enabled = True\ndebug_enabled = True\n", encoding="utf-8")

    result = run_needle(
        "replace-inside",
        str(target),
        "--within",
        "debug_enabled = True",
        "--old",
        "True",
        "--new",
        "False",
    )

    assert result.returncode == 3
    assert target.read_text(encoding="utf-8") == (
        "debug_enabled = True\ndebug_enabled = True\n"
    )


def test_replace_inside_missing_inner_text(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("debug_enabled = True\n", encoding="utf-8")

    result = run_needle(
        "replace-inside",
        str(target),
        "--within",
        "debug_enabled = True",
        "--old",
        "False",
        "--new",
        "True",
    )

    assert result.returncode == 2
    assert target.read_text(encoding="utf-8") == "debug_enabled = True\n"


def test_replace_inside_duplicate_inner_text(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("values = (True, True)\n", encoding="utf-8")

    result = run_needle(
        "replace-inside",
        str(target),
        "--within",
        "values = (True, True)",
        "--old",
        "True",
        "--new",
        "False",
    )

    assert result.returncode == 3
    assert target.read_text(encoding="utf-8") == "values = (True, True)\n"


def test_dry_run_leaves_file_unchanged_and_prints_diff(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("alpha beta gamma\n", encoding="utf-8")

    result = run_needle(
        "replace",
        str(target),
        "--old",
        "beta",
        "--new",
        "BETA",
        "--dry-run",
    )

    assert result.returncode == 0
    assert target.read_text(encoding="utf-8") == "alpha beta gamma\n"
    diff_lines = result.stdout.splitlines()
    assert diff_lines[0].startswith("--- ")
    assert diff_lines[1].startswith("+++ ")
    assert diff_lines[2].startswith("@@ ")
    assert "-alpha beta gamma" in result.stdout
    assert "+alpha BETA gamma" in result.stdout


def test_json_success_for_replace(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("alpha beta gamma\n", encoding="utf-8")

    result = run_needle(
        "replace",
        str(target),
        "--old",
        "beta",
        "--new",
        "BETA",
        "--json",
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 0
    assert result.stderr == ""
    assert payload == {
        "status": "ok",
        "command": "replace",
        "file": str(target),
        "matches": 1,
        "changed": True,
        "dry_run": False,
    }


def test_json_dry_run_success_includes_diff_and_does_not_change_file(
    tmp_path: Path,
) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("alpha beta gamma\n", encoding="utf-8")

    result = run_needle(
        "replace",
        str(target),
        "--old",
        "beta",
        "--new",
        "BETA",
        "--dry-run",
        "--json",
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 0
    assert result.stderr == ""
    assert target.read_text(encoding="utf-8") == "alpha beta gamma\n"
    assert payload["status"] == "ok"
    assert payload["changed"] is False
    assert payload["dry_run"] is True
    assert "-alpha beta gamma" in payload["diff"]
    assert "+alpha BETA gamma" in payload["diff"]


def test_json_failure_for_replace_no_match(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("alpha beta gamma\n", encoding="utf-8")

    result = run_needle(
        "replace",
        str(target),
        "--old",
        "missing",
        "--new",
        "x",
        "--json",
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 2
    assert result.stderr == ""
    assert payload["status"] == "error"
    assert payload["command"] == "replace"
    assert payload["file"] == str(target)
    assert payload["matches"] == 0
    assert payload["reason"] == "no_match"
    assert payload["hint"]


def test_json_success_for_replace_inside_includes_match_counts(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("debug_enabled = True\nother = True\n", encoding="utf-8")

    result = run_needle(
        "replace-inside",
        str(target),
        "--within",
        "debug_enabled = True",
        "--old",
        "True",
        "--new",
        "False",
        "--json",
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 0
    assert payload["status"] == "ok"
    assert payload["matches"] == 1
    assert payload["context_matches"] == 1
    assert payload["inner_matches"] == 1


def test_json_failure_for_replace_inside_duplicate_inner_includes_counts(
    tmp_path: Path,
) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("values = (True, True)\n", encoding="utf-8")

    result = run_needle(
        "replace-inside",
        str(target),
        "--within",
        "values = (True, True)",
        "--old",
        "True",
        "--new",
        "False",
        "--json",
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 3
    assert result.stderr == ""
    assert payload["status"] == "error"
    assert payload["matches"] == 2
    assert payload["context_matches"] == 1
    assert payload["inner_matches"] == 2
    assert payload["reason"] == "multiple_matches"


def test_invalid_arguments_exit_4(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("alpha beta gamma\n", encoding="utf-8")

    result = run_needle("replace", str(target), "--old", "", "--new", "x")

    assert result.returncode == 4
    assert target.read_text(encoding="utf-8") == "alpha beta gamma\n"


def test_json_invalid_arguments_exit_4_without_human_text(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("alpha beta gamma\n", encoding="utf-8")

    result = run_needle("replace", str(target), "--old", "", "--new", "x", "--json")
    payload = json.loads(result.stdout)

    assert result.returncode == 4
    assert result.stderr == ""
    assert payload["status"] == "error"
    assert payload["reason"] == "invalid_arguments"


def test_missing_file_exits_5_with_json(tmp_path: Path) -> None:
    target = tmp_path / "missing.txt"

    result = run_needle(
        "replace",
        str(target),
        "--old",
        "x",
        "--new",
        "y",
        "--json",
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 5
    assert result.stderr == ""
    assert payload["status"] == "error"
    assert payload["reason"] == "file_error"


def test_deferred_commands_are_not_implemented(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("alpha beta gamma\n", encoding="utf-8")

    for command in ("append", "insert-after", "delete"):
        result = run_needle(command, str(target))
        assert result.returncode == 4
