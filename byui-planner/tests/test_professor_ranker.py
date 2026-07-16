from planner.professor_ranker import _time_sort_key, rank_sections
from scrapers.byui_scraper import Section


def test_time_sort_key_handles_ampm_and_invalid_inputs():
    assert _time_sort_key("9:30 AM") == 570
    assert _time_sort_key("1:15 PM") == 795
    assert _time_sort_key("12:00 AM") == 0
    assert _time_sort_key("no time") == 9999
    assert _time_sort_key(None) == 9999


def test_rank_sections_sorts_by_rating_then_earlier_time():
    low_rating = Section(start_time="8:00 AM", rmp={"rating": "3.1"})
    high_rating_late = Section(start_time="10:00 AM", rmp={"rating": "4.5"})
    high_rating_early = Section(start_time="9:00 AM", rmp={"rating": "4.5"})

    ranked = rank_sections([low_rating, high_rating_late, high_rating_early])

    assert ranked == [high_rating_early, high_rating_late, low_rating]
