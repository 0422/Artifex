import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.scenario import ScenarioCreate, ScenarioRead, ScenarioUpdate
from app.services import scenario_service

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.get("", response_model=list[ScenarioRead])
async def get_scenarios(
    include_inactive: bool = Query(default=False),
    domain: str | None = Query(default=None, max_length=50),
    category_id: uuid.UUID | None = Query(default=None),
    q: str | None = Query(default=None, max_length=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ScenarioRead]:
    scenarios = await scenario_service.list_scenarios(
        db,
        current_user.id,
        include_inactive,
        domain=domain,
        category_id=category_id,
        query=q,
    )
    return [ScenarioRead.model_validate(scenario) for scenario in scenarios]


@router.post("", response_model=ScenarioRead, status_code=status.HTTP_201_CREATED)
async def create_scenario(
    payload: ScenarioCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScenarioRead:
    scenario = await scenario_service.create_scenario(db, current_user.id, payload)
    return ScenarioRead.model_validate(scenario)


@router.put("/{scenario_id}", response_model=ScenarioRead)
async def update_scenario(
    scenario_id: uuid.UUID,
    payload: ScenarioUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScenarioRead:
    scenario = await scenario_service.get_scenario(db, scenario_id, current_user.id)
    if scenario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="场景不存在")
    scenario = await scenario_service.update_scenario(db, scenario, payload)
    return ScenarioRead.model_validate(scenario)


@router.delete("/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scenario(
    scenario_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    scenario = await scenario_service.get_scenario(db, scenario_id, current_user.id)
    if scenario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="场景不存在")
    await scenario_service.deactivate_scenario(db, scenario)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
