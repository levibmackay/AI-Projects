import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    CANVAS_API_TOKEN = os.getenv("CANVAS_API_TOKEN")
    CANVAS_BASE_URL = os.getenv("CANVAS_BASE_URL", "https://canvas.instructure.com/api/v1")
    CANVAS_COURSE_ID = os.getenv("CANVAS_COURSE_ID")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./canvas_risk.db")

    @property
    def headers(self):
        return {
            "Authorization": f"Bearer {self.CANVAS_API_TOKEN}",
            "Accept": "application/json"
        }

settings = Settings()
