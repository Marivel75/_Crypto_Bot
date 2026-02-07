"""
Tests unitaires pour l'OHLCVLoader. Teste le chargement des données dans la base de données.
"""

import pytest
import sys
import os
import pandas as pd
from unittest.mock import MagicMock, patch, Mock
from sqlalchemy.exc import IntegrityError

# Ajouter le chemin racine au PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.etl.loader import OHLCVLoader, LoadingError


class TestOHLCVLoaderInitialization:
    """Tests pour l'initialisation du chargeur."""
    
    def test_initialization_with_engine(self):
        """Test l'initialisation avec un moteur mock."""
        mock_engine = MagicMock()
        loader = OHLCVLoader(mock_engine)
        
        assert loader.engine == mock_engine
        assert loader.table_name == "ohlcv"
        assert loader.batch_size == 1000
    
    def test_initialization_with_custom_params(self):
        """Test l'initialisation avec des paramètres personnalisés."""
        mock_engine = MagicMock()
        loader = OHLCVLoader(mock_engine, table_name="custom_table", batch_size=500)
        
        assert loader.table_name == "custom_table"
        assert loader.batch_size == 500


class TestOHLCVLoaderLoad:
    """Tests pour la méthode load."""
    
    def test_load_success(self):
        """Test le chargement réussi."""
        mock_engine = MagicMock()
        mock_engine.has_table.return_value = True
        
        # Mock de to_sql pour simuler une insertion réussie
        with patch('pandas.DataFrame.to_sql') as mock_to_sql:
            mock_to_sql.return_value = 2  # 2 lignes insérées
            
            loader = OHLCVLoader(mock_engine)
            df = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
            
            result = loader.load(df)
            
            assert result == 2
            mock_to_sql.assert_called_once()
    
    def test_load_empty_dataframe(self):
        """Test le chargement d'un DataFrame vide."""
        mock_engine = MagicMock()
        loader = OHLCVLoader(mock_engine)
        
        df = pd.DataFrame()
        result = loader.load(df)
        
        assert result == 0
    
    def test_load_with_integrity_error(self):
        """Test le chargement avec un conflit de données."""
        mock_engine = MagicMock()
        
        with patch('pandas.DataFrame.to_sql') as mock_to_sql:
            mock_to_sql.side_effect = IntegrityError("mock", "mock", "Duplicate entry")
            
            loader = OHLCVLoader(mock_engine)
            df = pd.DataFrame({"col1": [1, 2]})
            
            result = loader.load(df)
            
            assert result == 0
    
    def test_load_with_generic_error(self):
        """Test le chargement avec une erreur générique."""
        mock_engine = MagicMock()
        
        with patch('pandas.DataFrame.to_sql') as mock_to_sql:
            mock_to_sql.side_effect = Exception("Connection failed")
            
            loader = OHLCVLoader(mock_engine)
            df = pd.DataFrame({"col1": [1, 2]})
            
            with pytest.raises(LoadingError, match="Échec du chargement"):
                loader.load(df)
    
    def test_load_with_batch_insert(self):
        """Test le chargement avec insertion par batches."""
        mock_engine = MagicMock()
        
        loader = OHLCVLoader(mock_engine, batch_size=500)
        df = pd.DataFrame({"col1": range(1500)})  # > batch_size
        
        with patch.object(loader, '_batch_insert') as mock_batch:
            mock_batch.return_value = 1500
            
            # Mock to_sql to call the original method with our batch insert
            original_to_sql = pd.DataFrame.to_sql
            def mock_to_sql(*args, **kwargs):
                # Call original method but with our mocked batch insert
                if 'method' in kwargs and kwargs['method'] is not None:
                    return kwargs['method'](*args[:-1], **{k: v for k, v in kwargs.items() if k != 'method'})
                return original_to_sql(*args, **kwargs)
            
            with patch('pandas.DataFrame.to_sql', side_effect=mock_to_sql):
                result = loader.load(df)
            
            assert result == 1500
            mock_batch.assert_called_once()





class TestOHLCVLoaderBatchOperations:
    """Tests pour les opérations en batch."""
    
    def test_load_batch_success(self):
        """Test le chargement batch réussi."""
        mock_engine = MagicMock()
        
        with patch('pandas.DataFrame.to_sql') as mock_to_sql:
            mock_to_sql.return_value = 1
            
            loader = OHLCVLoader(mock_engine)
            batch_data = {
                "BTC/USDT": pd.DataFrame({"col1": [1]}),
                "ETH/USDT": pd.DataFrame({"col1": [2]})
            }
            
            results = loader.load_batch(batch_data)
            
            assert len(results) == 2
            assert results["BTC/USDT"] == 1
            assert results["ETH/USDT"] == 1
    
    def test_load_batch_partial_failure(self):
        """Test le chargement batch avec échec partiel."""
        mock_engine = MagicMock()
        
        loader = OHLCVLoader(mock_engine)
        batch_data = {
            "BTC/USDT": pd.DataFrame({"col1": [1]}),
            "ETH/USDT": pd.DataFrame({"col1": [2]})
        }
        
        # Mock du chargement individuel
        with patch.object(loader, 'load') as mock_load:
            # BTC réussit (retourne 1), ETH échoue (lève une exception)
            def load_side_effect(df, if_exists=None):
                if df["col1"].iloc[0] == 1:
                    return 1
                else:
                    raise LoadingError("Database error")
            
            mock_load.side_effect = load_side_effect
            
            results = loader.load_batch(batch_data)
            
            assert len(results) == 2
            assert results["BTC/USDT"] == 1
            assert results["ETH/USDT"] == 0
    
    def test_load_batch_with_none_values(self):
        """Test le chargement batch avec des valeurs None."""
        mock_engine = MagicMock()
        
        loader = OHLCVLoader(mock_engine)
        batch_data = {
            "BTC/USDT": pd.DataFrame({"col1": [1]}),
            "ETH/USDT": None
        }
        
        with patch('pandas.DataFrame.to_sql') as mock_to_sql:
            mock_to_sql.return_value = 1
            
            results = loader.load_batch(batch_data)
            
            assert len(results) == 2
            assert results["BTC/USDT"] == 1
            assert results["ETH/USDT"] == 0
            assert mock_to_sql.call_count == 1  # Seulement BTC chargé


class TestOHLCVLoaderTableOperations:
    """Tests pour les opérations sur les tables."""
    
    def test_table_exists(self):
        """Test la vérification d'existence de table."""
        mock_engine = MagicMock()
        mock_engine.has_table.return_value = True
        
        loader = OHLCVLoader(mock_engine)
        
        assert loader.table_exists()
        mock_engine.has_table.assert_called_once_with("ohlcv")
    
    def test_table_exists_false(self):
        """Test la vérification de non existence de table."""
        mock_engine = MagicMock()
        mock_engine.has_table.return_value = False
        
        loader = OHLCVLoader(mock_engine)
        
        assert not loader.table_exists()
    
    def test_table_exists_error(self):
        """Test la vérification d'existence avec erreur."""
        mock_engine = MagicMock()
        mock_engine.has_table.side_effect = Exception("Connection error")
        
        loader = OHLCVLoader(mock_engine)
        
        assert not loader.table_exists()
    
    def test_get_table_info(self):
        """Test la récupération des informations de table."""
        mock_engine = MagicMock()
        mock_engine.has_table.return_value = True
        
        # Mock de la connexion et de l'inspection
        mock_connection = Mock()
        mock_result = Mock()
        mock_result.keys.return_value = ["col1", "col2", "col3"]
        mock_connection.execute.return_value = mock_result
        mock_engine.connect.return_value.execution_options.return_value.connection = mock_connection
        
        loader = OHLCVLoader(mock_engine)
        
        info = loader.get_table_info()
        
        assert info is not None
        assert info["table"] == "ohlcv"
        assert info["columns"] == ["col1", "col2", "col3"]
        assert info["exists"]
    
    def test_get_table_info_nonexistent(self):
        """Test la récupération des informations pour une table inexistante."""
        mock_engine = MagicMock()
        mock_engine.has_table.return_value = False
        
        loader = OHLCVLoader(mock_engine)
        
        assert loader.get_table_info() is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])