from planner.schedule_optimizer import best_section, filter_sections
from scrapers.byui_scraper import Section


def test_filter_sections_applies_morning_and_friday_rules():
    sections = [
        Section(course_code="CS 101", start_time="8:00 AM", days=["M", "W"]),
        Section(course_code="CS 101", start_time="1:00 PM", days=["T", "Th"]),
        Section(course_code="CS 101", start_time="9:00 AM", days=["M", "F"]),
    ]

    filtered = filter_sections(sections, morning_only=True, no_friday=True)

    assert len(filtered) == 1
    assert filtered[0].start_time == "8:00 AM"


def test_best_section_returns_first_or_none():
    section = Section(course_code="MATH 112", start_time="7:45 AM")

    assert best_section([section]) is section
    assert best_section([]) is None
