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

    def get_modules(self, course_id: int) -> List[Dict]:
        return self._get_paginated(f'/courses/{course_id}/modules', {'per_page': 100})

    def get_module_items(self, course_id: int, module_id: int) -> List[Dict]:
        return self._get_paginated(f'/courses/{course_id}/modules/{module_id}/items', {'per_page': 100})

    def get_self_profile(self) -> Dict:
        resp = self.session.get(f'{self.base_url}/api/v1/users/self/profile')
        resp.raise_for_status()
        return resp.json()

    def get_assignments_with_overrides(self, course_id: int) -> List[Dict]:
        return self._get_paginated(f'/courses/{course_id}/assignments', [
            ('include[]', 'overrides'),
            ('order_by', 'due_at'),
            ('per_page', 100),
        ])

    def update_assignment(self, course_id: int, assignment_id: int, **fields) -> Dict:
        resp = self.session.put(
            f'{self.base_url}/api/v1/courses/{course_id}/assignments/{assignment_id}',
            data={f'assignment[{k}]': v for k, v in fields.items()},
        )
        resp.raise_for_status()
        return resp.json()

    def fetch_text(self, url: str, max_bytes: int = 300_000) -> Optional[str]:
        """Best-effort text download for a submission attachment (source code, .txt, .md).
        Returns None on any network error or if it can't be decoded as text.

        Submission attachment URLs are usually pre-authenticated via a `verifier`
        query param pointing at Canvas's file-storage host, which is often a
        different host than the API (e.g. an S3-backed domain). Sending our API
        Bearer token there can make that host reject the request outright, so we
        try a plain unauthenticated request first and only fall back to sending
        the token if that fails.
        """
        for use_auth in (False, True):
            try:
                headers = {'Authorization': self.session.headers['Authorization']} if use_auth else {}
                resp = requests.get(url, headers=headers, timeout=15)
                resp.raise_for_status()
            except requests.RequestException:
                continue
            try:
                return resp.content[:max_bytes].decode('utf-8')
            except UnicodeDecodeError:
                return resp.content[:max_bytes].decode('utf-8', errors='replace')
        return None
