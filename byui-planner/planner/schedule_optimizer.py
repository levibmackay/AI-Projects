from scrapers.byui_scraper import Section


def filter_sections(
    sections: list[Section],
    morning_only: bool = True,
    no_friday: bool = True,
) -> list[Section]:
    results = []
    for s in sections:
        if morning_only and not s.is_morning:
            continue
        if no_friday and s.has_friday:
            continue
        results.append(s)
    return results


def best_section(sections: list[Section]) -> Section | None:
    if not sections:
        return None
    return sections[0]  # already sorted by professor_ranker before calling this
