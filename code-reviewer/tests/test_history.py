import json
from pathlib import Path

from utils import history


def test_save_and_retrieve_history_entries():
    artifacts_dir = Path(__file__).parent / ".artifacts" / "history"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    index_file = artifacts_dir / "index.json"

    original_history_dir = history.HISTORY_DIR
    original_index_file = history.INDEX_FILE
    history.HISTORY_DIR = artifacts_dir
    history.INDEX_FILE = index_file

    try:
        saved_path = history.save(
            code="print('hello')",
            language="python",
            mode="quick",
            agent_name="TestAgent",
            review="Looks good.",
        )

        assert Path(saved_path).exists()

        history_items = history.get_history(limit=1)
        assert len(history_items) == 1
        assert history_items[0]["language"] == "python"

        review_id = history_items[0]["id"]
        loaded_review = history.get_review(review_id)
        assert loaded_review is not None
        assert "Looks good." in loaded_review

        index_data = json.loads(index_file.read_text())
        assert index_data[0]["agent"] == "TestAgent"
    finally:
        history.HISTORY_DIR = original_history_dir
        history.INDEX_FILE = original_index_file
