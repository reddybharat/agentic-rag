import uuid

from fastapi import APIRouter, status

from app.api.deps import SessionDep, SessionServiceDep
from app.api.schemas.sessions import SessionCreate, SessionOut, SessionUpdate

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_session(body: SessionCreate, sessions: SessionServiceDep) -> SessionOut:
    return SessionOut.model_validate(await sessions.create(body.title))


@router.get("")
async def list_sessions(sessions: SessionServiceDep) -> list[SessionOut]:
    return [SessionOut.model_validate(s) for s in await sessions.list_sessions()]


@router.get("/{session_id}")
async def get_session(session: SessionDep) -> SessionOut:
    return SessionOut.model_validate(session)


@router.patch("/{session_id}")
async def rename_session(
    session_id: uuid.UUID, body: SessionUpdate, sessions: SessionServiceDep
) -> SessionOut:
    return SessionOut.model_validate(await sessions.rename(session_id, body.title))


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: uuid.UUID, sessions: SessionServiceDep) -> None:
    await sessions.delete(session_id)
