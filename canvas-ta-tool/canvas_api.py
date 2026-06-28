import requests
from typing import Any, Dict, List, Optional


class CanvasAPI:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers['Authorization'] = f'Bearer {token}'

    def _get_paginated(self, path: str, params: Any = None) -> List[Dict]:
        url = f'{self.base_url}/api/v1{path}'
        results = []
        while url:
            resp = self.session.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                results.extend(data)
            url = None
            for part in resp.headers.get('Link', '').split(','):
                if 'rel="next"' in part:
                    url = part.split(';')[0].strip().strip('<>')
                    params = None
                    break
        return results

    def get_ta_courses(self) -> List[Dict]:
        courses: Dict[int, Dict] = {}
        for role in ('ta', 'teacher'):
            try:
                for c in self._get_paginated('/courses', {
                    'enrollment_type': role,
                    'enrollment_state': 'active',
                    'per_page': 100,
                }):
                    courses[c['id']] = c
            except requests.HTTPError:
                pass
        return list(courses.values())

    def get_students(self, course_id: int) -> List[Dict]:
        return self._get_paginated(f'/courses/{course_id}/users', [
            ('enrollment_type[]', 'student'),
            ('include[]', 'email'),
            ('per_page', 100),
        ])

    def get_assignments(self, course_id: int) -> List[Dict]:
        return self._get_paginated(f'/courses/{course_id}/assignments', {
            'order_by': 'due_at',
            'per_page': 100,
        })

    def get_enrollments(self, course_id: int) -> List[Dict]:
        return self._get_paginated(f'/courses/{course_id}/enrollments', [
            ('type[]', 'StudentEnrollment'),
            ('per_page', 100),
        ])

    def get_submissions(self, course_id: int) -> List[Dict]:
        return self._get_paginated(f'/courses/{course_id}/students/submissions', [
            ('student_ids[]', 'all'),
            ('include[]', 'assignment'),
            ('per_page', 100),
        ])
