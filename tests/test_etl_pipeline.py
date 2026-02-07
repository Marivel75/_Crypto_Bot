"""
Tests unitaires pour l'ETLPipeline.
Teste l'orchestration complète du pipeline ETL.
"""

import pytest
import sys
import os
import pandas as pd
from unittest.mock import MagicMock, patch
from datetime import datetime

# Ajouter le chemin racine au PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.etl.pipeline_ohlcv import (
    ETLPipelineOHLCV as ETLPipeline,
    PipelineResult,
    PipelineError,
)
from src.etl.extractor import OHLCVExtractor, ExtractionError
from src.etl.transformer import OHLCVTransformer, TransformationError
from src.etl.loader import OHLCVLoader, LoadingError


class TestPipelineResult:
    """Tests pour la classe PipelineResult."""

    def test_pipeline_result_initialization(self):
        """Test l'initialisation du résultat."""
        result = PipelineResult("BTC/USDT", "1h")

        assert result.symbol == "BTC/USDT"
        assert result.timeframe == "1h"
        assert not result.success
        assert result.extraction_time == 0.0
        assert result.transformation_time == 0.0
        assert result.loading_time == 0.0
        assert result.raw_rows == 0
        assert result.transformed_rows == 0
        assert result.loaded_rows == 0
        assert result.error is None
        assert result.error_step is None

    def test_pipeline_result_total_time(self):
        """Test le calcul du temps total."""
        result = PipelineResult("BTC/USDT", "1h")
        result.extraction_time = 1.0
        result.transformation_time = 2.0
        result.loading_time = 3.0

        assert result.total_time() == 6.0

    def test_pipeline_result_to_dict(self):
        """Test la conversion en dictionnaire."""
        result = PipelineResult("BTC/USDT", "1h")
        result.extraction_time = 1.0
        result.transformation_time = 2.0
        result.loading_time = 3.0
        result.raw_rows = 100
        result.transformed_rows = 95
        result.loaded_rows = 95
        result.success = True

        result_dict = result.to_dict()

        assert result_dict["symbol"] == "BTC/USDT"
        assert result_dict["timeframe"] == "1h"
        assert result_dict["success"]
        assert result_dict["total_time"] == 6.0


class TestETLPipelineInitialization:
    """Tests pour l'initialisation du pipeline."""

    def test_pipeline_initialization(self):
        """Test l'initialisation du pipeline."""
        mock_extractor = MagicMock(spec=OHLCVExtractor)
        mock_transformer = MagicMock(spec=OHLCVTransformer)
        mock_loader = MagicMock(spec=OHLCVLoader)

        pipeline = ETLPipeline(mock_extractor, mock_transformer, mock_loader)

        assert pipeline.extractor == mock_extractor
        assert pipeline.transformer == mock_transformer
        assert pipeline.loader == mock_loader


class TestETLPipelineRun:
    """Tests pour la méthode run."""

    def test_pipeline_run_success(self):
        """Test l'exécution réussie du pipeline."""
        # Configuration des mocks
        mock_extractor = MagicMock(spec=OHLCVExtractor)
        mock_transformer = MagicMock(spec=OHLCVTransformer)
        mock_loader = MagicMock(spec=OHLCVLoader)

        # Données mock
        raw_data = [[1768294800000, 90000.0, 90100.0, 89900.0, 90050.0, 123.45]]
        df = pd.DataFrame(
            raw_data, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )

        # Nouvelle API: extract_ohlcv_data retourne un dictionnaire
        mock_extractor.extract_ohlcv_data.return_value = {"BTC/USDT": df}
        mock_transformer.transform.return_value = df
        mock_loader.load.return_value = 1

        # Création du pipeline
        pipeline = ETLPipeline(mock_extractor, mock_transformer, mock_loader)

        # Exécution
        result = pipeline.run("BTC/USDT", "1h", 100)

        # Vérifications
        assert result.success
        assert result.symbol == "BTC/USDT"
        assert result.timeframe == "1h"
        assert result.raw_rows == 1
        assert result.transformed_rows == 1
        assert result.loaded_rows == 1
        assert result.error is None

        # Vérifier les appels avec la nouvelle API
        mock_extractor.extract_ohlcv_data.assert_called_once_with(
            ["BTC/USDT"], "1h", 100
        )
        mock_transformer.transform.assert_called_once_with(raw_data, "BTC/USDT", "1h")
        mock_loader.load.assert_called_once_with(df)

    def test_pipeline_run_extraction_error(self):
        """Test l'échec à l'étape d'extraction."""
        mock_extractor = MagicMock(spec=OHLCVExtractor)
        mock_transformer = MagicMock(spec=OHLCVTransformer)
        mock_loader = MagicMock(spec=OHLCVLoader)

        # Nouvelle API: lever une exception dans extract_ohlcv_data
        mock_extractor.extract_ohlcv_data.side_effect = ExtractionError(
            "Extraction failed"
        )

        pipeline = ETLPipeline(mock_extractor, mock_transformer, mock_loader)

        # Exécution
        result = pipeline.run("BTC/USDT", "1h")

        # Vérifications
        assert not result.success
        assert result.error_step == "extraction"
        assert "Extraction failed" in result.error

        # Vérifier que l'extraction a été appelée
        mock_extractor.extract_ohlcv_data.assert_called_once_with(
            ["BTC/USDT"], "1h", 100
        )
        # Vérifier que la transformation et le chargement n'ont pas été appelés
        mock_transformer.transform.assert_not_called()
        mock_loader.load.assert_not_called()

    def test_pipeline_run_transformation_error(self):
        """Test l'échec à l'étape de transformation."""
        mock_extractor = MagicMock(spec=OHLCVExtractor)
        mock_transformer = MagicMock(spec=OHLCVTransformer)
        mock_loader = MagicMock(spec=OHLCVLoader)

        # Données mock
        raw_data = [[1768294800000, 90000.0, 90100.0, 89900.0, 90050.0, 123.45]]
        df = pd.DataFrame(
            raw_data, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )

        # Nouvelle API
        mock_extractor.extract_ohlcv_data.return_value = {"BTC/USDT": df}
        mock_transformer.transform.side_effect = TransformationError(
            "Transformation failed"
        )

        pipeline = ETLPipeline(mock_extractor, mock_transformer, mock_loader)

        # Exécution
        result = pipeline.run("BTC/USDT", "1h")

        # Vérifications
        assert not result.success
        assert result.error_step == "transformation"
        assert "Transformation failed" in result.error

        # Vérifier les appels
        mock_extractor.extract_ohlcv_data.assert_called_once_with(
            ["BTC/USDT"], "1h", 100
        )
        mock_transformer.transform.assert_called_once_with(raw_data, "BTC/USDT", "1h")
        mock_loader.load.assert_not_called()

    def test_pipeline_run_loading_error(self):
        """Test l'échec à l'étape de chargement."""
        mock_extractor = MagicMock(spec=OHLCVExtractor)
        mock_transformer = MagicMock(spec=OHLCVTransformer)
        mock_loader = MagicMock(spec=OHLCVLoader)

        # Données mock
        raw_data = [[1768294800000, 90000.0, 90100.0, 89900.0, 90050.0, 123.45]]
        df = pd.DataFrame(
            raw_data, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )

        # Nouvelle API
        mock_extractor.extract_ohlcv_data.return_value = {"BTC/USDT": df}
        mock_transformer.transform.return_value = df
        mock_loader.load.side_effect = LoadingError("Loading failed")

        pipeline = ETLPipeline(mock_extractor, mock_transformer, mock_loader)

        # Exécution
        result = pipeline.run("BTC/USDT", "1h")

        # Vérifications
        assert not result.success
        assert result.error_step == "loading"
        assert "Loading failed" in result.error

        # Vérifier les appels
        mock_extractor.extract_ohlcv_data.assert_called_once_with(
            ["BTC/USDT"], "1h", 100
        )
        mock_transformer.transform.assert_called_once_with(raw_data, "BTC/USDT", "1h")
        mock_loader.load.assert_called_once_with(df)


class TestETLPipelineBatchOperations:
    """Tests pour les opérations batch."""

    def test_pipeline_run_batch_success(self):
        """Test l'exécution batch réussie."""
        mock_extractor = MagicMock(spec=OHLCVExtractor)
        mock_transformer = MagicMock(spec=OHLCVTransformer)
        mock_loader = MagicMock(spec=OHLCVLoader)

        # Données mock
        raw_data = [[1768294800000, 90000.0, 90100.0, 89900.0, 90050.0, 123.45]]
        df = pd.DataFrame(
            raw_data, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )

        # Nouvelle API - le pipeline appelle extract_ohlcv_data pour chaque symbole individuellement
        def extract_side_effect(pairs, timeframe, limit):
            result = {}
            for pair in pairs:
                result[pair] = df
            return result

        mock_extractor.extract_ohlcv_data.side_effect = extract_side_effect
        mock_transformer.transform.return_value = df
        mock_loader.load.return_value = 1

        pipeline = ETLPipeline(mock_extractor, mock_transformer, mock_loader)

        # Exécution batch
        symbols = ["BTC/USDT", "ETH/USDT"]
        results = pipeline.run_batch(symbols, "1h", 100)

        # Vérifications
        assert len(results) == 2
        assert all(r.success for r in results.values())
        assert all(r.raw_rows == 1 for r in results.values())

        # Vérifier les appels - le pipeline appelle une fois par symbole
        assert mock_extractor.extract_ohlcv_data.call_count == 2
        # Vérifier que transform a été appelé pour les deux symboles
        assert mock_transformer.transform.call_count == 2
        calls = mock_transformer.transform.call_args_list
        assert any(call[0][1] == "BTC/USDT" for call in calls)
        assert any(call[0][1] == "ETH/USDT" for call in calls)
        assert mock_loader.load.call_count == 2

    def test_pipeline_run_batch_partial_failure(self):
        """Test l'exécution batch avec échec partiel."""
        mock_extractor = MagicMock(spec=OHLCVExtractor)
        mock_transformer = MagicMock(spec=OHLCVTransformer)
        mock_loader = MagicMock(spec=OHLCVLoader)

        # Données mock
        raw_data = [[1768294800000, 90000.0, 90100.0, 89900.0, 90050.0, 123.45]]
        df = pd.DataFrame(
            raw_data, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )

        # Nouvelle API: BTC réussit, ETH échoue
        def extract_side_effect(pairs, *args):
            result = {}
            for pair in pairs:
                if pair == "BTC/USDT":
                    result[pair] = df
                else:
                    raise ExtractionError("Extraction failed")
            return result

        mock_extractor.extract_ohlcv_data.side_effect = extract_side_effect

        pipeline = ETLPipeline(mock_extractor, mock_transformer, mock_loader)

        # Exécution batch
        symbols = ["BTC/USDT", "ETH/USDT"]
        results = pipeline.run_batch(symbols, "1h")

        # Vérifications
        assert len(results) == 2
        assert results["BTC/USDT"].success
        assert not results["ETH/USDT"].success
        assert results["ETH/USDT"].error_step == "extraction"


class TestETLPipelineExtractTransformBatch:
    """Tests pour Extract+Transform batch."""

    def test_extract_transform_batch_success(self):
        """Test Extract+Transform batch réussi."""
        mock_extractor = MagicMock(spec=OHLCVExtractor)
        mock_transformer = MagicMock(spec=OHLCVTransformer)
        mock_loader = MagicMock(spec=OHLCVLoader)

        # Données mock
        raw_data = [[1768294800000, 90000.0, 90100.0, 89900.0, 90050.0, 123.45]]
        df = pd.DataFrame(
            raw_data, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )

        # Nouvelle API - le pipeline appelle extract_ohlcv_data pour chaque symbole individuellement
        def extract_side_effect(pairs, timeframe, limit):
            result = {}
            for pair in pairs:
                result[pair] = df
            return result

        mock_extractor.extract_ohlcv_data.side_effect = extract_side_effect
        mock_transformer.transform.return_value = df

        pipeline = ETLPipeline(mock_extractor, mock_transformer, mock_loader)

        # Exécution Extract+Transform batch
        symbols = ["BTC/USDT", "ETH/USDT"]
        results = pipeline.run_extract_transform_batch(symbols, "1h", 100)

        # Vérifications
        assert len(results) == 2
        assert all(isinstance(df, pd.DataFrame) for df in results.values())
        assert all(len(df) == 1 for df in results.values())

        # Vérifier les appels - le pipeline appelle une fois par symbole
        assert mock_extractor.extract_ohlcv_data.call_count == 2
        assert mock_transformer.transform.call_count == 2


class TestETLPipelineSummary:
    """Tests pour la génération de résumés."""

    def test_get_summary_success(self):
        """Test la génération de résumé avec succès."""
        # Création de résultats mock
        results = {
            "BTC/USDT": PipelineResult(
                "BTC/USDT",
                "1h",
                success=True,
                raw_rows=100,
                transformed_rows=95,
                loaded_rows=95,
            ),
            "ETH/USDT": PipelineResult(
                "ETH/USDT",
                "1h",
                success=True,
                raw_rows=100,
                transformed_rows=98,
                loaded_rows=98,
            ),
        }

        # Génération du résumé - get_summary est une méthode d'instance
        pipeline = ETLPipeline(MagicMock(), MagicMock(), MagicMock())
        summary = pipeline.get_summary(results)

        # Vérifications
        assert summary["total_symbols"] == 2
        assert summary["successful"] == 2
        assert summary["failed"] == 0
        assert summary["success_rate"] == 1.0
        assert summary["total_raw_rows"] == 200
        assert summary["total_transformed_rows"] == 193
        assert summary["total_loaded_rows"] == 193

    def test_get_summary_partial_failure(self):
        """Test la génération de résumé avec échec partiel."""
        # Création de résultats mock
        results = {
            "BTC/USDT": PipelineResult(
                "BTC/USDT",
                "1h",
                success=True,
                raw_rows=100,
                transformed_rows=95,
                loaded_rows=95,
            ),
            "ETH/USDT": PipelineResult(
                "ETH/USDT",
                "1h",
                success=False,
                raw_rows=100,
                transformed_rows=0,
                loaded_rows=0,
            ),
        }

        # Génération du résumé - get_summary est une méthode d'instance
        pipeline = ETLPipeline(MagicMock(), MagicMock(), MagicMock())
        summary = pipeline.get_summary(results)

        # Vérifications
        assert summary["total_symbols"] == 2
        assert summary["successful"] == 1
        assert summary["failed"] == 1
        assert summary["success_rate"] == 0.5
        # Correction: total_raw_rows inclut les deux symboles (100 chacun)
        assert summary["total_raw_rows"] == 200
        assert summary["total_transformed_rows"] == 95
        assert summary["total_loaded_rows"] == 95
