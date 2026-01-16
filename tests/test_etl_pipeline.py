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

from src.etl.pipeline_ohlcv import ETLPipelineOHLCV as ETLPipeline, PipelineResult, PipelineError
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
        result.success = True
        result.extraction_time = 1.0
        result.raw_rows = 100
        
        result_dict = result.to_dict()
        
        assert result_dict["symbol"] == "BTC/USDT"
        assert result_dict["timeframe"] == "1h"
        assert result_dict["success"]
        assert result_dict["extraction_time"] == 1.0
        assert result_dict["raw_rows"] == 100
        assert "total_time" in result_dict


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
        df = pd.DataFrame(raw_data, columns=["timestamp", "open", "high", "low", "close", "volume"])
        
        mock_extractor.extract.return_value = raw_data
        mock_transformer.transform.return_value = df
        mock_loader.load.return_value = 1
        
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
        assert result.extraction_time > 0
        assert result.transformation_time > 0
        assert result.loading_time > 0
        assert result.error is None
        assert result.error_step is None
        
        # Vérification des appels
        mock_extractor.extract.assert_called_once_with("BTC/USDT", "1h", 100)
        mock_transformer.transform.assert_called_once()
        mock_loader.load.assert_called_once()
    
    def test_pipeline_run_extraction_error(self):
        """Test l'échec à l'étape d'extraction."""
        mock_extractor = MagicMock(spec=OHLCVExtractor)
        mock_transformer = MagicMock(spec=OHLCVTransformer)
        mock_loader = MagicMock(spec=OHLCVLoader)
        
        mock_extractor.extract.side_effect = ExtractionError("Extraction failed")
        
        pipeline = ETLPipeline(mock_extractor, mock_transformer, mock_loader)
        
        result = pipeline.run("BTC/USDT", "1h")
        
        assert not result.success
        assert result.error_step == "extraction"
        assert "Extraction failed" in result.error
        assert result.raw_rows == 0
        
        # Vérification que les autres étapes ne sont pas appelées
        mock_transformer.transform.assert_not_called()
        mock_loader.load.assert_not_called()
    
    def test_pipeline_run_transformation_error(self):
        """Test l'échec à l'étape de transformation."""
        mock_extractor = MagicMock(spec=OHLCVExtractor)
        mock_transformer = MagicMock(spec=OHLCVTransformer)
        mock_loader = MagicMock(spec=OHLCVLoader)
        
        raw_data = [[1768294800000, 90000.0, 90100.0, 89900.0, 90050.0, 123.45]]
        
        mock_extractor.extract.return_value = raw_data
        mock_transformer.transform.side_effect = TransformationError("Transformation failed")
        
        pipeline = ETLPipeline(mock_extractor, mock_transformer, mock_loader)
        
        result = pipeline.run("BTC/USDT", "1h")
        
        assert not result.success
        assert result.error_step == "transformation"
        assert "Transformation failed" in result.error
        assert result.raw_rows == 1
        assert result.transformed_rows == 0
        
        # Vérification que le loader n'est pas appelé
        mock_loader.load.assert_not_called()
    
    def test_pipeline_run_loading_error(self):
        """Test l'échec à l'étape de chargement."""
        mock_extractor = MagicMock(spec=OHLCVExtractor)
        mock_transformer = MagicMock(spec=OHLCVTransformer)
        mock_loader = MagicMock(spec=OHLCVLoader)
        
        raw_data = [[1768294800000, 90000.0, 90100.0, 89900.0, 90050.0, 123.45]]
        df = pd.DataFrame(raw_data, columns=["timestamp", "open", "high", "low", "close", "volume"])
        
        mock_extractor.extract.return_value = raw_data
        mock_transformer.transform.return_value = df
        mock_loader.load.side_effect = LoadingError("Loading failed")
        
        pipeline = ETLPipeline(mock_extractor, mock_transformer, mock_loader)
        
        result = pipeline.run("BTC/USDT", "1h")
        
        assert not result.success
        assert result.error_step == "loading"
        assert "Loading failed" in result.error
        assert result.raw_rows == 1
        assert result.transformed_rows == 1
        assert result.loaded_rows == 0


class TestETLPipelineBatchOperations:
    """Tests pour les opérations en batch."""
    
    def test_pipeline_run_batch_success(self):
        """Test l'exécution batch réussie."""
        mock_extractor = MagicMock(spec=OHLCVExtractor)
        mock_transformer = MagicMock(spec=OHLCVTransformer)
        mock_loader = MagicMock(spec=OHLCVLoader)
        
        raw_data = [[1768294800000, 90000.0, 90100.0, 89900.0, 90050.0, 123.45]]
        df = pd.DataFrame(raw_data, columns=["timestamp", "open", "high", "low", "close", "volume"])
        
        mock_extractor.extract.return_value = raw_data
        mock_transformer.transform.return_value = df
        mock_loader.load.return_value = 1
        
        pipeline = ETLPipeline(mock_extractor, mock_transformer, mock_loader)
        
        symbols = ["BTC/USDT", "ETH/USDT"]
        results = pipeline.run_batch(symbols, "1h")
        
        assert len(results) == 2
        assert all(r.success for r in results.values())
        assert all(r.loaded_rows == 1 for r in results.values())
        
        # Vérification des appels
        assert mock_extractor.extract.call_count == 2
        assert mock_transformer.transform.call_count == 2
        assert mock_loader.load.call_count == 2
    
    def test_pipeline_run_batch_partial_failure(self):
        """Test l'exécution batch avec échec partiel."""
        mock_extractor = MagicMock(spec=OHLCVExtractor)
        mock_transformer = MagicMock(spec=OHLCVTransformer)
        mock_loader = MagicMock(spec=OHLCVLoader)
        
        raw_data = [[1768294800000, 90000.0, 90100.0, 89900.0, 90050.0, 123.45]]
        df = pd.DataFrame(raw_data, columns=["timestamp", "open", "high", "low", "close", "volume"])
        
        # BTC réussit, ETH échoue
        def extract_side_effect(symbol, *args):
            if symbol == "BTC/USDT":
                return raw_data
            else:
                raise ExtractionError("Extraction failed")
        
        mock_extractor.extract.side_effect = extract_side_effect
        mock_transformer.transform.return_value = df
        mock_loader.load.return_value = 1
        
        pipeline = ETLPipeline(mock_extractor, mock_transformer, mock_loader)
        
        symbols = ["BTC/USDT", "ETH/USDT"]
        results = pipeline.run_batch(symbols, "1h")
        
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
        
        raw_data = [[1768294800000, 90000.0, 90100.0, 89900.0, 90050.0, 123.45]]
        df = pd.DataFrame(raw_data, columns=["timestamp", "open", "high", "low", "close", "volume"])
        
        mock_extractor.extract.return_value = raw_data
        mock_transformer.transform.return_value = df
        
        pipeline = ETLPipeline(mock_extractor, mock_transformer, mock_loader)
        
        symbols = ["BTC/USDT", "ETH/USDT"]
        results = pipeline.run_extract_transform_batch(symbols, "1h")
        
        assert len(results) == 2
        assert all(isinstance(r, pd.DataFrame) for r in results.values() if r is not None)
        assert results["BTC/USDT"] is not None
        assert results["ETH/USDT"] is not None


class TestETLPipelineSummary:
    """Tests pour la génération de résumés."""
    
    def test_get_summary_success(self):
        """Test la génération de résumé avec succès."""
        # Créer des résultats mock
        results = {
            "BTC/USDT": self._create_success_result("BTC/USDT", "1h", 100, 95, 95, 1.0, 2.0, 3.0),
            "ETH/USDT": self._create_success_result("ETH/USDT", "1h", 100, 98, 98, 1.5, 2.5, 4.0),
        }
        
        pipeline = ETLPipeline(MagicMock(), MagicMock(), MagicMock())
        summary = pipeline.get_summary(results)
        
        assert summary["total_symbols"] == 2
        assert summary["successful"] == 2
        assert summary["failed"] == 0
        assert summary["success_rate"] == 1.0
        assert summary["total_raw_rows"] == 200
        assert summary["total_transformed_rows"] == 193  # 95 + 98
        assert summary["total_loaded_rows"] == 193  # 95 + 98
        assert summary["total_time"] == 14.0  # 1+2+3 + 1.5+2.5+4
        assert summary["average_time"] == 7.0
        assert "timestamp" in summary
    
    def test_get_summary_partial_failure(self):
        """Test la génération de résumé avec échec partiel."""
        results = {
            "BTC/USDT": self._create_success_result("BTC/USDT", "1h", 100, 95, 95, 1.0, 2.0, 3.0),
            "ETH/USDT": self._create_failed_result("ETH/USDT", "1h", "Transformation error"),
        }
        
        pipeline = ETLPipeline(MagicMock(), MagicMock(), MagicMock())
        summary = pipeline.get_summary(results)
        
        assert summary["total_symbols"] == 2
        assert summary["successful"] == 1
        assert summary["failed"] == 1
        assert summary["success_rate"] == 0.5
    
    def _create_success_result(self, symbol, timeframe, raw_rows, transformed_rows, loaded_rows,
                             extraction_time, transformation_time, loading_time):
        """Crée un résultat réussi pour les tests."""
        result = PipelineResult(symbol, timeframe)
        result.success = True
        result.raw_rows = raw_rows
        result.transformed_rows = transformed_rows
        result.loaded_rows = loaded_rows
        result.extraction_time = extraction_time
        result.transformation_time = transformation_time
        result.loading_time = loading_time
        return result
    
    def _create_failed_result(self, symbol, timeframe, error):
        """Crée un résultat échoué pour les tests."""
        result = PipelineResult(symbol, timeframe)
        result.success = False
        result.error = error
        result.error_step = "transformation"
        return result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])