import json
from pathlib import Path

from planner import course_filter


def test_get_remaining_courses_respects_completed():
    artifacts_dir = Path(__file__).parent / ".artifacts"
    artifacts_dir.mkdir(exist_ok=True)
    requirements_file = artifacts_dir / "degree_requirements_test.json"
    completed_file = artifacts_dir / "completed_courses_test.json"

    requirements_file.write_text(json.dumps({"required_courses": ["cs 101 ", " math 112"]}))
    completed_file.write_text(json.dumps({"completed": ["cs 101"]}))

    original_requirements = course_filter.REQUIREMENTS_FILE
    original_completed = course_filter.COMPLETED_FILE
    course_filter.REQUIREMENTS_FILE = requirements_file
    course_filter.COMPLETED_FILE = completed_file

    try:
        assert course_filter.get_remaining_courses() == ["MATH 112"]
    finally:
        course_filter.REQUIREMENTS_FILE = original_requirements
        course_filter.COMPLETED_FILE = original_completed


def test_mark_completed_normalizes_and_deduplicates():
    artifacts_dir = Path(__file__).parent / ".artifacts"
    artifacts_dir.mkdir(exist_ok=True)
    completed_file = artifacts_dir / "mark_completed_test.json"
    completed_file.write_text(json.dumps({"completed": ["CS 101"]}))

    original_completed = course_filter.COMPLETED_FILE
    course_filter.COMPLETED_FILE = completed_file

    try:
        course_filter.mark_completed(" cs 101 ")
        course_filter.mark_completed("math 112")

        data = json.loads(completed_file.read_text())
        assert data["completed"] == ["CS 101", "MATH 112"]
    finally:
        course_filter.COMPLETED_FILE = original_completed
