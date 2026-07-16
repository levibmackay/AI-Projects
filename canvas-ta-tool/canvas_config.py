from dataclasses import dataclass

from dotenv import load_dotenv
import os


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class CanvasConfig:
    base_url: str
    token: str


def load_canvas_config() -> CanvasConfig:
    load_dotenv()
    missing = [name for name in ("CANVAS_URL", "CANVAS_TOKEN") if not os.getenv(name)]
    if missing:
        missing_list = ", ".join(missing)
        raise ConfigError(f"Missing required environment variable(s): {missing_list}")

    return CanvasConfig(
        base_url=os.environ["CANVAS_URL"].rstrip("/"),
        token=os.environ["CANVAS_TOKEN"],
    )
