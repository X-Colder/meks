import fitz


def extract_pdf(file_data: bytes) -> tuple[str, dict]:
    doc = fitz.open(stream=file_data, filetype="pdf")
    metadata = {}

    if doc.metadata:
        metadata["title"] = doc.metadata.get("title", "")
        metadata["authors"] = doc.metadata.get("author", "")

    pages_text = []
    for page in doc:
        pages_text.append(page.get_text())

    full_text = "\n\n".join(pages_text)

    lines = full_text.split("\n")
    if lines and not metadata.get("title"):
        for line in lines[:5]:
            stripped = line.strip()
            if len(stripped) > 10:
                metadata["title"] = stripped
                break

    abstract_start = full_text.lower().find("abstract")
    if abstract_start >= 0:
        abstract_text = full_text[abstract_start:abstract_start + 2000]
        end_markers = ["introduction", "keywords", "1.", "1 "]
        end_pos = len(abstract_text)
        for marker in end_markers:
            pos = abstract_text.lower().find(marker, 10)
            if 0 < pos < end_pos:
                end_pos = pos
        metadata["abstract"] = abstract_text[len("abstract"):end_pos].strip()

    doc.close()
    return full_text, metadata
