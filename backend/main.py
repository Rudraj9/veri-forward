from fastapi import FastAPI
from backend.routes.health import router as health_router
from backend.routes.verify import router as verify_router
from backend.limits import BodyLimitMiddleware

app = FastAPI(title="VeriForward", version="0.1.0")
app.add_middleware(BodyLimitMiddleware)
app.include_router(health_router)
app.include_router(verify_router)
