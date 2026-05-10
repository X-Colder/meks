from lxml import etree


def extract_xml(file_data: bytes) -> tuple[str, dict]:
    metadata = {}
    root = etree.fromstring(file_data)

    nsmap = {
        "nlm": "http://dtd.nlm.nih.gov/publishing/",
    }

    title_el = root.find(".//{*}article-title")
    if title_el is not None and title_el.text:
        metadata["title"] = title_el.text

    authors = []
    for contrib in root.iter("{*}contrib"):
        if contrib.get("contrib-type") == "author":
            surname = contrib.findtext("{*}name/{*}surname", "")
            given = contrib.findtext("{*}name/{*}given-names", "")
            if surname:
                authors.append(f"{given} {surname}".strip())
    if authors:
        metadata["authors"] = ", ".join(authors)

    abstract_el = root.find(".//{*}abstract")
    if abstract_el is not None:
        metadata["abstract"] = " ".join(abstract_el.itertext()).strip()

    body_el = root.find(".//{*}body")
    if body_el is not None:
        full_text = " ".join(body_el.itertext()).strip()
    else:
        full_text = " ".join(root.itertext()).strip()

    return full_text, metadata
