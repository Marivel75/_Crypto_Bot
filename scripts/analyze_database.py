#!/usr/bin/env python3
"""
Script pour analyser la base de données SQLite avec des visualisations.
"""

import os
import sys
import pandas as pd
import numpy as np
import sqlite3
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

# Configuration des styles
plt.style.use('seaborn')
sns.set_theme(style='whitegrid')
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

def main():
    print("📊 Analyse de la Base de Données Crypto Bot")
    print("=" * 50)
    
    # Chemin vers la base de données
    db_path = 'data/processed/crypto_data.db'
    
    # Vérification que le fichier existe
    if not os.path.exists(db_path):
        print(f"❌ Base de données introuvable: {db_path}")
        print("Veuillez exécuter d'abord: python scripts/test_live_sqlite.py")
        return
    
    print(f"✅ Base de données trouvée: {db_path}")
    
    # Connexion à la base de données
    try:
        conn = sqlite3.connect(db_path)
        print("✅ Connexion établie avec succès")
        
        # Charger les données
        query = "SELECT * FROM ohlcv ORDER BY timestamp DESC LIMIT 1000"
        df = pd.read_sql_query(query, conn)
        
        print(f"📊 {len(df)} enregistrements chargés")
        print(f"Période: {df['timestamp'].min()} à {df['timestamp'].max()}")
        print(f"Symboles: {', '.join(df['symbol'].unique())}")
        print(f"Timeframes: {', '.join(df['timeframe'].unique())}")
        
        # Afficher un échantillon
        print("\n📋 Échantillon de données:")
        print(df.head(10))
        
        # Statistiques descriptives
        print("\n📈 Statistiques descriptives:")
        print(df[['open', 'high', 'low', 'close', 'volume', 'price_change_pct']].describe())
        
        # Visualisation 1: Évolution des prix
        plt.figure(figsize=(14, 7))
        for symbol in df['symbol'].unique():
            df_symbol = df[df['symbol'] == symbol]
            plt.plot(df_symbol['timestamp'], df_symbol['close'], label=symbol, alpha=0.7)
        
        plt.title('Évolution des prix par symbole', fontsize=16)
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('Prix (USD)', fontsize=12)
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig('analysis_price_evolution.png', dpi=150, bbox_inches='tight')
        print("\n✅ Graphique sauvegardé: analysis_price_evolution.png")
        
        # Visualisation 2: Distribution des variations de prix
        plt.figure(figsize=(14, 7))
        sns.boxplot(data=df, x='symbol', y='price_change_pct')
        plt.title('Distribution des variations de prix (%) par symbole', fontsize=16)
        plt.xlabel('Symbole', fontsize=12)
        plt.ylabel('Variation de prix (%)', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig('analysis_price_variation.png', dpi=150, bbox_inches='tight')
        print("✅ Graphique sauvegardé: analysis_price_variation.png")
        
        # Visualisation 3: Volume par symbole
        plt.figure(figsize=(14, 7))
        sns.boxplot(data=df, x='symbol', y='volume')
        plt.title('Distribution des volumes par symbole', fontsize=16)
        plt.xlabel('Symbole', fontsize=12)
        plt.ylabel('Volume', fontsize=12)
        plt.yscale('log')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig('analysis_volume_distribution.png', dpi=150, bbox_inches='tight')
        print("✅ Graphique sauvegardé: analysis_volume_distribution.png")
        
        # Analyse par timeframe
        timeframe_stats = df.groupby('timeframe').agg({
            'volume': ['mean', 'std', 'sum'],
            'price_change_pct': ['mean', 'std', 'min', 'max'],
            'close': ['mean', 'min', 'max']
        }).reset_index()
        
        print("\n📊 Statistiques par timeframe:")
        print(timeframe_stats)
        
        # Analyse de qualité
        print("\n🔍 Analyse de qualité des données:")
        
        # Valeurs manquantes
        missing = df.isnull().sum().sum()
        print(f"Valeurs manquantes: {missing}")
        
        # Prix invalides
        price_issues = ((df['open'] <= 0) | (df['high'] <= 0) | 
                       (df['low'] <= 0) | (df['close'] <= 0)).sum()
        print(f"Prix invalides: {price_issues}")
        
        # Volumes négatifs
        volume_issues = (df['volume'] < 0).sum()
        print(f"Volumes négatifs: {volume_issues}")
        
        # Incohérences high/low
        inconsistent = (df['high'] < df['low']).sum()
        print(f"Incohérences high/low: {inconsistent}")
        
        # Doublons
        duplicates = df.duplicated(subset=['symbol', 'timeframe', 'timestamp']).sum()
        print(f"Doublons: {duplicates} ({duplicates/len(df)*100:.2f}%)")
        
        # Export CSV optionnel
        export_path = 'crypto_data_analysis.csv'
        df.to_csv(export_path, index=False)
        print(f"\n✅ Données exportées: {export_path}")
        
    except Exception as e:
        print(f"❌ Erreur lors de l'analyse: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'conn' in locals():
            conn.close()
        print("\n✅ Analyse terminée et connexion fermée")

if __name__ == "__main__":
    main()