import json
import os
from copy import deepcopy
from pathlib import Path

from dotenv import load_dotenv

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Les clefs API
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET")
KRAKEN_API_KEY = os.getenv("KRAKEN_API_KEY")
KRAKEN_API_SECRET = os.getenv("KRAKEN_API_SECRET")
COINBASE_API_KEY = os.getenv("COINBASE_API_KEY")
COINBASE_API_SECRET = os.getenv("COINBASE_API_SECRET")
COINBASE_API_PASSPHRASE = os.getenv("COINBASE_API_PASSPHRASE")

# Les variables PostgreSQL
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")


def _build_database_url() -> str:
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url

    if POSTGRES_USER and POSTGRES_PASSWORD and POSTGRES_DB:
        return (
            "postgresql+psycopg2://"
            f"{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
        )

    return "sqlite:///data/processed/crypto_data.db"


DEFAULT_CONFIG = {
    "default_exchange": "binance",
    "pairs": ["BTC/USDT", "ETH/USDT"],
    "timeframes": ["1h", "4h"],
    "exchanges": ["binance"],
    "scheduler": {"schedule_time": "09:00"},
    "ticker": {
        "snapshot_interval": 5,
        "runtime": 60,
        "cache_size": 1000,
        "cache_cleanup_interval": 30,
    },
    "database": {"url": _build_database_url()},
}


def _ensure_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [item for item in value if item is not None]
    return [value]


def _extract_exchange_names(raw_exchanges):
    if raw_exchanges is None:
        return []
    if isinstance(raw_exchanges, dict):
        name = raw_exchanges.get("name")
        return [name] if name else []
    if isinstance(raw_exchanges, (list, tuple, set)):
        names = []
        for item in raw_exchanges:
            if isinstance(item, dict):
                name = item.get("name")
                if name:
                    names.append(name)
            elif item:
                names.append(item)
        return names
    return [raw_exchanges]


def _normalize_config(raw):
    normalized = deepcopy(DEFAULT_CONFIG)
    if not isinstance(raw, dict):
        return normalized

    if isinstance(raw.get("database"), dict) and raw["database"].get("url"):
        normalized["database"]["url"] = raw["database"]["url"]

    if isinstance(raw.get("scheduler"), dict) and raw["scheduler"].get("schedule_time"):
        normalized["scheduler"]["schedule_time"] = raw["scheduler"]["schedule_time"]
    elif raw.get("schedule_time"):
        normalized["scheduler"]["schedule_time"] = raw["schedule_time"]

    if raw.get("default_exchange"):
        normalized["default_exchange"] = raw["default_exchange"]

    exchange_names = _extract_exchange_names(raw.get("exchanges"))
    if exchange_names:
        normalized["exchanges"] = exchange_names
        if not normalized.get("default_exchange"):
            normalized["default_exchange"] = exchange_names[0]

    if raw.get("pairs"):
        normalized["pairs"] = _ensure_list(raw.get("pairs"))
    if raw.get("timeframes"):
        normalized["timeframes"] = _ensure_list(raw.get("timeframes"))

    if isinstance(raw.get("ticker"), dict):
        normalized["ticker"].update(
            {key: value for key, value in raw["ticker"].items() if value is not None}
        )

    if (
        (not raw.get("pairs") or not raw.get("timeframes"))
        and isinstance(raw.get("exchanges"), list)
    ):
        default_exchange = normalized.get("default_exchange")
        for exchange in raw.get("exchanges", []):
            if isinstance(exchange, dict) and exchange.get("name") == default_exchange:
                if not raw.get("pairs") and exchange.get("pairs"):
                    normalized["pairs"] = _ensure_list(exchange.get("pairs"))
                if not raw.get("timeframes") and exchange.get("timeframes"):
                    normalized["timeframes"] = _ensure_list(exchange.get("timeframes"))
                break

    return normalized


class Config:
    def __init__(self, data=None):
        self._data = deepcopy(data) if data is not None else deepcopy(DEFAULT_CONFIG)

    @classmethod
    def load(cls, path=None):
        config_path = Path(path or os.getenv("CONFIG", "data/scheduler_config.json"))
        try:
            raw = json.loads(config_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            raw = {}
        return cls(_normalize_config(raw))

    def get(self, key, default=None):
        current = self._data
        for part in key.split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        return current

    def as_dict(self):
        return deepcopy(self._data)

    def save_to_file(self, path):
        target = Path(path)
        payload = self.as_dict()
        if target.suffix in {".yaml", ".yml"}:
            target.write_text(_to_yaml(payload), encoding="utf-8")
            return True
        if target.suffix == ".json":
            target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            return True
        return False


def _format_yaml_scalar(value):
    if isinstance(value, str):
        return json.dumps(value)
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "null"
    return str(value)


def _build_yaml_lines(data, indent=0):
    lines = []
    pad = " " * indent
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                lines.append(f"{pad}{key}:")
                lines.extend(_build_yaml_lines(value, indent + 2))
            else:
                lines.append(f"{pad}{key}: {_format_yaml_scalar(value)}")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}-")
                lines.extend(_build_yaml_lines(item, indent + 2))
            else:
                lines.append(f"{pad}- {_format_yaml_scalar(item)}")
    else:
        lines.append(f"{pad}{_format_yaml_scalar(data)}")
    return lines


def _to_yaml(data):
    return "\n".join(_build_yaml_lines(data)) + "\n"


config = Config.load()
