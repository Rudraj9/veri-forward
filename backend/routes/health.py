from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok", "models": "lazy; readiness is not guaranteed"}
