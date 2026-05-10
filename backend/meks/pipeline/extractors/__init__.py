from meks.pipeline.extractors.pdf_extractor import extract_pdf
from meks.pipeline.extractors.docx_extractor import extract_docx
from meks.pipeline.extractors.xml_extractor import extract_xml
from meks.pipeline.extractors.text_extractor import extract_text_file


def extract_text(file_data: bytes, file_type: str) -> tuple[str, dict]:
    extractors = {
        "pdf": extract_pdf,
        "docx": extract_docx,
        "doc": extract_docx,
        "xml": extract_xml,
        "txt": extract_text_file,
        "markdown": extract_text_file,
    }
    extractor = extractors.get(file_type)
    if not extractor:
        raise ValueError(f"Unsupported file type: {file_type}")
    return extractor(file_data)
