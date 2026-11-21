"""Health and read-only published Gold results."""

from typing import Annotated, Literal

from fastapi import APIRouter, Path, Query, Request
from fastapi.responses import FileResponse

from backend.gold import not_found, read_gold
from backend.gold_models import (
    EvidencePage, GoldBreakdown, GoldFactor, GoldFinding, GoldMeasure, GoldOverview,
    GoldPackage, GoldRun, GoldSafety, GoldTableCatalog, GoldTablePage, Group, Scenario,
)
from backend.schemas import ErrorResponse, Health
from backend.utilization import inspect_utilization

router = APIRouter(prefix="/api/v1")
Identifier = Annotated[str, Path(pattern=r"^[A-Za-z0-9_-]{1,100}$")]
LiteralExport = Literal["baseline.csv", "measures.csv"]
GOLD_ERRORS = {
    503: {"model": ErrorResponse, "description": "Gold publication is unavailable"},
    404: {"model": ErrorResponse, "description": "Unknown Gold result"},
}
FINDINGS = """
    SELECT f.* EXCLUDE (run_id, subject_id), s.subject_name
    FROM gold.finding f JOIN gold.subject s USING (run_id, subject_id) WHERE f.run_id=?
"""


@router.get("/health", response_model=Health)
def health(request: Request) -> Health:
    return request.app.state.health


@router.get("/runs/current", response_model=GoldRun, responses=GOLD_ERRORS)
def current_run(request: Request):
    with read_gold(request) as gold:
        return gold.identity()


@router.get("/runs/{run_id}/overview", response_model=GoldOverview, responses=GOLD_ERRORS)
def overview(run_id: Identifier, request: Request, scenario: Scenario = "mid"):
    with read_gold(request, run_id) as gold:
        row = gold.analysis(1, scenario=scenario)[0]
        coverage = {field: row[field] for field in ("cost_coverage", "energy_coverage", "carbon_coverage")}
        return {
            "context": gold.identity(scenario),
            "cost": {"value": row["recorded_cost_chf"], "unit": "CHF", "estimated": False,
                     "quality_flags": [coverage["cost_coverage"]]},
            "energy": {"value": row["estimated_kwh"], "unit": "kWh", "estimated": True,
                       "quality_flags": [coverage["energy_coverage"]]},
            "emissions": {"value": row["estimated_location_kg"], "unit": f'kg_{row["emissions_basis"]}',
                          "estimated": True, "quality_flags": [coverage["carbon_coverage"]]},
            "imputed_cost_chf": row.get("imputed_cost_chf"),
            "recovered_cost_chf": row.get("recovered_cost_chf"),
            "swiss_operating_kg_co2e": row.get("swiss_operating_kg_co2e"),
            **coverage, "evidence_set_id": gold.run["evidence_set_id"],
            **{key: row[key] or 0 for key in ("included_rows", "missing_amount_rows", "missing_fx_rows", "review_rows")},
        }


@router.get("/runs/{run_id}/breakdowns", response_model=list[GoldBreakdown], responses=GOLD_ERRORS)
def breakdowns(run_id: Identifier, request: Request, group: Group = "department", scenario: Scenario = "mid"):
    with read_gold(request, run_id) as gold:
        return gold.analysis(2, scenario=scenario, group_by=group)


@router.get("/runs/{run_id}/utilization", responses=GOLD_ERRORS)
def utilization(run_id: Identifier, request: Request,
                months: Annotated[list[str] | None, Query()] = None,
                scenario: Scenario = "mid", group: Group = "tool", driver: str = "",
                include_estimates: bool = False):
    with read_gold(request, run_id) as gold:
        return inspect_utilization(gold, request.app.state.outputs, months, scenario, group, driver,
                                   include_estimates=include_estimates)


@router.get("/runs/{run_id}/tables", response_model=GoldTableCatalog, responses=GOLD_ERRORS)
def gold_tables(run_id: Identifier, request: Request):
    with read_gold(request, run_id) as gold:
        return {"run_id": run_id, "tables": gold.tables()}


@router.get("/runs/{run_id}/tables/{table}", response_model=GoldTablePage, responses=GOLD_ERRORS)
def gold_table(run_id: Identifier, table: Identifier, request: Request,
               offset: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100)):
    with read_gold(request, run_id) as gold:
        return gold.table_page(table, offset, limit)


@router.get("/runs/{run_id}/findings", response_model=list[GoldFinding], responses=GOLD_ERRORS)
def findings(run_id: Identifier, request: Request):
    with read_gold(request, run_id) as gold:
        return gold.select(FINDINGS + " ORDER BY f.finding_id")


@router.get("/runs/{run_id}/findings/{finding_id}", response_model=GoldFinding, responses=GOLD_ERRORS)
def finding(run_id: Identifier, finding_id: Identifier, request: Request):
    with read_gold(request, run_id) as gold:
        rows = gold.select(FINDINGS + " AND f.finding_id=?", finding_id)
        if not rows:
            raise not_found()
        return rows[0]


@router.get("/runs/{run_id}/factors", response_model=list[GoldFactor], responses=GOLD_ERRORS)
def factors(run_id: Identifier, request: Request):
    with read_gold(request, run_id) as gold:
        return gold.select("""
            SELECT * EXCLUDE (run_id, valid_from, valid_to_exclusive)
            FROM gold.factor WHERE run_id=? ORDER BY factor_id
        """)


@router.get("/runs/{run_id}/measures", response_model=list[GoldMeasure], responses=GOLD_ERRORS)
def measures(run_id: Identifier, request: Request):
    with read_gold(request, run_id) as gold:
        return gold.measures()


@router.get("/runs/{run_id}/safety-decisions", response_model=GoldSafety, responses=GOLD_ERRORS)
def safety_decisions(run_id: Identifier, request: Request):
    with read_gold(request, run_id) as gold:
        return {"decisions": gold.measures(only_review=True), "protections": gold.protections()}


@router.get("/runs/{run_id}/evidence/{evidence_set_id}", response_model=EvidencePage, responses=GOLD_ERRORS)
def evidence(run_id: Identifier, evidence_set_id: Identifier, request: Request,
             limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
    with read_gold(request, run_id) as gold:
        total = gold.select("""
            SELECT COUNT(*) AS total FROM gold.evidence WHERE run_id=? AND evidence_set_id=?
        """, evidence_set_id)[0]["total"]
        if not total:
            raise not_found()
        rows = gold.select("""
            SELECT e.evidence_type, e.source_file, e.source_row, e.source_record_id, e.detail,
                   e.factor_id, f.factor_name, f.source_reference
            FROM gold.evidence e LEFT JOIN gold.factor f USING (run_id, factor_id)
            WHERE e.run_id=? AND e.evidence_set_id=? ORDER BY e.evidence_no LIMIT ? OFFSET ?
        """, evidence_set_id, limit, offset)
        return {"run_id": run_id, "evidence_set_id": evidence_set_id, "total": total, "offset": offset, "items": rows}


@router.get("/runs/{run_id}/{section}", include_in_schema=False)
def unknown_section(run_id: Identifier, section: Literal["findings", "measures", "safety-decisions", "factors"]):
    # Preserve validation for the original /runs/{run_id}/{section} interface.
    raise not_found()


@router.get("/packages/{package_id}", response_model=GoldPackage, responses=GOLD_ERRORS)
def package(package_id: Identifier, request: Request):
    with read_gold(request, package_id.removesuffix("-conditional")) as gold:
        return gold.package(package_id)


@router.get("/packages/{package_id}/exports/{filename}", response_class=FileResponse, responses=GOLD_ERRORS)
def export(package_id: Identifier, filename: LiteralExport, request: Request):
    run_id = package_id.removesuffix("-conditional")
    conditional = run_id != package_id
    with read_gold(request, run_id) as gold:
        primary = gold.select("""
            SELECT evaluation_status FROM gold.package_result WHERE run_id=? AND package_id=?
                AND scenario='mid' AND horizon='steady_state'
        """, package_id)
        if not primary:
            raise not_found()
        official_name = ("template_baseline_and_assumptions.csv" if filename == "baseline.csv"
                         else "template_measures_package.csv")
        artifact_name = "conditional-measures.csv" if conditional and filename == "measures.csv" else filename
        if artifact_name not in gold.metadata["artifacts"]:
            raise not_found()
        artifact = gold.directory / artifact_name
        prefix = "draft-conditional-" if conditional else "draft-" if primary[0]["evaluation_status"] != "evaluated" else ""
        return FileResponse(artifact, media_type="text/csv", filename=prefix + official_name)
