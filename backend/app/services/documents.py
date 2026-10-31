import asyncio
import hashlib
import uuid
from collections.abc import Callable
from itertools import batched

import structlog

from app.core.errors import ConflictError, InvalidDocumentError, PayloadTooLargeError
from app.domain.models import ChunkHit, ChunkIn, Document, Session
from app.domain.ports import Embedder, UnitOfWork

log = structlog.get_logger()

PDF_MAGIC = b"%PDF-"
MAX_FILENAME_CHARS = 255
EMBED_BATCH_SIZE = 32
INGESTION_FAILED_MESSAGE = "Could not read this PDF."
NO_TEXT_MESSAGE = "No extractable text: the PDF may be scanned images."


class DocumentService:
    """Upload, ingestion (load → chunk → embed → store) and search of a session's PDFs."""

    def __init__(
        self,
        uow: Callable[[], UnitOfWork],
        embedder: Embedder,
        load_pages: Callable[[bytes], list[str]],
        chunk: Callable[[str], list[str]],
        max_upload_bytes: int,
    ) -> None:
        self._uow = uow
        self._embedder = embedder
        self._load_pages = load_pages
        self._chunk = chunk
        self._max_upload_bytes = max_upload_bytes

    async def upload(self, session: Session, filename: str, data: bytes) -> Document:
        """Validate and register a PDF as `pending`; call `ingest` afterwards."""
        if len(data) > self._max_upload_bytes:
            raise PayloadTooLargeError(f"PDF exceeds {self._max_upload_bytes} bytes")
        if not data.startswith(PDF_MAGIC):
            raise InvalidDocumentError("Only PDF files are supported")
        sha256 = hashlib.sha256(data).hexdigest()
        async with self._uow() as uow:
            if await uow.documents.get_by_sha256(session.id, sha256) is not None:
                raise ConflictError("This PDF is already in the session")
            document = await uow.documents.add(
                session.id, filename[:MAX_FILENAME_CHARS], sha256, self._embedder.model_name
            )
            await uow.commit()
        return document

    async def list_documents(self, session: Session) -> list[Document]:
        async with self._uow() as uow:
            return await uow.documents.list_by_session(session.id)

    async def ingest(self, document_id: uuid.UUID, data: bytes) -> None:
        """Runs after the upload response, so failures are recorded on the document."""
        try:
            pages = await asyncio.to_thread(self._load_pages, data)
            pieces = [
                (page_no, text)
                for page_no, page in enumerate(pages, start=1)
                for text in self._chunk(page)
            ]
            if not pieces:
                raise InvalidDocumentError(NO_TEXT_MESSAGE)
            embeddings: list[list[float]] = []
            for batch in batched((text for _, text in pieces), EMBED_BATCH_SIZE):
                embeddings += await self._embedder.embed_documents(list(batch))
            chunks = [
                ChunkIn(page=page, ordinal=ordinal, content=text, embedding=embedding)
                for ordinal, ((page, text), embedding) in enumerate(
                    zip(pieces, embeddings, strict=True)
                )
            ]
            async with self._uow() as uow:
                await uow.documents.mark_ready(document_id, len(pages), chunks)
                await uow.commit()
        except Exception as exc:
            log.exception("ingestion_failed", document_id=str(document_id))
            message = exc.message if isinstance(exc, InvalidDocumentError) else None
            async with self._uow() as uow:
                await uow.documents.mark_failed(document_id, message or INGESTION_FAILED_MESSAGE)
                await uow.commit()
            return
        log.info("ingestion_done", document_id=str(document_id), chunks=len(chunks))

    async def has_ready(self, session_id: uuid.UUID) -> bool:
        async with self._uow() as uow:
            return await uow.documents.has_ready(session_id)

    async def search(self, session_id: uuid.UUID, query: str, limit: int) -> list[ChunkHit]:
        embedding = await self._embedder.embed_query(query)
        async with self._uow() as uow:
            return await uow.documents.search(session_id, embedding, limit)

    async def check_embedding_model(self) -> None:
        """Readiness probe: stored vectors are only comparable with the configured embedder's."""
        async with self._uow() as uow:
            mismatch = await uow.documents.has_other_embedding_model(self._embedder.model_name)
        if mismatch:
            raise RuntimeError(
                f"Documents embedded with a model other than {self._embedder.model_name!r}"
            )
