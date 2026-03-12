"""Portfolio router — CRUD for user positions."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db
from src.api.schemas import (
    ApiResponse,
    PortfolioCreateRequest,
    PortfolioEntryResponse,
    PortfolioUpdateRequest,
)
from src.api.services import user_data_service
from src.shared.models.orm import UserOrm

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("", response_model=ApiResponse[list[PortfolioEntryResponse]])
async def get_portfolio(
    db: AsyncSession = Depends(get_db),
    current_user: UserOrm = Depends(get_current_user),
) -> ApiResponse[list[PortfolioEntryResponse]]:
    """Return the user's portfolio."""
    entries = await user_data_service.get_portfolio(db, str(current_user.id))
    return ApiResponse(data=[PortfolioEntryResponse.model_validate(e) for e in entries])


@router.post(
    "",
    response_model=ApiResponse[PortfolioEntryResponse],
    status_code=status.HTTP_201_CREATED,
)
async def add_entry(
    body: PortfolioCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserOrm = Depends(get_current_user),
) -> ApiResponse[PortfolioEntryResponse]:
    """Add a portfolio position."""
    entry = await user_data_service.add_portfolio_entry(
        db, str(current_user.id), body.symbol, body.quantity, body.entry_price, body.notes
    )
    return ApiResponse(data=PortfolioEntryResponse.model_validate(entry))


@router.put("/{entry_id}", response_model=ApiResponse[PortfolioEntryResponse])
async def update_entry(
    entry_id: UUID,
    body: PortfolioUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserOrm = Depends(get_current_user),
) -> ApiResponse[PortfolioEntryResponse]:
    """Update a portfolio position."""
    entry = await user_data_service.update_portfolio_entry(
        db, str(current_user.id), str(entry_id), body.quantity, body.entry_price, body.notes
    )
    return ApiResponse(data=PortfolioEntryResponse.model_validate(entry))


@router.delete("/{entry_id}", response_model=ApiResponse[None])
async def delete_entry(
    entry_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserOrm = Depends(get_current_user),
) -> ApiResponse[None]:
    """Delete a portfolio position."""
    await user_data_service.delete_portfolio_entry(db, str(current_user.id), str(entry_id))
    return ApiResponse(data=None)
