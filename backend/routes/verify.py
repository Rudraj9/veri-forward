from fastapi import APIRouter, HTTPException, Request
from starlette.concurrency import run_in_threadpool
from core.schemas import VerifyRequest, VerifyResponse, PrepareResponse
from core.pipeline import verify
from core.input_handler import prepare_input
from pydantic import BaseModel, Field
from typing import Literal

router = APIRouter()


class PrepareRequest(BaseModel):
    input_type: Literal["text", "url"]
    content: str = Field(min_length=1, max_length=20000)


@router.post("/prepare", response_model=PrepareResponse)
def prepare(body: PrepareRequest):
    try:
        return prepare_input(body.input_type, body.content)
    except (ValueError, OSError) as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/prepare/image", response_model=PrepareResponse)
async def prepare_image(request: Request):
    """Raw image body, not multipart, so upload size is bounded before parsing."""
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > 5_000_000:
            raise HTTPException(413, "Screenshot exceeds 5 MB")
    try:
        return await run_in_threadpool(prepare_input, "image", bytes(data))
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/verify", response_model=VerifyResponse)
def verify_claim(body: VerifyRequest):
    try:
        return verify(body)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
