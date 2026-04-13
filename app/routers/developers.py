from fastapi import APIRouter, Query
from app.models.schemas import Developer
from app.core.auth import get_token
from app.core.config import BASE_URL
from app.utils.http_client import apigee_request, apigee_delete
from app.utils.validators import validate

router = APIRouter(prefix="/developers", tags=["Developers"])

def dev_url(org: str, email: str = ""):
    base = f"{BASE_URL}/organizations/{org}/developers"
    return f"{base}/{email}" if email else base

@router.get("/")
async def list_developers(org: str = Query(...)):
    validate(org, "org")
    return await apigee_request("GET", dev_url(org), get_token())

@router.get("/{email}")
async def get_developer(email: str, org: str = Query(...)):
    validate(org, "org"); validate(email, "email")
    return await apigee_request("GET", dev_url(org, email), get_token())

@router.post("/")
async def create_developer(dev: Developer, org: str = Query(...)):
    validate(org, "org"); validate(dev.email, "email")
    return await apigee_request("POST", dev_url(org), get_token(), dev.model_dump())

@router.put("/{email}")
async def update_developer(email: str, dev: Developer, org: str = Query(...)):
    validate(org, "org"); validate(email, "email")
    return await apigee_request("PUT", dev_url(org, email), get_token(), dev.model_dump())

@router.delete("/{email}")
async def delete_developer(email: str, org: str = Query(...)):
    validate(org, "org"); validate(email, "email")
    return await apigee_delete(dev_url(org, email), get_token(), email)
