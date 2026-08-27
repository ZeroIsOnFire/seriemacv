from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pydantic import ValidationError
from ruamel.yaml.error import YAMLError

from seriemacv.application_ai import (
    apply_ai_response,
    create_ai_request,
    dump_ai,
    load_ai_request,
    load_ai_response,
    validate_ai_response,
    write_ai_request,
)
from seriemacv.applications import (
    ApplicationDocument,
    apply_answer,
    create_application,
    dump_application,
    list_applications,
    load_application,
    pending_questions,
    update_status,
    validate_applications,
)
from seriemacv.browser import clear_browser_profile, prepare_application
from seriemacv.career import (
    CAREER_FILE,
    add_record,
    dump_section,
    list_locales,
    list_section,
    load_localized_career,
    set_profile,
    validate_career,
    validate_locale,
)
from seriemacv.diagnostics import write_diagnostic_bundle
from seriemacv.evidence_search import search_verified_evidence
from seriemacv.jobs import (
    JOB_DIRECTORY,
    JobImportPayload,
    JobSource,
    create_job,
    dump_job,
    import_jobs,
    job_path,
    load_job,
    load_jobs,
    validate_job,
    validate_jobs,
)
from seriemacv.matching import dump_match_report, extract_requirements, match_job
from seriemacv.privacy import redact_sensitive_text
from seriemacv.project import (
    ProjectAlreadyExistsError,
    create_project,
    load_project_configuration,
    load_template,
    validate_project,
)
from seriemacv.proposals import (
    apply_proposal,
    create_proposal_request,
    diff_proposal,
    dump_proposal_diff,
    dump_proposal_request,
    load_proposal_request,
    load_proposal_response,
    validate_proposal,
    write_proposal_request,
)
from seriemacv.renderer import ResumeRenderError, write_resume
from seriemacv.studio import create_studio_server
from seriemacv.styles import STYLE_IDS, list_styles
from seriemacv.variants import (
    list_variant_locales,
    list_variants,
    load_variant_career,
    validate_variant,
    validate_variants,
)


def _print_error(value: object) -> None:
    print(redact_sensitive_text(value), file=sys.stderr)


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

    diagnostics_parser = subparsers.add_parser(
        "diagnostics", help="Create a minimal diagnostic bundle without career data"
    )
    diagnostics_subparsers = diagnostics_parser.add_subparsers(
        dest="diagnostics_command", required=True
    )
    diagnostics_bundle = diagnostics_subparsers.add_parser(
        "bundle", help="Write redacted project-structure diagnostics to a ZIP file"
    )
    diagnostics_bundle.add_argument("path", type=Path)
    diagnostics_bundle.add_argument("--output", type=Path, required=True)

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
    _add_answer_parser(career_subparsers)
    _add_story_parser(career_subparsers)

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
    render_parser.add_argument("--variant")
    resume_subparsers.add_parser(
        "styles", help="List built-in resume styles and their capabilities"
    )

    search_evidence_parser = career_subparsers.add_parser(
        "search-evidence", help="Search verified career evidence"
    )
    search_evidence_parser.add_argument("path", type=Path)
    search_evidence_parser.add_argument("query", nargs="?")
    search_evidence_parser.add_argument("--tag", action="append", default=[])
    search_evidence_parser.add_argument("--experience-id")

    applications_parser = subparsers.add_parser("applications", help="Manage local, reviewable job applications")
    applications_subparsers = applications_parser.add_subparsers(dest="applications_command", required=True)
    application_create = applications_subparsers.add_parser("create", help="Create a local application record")
    application_create.add_argument("path", type=Path)
    application_create.add_argument("--id", required=True)
    application_create.add_argument("--job-id", required=True)
    application_create.add_argument("--variant-id")
    application_create.add_argument("--url", default="")
    application_create.add_argument("--attachment", action="append", default=[])
    application_create.add_argument("--cover-letter-path")
    application_list = applications_subparsers.add_parser("list", help="List application records")
    application_list.add_argument("path", type=Path)
    application_validate = applications_subparsers.add_parser("validate", help="Validate application records")
    application_validate.add_argument("path", type=Path)
    application_show = applications_subparsers.add_parser("show", help="Print one application record")
    application_show.add_argument("path", type=Path)
    application_show.add_argument("id")
    application_status = applications_subparsers.add_parser("set-status", help="Transition an application status")
    application_status.add_argument("path", type=Path)
    application_status.add_argument("id")
    application_status.add_argument("status", choices=("saved", "preparing", "needs_user_input", "ready_for_review", "applied", "recruiter", "interview", "offer", "rejected", "withdrawn"))
    application_prepare = applications_subparsers.add_parser("prepare", help="Prepare a generic browser form without submitting it")
    application_prepare.add_argument("path", type=Path)
    application_prepare.add_argument("id")
    application_prepare.add_argument("--interactive", action="store_true")
    application_prepare.add_argument("--ai-assisted", action="store_true")
    application_questions = applications_subparsers.add_parser("questions", help="List unresolved application questions")
    application_questions.add_argument("path", type=Path)
    application_questions.add_argument("id")
    application_answer = applications_subparsers.add_parser("apply-answer", help="Explicitly apply a proposed or supplied answer")
    application_answer.add_argument("path", type=Path)
    application_answer.add_argument("id")
    application_answer.add_argument("question-id")
    application_answer.add_argument("--answer")
    application_answer.add_argument("--save-answer-id")
    application_answer.add_argument("--save-prompt")
    application_browser = applications_subparsers.add_parser("clear-browser-profile", help="Delete the isolated browser profile for this project")
    application_browser.add_argument("path", type=Path)
    application_ai_request = applications_subparsers.add_parser("ai-request", help="Write a minimal AI assistance request for detected form fields")
    application_ai_request.add_argument("path", type=Path)
    application_ai_request.add_argument("id")
    application_ai_request.add_argument("--request-id", required=True)
    application_ai_request.add_argument("--output", type=Path, required=True)
    application_ai_preview = applications_subparsers.add_parser(
        "ai-preview", help="Print the exact minimal AI assistance context without writing it"
    )
    application_ai_preview.add_argument("path", type=Path)
    application_ai_preview.add_argument("id")
    application_ai_preview.add_argument("--request-id", required=True)
    application_ai_review = applications_subparsers.add_parser("ai-review", help="Validate and show an AI application response")
    application_ai_review.add_argument("path", type=Path)
    application_ai_review.add_argument("request", type=Path)
    application_ai_review.add_argument("response", type=Path)
    application_ai_apply = applications_subparsers.add_parser("ai-apply", help="Persist explicitly accepted AI application proposals")
    application_ai_apply.add_argument("path", type=Path)
    application_ai_apply.add_argument("request", type=Path)
    application_ai_apply.add_argument("response", type=Path)
    application_ai_apply.add_argument("--accept", action="append", required=True)

    jobs_parser = subparsers.add_parser("jobs", help="Manage structured local job documents")
    jobs_subparsers = jobs_parser.add_subparsers(dest="jobs_command", required=True)
    _add_job_parser(jobs_subparsers)
    _add_job_import_parser(jobs_subparsers)
    _add_job_read_parsers(jobs_subparsers)
    job_extract = jobs_subparsers.add_parser(
        "extract-requirements", help="Print deterministic requirement candidates"
    )
    job_extract.add_argument("path", type=Path)
    job_extract.add_argument("id")

    match_parser = subparsers.add_parser(
        "match", help="Generate an evidence-backed deterministic job match report"
    )
    match_parser.add_argument("path", type=Path)
    match_parser.add_argument("job_id")

    studio_parser = subparsers.add_parser("studio", help="Start the local read-only Studio")
    studio_parser.add_argument("path", type=Path)
    studio_parser.add_argument("--port", type=int, default=8765)
    variants_parser = resume_subparsers.add_parser(
        "variants", help="List and validate structured resume variants"
    )
    variants_subparsers = variants_parser.add_subparsers(
        dest="variants_command", required=True
    )
    variants_list = variants_subparsers.add_parser("list", help="List resume variants")
    variants_list.add_argument("path", type=Path)
    variants_validate = variants_subparsers.add_parser(
        "validate", help="Validate one or every resume variant"
    )
    variants_validate.add_argument("path", type=Path)
    variants_validate.add_argument("--id")

    proposal_parser = subparsers.add_parser(
        "proposal", help="Exchange local, reviewable proposals with an AI agent"
    )
    proposal_subparsers = proposal_parser.add_subparsers(
        dest="proposal_command", required=True
    )
    proposal_request = proposal_subparsers.add_parser(
        "request", help="Write a minimal proposal request for an external agent"
    )
    proposal_request.add_argument("path", type=Path)
    proposal_request.add_argument("--id", required=True)
    proposal_request.add_argument("--variant-id", required=True)
    proposal_request.add_argument("--language", required=True)
    proposal_request.add_argument("--job-id")
    proposal_request.add_argument("--output", required=True, type=Path)
    proposal_preview = proposal_subparsers.add_parser(
        "preview", help="Print the exact proposal context without writing it"
    )
    proposal_preview.add_argument("path", type=Path)
    proposal_preview.add_argument("--id", required=True)
    proposal_preview.add_argument("--variant-id", required=True)
    proposal_preview.add_argument("--language", required=True)
    proposal_preview.add_argument("--job-id")
    proposal_review = proposal_subparsers.add_parser(
        "review", help="Validate a proposal response and print its granular diff"
    )
    proposal_review.add_argument("path", type=Path)
    proposal_review.add_argument("request", type=Path)
    proposal_review.add_argument("response", type=Path)
    proposal_apply = proposal_subparsers.add_parser(
        "apply", help="Persist explicitly accepted proposal items"
    )
    proposal_apply.add_argument("path", type=Path)
    proposal_apply.add_argument("request", type=Path)
    proposal_apply.add_argument("response", type=Path)
    proposal_apply.add_argument("--accept", action="append", required=True)

    template_parser = subparsers.add_parser(
        "template", help="Read built-in structured-data templates"
    )
    template_subparsers = template_parser.add_subparsers(
        dest="template_command", required=True
    )
    template_show = template_subparsers.add_parser(
        "show", help="Print a structured YAML template for an external tool"
    )
    template_show.add_argument("path", type=Path)
    template_show.add_argument("name", choices=("career", "job", "variant", "variant-locale"))
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


def _add_answer_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("add-answer", help="Add a reusable saved answer")
    parser.add_argument("path", type=Path)
    parser.add_argument("--id", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--answer", required=True)
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument("--evidence-id", action="append", default=[])


def _add_story_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("add-story", help="Add a reusable structured story")
    parser.add_argument("path", type=Path)
    parser.add_argument("--id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--situation", required=True)
    parser.add_argument("--action", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--evidence-id", action="append", default=[])


def _add_job_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("add", help="Add a job from explicit fields")
    parser.add_argument("path", type=Path)
    _add_job_fields(parser, required_identity=True)
    parser.add_argument("--description", required=True)


def _add_job_import_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("import", help="Import a structured local JSON or YAML job")
    parser.add_argument("path", type=Path)
    parser.add_argument("source", type=Path)


def _add_job_read_parsers(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    validate = subparsers.add_parser("validate", help="Validate one or all job documents")
    validate.add_argument("path", type=Path)
    validate.add_argument("--id")
    list_parser = subparsers.add_parser("list", help="Print validated job documents")
    list_parser.add_argument("path", type=Path)
    show = subparsers.add_parser("show", help="Print one validated job document")
    show.add_argument("path", type=Path)
    show.add_argument("id")


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
            parser.error(redact_sensitive_text(error))
        print(f"Created seriemaCV project at {project_path}")
        return 0

    if args.command == "career":
        return _run_career_command(args)

    if args.command == "resume":
        return _run_resume_command(args)

    if args.command == "proposal":
        return _run_proposal_command(args)

    if args.command == "jobs":
        return _run_jobs_command(args)

    if args.command == "applications":
        return _run_applications_command(args)

    if args.command == "match":
        return _run_match_command(args)

    if args.command == "studio":
        return _run_studio_command(args)

    if args.command == "diagnostics":
        try:
            output_path = write_diagnostic_bundle(args.path, args.output)
        except OSError as error:
            _print_error(f"{args.output}: {error}")
            return 1
        print(f"Wrote diagnostic bundle: {output_path}")
        return 0

    if args.command == "template":
        try:
            print(load_template(args.path, args.name), end="")
        except OSError as error:
            _print_error(f"{args.path}: {error}")
            return 1
        return 0

    errors = validate_project(args.path)
    if errors:
        for error in errors:
            _print_error(error)
        return 1
    print(f"Valid seriemaCV project: {args.path.expanduser().resolve()}")
    return 0


def _run_career_command(args: argparse.Namespace) -> int:
    if args.career_command == "locale":
        project_path = args.path.expanduser().resolve()
        if args.locale_command == "list":
            for locale in list_locales(project_path):
                print(locale)
            return 0
        diagnostics = validate_locale(project_path, args.language)
        if diagnostics:
            for diagnostic in diagnostics:
                _print_error(diagnostic.format(project_path / "career.locales" / f"{args.language}.yml"))
            return 1
        print(f"Valid locale document: {args.language}")
        return 0
    career_path = args.path.expanduser().resolve() / CAREER_FILE
    if args.career_command == "validate":
        diagnostics = validate_career(career_path)
        if diagnostics:
            for diagnostic in diagnostics:
                _print_error(diagnostic.format(career_path))
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
        elif args.career_command == "add-answer":
            add_record(career_path, "answers", {
                "id": args.id, "prompt": args.prompt, "answer": args.answer,
                "tags": args.tag, "evidence_ids": args.evidence_id,
            })
        elif args.career_command == "add-story":
            add_record(career_path, "stories", {
                "id": args.id, "title": args.title, "situation": args.situation,
                "action": args.action, "result": args.result,
                "evidence_ids": args.evidence_id,
            })
        elif args.career_command == "list":
            print(dump_section(list_section(career_path, args.section)), end="")
            return 0
        elif args.career_command == "search-evidence":
            results = search_verified_evidence(
                args.path,
                query=args.query,
                tags=args.tag,
                experience_id=args.experience_id,
            )
            print(dump_section(results), end="")
            return 0
        else:  # pragma: no cover - argparse guards this branch
            raise ValueError(f"Unknown career command: {args.career_command}")
    except (OSError, ValueError, ValidationError, YAMLError) as error:
        _print_error(f"{career_path}: {error}")
        return 1

    print(f"Updated career document: {career_path}")
    return 0


def _run_proposal_command(args: argparse.Namespace) -> int:
    project_path = args.path.expanduser().resolve()
    try:
        if args.proposal_command in {"request", "preview"}:
            request = create_proposal_request(
                project_path,
                args.id,
                args.variant_id,
                args.language,
                job_id=args.job_id,
            )
            if args.proposal_command == "preview":
                print(dump_proposal_request(request), end="")
                return 0
            write_proposal_request(args.output.expanduser().resolve(), request)
            print(f"Wrote proposal request: {args.output.expanduser().resolve()}")
            return 0
        request = load_proposal_request(args.request.expanduser().resolve())
        response = load_proposal_response(args.response.expanduser().resolve())
        diagnostics = validate_proposal(project_path, request, response)
        if diagnostics:
            for diagnostic in diagnostics:
                _print_error(f"{args.response}: {diagnostic.path}: {diagnostic.message}")
            return 1
        if args.proposal_command == "review":
            print(dump_proposal_diff(diff_proposal(response)), end="")
            return 0
        applied = apply_proposal(project_path, request, response, args.accept)
    except (OSError, ValueError, ValidationError, YAMLError) as error:
        _print_error(f"{project_path}: {error}")
        return 1
    paths = [path for path in (applied.variant_path, applied.cover_letter_path) if path]
    print(f"Applied proposal items: {', '.join(args.accept)}")
    for path in paths:
        print(path)
    return 0


def _run_resume_command(args: argparse.Namespace) -> int:
    if args.resume_command == "styles":
        for style in list_styles():
            ats = "ATS-safe" if style.ats_safe else "experimental, not ATS-safe"
            formats = ",".join(style.supported_formats)
            print(f"{style.id}\t{style.name}\t{style.layout}\t{ats}\t{formats}")
        return 0

    if args.resume_command == "variants":
        project_path = args.path.expanduser().resolve()
        try:
            if args.variants_command == "list":
                for variant in list_variants(project_path):
                    job_id = variant.job_id or "-"
                    locales = (
                        ",".join(list_variant_locales(project_path, variant.id)) or "-"
                    )
                    print(f"{variant.id}\t{job_id}\t{locales}")
                return 0
            diagnostics = (
                validate_variant(project_path, args.id)
                if args.id
                else validate_variants(project_path)
            )
        except (OSError, ValueError, ValidationError, YAMLError) as error:
            _print_error(f"{project_path}: {error}")
            return 1
        if diagnostics:
            for diagnostic in diagnostics:
                _print_error(diagnostic.format())
            return 1
        target = args.id or "all"
        print(f"Valid resume variant(s): {target}")
        return 0

    project_path = args.path.expanduser().resolve()
    career_path = project_path / CAREER_FILE
    configuration_path = project_path / "seriemacv.yml"
    diagnostics = validate_career(career_path)
    if diagnostics:
        for diagnostic in diagnostics:
            _print_error(diagnostic.format(career_path))
        return 1
    try:
        configuration = load_project_configuration(project_path)
    except (OSError, ValueError, ValidationError, YAMLError) as error:
        _print_error(f"{configuration_path}: {error}")
        return 1
    try:
        locale = args.language or configuration.resume_language
        variant = None
        if args.variant:
            variant, career = load_variant_career(project_path, args.variant, locale)
        else:
            career = load_localized_career(project_path, locale)
        style_id = (
            args.style
            or (variant.style if variant else None)
            or configuration.resume_style
        )
        output_paths = [
            write_resume(
                project_path,
                career,
                locale,
                output_format,
                style_id=style_id,
                resume_color=configuration.resume_color,
                variant_id=args.variant,
            )
            for output_format in args.format
        ]
    except (OSError, ResumeRenderError, ValueError, ValidationError, YAMLError) as error:
        _print_error(f"{career_path}: {error}")
        return 1
    print(f"Rendered {', '.join(item.upper() for item in args.format)} resume using {style_id}: {', '.join(str(path) for path in output_paths)}")
    return 0


def _run_applications_command(args: argparse.Namespace) -> int:
    project_path = args.path.expanduser().resolve()
    try:
        if args.applications_command == "create":
            saved = create_application(project_path, ApplicationDocument(
                id=args.id, job_id=args.job_id, variant_id=args.variant_id, url=args.url,
                attachments=args.attachment, cover_letter_path=args.cover_letter_path,
            ))
            print(f"Saved application document: {saved}")
            return 0
        if args.applications_command == "list":
            print(dump_application(list_applications(project_path)), end="")
            return 0
        if args.applications_command == "validate":
            diagnostics = validate_applications(project_path)
            if diagnostics:
                for path, message in diagnostics:
                    _print_error(f"{path}: {message}")
                return 1
            print(f"Valid application document(s): {project_path / 'applications'}")
            return 0
        if args.applications_command == "show":
            print(dump_application(load_application(project_path, args.id)), end="")
            return 0
        if args.applications_command == "set-status":
            print(dump_application(update_status(project_path, args.id, args.status)), end="")
            return 0
        if args.applications_command == "questions":
            print(dump_application(pending_questions(project_path, args.id)), end="")
            return 0
        if args.applications_command == "apply-answer":
            print(dump_application(apply_answer(
                project_path, args.id, args.question_id, args.answer,
                save_answer_id=args.save_answer_id, save_prompt=args.save_prompt,
            )), end="")
            return 0
        if args.applications_command == "prepare":
            print(dump_application(prepare_application(project_path, args.id, interactive=args.interactive, ai_assisted=args.ai_assisted)), end="")
            return 0
        if args.applications_command == "ai-request":
            request = create_ai_request(project_path, args.request_id, args.id)
            write_ai_request(args.output.expanduser().resolve(), request)
            print(f"Wrote application AI request: {args.output.expanduser().resolve()}")
            return 0
        if args.applications_command == "ai-preview":
            print(dump_ai(create_ai_request(project_path, args.request_id, args.id)), end="")
            return 0
        if args.applications_command == "ai-review":
            request = load_ai_request(args.request.expanduser().resolve())
            response = load_ai_response(args.response.expanduser().resolve())
            print(dump_ai([item.__dict__ for item in validate_ai_response(project_path, request, response)]), end="")
            return 0
        if args.applications_command == "ai-apply":
            request = load_ai_request(args.request.expanduser().resolve())
            response = load_ai_response(args.response.expanduser().resolve())
            print(dump_application(apply_ai_response(project_path, request, response, args.accept)), end="")
            return 0
        if args.applications_command == "clear-browser-profile":
            clear_browser_profile(project_path)
            print("Cleared isolated browser profile")
            return 0
        raise ValueError(f"Unknown applications command: {args.applications_command}")
    except (OSError, ValueError, ValidationError, YAMLError) as error:
        _print_error(f"{project_path / 'applications'}: {error}")
        return 1


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
                    _print_error(diagnostic.format(invalid_job_path))
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
                    _print_error(diagnostic.format(document_path))
                return 1
            print(dump_job(load_job(document_path)), end="")
            return 0

        if args.jobs_command == "extract-requirements":
            document_path = job_path(project_path, args.id)
            diagnostics = validate_job(document_path)
            if diagnostics:
                for diagnostic in diagnostics:
                    _print_error(diagnostic.format(document_path))
                return 1
            from io import StringIO

            from ruamel.yaml import YAML

            stream = StringIO()
            YAML().dump(
                [item.model_dump(mode="python") for item in extract_requirements(load_job(document_path))],
                stream,
            )
            print(stream.getvalue(), end="")
            return 0

        if args.jobs_command == "add":
            payload = _job_payload_from_args(args)
            source = JobSource(format="manual", content=args.description)
        elif args.jobs_command == "import":
            saved_job_paths = import_jobs(project_path, args.source)
            for saved_job_path in saved_job_paths:
                print(f"Saved job document: {saved_job_path}")
            return 0
        else:  # pragma: no cover - argparse guards this branch
            raise ValueError(f"Unknown jobs command: {args.jobs_command}")

        saved_job_path = create_job(project_path, payload, source)
    except (OSError, ValueError, ValidationError, YAMLError) as error:
        _print_error(f"{project_path / JOB_DIRECTORY}: {error}")
        return 1

    print(f"Saved job document: {saved_job_path}")
    return 0


def _run_match_command(args: argparse.Namespace) -> int:
    project_path = args.path.expanduser().resolve()
    document_path = job_path(project_path, args.job_id)
    try:
        diagnostics = validate_job(document_path)
        if diagnostics:
            for diagnostic in diagnostics:
                _print_error(diagnostic.format(document_path))
            return 1
        configuration = load_project_configuration(project_path)
        report = match_job(
            project_path,
            load_job(document_path),
            weights=configuration.match_weights,
        )
    except (OSError, ValueError, ValidationError, YAMLError) as error:
        _print_error(f"{project_path}: {error}")
        return 1
    print(dump_match_report(report), end="")
    return 0


def _run_studio_command(args: argparse.Namespace) -> int:
    try:
        server = create_studio_server(args.path, port=args.port)
    except OSError as error:
        _print_error(f"{args.path}: {error}")
        return 1
    print(f"seriemaCV Studio: http://127.0.0.1:{server.server_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
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
