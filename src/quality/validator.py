"""
Module de validation des données OHLCV.
"""

from datetime import datetime
from typing import List, Optional, Tuple, TypedDict

import pandas as pd


class StructureReport(TypedDict):
    errors: List[str]
    warnings: List[str]


class ValidationReport(TypedDict):
    total_rows: int
    valid_rows: int
    errors: List[str]
    warnings: List[str]
    validity_rate: float


class ConsistencyReport(TypedDict):
    total_rows: int
    is_sorted: bool
    has_gaps: bool
    gap_count: int
    gaps: List[float]
    time_range: Optional[str]


class CompletenessReport(TypedDict):
    actual_count: int
    expected_count: Optional[int]
    completeness_rate: float
    missing_data: bool
    missing_count: int


class ValidationSummary(TypedDict):
    timestamp: str
    data_shape: Tuple[int, int]
    columns: List[str]
    value_validation: ValidationReport
    temporal_validation: ConsistencyReport
    completeness_validation: CompletenessReport
    is_valid: bool
    quality_score: float


class DataValidator0HCLV:
    """
    Valideur de données OHLCV pour les données de marché crypto.

    Checks effectués :
    - Validité des valeurs numériques (prix, volume)
    - Ccohérence temporelle
    - Complétude des données
    - Détection des valeurs aberrantes
    """

    def __init__(self) -> None:
        """Initialise le valideur avec des paramètres par défaut."""
        self.min_price = 0.01  # Prix minimum acceptable (en USD)
        self.max_volume = 1e12  # Volume maximum acceptable
        self.allowed_exchanges = ["binance", "kraken", "coinbase"]

    def _validate_dataframe_structure(self, df: pd.DataFrame) -> Tuple[bool, "StructureReport"]:
        """
        Valide la structure du DataFrame (non vide et colonnes requises).
        """
        report: StructureReport = {"errors": [], "warnings": []}

        # Vérifier que le DataFrame n'est pas vide
        if df.empty:
            report["errors"].append("DataFrame vide")
            return False, report

        # Vérifier les colonnes requises
        required_columns = [
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "symbol",
            "timeframe",
        ]
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            report["errors"].append(f"Colonnes manquantes: {missing_columns}")
            return False, report

        return True, report

    def _validate_price_column(
        self, price_value: float, price_name: str
    ) -> Tuple[List[str], List[str]]:
        """
        Valide une valeur de prix individuelle.
        """
        errors: List[str] = []
        warnings: List[str] = []

        if pd.isna(price_value):
            errors.append(f"{price_name} est NaN")
        elif not isinstance(price_value, (int, float)):
            errors.append(f"{price_name} n'est pas numérique: {type(price_value)}")
        elif price_value <= 0:
            errors.append(f"{price_name} doit être positif: {price_value}")
        elif price_value < self.min_price:
            warnings.append(f"{price_name} très bas: {price_value}")

        return errors, warnings

    def _validate_volume(self, volume_value: float) -> Tuple[List[str], List[str]]:
        """
        Valide une valeur de volume.
        """
        errors: List[str] = []
        warnings: List[str] = []

        if pd.isna(volume_value):
            errors.append("volume est NaN")
        elif not isinstance(volume_value, (int, float)):
            errors.append(f"volume n'est pas numérique: {type(volume_value)}")
        elif volume_value < 0:
            errors.append(f"volume ne peut pas être négatif: {volume_value}")
        elif volume_value > self.max_volume:
            warnings.append(f"volume très élevé: {volume_value}")

        return errors, warnings

    def _validate_price_consistency(self, row: pd.Series) -> Tuple[List[str], List[str]]:
        """
        Valide la cohérence entre les différents prix.
        """
        errors: List[str] = []
        warnings: List[str] = []

        # Vérifier que high >= low
        if row["high"] < row["low"]:
            errors.append(f"high ({row['high']}) < low ({row['low']})")

        # Vérifier que open et close sont positifs
        if row["open"] < 0 or row["close"] < 0:
            errors.append("prix d'ouverture ou de clôture négatif")

        return errors, warnings

    def _validate_metadata(self, row: pd.Series) -> Tuple[List[str], List[str]]:
        """
        Valide les métadonnées (symbol et timeframe).
        """
        errors: List[str] = []
        warnings: List[str] = []

        if not isinstance(row["symbol"], str) or not row["symbol"]:
            errors.append("symbol invalide")

        if not isinstance(row["timeframe"], str) or not row["timeframe"]:
            errors.append("timeframe invalide")

        return errors, warnings

    def validate_ohlcv_values(self, df: pd.DataFrame) -> Tuple[bool, "ValidationReport"]:
        """
        Fonction orchestratrice pour valider les valeurs OHLCV d'un DataFrame.
        """
        validation_report: ValidationReport = {
            "total_rows": len(df),
            "valid_rows": 0,
            "errors": [],
            "warnings": [],
            "validity_rate": 0.0,
        }

        # 1. Structure du DataFrame
        structure_valid, structure_report = self._validate_dataframe_structure(df)
        if not structure_valid:
            validation_report["errors"].extend(structure_report["errors"])
            return False, validation_report

        # Initialiser les compteurs
        valid_rows = 0

        # 2. Validation des valeurs ligne par ligne
        for _idx, row in df.iterrows():
            row_errors: List[str] = []
            row_warnings: List[str] = []

            # Valider chaque colonne de prix
            for price_name in ["open", "high", "low", "close"]:
                price_errors, price_warnings = self._validate_price_column(
                    row[price_name], price_name
                )
                row_errors.extend(price_errors)
                row_warnings.extend(price_warnings)

            # Valider le volume
            volume_errors, volume_warnings = self._validate_volume(row["volume"])
            row_errors.extend(volume_errors)
            row_warnings.extend(volume_warnings)

            # Valider la cohérence des prix (si pas d'erreurs précédentes)
            if len(row_errors) == 0:
                consistency_errors, consistency_warnings = self._validate_price_consistency(row)
                row_errors.extend(consistency_errors)
                row_warnings.extend(consistency_warnings)

            # Valider les métadonnées (si pas d'erreurs précédentes)
            if len(row_errors) == 0:
                metadata_errors, metadata_warnings = self._validate_metadata(row)
                row_errors.extend(metadata_errors)
                row_warnings.extend(metadata_warnings)

            # Mettre à jour les compteurs
            if not row_errors:
                valid_rows += 1
                validation_report["warnings"].extend(row_warnings)
            else:
                validation_report["errors"].extend(row_errors)

        validation_report["valid_rows"] = valid_rows

        # Calculer le taux de validité (corrigé)
        validation_report["validity_rate"] = valid_rows / len(df) if not df.empty else 0.0

        return validation_report["valid_rows"] == len(df), validation_report

    def validate_temporal_consistency(self, df: pd.DataFrame) -> Tuple[bool, ConsistencyReport]:
        """
        Valide la cohérence temporelle des données, recherche les trous temporels.
        """
        consistency_report: ConsistencyReport = {
            "total_rows": len(df),
            "is_sorted": True,
            "has_gaps": False,
            "gap_count": 0,
            "gaps": [],
            "time_range": None,
        }

        if df.empty:
            return False, consistency_report

        # Convertir en datetime si nécessaire
        if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
            df = df.copy()
            df["timestamp"] = pd.to_datetime(df["timestamp"])

        # Vérifier que les timestamps sont triés
        is_sorted = df["timestamp"].is_monotonic_increasing
        consistency_report["is_sorted"] = is_sorted

        if not is_sorted:
            return False, consistency_report

        # Calculer l'intervalle de temps
        time_range = df["timestamp"].max() - df["timestamp"].min()
        consistency_report["time_range"] = str(time_range)

        # Détecter les trous temporels (écarts anormaux)
        if len(df) > 1:
            time_diffs = df["timestamp"].diff().dt.total_seconds()
            # Considérer qu'il y a un trou si la différence est > 2 fois la médiane
            if len(time_diffs) > 1:
                median_diff = time_diffs.median()
                if median_diff > 0:  # Eviter la division par zéro
                    gap_threshold = median_diff * 2
                    gaps = time_diffs[time_diffs > gap_threshold]

                    if not gaps.empty:
                        consistency_report["has_gaps"] = True
                        consistency_report["gap_count"] = len(gaps)
                        consistency_report["gaps"] = gaps.tolist()

        return not consistency_report["has_gaps"], consistency_report

    def validate_data_completeness(
        self, df: pd.DataFrame, expected_count: Optional[int] = None
    ) -> CompletenessReport:
        """
        Valide la complétude des données dans un DataFrame.
        """
        completeness_report: CompletenessReport = {
            "actual_count": len(df),
            "expected_count": expected_count,
            "completeness_rate": 1.0,
            "missing_data": False,
            "missing_count": 0,
        }

        if expected_count is not None and expected_count > 0:
            completeness_report["completeness_rate"] = len(df) / expected_count
            completeness_report["missing_data"] = len(df) < expected_count
            completeness_report["missing_count"] = max(0, expected_count - len(df))
        else:
            completeness_report["completeness_rate"] = 1.0

        return completeness_report

    def get_validation_summary(self, df: pd.DataFrame) -> ValidationSummary:
        """
        Génère un rapport de validation.
        """
        values_valid, value_report = self.validate_ohlcv_values(df)
        temporal_valid, temporal_report = self.validate_temporal_consistency(df)
        completeness_report = self.validate_data_completeness(df)

        summary: ValidationSummary = {
            "timestamp": datetime.utcnow().isoformat(),
            "data_shape": df.shape,
            "columns": list(df.columns),
            "value_validation": value_report,
            "temporal_validation": temporal_report,
            "completeness_validation": completeness_report,
            "is_valid": False,
            "quality_score": 0.0,
        }

        summary["is_valid"] = values_valid and temporal_valid
        summary["quality_score"] = self._calculate_quality_score(summary)

        return summary

    def _calculate_quality_score(self, validation_summary: ValidationSummary) -> float:
        """
        Calcule un score de qualité entre 0 et 1 basé sur les validations.
        """
        score = 1.0

        value_report = validation_summary["value_validation"]
        if value_report["errors"]:
            error_penalty = min(0.5, len(value_report["errors"]) * 0.01)
            score -= error_penalty

        temporal_report = validation_summary["temporal_validation"]
        if temporal_report["has_gaps"]:
            gap_penalty = min(0.3, temporal_report["gap_count"] * 0.01)
            score -= gap_penalty

        completeness_report = validation_summary["completeness_validation"]
        if completeness_report["missing_data"]:
            missing_penalty = min(0.2, completeness_report["completeness_rate"] * 0.1)
            score -= missing_penalty

        return max(0.0, min(1.0, score))
