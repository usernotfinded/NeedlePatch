"""Command line interface for NeedlePatch."""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


EXIT_SUCCESS = 0
EXIT_GENERIC_ERROR = 1
EXIT_NO_MATCH = 2
EXIT_MULTIPLE_MATCHES = 3
EXIT_INVALID_ARGUMENTS = 4
EXIT_FILE_ERROR = 5

REASON_NO_MATCH = "no_match"
REASON_MULTIPLE_MATCHES = "multiple_matches"
REASON_INVALID_ARGUMENTS = "invalid_arguments"
REASON_FILE_ERROR = "file_error"
REASON_GENERIC_ERROR = "generic_error"


class ParserError(Exception):
    """Raised instead of exiting directly from argparse."""


class NeedleArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ParserError(message)


@dataclass(frozen=True)
class CommandError(Exception):
    reason: str
    hint: str
    exit_code: int
    matches: int = 0
    context_matches: int | None = None
    inner_matches: int | None = None


def build_parser() -> argparse.ArgumentParser:
    parser = NeedleArgumentParser(
        prog="needle",
        description="Safe shell commands for tiny exact text edits.",
    )
    subparsers = parser.add_subparsers(dest="command")

    view = subparsers.add_parser("view", help="inspect exact text")
    view.add_argument("file")
    view.add_argument("--from", dest="from_line", type=int)
    view.add_argument("--to", dest="to_line", type=int)

    replace = subparsers.add_parser("replace", help="replace unique exact text")
    replace.add_argument("file")
    replace.add_argument("--old")
    replace.add_argument("--new")
    replace.add_argument("--dry-run", action="store_true", dest="dry_run")
    replace.add_argument("--json", action="store_true", dest="json_output")

    replace_inside = subparsers.add_parser(
        "replace-inside",
        help="replace tiny text inside a unique exact context",
    )
    replace_inside.add_argument("file")
    replace_inside.add_argument("--within")
    replace_inside.add_argument("--old")
    replace_inside.add_argument("--new")
    replace_inside.add_argument("--dry-run", action="store_true", dest="dry_run")
    replace_inside.add_argument("--json", action="store_true", dest="json_output")

    append = subparsers.add_parser("append", help="add suffix after a unique match")
    append.add_argument("file")
    append.add_argument("--match")
    append.add_argument("--text")
    append.add_argument("--dry-run", action="store_true", dest="dry_run")
    append.add_argument("--json", action="store_true", dest="json_output")

    insert_after = subparsers.add_parser(
        "insert-after",
        help="insert text after a unique match",
    )
    insert_after.add_argument("file")
    insert_after.add_argument("--match")
    insert_after.add_argument("--text")
    insert_after.add_argument("--dry-run", action="store_true", dest="dry_run")
    insert_after.add_argument("--json", action="store_true", dest="json_output")

    delete = subparsers.add_parser("delete", help="delete unique exact text")
    delete.add_argument("file")
    delete.add_argument("--text")
    delete.add_argument("--within")
    delete.add_argument("--dry-run", action="store_true", dest="dry_run")
    delete.add_argument("--json", action="store_true", dest="json_output")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    try:
        args = parser.parse_args(raw_argv)
        if args.command is None:
            raise ParserError("a command is required")

        if args.command == "view":
            return handle_view(args)
        if args.command == "replace":
            return handle_replace(args)
        if args.command == "replace-inside":
            return handle_replace_inside(args)
        if args.command == "append":
            return handle_append(args)
        if args.command == "insert-after":
            return handle_insert_after(args)
        if args.command == "delete":
            return handle_delete(args)
        raise ParserError(f"unknown command: {args.command}")
    except ParserError as exc:
        return handle_parse_error(raw_argv, str(exc))
    except CommandError as exc:
        return handle_command_error(raw_argv, exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        command, file_name, wants_json = command_context(raw_argv)
        if wants_json:
            print_json(
                error_payload(
                    command=command,
                    file=file_name,
                    matches=0,
                    reason=REASON_GENERIC_ERROR,
                    hint=str(exc) or "Unexpected error.",
                )
            )
        else:
            print(f"error: {exc}", file=sys.stderr)
        return EXIT_GENERIC_ERROR


def handle_view(args: argparse.Namespace) -> int:
    if args.from_line is None or args.to_line is None:
        raise CommandError(
            reason=REASON_INVALID_ARGUMENTS,
            hint="view requires --from and --to.",
            exit_code=EXIT_INVALID_ARGUMENTS,
        )
    if args.from_line < 1:
        raise CommandError(
            reason=REASON_INVALID_ARGUMENTS,
            hint="--from must be 1 or greater.",
            exit_code=EXIT_INVALID_ARGUMENTS,
        )
    if args.to_line < args.from_line:
        raise CommandError(
            reason=REASON_INVALID_ARGUMENTS,
            hint="--to must be greater than or equal to --from.",
            exit_code=EXIT_INVALID_ARGUMENTS,
        )

    content = read_file(Path(args.file))
    lines = content.splitlines()
    for line_number in range(args.from_line, args.to_line + 1):
        if line_number <= len(lines):
            print(f"{line_number} | {lines[line_number - 1]}")
    return EXIT_SUCCESS


def handle_replace(args: argparse.Namespace) -> int:
    validate_required_text(args.old, "--old")
    validate_present(args.new, "--new")

    path = Path(args.file)
    content = read_file(path)
    matches = content.count(args.old)
    if matches == 0:
        raise CommandError(
            reason=REASON_NO_MATCH,
            hint="No exact match found for --old.",
            exit_code=EXIT_NO_MATCH,
            matches=matches,
        )
    if matches > 1:
        raise CommandError(
            reason=REASON_MULTIPLE_MATCHES,
            hint="Use a more specific exact text or replace-inside with --within.",
            exit_code=EXIT_MULTIPLE_MATCHES,
            matches=matches,
        )

    updated = content.replace(args.old, args.new, 1)
    return finish_edit(
        args=args,
        path=path,
        original=content,
        updated=updated,
        matches=matches,
    )


def handle_replace_inside(args: argparse.Namespace) -> int:
    validate_required_text(args.within, "--within")
    validate_required_text(args.old, "--old")
    validate_present(args.new, "--new")

    path = Path(args.file)
    content = read_file(path)
    context_matches = content.count(args.within)
    if context_matches == 0:
        raise CommandError(
            reason=REASON_NO_MATCH,
            hint="No exact match found for --within.",
            exit_code=EXIT_NO_MATCH,
            matches=context_matches,
            context_matches=context_matches,
        )
    if context_matches > 1:
        raise CommandError(
            reason=REASON_MULTIPLE_MATCHES,
            hint="Use a larger exact context for --within.",
            exit_code=EXIT_MULTIPLE_MATCHES,
            matches=context_matches,
            context_matches=context_matches,
        )

    inner_matches = args.within.count(args.old)
    if inner_matches == 0:
        raise CommandError(
            reason=REASON_NO_MATCH,
            hint="No exact match found for --old inside --within.",
            exit_code=EXIT_NO_MATCH,
            matches=inner_matches,
            context_matches=context_matches,
            inner_matches=inner_matches,
        )
    if inner_matches > 1:
        raise CommandError(
            reason=REASON_MULTIPLE_MATCHES,
            hint="Use a more specific --within context or --old text.",
            exit_code=EXIT_MULTIPLE_MATCHES,
            matches=inner_matches,
            context_matches=context_matches,
            inner_matches=inner_matches,
        )

    updated_context = args.within.replace(args.old, args.new, 1)
    updated = content.replace(args.within, updated_context, 1)
    return finish_edit(
        args=args,
        path=path,
        original=content,
        updated=updated,
        matches=inner_matches,
        context_matches=context_matches,
        inner_matches=inner_matches,
    )


def handle_append(args: argparse.Namespace) -> int:
    validate_required_text(args.match, "--match")
    validate_present(args.text, "--text")

    path = Path(args.file)
    content = read_file(path)
    matches = content.count(args.match)
    if matches == 0:
        raise CommandError(
            reason=REASON_NO_MATCH,
            hint="No exact match found for --match.",
            exit_code=EXIT_NO_MATCH,
            matches=matches,
        )
    if matches > 1:
        raise CommandError(
            reason=REASON_MULTIPLE_MATCHES,
            hint="Use a more specific exact match.",
            exit_code=EXIT_MULTIPLE_MATCHES,
            matches=matches,
        )

    updated = content.replace(args.match, args.match + args.text, 1)
    return finish_edit(
        args=args,
        path=path,
        original=content,
        updated=updated,
        matches=matches,
    )


def handle_insert_after(args: argparse.Namespace) -> int:
    validate_required_text(args.match, "--match")
    validate_required_text(args.text, "--text")

    path = Path(args.file)
    content = read_file(path)
    matches = content.count(args.match)
    if matches == 0:
        raise CommandError(
            reason=REASON_NO_MATCH,
            hint="No exact match found for --match.",
            exit_code=EXIT_NO_MATCH,
            matches=matches,
        )
    if matches > 1:
        raise CommandError(
            reason=REASON_MULTIPLE_MATCHES,
            hint="Use a more specific exact match.",
            exit_code=EXIT_MULTIPLE_MATCHES,
            matches=matches,
        )

    updated = insert_after_match(content, args.match, args.text)
    return finish_edit(
        args=args,
        path=path,
        original=content,
        updated=updated,
        matches=matches,
    )


def handle_delete(args: argparse.Namespace) -> int:
    validate_required_text(args.text, "--text")

    path = Path(args.file)
    content = read_file(path)
    if args.within is None:
        matches = content.count(args.text)
        if matches == 0:
            raise CommandError(
                reason=REASON_NO_MATCH,
                hint="No exact match found for --text.",
                exit_code=EXIT_NO_MATCH,
                matches=matches,
            )
        if matches > 1:
            raise CommandError(
                reason=REASON_MULTIPLE_MATCHES,
                hint="Use --within with a larger exact context.",
                exit_code=EXIT_MULTIPLE_MATCHES,
                matches=matches,
            )

        updated = content.replace(args.text, "", 1)
        return finish_edit(
            args=args,
            path=path,
            original=content,
            updated=updated,
            matches=matches,
        )

    validate_required_text(args.within, "--within")
    context_matches = content.count(args.within)
    if context_matches == 0:
        raise CommandError(
            reason=REASON_NO_MATCH,
            hint="No exact match found for --within.",
            exit_code=EXIT_NO_MATCH,
            matches=context_matches,
            context_matches=context_matches,
        )
    if context_matches > 1:
        raise CommandError(
            reason=REASON_MULTIPLE_MATCHES,
            hint="Use a larger exact context for --within.",
            exit_code=EXIT_MULTIPLE_MATCHES,
            matches=context_matches,
            context_matches=context_matches,
        )

    inner_matches = args.within.count(args.text)
    if inner_matches == 0:
        raise CommandError(
            reason=REASON_NO_MATCH,
            hint="No exact match found for --text inside --within.",
            exit_code=EXIT_NO_MATCH,
            matches=inner_matches,
            context_matches=context_matches,
            inner_matches=inner_matches,
        )
    if inner_matches > 1:
        raise CommandError(
            reason=REASON_MULTIPLE_MATCHES,
            hint="Use a more specific --within context or --text.",
            exit_code=EXIT_MULTIPLE_MATCHES,
            matches=inner_matches,
            context_matches=context_matches,
            inner_matches=inner_matches,
        )

    updated_context = args.within.replace(args.text, "", 1)
    updated = content.replace(args.within, updated_context, 1)
    return finish_edit(
        args=args,
        path=path,
        original=content,
        updated=updated,
        matches=inner_matches,
        context_matches=context_matches,
        inner_matches=inner_matches,
    )


def finish_edit(
    *,
    args: argparse.Namespace,
    path: Path,
    original: str,
    updated: str,
    matches: int,
    context_matches: int | None = None,
    inner_matches: int | None = None,
) -> int:
    diff = make_diff(path, original, updated)
    changed = not args.dry_run and updated != original
    if changed:
        write_file(path, updated)

    if args.json_output:
        payload: dict[str, Any] = {
            "status": "ok",
            "command": args.command,
            "file": str(path),
            "matches": matches,
            "changed": changed,
            "dry_run": bool(args.dry_run),
        }
        if context_matches is not None:
            payload["context_matches"] = context_matches
        if inner_matches is not None:
            payload["inner_matches"] = inner_matches
        if args.dry_run:
            payload["diff"] = diff
        print_json(payload)
    elif args.dry_run:
        print(diff, end="" if diff.endswith("\n") else "\n")

    return EXIT_SUCCESS


def insert_after_match(content: str, match: str, text: str) -> str:
    start = content.find(match)
    end = start + len(match)
    prefix = content[:end]
    suffix = content[end:]
    line_separator, suffix_after_separator = split_leading_line_separator(suffix)

    if line_separator:
        insertion = text
        if not insertion.startswith(("\n", "\r")):
            insertion = line_separator + insertion
        if suffix_after_separator and not insertion.endswith(("\n", "\r")):
            insertion += line_separator
        return prefix + insertion + suffix_after_separator

    insertion = text
    if ends_with_line_separator(prefix):
        if suffix and not insertion.endswith(("\n", "\r")):
            insertion += "\n"
    elif not suffix and not insertion.startswith(("\n", "\r")):
        insertion = "\n" + insertion

    return prefix + insertion + suffix


def split_leading_line_separator(text: str) -> tuple[str, str]:
    if text.startswith("\r\n"):
        return "\r\n", text[2:]
    if text.startswith("\n"):
        return "\n", text[1:]
    if text.startswith("\r"):
        return "\r", text[1:]
    return "", text


def ends_with_line_separator(text: str) -> bool:
    return text.endswith(("\n", "\r"))


def validate_present(value: str | None, flag: str) -> None:
    if value is None:
        raise CommandError(
            reason=REASON_INVALID_ARGUMENTS,
            hint=f"{flag} is required.",
            exit_code=EXIT_INVALID_ARGUMENTS,
        )


def validate_required_text(value: str | None, flag: str) -> None:
    validate_present(value, flag)
    if value == "":
        raise CommandError(
            reason=REASON_INVALID_ARGUMENTS,
            hint=f"{flag} must not be empty.",
            exit_code=EXIT_INVALID_ARGUMENTS,
        )


def read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CommandError(
            reason=REASON_FILE_ERROR,
            hint=str(exc),
            exit_code=EXIT_FILE_ERROR,
        ) from exc
    except UnicodeDecodeError as exc:
        raise CommandError(
            reason=REASON_FILE_ERROR,
            hint=str(exc),
            exit_code=EXIT_FILE_ERROR,
        ) from exc


def write_file(path: Path, content: str) -> None:
    try:
        path.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise CommandError(
            reason=REASON_FILE_ERROR,
            hint=str(exc),
            exit_code=EXIT_FILE_ERROR,
        ) from exc


def make_diff(path: Path, original: str, updated: str) -> str:
    diff_lines = list(
        difflib.unified_diff(
            original.splitlines(),
            updated.splitlines(),
            fromfile=f"{path}\tbefore",
            tofile=f"{path}\tafter",
            lineterm="",
        )
    )
    return "\n".join(diff_lines) + ("\n" if diff_lines else "")


def handle_parse_error(argv: Sequence[str], message: str) -> int:
    command, file_name, wants_json = command_context(argv)
    if wants_json:
        print_json(
            error_payload(
                command=command,
                file=file_name,
                matches=0,
                reason=REASON_INVALID_ARGUMENTS,
                hint=message,
            )
        )
    else:
        print(f"error: {message}", file=sys.stderr)
    return EXIT_INVALID_ARGUMENTS


def handle_command_error(argv: Sequence[str], exc: CommandError) -> int:
    command, file_name, wants_json = command_context(argv)
    if wants_json:
        payload = error_payload(
            command=command,
            file=file_name,
            matches=exc.matches,
            reason=exc.reason,
            hint=exc.hint,
        )
        if exc.context_matches is not None:
            payload["context_matches"] = exc.context_matches
        if exc.inner_matches is not None:
            payload["inner_matches"] = exc.inner_matches
        print_json(payload)
    else:
        print(f"error: {exc.hint}", file=sys.stderr)
    return exc.exit_code


def command_context(argv: Sequence[str]) -> tuple[str, str, bool]:
    command = argv[0] if argv else ""
    file_name = argv[1] if len(argv) > 1 and not argv[1].startswith("-") else ""
    wants_json = "--json" in argv
    return command, file_name, wants_json


def error_payload(
    *,
    command: str,
    file: str,
    matches: int,
    reason: str,
    hint: str,
) -> dict[str, Any]:
    return {
        "status": "error",
        "command": command,
        "file": file,
        "matches": matches,
        "reason": reason,
        "hint": hint,
    }


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, separators=(",", ":")))


if __name__ == "__main__":
    sys.exit(main())
