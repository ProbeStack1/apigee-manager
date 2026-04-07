import re
import time
import logging
import httpx
from fastapi import FastAPI, HTTPException, Query, APIRouter
from pydantic import BaseModel
from typing import List, Optional
from google.oauth2 import service_account
from google.auth.transport.requests import Request

# ─── LOGGING ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ─── APP ─────────────────────────────────────────────────────────────────────

app = FastAPI(title="Apigee X Manager API")

ORG = "financialdataexchange"
SERVICE_ACCOUNT_FILE = "service-account.json"
BASE = "https://apigee.googleapis.com/v1"

# ─── AUTH ────────────────────────────────────────────────────────────────────

_token_cache = {"token": None, "expires_at": 0}

def get_token() -> str:
    if time.time() < _token_cache["expires_at"] - 60:
        return _token_cache["token"]
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    creds.refresh(Request())
    _token_cache["token"] = creds.token
    _token_cache["expires_at"] = time.time() + 3600
    logger.info("Google OAuth2 token refreshed")
    return creds.token

def headers(token: str):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

def auth_only(token: str):
    return {"Authorization": f"Bearer {token}"}

# ─── INPUT VALIDATION ────────────────────────────────────────────────────────

SAFE_PATTERN = re.compile(r'^[a-zA-Z0-9._@\-]+$')

def validate(value: str, field: str) -> str:
    if not value or not SAFE_PATTERN.match(value):
        raise HTTPException(status_code=400, detail=f"Invalid characters in '{field}'")
    return value

# ─── ASYNC HTTP ──────────────────────────────────────────────────────────────

def sanitize_log(value: str) -> str:
    return re.sub(r'[\r\n\t]', ' ', str(value))[:200]

async def apigee_request(method: str, url: str, token: str, payload: dict = None) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            logger.info("Apigee API: %s %s", method, sanitize_log(url))
            h = headers(token) if payload is not None else auth_only(token)
            response = await client.request(
                method, url, headers=h,
                json=payload if payload is not None else None
            )
            logger.info("Response Status: %s", response.status_code)
            if response.status_code not in (200, 201):
                logger.error("Error: %s", sanitize_log(response.text))
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json() if response.text else {}
        except httpx.RequestError as e:
            logger.error("Request failed: %s", sanitize_log(str(e)))
            raise HTTPException(status_code=500, detail="Apigee request failed")

async def apigee_delete(url: str, token: str, resource: str) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            logger.info("Apigee API: DELETE %s", sanitize_log(url))
            response = await client.delete(url, headers=auth_only(token))
            logger.info("Response Status: %s", response.status_code)
            if response.status_code != 200:
                logger.error("Delete failed: %s", sanitize_log(response.text))
                raise HTTPException(status_code=response.status_code, detail=response.text)
            logger.info("Deleted: %s", sanitize_log(resource))
            return {"message": f"'{resource}' deleted successfully"}
        except httpx.RequestError as e:
            logger.error("Delete request failed: %s", sanitize_log(str(e)))
            raise HTTPException(status_code=500, detail="Apigee delete request failed")

# ─── MODELS ──────────────────────────────────────────────────────────────────

class TargetServer(BaseModel):
    name: str
    host: str
    port: int
    isEnabled: bool = True

class Developer(BaseModel):
    email: str
    firstName: str
    lastName: str
    userName: str
    attributes: Optional[List[dict]] = []

class DeveloperApp(BaseModel):
    name: str
    apiProducts: Optional[List[str]] = []
    keyExpiresIn: Optional[int] = -1
    attributes: Optional[List[dict]] = []
    callbackUrl: Optional[str] = None

class ApiProduct(BaseModel):
    name: str
    displayName: str
    description: Optional[str] = None
    approvalType: str = "auto"
    environments: Optional[List[str]] = []
    proxies: Optional[List[str]] = []
    quota: Optional[str] = None
    quotaInterval: Optional[str] = None
    quotaTimeUnit: Optional[str] = None
    attributes: Optional[List[dict]] = []

class AppGroup(BaseModel):
    name: str
    displayName: Optional[str] = None
    attributes: Optional[List[dict]] = []

# ─── ROUTERS ─────────────────────────────────────────────────────────────────

ts_router    = APIRouter(prefix="/targetservers", tags=["Target Servers"])
dev_router   = APIRouter(prefix="/developers",    tags=["Developers"])
app_router   = APIRouter(prefix="/apps",          tags=["Apps"])
prod_router  = APIRouter(prefix="/products",      tags=["API Products"])
group_router = APIRouter(prefix="/appgroups",     tags=["App Groups"])

# ─── TARGET SERVERS ──────────────────────────────────────────────────────────

def ts_url(env: str, name: str = ""):
    base = f"{BASE}/organizations/{ORG}/environments/{env}/targetservers"
    return f"{base}/{name}" if name else base

@ts_router.get("/")
async def list_ts(env: str = Query(...)):
    validate(env, "env")
    return await apigee_request("GET", ts_url(env), get_token(), payload={})

@ts_router.get("/{name}")
async def get_ts(name: str, env: str = Query(...)):
    validate(env, "env")
    validate(name, "name")
    return await apigee_request("GET", ts_url(env, name), get_token(), payload={})

@ts_router.post("/")
async def create_ts(ts: TargetServer, env: str = Query(...)):
    validate(env, "env")
    return await apigee_request("POST", ts_url(env), get_token(), ts.model_dump())

@ts_router.put("/{name}")
async def update_ts(name: str, ts: TargetServer, env: str = Query(...)):
    validate(env, "env")
    validate(name, "name")
    return await apigee_request("PUT", ts_url(env, name), get_token(), ts.model_dump())

@ts_router.delete("/{name}")
async def delete_ts(name: str, env: str = Query(...)):
    validate(env, "env")
    validate(name, "name")
    return await apigee_delete(ts_url(env, name), get_token(), name)

# ─── DEVELOPERS ──────────────────────────────────────────────────────────────

def dev_url(email: str = ""):
    base = f"{BASE}/organizations/{ORG}/developers"
    return f"{base}/{email}" if email else base

@dev_router.get("/")
async def list_developers():
    return await apigee_request("GET", dev_url(), get_token(), payload={})

@dev_router.get("/{email}")
async def get_developer(email: str):
    validate(email, "email")
    return await apigee_request("GET", dev_url(email), get_token(), payload={})

@dev_router.post("/")
async def create_developer(dev: Developer):
    validate(dev.email, "email")
    return await apigee_request("POST", dev_url(), get_token(), dev.model_dump())

@dev_router.put("/{email}")
async def update_developer(email: str, dev: Developer):
    validate(email, "email")
    return await apigee_request("PUT", dev_url(email), get_token(), dev.model_dump())

@dev_router.delete("/{email}")
async def delete_developer(email: str):
    validate(email, "email")
    return await apigee_delete(dev_url(email), get_token(), email)

# ─── APPS ─────────────────────────────────────────────────────────────────────

def app_url(developer_email: str, app_name: str = ""):
    base = f"{BASE}/organizations/{ORG}/developers/{developer_email}/apps"
    return f"{base}/{app_name}" if app_name else base

def org_app_url(app_id: str = ""):
    base = f"{BASE}/organizations/{ORG}/apps"
    return f"{base}/{app_id}" if app_id else base

@app_router.get("/all")
async def list_all_apps():
    return await apigee_request("GET", org_app_url(), get_token(), payload={})

@app_router.get("/")
async def list_apps(developer_email: str = Query(...)):
    validate(developer_email, "developer_email")
    return await apigee_request("GET", app_url(developer_email), get_token(), payload={})

@app_router.get("/{app_name}")
async def get_app(app_name: str, developer_email: str = Query(...)):
    validate(developer_email, "developer_email")
    validate(app_name, "app_name")
    return await apigee_request("GET", app_url(developer_email, app_name), get_token(), payload={})

@app_router.post("/")
async def create_app(app_data: DeveloperApp, developer_email: str = Query(...)):
    validate(developer_email, "developer_email")
    return await apigee_request("POST", app_url(developer_email), get_token(), app_data.model_dump(exclude_none=True))

@app_router.put("/{app_name}")
async def update_app(app_name: str, app_data: DeveloperApp, developer_email: str = Query(...)):
    validate(developer_email, "developer_email")
    validate(app_name, "app_name")
    return await apigee_request("PUT", app_url(developer_email, app_name), get_token(), app_data.model_dump(exclude_none=True))

@app_router.delete("/{app_name}")
async def delete_app(app_name: str, developer_email: str = Query(...)):
    validate(developer_email, "developer_email")
    validate(app_name, "app_name")
    return await apigee_delete(app_url(developer_email, app_name), get_token(), app_name)

# ─── API PRODUCTS ─────────────────────────────────────────────────────────────

def prod_url(name: str = ""):
    base = f"{BASE}/organizations/{ORG}/apiproducts"
    return f"{base}/{name}" if name else base

@prod_router.get("/")
async def list_products():
    return await apigee_request("GET", prod_url(), get_token(), payload={})

@prod_router.get("/{name}")
async def get_product(name: str):
    validate(name, "name")
    return await apigee_request("GET", prod_url(name), get_token(), payload={})

@prod_router.post("/")
async def create_product(product: ApiProduct):
    return await apigee_request("POST", prod_url(), get_token(), product.model_dump(exclude_none=True))

@prod_router.put("/{name}")
async def update_product(name: str, product: ApiProduct):
    validate(name, "name")
    return await apigee_request("PUT", prod_url(name), get_token(), product.model_dump(exclude_none=True))

@prod_router.delete("/{name}")
async def delete_product(name: str):
    validate(name, "name")
    return await apigee_delete(prod_url(name), get_token(), name)

# ─── APP GROUPS ───────────────────────────────────────────────────────────────

def group_url(name: str = ""):
    base = f"{BASE}/organizations/{ORG}/appgroups"
    return f"{base}/{name}" if name else base

@group_router.get("/")
async def list_appgroups():
    return await apigee_request("GET", group_url(), get_token(), payload={})

@group_router.get("/{name}")
async def get_appgroup(name: str):
    validate(name, "name")
    return await apigee_request("GET", group_url(name), get_token(), payload={})

@group_router.post("/")
async def create_appgroup(group: AppGroup):
    return await apigee_request("POST", group_url(), get_token(), group.model_dump(exclude_none=True))

@group_router.put("/{name}")
async def update_appgroup(name: str, group: AppGroup):
    validate(name, "name")
    return await apigee_request("PUT", group_url(name), get_token(), group.model_dump(exclude_none=True))

@group_router.delete("/{name}")
async def delete_appgroup(name: str):
    validate(name, "name")
    return await apigee_delete(group_url(name), get_token(), name)

# ─── REGISTER ROUTERS ─────────────────────────────────────────────────────────

app.include_router(ts_router)
app.include_router(dev_router)
app.include_router(app_router)
app.include_router(prod_router)
app.include_router(group_router)
