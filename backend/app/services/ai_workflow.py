from __future__ import annotations

import math
import os
import re
from typing import Iterable, List, Sequence, Tuple

import numpy as np
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ..models.ai_config import AiKnowledgeBaseChunk, AiKnowledgeBaseDocument

_TOKEN_RE = re.compile(r"[A-Za-z0-9\u4e00-\u9fff]+")
_DEFAULT_CHUNK_SIZE = 450
_DEFAULT_CHUNK_OVERLAP = 80
_MAX_CHUNK_FETCH = 420


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_text_into_chunks(
    text: str,
    chunk_size: int = _DEFAULT_CHUNK_SIZE,
    overlap: int = _DEFAULT_CHUNK_OVERLAP,
) -> List[str]:
    text = _normalize_text(text)
    if not text:
        return []
    sentences = re.split(r"(\n|[。！？?!])", text)
    buffer = ""
    chunks: List[str] = []
    for part in sentences:
        buffer += part
        if len(buffer) >= chunk_size:
            chunks.append(buffer.strip())
            buffer = buffer[-overlap:]
    if buffer.strip():
        chunks.append(buffer.strip())
    if not chunks:
        chunks.append(text[:chunk_size])
    return [c for c in chunks if c]


def _read_text_file(path: str) -> str:
    try:
        with open(path, "rb") as f:
            data = f.read()
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _extract_from_pdf(path: str, max_pages: int = 20) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        return ""
    try:
        reader = PdfReader(path)
        texts = []
        for page in reader.pages[:max_pages]:
            content = page.extract_text() or ""
            texts.append(content)
        return "\n".join(texts)
    except Exception:
        return ""


def _extract_from_docx(path: str) -> str:
    try:
        import docx  # type: ignore
    except Exception:
        return ""
    try:
        document = docx.Document(path)
        return "\n".join(p.text for p in document.paragraphs if p.text)
    except Exception:
        return ""


def _extract_from_csv(path: str, limit_rows: int = 200) -> str:
    try:
        import csv
    except Exception:
        return ""
    rows = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            for idx, row in enumerate(reader):
                rows.append("\t".join(row))
                if idx >= limit_rows:
                    break
    except Exception:
        return ""
    return "\n".join(rows)


def extract_text_from_file(path: str, file_ext: str) -> str:
    ext = (file_ext or os.path.splitext(path)[1]).lower()
    if ext in {".txt", ".md"}:
        return _read_text_file(path)
    if ext in {".csv", ".tsv"}:
        return _extract_from_csv(path)
    if ext == ".pdf":
        return _extract_from_pdf(path)
    if ext in {".docx", ".doc"}:
        text = _extract_from_docx(path)
        if text:
            return text
        return _read_text_file(path)
    if ext in {".xlsx", ".xls"}:
        try:
            import pandas as pd  # type: ignore
        except Exception:
            return ""
        try:
            df = pd.read_excel(path)
            return df.to_csv(index=False)
        except Exception:
            return ""
    return _read_text_file(path)


async def delete_document_chunks(db: AsyncSession, document_id: int) -> None:
    await db.execute(delete(AiKnowledgeBaseChunk).where(AiKnowledgeBaseChunk.document_id == document_id))


def _extract_tokens(text: str, limit: int = 40) -> str:
    tokens = _TOKEN_RE.findall(text)
    return " ".join(tokens[:limit])


async def rebuild_document_chunks(
    db: AsyncSession,
    document: AiKnowledgeBaseDocument,
    text: str,
    *,
    chunk_size: int = _DEFAULT_CHUNK_SIZE,
    overlap: int = _DEFAULT_CHUNK_OVERLAP,
) -> int:
    if not document.knowledge_base_id:
        return 0
    await delete_document_chunks(db, document.id)
    content = _normalize_text(text)
    if not content:
        return 0
    chunks = split_text_into_chunks(content, chunk_size=chunk_size, overlap=overlap)
    for idx, chunk_text in enumerate(chunks):
        db.add(
            AiKnowledgeBaseChunk(
                knowledge_base_id=document.knowledge_base_id,
                document_id=document.id,
                seq=idx,
                content=chunk_text,
                tokens=_extract_tokens(chunk_text),
                document_title=document.title,
                document_url=document.url,
            )
        )
    return len(chunks)


async def fetch_recent_chunks(
    db: AsyncSession,
    kb_ids: Sequence[int],
    *,
    fetch_limit: int = _MAX_CHUNK_FETCH,
) -> List[AiKnowledgeBaseChunk]:
    if not kb_ids:
        return []
    stmt = (
        select(AiKnowledgeBaseChunk)
        .where(AiKnowledgeBaseChunk.knowledge_base_id.in_(kb_ids))
        .order_by(AiKnowledgeBaseChunk.created_at.desc())
        .limit(fetch_limit)
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def retrieve_top_chunks(
    db: AsyncSession,
    kb_ids: Sequence[int],
    question: str,
    *,
    limit: int = 6,
    fetch_limit: int = _MAX_CHUNK_FETCH,
) -> List[Tuple[AiKnowledgeBaseChunk, float]]:
    chunks = await fetch_recent_chunks(db, kb_ids, fetch_limit=fetch_limit)
    if not chunks:
        return []
    cleaned_question = (question or "").strip()
    if not cleaned_question:
        return [(chunk, 0.0) for chunk in chunks[:limit]]
    texts = [chunk.content for chunk in chunks]
    try:
        vectorizer = TfidfVectorizer(max_df=0.95, min_df=1, ngram_range=(1, 2))
        matrix = vectorizer.fit_transform(texts + [cleaned_question])
        query_vec = matrix[-1]
        doc_mat = matrix[:-1]
    except ValueError:
        return [(chunk, 0.0) for chunk in chunks[:limit]]

    sims = cosine_similarity(doc_mat, query_vec.reshape(1, -1)).ravel()
    if sims.size == 0:
        return [(chunk, 0.0) for chunk in chunks[:limit]]
    top_indices = np.argsort(sims)[::-1][: limit or 6]
    results: List[Tuple[AiKnowledgeBaseChunk, float]] = []
    for idx in top_indices:
        score = float(sims[idx])
        chunk = chunks[int(idx)]
        results.append((chunk, score))
    return results
