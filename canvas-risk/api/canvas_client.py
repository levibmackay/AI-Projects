import requests
from config.settings import settings

class CanvasClient:
    def __init__(self):
        self.base_url = settings.CANVAS_BASE_URL.rstrip('/')
        self.course_id = settings.CANVAS_COURSE_ID
        self.headers = settings.headers

    def _get_paginated(self, endpoint, params=None):
        if params is None:
            params = {}
        params['per_page'] = 100
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        results = []
        
        while url:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            results.extend(response.json())
            
            # Canvas uses the 'Link' header for pagination
            if 'next' in response.links:
                url = response.links['next']['url']
                params = None # Parameters are already in the 'next' URL
            else:
                url = None
                
        return results

    def get_course(self):
        return requests.get(f"{self.base_url}/courses/{self.course_id}", headers=self.headers).json()

    def get_assignment_groups(self):
        return self._get_paginated(f"courses/{self.course_id}/assignment_groups")

    def get_students(self):
        return self._get_paginated(f"courses/{self.course_id}/users", params={"enrollment_type[]": "student", "include[]": ["enrollments"]})

    def get_assignments(self):
        return self._get_paginated(f"courses/{self.course_id}/assignments")

    def get_submissions(self, assignment_id):
        return self._get_paginated(f"courses/{self.course_id}/assignments/{assignment_id}/submissions")

    def get_all_submissions(self):
        return self._get_paginated(f"courses/{self.course_id}/students/submissions", params={"student_ids[]": "all", "include[]": ["assignment"]})

    def send_message(self, user_ids, body, subject=None):
        """Send a Canvas conversation message to one or more users."""
        if isinstance(user_ids, int):
            user_ids = [user_ids]
        
        endpoint = f"{self.base_url}/conversations"
        data = {
            "recipients[]": user_ids,
            "body": body,
            "force_new": True
        }
        if subject:
            data["subject"] = subject
            
        response = requests.post(endpoint, headers=self.headers, data=data)
        response.raise_for_status()
        return response.json()
