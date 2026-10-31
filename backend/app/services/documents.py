import asyncio
import hashlib
import time
import uuid
from collections.abc import Callable
from itertools import batched

import structlog

from app.core.errors import (
    ConflictError,
    InvalidDocumentError,
    NotFoundError,
    PayloadTooLargeError,
)
from app.domain.models import ChunkHit, ChunkIn, Document
from app.domain.ports import Embedder, UnitOfWork

log = structlog.get_logger()

PDF_MAGIC = b"%PDF-"
MAX_FILENAME_CHARS = 255
EMBED_BATCH_SIZE = 32
MS_PER_S = 1000
INGESTION_FAILED_MESSAGE = "Could not read this PDF."
NO_TEXT_MESSAGE = "No extractable text: the PDF may be scanned images."


class DocumentService:
    """The owner's PDF library: upload, ingestion (load → chunk → embed → store), search, delete."""

    def __init__(
        self,
        uow: Callable[[], UnitOfWork],
        owner_id: str,
        embedder: Embedder,
        load_pages: Callable[[bytes], list[str]],
        chunk: Callable[[str], list[str]],
        max_upload_bytes: int,
    ) -> None:
        self._uow = uow
        self._owner_id = owner_id
        self._embedder = embedder
        self._load_pages = load_pages
        self._chunk = chunk
        self._max_upload_bytes = max_upload_bytes

    async def upload(self, filename: str, data: bytes) -> Document:
        """Validate and register a PDF as `pending`; call `ingest` afterwards."""
        if len(data) > self._max_upload_bytes:
            log.warning("upload_rejected", reason="size", filename=filename, bytes=len(data))
            raise PayloadTooLargeError(f"PDF exceeds {self._max_upload_bytes} bytes")
        if not data.startswith(PDF_MAGIC):
            log.warning("upload_rejected", reason="type", filename=filename, bytes=len(data))
            raise InvalidDocumentError("Only PDF files are supported")
        sha256 = hashlib.sha256(data).hexdigest()
        async with self._uow() as uow:
            if await uow.documents.get_by_sha256(self._owner_id, sha256) is not None:
                log.warning("upload_rejected", reason="duplicate", filename=filename)
                raise ConflictError("This PDF is already in the library")
            document = await uow.documents.add(
                self._owner_id, filename[:MAX_FILENAME_CHARS], sha256, self._embedder.model_name
            )
            await uow.commit()
        log.info(
            "upload_received",
            document_id=str(document.id),
            owner_id=self._owner_id,
            filename=document.filename,
            bytes=len(data),
        )
        return document

    async def list_documents(self) -> list[Document]:
        async with self._uow() as uow:
            return await uow.documents.list_by_owner(self._owner_id)

    async def delete(self, document_id: uuid.UUID) -> None:
        async with self._uow() as uow:
            deleted = await uow.documents.delete(self._owner_id, document_id)
            await uow.commit()
        if not deleted:
            raise NotFoundError(f"Document {document_id} not found")
        log.info("document_deleted", document_id=str(document_id), owner_id=self._owner_id)

    async def ingest(self, document_id: uuid.UUID, data: bytes) -> None:
        """Runs after the upload response, so failures are recorded on the document."""
        ingest_log = log.bind(document_id=str(document_id), owner_id=self._owner_id)
        ingest_log.info("ingestion_started", bytes=len(data))
        started = stage_started = time.perf_counter()
        timings: dict[str, int] = {}

        def end_stage(stage: str) -> None:
            nonlocal stage_started
            now = time.perf_counter()
            timings[f"{stage}_ms"] = round((now - stage_started) * MS_PER_S)
            stage_started = now

        try:
            pages = await asyncio.to_thread(self._load_pages, data)
            end_stage("load")
            pieces = [
                (page_no, text)
                for page_no, page in enumerate(pages, start=1)
                for text in self._chunk(page)
            ]
            end_stage("chunk")
            if not pieces:
                raise InvalidDocumentError(NO_TEXT_MESSAGE)
            embeddings: list[list[float]] = []
            for batch in batched((text for _, text in pieces), EMBED_BATCH_SIZE):
                embeddings += await self._embedder.embed_documents(list(batch))
            end_stage("embed")
            chunks = [
                ChunkIn(page=page, ordinal=ordinal, content=text, embedding=embedding)
                for ordinal, ((page, text), embedding) in enumerate(
                    zip(pieces, embeddings, strict=True)
                )
            ]
            async with self._uow() as uow:
                await uow.documents.mark_ready(document_id, len(pages), chunks)
                await uow.commit()
            end_stage("store")
        except Exception as exc:
            ingest_log.exception("ingestion_failed", **timings)
            message = exc.message if isinstance(exc, InvalidDocumentError) else None
            async with self._uow() as uow:
                await uow.documents.mark_failed(document_id, message or INGESTION_FAILED_MESSAGE)
                await uow.commit()
            return
        ingest_log.info(
            "ingestion_done",
            pages=len(pages),
            chunks=len(chunks),
            embed_batches=-(-len(pieces) // EMBED_BATCH_SIZE),
            total_ms=round((time.perf_counter() - started) * MS_PER_S),
            **timings,
        )

    async def has_ready(self, owner_id: str) -> bool:
        async with self._uow() as uow:
            return await uow.documents.has_ready(owner_id)

    async def search(self, owner_id: str, query: str, limit: int) -> list[ChunkHit]:
        started = time.perf_counter()
        embedding = await self._embedder.embed_query(query)
        async with self._uow() as uow:
            hits = await uow.documents.search(owner_id, embedding, limit)
        log.info(
            "search_done",
            owner_id=owner_id,
            query_chars=len(query),
            hits=len(hits),
            duration_ms=round((time.perf_counter() - started) * MS_PER_S),
        )
        return hits

    async def check_embedding_model(self) -> None:
        """Readiness probe: stored vectors are only comparable with the configured embedder's."""
        async with self._uow() as uow:
            mismatch = await uow.documents.has_other_embedding_model(self._embedder.model_name)
        if mismatch:
            raise RuntimeError(
                f"Documents embedded with a model other than {self._embedder.model_name!r}"
            )
