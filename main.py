from fastapi import FastAPI
from app.routers import targetservers, developers, apps, products, appgroups, auth, kvm
from app.core.logger import logger

app = FastAPI(
    title="Apigee X Manager API",
    description="REST API to manage Apigee X resources",
    version="1.0.0"
)

@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "message": "Apigee X Manager API is running"}

app.include_router(auth.router)
app.include_router(targetservers.router)
app.include_router(developers.router)
app.include_router(apps.router)
app.include_router(products.router)
app.include_router(appgroups.router)
app.include_router(kvm.router)

logger.info("Apigee X Manager API started")
