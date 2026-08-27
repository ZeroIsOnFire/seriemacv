"""Small dependency-free MCP stdio adapter for read and proposal use cases."""

from __future__ import annotations

import json
import sys
from io import StringIO
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

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
    raise ValueError(f"Unknown tool: {name}")


def _yaml(value: Any) -> str:
    stream = StringIO()
    YAML().dump(value, stream)
    return stream.getvalue()


if __name__ == "__main__":
    raise SystemExit(main())
