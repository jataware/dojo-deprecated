def try_parse_int(s: str, default: int = 0) -> int:
    try:
        return int(s)
    except ValueError:
        return default
