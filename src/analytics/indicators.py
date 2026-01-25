"""
Module pour le calcul des indicateurs techniques.
Ce module contient des fonctions pour calculer divers indicateurs techniques
comme les moyennes mobiles, RSI, MACD, etc.
"""

import pandas as pd
from typing import List, Union
from logger_settings import logger


def calculate_sma(data: Union[pd.DataFrame, List[float]], window: int = 20) -> Union[pd.Series, List[float]]:
    """
    Calcule la Simple Moving Average (SMA) pour une série de données.
    
    Args:
        data: DataFrame pandas avec une colonne 'close' ou une liste de valeurs de clôture
        window: Période pour le calcul de la SMA (par défaut 20)
        
    Returns:
        Série pandas ou liste contenant les valeurs SMA
        
    """
    try:
        # Vérifier le type de données
        if isinstance(data, pd.DataFrame):
            if 'close' not in data.columns:
                raise ValueError("Le DataFrame doit contenir une colonne 'close'")
            close_prices = data['close']
        elif isinstance(data, list):
            close_prices = pd.Series(data)
        else:
            raise TypeError("Type de données non supporté. Utilisez pandas.DataFrame ou list")
        
        # Vérifier que la fenêtre est valide
        if window > len(close_prices):
            raise ValueError(f"La fenêtre ({window}) ne peut pas être supérieure à la longueur des données ({len(close_prices)})")
        
        # Calculer la SMA
        sma = close_prices.rolling(window=window).mean()
        
        # Retourner le résultat dans le même format que l'entrée
        if isinstance(data, pd.DataFrame):
            return sma
        else:
            return sma.tolist()
            
    except Exception as e:
        logger.error(f"Erreur dans le calcul de la SMA: {e}")
        raise


def calculate_rsi(data: Union[pd.DataFrame, List[float]], window: int = 14) -> Union[pd.Series, List[float]]:
    """
    Calcule le Relative Strength Index (RSI) pour une série de données.
    
    Args:
        data: DataFrame pandas avec une colonne 'close' ou une liste de valeurs de clôture
        window: Période pour le calcul du RSI (par défaut 14)
        
    Returns:
        Série pandas ou liste contenant les valeurs RSI
    """
    try:
        # Vérifier le type de données
        if isinstance(data, pd.DataFrame):
            if 'close' not in data.columns:
                raise ValueError("Le DataFrame doit contenir une colonne 'close'")
            close_prices = data['close']
        elif isinstance(data, list):
            close_prices = pd.Series(data)
        else:
            raise TypeError("Type de données non supporté. Utilisez pandas.DataFrame ou list")
        
        # Calculer les variations de prix
        delta = close_prices.diff()
        
        # Séparer les gains et les pertes
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)
        
        # Calculer les moyennes mobiles des gains et pertes
        avg_gain = gains.rolling(window=window).mean()
        avg_loss = losses.rolling(window=window).mean()
        
        # Calculer le Relative Strength (RS)
        rs = avg_gain / avg_loss
        
        # Calculer le RSI
        rsi = 100 - (100 / (1 + rs))
        
        # Retourner le résultat dans le même format que l'entrée
        if isinstance(data, pd.DataFrame):
            return rsi
        else:
            return rsi.tolist()
            
    except Exception as e:
        logger.error(f"Erreur dans le calcul du RSI: {e}")
        raise


def calculate_macd(data: Union[pd.DataFrame, List[float]], fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """
    Calcule le Moving Average Convergence Divergence (MACD) pour une série de données.
    
    Args:
        data: DataFrame pandas avec une colonne 'close' ou une liste de valeurs de clôture
        fast: Période pour la moyenne mobile rapide (par défaut 12)
        slow: Période pour la moyenne mobile lente (par défaut 26)
        signal: Période pour la ligne de signal (par défaut 9)
        
    Returns:
        Dictionnaire contenant les séries MACD, signal et histogramme
    """
    try:
        # Vérifier le type de données
        if isinstance(data, pd.DataFrame):
            if 'close' not in data.columns:
                raise ValueError("Le DataFrame doit contenir une colonne 'close'")
            close_prices = data['close']
        elif isinstance(data, list):
            close_prices = pd.Series(data)
        else:
            raise TypeError("Type de données non supporté. Utilisez pandas.DataFrame ou list")
        
        # Calculer les moyennes mobiles exponentielles
        ema_fast = close_prices.ewm(span=fast, adjust=False).mean()
        ema_slow = close_prices.ewm(span=slow, adjust=False).mean()
        
        # Calculer la ligne MACD
        macd_line = ema_fast - ema_slow
        
        # Calculer la ligne de signal
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        
        # Calculer l'histogramme
        histogram = macd_line - signal_line
        
        # Retourner les résultats
        if isinstance(data, pd.DataFrame):
            return {
                'macd': macd_line,
                'signal': signal_line,
                'histogram': histogram
            }
        else:
            return {
                'macd': macd_line.tolist(),
                'signal': signal_line.tolist(),
                'histogram': histogram.tolist()
            }
            
    except Exception as e:
        logger.error(f"Erreur dans le calcul du MACD: {e}")
        raise