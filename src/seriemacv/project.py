from __future__ import annotations

import os
import sqlite3
import tempfile
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

CONFIG_FILE = "seriemacv.yml"
PROJECT_DIRECTORIES = (
    "resume",
    "resume/variants",
    "jobs",
    "jobs/sources",
    "applications",
    "knowledge",
    "styles",
    "exports",
    ".seriemacv/cache",
    ".seriemacv/browser",
    ".seriemacv/index",
)
PROJECT_ARTIFACTS = {
    "profile.yml": (
        "# Reusable, deterministic application data\n"
        "schema_version: 1\n"
        'name: ""\n'
        'location: ""\n'
        'email: ""\n'
    ),
    "resume/master.md": (
        "---\n"
        'name: ""\n'
        'title: ""\n'
        'location: ""\n'
        "---\n\n"
        "# Your Name\n\n"
        "## Experience\n\n"
        "## Skills\n"
    ),
    "knowledge/achievements.yml": "[]\n",
    "knowledge/skills.yml": "[]\n",
    "knowledge/answers.md": "# Application answers\n",
    "knowledge/stories.md": "# Interview stories\n",
}
DATABASE_RELATIVE_PATH = Path(".seriemacv/index/seriemacv.db")

class ProjectAlreadyExistsError(FileExistsError):
    """Raised when creating a project would overwrite its configuration."""


class InvalidProjectError(ValueError):
    """Raised when a directory does not satisfy the seriemaCV project contract."""


@dataclass(frozen=True)
class CareerProject:
    """Validated local project and its private SQLite index."""

    path: Path
    name: str
    database_path: Path
    database_schema_version: int


class ProjectConfiguration(BaseModel):
    """Strict, versioned configuration owned by a career project."""

    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal[1]
    project_name: str = Field(min_length=1, max_length=120)

    @field_validator("project_name")
    @classmethod
    def project_name_cannot_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


def create_project(path: Path, *, project_name: str) -> Path:
    """Create a new portable seriemaCV project without overwriting one."""
    project_path = path.expanduser().resolve()
    ProjectConfiguration(schema_version=1, project_name=project_name)

    if (project_path / CONFIG_FILE).exists():
        raise ProjectAlreadyExistsError(
            f"A seriemaCV project already exists at {project_path}"
        )

    project_path.mkdir(parents=True, exist_ok=True)
    for relative_directory in PROJECT_DIRECTORIES:
        (project_path / relative_directory).mkdir(parents=True, exist_ok=True)
    for relative_path, content in PROJECT_ARTIFACTS.items():
        _atomic_write(project_path / relative_path, content)

    config = (
        "# seriemaCV project configuration\n"
        "schema_version: 1\n"
        f"project_name: {_yaml_string(project_name)}\n"
    )
    _atomic_write(project_path / CONFIG_FILE, config)
    _initialize_database(project_path / DATABASE_RELATIVE_PATH)
    return project_path


def open_project(path: Path) -> CareerProject:
    """Open a validated project and return its local infrastructure paths."""
    project_path = path.expanduser().resolve()
    errors = validate_project(project_path)
    if errors:
        raise InvalidProjectError("; ".join(errors))

    configuration = _read_project_configuration(project_path / CONFIG_FILE)
    database_path = project_path / DATABASE_RELATIVE_PATH
    return CareerProject(
        path=project_path,
        name=configuration.project_name,
        database_path=database_path,
        database_schema_version=_database_schema_version(database_path),
    )


def validate_project(path: Path) -> list[str]:
    """Return validation errors for a project; an empty list means valid."""
    project_path = path.expanduser().resolve()
    errors: list[str] = []
    config_path = project_path / CONFIG_FILE

    if not config_path.is_file():
        errors.append(f"Required file is missing: {CONFIG_FILE}")
    else:
        errors.extend(_validate_config(config_path))

    for relative_directory in PROJECT_DIRECTORIES:
        if not (project_path / relative_directory).is_dir():
            errors.append(f"Required directory is missing: {relative_directory}")
    for relative_path in PROJECT_ARTIFACTS:
        if not (project_path / relative_path).is_file():
            errors.append(f"Required file is missing: {relative_path}")

    database_path = project_path / DATABASE_RELATIVE_PATH
    if not database_path.is_file():
        errors.append(f"Required file is missing: {DATABASE_RELATIVE_PATH.as_posix()}")
    elif not _is_valid_database(database_path):
        errors.append("Invalid local SQLite index")

    return errors


def _validate_config(config_path: Path) -> list[str]:
    try:
        _read_project_configuration(config_path)
    except (OSError, ValueError, YAMLError, ValidationError) as error:
        return [f"Invalid {CONFIG_FILE}: {error}"]
    return []


def _read_project_configuration(config_path: Path) -> ProjectConfiguration:
    document = YAML(typ="rt").load(config_path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"{CONFIG_FILE} must contain a mapping")
    return ProjectConfiguration.model_validate(document)


def _yaml_string(value: str) -> str:
    """Return a safe double-quoted YAML scalar for generated configuration."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _atomic_write(path: Path, content: str) -> None:
    file_descriptor, temporary_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        text=True,
    )
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="\n") as file:
            file.write(content)
        os.replace(temporary_path, path)
    except BaseException:
        Path(temporary_path).unlink(missing_ok=True)
        raise


def _initialize_database(database_path: Path) -> None:
    with closing(sqlite3.connect(database_path)) as connection:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS project_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO schema_migrations (version) VALUES (1)"
            )


def _database_schema_version(database_path: Path) -> int:
    with closing(
        sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)
    ) as connection:
        row = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
    return int(row[0] or 0)


def _is_valid_database(database_path: Path) -> bool:
    try:
        return _database_schema_version(database_path) >= 1
    except sqlite3.Error:
        return False
