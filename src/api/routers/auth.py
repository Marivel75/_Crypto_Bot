"""Auth router — register, login, me."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db
from src.api.schemas import ApiResponse, LoginRequest, LoginResponse, RegisterRequest, UserResponse
from src.api.services import auth_service
from src.shared.models.orm import UserOrm

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=ApiResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[UserResponse]:
    """Create a new user account."""
    user = await auth_service.register(db, body.username, body.email, body.password, body.persona_type)
    logger.info("New user registered: %s", body.username)
    return ApiResponse(data=UserResponse.model_validate(user))


@router.post("/login", response_model=ApiResponse[LoginResponse])
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[LoginResponse]:
    """Authenticate with email and password and return a JWT token."""
    user = await auth_service.authenticate(db, body.email, body.password)
    token = auth_service.create_access_token(str(user.id), username=str(user.username))
    logger.info("User authenticated: %s", user.username)
    return ApiResponse(data=LoginResponse(access_token=token))


@router.get("/me", response_model=ApiResponse[UserResponse])
async def me(
    current_user: UserOrm = Depends(get_current_user),
) -> ApiResponse[UserResponse]:
    """Return current authenticated user."""
    return ApiResponse(data=UserResponse.model_validate(current_user))
