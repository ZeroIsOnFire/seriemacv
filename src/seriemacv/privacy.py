"""Privacy guards for technical output that may be captured outside a project."""

from __future__ import annotations

import re

REDACTED = "<redacted>"
TELEMETRY_ENABLED = False

_EMAIL = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
_PHONE = re.compile(
    r"(?<!\w)(?:\+?\d{1,3}[ .-])?(?:\(?\d{2,3}\)?[ .-])?\d{3,5}[ .-]\d{4}(?!\w)"
)
_BEARER = re.compile(r"(?i)\bbearer\s+[A-Z0-9._~+/=-]+")
_AUTHORIZATION = re.compile(
    r"(?i)(\bauthorization\s*:\s*)(?:bearer\s+[^\s,;]+|[^\s,;]+)"
)
_SENSITIVE_VALUE = re.compile(
    r"(?ix)(\b(?:api[_ -]?key|access[_ -]?token|token|secret|password|passwd|cookie|"
    r"credential(?:s)?|email|e-mail|phone|telephone|salary|compensation|pay|legal|"
    r"work[_ -]?authorization|visa|demographic|gender|race|ethnicity|disability|"
    r"veteran|self[_ -]?ident(?:ification)?)\b\s*(?:=|:)\s*)"
    r"(?:\"[^\"]*\"|'[^']*'|[^\s,;]+)"
)


def redact_sensitive_text(value: object) -> str:
    """Mask secrets and personal values in errors without removing their field names."""
    text = str(value)
    text = _BEARER.sub("Bearer " + REDACTED, text)
    text = _AUTHORIZATION.sub(r"\1" + REDACTED, text)
    text = _EMAIL.sub(REDACTED, text)
    text = _PHONE.sub(REDACTED, text)
    return _SENSITIVE_VALUE.sub(r"\1" + REDACTED, text)
