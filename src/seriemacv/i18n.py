"""Small, explicit translation catalog for local resume projections."""

from __future__ import annotations

from typing import Literal

Locale = Literal["pt-BR", "en"]

_MESSAGES = {
    "pt-BR": {
        "summary": "Resumo",
        "experience": "Experiência profissional",
        "education": "Formação acadêmica",
        "skills": "Habilidades",
        "languages": "Idiomas",
        "highlight": "Destaque",
        "current": "Atual",
        "other": "Outras",
        "level.beginner": "Iniciante",
        "level.intermediate": "Intermediário",
        "level.advanced": "Avançado",
        "level.expert": "Especialista",
    },
    "en": {
        "summary": "Summary",
        "experience": "Professional Experience",
        "education": "Education",
        "skills": "Skills",
        "languages": "Languages",
        "highlight": "Highlight",
        "current": "Present",
        "other": "Other",
        "level.beginner": "Beginner",
        "level.intermediate": "Intermediate",
        "level.advanced": "Advanced",
        "level.expert": "Expert",
    },
}


def translate(locale: Locale, key: str) -> str:
    """Return a UI label; canonical YAML values never pass through unchanged."""
    return _MESSAGES[locale][key]
