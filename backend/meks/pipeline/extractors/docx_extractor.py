from io import BytesIO

from docx import Document


def extract_docx(file_data: bytes) -> tuple[str, dict]:
    doc = Document(BytesIO(file_data))
    metadata = {}

    core_props = doc.core_properties
    if core_props.title:
        metadata["title"] = core_props.title
    if core_props.author:
        metadata["authors"] = core_props.author

    paragraphs = []
    for para in doc.paragraphs:
        if para.text.strip():
            paragraphs.append(para.text)

    full_text = "\n\n".join(paragraphs)
    return full_text, metadata
