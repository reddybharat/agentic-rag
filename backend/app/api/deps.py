import uuid
from typing import Annotated

from fastapi import Depends, Request

from app.container import Container
from app.domain.models import Session
from app.services.chat import ChatService
from app.services.sessions import SessionService


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


ContainerDep = Annotated[Container, Depends(get_container)]


def get_session_service(container: ContainerDep) -> SessionService:
    return container.sessions


def get_chat_service(container: ContainerDep) -> ChatService:
    return container.chat


SessionServiceDep = Annotated[SessionService, Depends(get_session_service)]
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]


async def get_session(session_id: uuid.UUID, sessions: SessionServiceDep) -> Session:
    return await sessions.get(session_id)


SessionDep = Annotated[Session, Depends(get_session)]
