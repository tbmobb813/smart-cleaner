def test_toml_parser_available():
    try:
        import tomllib  # type: ignore
        available = True
    except Exception:
        try:
            import tomli  # type: ignore
            available = True
        except Exception:
            available = False

    assert available, "No TOML parser available; install tomli for Python <3.11"
