from utils.language_detector import detect


def test_detect_prefers_filepath_extension():
    code = "console.log('hello')"
    assert detect(code, filepath="script.py") == "python"


def test_detect_uses_shebang_when_no_filepath():
    code = "#!/usr/bin/env node\nconsole.log('hello')"
    assert detect(code) == "javascript"


def test_detect_weights_python_patterns_over_embedded_sql():
    code = """
def get_users():
    query = \"SELECT * FROM users WHERE id = 1\"
    return query
"""
    assert detect(code) == "python"


def test_detect_returns_unknown_for_plain_text():
    assert detect("just a plain sentence with no code markers") == "unknown"
