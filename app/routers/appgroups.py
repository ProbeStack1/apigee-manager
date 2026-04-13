from fastapi import APIRouter, Query
from app.models.schemas import AppGroup
from app.core.auth import get_token
from app.core.config import BASE_URL
from app.utils.http_client import apigee_request, apigee_delete
from app.utils.validators import validate

router = APIRouter(prefix="/appgroups", tags=["App Groups"])

def group_url(org: str, name: str = ""):
    base = f"{BASE_URL}/organizations/{org}/appgroups"
    return f"{base}/{name}" if name else base

@router.get("/")
async def list_appgroups(org: str = Query(...)):
    validate(org, "org")
    return await apigee_request("GET", group_url(org), get_token())

@router.get("/{name}")
async def get_appgroup(name: str, org: str = Query(...)):
    validate(org, "org"); validate(name, "name")
    return await apigee_request("GET", group_url(org, name), get_token())

@router.post("/")
async def create_appgroup(group: AppGroup, org: str = Query(...)):
    validate(org, "org")
    return await apigee_request("POST", group_url(org), get_token(), group.model_dump(exclude_none=True))

@router.put("/{name}")
async def update_appgroup(name: str, group: AppGroup, org: str = Query(...)):
    validate(org, "org"); validate(name, "name")
    return await apigee_request("PUT", group_url(org, name), get_token(), group.model_dump(exclude_none=True))

@router.delete("/{name}")
async def delete_appgroup(name: str, org: str = Query(...)):
    validate(org, "org"); validate(name, "name")
    return await apigee_delete(group_url(org, name), get_token(), name)
