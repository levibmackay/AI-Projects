import re
from pathlib import Path

EXTENSION_MAP = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".jsx": "javascript", ".tsx": "typescript", ".java": "java",
    ".c": "c", ".cpp": "cpp", ".h": "c", ".hpp": "cpp",
    ".cs": "csharp", ".go": "go", ".rs": "rust", ".rb": "ruby",
    ".php": "php", ".swift": "swift", ".kt": "kotlin",
    ".sh": "bash", ".bash": "bash", ".zsh": "bash",
    ".sql": "sql", ".html": "html", ".css": "css",
    ".json": "json", ".yaml": "yaml", ".yml": "yaml",
    ".md": "markdown", ".r": "r", ".dart": "dart",
    ".lua": "lua", ".scala": "scala", ".ex": "elixir",
}

SHEBANG_MAP = {
    "python": "python", "node": "javascript", "ruby": "ruby",
    "perl": "perl", "bash": "bash", "sh": "bash",
}

KEYWORD_PATTERNS = {
    # Python patterns weighted 2x because embedded SQL in Python strings is common
    "python": [
        r"\bdef \w+\(", r"\bdef \w+\(", r"\bimport \w+", r"\bimport \w+",
        r"\bclass \w+:", r"print\(", r"if __name__", r"\bself\b", r"\.py\b",
    ],
    "javascript": [r"\bconst \w+", r"\blet \w+", r"=>\s*{", r"console\.log", r"require\("],
    "typescript": [r":\s*(string|number|boolean|any)\b", r"interface \w+", r"<[A-Z]\w+>"],
    "java": [r"public\s+(static\s+)?void\s+main", r"System\.out\.print", r"import java\."],
    "go": [r"\bfunc \w+\(", r"\bpackage \w+", r":=", r"fmt\.Print"],
    "rust": [r"\bfn \w+\(", r"\blet mut\b", r"println!", r"use std::"],
    "cpp": [r"#include\s*<", r"std::", r"cout\s*<<", r"::\w+"],
    "sql": [r"^\s*SELECT\b", r"^\s*FROM\b", r"^\s*WHERE\b", r"^\s*INSERT INTO\b", r"^\s*CREATE TABLE\b"],
    "bash": [r"#!/bin/(ba)?sh", r"\$\{?\w+\}?", r"\[\[", r"echo "],
    "html": [r"<html", r"<div", r"<!DOCTYPE"],
    "css": [r"[.#]\w+\s*\{", r":\s*\w+;", r"@media"],
}


def detect(code: str, filepath: str = None) -> str:
    if filepath:
        ext = Path(filepath).suffix.lower()
        if ext in EXTENSION_MAP:
            return EXTENSION_MAP[ext]

    lines = code.strip().splitlines()
    if lines and lines[0].startswith("#!"):
        for key, lang in SHEBANG_MAP.items():
            if key in lines[0]:
                return lang

    scores = {}
    for lang, patterns in KEYWORD_PATTERNS.items():
        score = sum(1 for p in patterns if re.search(p, code, re.MULTILINE | re.IGNORECASE))
        if score:
            scores[lang] = score

    if scores:
        return max(scores, key=scores.get)

    return "unknown"
