from __future__ import annotations

import argparse
import sys
from pathlib import Path

from seriemacv.project import ProjectAlreadyExistsError, create_project, validate_project


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="seriemacv")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create a local career project")
    init_parser.add_argument("path", type=Path)
    init_parser.add_argument("--name", required=True, help="Human-readable project name")

    validate_parser = subparsers.add_parser(
        "validate", help="Validate a local career project"
    )
    validate_parser.add_argument("path", nargs="?", type=Path, default=Path.cwd())
    return parser


def main(arguments: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(arguments)

    if args.command == "init":
        try:
            project_path = create_project(args.path, project_name=args.name)
        except (OSError, ValueError, ProjectAlreadyExistsError) as error:
            parser.error(str(error))
        print(f"Created seriemaCV project at {project_path}")
        return 0

    errors = validate_project(args.path)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f"Valid seriemaCV project: {args.path.expanduser().resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
