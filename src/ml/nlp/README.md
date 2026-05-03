# Module NLP — Text Mining & Sentiment

Pipeline d'analyse textuelle des news crypto. Enrichit chaque article collecté avec des mots-clés, des entités nommées et une classification par topic.

## Modules

### `text_mining.py`

Analyse d'un article en trois dimensions :

| Fonction | Description | Exemple de sortie |
|---|---|---|
| `extract_keywords(text)` | Top-N mots-clés TF-IDF (unigrammes + bigrammes) | `["etf approved", "sec", "rally"]` |
| `extract_entities(text)` | Cryptos et exchanges détectés | `{"crypto_symbols": ["BTC","ETH"], "exchanges": ["binance"]}` |
| `detect_topics(text)` | Classification par topic(s) | `["regulation", "adoption"]` |
| `analyse_text(text)` | Pipeline complet (les trois) | `{keywords, entities, topics}` |

#### Détection d'entités

Deux mécanismes combinés :
- **Tickers** : détection par expression régulière avec word boundary (`\bBTC\b`, `\bETH\b`…) dans le texte en majuscules
- **Noms complets** : mapping dictionnaire avec word boundary (`"bitcoin"` → `BTC`, `"ethereum"` → `ETH`…)

Symboles couverts (37) : tous les actifs collectés dans l'ETL + top CoinGecko en base.

#### Classification par topic

| Topic | Mots-clés déclencheurs | Couleur UI |
|---|---|---|
| `regulation` | sec, cftc, ban, legal, law, compliance… | Violet |
| `hack_security` | hack, exploit, breach, stolen, attack… | Rouge |
| `adoption` | etf, institutional, partnership, integration… | Vert |
| `defi` | defi, yield, pool, staking, protocol… | Bleu |
| `nft` | nft, marketplace, metaverse, gaming… | Rose |
| `macro` | fed, inflation, recession, gdp, dollar… | Orange |
| `price_action` | ath, rally, crash, pump, correction… | Jaune |
| `general` | (aucun match) | Gris |

Un article peut avoir **plusieurs topics** simultanément (ex: un hack DeFi → `hack_security` + `defi`).

#### Extraction de mots-clés (TF-IDF)

- Vectorisation TF-IDF sur document unique (unigrammes + bigrammes, max 500 features)
- Stop-words anglais supprimés + stop-words crypto spécifiques (`bitcoin`, `ethereum`, `crypto`…)
- Retourne les N termes avec le score TF-IDF le plus élevé

### `sentiment.py` *(à venir)*

`SentimentAnalyzer` — pipeline TF-IDF + Logistic Regression pour un scoring de sentiment [-1, +1]. Nécessite des données d'entraînement labellisées. Le scoring actuel utilise VADER (dictionnaire, pas d'entraînement requis).

## Intégration dans le pipeline

```
RSS feed → NewsCollector._parse_entry()
               ├── VADER → sentiment_score, sentiment_label
               ├── extract_keywords() → keywords
               ├── extract_entities() → entities
               └── detect_topics() → topics
                        ↓
               NewsArticle (SQLite) → API /news → Streamlit page Veille
```

## Tester

```bash
# Test text mining uniquement (pas de réseau)
python scripts/test_nlp.py --offline

# Collecte live + enrichissement en base
python scripts/test_nlp.py

# Affiche les derniers articles enrichis en base
python scripts/test_nlp.py --db
```
