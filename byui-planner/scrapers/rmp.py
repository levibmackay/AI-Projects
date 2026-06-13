import json
import ratemyprofessor
from pathlib import Path

CACHE_FILE = Path(__file__).parent.parent / "data" / "rmp_cache.json"
SCHOOL_NAME = "Brigham Young University-Idaho"

_school = None


def _get_school():
    global _school
    if _school is None:
        _school = ratemyprofessor.get_school_by_name(SCHOOL_NAME)
    return _school


def _load_cache() -> dict:
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text())
    return {}


def _save_cache(cache: dict):
    CACHE_FILE.write_text(json.dumps(cache, indent=2))


def get_professor_rating(name: str) -> dict | None:
    cache = _load_cache()
    if name in cache:
        return cache[name]

    school = _get_school()
    if not school:
        return None

    professor = ratemyprofessor.get_professor_by_school_and_name(school, name)
    if not professor:
        cache[name] = None
        _save_cache(cache)
        return None

    result = {
        "name": professor.name,
        "rating": professor.rating,
        "difficulty": professor.difficulty,
        "num_ratings": professor.num_ratings,
        "would_take_again": professor.would_take_again,
    }
    cache[name] = result
    _save_cache(cache)
    return result
