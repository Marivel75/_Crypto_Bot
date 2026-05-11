"""Endpoints abonnements aux alertes email."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import nullslast
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.schemas.alerts import SubscribeRequest, SubscribeResponse
from src.models.alert_subscriber import AlertSubscriber
from src.models.news import NewsArticle
from src.notifications.notifier import notify_subscribe_confirmation, notify_unsubscribe_confirmation

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _latest_articles(db: Session, n: int = 5) -> list[dict]:
    rows = (
        db.query(NewsArticle)
        .order_by(nullslast(NewsArticle.published_at.desc()), NewsArticle.collected_at.desc())
        .limit(n)
        .all()
    )
    return [
        {
            "title": r.title,
            "url": r.url,
            "source": r.source,
            "published_at": r.published_at.isoformat() if r.published_at else None,
            "collected_at": r.collected_at.isoformat() if r.collected_at else None,
            "sentiment_label": r.sentiment_label,
        }
        for r in rows
    ]


@router.post("/subscribe", response_model=SubscribeResponse)
def subscribe(body: SubscribeRequest, db: Session = Depends(get_db)):
    existing = db.query(AlertSubscriber).filter_by(email=body.email).first()
    if existing:
        if existing.active:
            return SubscribeResponse(email=body.email, message="already_subscribed")
        existing.active = True
        db.commit()
        articles = _latest_articles(db)
        notify_subscribe_confirmation(body.email, articles)
        return SubscribeResponse(email=body.email, message="reactivated")
    db.add(AlertSubscriber(email=body.email))
    db.commit()
    articles = _latest_articles(db)
    notify_subscribe_confirmation(body.email, articles)
    return SubscribeResponse(email=body.email, message="subscribed")


@router.delete("/unsubscribe/{email}", response_model=SubscribeResponse)
def unsubscribe(email: str, db: Session = Depends(get_db)):
    sub = db.query(AlertSubscriber).filter_by(email=email).first()
    if not sub or not sub.active:
        raise HTTPException(status_code=404, detail="Email non abonné")
    sub.active = False
    db.commit()
    notify_unsubscribe_confirmation(email)
    return SubscribeResponse(email=email, message="unsubscribed")
