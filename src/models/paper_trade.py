from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class PaperPortfolio(Base):
    __tablename__ = "paper_portfolios"

    id = Column(String(36), primary_key=True, nullable=False)
    name = Column(String(100), nullable=False)
    initial_capital = Column(Float, nullable=False, comment="Capital de départ en USDT")
    cash = Column(Float, nullable=False, comment="Cash disponible actuel en USDT")
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<PaperPortfolio(id={self.id}, name={self.name}, cash={self.cash})>"


class PaperTrade(Base):
    __tablename__ = "paper_trades"

    id = Column(String(36), primary_key=True, nullable=False)
    portfolio_id = Column(String(36), ForeignKey("paper_portfolios.id"), nullable=False)

    symbol = Column(String(20), nullable=False, comment="Ex: BTC/USDT")
    side = Column(String(4), nullable=False, comment="BUY ou SELL")
    quantity = Column(Float, nullable=False, comment="Quantité d'actif")
    entry_price = Column(Float, nullable=False, comment="Prix d'entrée (close bougie)")
    entry_time = Column(DateTime, nullable=False)

    exit_price = Column(Float, nullable=True, comment="Prix de sortie")
    exit_time = Column(DateTime, nullable=True)

    status = Column(String(6), nullable=False, default="OPEN", comment="OPEN ou CLOSED")
    pnl = Column(Float, nullable=True, comment="P&L réalisé en USDT")
    pnl_pct = Column(Float, nullable=True, comment="P&L en %")

    signal_source = Column(String(50), nullable=False, default="manual",
                           comment="manual | technical | xgboost | random_forest | ...")
    signal_score = Column(Float, nullable=True, comment="Score du signal déclencheur")

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_paper_trades_portfolio", "portfolio_id"),
        Index("idx_paper_trades_status", "status"),
        Index("idx_paper_trades_symbol", "symbol"),
    )

    def __repr__(self):
        return (
            f"<PaperTrade(id={self.id}, symbol={self.symbol}, side={self.side}, "
            f"status={self.status}, pnl={self.pnl})>"
        )
