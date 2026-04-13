import re
from fastapi import HTTPException

SAFE_PATTERN = re.compile(r'^[a-zA-Z0-9._@\-]+$')

def validate(value: str, field: str) -> str:
    if not value or not SAFE_PATTERN.match(value):
        raise HTTPException(status_code=400, detail=f"Invalid characters in '{field}'")
    return value
