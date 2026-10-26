"""Module 5: load the approved corpus strictly and chunk it with content-addressed IDs."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

CORPUS_DIR = Path(__file__).resolve().parents[1] / "data" / "corpus"
REQUIRED = {"doc_id", "title", "version", "status", "effective_date", "region"}
STATUSES = {"draft", "approved", "retired"}
REGIONS = {"all", "PK", "AE"}
MAX_CHARS = 800
OVERLAP = 120


@dataclass(frozen=True)
class Document:
    doc_id: str
    title: str
    version: int
    status: str
    effective_date: str
    region: str
    source: str
    body: str


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    version: int
    status: str
    effective_date: str
    region: str
    source: str
    heading: str
    index: int
    text: str


def parse_document(raw: str, source: str) -> Document:
    """Strict on metadata: a bad file is named and rejected, never skipped quietly."""
    match = re.match(r"---\r?\n(.*?)\r?\n---\r?\n(.*)", raw, re.S)
    if not match:
        raise ValueError(f"{source}: missing front-matter")
    meta = {}
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(":")
        if not sep:
            raise ValueError(f"{source}: bad front-matter line {line!r}")
        meta[key.strip()] = value.strip()
    if set(meta) != REQUIRED:
        raise ValueError(f"{source}: front-matter keys must be {sorted(REQUIRED)}")
    if meta["status"] not in STATUSES or meta["region"] not in REGIONS:
        raise ValueError(f"{source}: unknown status or region")
    if not re.fullmatch(r"[1-9]\d*", meta["version"]):
        raise ValueError(f"{source}: version must be a whole number")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", meta["effective_date"]):
        raise ValueError(f"{source}: effective_date must be YYYY-MM-DD")
    if not meta["doc_id"] or not meta["title"]:
        raise ValueError(f"{source}: doc_id and title are required")
    return Document(meta["doc_id"], meta["title"], int(meta["version"]), meta["status"],
                    meta["effective_date"], meta["region"], source, match.group(2))


def load_corpus(folder: Path = CORPUS_DIR) -> list[Document]:
    docs, seen = [], set()
    for path in sorted(folder.glob("*.md")):
        doc = parse_document(path.read_text(encoding="utf-8"), path.name)
        key = (doc.doc_id, doc.version)
        if key in seen:
            raise ValueError(f"{path.name}: duplicate {doc.doc_id} version {doc.version}")
        seen.add(key)
        docs.append(doc)
    return docs


def split_text(text: str, size: int = MAX_CHARS, overlap: int = OVERLAP) -> list[str]:
    """Size-based split on whitespace, with overlap that always moves forward."""
    text = text.strip()
    pieces, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            space = text.rfind(" ", start, end)
            if space > start:
                end = space
        pieces.append(text[start:end].strip())
        if end >= len(text):
            break
        start = boundary = max(end - overlap, start + 1)
        while boundary < end and not text[boundary - 1].isspace():
            boundary += 1  # begin the next piece on a word boundary, if the overlap has one
        if boundary < end:
            start = boundary
    return [p for p in pieces if p]


def chunk_id(doc: Document, index: int, text: str) -> str:
    """Content-addressed: the same text at the same place always gets the same ID."""
    key = f"{doc.doc_id}|{doc.version}|{index}|{text}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def chunk_document(doc: Document) -> list[Chunk]:
    """Split on ## headings first; only long sections are split by size.

    Text before the first heading (the fictional-policy banner) is never chunked.
    """
    chunks = []
    for section in re.split(r"^## ", doc.body, flags=re.M)[1:]:
        heading, _, text = section.partition("\n")
        for piece in split_text(" ".join(text.split())):
            index = len(chunks)
            chunks.append(Chunk(chunk_id(doc, index, piece), doc.doc_id, doc.title, doc.version,
                                doc.status, doc.effective_date, doc.region, doc.source,
                                heading.strip(), index, piece))
    return chunks


def ingest(docs: list[Document]) -> list[Chunk]:
    return [chunk for doc in docs for chunk in chunk_document(doc)]
