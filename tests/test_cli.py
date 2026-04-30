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


def test_version_flag_prints_package_version() -> None:
    result = run_needle("--version")

    assert result.returncode == 0
    assert result.stdout == "0.1.0\n"
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


def test_append_success(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("from x import y\n", encoding="utf-8")

    result = run_needle(
        "append",
        str(target),
        "--match",
        "from x import y",
        "--text",
        "  # noqa: E402",
    )

    assert result.returncode == 0
    assert target.read_text(encoding="utf-8") == "from x import y  # noqa: E402\n"
    assert result.stdout == ""
    assert result.stderr == ""


def test_append_no_match_failure_does_not_modify_file(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("from x import y\n", encoding="utf-8")

    result = run_needle(
        "append",
        str(target),
        "--match",
        "from missing import y",
        "--text",
        "  # noqa: E402",
    )

    assert result.returncode == 2
    assert target.read_text(encoding="utf-8") == "from x import y\n"


def test_append_multiple_match_failure_does_not_modify_file(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("import x\nimport x\n", encoding="utf-8")

    result = run_needle(
        "append",
        str(target),
        "--match",
        "import x",
        "--text",
        "  # noqa: E402",
    )

    assert result.returncode == 3
    assert target.read_text(encoding="utf-8") == "import x\nimport x\n"


def test_append_dry_run_leaves_file_unchanged(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("from x import y\n", encoding="utf-8")

    result = run_needle(
        "append",
        str(target),
        "--match",
        "from x import y",
        "--text",
        "  # noqa: E402",
        "--dry-run",
    )

    assert result.returncode == 0
    assert target.read_text(encoding="utf-8") == "from x import y\n"
    assert "-from x import y" in result.stdout
    assert "+from x import y  # noqa: E402" in result.stdout


def test_append_json_success(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("from x import y\n", encoding="utf-8")

    result = run_needle(
        "append",
        str(target),
        "--match",
        "from x import y",
        "--text",
        "  # noqa: E402",
        "--json",
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 0
    assert result.stderr == ""
    assert payload == {
        "status": "ok",
        "command": "append",
        "file": str(target),
        "matches": 1,
        "changed": True,
        "dry_run": False,
    }


def test_insert_after_success_with_normal_line_insertion(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("init_config()\nrun_app()\n", encoding="utf-8")

    result = run_needle(
        "insert-after",
        str(target),
        "--match",
        "init_config()",
        "--text",
        "validate_config()",
    )

    assert result.returncode == 0
    assert target.read_text(encoding="utf-8") == (
        "init_config()\nvalidate_config()\nrun_app()\n"
    )


def test_insert_after_no_match_failure_does_not_modify_file(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("init_config()\nrun_app()\n", encoding="utf-8")

    result = run_needle(
        "insert-after",
        str(target),
        "--match",
        "missing()",
        "--text",
        "validate_config()",
    )

    assert result.returncode == 2
    assert target.read_text(encoding="utf-8") == "init_config()\nrun_app()\n"


def test_insert_after_multiple_match_failure_does_not_modify_file(
    tmp_path: Path,
) -> None:
    target = tmp_path / "sample.py"
    target.write_text("init_config()\ninit_config()\nrun_app()\n", encoding="utf-8")

    result = run_needle(
        "insert-after",
        str(target),
        "--match",
        "init_config()",
        "--text",
        "validate_config()",
    )

    assert result.returncode == 3
    assert target.read_text(encoding="utf-8") == (
        "init_config()\ninit_config()\nrun_app()\n"
    )


def test_insert_after_dry_run_leaves_file_unchanged(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("init_config()\nrun_app()\n", encoding="utf-8")

    result = run_needle(
        "insert-after",
        str(target),
        "--match",
        "init_config()",
        "--text",
        "validate_config()",
        "--dry-run",
    )

    assert result.returncode == 0
    assert target.read_text(encoding="utf-8") == "init_config()\nrun_app()\n"
    assert "+validate_config()" in result.stdout


def test_insert_after_json_success(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("init_config()\nrun_app()\n", encoding="utf-8")

    result = run_needle(
        "insert-after",
        str(target),
        "--match",
        "init_config()",
        "--text",
        "validate_config()",
        "--json",
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 0
    assert result.stderr == ""
    assert payload == {
        "status": "ok",
        "command": "insert-after",
        "file": str(target),
        "matches": 1,
        "changed": True,
        "dry_run": False,
    }


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


def test_delete_success_without_within(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("import llm  # noqa: E402\n", encoding="utf-8")

    result = run_needle("delete", str(target), "--text", "  # noqa: E402")

    assert result.returncode == 0
    assert target.read_text(encoding="utf-8") == "import llm\n"


def test_delete_success_with_within(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("import llm  # noqa: E402\nimport os  # noqa: E402\n", encoding="utf-8")

    result = run_needle(
        "delete",
        str(target),
        "--within",
        "import llm  # noqa: E402",
        "--text",
        "  # noqa: E402",
    )

    assert result.returncode == 0
    assert target.read_text(encoding="utf-8") == "import llm\nimport os  # noqa: E402\n"


def test_delete_no_match_failure_does_not_modify_file(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("import llm\n", encoding="utf-8")

    result = run_needle("delete", str(target), "--text", "  # noqa: E402")

    assert result.returncode == 2
    assert target.read_text(encoding="utf-8") == "import llm\n"


def test_delete_multiple_match_failure_does_not_modify_file(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("import llm  # noqa\nimport os  # noqa\n", encoding="utf-8")

    result = run_needle("delete", str(target), "--text", "  # noqa")

    assert result.returncode == 3
    assert target.read_text(encoding="utf-8") == "import llm  # noqa\nimport os  # noqa\n"


def test_delete_missing_context_failure_does_not_modify_file(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("import llm  # noqa\n", encoding="utf-8")

    result = run_needle(
        "delete",
        str(target),
        "--within",
        "import missing  # noqa",
        "--text",
        "  # noqa",
    )

    assert result.returncode == 2
    assert target.read_text(encoding="utf-8") == "import llm  # noqa\n"


def test_delete_duplicate_context_failure_does_not_modify_file(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("import llm  # noqa\nimport llm  # noqa\n", encoding="utf-8")

    result = run_needle(
        "delete",
        str(target),
        "--within",
        "import llm  # noqa",
        "--text",
        "  # noqa",
    )

    assert result.returncode == 3
    assert target.read_text(encoding="utf-8") == "import llm  # noqa\nimport llm  # noqa\n"


def test_delete_missing_inner_text_failure_does_not_modify_file(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("import llm  # noqa\n", encoding="utf-8")

    result = run_needle(
        "delete",
        str(target),
        "--within",
        "import llm  # noqa",
        "--text",
        "  # type: ignore",
    )

    assert result.returncode == 2
    assert target.read_text(encoding="utf-8") == "import llm  # noqa\n"


def test_delete_duplicate_inner_text_failure_does_not_modify_file(
    tmp_path: Path,
) -> None:
    target = tmp_path / "sample.py"
    target.write_text("values = (True, True)\n", encoding="utf-8")

    result = run_needle(
        "delete",
        str(target),
        "--within",
        "values = (True, True)",
        "--text",
        "True",
    )

    assert result.returncode == 3
    assert target.read_text(encoding="utf-8") == "values = (True, True)\n"


def test_delete_dry_run_leaves_file_unchanged(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("import llm  # noqa: E402\n", encoding="utf-8")

    result = run_needle(
        "delete",
        str(target),
        "--text",
        "  # noqa: E402",
        "--dry-run",
    )

    assert result.returncode == 0
    assert target.read_text(encoding="utf-8") == "import llm  # noqa: E402\n"
    assert "-import llm  # noqa: E402" in result.stdout
    assert "+import llm" in result.stdout


def test_delete_json_success_with_within_includes_match_counts(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("import llm  # noqa: E402\nimport os  # noqa: E402\n", encoding="utf-8")

    result = run_needle(
        "delete",
        str(target),
        "--within",
        "import llm  # noqa: E402",
        "--text",
        "  # noqa: E402",
        "--json",
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 0
    assert result.stderr == ""
    assert payload == {
        "status": "ok",
        "command": "delete",
        "file": str(target),
        "matches": 1,
        "changed": True,
        "dry_run": False,
        "context_matches": 1,
        "inner_matches": 1,
    }


def test_delete_json_error_for_missing_inner_text_includes_counts(
    tmp_path: Path,
) -> None:
    target = tmp_path / "sample.py"
    target.write_text("import llm  # noqa\n", encoding="utf-8")

    result = run_needle(
        "delete",
        str(target),
        "--within",
        "import llm  # noqa",
        "--text",
        "  # type: ignore",
        "--json",
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 2
    assert result.stderr == ""
    assert payload["status"] == "error"
    assert payload["command"] == "delete"
    assert payload["file"] == str(target)
    assert payload["matches"] == 0
    assert payload["context_matches"] == 1
    assert payload["inner_matches"] == 0
    assert payload["reason"] == "no_match"


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
