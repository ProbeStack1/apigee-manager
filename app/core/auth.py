import json
import time
import base64
import threading
from fastapi import HTTPException
from google.oauth2 import service_account
from google.auth import default
from google.auth.transport.requests import Request
from app.core.config import SA_KEY_ENV, SA_KEY_PATH
from app.core.logger import logger
import os

_sa_info = {"data": None}
_token_cache = {"token": None, "expires_at": 0}
_lock = threading.Lock()

# Auto-load service account on startup
SA_KEY_B64 = os.environ.get("APIGEE_SA_KEY_B64")

if SA_KEY_B64:
    try:
        decoded = base64.b64decode(SA_KEY_B64).decode('utf-8')
        _sa_info["data"] = json.loads(decoded)
        logger.info("Loaded service account from base64 env variable")
    except Exception as e:
        logger.error("Failed to decode APIGEE_SA_KEY_B64: %s", str(e))
elif SA_KEY_ENV:
    try:
        _sa_info["data"] = json.loads(SA_KEY_ENV)
        logger.info("Loaded service account from environment variable")
    except json.JSONDecodeError:
        logger.error("Invalid APIGEE_SA_KEY environment variable")
elif SA_KEY_PATH and os.path.isfile(SA_KEY_PATH):
    with open(SA_KEY_PATH) as f:
        _sa_info["data"] = json.load(f)
    logger.info("Loaded service account from: %s", SA_KEY_PATH)

def get_sa_info():
    return _sa_info

def get_token() -> str:
    with _lock:
        if _token_cache["token"] and time.time() < _token_cache["expires_at"] - 60:
            return _token_cache["token"]
        if _sa_info["data"]:
            logger.info("Using service account JSON")
            creds = service_account.Credentials.from_service_account_info(
                _sa_info["data"],
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
        else:
            logger.info("Using GCP default credentials (Cloud Run)")
            creds, _ = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        creds.refresh(Request())
        _token_cache["token"] = creds.token
        _token_cache["expires_at"] = time.time() + 3600
        logger.info("Token refreshed successfully")
        return creds.token
