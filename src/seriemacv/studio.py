"""Initial local, read-only Studio web interface."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from seriemacv.jobs import load_job, load_jobs
from seriemacv.matching import match_job
from seriemacv.project import load_project_configuration


def create_studio_server(
    project_path: Path, host: str = "127.0.0.1", port: int = 0
) -> ThreadingHTTPServer:
    """Create a loopback-only-by-default server without mutating the project."""
    resolved_path = project_path.expanduser().resolve()

    class StudioHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            try:
                if path == "/":
                    self._html(_PAGE)
                elif path == "/api/jobs":
                    self._json([
                        {"id": job.id, "title": job.title, "company": job.company}
                        for job in load_jobs(resolved_path)
                    ])
                elif path.startswith("/api/match/"):
                    job_id = unquote(path.removeprefix("/api/match/"))
                    job = load_job(resolved_path / "jobs" / f"{job_id}.yml")
                    report = match_job(
                        resolved_path,
                        job,
                        weights=load_project_configuration(resolved_path).match_weights,
                    )
                    self._json(report.model_dump(mode="json"))
                else:
                    self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            except (OSError, ValueError) as error:
                self._json({"error": str(error)}, status=HTTPStatus.BAD_REQUEST)

        def _html(self, content: str) -> None:
            encoded = content.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def _json(self, value: object, status: HTTPStatus = HTTPStatus.OK) -> None:
            encoded = json.dumps(value).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, format: str, *args: object) -> None:
            return

    return ThreadingHTTPServer((host, port), StudioHandler)


_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>seriemaCV Studio</title>
<style>body{font:16px system-ui;margin:2rem;max-width:55rem}button{margin:.25rem}pre{white-space:pre-wrap;background:#f3f4f2;padding:1rem}</style>
</head><body><h1>seriemaCV Studio</h1><p>Local, read-only job workspace.</p><div id="jobs">Loading jobs…</div><pre id="report" hidden></pre>
<script>
const output=document.querySelector('#report');
fetch('/api/jobs').then(r=>r.json()).then(jobs=>{const box=document.querySelector('#jobs');box.textContent='';if(!jobs.length){box.textContent='No jobs imported.'}for(const job of jobs){const b=document.createElement('button');b.textContent=job.title;b.onclick=()=>fetch('/api/match/'+encodeURIComponent(job.id)).then(r=>r.json()).then(report=>{output.hidden=false;output.textContent=JSON.stringify(report,null,2)});box.append(b)}}).catch(error=>document.querySelector('#jobs').textContent=error.message);
</script></body></html>"""
