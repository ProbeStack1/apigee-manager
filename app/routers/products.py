from fastapi import APIRouter, Query
from app.models.schemas import ApiProduct
from app.core.auth import get_token
from app.core.config import BASE_URL
from app.utils.http_client import apigee_request, apigee_delete
from app.utils.validators import validate

router = APIRouter(prefix="/products", tags=["API Products"])

def prod_url(org: str, name: str = ""):
    base = f"{BASE_URL}/organizations/{org}/apiproducts"
    return f"{base}/{name}" if name else base

@router.get("/")
async def list_products(org: str = Query(...)):
    validate(org, "org")
    return await apigee_request("GET", prod_url(org), get_token())

@router.get("/{name}")
async def get_product(name: str, org: str = Query(...)):
    validate(org, "org"); validate(name, "name")
    return await apigee_request("GET", prod_url(org, name), get_token())

@router.post("/")
async def create_product(product: ApiProduct, org: str = Query(...)):
    validate(org, "org")
    return await apigee_request("POST", prod_url(org), get_token(), product.model_dump(exclude_none=True))

@router.put("/{name}")
async def update_product(name: str, product: ApiProduct, org: str = Query(...)):
    validate(org, "org"); validate(name, "name")
    return await apigee_request("PUT", prod_url(org, name), get_token(), product.model_dump(exclude_none=True))

@router.delete("/{name}")
async def delete_product(name: str, org: str = Query(...)):
    validate(org, "org"); validate(name, "name")
    return await apigee_delete(prod_url(org, name), get_token(), name)
