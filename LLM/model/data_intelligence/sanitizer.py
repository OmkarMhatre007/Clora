"""
Security, Sanitization & Path Traversal Guards for CLORA Deliverables.
Defends against:
1. Formula Injection in spreadsheets (=, +, -, @, control characters)
2. XML Entity Injection / unescaped characters in Office Open XML
3. Path traversal attacks (../, absolute paths) in ZIP packaging
"""
from __future__ import annotations

import re
import html
from typing import Any


DANGEROUS_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r", "\n")


def sanitize_spreadsheet_text(val: Any) -> Any:
    """
    Sanitize text before writing into Excel cells.
    If string starts with dangerous formula triggers (=, +, -, @, tab, newline),
    prefixes with a single quote to force Excel to treat it as plain text.
    """
    if not isinstance(val, str):
        return val

    # Strip leading whitespace for check, but preserve original text
    stripped = val.lstrip()
    if any(stripped.startswith(prefix) for prefix in DANGEROUS_FORMULA_PREFIXES):
        # Prefix with single quote to force text interpretation
        return "'" + val
    return val


def sanitize_xml_text(val: Any) -> str:
    """Escape XML reserved characters (&, <, >, ", ') for safe insertion into docx/pptx."""
    if val is None:
        return ""
    text = str(val)
    return html.escape(text)


def validate_zip_entry_path(arcname: str) -> None:
    r"""
    Validate that a file path inside a ZIP archive is safe:
    - No path traversal (../)
    - No absolute paths (/, C:\)
    - No executable extensions (.exe, .bat, .cmd, .sh)
    """
    if not arcname:
        raise ValueError("ZIP entry arcname cannot be empty.")

    normalized = arcname.replace("\\", "/")
    if normalized.startswith("/") or re.match(r"^[a-zA-Z]:", normalized):
        raise ValueError(f"Absolute paths prohibited in ZIP package: {arcname}")

    parts = normalized.split("/")
    if ".." in parts or "." in parts:
        raise ValueError(f"Path traversal detected in ZIP entry: {arcname}")

    dangerous_exts = (".exe", ".bat", ".cmd", ".sh", ".ps1", ".vbs")
    if normalized.lower().endswith(dangerous_exts):
        raise ValueError(f"Executable file types prohibited in evidence package: {arcname}")
