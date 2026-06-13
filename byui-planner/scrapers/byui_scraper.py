import re
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from typing import Optional

BASE_URL = "https://student.byui.edu"
SEARCH_URL = f"{BASE_URL}/ICS/Class_Schedule/Public_Course_Search.jnz"
PARAMS = {"portlet": "Course_Schedules"}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


@dataclass
class Section:
    course_code: str = ""
    title: str = ""
    section_num: str = ""
    crn: str = ""
    professor: str = "TBA"
    days: list = field(default_factory=list)
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    credits: int = 0
    seats_available: int = 0
    delivery_method: str = ""
    rmp: Optional[dict] = None

    @property
    def has_friday(self) -> bool:
        return "F" in self.days

    @property
    def is_morning(self) -> bool:
        if not self.start_time:
            return False
        return _before_noon(self.start_time)

    @property
    def rmp_rating(self) -> float:
        if self.rmp and self.rmp.get("rating"):
            return float(self.rmp["rating"])
        return 0.0


def _before_noon(time_str: str) -> bool:
    time_str = time_str.strip().upper()
    if "PM" in time_str:
        hour = int(re.search(r"(\d+):", time_str).group(1))
        return hour == 12  # 12 PM is noon — treat as not morning
    if "AM" in time_str:
        return True
    return False


def _parse_days(day_str: str) -> list:
    if not day_str or day_str.strip() in ("-", "TBA", ""):
        return []
    days, i = [], 0
    s = day_str.strip()
    while i < len(s):
        if s[i:i+2] == "Th":
            days.append("Th")
            i += 2
        elif s[i] in "MTWFS":
            days.append(s[i])
            i += 1
        else:
            i += 1
    return days


def _get_form_data(session: requests.Session):
    resp = session.get(SEARCH_URL, params=PARAMS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    form_data = {}
    for tag in soup.find_all(["input", "select", "textarea"]):
        name = tag.get("name")
        if not name:
            continue
        if tag.name == "select":
            selected = tag.find("option", selected=True)
            first = tag.find("option")
            form_data[name] = (selected or first or {}).get("value", "")
        elif tag.name == "input" and tag.get("type", "").lower() not in ("submit", "button", "image", "reset"):
            form_data[name] = tag.get("value", "")

    return form_data, soup


def _set_term(form_data: dict, soup, term: str):
    for select in soup.find_all("select"):
        name = select.get("name", "")
        if any(kw in name.lower() for kw in ["semester", "term", "period", "session"]):
            for opt in select.find_all("option"):
                if term.lower() in opt.get_text(strip=True).lower():
                    form_data[name] = opt.get("value", "")
                    return


def _find_field(form_data: dict, *keywords) -> Optional[str]:
    for key in form_data:
        k = key.lower()
        if any(kw.lower() in k for kw in keywords):
            return key
    return None


def search_courses(course_code: str = "", term: str = "Fall Semester 2026") -> list[Section]:
    session = requests.Session()
    session.headers.update(HEADERS)

    form_data, soup = _get_form_data(session)
    _set_term(form_data, soup, term)

    code_field = _find_field(form_data, "coursecode", "course_code", "crse", "coursenbr")
    if code_field:
        # Strip space so "CS 246" -> course number only if needed
        parts = course_code.strip().split()
        form_data[code_field] = parts[-1] if len(parts) > 1 else course_code

    subj_field = _find_field(form_data, "subject", "subj", "dept", "department")
    if subj_field and " " in course_code.strip():
        form_data[subj_field] = course_code.strip().split()[0]

    # Trigger the search submit button
    for tag in soup.find_all("input", type="submit"):
        name = tag.get("name")
        if name and any(kw in name.lower() for kw in ["search", "find", "go"]):
            form_data[name] = tag.get("value", "Search")
            break

    resp = session.post(SEARCH_URL, params=PARAMS, data=form_data, timeout=20)
    resp.raise_for_status()

    return _parse_results(resp.text, course_code)


def _parse_results(html: str, course_code: str = "") -> list[Section]:
    soup = BeautifulSoup(html, "html.parser")
    sections = []

    for table in soup.find_all("table"):
        header_cells = table.find("tr")
        if not header_cells:
            continue
        headers = [c.get_text(strip=True).lower() for c in header_cells.find_all(["th", "td"])]
        joined = " ".join(headers)

        if not any(kw in joined for kw in ["course", "section", "instructor", "crn", "credit"]):
            continue

        for row in table.find_all("tr")[1:]:
            cells = row.find_all("td")
            if len(cells) < 3:
                continue
            section = _parse_row(cells, headers, course_code)
            if section:
                sections.append(section)

    return sections


def _parse_row(cells: list, headers: list, course_code: str) -> Optional[Section]:
    def get(*keywords):
        for kw in keywords:
            for i, h in enumerate(headers):
                if kw in h and i < len(cells):
                    val = cells[i].get_text(strip=True)
                    if val and val != "-":
                        return val
        return ""

    code = get("course code", "course", "code") or course_code
    title = get("title", "name", "description")
    section_num = get("section", "sec #", "sec")
    crn = get("crn", "reference")
    professor = get("instructor", "professor", "faculty", "teacher") or "TBA"
    days_str = get("days", "day", "meets")
    time_str = get("time", "times", "schedule")
    credits_str = get("credit", "credits", "hrs", "hours")
    seats_str = get("available", "open seats", "seats", "avail")
    method_str = get("delivery", "method", "format")

    if not code and not title:
        return None

    start_time = end_time = None
    if time_str:
        if "-" in time_str:
            parts = time_str.split("-", 1)
            start_time, end_time = parts[0].strip(), parts[1].strip()
        else:
            start_time = time_str.strip()

    def parse_int(s):
        m = re.search(r"\d+", s) if s else None
        return int(m.group()) if m else 0

    return Section(
        course_code=code.strip(),
        title=title.strip(),
        section_num=section_num.strip(),
        crn=crn.strip(),
        professor=professor.strip(),
        days=_parse_days(days_str),
        start_time=start_time,
        end_time=end_time,
        credits=parse_int(credits_str),
        seats_available=parse_int(seats_str),
        delivery_method=method_str.strip(),
    )
