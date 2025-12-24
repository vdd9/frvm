import re


def parse_compact_categories(text: str) -> dict[str, str]:
    """Parse compact category format like '+🥗+🐈-👎' into dict."""
    text = re.sub(r"\s+", "", text)
    result = {}
    i = 0
    n = len(text)
    while i < n:
        sign = text[i]
        if sign not in "+-":
            raise ValueError(f"Invalid format at position {i}")
        state = "YES" if sign == "+" else "NO"
        i += 1
        start = i
        while i < n and text[i] not in "+-":
            i += 1
        cat = text[start:i]
        if not cat:
            raise ValueError("Empty category")
        result[cat] = state
    return result
