import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
REQUIREMENTS_FILE = DATA_DIR / "degree_requirements.json"
COMPLETED_FILE = DATA_DIR / "completed_courses.json"


def _load_requirements() -> list[str]:
    if not REQUIREMENTS_FILE.exists():
        return []
    data = json.loads(REQUIREMENTS_FILE.read_text())
    return [c.upper().strip() for c in data.get("required_courses", [])]


def _load_completed() -> list[str]:
    if not COMPLETED_FILE.exists():
        return []
    data = json.loads(COMPLETED_FILE.read_text())
    return [c.upper().strip() for c in data.get("completed", [])]


def get_remaining_courses() -> list[str]:
    required = _load_requirements()
    completed = set(_load_completed())
    return [c for c in required if c not in completed]


def mark_completed(course_code: str):
    data = json.loads(COMPLETED_FILE.read_text()) if COMPLETED_FILE.exists() else {"completed": []}
    code = course_code.upper().strip()
    if code not in data["completed"]:
        data["completed"].append(code)
    COMPLETED_FILE.write_text(json.dumps(data, indent=2))
