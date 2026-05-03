"""Endpoints abonnements aux alertes email."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.schemas.alerts import SubscribeRequest, SubscribeResponse
from src.models.alert_subscriber import AlertSubscriber

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("/subscribe", response_model=SubscribeResponse)
def subscribe(body: SubscribeRequest, db: Session = Depends(get_db)):
    existing = db.query(AlertSubscriber).filter_by(email=body.email).first()
    if existing:
        if existing.active:
            return SubscribeResponse(email=body.email, message="already_subscribed")
        existing.active = True
        db.commit()
        return SubscribeResponse(email=body.email, message="reactivated")
    db.add(AlertSubscriber(email=body.email))
    db.commit()
    return SubscribeResponse(email=body.email, message="subscribed")


@router.delete("/unsubscribe/{email}", response_model=SubscribeResponse)
def unsubscribe(email: str, db: Session = Depends(get_db)):
    sub = db.query(AlertSubscriber).filter_by(email=email).first()
    if not sub or not sub.active:
        raise HTTPException(status_code=404, detail="Email non abonné")
    sub.active = False
    db.commit()
    return SubscribeResponse(email=email, message="unsubscribed")
