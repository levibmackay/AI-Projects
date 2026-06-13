from scrapers.byui_scraper import Section


def rank_sections(sections: list[Section]) -> list[Section]:
    """Sort sections by RMP rating descending, then by start time ascending."""
    return sorted(
        sections,
        key=lambda s: (-s.rmp_rating, _time_sort_key(s.start_time)),
    )


def _time_sort_key(time_str: str | None) -> int:
    """Convert time string to minutes since midnight for sorting."""
    if not time_str:
        return 9999
    import re
    m = re.search(r"(\d+):(\d+)\s*(AM|PM)?", time_str.upper())
    if not m:
        return 9999
    hour, minute = int(m.group(1)), int(m.group(2))
    period = m.group(3)
    if period == "PM" and hour != 12:
        hour += 12
    elif period == "AM" and hour == 12:
        hour = 0
    return hour * 60 + minute
