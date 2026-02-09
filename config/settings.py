"""
Module de configuration centralisé pour Crypto Bot.
Supporte JSON et YAML avec surcharge par variables d'environnement et arguments.
"""

import os
import json
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path
from logger_settings import logger


class Config:
    """Classe de configuration centralisée"""

    def __init__(self):
        self._config = self._load_configuration()
        logger.info("✅ Configuration chargée avec succès")

    def _load_configuration(self) -> Dict[str, Any]:
        """Charge la configuration depuis les différentes sources"""
        config = {}

        # 1. Valeurs par défaut
        config.update(self._get_default_config())

        # 2. Fichier de configuration (YAML ou JSON)
        config.update(self._load_config_file())

        # 3. Variables d'environnement
        config.update(self._load_env_vars())

        return config

    def _get_default_config(self) -> Dict[str, Any]:
        """Configuration par défaut"""
        return {
            "pairs": ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "ADA/USDT"],
            "timeframes": ["1h", "4h"],
            "exchanges": ["binance", "kraken", "coinbase"],
            "ticker": {
                "enabled": False,
                "pairs": None,  # Utilise les mêmes que pairs si None
                "snapshot_interval": 5,  # minutes
                "runtime": 60,  # minutes (Attention, 0 = illimité)
                "cache_size": 1000,
            },
            "scheduler": {"enabled": False, "schedule_time": "09:00"},
            "database": {
                "url": "sqlite:///data/processed/crypto_data.db",
                "backup_interval": 24,  # heures
                "max_connections": 5,
                "timeout": 30,  # secondes
            },
            "logging": {
                "level": "INFO",
                "file": "crypto_bot.log",
                "max_size": 10,  # MB
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
        """Charge la configuration depuis le fichier (YAML ou JSON)"""
        config_dir = Path("config")
        yaml_file = config_dir / "config.yaml"
        json_file = config_dir / "config.json"

        # Priorité au YAML si les deux existent
        config_file = yaml_file if yaml_file.exists() else json_file

        if not config_file.exists():
            logger.info(
                "⚠️  Aucun fichier de configuration trouvé (config/config.yaml ou config/config.json)"
            )
            return {}

        try:
            if config_file.suffix == ".yaml":
                with open(config_file, "r") as f:
                    return yaml.safe_load(f) or {}
            elif config_file.suffix == ".json":
                with open(config_file, "r") as f:
                    return json.load(f)
            else:
                logger.warning(f"⚠️  Format de fichier non supporté: {config_file}")
                return {}
        except Exception as e:
            logger.error(f"❌ Impossible de charger le fichier de configuration: {e}")
            return {}

    def _load_env_vars(self) -> Dict[str, Any]:
        """Charge la configuration depuis les variables d'environnement"""
        env_config = {}

        # Mappage des variables d'environnement
        env_mapping = {
            "CRYPTO_BOT_PAIRS": ("pairs", self._parse_list),
            "CRYPTO_BOT_TIMEFRAMES": ("timeframes", self._parse_list),
            "CRYPTO_BOT_EXCHANGES": ("exchanges", self._parse_list),
            "CRYPTO_BOT_TICKER_ENABLED": ("ticker.enabled", self._parse_bool),
            "CRYPTO_BOT_SNAPSHOT_INTERVAL": ("ticker.snapshot_interval", int),
            "CRYPTO_BOT_RUNTIME": ("ticker.runtime", int),
            "CRYPTO_BOT_SCHEDULE_TIME": ("scheduler.schedule_time", str),
            "CRYPTO_BOT_DB_URL": ("database.url", str),
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
        """Définir une valeur dans un dictionnaire imbriqué"""
        keys = path.split(".")
        current = config

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value

    def _parse_list(self, value: str) -> List[str]:
        """Parser une liste depuis une chaîne"""
        return [item.strip() for item in value.split(",") if item.strip()]

    def _parse_bool(self, value: str) -> bool:
        """Parser un booléen depuis une chaîne"""
        return value.lower() in ("true", "1", "yes", "y", "on")

    def get(self, key: str, default=None):
        """Récupérer une valeur de configuration"""
        keys = key.split(".")
        current = self._config

        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default

        return current

    def update_from_args(self, args):
        """Mettre à jour la configuration depuis les arguments de ligne de commande"""
        # Mettre à jour les paramètres de base
        # Utiliser args.pairs même s'il est vide pour permettre de réinitialiser
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

        # Mettre à jour les paramètres du scheduler
        if hasattr(args, "schedule"):
            self._config["scheduler"]["enabled"] = args.schedule
            if args.schedule and hasattr(args, "schedule_time"):
                self._config["scheduler"]["schedule_time"] = args.schedule_time

        # Mettre à jour les paramètres du ticker si activé
        if hasattr(args, "ticker") and args.ticker:
            self._config["ticker"]["enabled"] = True

            # Mettre à jour les paires de ticker
            if hasattr(args, "ticker_pairs") and args.ticker_pairs:
                # Si ticker_pairs est spécifié, l'utiliser pour le ticker ET les paires principales
                self._config["ticker"]["pairs"] = args.ticker_pairs
                self._config["pairs"] = (
                    args.ticker_pairs
                )  # Mettre aussi à jour les paires principales
            elif hasattr(args, "pairs") and args.pairs:
                # Sinon, utiliser les paires principales si elles sont spécifiées
                self._config["ticker"]["pairs"] = args.pairs
            else:
                # Sinon, utiliser les paires principales actuelles
                self._config["ticker"]["pairs"] = self._config.get(
                    "pairs", ["BTC/USDT", "ETH/USDT"]
                )

            # Mettre à jour l'intervalle de snapshot (toujours mettre à jour si fourni)
            if hasattr(args, "snapshot_interval"):
                self._config["ticker"]["snapshot_interval"] = args.snapshot_interval

            # Mettre à jour le runtime (toujours mettre à jour si fourni)
            if hasattr(args, "runtime"):
                self._config["ticker"]["runtime"] = args.runtime
        else:
            # Si le ticker n'est pas activé, s'assurer qu'il est bien désactivé
            self._config["ticker"]["enabled"] = False

        # Journaliser les paramètres mis à jour
        logger.info(
            f"✅ Configuration mise à jour depuis les arguments de ligne de commande:"
        )
        logger.info(f"  Paires: {self._config.get('pairs')}")
        logger.info(f"  Exchanges: {self._config.get('exchanges')}")
        logger.info(
            f"  Ticker enabled: {self._config.get('ticker', {}).get('enabled')}"
        )
        logger.info(
            f"  Snapshot interval: {self._config.get('ticker', {}).get('snapshot_interval')}"
        )
        logger.info(
            f"  Runtime: {self._config.get('ticker', {}).get('runtime')} minutes"
        )
        logger.info(
            f"  Schedule enabled: {self._config.get('scheduler', {}).get('enabled')}"
        )

    def get_all(self) -> Dict[str, Any]:
        """Récupérer toute la configuration"""
        return self._config

    def save_to_file(self, file_path: str = "config/config.yaml"):
        """Sauvegarder la configuration actuelle dans un fichier"""
        try:
            # Créer le dossier config s'il n'existe pas
            config_dir = Path("config")
            config_dir.mkdir(exist_ok=True)

            full_path = Path(file_path)
            if not full_path.parent.exists():
                full_path.parent.mkdir(parents=True, exist_ok=True)

            if file_path.endswith(".yaml"):
                with open(file_path, "w") as f:
                    yaml.safe_dump(
                        self._config, f, default_flow_style=False, sort_keys=False
                    )
            elif file_path.endswith(".json"):
                with open(file_path, "w") as f:
                    json.dump(self._config, f, indent=2, sort_keys=False)
            else:
                logger.error(f"❌ Format de fichier non supporté: {file_path}")
                return False

            logger.info(f"✅ Configuration sauvegardée dans {file_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Impossible de sauvegarder la configuration: {e}")
            return False


# Singleton de configuration
config = Config()
