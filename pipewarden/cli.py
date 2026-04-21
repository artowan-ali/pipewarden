"""Minimal CLI entry-point for PipeWarden."""

from __future__ import annotations

import argparse
import importlib
import sys
from typing import Any

from pipewarden.reporter import format_json_report, format_text_report, write_report
from pipewarden.runner import run_checks


def _load_checks_from_module(module_path: str) -> list[Any]:
    """Import *module_path* and return its ``CHECKS`` list."""
    try:
        mod = importlib.import_module(module_path)
    except ModuleNotFoundError as exc:
        print(f"[error] Cannot import '{module_path}': {exc}", file=sys.stderr)
        sys.exit(2)
    checks = getattr(mod, "CHECKS", None)
    if checks is None:
        print(f"[error] Module '{module_path}' has no 'CHECKS' attribute.", file=sys.stderr)
        sys.exit(2)
    return checks  # type: ignore[return-value]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pipewarden",
        description="Validate and monitor ETL pipeline health.",
    )
    parser.add_argument(
        "module",
        help="Dotted Python module path that exposes a CHECKS list, e.g. myproject.pipeline_checks",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        dest="fmt",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        default=None,
        help="Write report to FILE instead of stdout",
    )
    parser.add_argument(
        "--fail-on-warn",
        action="store_true",
        default=False,
        help="Exit with code 1 when any check warns",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    checks = _load_checks_from_module(args.module)
    result = run_checks(checks)

    if args.output:
        write_report(result, args.output, fmt=args.fmt)
    else:
        if args.fmt == "json":
            print(format_json_report(result))
        else:
            print(format_text_report(result))

    if not result.healthy:
        return 1
    if args.fail_on_warn and any(r.status.value == "warned" for r in result.results):
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
