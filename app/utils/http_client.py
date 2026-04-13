import re
import httpx
from fastapi import HTTPException
from app.core.logger import logger

def sanitize_log(value: str) -> str:
    return re.sub(r'[\r\n\t]', ' ', str(value))[:200]

def build_headers(token: str, with_content_type: bool = True):
    h = {"Authorization": f"Bearer {token}"}
    if with_content_type:
        h["Content-Type"] = "application/json"
    return h

async def apigee_request(method: str, url: str, token: str, payload: dict = None) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            logger.info("Apigee API: %s %s", method, sanitize_log(url))
            headers = build_headers(token, with_content_type=payload is not None)
            response = await client.request(
                method, url, headers=headers,
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
            logger.info("Apigee DELETE: %s", sanitize_log(url))
            response = await client.delete(url, headers=build_headers(token, False))
            logger.info("Response Status: %s", response.status_code)
            if response.status_code != 200:
                logger.error("Delete failed: %s", sanitize_log(response.text))
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return {"message": f"'{resource}' deleted successfully"}
        except httpx.RequestError as e:
            logger.error("Delete failed: %s", sanitize_log(str(e)))
            raise HTTPException(status_code=500, detail="Apigee delete request failed")
