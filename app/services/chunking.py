import io
from dataclasses import dataclass

from pypdf import PdfReader


@dataclass(frozen=True)
class TextChunk:
    page: int
    content: str


def extract_pages(data: bytes) -> list[str]:
    reader = PdfReader(io.BytesIO(data))
    return [page.extract_text() or "" for page in reader.pages]


def chunk_pages(pages: list[str], size: int, overlap: int) -> list[TextChunk]:
    """Split each page into overlapping chunks of roughly `size` characters.

    Chunks never span pages, so every chunk maps to an exact page for citations.
    Cuts prefer a sentence end, then a space, in the back half of the window.
    """
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")

    chunks: list[TextChunk] = []
    for page_no, raw in enumerate(pages, start=1):
        text = " ".join(raw.split())
        start = 0
        while start < len(text):
            end = min(start + size, len(text))
            if end < len(text):
                floor = start + size // 2
                cut = text.rfind(". ", floor, end)
                if cut == -1:
                    cut = text.rfind(" ", floor, end)
                if cut != -1:
                    end = cut + 1
            piece = text[start:end].strip()
            if piece:
                chunks.append(TextChunk(page=page_no, content=piece))
            if end >= len(text):
                break
            start = max(end - overlap, start + 1)
    return chunks
