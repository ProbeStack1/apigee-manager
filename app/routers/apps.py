from fastapi import APIRouter, Query
from app.models.schemas import DeveloperApp
from app.core.auth import get_token
from app.core.config import BASE_URL
from app.utils.http_client import apigee_request, apigee_delete
from app.utils.validators import validate

router = APIRouter(prefix="/apps", tags=["Apps"])

def app_url(org: str, developer_email: str, app_name: str = ""):
    base = f"{BASE_URL}/organizations/{org}/developers/{developer_email}/apps"
    return f"{base}/{app_name}" if app_name else base

def org_app_url(org: str):
    return f"{BASE_URL}/organizations/{org}/apps"

@router.get("/all")
async def list_all_apps(org: str = Query(...)):
    validate(org, "org")
    return await apigee_request("GET", org_app_url(org), get_token())

@router.get("/")
async def list_apps(org: str = Query(...), developer_email: str = Query(...)):
    validate(org, "org"); validate(developer_email, "developer_email")
    return await apigee_request("GET", app_url(org, developer_email), get_token())

@router.get("/{app_name}")
async def get_app(app_name: str, org: str = Query(...), developer_email: str = Query(...)):
    validate(org, "org"); validate(developer_email, "developer_email"); validate(app_name, "app_name")
    return await apigee_request("GET", app_url(org, developer_email, app_name), get_token())

@router.post("/")
async def create_app(app_data: DeveloperApp, org: str = Query(...), developer_email: str = Query(...)):
    validate(org, "org"); validate(developer_email, "developer_email")
    return await apigee_request("POST", app_url(org, developer_email), get_token(), app_data.model_dump(exclude_none=True))

@router.put("/{app_name}")
async def update_app(app_name: str, app_data: DeveloperApp, org: str = Query(...), developer_email: str = Query(...)):
    validate(org, "org"); validate(developer_email, "developer_email"); validate(app_name, "app_name")
    return await apigee_request("PUT", app_url(org, developer_email, app_name), get_token(), app_data.model_dump(exclude_none=True))

@router.delete("/{app_name}")
async def delete_app(app_name: str, org: str = Query(...), developer_email: str = Query(...)):
    validate(org, "org"); validate(developer_email, "developer_email"); validate(app_name, "app_name")
    return await apigee_delete(app_url(org, developer_email, app_name), get_token(), app_name)
