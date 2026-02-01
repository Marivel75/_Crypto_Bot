"""
Module de configuration centralisé pour Crypto Bot.
Charge la configuration depuis config.yaml et les variables d'environnement non sensibles.
"""

import os
import yaml
from typing import Dict, Any, List
from pathlib import Path
from logger_settings import logger


class Config:
    """Classe de configuration centralisée."""

    def __init__(self):
        self._config = self._load_configuration()
        logger.info("✅ Configuration chargée avec succès")

    def _load_configuration(self) -> Dict[str, Any]:
        """Charge la configuration depuis les différentes sources."""
        config = {}

        # 1. Valeurs par défaut
        config.update(self._get_default_config())

        # 2. Fichier de configuration YAML
        config.update(self._load_config_file())

        # 3. Variables d'environnement non sensibles
        config.update(self._load_non_sensitive_env_vars())

        return config

    def _get_default_config(self) -> Dict[str, Any]:
        """Retourne la configuration par défaut."""
        return {
            "pairs": ["BTC/USDT", "ETH/USDT"],
            "timeframes": ["1h", "4h"],
            "exchanges": ["binance"],
            "ticker": {
                "enabled": False,
                "pairs": None,
                "snapshot_interval": 5,
                "runtime": 60,
                "cache_size": 1000,
            },
            "scheduler": {"enabled": False, "schedule_time": "09:00"},
            "database": {
                "type": "postgresql",  # ou "sqlite" pour le mode local
                "url": "",  # À définir dans .env via SUPABASE_DB_URL
                "timeout": 30,
                "max_connections": 10,
                "pool_size": 5,
                "max_overflow": 10,
                "backup_interval": 24,
            },
            "logging": {
                "level": "INFO",
                "file": "crypto_bot.log",
                "max_size": 10,
                "backup_count": 5,
            },
            "api": {
                "rate_limit": 100,  # requêtes/minute
                "timeout": 30,  # secondes
                "retry_attempts": 3,
                "retry_delay": 5,  # secondes
            },
        }

    def _load_config_file(self) -> Dict[str, Any]:
        """Charge la configuration depuis le fichier YAML."""
        config_dir = Path(__file__).parent
        yaml_file = config_dir / "config.yaml"

        if not yaml_file.exists():
            logger.info("⚠️ Aucun fichier de configuration YAML trouvé")
            return {}

        try:
            with open(yaml_file, "r") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"❌ Impossible de charger le fichier YAML: {e}")
            return {}

    def _load_non_sensitive_env_vars(self) -> Dict[str, Any]:
        """Charge les variables d'environnement non sensibles."""
        env_config = {}

        # Mappage des variables d'environnement non sensibles
        env_mapping = {
            "CRYPTO_BOT_PAIRS": ("pairs", self._parse_list),
            "CRYPTO_BOT_TIMEFRAMES": ("timeframes", self._parse_list),
            "CRYPTO_BOT_EXCHANGES": ("exchanges", self._parse_list),
            "CRYPTO_BOT_TICKER_ENABLED": ("ticker.enabled", self._parse_bool),
            "CRYPTO_BOT_SNAPSHOT_INTERVAL": ("ticker.snapshot_interval", int),
            "CRYPTO_BOT_RUNTIME": ("ticker.runtime", int),
            "CRYPTO_BOT_SCHEDULE_TIME": ("scheduler.schedule_time", str),
            "CRYPTO_BOT_DB_TYPE": ("database.type", str),
            "CRYPTO_BOT_LOG_LEVEL": ("logging.level", str),
            "CRYPTO_BOT_API_TIMEOUT": ("api.timeout", int),
            "CRYPTO_BOT_API_RETRY_ATTEMPTS": ("api.retry_attempts", int),
        }

        for env_var, (config_path, parser) in env_mapping.items():
            if env_var in os.environ:
                value = os.environ[env_var]
                try:
                    parsed_value = parser(value) if parser else value
                    self._set_nested_config(env_config, config_path, parsed_value)
                    logger.debug(
                        f"Configuration chargée depuis {env_var}: {parsed_value}"
                    )
                except Exception as e:
                    logger.error(f"❌ Impossible de parser {env_var}: {e}")

        return env_config

    def _set_nested_config(self, config: Dict, path: str, value: Any):
        """Définir une valeur dans un dictionnaire imbriqué."""
        keys = path.split(".")
        current = config

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value

    def _parse_list(self, value: str) -> List[str]:
        """Parser une liste depuis une chaîne."""
        return [item.strip() for item in value.split(",") if item.strip()]

    def _parse_bool(self, value: str) -> bool:
        """Parser un booléen depuis une chaîne."""
        return value.lower() in ("true", "1", "yes", "y", "on")

    def get(self, key: str, default=None):
        """Récupérer une valeur de configuration."""
        keys = key.split(".")
        current = self._config

        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default

        return current

    def get_all(self) -> Dict[str, Any]:
        """Récupérer toute la configuration."""
        return self._config

    def update_from_args(self, args):
        """Mettre à jour la configuration depuis les arguments de ligne de commande."""
        if hasattr(args, "pairs"):
            self._config["pairs"] = (
                args.pairs if args.pairs else self._config.get("pairs")
            )
        if hasattr(args, "timeframes"):
            self._config["timeframes"] = (
                args.timeframes if args.timeframes else self._config.get("timeframes")
            )
        if hasattr(args, "exchanges"):
            self._config["exchanges"] = (
                args.exchanges if args.exchanges else self._config.get("exchanges")
            )

        if hasattr(args, "schedule"):
            self._config["scheduler"]["enabled"] = args.schedule
            if args.schedule and hasattr(args, "schedule_time"):
                self._config["scheduler"]["schedule_time"] = args.schedule_time

        if hasattr(args, "ticker") and args.ticker:
            self._config["ticker"]["enabled"] = True
            if hasattr(args, "ticker_pairs") and args.ticker_pairs:
                self._config["ticker"]["pairs"] = args.ticker_pairs
                self._config["pairs"] = args.ticker_pairs
            elif hasattr(args, "pairs") and args.pairs:
                self._config["ticker"]["pairs"] = args.pairs
            else:
                self._config["ticker"]["pairs"] = self._config.get(
                    "pairs", ["BTC/USDT", "ETH/USDT"]
                )

            if hasattr(args, "snapshot_interval"):
                self._config["ticker"]["snapshot_interval"] = args.snapshot_interval
            if hasattr(args, "runtime"):
                self._config["ticker"]["runtime"] = args.runtime
        else:
            self._config["ticker"]["enabled"] = False

        logger.info(
            f"✅ Configuration mise à jour depuis les arguments de ligne de commande"
        )

    def save_to_file(self, file_path: str = "config/config.yaml"):
        """Sauvegarder la configuration actuelle dans un fichier."""
        try:
            config_dir = Path(__file__).parent
            config_dir.mkdir(exist_ok=True)

            full_path = config_dir / file_path
            with open(full_path, "w") as f:
                yaml.safe_dump(
                    self._config, f, default_flow_style=False, sort_keys=False
                )

            logger.info(f"✅ Configuration sauvegardée dans {full_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Impossible de sauvegarder la configuration: {e}")
            return False


# Singleton de configuration
config = Config()
