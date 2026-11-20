"""Phase 1 routes; calculation endpoints fail explicitly until implemented."""

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Path, Request

from backend.schemas import ErrorResponse, Health, Overview, RunIdentity

router = APIRouter(prefix="/api/v1")
Identifier = Annotated[str, Path(pattern=r"^[A-Za-z0-9_-]{1,100}$")]
LiteralSection = Literal["findings", "measures", "safety-decisions", "factors"]
LiteralExport = Literal["baseline.csv", "measures.csv"]
NOT_READY = {503: {"model": ErrorResponse, "description": "No calculated run exists yet"}}


def not_ready() -> None:
    raise HTTPException(status_code=503, detail={
        "code": "not_ready",
        "message": "Calculated run unavailable. Source snapshotting does not calculate a baseline or package.",
    })


@router.get("/health", response_model=Health)
def health(request: Request) -> Health:
    return request.app.state.health


@router.get("/runs/current", response_model=RunIdentity, responses=NOT_READY)
def current_run():
    not_ready()


@router.get("/runs/{run_id}/overview", response_model=Overview, responses=NOT_READY)
def overview(run_id: Identifier):
    not_ready()


@router.get("/runs/{run_id}/{section}", responses=NOT_READY)
def run_section(run_id: Identifier, section: LiteralSection):
    not_ready()


@router.get("/runs/{run_id}/findings/{finding_id}", responses=NOT_READY)
def finding(run_id: Identifier, finding_id: Identifier):
    not_ready()


@router.get("/packages/{package_id}", responses=NOT_READY)
def package(package_id: Identifier):
    not_ready()


@router.get("/packages/{package_id}/exports/{filename}", responses=NOT_READY)
def export(package_id: Identifier, filename: LiteralExport):
    not_ready()
