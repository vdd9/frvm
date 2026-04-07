import re


def parse_compact_categories(text: str) -> dict[str, str]:
    """Parse compact category format like '+🥗+🐈-👎' into dict.
    Only parses the first line (categories). Use parse_video_txt for full parsing."""
    # Take only first line (performers may be on second line)
    first_line = text.split("\n")[0].strip()
    first_line = re.sub(r"\s+", "", first_line)
    if not first_line:
        return {}
    result = {}
    i = 0
    n = len(first_line)
    while i < n:
        sign = first_line[i]
        if sign not in "+-":
            raise ValueError(f"Invalid format at position {i}")
        state = "YES" if sign == "+" else "NO"
        i += 1
        start = i
        while i < n and first_line[i] not in "+-":
            i += 1
        cat = first_line[start:i]
        if not cat:
            raise ValueError("Empty category")
        result[cat] = state
    return result


def parse_performers_line(text: str) -> list[str]:
    """Parse performers from a line like '@Sage_bd@livymae' into a list of names.
    Can appear on the second line of a video .txt, or appended to the first line."""
    # Look for performers on second line first
    lines = text.strip().split("\n")
    perf_text = ""
    if len(lines) >= 2:
        perf_text = lines[1].strip()
    else:
        # Check if performers are appended after categories on first line
        # Find the last +/- category entry, then look for @ after it
        first_line = lines[0].strip()
        # Find first @ that could start performers
        at_pos = first_line.find("@")
        if at_pos >= 0:
            perf_text = first_line[at_pos:]

    if not perf_text:
        return []

    # Parse @name@name format
    result = []
    for part in perf_text.split("@"):
        name = part.strip()
        if name:
            result.append(name)
    return result


def format_performers_line(performers: list[str]) -> str:
    """Format a list of performer names into '@Name1@Name2' format."""
    if not performers:
        return ""
    return "".join(f"@{name}" for name in performers)
