
from uuid import UUID
import math

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agents.workflow import run_fsi_workflow


router = APIRouter(
    prefix="/api/v1/intelligence",
    tags=["FSI Intelligence"],
)


class IntelligenceRequest(BaseModel):
    run_id: UUID
    as_of_second: float = Field(ge=0, le=5400)
    fan_level: str = Field(default="beginner")
    preferred_team: str = Field(default="BLU")


@router.post("/analyse")
async def analyse_match(request: IntelligenceRequest):
    if not math.isfinite(request.as_of_second):
        raise HTTPException(
            status_code=422,
            detail="Invalid match time",
        )

    if request.fan_level not in {
        "beginner", "enthusiast", "advanced"
    }:
        raise HTTPException(
            status_code=422,
            detail="Invalid fan level",
        )

    if request.preferred_team not in {"RED", "BLU"}:
        raise HTTPException(
            status_code=422,
            detail="Invalid preferred team",
        )

    return await run_fsi_workflow(
        run_id=str(request.run_id),
        as_of_second=request.as_of_second,
        fan_level=request.fan_level,
        preferred_team=request.preferred_team,
    )
