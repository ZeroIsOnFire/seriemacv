from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pydantic import ValidationError
from ruamel.yaml.error import YAMLError

from seriemacv.career import (
    CAREER_FILE,
    add_record,
    dump_section,
    list_section,
    set_profile,
    validate_career,
)
from seriemacv.project import (
    ProjectAlreadyExistsError,
    create_project,
    load_project_configuration,
    validate_project,
)
from seriemacv.renderer import ResumeRenderError, write_resume


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="seriemacv")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create a local career project")
    init_parser.add_argument("path", type=Path)
    init_parser.add_argument("--name", required=True, help="Human-readable project name")
    init_parser.add_argument("--language", choices=("pt-BR", "en"), default="pt-BR")

    validate_parser = subparsers.add_parser(
        "validate", help="Validate a local career project"
    )
    validate_parser.add_argument("path", nargs="?", type=Path, default=Path.cwd())

    career_parser = subparsers.add_parser("career", help="Manage canonical career data")
    career_subparsers = career_parser.add_subparsers(dest="career_command", required=True)

    career_validate = career_subparsers.add_parser(
        "validate", help="Validate career.yml and report actionable diagnostics"
    )
    career_validate.add_argument("path", nargs="?", type=Path, default=Path.cwd())

    profile_parser = career_subparsers.add_parser(
        "set-profile", help="Set one or more profile fields"
    )
    profile_parser.add_argument("path", type=Path)
    for field in (
        "name",
        "title",
        "location",
        "email",
        "phone",
        "linkedin",
        "portfolio",
        "work-preference",
        "work-authorization",
        "notice-period",
    ):
        profile_parser.add_argument(f"--{field}")
    profile_parser.add_argument("--link", action="append", default=[], metavar="NAME=URL")
    profile_parser.add_argument("--language", action="append", default=[])

    _add_experience_parser(career_subparsers)
    _add_education_parser(career_subparsers)
    _add_skill_parser(career_subparsers)
    _add_evidence_parser(career_subparsers)

    list_parser = career_subparsers.add_parser("list", help="Print a validated section")
    list_parser.add_argument("path", type=Path)
    list_parser.add_argument(
        "section",
        choices=("profile", "summary", "experience", "education", "skills", "evidence", "answers", "stories"),
    )

    resume_parser = subparsers.add_parser("resume", help="Render resume artifacts")
    resume_subparsers = resume_parser.add_subparsers(dest="resume_command", required=True)
    render_parser = resume_subparsers.add_parser(
        "render", help="Render an ATS-safe resume from career.yml"
    )
    render_parser.add_argument("path", type=Path)
    render_parser.add_argument("--format", choices=("markdown", "html", "pdf"), required=True)
    return parser


def _add_experience_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("add-experience", help="Add an experience record")
    parser.add_argument("path", type=Path)
    parser.add_argument("--id", required=True)
    parser.add_argument("--company", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date")
    parser.add_argument("--location", default="")
    parser.add_argument("--employment-type", default="")
    parser.add_argument("--highlight", action="append", default=[])


def _add_education_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("add-education", help="Add an education record")
    parser.add_argument("path", type=Path)
    parser.add_argument("--id", required=True)
    parser.add_argument("--institution", required=True)
    parser.add_argument("--degree", required=True)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date")
    parser.add_argument("--field-of-study", default="")
    parser.add_argument("--location", default="")
    parser.add_argument("--highlight", action="append", default=[])


def _add_skill_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("add-skill", help="Add a skill record")
    parser.add_argument("path", type=Path)
    parser.add_argument("--id", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--category", default="")
    parser.add_argument("--level", choices=("beginner", "intermediate", "advanced", "expert"))
    parser.add_argument("--core", action="store_true")
    parser.add_argument("--tag", action="append", default=[])


def _add_evidence_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("add-evidence", help="Add verified or pending evidence")
    parser.add_argument("path", type=Path)
    parser.add_argument("--id", required=True)
    parser.add_argument("--statement", required=True)
    parser.add_argument("--experience-id")
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument("--detail", action="append", default=[])
    parser.add_argument("--verified", action="store_true")


def main(arguments: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(arguments)

    if args.command == "init":
        try:
            project_path = create_project(
                args.path, project_name=args.name, resume_language=args.language
            )
        except (OSError, ValueError, ProjectAlreadyExistsError) as error:
            parser.error(str(error))
        print(f"Created seriemaCV project at {project_path}")
        return 0

    if args.command == "career":
        return _run_career_command(args)

    if args.command == "resume":
        return _run_resume_command(args)

    errors = validate_project(args.path)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f"Valid seriemaCV project: {args.path.expanduser().resolve()}")
    return 0


def _run_career_command(args: argparse.Namespace) -> int:
    career_path = args.path.expanduser().resolve() / CAREER_FILE
    if args.career_command == "validate":
        diagnostics = validate_career(career_path)
        if diagnostics:
            for diagnostic in diagnostics:
                print(diagnostic.format(career_path), file=sys.stderr)
            return 1
        print(f"Valid career document: {career_path}")
        return 0

    try:
        if args.career_command == "set-profile":
            values = {
                key: getattr(args, key)
                for key in (
                    "name", "title", "location", "email", "phone", "linkedin", "portfolio",
                    "work_preference", "work_authorization", "notice_period",
                )
            }
            if args.link:
                values["links"] = _key_values(args.link, "--link")
            if args.language:
                values["languages"] = args.language
            set_profile(career_path, values)
        elif args.career_command == "add-experience":
            add_record(career_path, "experience", {
                "id": args.id, "company": args.company, "title": args.title,
                "start_date": args.start_date, "end_date": args.end_date,
                "location": args.location, "employment_type": args.employment_type,
                "highlights": args.highlight,
            })
        elif args.career_command == "add-education":
            add_record(career_path, "education", {
                "id": args.id, "institution": args.institution, "degree": args.degree,
                "start_date": args.start_date, "end_date": args.end_date,
                "field_of_study": args.field_of_study, "location": args.location,
                "highlights": args.highlight,
            })
        elif args.career_command == "add-skill":
            add_record(career_path, "skills", {
                "id": args.id, "name": args.name, "category": args.category,
                "tags": args.tag, "level": args.level, "core": args.core,
            })
        elif args.career_command == "add-evidence":
            add_record(career_path, "evidence", {
                "id": args.id, "statement": args.statement,
                "experience_id": args.experience_id, "tags": args.tag,
                "details": args.detail, "verified": args.verified,
            })
        elif args.career_command == "list":
            print(dump_section(list_section(career_path, args.section)), end="")
            return 0
        else:  # pragma: no cover - argparse guards this branch
            raise ValueError(f"Unknown career command: {args.career_command}")
    except (OSError, ValueError, ValidationError, YAMLError) as error:
        print(f"{career_path}: {error}", file=sys.stderr)
        return 1

    print(f"Updated career document: {career_path}")
    return 0


def _run_resume_command(args: argparse.Namespace) -> int:
    project_path = args.path.expanduser().resolve()
    career_path = project_path / CAREER_FILE
    configuration_path = project_path / "seriemacv.yml"
    diagnostics = validate_career(career_path)
    if diagnostics:
        for diagnostic in diagnostics:
            print(diagnostic.format(career_path), file=sys.stderr)
        return 1
    try:
        configuration = load_project_configuration(project_path)
    except (OSError, ValueError, ValidationError, YAMLError) as error:
        print(f"{configuration_path}: {error}", file=sys.stderr)
        return 1
    try:
        from seriemacv.career import load_career

        output_path = write_resume(
            project_path, load_career(career_path), configuration.resume_language, args.format
        )
    except (OSError, ResumeRenderError, ValueError, ValidationError, YAMLError) as error:
        print(f"{career_path}: {error}", file=sys.stderr)
        return 1
    print(f"Rendered Markdown resume: {output_path}")
    return 0


def _key_values(values: list[str], option: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        key, separator, item = value.partition("=")
        if not separator or not key or not item:
            raise ValueError(f"{option} must use NAME=VALUE")
        result[key] = item
    return result


if __name__ == "__main__":
    raise SystemExit(main())
