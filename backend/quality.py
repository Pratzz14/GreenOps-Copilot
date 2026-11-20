"""Read saved profiling artifacts once, serve cached typed responses."""
import hashlib
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import ValidationError
from backend.schemas import ErrorResponse
from backend.quality_models import Report, QualityOverview, SourceDetail, IssuePage, Scope
from src.ingest import CORE_FILES, TEMPLATES
from src.source_specs import CANONICAL_FIELDS
from src.profile import digest

router = APIRouter(prefix='/api/v1/data-quality')


def load_quality(outputs: Path, snapshot_id: str | None):
    if not snapshot_id: return None, 'No valid source snapshot is loaded.'
    try:
        raw = json.loads((outputs/'data_quality.json').read_text(encoding='utf-8'))
        if not isinstance(raw,dict): raise ValueError('Report must be an object')
        report_id=raw.pop('report_id')
        if digest(raw)!=report_id: raise ValueError('Report checksum mismatch')
        raw['report_id']=report_id
        value=Report.model_validate(raw)
        manifest=json.loads((outputs/'snapshots'/snapshot_id/'manifest.json').read_text(encoding='utf-8'))
        if value.snapshot_id!=snapshot_id or raw['inputs']!=manifest['files']: raise ValueError('Report snapshot mismatch')
        if hashlib.sha256(json.dumps(raw['inputs'],sort_keys=True).encode()).hexdigest()!=snapshot_id: raise ValueError('Invalid snapshot hashes')
        if [s.name for s in value.sources]!=list(CORE_FILES) or [t.name for t in value.templates]!=list(TEMPLATES): raise ValueError('Incomplete report')
        for s in value.sources:
            if set(s.canonical_mapping)!=set(CANONICAL_FIELDS) or set(s.views)!={'full','baseline'}: raise ValueError('Incomplete mappings/views')
            if s.sha256!=next(h.sha256 for h in value.inputs if h.name==s.name): raise ValueError('Source hash mismatch')
        return value, None
    except (OSError,ValueError,KeyError,TypeError,StopIteration,ValidationError) as error:
        return None, f'Profiling report unavailable or invalid: {error}. Regenerate it and restart the API.'


def report(request: Request):
    value=request.app.state.quality
    if value is None:
        raise HTTPException(503,detail={'code':'not_ready','message':request.app.state.quality_error})
    return value


def find_source(source_name, request):
    value=report(request)
    for item in value.sources:
        if item.name==source_name: return value,item
    raise HTTPException(404,detail={'code':'not_found','message':'Unknown core source'})


@router.get('', response_model=QualityOverview, responses={503: {'model': ErrorResponse}})
def overview(request: Request, scope: Scope='full'):
    value=report(request); summaries=[]
    for s in value.sources:
        v=s.views[scope]
        summaries.append({'name':s.name,'role':s.role,'cadence':s.cadence,'rows':v.rows,'column_count':v.column_count,'missing_percent':v.missing_percent,'missing_cells':v.missing_cells,'duplicate_excess':v.duplicate_excess,'issue_counts':v.issue_counts,'date_coverage':v.date_coverage,'gap_count':sum(len(g.baseline_absent_periods if scope=='baseline' else g.internal_gaps) for g in v.gaps)})
    return {'report_id':value.report_id,'snapshot_id':value.snapshot_id,'baseline':value.baseline,'scope':scope,'sources':summaries,'limitations':value.limitations}


@router.get('/sources/{source_name}', response_model=SourceDetail, responses={503: {'model': ErrorResponse},404: {'model': ErrorResponse}})
def source(source_name: str, request: Request, scope: Scope='full'):
    value,item=find_source(source_name,request)
    # Issues are paginated separately; aggregate counts stay in the detail payload.
    view=item.views[scope].model_copy(update={'issues':[]})
    return {'report_id':value.report_id,'name':item.name,'role':item.role,'cadence':item.cadence,'scope':scope,'profile':view,'canonical_mapping':item.canonical_mapping}


@router.get('/sources/{source_name}/issues', response_model=IssuePage, responses={503: {'model': ErrorResponse},404: {'model': ErrorResponse}})
def issues(source_name: str, request: Request, scope: Scope='full', code: str | None=None, offset: int=Query(0,ge=0), limit: int=Query(20,ge=1,le=200)):
    value,item=find_source(source_name,request)
    items=[i for i in item.views[scope].issues if code is None or i.code==code]
    return {'report_id':value.report_id,'total':len(items),'offset':offset,'limit':limit,'items':items[offset:offset+limit]}
