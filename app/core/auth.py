import json
import time
import base64
import threading
import os
from google.oauth2 import service_account
from google.auth import default
from google.auth.transport.requests import Request
from app.core.config import SA_KEY_PATH
from app.core.logger import logger

_sa_info = {"data": None}
_token_cache = {"token": None, "expires_at": 0}
_lock = threading.Lock()

# K_SERVICE is automatically set by GCP on Cloud Run
IS_CLOUD_RUN = os.environ.get("K_SERVICE") is not None

# Load SA only for local — Cloud Run uses attached service account
if not IS_CLOUD_RUN:
    SA_KEY_B64 = os.environ.get("APIGEE_SA_KEY_B64")
    if SA_KEY_B64:
        try:
            decoded = base64.b64decode(SA_KEY_B64).decode('utf-8')
            _sa_info["data"] = json.loads(decoded)
            logger.info("Loaded service account from base64 env variable")
        except Exception as e:
            logger.error("Failed to decode APIGEE_SA_KEY_B64: %s", str(e))
    elif SA_KEY_PATH and os.path.isfile(SA_KEY_PATH):
        with open(SA_KEY_PATH) as f:
            _sa_info["data"] = json.load(f)
        logger.info("Loaded service account from: %s", SA_KEY_PATH)
else:
    logger.info("Running on Cloud Run — using attached service account")

def get_sa_info():
    return _sa_info

def get_token() -> str:
    with _lock:
        if _token_cache["token"] and time.time() < _token_cache["expires_at"] - 60:
            return _token_cache["token"]
        if IS_CLOUD_RUN:
            # Cloud Run — use attached service account automatically
            logger.info("Using GCP default credentials (Cloud Run)")
            creds, _ = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        elif _sa_info["data"]:
            # Local — use key.json
            logger.info("Using service account JSON (local)")
            creds = service_account.Credentials.from_service_account_info(
                _sa_info["data"],
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
        else:
            # Fallback
            logger.info("Fallback to GCP default credentials")
            creds, _ = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        creds.refresh(Request())
        _token_cache["token"] = creds.token
        _token_cache["expires_at"] = time.time() + 3600
        logger.info("Token refreshed successfully")
        return creds.token
