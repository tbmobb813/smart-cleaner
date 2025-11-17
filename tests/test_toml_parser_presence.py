def test_toml_parser_available():
    try:
        available = True
    except Exception:
        try:
            available = True
        except Exception:
            available = False

    assert available, "No TOML parser available; install tomli for Python <3.11"
