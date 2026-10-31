import uuid

from fastapi import APIRouter, BackgroundTasks, Response, UploadFile, status

from app.api.deps import DocumentServiceDep
from app.api.schemas.documents import DocumentOut

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile, documents: DocumentServiceDep, background: BackgroundTasks
) -> DocumentOut:
    """Registers the PDF as `pending`; ingestion continues after the response. One file per
    request, so each file of a multi-file upload gets its own status and error."""
    # shortcut: multipart spools the whole body before this runs, so the size limit is checked
    # after receipt; enforce a body limit at the proxy if this is ever exposed.
    data = await file.read()
    document = await documents.upload(file.filename or "document.pdf", data)
    # shortcut: FastAPI BackgroundTasks, upgrade to a job queue if ingestion must survive restarts.
    background.add_task(documents.ingest, document.id, data)
    return DocumentOut.model_validate(document)


@router.get("")
async def list_documents(documents: DocumentServiceDep) -> list[DocumentOut]:
    return [DocumentOut.model_validate(d) for d in await documents.list_documents()]


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: uuid.UUID, documents: DocumentServiceDep) -> Response:
    await documents.delete(document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
