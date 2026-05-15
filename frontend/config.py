"""Frontend configuration — reads API_URL and LOG_LEVEL from environment."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class FrontendSettings:
    api_url: str = "http://localhost:8000"
    tracked_symbols: list[str] = field(default_factory=lambda: [
        "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "ADA/USDT",
        "XRP/USDT", "DOT/USDT", "AVAX/USDT", "MATIC/USDT", "LINK/USDT",
    ])
    timeframes: list[str] = field(default_factory=lambda: ["1h", "4h", "1d", "1w"])
    log_level: str = "INFO"

    def __post_init__(self) -> None:
        if url := os.getenv("API_URL"):
            self.api_url = url
        else:
            try:
                import streamlit as st
                if "API_URL" in st.secrets:
                    self.api_url = st.secrets["API_URL"]
            except Exception:
                pass
        if level := os.getenv("LOG_LEVEL"):
            self.log_level = level


frontend_settings = FrontendSettings()
