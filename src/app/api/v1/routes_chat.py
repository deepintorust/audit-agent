from __future__ import annotations

from typing import Any
from urllib.parse import quote

from fastapi import Query, HTTPException
from fastapi.responses import StreamingResponse

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from qdrant_client.http import models as qdrant_models

from src.app.deps import (
    db as db_dep,
    qdrant as qdrant_dep,
    settings as settings_dep,
    embedding as embedding_dep,
    storage as storage_dep,
)
from src.workers._llm import llm_client as llm_client_dep

router = APIRouter(prefix="/api/v1")


class KnowledgeChatRequest(BaseModel):
    query: str
    project: str | None = ""
    company: str | None = ""
    phase: str | None = ""
    category: str | None = ""
    subcategory: str | None = ""


@router.post("/knowledges/chat")
async def knowledges_chat(
    body: KnowledgeChatRequest,
    db=Depends(db_dep),
    qdrant=Depends(qdrant_dep),
    settings=Depends(settings_dep),
    embedding=Depends(embedding_dep),
    llm_client=Depends(llm_client_dep),
) -> dict[str, Any]:
    vecs = await embedding.embed_texts([body.query])
    if not vecs:
        return {"assistant": "", "chunks": [], "documents": []}
    qvec = vecs[0]

    # 2) build filter from non-empty fields (AND / must)
    must_conditions: list[qdrant_models.FieldCondition] = []
    for fname, val in (
        ("project", body.project or ""),
        ("company", body.company or ""),
        ("phase", body.phase or ""),
        ("category", body.category or ""),
        ("subcategory", body.subcategory or ""),
    ):
        if val and str(val).strip():
            must_conditions.append(
                qdrant_models.FieldCondition(
                    key=fname, match=qdrant_models.MatchValue(value=val)
                )
            )

    q_filter = None
    if must_conditions:
        q_filter = qdrant_models.Filter(must=must_conditions)

    # 3) search qdrant
    # 3) search qdrant: use configurable limit and pass score_threshold to qdrant if supported
    limit = int(settings.qdrant_search_limit)
    # use QdrantStore.search wrapper (handles client-version differences)
    res = qdrant.search(
        collection_name=settings.qdrant_collection,
        query_vector=qvec,
        limit=limit,
        query_filter=q_filter,
        score_threshold=float(settings.similarity_threshold),
    )

    # 4) select candidates with score >= threshold
    threshold = float(settings.similarity_threshold)
    candidates: list[dict[str, Any]] = []
    for p in res:
        # p.score exists when with_scores=True
        score = float(p.score) if getattr(p, "score", None) is not None else 0.0
        if score >= threshold:
            payload = p.payload or {}
            candidates.append(
                {
                    "content": payload.get("content", ""),
                    "score": score,
                    "payload": payload,
                }
            )

    if not candidates:
        return {
            "assistant": "没有找到相关的项目资料。",
            "chunks": [],
            "documents": [],
        }

    # sort by score desc
    candidates.sort(key=lambda x: x["score"], reverse=True)

    # 5) assemble final prompt: question first, then chunks in score desc
    parts: list[str] = [body.query]
    for c in candidates:
        parts.append(c["content"])
    full_text = "\n\n".join(parts)

    # If too long, truncate to max_input_chars
    max_chars = int(settings.max_input_chars)
    if len(full_text) > max_chars:
        full_text = full_text[:max_chars]

    # 6) call LLM gateway for analysis
    from src.llm_gateway.schemas import ChatRequest

    chat_req = ChatRequest(prompt=full_text, json_mode=False)
    answer = await llm_client.chat(chat_req)

    # 7) collect chunks and related documents
    chunks_out: list[dict[str, Any]] = [
        {"chunk": c["content"], "score": c["score"]} for c in candidates
    ]

    documents: list[dict[str, str]] = []
    # lookup file info from DB for unique fileuuids
    async with db.session() as session:
        seen = set()
        for c in candidates:
            fileuuid = c["payload"].get("fileuuid")
            if not fileuuid or fileuuid in seen:
                continue
            seen.add(fileuuid)
            # query file row
            from sqlalchemy import select
            from src.db.orm.file import File as FileOrm

            f = await session.scalar(select(FileOrm).where(FileOrm.file_id == fileuuid))
            if not f:
                continue
            documents.append({"filename": f.filename, "fileid": fileuuid})

    return {"assistant": answer, "chunks": chunks_out, "documents": documents}


# 问题库问答
@router.post("/questions/chat")
async def questions_chat(): ...


# 制度库问答
@router.post("/policies/chat")
async def policies_chat(): ...


@router.get("/document/download")
async def document_download(
    id: str = Query(...),
    db=Depends(db_dep),
    storage=Depends(storage_dep),
):
    from sqlalchemy import select
    from src.db.orm.file import File as FileOrm

    async with db.session() as session:
        f = await session.scalar(select(FileOrm).where(FileOrm.file_id == id))
        if not f:
            raise HTTPException(status_code=404, detail="file not found")

        bucket = f.storage_bucket or storage.settings.s3_bucket
        key = f.storage_key
        if not key:
            raise HTTPException(status_code=404, detail="storage key missing for file")

        # download into a file-like object and stream
        fileobj = await storage.download_fileobj(bucket=bucket, key=key)
        filename_quoted = quote(f.filename)
        disposition = f"attachment; filename*=UTF-8''{filename_quoted}"
        headers = {"Content-Disposition": disposition}
        return StreamingResponse(
            fileobj,
            media_type=f.content_type or "application/octet-stream",
            headers=headers,
        )
