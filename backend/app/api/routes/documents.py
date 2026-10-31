from fastapi import APIRouter, BackgroundTasks, UploadFile, status

from app.api.deps import DocumentServiceDep, SessionDep
from app.api.schemas.documents import DocumentOut

router = APIRouter(prefix="/sessions/{session_id}/documents", tags=["documents"])


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    session: SessionDep,
    file: UploadFile,
    documents: DocumentServiceDep,
    background: BackgroundTasks,
) -> DocumentOut:
    """Registers the PDF as `pending`; ingestion continues after the response."""
    # shortcut: multipart spools the whole body before this runs, so the size limit is checked
    # after receipt; enforce a body limit at the proxy if this is ever exposed.
    data = await file.read()
    document = await documents.upload(session, file.filename or "document.pdf", data)
    # shortcut: FastAPI BackgroundTasks, upgrade to a job queue if ingestion must survive restarts.
    background.add_task(documents.ingest, document.id, data)
    return DocumentOut.model_validate(document)


@router.get("")
async def list_documents(session: SessionDep, documents: DocumentServiceDep) -> list[DocumentOut]:
    return [DocumentOut.model_validate(d) for d in await documents.list_documents(session)]
