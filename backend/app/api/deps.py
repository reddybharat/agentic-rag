import uuid
from typing import Annotated

from fastapi import Depends, Request

from app.api.schemas.chat import ChatRequest, MessageIn
from app.container import Container
from app.domain.models import Session
from app.services.chat import ChatService
from app.services.documents import DocumentService
from app.services.sessions import SessionService


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


ContainerDep = Annotated[Container, Depends(get_container)]


def get_session_service(container: ContainerDep) -> SessionService:
    return container.sessions


def get_chat_service(container: ContainerDep) -> ChatService:
    return container.chat


def get_document_service(container: ContainerDep) -> DocumentService:
    return container.documents


SessionServiceDep = Annotated[SessionService, Depends(get_session_service)]
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]


async def get_session(session_id: uuid.UUID, sessions: SessionServiceDep) -> Session:
    return await sessions.get(session_id)


SessionDep = Annotated[Session, Depends(get_session)]


async def get_chat_request(body: MessageIn, chat: ChatServiceDep) -> ChatRequest:
    """Validates the model before streaming starts, so a bad id is a 422 and not a stream error."""
    return ChatRequest(text=body.text, model_id=chat.resolve_model_id(body.model_id))


ChatRequestDep = Annotated[ChatRequest, Depends(get_chat_request)]
