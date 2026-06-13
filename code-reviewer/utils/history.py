import json
import hashlib
from datetime import datetime
from pathlib import Path

HISTORY_DIR = Path(__file__).parent.parent / "history"
HISTORY_DIR.mkdir(exist_ok=True)
INDEX_FILE = HISTORY_DIR / "index.json"


def _load_index() -> list:
    if INDEX_FILE.exists():
        return json.loads(INDEX_FILE.read_text())
    return []


def _save_index(index: list):
    INDEX_FILE.write_text(json.dumps(index, indent=2))


def save(code: str, language: str, mode: str, agent_name: str, review: str) -> str:
    ts = datetime.now()
    code_hash = hashlib.md5(code.encode()).hexdigest()[:8]
    slug = f"{ts.strftime('%Y%m%d_%H%M%S')}_{language}_{code_hash}"

    review_file = HISTORY_DIR / f"{slug}.md"
    review_file.write_text(
        f"# Code Review\n\n"
        f"**Date:** {ts.strftime('%Y-%m-%d %H:%M:%S')}  \n"
        f"**Language:** {language}  \n"
        f"**Mode:** {mode}  \n"
        f"**Model:** {agent_name}  \n\n"
        f"## Code\n\n```{language}\n{code}\n```\n\n"
        f"## Review\n\n{review}\n"
    )

    index = _load_index()
    index.insert(0, {
        "id": slug,
        "date": ts.isoformat(),
        "language": language,
        "mode": mode,
        "agent": agent_name,
        "file": str(review_file),
        "preview": review[:120].replace("\n", " "),
    })
    _save_index(index[:50])  # keep last 50

    return str(review_file)


def get_history(limit: int = 10) -> list:
    return _load_index()[:limit]


def get_review(review_id: str) -> str | None:
    index = _load_index()
    for entry in index:
        if entry["id"] == review_id or review_id in entry["id"]:
            path = Path(entry["file"])
            if path.exists():
                return path.read_text()
    return None
