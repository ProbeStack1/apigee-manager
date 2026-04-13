from pydantic import BaseModel
from typing import List, Optional

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

# ─── KVM MODELS ──────────────────────────────────────────────────────────────

class KVM(BaseModel):
    name: str
    encrypted: bool = True

class KVMEntry(BaseModel):
    name: str
    value: str
