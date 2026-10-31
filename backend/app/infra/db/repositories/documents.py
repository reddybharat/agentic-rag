import uuid

from sqlalchemy import exists, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import ChunkHit, ChunkIn, Document, DocumentStatus
from app.infra.db.orm import ChunkRow, DocumentRow

# Keep scanning the HNSW index until `limit` rows pass the session filter (pgvector >= 0.8).
ITERATIVE_SCAN_SQL = "SET LOCAL hnsw.iterative_scan = strict_order"


class SqlDocumentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def add(
        self, session_id: uuid.UUID, filename: str, sha256: str, embedding_model: str
    ) -> Document:
        row = DocumentRow(
            session_id=session_id,
            filename=filename,
            sha256=sha256,
            embedding_model=embedding_model,
            status=DocumentStatus.PENDING,
        )
        self._db.add(row)
        await self._db.flush()
        await self._db.refresh(row)
        return Document.model_validate(row)

    async def get_by_sha256(self, session_id: uuid.UUID, sha256: str) -> Document | None:
        row = await self._db.scalar(
            select(DocumentRow).where(
                DocumentRow.session_id == session_id, DocumentRow.sha256 == sha256
            )
        )
        return None if row is None else Document.model_validate(row)

    async def list_by_session(self, session_id: uuid.UUID) -> list[Document]:
        rows = await self._db.scalars(
            select(DocumentRow)
            .where(DocumentRow.session_id == session_id)
            .order_by(DocumentRow.created_at)
        )
        return [Document.model_validate(row) for row in rows]

    async def has_ready(self, session_id: uuid.UUID) -> bool:
        return bool(
            await self._db.scalar(
                select(
                    exists().where(
                        DocumentRow.session_id == session_id,
                        DocumentRow.status == DocumentStatus.READY,
                    )
                )
            )
        )

    async def mark_ready(
        self, document_id: uuid.UUID, page_count: int, chunks: list[ChunkIn]
    ) -> None:
        session_id = await self._db.scalar(
            update(DocumentRow)
            .where(DocumentRow.id == document_id)
            .values(status=DocumentStatus.READY, page_count=page_count, error=None)
            .returning(DocumentRow.session_id)
        )
        if session_id is None:
            raise LookupError(f"Document {document_id} not found")
        self._db.add_all(
            ChunkRow(document_id=document_id, session_id=session_id, **chunk.model_dump())
            for chunk in chunks
        )

    async def mark_failed(self, document_id: uuid.UUID, error: str) -> None:
        await self._db.execute(
            update(DocumentRow)
            .where(DocumentRow.id == document_id)
            .values(status=DocumentStatus.FAILED, error=error)
        )

    async def search(
        self, session_id: uuid.UUID, embedding: list[float], limit: int
    ) -> list[ChunkHit]:
        await self._db.execute(text(ITERATIVE_SCAN_SQL))
        hits = (
            await self._db.execute(
                select(ChunkRow, DocumentRow.filename)
                .join(DocumentRow, DocumentRow.id == ChunkRow.document_id)
                .where(ChunkRow.session_id == session_id)
                .order_by(ChunkRow.embedding.cosine_distance(embedding))
                .limit(limit)
            )
        ).all()
        if not hits:
            return []
        neighbour_keys = {
            (chunk.document_id, chunk.ordinal + offset) for chunk, _ in hits for offset in (-1, 1)
        }
        neighbours = await self._db.execute(
            select(ChunkRow.document_id, ChunkRow.ordinal, ChunkRow.page, ChunkRow.content).where(
                ChunkRow.document_id.in_({doc_id for doc_id, _ in neighbour_keys}),
                ChunkRow.ordinal.in_({ordinal for _, ordinal in neighbour_keys}),
            )
        )
        # Context from another page would be cited with the hit's page, so it is left out.
        content_by_key = {
            (doc_id, ordinal, page): content for doc_id, ordinal, page, content in neighbours
        }
        return [
            ChunkHit(
                chunk_id=chunk.id,
                filename=filename,
                page=chunk.page,
                content=chunk.content,
                context_before=content_by_key.get(
                    (chunk.document_id, chunk.ordinal - 1, chunk.page), ""
                ),
                context_after=content_by_key.get(
                    (chunk.document_id, chunk.ordinal + 1, chunk.page), ""
                ),
            )
            for chunk, filename in hits
        ]

    async def has_other_embedding_model(self, embedding_model: str) -> bool:
        return bool(
            await self._db.scalar(
                select(
                    exists().where(
                        DocumentRow.status == DocumentStatus.READY,
                        DocumentRow.embedding_model != embedding_model,
                    )
                )
            )
        )
