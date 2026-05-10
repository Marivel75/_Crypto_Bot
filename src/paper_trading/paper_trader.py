import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from src.models.ohlcv import OHLCV
from src.models.paper_trade import PaperPortfolio, PaperTrade


class PaperTrader:
    def __init__(self, db: Session):
        self.db = db

    def get_last_price(self, symbol: str, timeframe: str = "1d") -> float:
        # Préférer le prix live WebSocket si disponible
        from src.services.live_price_cache import live_price_cache
        live = live_price_cache.get(symbol.upper())
        if live:
            return live

        # Fallback : dernière bougie OHLCV
        row = (
            self.db.query(OHLCV)
            .filter(OHLCV.symbol == symbol.upper(), OHLCV.timeframe == timeframe)
            .order_by(OHLCV.timestamp.desc())
            .first()
        )
        if row is None:
            raise ValueError(f"Aucune bougie {timeframe} trouvée pour {symbol}")
        return row.close

    def create_portfolio(self, name: str, initial_capital: float) -> PaperPortfolio:
        portfolio = PaperPortfolio(
            id=str(uuid.uuid4()),
            name=name,
            initial_capital=initial_capital,
            cash=initial_capital,
            created_at=datetime.utcnow(),
        )
        self.db.add(portfolio)
        self.db.commit()
        self.db.refresh(portfolio)
        return portfolio

    def open_position(
        self,
        portfolio_id: str,
        symbol: str,
        quantity: Optional[float] = None,
        amount_usdt: Optional[float] = None,
        signal_source: str = "manual",
        signal_score: Optional[float] = None,
    ) -> PaperTrade:
        portfolio = self.db.query(PaperPortfolio).filter(PaperPortfolio.id == portfolio_id).first()
        if portfolio is None:
            raise ValueError(f"Portefeuille {portfolio_id} introuvable")

        price = self.get_last_price(symbol)

        if quantity is None and amount_usdt is None:
            raise ValueError("Fournir quantity ou amount_usdt")
        if quantity is None:
            quantity = amount_usdt / price
        if quantity < 0.0001:
            raise ValueError("Quantité minimale : 0.0001")

        cost = quantity * price
        if portfolio.cash < cost:
            raise ValueError(
                f"Cash insuffisant : disponible {portfolio.cash:.2f} USDT, requis {cost:.2f} USDT"
            )

        portfolio.cash -= cost

        trade = PaperTrade(
            id=str(uuid.uuid4()),
            portfolio_id=portfolio_id,
            symbol=symbol.upper(),
            side="BUY",
            quantity=quantity,
            entry_price=price,
            entry_time=datetime.utcnow(),
            status="OPEN",
            signal_source=signal_source,
            signal_score=signal_score,
            created_at=datetime.utcnow(),
        )
        self.db.add(trade)
        self.db.commit()
        self.db.refresh(trade)
        return trade

    def close_position(self, trade_id: str) -> PaperTrade:
        trade = self.db.query(PaperTrade).filter(PaperTrade.id == trade_id).first()
        if trade is None:
            raise ValueError(f"Trade {trade_id} introuvable")
        if trade.status == "CLOSED":
            raise ValueError("Position déjà fermée")

        portfolio = self.db.query(PaperPortfolio).filter(PaperPortfolio.id == trade.portfolio_id).first()
        exit_price = self.get_last_price(trade.symbol)

        pnl = (exit_price - trade.entry_price) * trade.quantity
        pnl_pct = ((exit_price - trade.entry_price) / trade.entry_price) * 100

        trade.exit_price = exit_price
        trade.exit_time = datetime.utcnow()
        trade.status = "CLOSED"
        trade.pnl = pnl
        trade.pnl_pct = pnl_pct

        portfolio.cash += trade.quantity * exit_price

        self.db.commit()
        self.db.refresh(trade)
        return trade

    def get_portfolio_summary(self, portfolio_id: str) -> dict:
        portfolio = self.db.query(PaperPortfolio).filter(PaperPortfolio.id == portfolio_id).first()
        if portfolio is None:
            raise ValueError(f"Portefeuille {portfolio_id} introuvable")

        open_trades = (
            self.db.query(PaperTrade)
            .filter(PaperTrade.portfolio_id == portfolio_id, PaperTrade.status == "OPEN")
            .all()
        )
        closed_trades = (
            self.db.query(PaperTrade)
            .filter(PaperTrade.portfolio_id == portfolio_id, PaperTrade.status == "CLOSED")
            .all()
        )

        latent_value = 0.0
        latent_pnl = 0.0
        open_trades_out = []
        for t in open_trades:
            try:
                current_price = self.get_last_price(t.symbol)
            except ValueError:
                current_price = t.entry_price
            pos_value = t.quantity * current_price
            pos_pnl = (current_price - t.entry_price) * t.quantity
            pos_pnl_pct = ((current_price - t.entry_price) / t.entry_price) * 100
            latent_value += pos_value
            latent_pnl += pos_pnl
            open_trades_out.append({
                "id": t.id,
                "symbol": t.symbol,
                "quantity": t.quantity,
                "entry_price": t.entry_price,
                "current_price": current_price,
                "pnl_latent": round(pos_pnl, 4),
                "pnl_latent_pct": round(pos_pnl_pct, 2),
                "signal_source": t.signal_source,
                "entry_time": t.entry_time,
            })

        total_capital = portfolio.cash + latent_value
        total_realized_pnl = sum(t.pnl for t in closed_trades if t.pnl is not None)

        winning = [t for t in closed_trades if t.pnl is not None and t.pnl > 0]
        win_rate = (len(winning) / len(closed_trades) * 100) if closed_trades else 0.0

        best_trade = max(closed_trades, key=lambda t: t.pnl or 0, default=None)
        worst_trade = min(closed_trades, key=lambda t: t.pnl or 0, default=None)

        return {
            "portfolio": {
                "id": portfolio.id,
                "name": portfolio.name,
                "initial_capital": portfolio.initial_capital,
                "cash": round(portfolio.cash, 4),
                "created_at": portfolio.created_at,
            },
            "metrics": {
                "total_capital": round(total_capital, 4),
                "total_realized_pnl": round(total_realized_pnl, 4),
                "latent_pnl": round(latent_pnl, 4),
                "win_rate": round(win_rate, 2),
                "total_closed_trades": len(closed_trades),
                "total_open_trades": len(open_trades),
                "best_trade_pnl": round(best_trade.pnl, 4) if best_trade and best_trade.pnl else None,
                "worst_trade_pnl": round(worst_trade.pnl, 4) if worst_trade and worst_trade.pnl else None,
            },
            "open_positions": open_trades_out,
            "closed_trades": [
                {
                    "id": t.id,
                    "symbol": t.symbol,
                    "quantity": t.quantity,
                    "entry_price": t.entry_price,
                    "exit_price": t.exit_price,
                    "pnl": round(t.pnl, 4) if t.pnl is not None else None,
                    "pnl_pct": round(t.pnl_pct, 2) if t.pnl_pct is not None else None,
                    "signal_source": t.signal_source,
                    "entry_time": t.entry_time,
                    "exit_time": t.exit_time,
                }
                for t in closed_trades
            ],
        }
