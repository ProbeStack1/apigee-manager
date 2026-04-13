import json
from fastapi import APIRouter, HTTPException, UploadFile, File
from app.core.auth import _sa_info, _token_cache
from app.utils.http_client import sanitize_log
from app.core.logger import logger

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/upload")
async def upload_service_account(file: UploadFile = File(...)):
    try:
        content = await file.read()
        sa_data = json.loads(content)
        for key in ["type", "project_id", "private_key", "client_email"]:
            if key not in sa_data:
                raise HTTPException(status_code=400, detail=f"Invalid service account — missing '{key}'")
        if sa_data.get("type") != "service_account":
            raise HTTPException(status_code=400, detail="File is not a service account JSON")
        _sa_info["data"] = sa_data
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

@router.get("/status")
async def auth_status():
    if _sa_info["data"]:
        return {
            "status": "uploaded",
            "project_id": _sa_info["data"].get("project_id"),
            "client_email": _sa_info["data"].get("client_email")
        }
    return {"status": "no service account uploaded"}
