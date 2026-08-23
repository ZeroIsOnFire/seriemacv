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
    list_locales,
    load_localized_career,
    set_profile,
    validate_career,
    validate_locale,
)
from seriemacv.jobs import (
    JOB_DIRECTORY,
    JobImportPayload,
    JobSource,
    create_job,
    dump_job,
    job_path,
    load_job,
    load_jobs,
    load_json_payload,
    load_yaml_payload,
    source_format_for_path,
    validate_job,
    validate_jobs,
)
from seriemacv.project import (
    ProjectAlreadyExistsError,
    create_project,
    load_project_configuration,
    load_template,
    validate_project,
)
from seriemacv.renderer import ResumeRenderError, write_resume
from seriemacv.importer import ImportError, apply_proposal, load_proposal, new_proposal, save_proposal
from seriemacv.styles import STYLE_IDS, list_styles


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="seriemacv")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create a local career project")
    init_parser.add_argument("path", type=Path)
    init_parser.add_argument("--name", required=True, help="Human-readable project name")
    init_parser.add_argument("--language", default="pt-BR", help="Default BCP 47 resume locale")
    init_parser.add_argument("--style", choices=STYLE_IDS, default="clean")

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

    locale_parser = career_subparsers.add_parser("locale", help="Manage localized resume content")
    locale_subparsers = locale_parser.add_subparsers(dest="locale_command", required=True)
    locale_list = locale_subparsers.add_parser("list", help="List available locales")
    locale_list.add_argument("path", type=Path)
    locale_validate = locale_subparsers.add_parser("validate", help="Validate one locale")
    locale_validate.add_argument("path", type=Path)
    locale_validate.add_argument("--language", required=True)

    import_parser = career_subparsers.add_parser("import", help="Propose career data from a local resume")
    import_subparsers = import_parser.add_subparsers(dest="import_command", required=True)
    import_propose = import_subparsers.add_parser("propose")
    import_propose.add_argument("path", type=Path)
    import_propose.add_argument("source", type=Path)
    import_propose.add_argument("--language", required=True)
    import_list = import_subparsers.add_parser("list")
    import_list.add_argument("path", type=Path)
    import_show = import_subparsers.add_parser("show")
    import_show.add_argument("path", type=Path)
    import_show.add_argument("id")
    import_apply = import_subparsers.add_parser("apply")
    import_apply.add_argument("path", type=Path)
    import_apply.add_argument("id")

    profile_parser = career_subparsers.add_parser(
        "set-profile", help="Set one or more profile fields"
    )
    profile_parser.add_argument("path", type=Path)
    for field in (
        "name",
        "email",
        "phone",
        "linkedin",
        "portfolio",
    ):
        profile_parser.add_argument(f"--{field}")
    profile_parser.add_argument("--link", action="append", default=[], metavar="NAME=URL")

    _add_experience_parser(career_subparsers)
    _add_education_parser(career_subparsers)
    _add_skill_parser(career_subparsers)
    _add_evidence_parser(career_subparsers)

    list_parser = career_subparsers.add_parser("list", help="Print a validated section")
    list_parser.add_argument("path", type=Path)
    list_parser.add_argument(
        "section",
        choices=("profile", "experience", "education", "skills", "evidence", "answers", "stories"),
    )

    resume_parser = subparsers.add_parser("resume", help="Render resume artifacts")
    resume_subparsers = resume_parser.add_subparsers(dest="resume_command", required=True)
    render_parser = resume_subparsers.add_parser(
        "render", help="Render an ATS-safe resume from career.yml"
    )
    render_parser.add_argument("path", type=Path)
    render_parser.add_argument("--format", choices=("markdown", "html", "pdf", "docx"), required=True, action="append")
    render_parser.add_argument("--style", choices=STYLE_IDS)
    render_parser.add_argument("--language")
    resume_subparsers.add_parser(
        "styles", help="List built-in resume styles and their capabilities"
    )

    template_parser = subparsers.add_parser(
        "template", help="Read built-in structured-data templates"
    )
    template_subparsers = template_parser.add_subparsers(
        dest="template_command", required=True
    )
    template_show = template_subparsers.add_parser(
        "show", help="Print a career template for an external tool"
    )
    template_show.add_argument("path", type=Path)
    template_show.add_argument("name", choices=("career",))
    return parser


def _add_experience_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("add-experience", help="Add an experience record")
    parser.add_argument("path", type=Path)
    parser.add_argument("--id", required=True)
    parser.add_argument("--company", required=True)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date")


def _add_education_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("add-education", help="Add an education record")
    parser.add_argument("path", type=Path)
    parser.add_argument("--id", required=True)
    parser.add_argument("--institution", required=True)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date")


def _add_skill_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("add-skill", help="Add a skill record")
    parser.add_argument("path", type=Path)
    parser.add_argument("--id", required=True)
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


def _add_job_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("add", help="Add a job from explicit fields")
    parser.add_argument("path", type=Path)
    _add_job_fields(parser, required_identity=True)
    parser.add_argument("--description", required=True)


def _add_job_import_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("import", help="Import a structured local JSON or YAML job")
    parser.add_argument("path", type=Path)
    parser.add_argument("source", type=Path)


def _add_job_fields(parser: argparse.ArgumentParser, *, required_identity: bool) -> None:
    parser.add_argument("--id", required=required_identity)
    parser.add_argument("--title", required=required_identity)
    parser.add_argument("--company", default="")
    parser.add_argument("--location", default="")
    parser.add_argument("--work-model", default="")
    parser.add_argument("--employment-type", default="")
    parser.add_argument("--seniority", default="")
    parser.add_argument("--language", default="")
    parser.add_argument("--salary-range", default="")
    parser.add_argument("--requirement", action="append", default=[], metavar="ID=TEXT")
    parser.add_argument(
        "--preferred-requirement", action="append", default=[], metavar="ID=TEXT"
    )


def main(arguments: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(arguments)

    if args.command == "init":
        try:
            project_path = create_project(
                args.path,
                project_name=args.name,
                resume_language=args.language,
                resume_style=args.style,
            )
        except (OSError, ValueError, ProjectAlreadyExistsError) as error:
            parser.error(str(error))
        print(f"Created seriemaCV project at {project_path}")
        return 0

    if args.command == "career":
        return _run_career_command(args)

    if args.command == "resume":
        return _run_resume_command(args)

    if args.command == "template":
        try:
            print(load_template(args.path, args.name), end="")
        except OSError as error:
            print(f"{args.path}: {error}", file=sys.stderr)
            return 1
        return 0

    errors = validate_project(args.path)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f"Valid seriemaCV project: {args.path.expanduser().resolve()}")
    return 0


def _run_career_command(args: argparse.Namespace) -> int:
    if args.career_command == "import":
        project_path = args.path.expanduser().resolve()
        try:
            if args.import_command == "list":
                for item in sorted((project_path / "proposals").glob("import-*.yml")):
                    print(item.stem)
                return 0
            if args.import_command == "show":
                print(dump_section(load_proposal(project_path, args.id)), end="")
                return 0
            if args.import_command == "apply":
                career_path, translated_path = apply_proposal(project_path, args.id)
                print(f"Applied import proposal to: {career_path}, {translated_path}")
                return 0
            config = load_project_configuration(project_path)
            if config.nuextract is None:
                raise ImportError("configure nuextract in seriemacv.yml before importing")
            proposal = new_proposal(project_path, args.source, args.language, config.nuextract)
            print(f"Created import proposal: {save_proposal(project_path, proposal)}")
            return 0
        except (OSError, ValueError, ValidationError, YAMLError, ImportError) as error:
            print(f"{project_path}: {error}", file=sys.stderr)
            return 1
    if args.career_command == "locale":
        project_path = args.path.expanduser().resolve()
        if args.locale_command == "list":
            for locale in list_locales(project_path):
                print(locale)
            return 0
        diagnostics = validate_locale(project_path, args.language)
        if diagnostics:
            for diagnostic in diagnostics:
                print(diagnostic.format(project_path / "career.locales" / f"{args.language}.yml"), file=sys.stderr)
            return 1
        print(f"Valid locale document: {args.language}")
        return 0
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
                    "name", "email", "phone", "linkedin", "portfolio",
                )
            }
            if args.link:
                values["links"] = _key_values(args.link, "--link")
            set_profile(career_path, values)
        elif args.career_command == "add-experience":
            add_record(career_path, "experience", {
                "id": args.id, "company": args.company, "start_date": args.start_date, "end_date": args.end_date,
            })
        elif args.career_command == "add-education":
            add_record(career_path, "education", {
                "id": args.id, "institution": args.institution, "start_date": args.start_date, "end_date": args.end_date,
            })
        elif args.career_command == "add-skill":
            add_record(career_path, "skills", {
                "id": args.id, "tags": args.tag, "level": args.level, "core": args.core,
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
    if args.resume_command == "styles":
        for style in list_styles():
            ats = "ATS-safe" if style.ats_safe else "experimental, not ATS-safe"
            formats = ",".join(style.supported_formats)
            print(f"{style.id}\t{style.name}\t{style.layout}\t{ats}\t{formats}")
        return 0

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
        style_id = args.style or configuration.resume_style
        locale = args.language or configuration.resume_language
        career = load_localized_career(project_path, locale)
        output_paths = [write_resume(project_path, career, locale, output_format, style_id=style_id) for output_format in args.format]
    except (OSError, ResumeRenderError, ValueError, ValidationError, YAMLError) as error:
        print(f"{career_path}: {error}", file=sys.stderr)
        return 1
    print(f"Rendered {', '.join(item.upper() for item in args.format)} resume using {style_id}: {', '.join(str(path) for path in output_paths)}")
    return 0


def _run_jobs_command(args: argparse.Namespace) -> int:
    project_path = args.path.expanduser().resolve()
    try:
        if args.jobs_command == "validate":
            if args.id:
                document_path = job_path(project_path, args.id)
                diagnostics = [(document_path, item) for item in validate_job(document_path)]
            else:
                diagnostics = validate_jobs(project_path)
            if diagnostics:
                for invalid_job_path, diagnostic in diagnostics:
                    print(diagnostic.format(invalid_job_path), file=sys.stderr)
                return 1
            print(f"Valid job document(s): {project_path / JOB_DIRECTORY}")
            return 0

        if args.jobs_command == "list":
            print(dump_job(load_jobs(project_path)), end="")
            return 0

        if args.jobs_command == "show":
            document_path = job_path(project_path, args.id)
            diagnostics = validate_job(document_path)
            if diagnostics:
                for diagnostic in diagnostics:
                    print(diagnostic.format(document_path), file=sys.stderr)
                return 1
            print(dump_job(load_job(document_path)), end="")
            return 0

        if args.jobs_command == "add":
            payload = _job_payload_from_args(args)
            source = JobSource(format="manual", content=args.description)
        elif args.jobs_command == "import":
            source_path = args.source.expanduser().resolve()
            source_content = source_path.read_text(encoding="utf-8")
            source_format = source_format_for_path(source_path)
            if source_format == "json":
                payload = load_json_payload(source_content)
            else:
                payload = load_yaml_payload(source_content)
            source = JobSource(
                format=source_format, filename=source_path.name, content=source_content
            )
        else:  # pragma: no cover - argparse guards this branch
            raise ValueError(f"Unknown jobs command: {args.jobs_command}")

        saved_job_path = create_job(project_path, payload, source)
    except (OSError, ValueError, ValidationError, YAMLError) as error:
        print(f"{project_path / JOB_DIRECTORY}: {error}", file=sys.stderr)
        return 1

    print(f"Saved job document: {saved_job_path}")
    return 0


def _job_payload_from_args(args: argparse.Namespace) -> JobImportPayload:
    requirements = _requirements_from_args(args.requirement, "required")
    requirements.extend(_requirements_from_args(args.preferred_requirement, "preferred"))
    return JobImportPayload(
        schema_version=1,
        id=args.id,
        title=args.title,
        description=args.description,
        company=args.company,
        location=args.location,
        work_model=args.work_model,
        employment_type=args.employment_type,
        seniority=args.seniority,
        language=args.language,
        salary_range=args.salary_range,
        requirements=requirements,
    )


def _requirements_from_args(values: list[str], priority: str) -> list[dict[str, str]]:
    requirements: list[dict[str, str]] = []
    for value in values:
        identifier, separator, statement = value.partition("=")
        if not separator or not identifier or not statement:
            raise ValueError("requirements must use ID=TEXT")
        requirements.append({"id": identifier, "statement": statement, "priority": priority})
    return requirements


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
