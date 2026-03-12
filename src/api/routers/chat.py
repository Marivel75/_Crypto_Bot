"""Chat router — LLM-powered crypto assistant."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db
from src.api.schemas import ApiResponse, ChatRequest, ChatResponse
from src.api.services import chat_service
from src.shared.models.orm import UserOrm

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ApiResponse[ChatResponse])
async def chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserOrm = Depends(get_current_user),
) -> ApiResponse[ChatResponse]:
    """Send a message to the crypto assistant."""
    result = await chat_service.chat(db, body.message, str(current_user.id))
    return ApiResponse(data=ChatResponse(reply=result["reply"] or "", disclaimer=result.get("disclaimer")))
