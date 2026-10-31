from fastapi import APIRouter

from app.api.deps import ContainerDep
from app.api.schemas.models import ModelOut

router = APIRouter(tags=["models"])


@router.get("/models")
async def list_models(container: ContainerDep) -> list[ModelOut]:
    return [ModelOut.model_validate(spec.model_dump()) for spec in container.model_factory.specs]
