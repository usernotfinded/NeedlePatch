#!/usr/bin/env python3
"""Compare small normal diffs with equivalent NeedlePatch commands."""

from __future__ import annotations

import argparse
import difflib
import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Case:
    name: str
    original: str
    result: str
    needle_command: str
    recommended: str
    reason: str


@dataclass(frozen=True)
class Row:
    case_name: str
    normal_diff_chars: int
    needle_command_chars: int
    shorter: str
    recommended: str
    reason: str


CASES = [
    Case(
        name="append noqa",
        original="import llm\n",
        result="import llm  # noqa: E402\n",
        needle_command=(
            'needle append file.py --match "import llm" --text "  # noqa: E402"'
        ),
        recommended="needle",
        reason="Good when the suffix target is unique.",
    ),
    Case(
        name="toggle boolean",
        original="debug_enabled = True\n",
        result="debug_enabled = False\n",
        needle_command=(
            'needle replace-inside file.py --within "debug_enabled = True" '
            '--old "True" --new "False"'
        ),
        recommended="needle",
        reason="Context makes a generic token safer to edit.",
    ),
    Case(
        name="replace tuple item",
        original="for hie_lite_enabled in (False, True):\n",
        result="for hie_lite_enabled in (False,):\n",
        needle_command=(
            'needle replace-inside file.py '
            '--within "for hie_lite_enabled in (False, True):" '
            '--old "(False, True)" --new "(False,)"'
        ),
        recommended="needle",
        reason="Useful when one tuple expression changes.",
    ),
    Case(
        name="insert one line",
        original="init_config()\nrun_app()\n",
        result="init_config()\nvalidate_config()\nrun_app()\n",
        needle_command=(
            'needle insert-after file.py --match "init_config()" '
            '--text "validate_config()"'
        ),
        recommended="needle",
        reason="Useful for one short line after a unique anchor.",
    ),
    Case(
        name="delete suffix",
        original="import llm  # noqa: E402\n",
        result="import llm\n",
        needle_command=(
            'needle delete file.py --within "import llm  # noqa: E402" '
            '--text "  # noqa: E402"'
        ),
        recommended="needle",
        reason="Scoped deletion with --within limits the target.",
    ),
    Case(
        name="long unique line",
        original=(
            "SERVICE_CONFIG = {'name': 'analytics', 'region': 'eu-west-1', "
            "'timeout': 30, 'retries': 2, 'enabled': True}\n"
        ),
        result=(
            "SERVICE_CONFIG = {'name': 'analytics', 'region': 'eu-west-1', "
            "'timeout': 31, 'retries': 2, 'enabled': True}\n"
        ),
        needle_command=(
            "needle replace-inside "
            "src/services/analytics/runtime/defaults/generated/"
            "production_service_config_snapshot.py "
            "--within \"SERVICE_CONFIG = {'name': 'analytics', "
            "'region': 'eu-west-1', 'timeout': 30, 'retries': 2, "
            "'enabled': True}\" --old \"'timeout': 30\" --new \"'timeout': 31\""
        ),
        recommended="diff",
        reason="Not clearly better when context is long.",
    ),
    Case(
        name="multi-line logic change",
        original=(
            "if user.is_active:\n"
            "    send_email(user)\n"
            "return True\n"
        ),
        result=(
            "if user.is_active and user.email:\n"
            "    send_email(user)\n"
            "    record_delivery(user)\n"
            "return user.is_active\n"
        ),
        needle_command=(
            "not recommended: use apply_patch or a normal diff for multi-line "
            "logic changes"
        ),
        recommended="diff",
        reason="Out of scope for NeedlePatch.",
    ),
    Case(
        name="ambiguous target",
        original=(
            "if account.enabled:\n"
            "    enabled = True\n"
            "    run_sync()\n"
            "if project.enabled:\n"
            "    enabled = True\n"
            "    run_sync()\n"
            "if feature.enabled:\n"
            "    enabled = True\n"
            "    run_sync()\n"
        ),
        result=(
            "if account.enabled:\n"
            "    enabled = True\n"
            "    run_sync()\n"
            "if project.enabled:\n"
            "    enabled = False\n"
            "    run_sync()\n"
            "if feature.enabled:\n"
            "    enabled = True\n"
            "    run_sync()\n"
        ),
        needle_command=(
            "needle replace-inside "
            "src/services/sync/runtime/generated/project_feature_switches_snapshot.py "
            '--within "if project.enabled:\\n'
            '    enabled = True\\n    run_sync()" --old "enabled = True" '
            '--new "enabled = False"'
        ),
        recommended="tie",
        reason="Needs bulky context; a normal diff may be clearer.",
    ),
    Case(
        name="function-level rewrite",
        original=(
            "def score(items):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        total += item.value\n"
            "    return total\n"
        ),
        result=(
            "def score(items):\n"
            "    values = [item.value for item in items if item.enabled]\n"
            "    if not values:\n"
            "        return 0\n"
            "    return sum(values) / len(values)\n"
        ),
        needle_command=(
            "not recommended: use apply_patch or a normal diff for "
            "function-level rewrites"
        ),
        recommended="diff",
        reason="Out of scope for NeedlePatch.",
    ),
]

SUMMARY = (
    "NeedlePatch can be shorter for some out-of-scope examples, but that does "
    "not mean it should be used. Recommendation is based on clarity, safety, "
    "and scope, not only character count. For larger edits, use apply_patch or "
    "a normal diff."
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare normal diff size with NeedlePatch command size.",
    )
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    rows = [build_row(case) for case in CASES]
    if args.json_output:
        payload = {"summary": SUMMARY, "cases": [asdict(row) for row in rows]}
        print(json.dumps(payload, indent=2))
    else:
        print_table(rows)
        print()
        print(SUMMARY)
    return 0


def build_row(case: Case) -> Row:
    diff_text = normal_diff(case)
    diff_chars = len(diff_text)
    command_chars = len(case.needle_command)
    if diff_chars < command_chars:
        shorter = "diff"
    elif command_chars < diff_chars:
        shorter = "needle"
    else:
        shorter = "tie"
    return Row(
        case_name=case.name,
        normal_diff_chars=diff_chars,
        needle_command_chars=command_chars,
        shorter=shorter,
        recommended=case.recommended,
        reason=case.reason,
    )


def normal_diff(case: Case) -> str:
    return "".join(
        difflib.unified_diff(
            case.original.splitlines(keepends=True),
            case.result.splitlines(keepends=True),
            fromfile="before/file.py",
            tofile="after/file.py",
        )
    )


def print_table(rows: list[Row]) -> None:
    headers = [
        "case name",
        "normal diff chars",
        "needle command chars",
        "shorter",
        "recommended",
        "reason",
    ]
    table = [
        [
            row.case_name,
            str(row.normal_diff_chars),
            str(row.needle_command_chars),
            row.shorter,
            row.recommended,
            row.reason,
        ]
        for row in rows
    ]
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in table))
        for index in range(len(headers))
    ]

    print(format_row(headers, widths))
    print(format_row(["-" * width for width in widths], widths))
    for row in table:
        print(format_row(row, widths))


def format_row(values: list[str], widths: list[int]) -> str:
    return " | ".join(
        value.ljust(width)
        for value, width in zip(values, widths, strict=True)
    )


if __name__ == "__main__":
    raise SystemExit(main())
