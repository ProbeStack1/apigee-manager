import re
import os
import time
import json
import logging
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, APIRouter, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from google.auth import default
import time
import threading
from pydantic import EmailStr

load_dotenv()

# ─── LOGGING ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ─── APP ─────────────────────────────────────────────────────────────────────

app = FastAPI(title="Apigee X Manager API")

BASE = "https://apigee.googleapis.com/v1"

# ─── IN-MEMORY SERVICE ACCOUNT STORE ─────────────────────────────────────────

_sa_info = {"data": None}
_token_cache = {"token": None, "expires_at": 0}

# Load service account from env variable (Cloud Run) or local file path from .env
_sa_key_env = os.environ.get("APIGEE_SA_KEY")
_sa_key_path = os.environ.get("APIGEE_SA_KEY_PATH", "service-account.json")

if _sa_key_env:
    try:
        _sa_info["data"] = json.loads(_sa_key_env)
        logger.info("Auto-loaded service account from environment variable")
    except json.JSONDecodeError:
        logger.error("Invalid APIGEE_SA_KEY environment variable")
elif _sa_key_path and os.path.isfile(_sa_key_path):
    with open(_sa_key_path) as _f:
        _sa_info["data"] = json.load(_f)
    logger.info("Auto-loaded service account from: %s", _sa_key_path)

# ─── AUTH ────────────────────────────────────────────────────────────────────

_lock = threading.Lock()

def get_token() -> str:
    try:
        with _lock:
            # Use cached token
            if _token_cache["token"] and time.time() < _token_cache["expires_at"] - 60:
                return _token_cache["token"]
            try:
                # ✅ Cloud Run / GCP way
                creds, _ = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
                logger.info("Using default credentials (Cloud Run)")
            except Exception:
                # ✅ Local fallback
                logger.info("Using service account file (local)")
                creds = service_account.Credentials.from_service_account_file(
                    os.getenv("APIGEE_SA_KEY_PATH", "service-account.json"),
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
            creds.refresh(Request())
            _token_cache["token"] = creds.token
            _token_cache["expires_at"] = creds.expiry.timestamp()
            return creds.token
    except Exception as e:
        logger.error(f"Token generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate token")

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

# ─── ROOT ────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"status": "ok", "message": "Apigee X Manager API is running"}

# ─── AUTH UPLOAD ─────────────────────────────────────────────────────────────

@app.post("/auth/upload", tags=["Auth"])
async def upload_service_account(file: UploadFile = File(...)):
    try:
        content = await file.read()
        sa_data = json.loads(content)
        # Validate it looks like a service account file
        required_keys = ["type", "project_id", "private_key", "client_email"]
        for key in required_keys:
            if key not in sa_data:
                raise HTTPException(status_code=400, detail=f"Invalid service account file — missing '{key}'")
        if sa_data.get("type") != "service_account":
            raise HTTPException(status_code=400, detail="File is not a service account JSON")
        # Store in memory
        _sa_info["data"] = sa_data
        # Reset token cache so new credentials are used
        _token_cache["token"] = None
        _token_cache["expires_at"] = 0
        logger.info("Service account uploaded: %s", sanitize_log(sa_data.get("client_email", "")))
        return {
            "message": "Service account uploaded successfully",
            "project_id": sa_data.get("project_id"),
            "client_email": sa_data.get("client_email")
        }
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")

@app.get("/auth/status", tags=["Auth"])
async def auth_status():
    if _sa_info["data"]:
        return {
            "status": "uploaded",
            "project_id": _sa_info["data"].get("project_id"),
            "client_email": _sa_info["data"].get("client_email")
        }
    return {"status": "no service account uploaded"}

# ─── ROUTERS ─────────────────────────────────────────────────────────────────

ts_router    = APIRouter(prefix="/targetservers", tags=["Target Servers"])
dev_router   = APIRouter(prefix="/developers",    tags=["Developers"])
app_router   = APIRouter(prefix="/apps",          tags=["Apps"])
prod_router  = APIRouter(prefix="/products",      tags=["API Products"])
group_router = APIRouter(prefix="/appgroups",     tags=["App Groups"])

# ─── TARGET SERVERS ──────────────────────────────────────────────────────────

def ts_url(org: str, env: str, name: str = ""):
    base = f"{BASE}/organizations/{org}/environments/{env}/targetservers"
    return f"{base}/{name}" if name else base

@ts_router.get("/")
async def list_ts(org: str = Query(...), env: str = Query(...)):
    validate(org, "org"); validate(env, "env")
    return await apigee_request("GET", ts_url(org, env), get_token())

@ts_router.get("/{name}")
async def get_ts(name: str, org: str = Query(...), env: str = Query(...)):
    validate(org, "org"); validate(env, "env"); validate(name, "name")
    return await apigee_request("GET", ts_url(org, env, name), get_token())

@ts_router.post("/")
async def create_ts(ts: TargetServer, org: str = Query(...), env: str = Query(...)):
    validate(org, "org"); validate(env, "env")
    return await apigee_request("POST", ts_url(org, env), get_token(), ts.model_dump())

@ts_router.put("/{name}")
async def update_ts(name: str, ts: TargetServer, org: str = Query(...), env: str = Query(...)):
    validate(org, "org"); validate(env, "env"); validate(name, "name")
    return await apigee_request("PUT", ts_url(org, env, name), get_token(), ts.model_dump())

@ts_router.delete("/{name}")
async def delete_ts(name: str, org: str = Query(...), env: str = Query(...)):
    validate(org, "org"); validate(env, "env"); validate(name, "name")
    return await apigee_delete(ts_url(org, env, name), get_token(), name)

# ─── DEVELOPERS ──────────────────────────────────────────────────────────────

def dev_url(org: str, email: str = ""):
    base = f"{BASE}/organizations/{org}/developers"
    return f"{base}/{email}" if email else base

@dev_router.get("/")
async def list_developers(org: str = Query(...)):
    validate(org, "org")
    return await apigee_request("GET", dev_url(org), get_token())

@dev_router.get("/{email}")
async def get_developer(email: str, org: str = Query(...)):
    validate(org, "org"); validate(email, "email")
    return await apigee_request("GET", dev_url(org, email), get_token())

@dev_router.post("/")
async def create_developer(dev: Developer, org: str = Query(...)):
    validate(org, "org"); validate(dev.email, "email")
    return await apigee_request("POST", dev_url(org), get_token(), dev.model_dump())

@dev_router.put("/{email}")
async def update_developer(email: str, dev: Developer, org: str = Query(...)):
    validate(org, "org"); validate(email, "email")
    return await apigee_request("PUT", dev_url(org, email), get_token(), dev.model_dump())

@dev_router.delete("/{email}")
async def delete_developer(email: str, org: str = Query(...)):
    validate(org, "org"); validate(email, "email")
    return await apigee_delete(dev_url(org, email), get_token(), email)

# ─── APPS ─────────────────────────────────────────────────────────────────────

def app_url(org: str, developer_email: str, app_name: str = ""):
    base = f"{BASE}/organizations/{org}/developers/{developer_email}/apps"
    return f"{base}/{app_name}" if app_name else base

def org_app_url(org: str, app_id: str = ""):
    base = f"{BASE}/organizations/{org}/apps"
    return f"{base}/{app_id}" if app_id else base

@app_router.get("/all")
async def list_all_apps(org: str = Query(...)):
    validate(org, "org")
    return await apigee_request("GET", org_app_url(org), get_token())

@app_router.get("/")
async def list_apps(org: str = Query(...), developer_email: str = Query(...)):
    validate(org, "org"); validate(developer_email, "developer_email")
    return await apigee_request("GET", app_url(org, developer_email), get_token())

@app_router.get("/{app_name}")
async def get_app(app_name: str, org: str = Query(...), developer_email: str = Query(...)):
    validate(org, "org"); validate(developer_email, "developer_email"); validate(app_name, "app_name")
    return await apigee_request("GET", app_url(org, developer_email, app_name), get_token())

@app_router.post("/")
async def create_app(app_data: DeveloperApp, org: str = Query(...), developer_email: str = Query(...)):
    validate(org, "org"); validate(developer_email, "developer_email")
    return await apigee_request("POST", app_url(org, developer_email), get_token(), app_data.model_dump(exclude_none=True))

@app_router.put("/{app_name}")
async def update_app(app_name: str, app_data: DeveloperApp, org: str = Query(...), developer_email: str = Query(...)):
    validate(org, "org"); validate(developer_email, "developer_email"); validate(app_name, "app_name")
    return await apigee_request("PUT", app_url(org, developer_email, app_name), get_token(), app_data.model_dump(exclude_none=True))

@app_router.delete("/{app_name}")
async def delete_app(app_name: str, org: str = Query(...), developer_email: str = Query(...)):
    validate(org, "org"); validate(developer_email, "developer_email"); validate(app_name, "app_name")
    return await apigee_delete(app_url(org, developer_email, app_name), get_token(), app_name)

# ─── API PRODUCTS ─────────────────────────────────────────────────────────────

def prod_url(org: str, name: str = ""):
    base = f"{BASE}/organizations/{org}/apiproducts"
    return f"{base}/{name}" if name else base

@prod_router.get("/")
async def list_products(org: str = Query(...)):
    validate(org, "org")
    return await apigee_request("GET", prod_url(org), get_token())

@prod_router.get("/{name}")
async def get_product(name: str, org: str = Query(...)):
    validate(org, "org"); validate(name, "name")
    return await apigee_request("GET", prod_url(org, name), get_token())

@prod_router.post("/")
async def create_product(product: ApiProduct, org: str = Query(...)):
    validate(org, "org")
    return await apigee_request("POST", prod_url(org), get_token(), product.model_dump(exclude_none=True))

@prod_router.put("/{name}")
async def update_product(name: str, product: ApiProduct, org: str = Query(...)):
    validate(org, "org"); validate(name, "name")
    return await apigee_request("PUT", prod_url(org, name), get_token(), product.model_dump(exclude_none=True))

@prod_router.delete("/{name}")
async def delete_product(name: str, org: str = Query(...)):
    validate(org, "org"); validate(name, "name")
    return await apigee_delete(prod_url(org, name), get_token(), name)

# ─── APP GROUPS ───────────────────────────────────────────────────────────────

def group_url(org: str, name: str = ""):
    base = f"{BASE}/organizations/{org}/appgroups"
    return f"{base}/{name}" if name else base

@group_router.get("/")
async def list_appgroups(org: str = Query(...)):
    validate(org, "org")
    return await apigee_request("GET", group_url(org), get_token())

@group_router.get("/{name}")
async def get_appgroup(name: str, org: str = Query(...)):
    validate(org, "org"); validate(name, "name")
    return await apigee_request("GET", group_url(org, name), get_token())

@group_router.post("/")
async def create_appgroup(group: AppGroup, org: str = Query(...)):
    validate(org, "org")
    return await apigee_request("POST", group_url(org), get_token(), group.model_dump(exclude_none=True))

@group_router.put("/{name}")
async def update_appgroup(name: str, group: AppGroup, org: str = Query(...)):
    validate(org, "org"); validate(name, "name")
    return await apigee_request("PUT", group_url(org, name), get_token(), group.model_dump(exclude_none=True))

@group_router.delete("/{name}")
async def delete_appgroup(name: str, org: str = Query(...)):
    validate(org, "org"); validate(name, "name")
    return await apigee_delete(group_url(org, name), get_token(), name)

# ─── REGISTER ROUTERS ─────────────────────────────────────────────────────────

app.include_router(ts_router)
app.include_router(dev_router)
app.include_router(app_router)
app.include_router(prod_router)
app.include_router(group_router)
