from fastapi import APIRouter, Query
from app.models.schemas import KVM, KVMEntry
from app.core.auth import get_token
from app.core.config import BASE_URL
from app.utils.http_client import apigee_request, apigee_delete
from app.utils.validators import validate

router = APIRouter(tags=["KVM"])

# ─── URL BUILDERS ─────────────────────────────────────────────────────────────

def org_kvm_url(org: str, kvm_name: str = ""):
    base = f"{BASE_URL}/organizations/{org}/keyvaluemaps"
    return f"{base}/{kvm_name}" if kvm_name else base

def env_kvm_url(org: str, env: str, kvm_name: str = ""):
    base = f"{BASE_URL}/organizations/{org}/environments/{env}/keyvaluemaps"
    return f"{base}/{kvm_name}" if kvm_name else base

def org_entry_url(org: str, kvm_name: str, entry_name: str = ""):
    base = f"{BASE_URL}/organizations/{org}/keyvaluemaps/{kvm_name}/entries"
    return f"{base}/{entry_name}" if entry_name else base

def env_entry_url(org: str, env: str, kvm_name: str, entry_name: str = ""):
    base = f"{BASE_URL}/organizations/{org}/environments/{env}/keyvaluemaps/{kvm_name}/entries"
    return f"{base}/{entry_name}" if entry_name else base

# ─── ORG LEVEL KVM ────────────────────────────────────────────────────────────

@router.get("/kvm/org", summary="List org-level KVMs")
async def list_org_kvms(org: str = Query(...)):
    validate(org, "org")
    return await apigee_request("GET", org_kvm_url(org), get_token())

@router.get("/kvm/org/{kvm_name}", summary="Get org-level KVM")
async def get_org_kvm(kvm_name: str, org: str = Query(...)):
    validate(org, "org"); validate(kvm_name, "kvm_name")
    return await apigee_request("GET", org_kvm_url(org, kvm_name), get_token())

@router.post("/kvm/org", summary="Create org-level KVM")
async def create_org_kvm(kvm: KVM, org: str = Query(...)):
    validate(org, "org")
    return await apigee_request("POST", org_kvm_url(org), get_token(), kvm.model_dump())

@router.delete("/kvm/org/{kvm_name}", summary="Delete org-level KVM")
async def delete_org_kvm(kvm_name: str, org: str = Query(...)):
    validate(org, "org"); validate(kvm_name, "kvm_name")
    return await apigee_delete(org_kvm_url(org, kvm_name), get_token(), kvm_name)

# ─── ENV LEVEL KVM ────────────────────────────────────────────────────────────

@router.get("/kvm/env", summary="List env-level KVMs")
async def list_env_kvms(org: str = Query(...), env: str = Query(...)):
    validate(org, "org"); validate(env, "env")
    return await apigee_request("GET", env_kvm_url(org, env), get_token())

@router.get("/kvm/env/{kvm_name}", summary="Get env-level KVM")
async def get_env_kvm(kvm_name: str, org: str = Query(...), env: str = Query(...)):
    validate(org, "org"); validate(env, "env"); validate(kvm_name, "kvm_name")
    return await apigee_request("GET", env_kvm_url(org, env, kvm_name), get_token())

@router.post("/kvm/env", summary="Create env-level KVM")
async def create_env_kvm(kvm: KVM, org: str = Query(...), env: str = Query(...)):
    validate(org, "org"); validate(env, "env")
    return await apigee_request("POST", env_kvm_url(org, env), get_token(), kvm.model_dump())

@router.delete("/kvm/env/{kvm_name}", summary="Delete env-level KVM")
async def delete_env_kvm(kvm_name: str, org: str = Query(...), env: str = Query(...)):
    validate(org, "org"); validate(env, "env"); validate(kvm_name, "kvm_name")
    return await apigee_delete(env_kvm_url(org, env, kvm_name), get_token(), kvm_name)

# ─── ORG KVM ENTRIES ──────────────────────────────────────────────────────────

@router.get("/kvm/org/{kvm_name}/entries", summary="List org KVM entries")
async def list_org_kvm_entries(kvm_name: str, org: str = Query(...)):
    validate(org, "org"); validate(kvm_name, "kvm_name")
    return await apigee_request("GET", org_entry_url(org, kvm_name), get_token())

@router.get("/kvm/org/{kvm_name}/entries/{entry_name}", summary="Get org KVM entry")
async def get_org_kvm_entry(kvm_name: str, entry_name: str, org: str = Query(...)):
    validate(org, "org"); validate(kvm_name, "kvm_name"); validate(entry_name, "entry_name")
    return await apigee_request("GET", org_entry_url(org, kvm_name, entry_name), get_token())

@router.post("/kvm/org/{kvm_name}/entries", summary="Create org KVM entry")
async def create_org_kvm_entry(kvm_name: str, entry: KVMEntry, org: str = Query(...)):
    validate(org, "org"); validate(kvm_name, "kvm_name")
    return await apigee_request("POST", org_entry_url(org, kvm_name), get_token(), entry.model_dump())

@router.put("/kvm/org/{kvm_name}/entries/{entry_name}", summary="Update org KVM entry")
async def update_org_kvm_entry(kvm_name: str, entry_name: str, entry: KVMEntry, org: str = Query(...)):
    validate(org, "org"); validate(kvm_name, "kvm_name"); validate(entry_name, "entry_name")
    return await apigee_request("PUT", org_entry_url(org, kvm_name, entry_name), get_token(), entry.model_dump())

@router.delete("/kvm/org/{kvm_name}/entries/{entry_name}", summary="Delete org KVM entry")
async def delete_org_kvm_entry(kvm_name: str, entry_name: str, org: str = Query(...)):
    validate(org, "org"); validate(kvm_name, "kvm_name"); validate(entry_name, "entry_name")
    return await apigee_delete(org_entry_url(org, kvm_name, entry_name), get_token(), entry_name)

# ─── ENV KVM ENTRIES ──────────────────────────────────────────────────────────

@router.get("/kvm/env/{kvm_name}/entries", summary="List env KVM entries")
async def list_env_kvm_entries(kvm_name: str, org: str = Query(...), env: str = Query(...)):
    validate(org, "org"); validate(env, "env"); validate(kvm_name, "kvm_name")
    return await apigee_request("GET", env_entry_url(org, env, kvm_name), get_token())

@router.get("/kvm/env/{kvm_name}/entries/{entry_name}", summary="Get env KVM entry")
async def get_env_kvm_entry(kvm_name: str, entry_name: str, org: str = Query(...), env: str = Query(...)):
    validate(org, "org"); validate(env, "env"); validate(kvm_name, "kvm_name"); validate(entry_name, "entry_name")
    return await apigee_request("GET", env_entry_url(org, env, kvm_name, entry_name), get_token())

@router.post("/kvm/env/{kvm_name}/entries", summary="Create env KVM entry")
async def create_env_kvm_entry(kvm_name: str, entry: KVMEntry, org: str = Query(...), env: str = Query(...)):
    validate(org, "org"); validate(env, "env"); validate(kvm_name, "kvm_name")
    return await apigee_request("POST", env_entry_url(org, env, kvm_name), get_token(), entry.model_dump())

@router.put("/kvm/env/{kvm_name}/entries/{entry_name}", summary="Update env KVM entry")
async def update_env_kvm_entry(kvm_name: str, entry_name: str, entry: KVMEntry, org: str = Query(...), env: str = Query(...)):
    validate(org, "org"); validate(env, "env"); validate(kvm_name, "kvm_name"); validate(entry_name, "entry_name")
    return await apigee_request("PUT", env_entry_url(org, env, kvm_name, entry_name), get_token(), entry.model_dump())

@router.delete("/kvm/env/{kvm_name}/entries/{entry_name}", summary="Delete env KVM entry")
async def delete_env_kvm_entry(kvm_name: str, entry_name: str, org: str = Query(...), env: str = Query(...)):
    validate(org, "org"); validate(env, "env"); validate(kvm_name, "kvm_name"); validate(entry_name, "entry_name")
    return await apigee_delete(env_entry_url(org, env, kvm_name, entry_name), get_token(), entry_name)
