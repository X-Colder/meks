import chardet


def extract_text_file(file_data: bytes) -> tuple[str, dict]:
    detected = chardet.detect(file_data)
    encoding = detected.get("encoding", "utf-8") or "utf-8"

    try:
        text = file_data.decode(encoding)
    except (UnicodeDecodeError, LookupError):
        text = file_data.decode("utf-8", errors="replace")

    metadata = {}
    lines = text.strip().split("\n")
    if lines:
        first_line = lines[0].strip().lstrip("# ")
        if 5 < len(first_line) < 200:
            metadata["title"] = first_line

    return text, metadata
