from fastapi import APIRouter, Depends, Query, Path, HTTPException
from app.auth import UserAuth
from app.session import Session
from app.utils import get_tag_names

tags = [
    {
        'name': 'procedure',
        'description': 'Manage recipe procedures and steps within a session'
    }
]
router = APIRouter(prefix='/session/{session_id}/procedure', tags=get_tag_names(tags),
                   dependencies=[Depends(UserAuth.require_authorization)])

PARAM_SESSION_ID = Path(None, alias='session_id', description='A session UID, e.g. linked to a set of camera streams')

@router.get('/', summary='Get the list of steps and the current index of the active procedure')
async def get_procedure(uid: str = PARAM_SESSION_ID):
    pid,index,steps = await Session.getProcedureInfo(uid)
    return {
        'index': index or 0,
        'steps': steps,
    }

@router.post('/load/{procedure_id}', summary='Set the active procedure of the session')
async def set_procedure(
        uid: str = PARAM_SESSION_ID,
        procedure_id: str = Path(None, description='The ID of the procedure to be set, e.g. `orange` or `desk-stuff`')):
    await Session.setProcedureInfo(uid, procedure_id, 0)
    return {
        'index': 0,
        'steps': Session.getProcedureSteps(procedure_id),
    }

@router.get('/current', summary='Get the current status of the active procedure')
async def get_procedure_current_step(
        uid: str = PARAM_SESSION_ID,
        offset: int | None = Query(0, description="Unused at the moment")):
    pid, i, proc = await Session.getProcedureInfo(uid)
    if not pid:
        return {}
    return {
        'index': i,
        'step': proc[i],
        'next': proc[i+1] if len(proc) > i+1 else None,
    }

@router.post('/current/{step}', summary='Advance a number of steps of the active procedure')
async def get_procedure_inc_step(uid: str = PARAM_SESSION_ID,
                                 step: int = Path(0, description="The number of steps to advance")):
    pid, i, proc = await Session.getProcedureInfo(uid)
    if not pid:
        raise HTTPException(status_code=400,
            detail='No procedure set. Use POST /session/{session_id}/procedure/load/{procedure_id}')
    inew = min(max(0, i + step), len(proc))
    if i != inew:
        await Session.setProcedureIndex(uid, inew)
        i = inew
        return {
            'index': i,
            'current': proc[i],
            'next': proc[i+1] if len(proc) > i+1 else None,
    }
