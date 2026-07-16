import requests
from typing import Any, Dict, List, Optional


class CanvasAPIError(RuntimeError):
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class CanvasAPI:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers['Authorization'] = f'Bearer {token}'

    @staticmethod
    def _extract_error_detail(resp: requests.Response) -> str:
        try:
            payload = resp.json()
        except ValueError:
            return resp.text.strip() or 'No response details provided.'

        if isinstance(payload, dict):
            if isinstance(payload.get('errors'), list) and payload['errors']:
                return '; '.join(str(e.get('message', e)) for e in payload['errors'])
            if payload.get('message'):
                return str(payload['message'])
        return str(payload)

    def _raise_api_error(self, action: str, resp: requests.Response) -> None:
        status = resp.status_code
        detail = self._extract_error_detail(resp)
        if status in (401, 403):
            msg = f'Canvas authentication failed while {action}. Verify CANVAS_TOKEN and permissions.'
        elif status >= 500:
            msg = f'Canvas API is unavailable while {action} (HTTP {status}). Please try again shortly.'
        else:
            msg = f'Canvas API request failed while {action} (HTTP {status}): {detail}'
        raise CanvasAPIError(msg, status_code=status)

    def _get_paginated(self, path: str, params: Any = None) -> List[Dict]:
        url = f'{self.base_url}/api/v1{path}'
        results = []
        while url:
            try:
                resp = self.session.get(url, params=params, timeout=20)
            except requests.RequestException as exc:
                raise CanvasAPIError(f'Network error while fetching {path}: {exc}') from exc
            if not resp.ok:
                self._raise_api_error(f'fetching {path}', resp)
            try:
                data = resp.json()
            except ValueError as exc:
                raise CanvasAPIError(f'Canvas returned invalid JSON while fetching {path}.') from exc
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
            except CanvasAPIError as exc:
                if exc.status_code in (401, 403):
                    raise
                continue
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
        url = f'{self.base_url}/api/v1/users/self/profile'
        try:
            resp = self.session.get(url, timeout=20)
        except requests.RequestException as exc:
            raise CanvasAPIError(f'Network error while fetching your Canvas profile: {exc}') from exc
        if not resp.ok:
            self._raise_api_error('fetching your Canvas profile', resp)
        try:
            return resp.json()
        except ValueError as exc:
            raise CanvasAPIError('Canvas returned invalid JSON for your profile.') from exc

    def get_assignments_with_overrides(self, course_id: int) -> List[Dict]:
        return self._get_paginated(f'/courses/{course_id}/assignments', [
            ('include[]', 'overrides'),
            ('order_by', 'due_at'),
            ('per_page', 100),
        ])

    def update_assignment(self, course_id: int, assignment_id: int, **fields) -> Dict:
        try:
            resp = self.session.put(
                f'{self.base_url}/api/v1/courses/{course_id}/assignments/{assignment_id}',
                data={f'assignment[{k}]': v for k, v in fields.items()},
                timeout=20,
            )
        except requests.RequestException as exc:
            raise CanvasAPIError(
                f'Network error while updating assignment {assignment_id} in course {course_id}: {exc}'
            ) from exc
        if not resp.ok:
            self._raise_api_error(f'updating assignment {assignment_id}', resp)
        try:
            return resp.json()
        except ValueError as exc:
            raise CanvasAPIError(
                f'Canvas returned invalid JSON after updating assignment {assignment_id}.'
            ) from exc

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
