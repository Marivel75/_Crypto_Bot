"""Database seed script — populate all 9 tables with realistic demo data.

Usage:
    python -m scripts.seed_db
    docker-compose exec api python -m scripts.seed_db

Safe to re-run (idempotent via ON CONFLICT / SELECT-before-insert).

Demo credentials: all seed users use the passphrase ``Demo1234!``
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import bcrypt
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.database import async_session_factory
from src.shared.db_models import (
    PortfolioOrm,
    SignalOutcomeOrm,
    TextMiningResultOrm,
    TradingSignalOrm,
    UserOrm,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Seed passphrase read from env, falling back to a well-known demo value.
_SEED_PASSPHRASE = os.environ.get("SEED_USER_PASSPHRASE", "Demo1234!")  # noqa: S105


def _hash_seed_passphrase() -> str:
    """Hash the seed passphrase using bcrypt (same pattern as auth_service)."""
    return bcrypt.hashpw(_SEED_PASSPHRASE.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


SEED_USERS: tuple[dict[str, str], ...] = (
    {"username": "demo_trader", "email": "trader@demo.local", "persona_type": "trader"},
    {"username": "demo_journalist", "email": "journalist@demo.local", "persona_type": "journalist"},
    {"username": "demo_investor", "email": "investor@demo.local", "persona_type": "investor"},
    {"username": "demo_admin", "email": "admin@demo.local", "persona_type": "trader"},
)

BASE_PRICES: dict[str, float] = {
    "BTCUSDT": 67_500.0,
    "ETHUSDT": 3_450.0,
    "SOLUSDT": 145.0,
    "BNBUSDT": 580.0,
    "XRPUSDT": 0.52,
}

SEED_SYMBOLS = tuple(BASE_PRICES.keys())
SEED_TIMEFRAME = "4h"
SEED_DAYS = 30
CANDLES_PER_DAY = 6  # 24h / 4h

SEED_SIGNALS: tuple[dict[str, object], ...] = (
    {"symbol": "BTCUSDT", "signal_type": "BUY", "confidence": 0.82},
    {"symbol": "BTCUSDT", "signal_type": "SELL", "confidence": 0.71},
    {"symbol": "BTCUSDT", "signal_type": "BUY", "confidence": 0.65},
    {"symbol": "BTCUSDT", "signal_type": "HOLD", "confidence": 0.60},
    {"symbol": "BTCUSDT", "signal_type": "BUY", "confidence": 0.78},
    {"symbol": "ETHUSDT", "signal_type": "BUY", "confidence": 0.75},
    {"symbol": "ETHUSDT", "signal_type": "SELL", "confidence": 0.68},
    {"symbol": "ETHUSDT", "signal_type": "BUY", "confidence": 0.91},
    {"symbol": "ETHUSDT", "signal_type": "HOLD", "confidence": 0.63},
    {"symbol": "ETHUSDT", "signal_type": "SELL", "confidence": 0.72},
    {"symbol": "SOLUSDT", "signal_type": "BUY", "confidence": 0.88},
    {"symbol": "SOLUSDT", "signal_type": "SELL", "confidence": 0.66},
    {"symbol": "SOLUSDT", "signal_type": "BUY", "confidence": 0.74},
    {"symbol": "SOLUSDT", "signal_type": "HOLD", "confidence": 0.61},
    {"symbol": "SOLUSDT", "signal_type": "BUY", "confidence": 0.80},
    {"symbol": "BNBUSDT", "signal_type": "BUY", "confidence": 0.77},
    {"symbol": "BNBUSDT", "signal_type": "SELL", "confidence": 0.69},
    {"symbol": "BNBUSDT", "signal_type": "BUY", "confidence": 0.85},
    {"symbol": "BNBUSDT", "signal_type": "HOLD", "confidence": 0.62},
    {"symbol": "BNBUSDT", "signal_type": "SELL", "confidence": 0.73},
    {"symbol": "XRPUSDT", "signal_type": "BUY", "confidence": 0.70},
    {"symbol": "XRPUSDT", "signal_type": "SELL", "confidence": 0.64},
    {"symbol": "XRPUSDT", "signal_type": "BUY", "confidence": 0.83},
    {"symbol": "XRPUSDT", "signal_type": "HOLD", "confidence": 0.67},
    {"symbol": "XRPUSDT", "signal_type": "BUY", "confidence": 0.76},
)

SEED_NEWS: tuple[dict[str, object], ...] = (
    {
        "title": "Bitcoin Breaks $70K Resistance as Institutional Demand Surges",
        "source": "Decrypt",
        "url": "https://example.com/seed-news/btc-70k",
        "sentiment": 0.82,
        "keywords": ["bitcoin", "institutional", "resistance"],
    },
    {
        "title": "Ethereum Layer 2 Ecosystem Hits Record TVL",
        "source": "CoinTelegraph",
        "url": "https://example.com/seed-news/eth-l2-tvl",
        "sentiment": 0.75,
        "keywords": ["ethereum", "layer2", "tvl"],
    },
    {
        "title": "SEC Delays Bitcoin ETF Decision Yet Again",
        "source": "Decrypt",
        "url": "https://example.com/seed-news/sec-etf-delay",
        "sentiment": -0.45,
        "keywords": ["bitcoin", "sec", "etf", "regulation"],
    },
    {
        "title": "Solana DeFi Volume Exceeds $5B in 24 Hours",
        "source": "CoinTelegraph",
        "url": "https://example.com/seed-news/sol-defi-volume",
        "sentiment": 0.68,
        "keywords": ["solana", "defi", "volume"],
    },
    {
        "title": "BNB Chain Launches opBNB Mainnet for Scalability",
        "source": "Decrypt",
        "url": "https://example.com/seed-news/bnb-opbnb",
        "sentiment": 0.55,
        "keywords": ["bnb", "opbnb", "scalability"],
    },
    {
        "title": "XRP Ledger Adds Native AMM Support",
        "source": "CoinTelegraph",
        "url": "https://example.com/seed-news/xrp-amm",
        "sentiment": 0.62,
        "keywords": ["xrp", "amm", "ledger"],
    },
    {
        "title": "Crypto Market Faces Liquidation Wave: $800M Wiped",
        "source": "Decrypt",
        "url": "https://example.com/seed-news/liquidation-wave",
        "sentiment": -0.78,
        "keywords": ["liquidation", "market", "crash"],
    },
    {
        "title": "Fed Rate Decision Sends Mixed Signals to Crypto Markets",
        "source": "CoinTelegraph",
        "url": "https://example.com/seed-news/fed-rate-crypto",
        "sentiment": -0.15,
        "keywords": ["fed", "rates", "macro"],
    },
    {
        "title": "Bitcoin Mining Difficulty Reaches All-Time High",
        "source": "Decrypt",
        "url": "https://example.com/seed-news/btc-mining-difficulty",
        "sentiment": 0.30,
        "keywords": ["bitcoin", "mining", "difficulty"],
    },
    {
        "title": "Ethereum Foundation Announces Major Protocol Upgrade Timeline",
        "source": "CoinTelegraph",
        "url": "https://example.com/seed-news/eth-upgrade",
        "sentiment": 0.70,
        "keywords": ["ethereum", "upgrade", "protocol"],
    },
    {
        "title": "Solana Mobile Chapter 2 Pre-Orders Sell Out in 30 Minutes",
        "source": "Decrypt",
        "url": "https://example.com/seed-news/sol-mobile-ch2",
        "sentiment": 0.85,
        "keywords": ["solana", "mobile", "hardware"],
    },
    {
        "title": "ESMA Publishes Final MiCA Guidelines for Crypto Assets",
        "source": "CoinTelegraph",
        "url": "https://example.com/seed-news/esma-mica",
        "sentiment": 0.20,
        "keywords": ["esma", "mica", "regulation", "europe"],
    },
    {
        "title": "Fear and Greed Index Drops to 25: Extreme Fear",
        "source": "Decrypt",
        "url": "https://example.com/seed-news/fng-extreme-fear",
        "sentiment": -0.60,
        "keywords": ["fear", "greed", "sentiment"],
    },
    {
        "title": "Whale Alert: 10,000 BTC Moved to Exchange Wallets",
        "source": "CoinTelegraph",
        "url": "https://example.com/seed-news/whale-btc-exchange",
        "sentiment": -0.35,
        "keywords": ["whale", "bitcoin", "exchange"],
    },
    {
        "title": "DeFi Protocol Hack Exposes $12M Vulnerability",
        "source": "Decrypt",
        "url": "https://example.com/seed-news/defi-hack-12m",
        "sentiment": -0.88,
        "keywords": ["defi", "hack", "security"],
    },
    {
        "title": "Bitcoin Hashrate Surpasses 600 EH/s Milestone",
        "source": "CoinTelegraph",
        "url": "https://example.com/seed-news/btc-hashrate-600",
        "sentiment": 0.45,
        "keywords": ["bitcoin", "hashrate", "mining"],
    },
    {
        "title": "Crypto VC Funding Rebounds in Q4 With $3.2B Raised",
        "source": "Decrypt",
        "url": "https://example.com/seed-news/vc-funding-q4",
        "sentiment": 0.72,
        "keywords": ["vc", "funding", "investment"],
    },
    {
        "title": "Cross-Chain Bridge Volume Hits $1B Daily Average",
        "source": "CoinTelegraph",
        "url": "https://example.com/seed-news/bridge-volume",
        "sentiment": 0.50,
        "keywords": ["bridge", "cross-chain", "interoperability"],
    },
)

# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------


def _deterministic_uuid(seed_key: str) -> uuid.UUID:
    """Generate a deterministic UUID5 from a seed key for idempotent inserts."""
    return uuid.uuid5(uuid.NAMESPACE_DNS, seed_key)


async def _seed_users(session: AsyncSession) -> dict[str, uuid.UUID]:
    """Insert demo users, returning mapping of username -> UUID."""
    hashed = _hash_seed_passphrase()
    user_ids: dict[str, uuid.UUID] = {}

    for user_data in SEED_USERS:
        email = user_data["email"]
        result = await session.execute(select(UserOrm).where(UserOrm.email == email))
        existing = result.scalar_one_or_none()
        if existing is not None:
            user_ids[user_data["username"]] = existing.id  # type: ignore[assignment]
            logger.info("User %s already exists, skipping", user_data["username"])
            continue

        user = UserOrm(
            username=user_data["username"],
            email=email,
            password_hash=hashed,
            persona_type=user_data["persona_type"],
            preferences={},
        )
        session.add(user)
        await session.flush()
        user_ids[user_data["username"]] = user.id  # type: ignore[assignment]
        logger.info("Created user: %s", user_data["username"])

    return user_ids


async def _seed_crypto_prices(session: AsyncSession) -> int:
    """Generate and insert OHLCV candles using a random walk."""
    rng = random.Random(42)  # noqa: S311
    now = datetime.now(tz=UTC)
    start = now - timedelta(days=SEED_DAYS)
    total_candles = SEED_DAYS * CANDLES_PER_DAY
    inserted = 0

    for symbol, base_price in BASE_PRICES.items():
        price = base_price
        for i in range(total_candles):
            ts = start + timedelta(hours=4 * i)
            change = rng.uniform(-0.03, 0.03)  # noqa: S311
            price_open = price
            price_close = price * (1 + change)
            price_high = max(price_open, price_close) * (1 + rng.uniform(0.001, 0.015))  # noqa: S311
            price_low = min(price_open, price_close) * (1 - rng.uniform(0.001, 0.015))  # noqa: S311
            volume = base_price * rng.uniform(500, 5000)  # noqa: S311

            result = await session.execute(
                text("""
                    INSERT INTO crypto_prices
                        (symbol, timeframe, timestamp, price_open, price_high,
                         price_low, price_close, volume_24h, market_cap, source)
                    VALUES
                        (:symbol, :timeframe, :timestamp, :price_open, :price_high,
                         :price_low, :price_close, :volume_24h, :market_cap, :source)
                    ON CONFLICT (symbol, timeframe, timestamp) DO NOTHING
                """),
                {
                    "symbol": symbol,
                    "timeframe": SEED_TIMEFRAME,
                    "timestamp": ts,
                    "price_open": round(price_open, 8),
                    "price_high": round(price_high, 8),
                    "price_low": round(price_low, 8),
                    "price_close": round(price_close, 8),
                    "volume_24h": round(volume, 8),
                    "market_cap": None,
                    "source": "seed",
                },
            )
            inserted += result.rowcount  # type: ignore[attr-defined]
            price = price_close

    logger.info("Crypto prices: %d/%d rows inserted", inserted, total_candles * len(BASE_PRICES))
    return inserted


async def _seed_indicators(session: AsyncSession) -> int:
    """Compute simplified RSI + Bollinger and upsert into indicators table."""
    rng = random.Random(42)  # noqa: S311
    now = datetime.now(tz=UTC)
    start = now - timedelta(days=SEED_DAYS)
    total_candles = SEED_DAYS * CANDLES_PER_DAY
    affected = 0

    for symbol, base_price in BASE_PRICES.items():
        closes: list[float] = []
        price = base_price
        for i in range(total_candles):
            ts = start + timedelta(hours=4 * i)
            change = rng.uniform(-0.03, 0.03)  # noqa: S311
            price = price * (1 + change)
            closes.append(price)

            # RSI (simplified, 14-period)
            rsi_val = None
            if len(closes) >= 15:
                gains = []
                losses = []
                for j in range(len(closes) - 14, len(closes)):
                    diff = closes[j] - closes[j - 1]
                    if diff > 0:
                        gains.append(diff)
                    else:
                        losses.append(abs(diff))
                avg_gain = sum(gains) / 14 if gains else 0.0001
                avg_loss = sum(losses) / 14 if losses else 0.0001
                rs = avg_gain / avg_loss
                rsi_val = round(100 - (100 / (1 + rs)), 4)

            # Bollinger Bands (20-period SMA +- 2 stddev)
            bb_upper = bb_middle = bb_lower = pvb = None
            if len(closes) >= 20:
                window = closes[-20:]
                sma = sum(window) / 20
                std = (sum((x - sma) ** 2 for x in window) / 20) ** 0.5
                bb_middle = round(sma, 8)
                bb_upper = round(sma + 2 * std, 8)
                bb_lower = round(sma - 2 * std, 8)
                band_width = bb_upper - bb_lower
                if band_width > 0:
                    pvb = round((price - bb_lower) / band_width, 6)

            result = await session.execute(
                text("""
                    INSERT INTO indicators
                        (id, symbol, timeframe, timestamp, rsi, bollinger_upper,
                         bollinger_middle, bollinger_lower, price_vs_bollinger,
                         harmonic_pattern, trend_slope, trend_type, metadata)
                    VALUES
                        (gen_random_uuid(), :symbol, :timeframe, :timestamp, :rsi,
                         :bollinger_upper, :bollinger_middle, :bollinger_lower,
                         :price_vs_bollinger, :harmonic_pattern, :trend_slope,
                         :trend_type, :metadata::jsonb)
                    ON CONFLICT (symbol, timeframe, timestamp)
                    DO UPDATE SET
                        rsi = EXCLUDED.rsi,
                        bollinger_upper = EXCLUDED.bollinger_upper,
                        bollinger_middle = EXCLUDED.bollinger_middle,
                        bollinger_lower = EXCLUDED.bollinger_lower,
                        price_vs_bollinger = EXCLUDED.price_vs_bollinger,
                        harmonic_pattern = EXCLUDED.harmonic_pattern,
                        trend_slope = EXCLUDED.trend_slope,
                        trend_type = EXCLUDED.trend_type,
                        metadata = EXCLUDED.metadata
                """),
                {
                    "symbol": symbol,
                    "timeframe": SEED_TIMEFRAME,
                    "timestamp": ts,
                    "rsi": rsi_val,
                    "bollinger_upper": bb_upper,
                    "bollinger_middle": bb_middle,
                    "bollinger_lower": bb_lower,
                    "price_vs_bollinger": pvb,
                    "harmonic_pattern": None,
                    "trend_slope": None,
                    "trend_type": None,
                    "metadata": "{}",
                },
            )
            affected += result.rowcount  # type: ignore[attr-defined]

    logger.info("Indicators: %d/%d rows affected", affected, total_candles * len(BASE_PRICES))
    return affected


async def _seed_trading_signals(session: AsyncSession) -> list[uuid.UUID]:
    """Insert deterministic trading signals, returning their IDs."""
    signal_ids: list[uuid.UUID] = []
    now = datetime.now(tz=UTC)

    for idx, sig in enumerate(SEED_SIGNALS):
        sig_id = _deterministic_uuid(f"seed-signal-{idx}")
        result = await session.execute(select(TradingSignalOrm).where(TradingSignalOrm.id == sig_id))
        if result.scalar_one_or_none() is not None:
            signal_ids.append(sig_id)
            continue

        created_at = now - timedelta(hours=idx * 8)
        signal = TradingSignalOrm(
            id=sig_id,
            symbol=str(sig["symbol"]),
            signal_type=str(sig["signal_type"]),
            confidence_score=Decimal(str(sig["confidence"])),
            timeframe_primary=SEED_TIMEFRAME,
            timeframes_aligned=["1h", "2h", "4h"],
            rules_triggered=["RSI_oversold", "BB_squeeze"],
            leverage_suggested=2,
            margin_safety=Decimal("2.5"),
            fees_estimated=Decimal("0.001"),
            model_version="seed-v1",
            created_at=created_at,
        )
        session.add(signal)
        signal_ids.append(sig_id)

    await session.flush()
    logger.info("Trading signals: %d total (%d new)", len(signal_ids), len(SEED_SIGNALS))
    return signal_ids


async def _seed_signal_outcomes(session: AsyncSession, signal_ids: list[uuid.UUID]) -> int:
    """Create outcomes for 80%% of signals."""
    rng = random.Random(99)  # noqa: S311
    created = 0
    # Take first 20 signals (80% of 25)
    for sig_id in signal_ids[:20]:
        result = await session.execute(select(SignalOutcomeOrm).where(SignalOutcomeOrm.signal_id == sig_id))
        if result.scalar_one_or_none() is not None:
            continue

        base = rng.uniform(50_000, 70_000)  # noqa: S311
        pnl = rng.uniform(-5.0, 8.0)  # noqa: S311
        outcome = SignalOutcomeOrm(
            signal_id=sig_id,
            price_at_signal=Decimal(str(round(base, 8))),
            price_after_1h=Decimal(str(round(base * (1 + pnl / 400), 8))),
            price_after_4h=Decimal(str(round(base * (1 + pnl / 200), 8))),
            price_after_1d=Decimal(str(round(base * (1 + pnl / 100), 8))),
            pnl_simulated=Decimal(str(round(pnl, 4))),
            was_correct=pnl > 0,
        )
        session.add(outcome)
        created += 1

    await session.flush()
    logger.info("Signal outcomes: %d created", created)
    return created


async def _seed_portfolio(session: AsyncSession, user_ids: dict[str, uuid.UUID]) -> int:
    """Create portfolio positions for trader, investor, journalist."""
    positions: tuple[tuple[str, str, str, str], ...] = (
        ("demo_trader", "BTCUSDT", "0.5", "65000.00"),
        ("demo_trader", "ETHUSDT", "10.0", "3200.00"),
        ("demo_trader", "SOLUSDT", "100.0", "130.00"),
        ("demo_investor", "BTCUSDT", "2.0", "62000.00"),
        ("demo_investor", "ETHUSDT", "50.0", "3100.00"),
        ("demo_investor", "BNBUSDT", "20.0", "550.00"),
        ("demo_journalist", "BTCUSDT", "0.1", "68000.00"),
        ("demo_journalist", "SOLUSDT", "25.0", "140.00"),
    )
    created = 0
    for username, symbol, qty, entry in positions:
        uid = user_ids.get(username)
        if uid is None:
            continue
        result = await session.execute(
            select(PortfolioOrm).where(
                PortfolioOrm.user_id == uid,
                PortfolioOrm.symbol == symbol,
            )
        )
        if result.scalar_one_or_none() is not None:
            continue
        session.add(
            PortfolioOrm(
                user_id=uid,
                symbol=symbol,
                quantity=Decimal(qty),
                entry_price=Decimal(entry),
            )
        )
        created += 1

    await session.flush()
    logger.info("Portfolio positions: %d created", created)
    return created


async def _seed_watchlist(session: AsyncSession, user_ids: dict[str, uuid.UUID]) -> int:
    """Create watchlist entries — 4 symbols per user."""
    assignments: dict[str, tuple[str, ...]] = {
        "demo_trader": ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"),
        "demo_journalist": ("BTCUSDT", "ETHUSDT", "XRPUSDT", "SOLUSDT"),
        "demo_investor": ("BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT"),
    }
    inserted = 0
    for username, symbols in assignments.items():
        uid = user_ids.get(username)
        if uid is None:
            continue
        for symbol in symbols:
            result = await session.execute(
                text("""
                    INSERT INTO watchlist (id, user_id, symbol)
                    VALUES (:id, :user_id, :symbol)
                    ON CONFLICT (user_id, symbol) DO NOTHING
                """),
                {
                    "id": _deterministic_uuid(f"watchlist-{username}-{symbol}"),
                    "user_id": uid,
                    "symbol": symbol,
                },
            )
            inserted += result.rowcount  # type: ignore[attr-defined]

    logger.info("Watchlist entries: %d inserted", inserted)
    return inserted


async def _seed_news_articles(session: AsyncSession) -> list[uuid.UUID]:
    """Insert seed news articles, returning their IDs."""
    article_ids: list[uuid.UUID] = []
    now = datetime.now(tz=UTC)

    for idx, article in enumerate(SEED_NEWS):
        pub_at = now - timedelta(hours=idx * 6)
        await session.execute(
            text("""
                INSERT INTO news_articles
                    (id, title, content, source, url, published_at,
                     sentiment_score, keywords, reliability_score)
                VALUES
                    (:id, :title, :content, :source, :url, :published_at,
                     :sentiment_score, :keywords::jsonb, :reliability_score)
                ON CONFLICT (url) DO NOTHING
            """),
            {
                "id": _deterministic_uuid(f"seed-news-{idx}"),
                "title": str(article["title"]),
                "content": f"Full article content for: {article['title']}. "
                f"This is seed data for development and testing purposes.",
                "source": str(article["source"]),
                "url": str(article["url"]),
                "published_at": pub_at,
                "sentiment_score": float(article["sentiment"]),  # type: ignore[arg-type]
                "keywords": json.dumps(article["keywords"]),
                "reliability_score": 0.85,
            },
        )
        article_ids.append(_deterministic_uuid(f"seed-news-{idx}"))

    logger.info("News articles: %d processed", len(article_ids))
    return article_ids


async def _seed_text_mining_results(session: AsyncSession, article_ids: list[uuid.UUID]) -> int:
    """Create text mining results for ~78%% of articles (first 14 of 18)."""
    created = 0
    for idx, article_id in enumerate(article_ids[:14]):
        result = await session.execute(select(TextMiningResultOrm).where(TextMiningResultOrm.article_id == article_id))
        if result.scalar_one_or_none() is not None:
            continue

        word_cloud = {
            "bitcoin": 45,
            "market": 32,
            "price": 28,
            "trading": 22,
            "crypto": 20,
            "blockchain": 15,
            "defi": 12,
            "analysis": 10,
        }
        session.add(
            TextMiningResultOrm(
                article_id=article_id,
                word_cloud=word_cloud,
                summary=f"Automated summary for seed article #{idx + 1}.",
                entities=["Bitcoin", "Ethereum", "SEC"],
                topics=["cryptocurrency", "market-analysis"],
            )
        )
        created += 1

    await session.flush()
    logger.info("Text mining results: %d created", created)
    return created


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


async def main() -> None:
    """Run all seed functions in FK-safe order."""
    logger.info("Starting database seed...")

    async with async_session_factory() as session, session.begin():
        # Level 1: no FK dependencies
        user_ids = await _seed_users(session)
        await _seed_crypto_prices(session)
        await _seed_indicators(session)
        article_ids = await _seed_news_articles(session)

        # Level 2: depends on users / signals / articles
        signal_ids = await _seed_trading_signals(session)
        await _seed_signal_outcomes(session, signal_ids)
        await _seed_portfolio(session, user_ids)
        await _seed_watchlist(session, user_ids)
        await _seed_text_mining_results(session, article_ids)

    logger.info("Database seed complete.")


if __name__ == "__main__":
    asyncio.run(main())
