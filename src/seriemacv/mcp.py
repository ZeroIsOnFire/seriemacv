"""Small dependency-free MCP stdio adapter for read and proposal use cases."""

from __future__ import annotations

import json
import sys
from io import StringIO
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from seriemacv.application_ai import create_ai_request, dump_ai
from seriemacv.applications import (
    dump_application,
    list_applications,
    load_application,
    pending_questions,
)
from seriemacv.evidence_search import search_verified_evidence
from seriemacv.jobs import dump_job, load_job, load_jobs
from seriemacv.matching import dump_match_report, match_job
from seriemacv.project import load_project_configuration
from seriemacv.proposals import create_proposal_request

TOOLS = [
    {"name": "search_career_evidence", "description": "Search verified canonical career evidence.", "inputSchema": {"type": "object", "required": ["project_path"], "properties": {"project_path": {"type": "string"}, "query": {"type": "string"}, "tags": {"type": "array", "items": {"type": "string"}}, "experience_id": {"type": "string"}}}},
    {"name": "list_jobs", "description": "List validated local job documents.", "inputSchema": {"type": "object", "required": ["project_path"], "properties": {"project_path": {"type": "string"}}}},
    {"name": "get_match_report", "description": "Generate a deterministic, evidence-backed match report.", "inputSchema": {"type": "object", "required": ["project_path", "job_id"], "properties": {"project_path": {"type": "string"}, "job_id": {"type": "string"}}}},
    {"name": "propose_resume_tailoring", "description": "Return a reviewable proposal request; never writes the project.", "inputSchema": {"type": "object", "required": ["project_path", "id", "variant_id", "language", "job_id"], "properties": {"project_path": {"type": "string"}, "id": {"type": "string"}, "variant_id": {"type": "string"}, "language": {"type": "string"}, "job_id": {"type": "string"}}}},
    {"name": "list_applications", "description": "List local application records without writing them.", "inputSchema": {"type": "object", "required": ["project_path"], "properties": {"project_path": {"type": "string"}}}},
    {"name": "get_application_questions", "description": "Read unresolved application questions without exposing form values.", "inputSchema": {"type": "object", "required": ["project_path", "application_id"], "properties": {"project_path": {"type": "string"}, "application_id": {"type": "string"}}}},
    {"name": "propose_application_answer", "description": "Return a reviewable answer-proposal envelope; it never writes career.yml or an application.", "inputSchema": {"type": "object", "required": ["project_path", "application_id", "question_id"], "properties": {"project_path": {"type": "string"}, "application_id": {"type": "string"}, "question_id": {"type": "string"}}}},
    {"name": "prepare_application_ai_assistance", "description": "Return minimal verified context and detected form questions for an external AI agent; never writes.", "inputSchema": {"type": "object", "required": ["project_path", "application_id", "request_id"], "properties": {"project_path": {"type": "string"}, "application_id": {"type": "string"}, "request_id": {"type": "string"}}}},
]


def main() -> int:
    for line in sys.stdin:
        try:
            request = json.loads(line)
            response = _handle(request)
        except (ValueError, OSError, KeyError) as error:
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32602, "message": str(error)}}
        print(json.dumps(response), flush=True)
    return 0


def _handle(request: dict[str, Any]) -> dict[str, Any]:
    method = request.get("method")
    request_id = request.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "seriemacv", "version": "0.1.0"}}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        arguments = request.get("params", {}).get("arguments", {})
        result = _call(request["params"]["name"], arguments)
        return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": result}]}}
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Unknown method: {method}"}}


def _call(name: str, arguments: dict[str, Any]) -> str:
    project_path = Path(arguments["project_path"])
    if name == "search_career_evidence":
        return _yaml([item.model_dump(mode="python") for item in search_verified_evidence(project_path, query=arguments.get("query"), tags=arguments.get("tags"), experience_id=arguments.get("experience_id"))])
    if name == "list_jobs":
        return dump_job(load_jobs(project_path))
    if name == "get_match_report":
        job = load_job(project_path / "jobs" / f"{arguments['job_id']}.yml")
        return dump_match_report(match_job(project_path, job, weights=load_project_configuration(project_path).match_weights))
    if name == "propose_resume_tailoring":
        return _yaml(create_proposal_request(project_path, arguments["id"], arguments["variant_id"], arguments["language"], job_id=arguments["job_id"]).model_dump(mode="json"))
    if name == "list_applications":
        return dump_application(list_applications(project_path))
    if name == "get_application_questions":
        return dump_application(pending_questions(project_path, arguments["application_id"]))
    if name == "propose_application_answer":
        application = load_application(project_path, arguments["application_id"])
        question = next((item for item in application.questions if item.id == arguments["question_id"]), None)
        if question is None:
            raise ValueError(f"unknown question: {arguments['question_id']}")
        return _yaml({"application_id": application.id, "question_id": question.id, "question": question.model_dump(mode="python"), "proposal": {"answer": None, "evidence_ids": []}, "persistence": "Use 'seriemacv applications apply-answer' only after explicit user confirmation."})
    if name == "prepare_application_ai_assistance":
        return dump_ai(create_ai_request(project_path, arguments["request_id"], arguments["application_id"]))
    raise ValueError(f"Unknown tool: {name}")


def _yaml(value: Any) -> str:
    stream = StringIO()
    YAML().dump(value, stream)
    return stream.getvalue()


if __name__ == "__main__":
    raise SystemExit(main())
