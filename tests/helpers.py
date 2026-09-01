from hashlib import sha256
from pathlib import Path

import fitz


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def make_pdf(
    path: Path,
    text: str,
    width: float = 595.0,
    height: float = 397.0,
) -> Path:
    document = fitz.open()
    page = document.new_page(width=width, height=height)
    page.insert_textbox(
        fitz.Rect(36, 36, width - 36, height - 36),
        text,
        fontsize=14,
    )
    document.save(path)
    document.close()
    return path
