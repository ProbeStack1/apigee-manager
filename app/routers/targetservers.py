from fastapi import APIRouter, Query
from app.models.schemas import TargetServer
from app.core.auth import get_token
from app.core.config import BASE_URL
from app.utils.http_client import apigee_request, apigee_delete
from app.utils.validators import validate

router = APIRouter(prefix="/targetservers", tags=["Target Servers"])

def ts_url(org: str, env: str, name: str = ""):
    base = f"{BASE_URL}/organizations/{org}/environments/{env}/targetservers"
    return f"{base}/{name}" if name else base

@router.get("/")
async def list_ts(org: str = Query(...), env: str = Query(...)):
    validate(org, "org"); validate(env, "env")
    return await apigee_request("GET", ts_url(org, env), get_token())

@router.get("/{name}")
async def get_ts(name: str, org: str = Query(...), env: str = Query(...)):
    validate(org, "org"); validate(env, "env"); validate(name, "name")
    return await apigee_request("GET", ts_url(org, env, name), get_token())

@router.post("/")
async def create_ts(ts: TargetServer, org: str = Query(...), env: str = Query(...)):
    validate(org, "org"); validate(env, "env")
    return await apigee_request("POST", ts_url(org, env), get_token(), ts.model_dump())

@router.put("/{name}")
async def update_ts(name: str, ts: TargetServer, org: str = Query(...), env: str = Query(...)):
    validate(org, "org"); validate(env, "env"); validate(name, "name")
    return await apigee_request("PUT", ts_url(org, env, name), get_token(), ts.model_dump())

@router.delete("/{name}")
async def delete_ts(name: str, org: str = Query(...), env: str = Query(...)):
    validate(org, "org"); validate(env, "env"); validate(name, "name")
    return await apigee_delete(ts_url(org, env, name), get_token(), name)
