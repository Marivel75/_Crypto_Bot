---
type: catalog
title: "Catalogue UML CryptoBot"
created: 2026-04-15
updated: 2026-04-15
tags: [architecture, plantuml, catalog, snapshot]
---

# Catalogue UML CryptoBot — État actuel

Snapshot figé le 2026-04-15 depuis la branche `dev`. Chaque diagramme est rendu en live par le plugin `obsidian-plantuml`.

## AC01-etl-pipeline
> Explications : [[CryptoBot/avril/architecture/ac01-etl-pipeline]]

```plantuml
@startuml AC01-etl-pipeline
@startuml _common
' ============================================================
' CryptoBot — PlantUML Shared Skin & Stereotypes
' ============================================================

' --- Theme clair (lisible GitHub) ---
skinparam backgroundColor white
skinparam defaultFontName "Segoe UI, Helvetica, Arial, sans-serif"
skinparam defaultFontSize 12
skinparam defaultFontColor #333333
skinparam shadowing false
skinparam roundCorner 6

' --- Palette ---
' Bleu:   #4A6FA5
' Orange: #FEF3E8 (fond) / #E8943A (bordure)
' Vert:   #ECFDF5 (fond) / #34A853 (bordure)
' Violet: #F3EEFF (fond) / #7C5CFC (bordure)
' Gris:   #F5F5F5 (fond) / #CCCCCC (bordure)

' --- Component ---
skinparam component {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
}

' --- Package ---
skinparam package {
  BackgroundColor #F5F5F5
  BorderColor #4A6FA5
  FontColor #333333
}

' --- Class ---
skinparam class {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
  HeaderBackgroundColor #34A853
  HeaderFontColor white
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
  AttributeFontColor #555555
}

' --- Sequence ---
skinparam sequence {
  ArrowColor #4A6FA5
  ActorBorderColor #7C5CFC
  LifeLineBorderColor #CCCCCC
  LifeLineBackgroundColor #F5F5F5
  ParticipantBorderColor #4A6FA5
  ParticipantBackgroundColor #F3EEFF
  ParticipantFontColor #333333
  BoxBorderColor #CCCCCC
  BoxBackgroundColor #F5F5F5
  DividerBackgroundColor #4A6FA5
  DividerFontColor white
}

' --- Activity ---
skinparam activity {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
  DiamondBackgroundColor #F3EEFF
  DiamondBorderColor #7C5CFC
}

' --- Node (deployment) ---
skinparam node {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
}

' --- Database ---
skinparam database {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
}

' --- Entity (ER) ---
skinparam entity {
  BackgroundColor white
  BorderColor #4A6FA5
  FontColor #333333
  HeaderBackgroundColor #4A6FA5
  HeaderFontColor white
}

' --- State ---
skinparam state {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
}

' --- Usecase ---
skinparam usecase {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  ActorBorderColor #E8943A
}

' --- Note ---
skinparam note {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
}

' --- Legend ---
skinparam legend {
  BackgroundColor #F5F5F5
  BorderColor #CCCCCC
  FontColor #333333
}

' --- Stereotypes ---
' <<collector>>   ETL data collectors
' <<transformer>> ETL data transformers
' <<loader>>      ETL data loaders
' <<scheduler>>   APScheduler jobs
' <<rule>>        ML rule evaluator
' <<model>>       ML model
' <<router>>      FastAPI router
' <<service>>     FastAPI service
' <<middleware>>   FastAPI middleware
' <<page>>        Streamlit page
' <<component>>   Streamlit/Plotly component
' <<hypertable>>  TimescaleDB hypertable
' <<phase2>>      Phase 2 planned feature

@enduml


title CryptoBot — Pipeline ETL Complet
caption 10 jobs APScheduler | retry max_attempts=5 | semaphore(5)

|#FEF3E8| Scheduler |
start
fork
  :collect_ohlcv_priority\n**every 1 min**\n13 priority symbols;
fork again
  :collect_ohlcv_all\n**every 5 min**\nall tracked symbols;
fork again
  :collect_market_data\n**every 5 min**\nCoinGecko markets;
fork again
  :collect_news\n**every 15 min**\nRSS feeds;
fork again
  :collect_fear_greed\n**every 1 hour**\nAlternative.me;
end fork

|#F3EEFF| Collection |
:Acquire semaphore (max 5 concurrent);
:Call collector.fetch_*();

if (Success?) then (yes)
  :Return raw records;
else (no)
  :Retry with exponential backoff;
  if (attempts < 5?) then (yes)
    :Wait 2^attempt seconds;
    :Retry fetch;
  else (no)
    :Log CollectorError;
    :Skip this cycle;
    stop
  endif
endif

|#ECFDF5| Transform |
:deduplicate_ohlcv(records);
:validate_ohlcv_relationships();
:filter_valid_records();

if (OHLCV data?) then (yes)
  :compute_rsi(period=14);
  :compute_bollinger_bands(20, 2std);
  :compute_price_vs_bollinger();
  :compute_trend(slope + type);
else (news data?)
  :extract_keywords();
  :compute_sentiment_score();
endif

|#FEF3E8| Load |
fork
  :insert_ohlcv_batch()\nTimescaleDB;
fork again
  :insert_indicators_batch()\nTimescaleDB;
fork again
  :insert_news_batch()\nTimescaleDB;
end fork

|#F5F5F5| Periodic Jobs |
fork
  :compute_indicators\n**every 5 min**;
fork again
  :enrich_news_nlp\n**every 20 min**;
fork again
  :reconciliation\n**every 1 hour**\ndetect & backfill gaps;
fork again
  :evaluate_signal_outcomes\n**every 1 hour**\nP&L at 1h/4h/1d;
fork again
  :export_datasets\n**daily 03:00 UTC**\nParquet to MinIO;
end fork

stop

@enduml
```

## AC02-signal-lifecycle
> Explications : [[CryptoBot/avril/architecture/ac02-signal-lifecycle]]

```plantuml
@startuml AC02-signal-lifecycle
@startuml _common
' ============================================================
' CryptoBot — PlantUML Shared Skin & Stereotypes
' ============================================================

' --- Theme clair (lisible GitHub) ---
skinparam backgroundColor white
skinparam defaultFontName "Segoe UI, Helvetica, Arial, sans-serif"
skinparam defaultFontSize 12
skinparam defaultFontColor #333333
skinparam shadowing false
skinparam roundCorner 6

' --- Palette ---
' Bleu:   #4A6FA5
' Orange: #FEF3E8 (fond) / #E8943A (bordure)
' Vert:   #ECFDF5 (fond) / #34A853 (bordure)
' Violet: #F3EEFF (fond) / #7C5CFC (bordure)
' Gris:   #F5F5F5 (fond) / #CCCCCC (bordure)

' --- Component ---
skinparam component {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
}

' --- Package ---
skinparam package {
  BackgroundColor #F5F5F5
  BorderColor #4A6FA5
  FontColor #333333
}

' --- Class ---
skinparam class {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
  HeaderBackgroundColor #34A853
  HeaderFontColor white
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
  AttributeFontColor #555555
}

' --- Sequence ---
skinparam sequence {
  ArrowColor #4A6FA5
  ActorBorderColor #7C5CFC
  LifeLineBorderColor #CCCCCC
  LifeLineBackgroundColor #F5F5F5
  ParticipantBorderColor #4A6FA5
  ParticipantBackgroundColor #F3EEFF
  ParticipantFontColor #333333
  BoxBorderColor #CCCCCC
  BoxBackgroundColor #F5F5F5
  DividerBackgroundColor #4A6FA5
  DividerFontColor white
}

' --- Activity ---
skinparam activity {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
  DiamondBackgroundColor #F3EEFF
  DiamondBorderColor #7C5CFC
}

' --- Node (deployment) ---
skinparam node {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
}

' --- Database ---
skinparam database {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
}

' --- Entity (ER) ---
skinparam entity {
  BackgroundColor white
  BorderColor #4A6FA5
  FontColor #333333
  HeaderBackgroundColor #4A6FA5
  HeaderFontColor white
}

' --- State ---
skinparam state {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
}

' --- Usecase ---
skinparam usecase {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  ActorBorderColor #E8943A
}

' --- Note ---
skinparam note {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
}

' --- Legend ---
skinparam legend {
  BackgroundColor #F5F5F5
  BorderColor #CCCCCC
  FontColor #333333
}

' --- Stereotypes ---
' <<collector>>   ETL data collectors
' <<transformer>> ETL data transformers
' <<loader>>      ETL data loaders
' <<scheduler>>   APScheduler jobs
' <<rule>>        ML rule evaluator
' <<model>>       ML model
' <<router>>      FastAPI router
' <<service>>     FastAPI service
' <<middleware>>   FastAPI middleware
' <<page>>        Streamlit page
' <<component>>   Streamlit/Plotly component
' <<hypertable>>  TimescaleDB hypertable
' <<phase2>>      Phase 2 planned feature

@enduml


title CryptoBot — Cycle de Vie d'un Signal
caption De l'indicateur a l'evaluation post-hoc

|#FEF3E8| Indicateurs |
start
:Recuperer OHLCV\nmulti-timeframe\n(1h, 2h, 3h, 4h);
:Calculer RSI, Bollinger\nHarmonics, Trend;

|#F3EEFF| Rule Engine |
:RuleEngine.evaluate();
fork
  :RSI evaluator\n(poids 0.25);
fork again
  :Bollinger evaluator\n(poids 0.25);
fork again
  :Harmonic evaluator\n(poids 0.30);
fork again
  :Trend evaluator\n(poids 0.20);
end fork

:Convergence checks\n(RSI+BB, Trend+RSI\nmulti-TF, supermajority);

:RuleEngine.aggregate()\nweighted average\nopposition penalty;

if (rule_confidence >= 0.6?) then (yes)
  :Produce RuleResult[];
else (no)
  :Discard — below threshold;
  stop
endif

|#ECFDF5| ML Blend |
if (Predictor available?) then (yes)
  :ML predict(features);
  if (Same direction?) then (yes)
    :confidence = 0.6*ML + 0.4*rules;
  else (conflict)
    :confidence = 0.4 * min(ML, rules);
  endif
else (rules only)
  :confidence = rule_confidence;
endif

:Sentiment adjustment\n+/- 5 percentage points;
:Clamp [0.0, 0.95];

if (final confidence >= 0.6?) then (yes)
  :Build TradingSignal;
else (no)
  :Discard;
  stop
endif

|#FEF3E8| Validation |
:Suggest leverage (1-20);
:Estimate fees;
:Verify 2x margin safety;
:Check fee/confidence ratio;

if (All gates pass?) then (yes)
  :Persist to trading_signals;
else (no)
  :Discard;
  stop
endif

|#F5F5F5| Post-Hoc Evaluation |
:Wait evaluation windows;
fork
  :Check price_after_1h;
fork again
  :Check price_after_4h;
fork again
  :Check price_after_1d;
end fork

:Compute pnl_simulated;
:Set was_correct (bool);
:Persist SignalOutcome;

stop

@enduml
```

## C01-architecture-macro
> Explications : [[CryptoBot/avril/architecture/c01-macro]]

```plantuml
@startuml C01-architecture-macro
@startuml _common
' ============================================================
' CryptoBot — PlantUML Shared Skin & Stereotypes
' ============================================================

' --- Theme clair (lisible GitHub) ---
skinparam backgroundColor white
skinparam defaultFontName "Segoe UI, Helvetica, Arial, sans-serif"
skinparam defaultFontSize 12
skinparam defaultFontColor #333333
skinparam shadowing false
skinparam roundCorner 6

' --- Palette ---
' Bleu:   #4A6FA5
' Orange: #FEF3E8 (fond) / #E8943A (bordure)
' Vert:   #ECFDF5 (fond) / #34A853 (bordure)
' Violet: #F3EEFF (fond) / #7C5CFC (bordure)
' Gris:   #F5F5F5 (fond) / #CCCCCC (bordure)

' --- Component ---
skinparam component {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
}

' --- Package ---
skinparam package {
  BackgroundColor #F5F5F5
  BorderColor #4A6FA5
  FontColor #333333
}

' --- Class ---
skinparam class {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
  HeaderBackgroundColor #34A853
  HeaderFontColor white
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
  AttributeFontColor #555555
}

' --- Sequence ---
skinparam sequence {
  ArrowColor #4A6FA5
  ActorBorderColor #7C5CFC
  LifeLineBorderColor #CCCCCC
  LifeLineBackgroundColor #F5F5F5
  ParticipantBorderColor #4A6FA5
  ParticipantBackgroundColor #F3EEFF
  ParticipantFontColor #333333
  BoxBorderColor #CCCCCC
  BoxBackgroundColor #F5F5F5
  DividerBackgroundColor #4A6FA5
  DividerFontColor white
}

' --- Activity ---
skinparam activity {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
  DiamondBackgroundColor #F3EEFF
  DiamondBorderColor #7C5CFC
}

' --- Node (deployment) ---
skinparam node {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
}

' --- Database ---
skinparam database {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
}

' --- Entity (ER) ---
skinparam entity {
  BackgroundColor white
  BorderColor #4A6FA5
  FontColor #333333
  HeaderBackgroundColor #4A6FA5
  HeaderFontColor white
}

' --- State ---
skinparam state {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
}

' --- Usecase ---
skinparam usecase {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  ActorBorderColor #E8943A
}

' --- Note ---
skinparam note {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
}

' --- Legend ---
skinparam legend {
  BackgroundColor #F5F5F5
  BorderColor #CCCCCC
  FontColor #333333
}

' --- Stereotypes ---
' <<collector>>   ETL data collectors
' <<transformer>> ETL data transformers
' <<loader>>      ETL data loaders
' <<scheduler>>   APScheduler jobs
' <<rule>>        ML rule evaluator
' <<model>>       ML model
' <<router>>      FastAPI router
' <<service>>     FastAPI service
' <<middleware>>   FastAPI middleware
' <<page>>        Streamlit page
' <<component>>   Streamlit/Plotly component
' <<hypertable>>  TimescaleDB hypertable
' <<phase2>>      Phase 2 planned feature

@enduml


title CryptoBot — Architecture Systeme Globale
caption Phase 1 (actuelle) + Phase 2 (planifiee)

' ============================================================
' Data Sources (external)
' ============================================================
cloud "Sources de Donnees" as sources #F5F5F5 {
  [Binance\nREST + WebSocket] as binance <<collector>>
  [CoinGecko\nDemo API] as coingecko <<collector>>
  [CCXT\nMulti-exchange] as ccxt <<collector>>
  [News RSS\nDecrypt, Cointelegraph\nPhoenixNews] as rss <<collector>>
  [Alternative.me\nFear & Greed Index] as fng <<collector>>
  [ESMA / SEC\nRegulatory] as regulatory <<collector>>
}

' ============================================================
' ETL Pipeline
' ============================================================
package "ETL Pipeline" as etl #FEF3E8 {
  [Collectors\n6 sources] as collectors <<scheduler>>
  [Transformers\nIndicateurs techniques\nNettoyage] as transformers <<transformer>>
  [Loaders\nTimescaleDB + MinIO] as loaders <<loader>>
  [APScheduler\n10 jobs recurrents] as scheduler <<scheduler>>
}

' ============================================================
' Storage Layer
' ============================================================
package "Stockage" as storage #ECFDF5 {
  database "TimescaleDB\nHypertables OHLCV\nIndicateurs, Signaux\nNews, Users" as tsdb <<hypertable>>
  database "MinIO\nS3-compatible\nDatasets, Modeles\nArtifacts MLflow" as minio
}

' ============================================================
' ML Engine
' ============================================================
package "ML Engine" as ml #F3EEFF {
  [Rule Engine\nRSI, Bollinger\nHarmonics, Trends\nConvergence multi-TF] as rules <<rule>>
  [Signal Generator\nAggregation ponderee\nML blend 60/40\nValidation seuils] as siggen
  [NLP / Sentiment\nTF-IDF, NLTK\nScoring articles] as nlp <<model>>

  package "Phase 2" <<phase2>> #white {
    [Supervised ML\nXGBoost, LightGBM\nLSTM] as supml <<phase2>>
    [MLflow\nExperiment tracking\nModel registry] as mlflow <<phase2>>
    [DVC\nDataset versioning] as dvc <<phase2>>
    [RL Agents\nPaper Trading] as rl <<phase2>>
  }
}

' ============================================================
' Backend API
' ============================================================
package "Backend API" as api #FEF3E8 {
  [FastAPI\n/api/v1/*\n8 routers] as fastapi <<router>>
  [Auth Service\nJWT HS256\nbcrypt] as auth <<service>>
  [Middleware\nRate Limiting\nRequest ID\nCORS] as middleware <<middleware>>
}

' ============================================================
' Frontend
' ============================================================
package "Frontend" as frontend #F3EEFF {
  [Streamlit\n5 pages] as streamlit <<page>>
  [Plotly\nCandlestick, Heatmaps\nCorrelations] as plotly <<component>>
  [Chatbot IA\nAssistant integre] as chatbot <<component>>
  [i18n\nFR / EN] as i18n <<component>>
}

' ============================================================
' Infrastructure
' ============================================================
package "Infrastructure" as infra #F5F5F5 {
  [Nginx\nReverse proxy\nSSL Let's Encrypt] as nginx
  [Docker Compose\n12 services] as docker
  [GitHub Actions\nCI/CD] as ci
  [Grafana + Prometheus\nMonitoring] as monitoring
}

' ============================================================
' Personas
' ============================================================
actor "Noah\nTrader" as noah
actor "Sarah\nJournaliste" as sarah
actor "Aleksandar\nDebutant" as aleksandar

' ============================================================
' Relations — Data Flow
' ============================================================
sources -down-> collectors : donnees brutes
collectors -right-> transformers : donnees collectees
transformers -right-> loaders : donnees transformees
scheduler .down.> collectors : declenche
loaders -down-> tsdb : OHLCV, indicateurs
loaders -down-> minio : parquet, artifacts

' ML reads from storage
tsdb -right-> rules : indicateurs
tsdb -right-> nlp : articles
rules -down-> siggen : scores par regle
nlp -down-> siggen : sentiment
supml -up-> siggen : predictions ML
siggen -left-> tsdb : signaux persistes

' MLflow/DVC
minio <.right.> mlflow : artifacts
minio <.right.> dvc : datasets

' API reads from storage + ML
tsdb -down-> fastapi : donnees + signaux
fastapi -left-> auth : authentification
fastapi -left-> middleware : filtrage

' Frontend calls API
streamlit -up-> fastapi : REST /api/v1/*
plotly -[hidden]up-> streamlit
chatbot -[hidden]up-> streamlit

' Infra
nginx -down-> streamlit : port 8501
nginx -down-> fastapi : port 8000
docker ..> infra : orchestre tout

' Personas access
noah -down-> nginx : HTTPS
sarah -down-> nginx : HTTPS
aleksandar -down-> nginx : HTTPS

' ============================================================
' Legend
' ============================================================
legend bottom right
  |= Couleur |= Signification |
  | <#FEF3E8> | Pipeline / API |
  | <#ECFDF5> | Stockage |
  | <#F3EEFF> | ML / Frontend |
  | <#white> | Phase 2 (planifie) |
endlegend

@enduml
```

## C02-etl-components
> Explications : [[CryptoBot/avril/architecture/c02-etl-components]]

```plantuml
@startuml C02-etl-components
@startuml _common
' ============================================================
' CryptoBot — PlantUML Shared Skin & Stereotypes
' ============================================================

' --- Theme clair (lisible GitHub) ---
skinparam backgroundColor white
skinparam defaultFontName "Segoe UI, Helvetica, Arial, sans-serif"
skinparam defaultFontSize 12
skinparam defaultFontColor #333333
skinparam shadowing false
skinparam roundCorner 6

' --- Palette ---
' Bleu:   #4A6FA5
' Orange: #FEF3E8 (fond) / #E8943A (bordure)
' Vert:   #ECFDF5 (fond) / #34A853 (bordure)
' Violet: #F3EEFF (fond) / #7C5CFC (bordure)
' Gris:   #F5F5F5 (fond) / #CCCCCC (bordure)

' --- Component ---
skinparam component {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
}

' --- Package ---
skinparam package {
  BackgroundColor #F5F5F5
  BorderColor #4A6FA5
  FontColor #333333
}

' --- Class ---
skinparam class {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
  HeaderBackgroundColor #34A853
  HeaderFontColor white
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
  AttributeFontColor #555555
}

' --- Sequence ---
skinparam sequence {
  ArrowColor #4A6FA5
  ActorBorderColor #7C5CFC
  LifeLineBorderColor #CCCCCC
  LifeLineBackgroundColor #F5F5F5
  ParticipantBorderColor #4A6FA5
  ParticipantBackgroundColor #F3EEFF
  ParticipantFontColor #333333
  BoxBorderColor #CCCCCC
  BoxBackgroundColor #F5F5F5
  DividerBackgroundColor #4A6FA5
  DividerFontColor white
}

' --- Activity ---
skinparam activity {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
  DiamondBackgroundColor #F3EEFF
  DiamondBorderColor #7C5CFC
}

' --- Node (deployment) ---
skinparam node {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
}

' --- Database ---
skinparam database {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
}

' --- Entity (ER) ---
skinparam entity {
  BackgroundColor white
  BorderColor #4A6FA5
  FontColor #333333
  HeaderBackgroundColor #4A6FA5
  HeaderFontColor white
}

' --- State ---
skinparam state {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
}

' --- Usecase ---
skinparam usecase {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  ActorBorderColor #E8943A
}

' --- Note ---
skinparam note {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
}

' --- Legend ---
skinparam legend {
  BackgroundColor #F5F5F5
  BorderColor #CCCCCC
  FontColor #333333
}

' --- Stereotypes ---
' <<collector>>   ETL data collectors
' <<transformer>> ETL data transformers
' <<loader>>      ETL data loaders
' <<scheduler>>   APScheduler jobs
' <<rule>>        ML rule evaluator
' <<model>>       ML model
' <<router>>      FastAPI router
' <<service>>     FastAPI service
' <<middleware>>   FastAPI middleware
' <<page>>        Streamlit page
' <<component>>   Streamlit/Plotly component
' <<hypertable>>  TimescaleDB hypertable
' <<phase2>>      Phase 2 planned feature

@enduml


title CryptoBot — Sous-systeme ETL
caption src/etl/ | 5 collectors, 2 transformers, 2 loaders, 10 jobs

' ============================================================
' Collectors
' ============================================================
package "Collectors" as coll #FEF3E8 {
  [BinanceCollector\nREST + WebSocket\nfetch_ohlcv(symbols, tf, limit)] as binance <<collector>>
  [CoinGeckoCollector\nDemo API\nfetch_market_data(symbols)] as coingecko <<collector>>
  [CCXTCollector\nMulti-exchange\nfetch_ohlcv(symbol, tf)] as ccxt <<collector>>
  [NewsCollector\nRSS: Decrypt, Cointelegraph\nfetch_news(sources, keywords)] as news <<collector>>
  [FearGreedCollector\nAlternative.me\nfetch_fear_greed()] as fng <<collector>>
}

' ============================================================
' Transformers
' ============================================================
package "Transformers" as trans #F3EEFF {
  [cleaner.py\ndeduplicate_ohlcv()\nvalidate_ohlcv_relationships()\nfilter_valid_records()\ndetect_gaps()] as cleaner <<transformer>>
  [indicators.py\ncompute_rsi(period=14)\ncompute_bollinger_bands(20, 2std)\ncompute_price_vs_bollinger()\ncompute_trend(slope + type)] as indicators <<transformer>>
}

' ============================================================
' Loaders
' ============================================================
package "Loaders" as load #ECFDF5 {
  [timescaledb.py\ninsert_ohlcv_batch()\ninsert_indicators_batch()\ninsert_news_batch()\nfetch_ohlcv_for_indicators()\ndetect_gaps()] as tsloader <<loader>>
  [minio_loader.py\nupload_ohlcv_parquet()\nupload_dataset_parquet()\nupload_raw_json()\ndownload_dataframe()] as minloader <<loader>>
}

' ============================================================
' Scheduler
' ============================================================
package "APScheduler (10 jobs)" as sched #F5F5F5 {
  [collect_ohlcv_priority\n1 min | 13 symbols] as j1 <<scheduler>>
  [collect_ohlcv_all\n5 min | all symbols] as j2 <<scheduler>>
  [collect_market_data\n5 min | CoinGecko] as j3 <<scheduler>>
  [collect_news\n15 min | RSS feeds] as j4 <<scheduler>>
  [enrich_news_nlp\n20 min | sentiment] as j5 <<scheduler>>
  [collect_fear_greed\n1 hour] as j6 <<scheduler>>
  [compute_indicators\n5 min | RSI, BB, trend] as j7 <<scheduler>>
  [export_datasets\ndaily 03:00 UTC] as j8 <<scheduler>>
  [reconciliation\n1 hour | gap detection] as j9 <<scheduler>>
  [evaluate_signal_outcomes\n1 hour | P&L check] as j10 <<scheduler>>
}

' ============================================================
' Storage
' ============================================================
database "TimescaleDB" as tsdb #ECFDF5
database "MinIO" as minio #ECFDF5

' ============================================================
' Relations
' ============================================================
' Scheduler triggers collectors
j1 --> binance
j2 --> binance
j2 --> ccxt
j3 --> coingecko
j4 --> news
j6 --> fng

' Collectors to transformers
binance --> cleaner : raw OHLCV
ccxt --> cleaner : raw OHLCV
coingecko --> cleaner : market data
news --> cleaner : articles

' Transformers to loaders
cleaner --> tsloader : clean records
cleaner --> indicators : valid OHLCV
j7 --> indicators
indicators --> tsloader : IndicatorRecord

' Loaders to storage
tsloader --> tsdb
minloader --> minio
j8 --> minloader : daily export

' Reconciliation
j9 --> tsloader : gap backfill
j10 --> tsloader : signal evaluation

@enduml
```

## C03-ml-components
> Explications : [[CryptoBot/avril/architecture/c03-ml-components]]

```plantuml
@startuml C03-ml-components
@startuml _common
' ============================================================
' CryptoBot — PlantUML Shared Skin & Stereotypes
' ============================================================

' --- Theme clair (lisible GitHub) ---
skinparam backgroundColor white
skinparam defaultFontName "Segoe UI, Helvetica, Arial, sans-serif"
skinparam defaultFontSize 12
skinparam defaultFontColor #333333
skinparam shadowing false
skinparam roundCorner 6

' --- Palette ---
' Bleu:   #4A6FA5
' Orange: #FEF3E8 (fond) / #E8943A (bordure)
' Vert:   #ECFDF5 (fond) / #34A853 (bordure)
' Violet: #F3EEFF (fond) / #7C5CFC (bordure)
' Gris:   #F5F5F5 (fond) / #CCCCCC (bordure)

' --- Component ---
skinparam component {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
}

' --- Package ---
skinparam package {
  BackgroundColor #F5F5F5
  BorderColor #4A6FA5
  FontColor #333333
}

' --- Class ---
skinparam class {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
  HeaderBackgroundColor #34A853
  HeaderFontColor white
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
  AttributeFontColor #555555
}

' --- Sequence ---
skinparam sequence {
  ArrowColor #4A6FA5
  ActorBorderColor #7C5CFC
  LifeLineBorderColor #CCCCCC
  LifeLineBackgroundColor #F5F5F5
  ParticipantBorderColor #4A6FA5
  ParticipantBackgroundColor #F3EEFF
  ParticipantFontColor #333333
  BoxBorderColor #CCCCCC
  BoxBackgroundColor #F5F5F5
  DividerBackgroundColor #4A6FA5
  DividerFontColor white
}

' --- Activity ---
skinparam activity {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
  DiamondBackgroundColor #F3EEFF
  DiamondBorderColor #7C5CFC
}

' --- Node (deployment) ---
skinparam node {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
}

' --- Database ---
skinparam database {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
}

' --- Entity (ER) ---
skinparam entity {
  BackgroundColor white
  BorderColor #4A6FA5
  FontColor #333333
  HeaderBackgroundColor #4A6FA5
  HeaderFontColor white
}

' --- State ---
skinparam state {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
}

' --- Usecase ---
skinparam usecase {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  ActorBorderColor #E8943A
}

' --- Note ---
skinparam note {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
}

' --- Legend ---
skinparam legend {
  BackgroundColor #F5F5F5
  BorderColor #CCCCCC
  FontColor #333333
}

' --- Stereotypes ---
' <<collector>>   ETL data collectors
' <<transformer>> ETL data transformers
' <<loader>>      ETL data loaders
' <<scheduler>>   APScheduler jobs
' <<rule>>        ML rule evaluator
' <<model>>       ML model
' <<router>>      FastAPI router
' <<service>>     FastAPI service
' <<middleware>>   FastAPI middleware
' <<page>>        Streamlit page
' <<component>>   Streamlit/Plotly component
' <<hypertable>>  TimescaleDB hypertable
' <<phase2>>      Phase 2 planned feature

@enduml


title CryptoBot — Sous-systeme ML
caption src/ml/ | Phase 1 (rules) + Phase 2 (supervised)

' ============================================================
' Phase 1 — Rule Engine
' ============================================================
package "Phase 1 — Rule Engine" as p1 #F3EEFF {

  package "rules/" #white {
    [RuleEngine\nfrom_yaml(config)\nevaluate(symbol, indicators)\naggregate(results)] as engine <<rule>>
    [RSI Evaluator\noverbought/oversold\nmulti-TF convergence] as rsi <<rule>>
    [Bollinger Evaluator\nsqueeze detection\nband reversal] as boll <<rule>>
    [Harmonic Evaluator\nGartley, Butterfly\nCrab, XAB=CD] as harm <<rule>>
    [Trend Evaluator\nslope + type\nweekly/monthly] as trend <<rule>>
    [Convergence Evaluators\nRSI+BB, Trend+RSI\nmulti-TF alignment\nsupermajority] as conv <<rule>>
  }

  [SignalGenerator\nML blend 60/40\nsentiment +/-5pp\nthreshold >= 0.6] as siggen

  [NLP / Sentiment\nTF-IDF, NLTK\nkeyword extraction\nsentiment scoring] as nlp <<model>>
}

' ============================================================
' Phase 2 — Supervised ML
' ============================================================
package "Phase 2 — Supervised ML" <<phase2>> #FEF3E8 {
  [Trainer\nXGBoost, LightGBM\nwalk-forward CV\npurge + embargo] as trainer <<phase2>>
  [FeatureBuilder\nRSI by TF, BB position\nsqueeze width, trend slope\nvolume, Fear&Greed] as features <<phase2>>
  [Predictor\npredict(features)\nmodel_version] as predictor <<phase2>>
  [LSTM\ndeep learning\nsequence prediction] as lstm <<phase2>>
  [Backtester\n6-month train\n1-month test\ntemporal splits] as backtester <<phase2>>
}

' ============================================================
' MLOps
' ============================================================
package "MLOps" #ECFDF5 {
  [MLflow\nexperiment tracking\nmodel registry\nStaging -> Production] as mlflow
  [DVC\ndataset versioning\nMinIO backend] as dvc
}

' ============================================================
' Config
' ============================================================
artifact "indicators.yaml\nperiods, thresholds\ntimeframes" as config #F5F5F5

' ============================================================
' Storage
' ============================================================
database "TimescaleDB" as tsdb #ECFDF5
database "MinIO" as minio #ECFDF5

' ============================================================
' Relations
' ============================================================
' Rule engine flow
config --> engine
engine --> rsi
engine --> boll
engine --> harm
engine --> trend
engine --> conv
engine --> siggen : RuleResult[]

' NLP
nlp --> siggen : sentiment score

' Signal generator
siggen --> tsdb : persist signals

' Phase 2 flow
features --> trainer : feature matrix
trainer --> mlflow : log experiments
trainer --> predictor : trained model
predictor --> siggen : ML predictions
lstm --> trainer : DL model
backtester --> trainer : validation

' MLOps
mlflow --> minio : artifacts
dvc --> minio : datasets
tsdb --> features : raw data

@enduml
```

## C04-api-components
> Explications : [[CryptoBot/avril/architecture/c04-api-components]]

```plantuml
@startuml C04-api-components
@startuml _common
' ============================================================
' CryptoBot — PlantUML Shared Skin & Stereotypes
' ============================================================

' --- Theme clair (lisible GitHub) ---
skinparam backgroundColor white
skinparam defaultFontName "Segoe UI, Helvetica, Arial, sans-serif"
skinparam defaultFontSize 12
skinparam defaultFontColor #333333
skinparam shadowing false
skinparam roundCorner 6

' --- Palette ---
' Bleu:   #4A6FA5
' Orange: #FEF3E8 (fond) / #E8943A (bordure)
' Vert:   #ECFDF5 (fond) / #34A853 (bordure)
' Violet: #F3EEFF (fond) / #7C5CFC (bordure)
' Gris:   #F5F5F5 (fond) / #CCCCCC (bordure)

' --- Component ---
skinparam component {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
}

' --- Package ---
skinparam package {
  BackgroundColor #F5F5F5
  BorderColor #4A6FA5
  FontColor #333333
}

' --- Class ---
skinparam class {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
  HeaderBackgroundColor #34A853
  HeaderFontColor white
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
  AttributeFontColor #555555
}

' --- Sequence ---
skinparam sequence {
  ArrowColor #4A6FA5
  ActorBorderColor #7C5CFC
  LifeLineBorderColor #CCCCCC
  LifeLineBackgroundColor #F5F5F5
  ParticipantBorderColor #4A6FA5
  ParticipantBackgroundColor #F3EEFF
  ParticipantFontColor #333333
  BoxBorderColor #CCCCCC
  BoxBackgroundColor #F5F5F5
  DividerBackgroundColor #4A6FA5
  DividerFontColor white
}

' --- Activity ---
skinparam activity {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
  DiamondBackgroundColor #F3EEFF
  DiamondBorderColor #7C5CFC
}

' --- Node (deployment) ---
skinparam node {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
}

' --- Database ---
skinparam database {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
}

' --- Entity (ER) ---
skinparam entity {
  BackgroundColor white
  BorderColor #4A6FA5
  FontColor #333333
  HeaderBackgroundColor #4A6FA5
  HeaderFontColor white
}

' --- State ---
skinparam state {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
}

' --- Usecase ---
skinparam usecase {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  ActorBorderColor #E8943A
}

' --- Note ---
skinparam note {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
}

' --- Legend ---
skinparam legend {
  BackgroundColor #F5F5F5
  BorderColor #CCCCCC
  FontColor #333333
}

' --- Stereotypes ---
' <<collector>>   ETL data collectors
' <<transformer>> ETL data transformers
' <<loader>>      ETL data loaders
' <<scheduler>>   APScheduler jobs
' <<rule>>        ML rule evaluator
' <<model>>       ML model
' <<router>>      FastAPI router
' <<service>>     FastAPI service
' <<middleware>>   FastAPI middleware
' <<page>>        Streamlit page
' <<component>>   Streamlit/Plotly component
' <<hypertable>>  TimescaleDB hypertable
' <<phase2>>      Phase 2 planned feature

@enduml


title CryptoBot — FastAPI Backend
caption src/api/ | 8 routers, 7 services, 2 middleware

' ============================================================
' Middleware
' ============================================================
package "Middleware" #F5F5F5 {
  [RateLimitHeadersMiddleware\n30 req/s default\n5 req/min auth\nX-RateLimit-* headers] as ratelimit <<middleware>>
  [RequestIdMiddleware\nX-Request-Id header\nper-IP tracking] as reqid <<middleware>>
  [CORS\nallow_origins from settings] as cors <<middleware>>
}

' ============================================================
' Routers (8)
' ============================================================
package "Routers" #FEF3E8 {
  [auth\n/api/v1/auth\nPOST register\nPOST login\nGET me] as r_auth <<router>>

  [crypto\n/api/v1/crypto\nGET list\nGET market-overview\nGET {symbol}/prices\nGET {symbol}/indicators\nGET {symbol}/latest] as r_crypto <<router>>

  [signals\n/api/v1/signals\nGET active\nGET performance\nGET {id}/detail\nGET {symbol}] as r_signals <<router>>

  [news\n/api/v1/news\nGET latest\nGET sentiment\nGET {id}] as r_news <<router>>

  [portfolio\n/api/v1/portfolio\nGET, POST\nPUT {id}, DELETE {id}] as r_port <<router>>

  [watchlist\n/api/v1/watchlist\nGET, POST\nDELETE {symbol}] as r_watch <<router>>

  [chat\n/api/v1/chat\nPOST message] as r_chat <<router>>

  [system\n/health\n/api/v1/system/sources-status] as r_sys <<router>>
}

' ============================================================
' Services (7)
' ============================================================
package "Services" #F3EEFF {
  [auth_service\nhash_password (bcrypt)\nverify_password\ncreate_access_token (JWT HS256)\ndecode_access_token\nregister, authenticate] as s_auth <<service>>

  [crypto_service\nlist_tracked()\nget_prices()\nget_indicators()\nget_latest()\nget_market_overview()] as s_crypto <<service>>

  [signal_service\nget_active()\nget_by_symbol()\nget_detail()\nget_performance()] as s_signal <<service>>

  [news_service\nget_latest()\nget_by_id()\nget_sentiment()] as s_news <<service>>

  [user_data_service\nget/add/update/delete\nportfolio + watchlist] as s_user <<service>>

  [chat_service\nLLM integration] as s_chat <<service>>
}

' ============================================================
' Dependencies
' ============================================================
package "Dependencies" #ECFDF5 {
  [get_db()\nAsyncSession yield] as dep_db
  [get_current_user()\nJWT decode + fetch user] as dep_user
}

' ============================================================
' Storage
' ============================================================
database "TimescaleDB" as tsdb #ECFDF5

' ============================================================
' Relations
' ============================================================
' Middleware chain
ratelimit --> reqid
reqid --> cors

' Router -> Service
r_auth --> s_auth
r_crypto --> s_crypto
r_signals --> s_signal
r_news --> s_news
r_port --> s_user
r_watch --> s_user
r_chat --> s_chat
r_sys --> dep_db

' Auth dependency
r_auth --> dep_user
r_port --> dep_user
r_watch --> dep_user

' Service -> DB
s_auth --> dep_db
s_crypto --> dep_db
s_signal --> dep_db
s_news --> dep_db
s_user --> dep_db
dep_db --> tsdb

@enduml
```

## C05-frontend-components
> Explications : [[CryptoBot/avril/architecture/c05-frontend-components]]

```plantuml
@startuml C05-frontend-components
@startuml _common
' ============================================================
' CryptoBot — PlantUML Shared Skin & Stereotypes
' ============================================================

' --- Theme clair (lisible GitHub) ---
skinparam backgroundColor white
skinparam defaultFontName "Segoe UI, Helvetica, Arial, sans-serif"
skinparam defaultFontSize 12
skinparam defaultFontColor #333333
skinparam shadowing false
skinparam roundCorner 6

' --- Palette ---
' Bleu:   #4A6FA5
' Orange: #FEF3E8 (fond) / #E8943A (bordure)
' Vert:   #ECFDF5 (fond) / #34A853 (bordure)
' Violet: #F3EEFF (fond) / #7C5CFC (bordure)
' Gris:   #F5F5F5 (fond) / #CCCCCC (bordure)

' --- Component ---
skinparam component {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
}

' --- Package ---
skinparam package {
  BackgroundColor #F5F5F5
  BorderColor #4A6FA5
  FontColor #333333
}

' --- Class ---
skinparam class {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
  HeaderBackgroundColor #34A853
  HeaderFontColor white
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
  AttributeFontColor #555555
}

' --- Sequence ---
skinparam sequence {
  ArrowColor #4A6FA5
  ActorBorderColor #7C5CFC
  LifeLineBorderColor #CCCCCC
  LifeLineBackgroundColor #F5F5F5
  ParticipantBorderColor #4A6FA5
  ParticipantBackgroundColor #F3EEFF
  ParticipantFontColor #333333
  BoxBorderColor #CCCCCC
  BoxBackgroundColor #F5F5F5
  DividerBackgroundColor #4A6FA5
  DividerFontColor white
}

' --- Activity ---
skinparam activity {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
  DiamondBackgroundColor #F3EEFF
  DiamondBorderColor #7C5CFC
}

' --- Node (deployment) ---
skinparam node {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
}

' --- Database ---
skinparam database {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
}

' --- Entity (ER) ---
skinparam entity {
  BackgroundColor white
  BorderColor #4A6FA5
  FontColor #333333
  HeaderBackgroundColor #4A6FA5
  HeaderFontColor white
}

' --- State ---
skinparam state {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
}

' --- Usecase ---
skinparam usecase {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  ActorBorderColor #E8943A
}

' --- Note ---
skinparam note {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
}

' --- Legend ---
skinparam legend {
  BackgroundColor #F5F5F5
  BorderColor #CCCCCC
  FontColor #333333
}

' --- Stereotypes ---
' <<collector>>   ETL data collectors
' <<transformer>> ETL data transformers
' <<loader>>      ETL data loaders
' <<scheduler>>   APScheduler jobs
' <<rule>>        ML rule evaluator
' <<model>>       ML model
' <<router>>      FastAPI router
' <<service>>     FastAPI service
' <<middleware>>   FastAPI middleware
' <<page>>        Streamlit page
' <<component>>   Streamlit/Plotly component
' <<hypertable>>  TimescaleDB hypertable
' <<phase2>>      Phase 2 planned feature

@enduml


title CryptoBot — Frontend Streamlit
caption src/frontend/ | 5 pages, 5 composants, i18n FR/EN

' ============================================================
' Personas
' ============================================================
actor "Noah\nTrader" as noah
actor "Sarah\nJournaliste" as sarah
actor "Aleksandar\nDebutant" as aleksandar

' ============================================================
' Pages
' ============================================================
package "Pages" #FEF3E8 {
  [Dashboard\nCandlestick multi-TF\nIndicateurs, signaux\nAlertes temps reel] as p_dash <<page>>
  [Veille\nNews feed\nSentiment analysis\nAlertes reglementaires] as p_veille <<page>>
  [Portfolio\nPosition tracking\nP&L calcul\nChatbot IA] as p_portfolio <<page>>
  [Analytics\nHeatmaps correlations\nMarket microstructure\nVolume analysis] as p_analytics <<page>>
  [Performance\nHistorique signaux\nWin rate, Sharpe\nRendement simule] as p_perf <<page>>
}

' ============================================================
' Components
' ============================================================
package "Composants Plotly" #F3EEFF {
  [CandlestickChart\nmulti-timeframe\nindicators overlay] as c_candle <<component>>
  [SignalCard\ndirection, confidence\nleverage, fees] as c_signal <<component>>
  [NewsFeed\nsource, sentiment\nkeywords highlight] as c_news <<component>>
  [IndicatorPanel\nRSI, Bollinger\ntrend, harmonics] as c_indic <<component>>
  [ChatbotWidget\nmessage input\nLLM response\ndisclaimer] as c_chat <<component>>
}

' ============================================================
' API Client
' ============================================================
package "Infra" #ECFDF5 {
  [APIClient\nbase_url: /api/v1\nget/post/put/delete\nerror handling] as api_client
  [i18n\nFR / EN\nlabels, messages] as i18n
}

' ============================================================
' Backend
' ============================================================
node "FastAPI\n/api/v1/*" as fastapi #F5F5F5

' ============================================================
' Relations — Personas -> Pages
' ============================================================
noah --> p_dash : signaux, charts
noah --> p_analytics : correlations
sarah --> p_veille : news, regulatory
sarah --> p_analytics : heatmaps
aleksandar --> p_portfolio : chatbot, P&L
aleksandar --> p_perf : historique

' Pages -> Components
p_dash --> c_candle
p_dash --> c_signal
p_dash --> c_indic
p_veille --> c_news
p_portfolio --> c_chat
p_perf --> c_signal

' Components -> APIClient
c_candle --> api_client
c_signal --> api_client
c_news --> api_client
c_chat --> api_client
c_indic --> api_client

' APIClient -> Backend
api_client --> fastapi : REST HTTP

@enduml
```

## C06-phase2-ml-pipeline
> Explications : [[CryptoBot/avril/architecture/c06-phase2-ml-pipeline]]

```plantuml
@startuml C06-phase2-ml-pipeline
@startuml _common
' ============================================================
' CryptoBot — PlantUML Shared Skin & Stereotypes
' ============================================================

' --- Theme clair (lisible GitHub) ---
skinparam backgroundColor white
skinparam defaultFontName "Segoe UI, Helvetica, Arial, sans-serif"
skinparam defaultFontSize 12
skinparam defaultFontColor #333333
skinparam shadowing false
skinparam roundCorner 6

' --- Palette ---
' Bleu:   #4A6FA5
' Orange: #FEF3E8 (fond) / #E8943A (bordure)
' Vert:   #ECFDF5 (fond) / #34A853 (bordure)
' Violet: #F3EEFF (fond) / #7C5CFC (bordure)
' Gris:   #F5F5F5 (fond) / #CCCCCC (bordure)

' --- Component ---
skinparam component {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
}

' --- Package ---
skinparam package {
  BackgroundColor #F5F5F5
  BorderColor #4A6FA5
  FontColor #333333
}

' --- Class ---
skinparam class {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
  HeaderBackgroundColor #34A853
  HeaderFontColor white
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
  AttributeFontColor #555555
}

' --- Sequence ---
skinparam sequence {
  ArrowColor #4A6FA5
  ActorBorderColor #7C5CFC
  LifeLineBorderColor #CCCCCC
  LifeLineBackgroundColor #F5F5F5
  ParticipantBorderColor #4A6FA5
  ParticipantBackgroundColor #F3EEFF
  ParticipantFontColor #333333
  BoxBorderColor #CCCCCC
  BoxBackgroundColor #F5F5F5
  DividerBackgroundColor #4A6FA5
  DividerFontColor white
}

' --- Activity ---
skinparam activity {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
  DiamondBackgroundColor #F3EEFF
  DiamondBorderColor #7C5CFC
}

' --- Node (deployment) ---
skinparam node {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
}

' --- Database ---
skinparam database {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
}

' --- Entity (ER) ---
skinparam entity {
  BackgroundColor white
  BorderColor #4A6FA5
  FontColor #333333
  HeaderBackgroundColor #4A6FA5
  HeaderFontColor white
}

' --- State ---
skinparam state {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
}

' --- Usecase ---
skinparam usecase {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  ActorBorderColor #E8943A
}

' --- Note ---
skinparam note {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
}

' --- Legend ---
skinparam legend {
  BackgroundColor #F5F5F5
  BorderColor #CCCCCC
  FontColor #333333
}

' --- Stereotypes ---
' <<collector>>   ETL data collectors
' <<transformer>> ETL data transformers
' <<loader>>      ETL data loaders
' <<scheduler>>   APScheduler jobs
' <<rule>>        ML rule evaluator
' <<model>>       ML model
' <<router>>      FastAPI router
' <<service>>     FastAPI service
' <<middleware>>   FastAPI middleware
' <<page>>        Streamlit page
' <<component>>   Streamlit/Plotly component
' <<hypertable>>  TimescaleDB hypertable
' <<phase2>>      Phase 2 planned feature

@enduml


title CryptoBot — Architecture ML Phase 2
caption Supervised ML + LSTM + Walk-Forward Backtesting

' ============================================================
' Data Sources
' ============================================================
package "Data Layer" #ECFDF5 {
  database "TimescaleDB\nOHLCV + Indicators" as tsdb
  database "MinIO\nDatasets (DVC)\nModel artifacts" as minio
}

' ============================================================
' Feature Engineering
' ============================================================
package "Feature Engineering" #FEF3E8 {
  [FeatureBuilder\nRSI by timeframe\nBB position, squeeze width\ntrend slope, volume\nFear & Greed index\nsentiment score] as features
}

' ============================================================
' Models
' ============================================================
package "Supervised Models" #F3EEFF {
  [XGBoost\ngradient boosting\nfeature importance] as xgb
  [LightGBM\nfast training\ncategorical support] as lgbm
  [LSTM\nsequence prediction\nmulti-step forecast] as lstm
}

' ============================================================
' Training Pipeline
' ============================================================
package "Training Pipeline" #FEF3E8 {
  [Trainer\ntrain(features, labels)\nhyperparameter tuning\ncross-validation] as trainer
  [Walk-Forward Backtester\n6-month train window\n1-month test window\ntemporal-only splits\npurge + embargo] as backtester
  [Drift Detector\nfeature distribution\nmodel performance\nalert on degradation] as drift
}

' ============================================================
' MLOps
' ============================================================
package "MLOps" #F5F5F5 {
  [MLflow\nExperiment tracking\nModel registry\nStaging -> Production] as mlflow
  [DVC\nDataset versioning\nReproducible pipelines\nMinIO backend] as dvc
}

' ============================================================
' Inference
' ============================================================
package "Inference" #ECFDF5 {
  [Predictor\nload model from registry\npredict(features)\nreturn {direction, confidence}] as predictor
  [SignalGenerator\nML blend 60/40\nintegration Phase 1 rules] as siggen
}

' ============================================================
' Relations
' ============================================================
tsdb --> features : raw data
features --> trainer : feature matrix
features --> predictor : live features

trainer --> xgb : train
trainer --> lgbm : train
trainer --> lstm : train

trainer --> mlflow : log metrics, params
trainer --> backtester : validate
backtester --> mlflow : log results

mlflow --> minio : store artifacts
dvc --> minio : version datasets
mlflow --> predictor : load production model

predictor --> siggen : ML predictions
drift --> mlflow : monitor performance
drift --> trainer : retrain trigger

legend bottom right
  |= Couleur |= Phase |
  | <#FEF3E8> | Pipeline training |
  | <#F3EEFF> | Modeles |
  | <#ECFDF5> | Data + Inference |
  | <#F5F5F5> | MLOps |
endlegend

@enduml
```

## C07-phase2-features
> Explications : [[CryptoBot/avril/architecture/c07-phase2-features]]

```plantuml
@startuml C07-phase2-features
@startuml _common
' ============================================================
' CryptoBot — PlantUML Shared Skin & Stereotypes
' ============================================================

' --- Theme clair (lisible GitHub) ---
skinparam backgroundColor white
skinparam defaultFontName "Segoe UI, Helvetica, Arial, sans-serif"
skinparam defaultFontSize 12
skinparam defaultFontColor #333333
skinparam shadowing false
skinparam roundCorner 6

' --- Palette ---
' Bleu:   #4A6FA5
' Orange: #FEF3E8 (fond) / #E8943A (bordure)
' Vert:   #ECFDF5 (fond) / #34A853 (bordure)
' Violet: #F3EEFF (fond) / #7C5CFC (bordure)
' Gris:   #F5F5F5 (fond) / #CCCCCC (bordure)

' --- Component ---
skinparam component {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
}

' --- Package ---
skinparam package {
  BackgroundColor #F5F5F5
  BorderColor #4A6FA5
  FontColor #333333
}

' --- Class ---
skinparam class {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
  HeaderBackgroundColor #34A853
  HeaderFontColor white
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
  AttributeFontColor #555555
}

' --- Sequence ---
skinparam sequence {
  ArrowColor #4A6FA5
  ActorBorderColor #7C5CFC
  LifeLineBorderColor #CCCCCC
  LifeLineBackgroundColor #F5F5F5
  ParticipantBorderColor #4A6FA5
  ParticipantBackgroundColor #F3EEFF
  ParticipantFontColor #333333
  BoxBorderColor #CCCCCC
  BoxBackgroundColor #F5F5F5
  DividerBackgroundColor #4A6FA5
  DividerFontColor white
}

' --- Activity ---
skinparam activity {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
  DiamondBackgroundColor #F3EEFF
  DiamondBorderColor #7C5CFC
}

' --- Node (deployment) ---
skinparam node {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
}

' --- Database ---
skinparam database {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
}

' --- Entity (ER) ---
skinparam entity {
  BackgroundColor white
  BorderColor #4A6FA5
  FontColor #333333
  HeaderBackgroundColor #4A6FA5
  HeaderFontColor white
}

' --- State ---
skinparam state {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
}

' --- Usecase ---
skinparam usecase {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  ActorBorderColor #E8943A
}

' --- Note ---
skinparam note {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
}

' --- Legend ---
skinparam legend {
  BackgroundColor #F5F5F5
  BorderColor #CCCCCC
  FontColor #333333
}

' --- Stereotypes ---
' <<collector>>   ETL data collectors
' <<transformer>> ETL data transformers
' <<loader>>      ETL data loaders
' <<scheduler>>   APScheduler jobs
' <<rule>>        ML rule evaluator
' <<model>>       ML model
' <<router>>      FastAPI router
' <<service>>     FastAPI service
' <<middleware>>   FastAPI middleware
' <<page>>        Streamlit page
' <<component>>   Streamlit/Plotly component
' <<hypertable>>  TimescaleDB hypertable
' <<phase2>>      Phase 2 planned feature

@enduml


title CryptoBot — Roadmap Features Phase 2
caption 8 features | 62 story points | Sprints 11-16

' ============================================================
' Existing Phase 1
' ============================================================
package "Phase 1 (existant)" #F5F5F5 {
  [ETL Pipeline\n5 collectors\n10 jobs] as etl
  [Rule Engine\nRSI, BB, Harmonics\nTrend, Convergence] as rules
  [FastAPI\n8 routers\n22 endpoints] as api
  [Streamlit\n5 pages\n3 personas] as frontend
}

' ============================================================
' P0 — Quick Wins (8 pts, Sprint 11)
' ============================================================
package "P0 — Quick Wins (8 pts)" #ECFDF5 {
  [F1 Regulatory Scraping\nESMA, SEC\nBeautifulSoup\n3 pts] as f1
  [F2 RSS ESMA/SEC\nFeed integration\n2 pts] as f2
  [F3 K-Means Clustering\nMarket regimes\n3 pts] as f3
}

' ============================================================
' P1 — Medium (15 pts, Sprint 12-13)
' ============================================================
package "P1 — Medium (15 pts)" #FEF3E8 {
  [F4 Alerts System\nPrice, signal, news\nWebSocket push\n5 pts] as f4
  [F5 On-Chain Data\nPublic APIs\nWhale tracking\n5 pts] as f5
  [F6 LSTM Deep Learning\nSequence prediction\nMulti-step forecast\n5 pts] as f6
}

' ============================================================
' P2 — High Effort (34 pts, Sprint 13-16)
' ============================================================
package "P2 — High Effort (34 pts)" #F3EEFF {
  [F7 Paper Trading\nSimulated execution\nP&L tracking\nPortfolio management\n13 pts] as f7
  [F8 RL Agents\nReinforcement Learning\nPolicy optimization\n21 pts] as f8
}

' ============================================================
' Integration Points
' ============================================================
f1 --> etl : nouveau collector
f2 --> etl : nouveau collector
f3 --> rules : nouveau evaluator
f4 --> api : WebSocket endpoint
f4 --> frontend : notification UI
f5 --> etl : nouveau collector
f6 --> rules : ML model
f7 --> api : trading endpoints
f7 --> frontend : paper trading UI
f8 --> f7 : depends on paper trading

' Critical path
f7 -[#E8943A,bold]-> f8 : **bloque**

legend bottom right
  |= Priorite |= Story Points |= Risque |
  | P0 Quick Wins | 8 pts | Bas |
  | P1 Medium | 15 pts | Bas-Moyen |
  | P2 High Effort | 34 pts | Moyen-Haut |
  | **Total** | **62 pts** | |
endlegend

@enduml
```

## CL01-pydantic-models
> Explications : [[CryptoBot/avril/architecture/cl01-pydantic-models]]

```plantuml
@startuml CL01-pydantic-models
@startuml _common
' ============================================================
' CryptoBot — PlantUML Shared Skin & Stereotypes
' ============================================================

' --- Theme clair (lisible GitHub) ---
skinparam backgroundColor white
skinparam defaultFontName "Segoe UI, Helvetica, Arial, sans-serif"
skinparam defaultFontSize 12
skinparam defaultFontColor #333333
skinparam shadowing false
skinparam roundCorner 6

' --- Palette ---
' Bleu:   #4A6FA5
' Orange: #FEF3E8 (fond) / #E8943A (bordure)
' Vert:   #ECFDF5 (fond) / #34A853 (bordure)
' Violet: #F3EEFF (fond) / #7C5CFC (bordure)
' Gris:   #F5F5F5 (fond) / #CCCCCC (bordure)

' --- Component ---
skinparam component {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
}

' --- Package ---
skinparam package {
  BackgroundColor #F5F5F5
  BorderColor #4A6FA5
  FontColor #333333
}

' --- Class ---
skinparam class {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
  HeaderBackgroundColor #34A853
  HeaderFontColor white
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
  AttributeFontColor #555555
}

' --- Sequence ---
skinparam sequence {
  ArrowColor #4A6FA5
  ActorBorderColor #7C5CFC
  LifeLineBorderColor #CCCCCC
  LifeLineBackgroundColor #F5F5F5
  ParticipantBorderColor #4A6FA5
  ParticipantBackgroundColor #F3EEFF
  ParticipantFontColor #333333
  BoxBorderColor #CCCCCC
  BoxBackgroundColor #F5F5F5
  DividerBackgroundColor #4A6FA5
  DividerFontColor white
}

' --- Activity ---
skinparam activity {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
  DiamondBackgroundColor #F3EEFF
  DiamondBorderColor #7C5CFC
}

' --- Node (deployment) ---
skinparam node {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
}

' --- Database ---
skinparam database {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
}

' --- Entity (ER) ---
skinparam entity {
  BackgroundColor white
  BorderColor #4A6FA5
  FontColor #333333
  HeaderBackgroundColor #4A6FA5
  HeaderFontColor white
}

' --- State ---
skinparam state {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
}

' --- Usecase ---
skinparam usecase {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  ActorBorderColor #E8943A
}

' --- Note ---
skinparam note {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
}

' --- Legend ---
skinparam legend {
  BackgroundColor #F5F5F5
  BorderColor #CCCCCC
  FontColor #333333
}

' --- Stereotypes ---
' <<collector>>   ETL data collectors
' <<transformer>> ETL data transformers
' <<loader>>      ETL data loaders
' <<scheduler>>   APScheduler jobs
' <<rule>>        ML rule evaluator
' <<model>>       ML model
' <<router>>      FastAPI router
' <<service>>     FastAPI service
' <<middleware>>   FastAPI middleware
' <<page>>        Streamlit page
' <<component>>   Streamlit/Plotly component
' <<hypertable>>  TimescaleDB hypertable
' <<phase2>>      Phase 2 planned feature

@enduml


title CryptoBot — Modeles Domaine Pydantic v2
caption src/shared/models/ | 7 modeles

' ============================================================
' Crypto Domain
' ============================================================
package "crypto.py" #FEF3E8 {

  class OHLCVRecord <<BaseModel>> {
    + symbol : str
    + price_open : Decimal
    + price_high : Decimal
    + price_low : Decimal
    + price_close : Decimal
    + volume_24h : Decimal
    + market_cap : Decimal | None
    + timestamp : datetime
    + source : str
    + timeframe : str
    --
    <<validator>> price_high >= price_low
    <<validator>> volume_24h >= 0
  }

  class IndicatorRecord <<BaseModel>> {
    + symbol : str
    + timeframe : str
    + timestamp : datetime
    + rsi : Decimal | None
    + bollinger_upper : Decimal | None
    + bollinger_middle : Decimal | None
    + bollinger_lower : Decimal | None
    + price_vs_bollinger : Decimal | None
    + harmonic_pattern : str | None
    + trend_slope : Decimal | None
    + trend_type : str | None
    + metadata : dict
  }

  class NewsArticle <<BaseModel>> {
    + title : str
    + content : str | None
    + source : str
    + url : str
    + published_at : datetime | None
    + sentiment_score : Decimal | None
    + keywords : list[str]
    + reliability_score : Decimal | None
  }
}

' ============================================================
' Signal Domain
' ============================================================
package "signal.py" #F3EEFF {

  class TradingSignal <<BaseModel>> {
    + symbol : str
    + signal_type : Literal["BUY","SELL","HOLD"]
    + confidence_score : Decimal
    + timeframe_primary : str
    + timeframes_aligned : dict
    + rules_triggered : list[str]
    + leverage_suggested : int | None
    + margin_safety : Decimal | None
    + fees_estimated : Decimal | None
    + model_version : str
    + created_at : datetime | None
    --
    <<constraint>> confidence >= 0.6
    <<constraint>> leverage 1-20
  }

  class SignalOutcome <<BaseModel>> {
    + signal_id : str
    + price_at_signal : Decimal
    + price_after_1h : Decimal | None
    + price_after_4h : Decimal | None
    + price_after_1d : Decimal | None
    + pnl_simulated : Decimal | None
    + was_correct : bool | None
    + evaluated_at : datetime
  }
}

' ============================================================
' User Domain
' ============================================================
package "user.py" #ECFDF5 {

  class UserCreate <<BaseModel>> {
    + username : str {3-100}
    + email : EmailStr
    + password : str {min 8}
    + persona_type : str
    --
    trader | journalist | investor
  }

  class UserRead <<BaseModel>> {
    + id : str
    + username : str
    + email : str
    + persona_type : str
    + preferences : dict
    + created_at : datetime
  }
}

' ============================================================
' Relations
' ============================================================
TradingSignal "1" -- "0..1" SignalOutcome : evaluation
OHLCVRecord ..> IndicatorRecord : calcule
IndicatorRecord ..> TradingSignal : genere
NewsArticle ..> TradingSignal : sentiment

@enduml
```

## CL02-orm-models
> Explications : [[CryptoBot/avril/architecture/cl02-orm-models]]

```plantuml
@startuml CL02-orm-models
@startuml _common
' ============================================================
' CryptoBot — PlantUML Shared Skin & Stereotypes
' ============================================================

' --- Theme clair (lisible GitHub) ---
skinparam backgroundColor white
skinparam defaultFontName "Segoe UI, Helvetica, Arial, sans-serif"
skinparam defaultFontSize 12
skinparam defaultFontColor #333333
skinparam shadowing false
skinparam roundCorner 6

' --- Palette ---
' Bleu:   #4A6FA5
' Orange: #FEF3E8 (fond) / #E8943A (bordure)
' Vert:   #ECFDF5 (fond) / #34A853 (bordure)
' Violet: #F3EEFF (fond) / #7C5CFC (bordure)
' Gris:   #F5F5F5 (fond) / #CCCCCC (bordure)

' --- Component ---
skinparam component {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
}

' --- Package ---
skinparam package {
  BackgroundColor #F5F5F5
  BorderColor #4A6FA5
  FontColor #333333
}

' --- Class ---
skinparam class {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
  HeaderBackgroundColor #34A853
  HeaderFontColor white
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
  AttributeFontColor #555555
}

' --- Sequence ---
skinparam sequence {
  ArrowColor #4A6FA5
  ActorBorderColor #7C5CFC
  LifeLineBorderColor #CCCCCC
  LifeLineBackgroundColor #F5F5F5
  ParticipantBorderColor #4A6FA5
  ParticipantBackgroundColor #F3EEFF
  ParticipantFontColor #333333
  BoxBorderColor #CCCCCC
  BoxBackgroundColor #F5F5F5
  DividerBackgroundColor #4A6FA5
  DividerFontColor white
}

' --- Activity ---
skinparam activity {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
  DiamondBackgroundColor #F3EEFF
  DiamondBorderColor #7C5CFC
}

' --- Node (deployment) ---
skinparam node {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
}

' --- Database ---
skinparam database {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
}

' --- Entity (ER) ---
skinparam entity {
  BackgroundColor white
  BorderColor #4A6FA5
  FontColor #333333
  HeaderBackgroundColor #4A6FA5
  HeaderFontColor white
}

' --- State ---
skinparam state {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
}

' --- Usecase ---
skinparam usecase {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  ActorBorderColor #E8943A
}

' --- Note ---
skinparam note {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
}

' --- Legend ---
skinparam legend {
  BackgroundColor #F5F5F5
  BorderColor #CCCCCC
  FontColor #333333
}

' --- Stereotypes ---
' <<collector>>   ETL data collectors
' <<transformer>> ETL data transformers
' <<loader>>      ETL data loaders
' <<scheduler>>   APScheduler jobs
' <<rule>>        ML rule evaluator
' <<model>>       ML model
' <<router>>      FastAPI router
' <<service>>     FastAPI service
' <<middleware>>   FastAPI middleware
' <<page>>        Streamlit page
' <<component>>   Streamlit/Plotly component
' <<hypertable>>  TimescaleDB hypertable
' <<phase2>>      Phase 2 planned feature

@enduml


title CryptoBot — Classes SQLAlchemy ORM
caption src/shared/db_models.py | 9 classes | TimescaleDB

' ============================================================
' User Domain
' ============================================================
class UserOrm <<users>> {
  + id : UUID <<PK>>
  + username : String(100) <<UNIQUE>>
  + email : String(255) <<UNIQUE>>
  + password_hash : String(255)
  + persona_type : String(20)
  + preferences : JSONB
  + created_at : DateTime
  --
  <<CHECK>> persona_type IN
  (trader, journalist, investor)
  <<rel>> portfolio_entries : 1:N
  <<rel>> watchlist_entries : 1:N
}

' ============================================================
' Market Data
' ============================================================
class CryptoPriceOrm <<crypto_prices>> {
  + symbol : String(20) <<PK>>
  + timeframe : String(10) <<PK>>
  + timestamp : DateTime(tz) <<PK>>
  + price_open : Numeric(20,8)
  + price_high : Numeric(20,8)
  + price_low : Numeric(20,8)
  + price_close : Numeric(20,8)
  + volume_24h : Numeric(20,8)
  + market_cap : Numeric(20,2)
  + source : String(50)
  --
  <<HYPERTABLE>> retain=90d compress=7d
  <<INDEX>> (symbol, timeframe, timestamp)
}

class IndicatorOrm <<indicators>> {
  + id : UUID <<PK>>
  + symbol : String(20)
  + timeframe : String(10)
  + timestamp : DateTime(tz)
  + rsi : Numeric(10,4)
  + bollinger_upper : Numeric(20,8)
  + bollinger_middle : Numeric(20,8)
  + bollinger_lower : Numeric(20,8)
  + price_vs_bollinger : Numeric(10,6)
  + harmonic_pattern : String(50)
  + trend_slope : Numeric(10,6)
  + trend_type : String(20)
  + metadata : JSONB
  --
  <<UNIQUE>> (symbol, timeframe, timestamp)
}

' ============================================================
' Signals
' ============================================================
class TradingSignalOrm <<trading_signals>> {
  + id : UUID <<PK>>
  + symbol : String(20)
  + signal_type : String(10)
  + confidence_score : Numeric(5,4)
  + timeframe_primary : String(10)
  + timeframes_aligned : JSONB
  + rules_triggered : JSONB
  + leverage_suggested : Integer
  + margin_safety : Numeric(10,4)
  + fees_estimated : Numeric(10,6)
  + model_version : String(50)
  + created_at : DateTime
  --
  <<CHECK>> signal_type IN (BUY,SELL,HOLD)
  <<INDEX>> (symbol, created_at)
  <<rel>> outcome : 0..1
}

class SignalOutcomeOrm <<signal_outcomes>> {
  + id : UUID <<PK>>
  + signal_id : UUID <<FK>>
  + price_at_signal : Numeric(20,8)
  + price_after_1h : Numeric(20,8)
  + price_after_4h : Numeric(20,8)
  + price_after_1d : Numeric(20,8)
  + pnl_simulated : Numeric(10,4)
  + was_correct : Boolean
  + evaluated_at : DateTime
  --
  <<INDEX>> (signal_id)
  <<INDEX>> (was_correct)
}

' ============================================================
' User Data
' ============================================================
class PortfolioOrm <<portfolio_entries>> {
  + id : UUID <<PK>>
  + user_id : UUID <<FK>>
  + symbol : String(20)
  + quantity : Numeric(20,8)
  + entry_price : Numeric(20,8)
  + current_price : Numeric(20,8)
  + notes : Text
  + created_at : DateTime
  + updated_at : DateTime
  --
  <<INDEX>> (user_id)
}

class WatchlistOrm <<watchlist_entries>> {
  + id : UUID <<PK>>
  + user_id : UUID <<FK>>
  + symbol : String(20)
  + added_at : DateTime
  --
  <<UNIQUE>> (user_id, symbol)
}

' ============================================================
' News / NLP
' ============================================================
class NewsArticleOrm <<news_articles>> {
  + id : UUID <<PK>>
  + title : String(500)
  + content : Text
  + source : String(100)
  + url : String(1000) <<UNIQUE>>
  + published_at : DateTime(tz)
  + sentiment_score : Numeric(5,4)
  + keywords : JSONB
  + reliability_score : Numeric(5,4)
  + collected_at : DateTime
  --
  <<INDEX>> (published_at)
  <<INDEX>> (source)
  <<rel>> text_mining_result : 0..1
}

class TextMiningResultOrm <<text_mining_results>> {
  + id : UUID <<PK>>
  + article_id : UUID <<FK>>
  + word_cloud : JSONB
  + summary : Text
  + entities : JSONB
  + topics : JSONB
  + processed_at : DateTime
}

' ============================================================
' Relations
' ============================================================
UserOrm "1" ||--o{ "N" PortfolioOrm : CASCADE
UserOrm "1" ||--o{ "N" WatchlistOrm : CASCADE
TradingSignalOrm "1" ||--o| "0..1" SignalOutcomeOrm : CASCADE
NewsArticleOrm "1" ||--o| "0..1" TextMiningResultOrm : CASCADE

@enduml
```

## CL03-api-schemas
> Explications : [[CryptoBot/avril/architecture/cl03-api-schemas]]

```plantuml
@startuml CL03-api-schemas
@startuml _common
' ============================================================
' CryptoBot — PlantUML Shared Skin & Stereotypes
' ============================================================

' --- Theme clair (lisible GitHub) ---
skinparam backgroundColor white
skinparam defaultFontName "Segoe UI, Helvetica, Arial, sans-serif"
skinparam defaultFontSize 12
skinparam defaultFontColor #333333
skinparam shadowing false
skinparam roundCorner 6

' --- Palette ---
' Bleu:   #4A6FA5
' Orange: #FEF3E8 (fond) / #E8943A (bordure)
' Vert:   #ECFDF5 (fond) / #34A853 (bordure)
' Violet: #F3EEFF (fond) / #7C5CFC (bordure)
' Gris:   #F5F5F5 (fond) / #CCCCCC (bordure)

' --- Component ---
skinparam component {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
}

' --- Package ---
skinparam package {
  BackgroundColor #F5F5F5
  BorderColor #4A6FA5
  FontColor #333333
}

' --- Class ---
skinparam class {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
  HeaderBackgroundColor #34A853
  HeaderFontColor white
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
  AttributeFontColor #555555
}

' --- Sequence ---
skinparam sequence {
  ArrowColor #4A6FA5
  ActorBorderColor #7C5CFC
  LifeLineBorderColor #CCCCCC
  LifeLineBackgroundColor #F5F5F5
  ParticipantBorderColor #4A6FA5
  ParticipantBackgroundColor #F3EEFF
  ParticipantFontColor #333333
  BoxBorderColor #CCCCCC
  BoxBackgroundColor #F5F5F5
  DividerBackgroundColor #4A6FA5
  DividerFontColor white
}

' --- Activity ---
skinparam activity {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
  DiamondBackgroundColor #F3EEFF
  DiamondBorderColor #7C5CFC
}

' --- Node (deployment) ---
skinparam node {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
}

' --- Database ---
skinparam database {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
}

' --- Entity (ER) ---
skinparam entity {
  BackgroundColor white
  BorderColor #4A6FA5
  FontColor #333333
  HeaderBackgroundColor #4A6FA5
  HeaderFontColor white
}

' --- State ---
skinparam state {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
}

' --- Usecase ---
skinparam usecase {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  ActorBorderColor #E8943A
}

' --- Note ---
skinparam note {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
}

' --- Legend ---
skinparam legend {
  BackgroundColor #F5F5F5
  BorderColor #CCCCCC
  FontColor #333333
}

' --- Stereotypes ---
' <<collector>>   ETL data collectors
' <<transformer>> ETL data transformers
' <<loader>>      ETL data loaders
' <<scheduler>>   APScheduler jobs
' <<rule>>        ML rule evaluator
' <<model>>       ML model
' <<router>>      FastAPI router
' <<service>>     FastAPI service
' <<middleware>>   FastAPI middleware
' <<page>>        Streamlit page
' <<component>>   Streamlit/Plotly component
' <<hypertable>>  TimescaleDB hypertable
' <<phase2>>      Phase 2 planned feature

@enduml


title CryptoBot — Schemas API Request/Response
caption src/api/schemas.py | 30+ schemas Pydantic v2

' ============================================================
' Generic Envelope
' ============================================================
package "Envelope" #F5F5F5 {
  class "ApiResponse<T>" as ApiResponse <<Generic>> {
    + data : T | None
    + error : ErrorDetail | None
    + meta : PaginationMeta | None
  }

  class ErrorDetail {
    + code : str
    + message : str
  }

  class PaginationMeta {
    + total : int
    + page : int
    + limit : int
  }
}

' ============================================================
' Auth
' ============================================================
package "Auth" #FEF3E8 {
  class RegisterRequest {
    + username : str {3-100}
    + email : EmailStr
    + password : str {8+, upper+digit+special}
    + persona_type : Literal[trader|journalist|investor]
  }

  class LoginRequest {
    + email : EmailStr
    + password : str {8+}
  }

  class LoginResponse {
    + access_token : str
    + token_type : str = "bearer"
  }

  class UserResponse {
    + id : UUID
    + username : str
    + email : str
    + persona_type : str
    + preferences : dict
    + created_at : datetime
  }
}

' ============================================================
' Crypto
' ============================================================
package "Crypto" #ECFDF5 {
  class CryptoListItem {
    + symbol : str
    + name : str | None
  }

  class OHLCVResponse {
    + symbol : str
    + timeframe : str
    + timestamp : datetime
    + price_open..close : float
    + volume_24h : float
    + market_cap : float | None
    + source : str
  }

  class IndicatorResponse {
    + symbol, timeframe, timestamp
    + rsi : float | None
    + bollinger_upper/middle/lower
    + price_vs_bollinger
    + harmonic_pattern : str | None
    + trend_slope, trend_type
  }

  class LatestResponse {
    + symbol : str
    + ohlcv : OHLCVResponse | None
    + indicators : IndicatorResponse | None
  }

  class MarketOverviewResponse {
    + top_movers
    + gainers
    + losers
  }
}

' ============================================================
' Signals
' ============================================================
package "Signals" #F3EEFF {
  class SignalResponse {
    + symbol, signal_type
    + confidence_score
    + timeframe_primary
    + timeframes_aligned : JSON
    + rules_triggered : JSON
    + leverage_suggested
    + margin_safety, fees_estimated
    + model_version
    + created_at
    + pnl_simulated : float | None
    + was_correct : bool | None
  }

  class SignalDetailResponse {
    + signal : SignalResponse
    + outcome : SignalOutcomeResponse | None
  }

  class SignalOutcomeResponse {
    + signal_id : UUID
    + price_at_signal : Decimal
    + price_after_1h/4h/1d
    + pnl_simulated
    + was_correct : bool | None
    + evaluated_at
  }

  class PerformanceResponse {
    + total_signals : int
    + evaluated_signals : int
    + correct_signals : int
    + win_rate : float
    + total_pnl : float
  }
}

' ============================================================
' News
' ============================================================
package "News" #FEF3E8 {
  class NewsResponse {
    + title, content, source, url
    + published_at
    + sentiment_score
    + keywords : list[str]
    + reliability_score
  }

  class NewsSentimentResponse {
    + source aggregates
  }
}

' ============================================================
' User Data
' ============================================================
package "Portfolio / Watchlist" #ECFDF5 {
  class PortfolioCreateRequest {
    + symbol : str <<uppercase>>
    + quantity : Decimal
    + entry_price : Decimal
    + notes : str | None
  }

  class PortfolioEntryResponse {
    + id, user_id, symbol
    + quantity, entry_price
    + current_price, notes
    + created_at, updated_at
  }

  class WatchlistAddRequest {
    + symbol : str <<uppercase>>
  }

  class WatchlistEntryResponse {
    + id, user_id, symbol
    + added_at
  }
}

' ============================================================
' System
' ============================================================
package "System / Chat" #F5F5F5 {
  class HealthResponse {
    + status : str
    + database : str
    + timestamp : datetime
  }

  class ChatRequest {
    + message : str
  }

  class ChatResponse {
    + response : str
  }
}

' ============================================================
' Relations
' ============================================================
ApiResponse *-- ErrorDetail
ApiResponse *-- PaginationMeta
SignalDetailResponse *-- SignalResponse
SignalDetailResponse *-- SignalOutcomeResponse
LatestResponse *-- OHLCVResponse
LatestResponse *-- IndicatorResponse

@enduml
```

## CL04-ml-rules-models
> Explications : [[CryptoBot/avril/architecture/cl04-ml-rules-models]]

```plantuml
@startuml CL04-ml-rules-models
@startuml _common
' ============================================================
' CryptoBot — PlantUML Shared Skin & Stereotypes
' ============================================================

' --- Theme clair (lisible GitHub) ---
skinparam backgroundColor white
skinparam defaultFontName "Segoe UI, Helvetica, Arial, sans-serif"
skinparam defaultFontSize 12
skinparam defaultFontColor #333333
skinparam shadowing false
skinparam roundCorner 6

' --- Palette ---
' Bleu:   #4A6FA5
' Orange: #FEF3E8 (fond) / #E8943A (bordure)
' Vert:   #ECFDF5 (fond) / #34A853 (bordure)
' Violet: #F3EEFF (fond) / #7C5CFC (bordure)
' Gris:   #F5F5F5 (fond) / #CCCCCC (bordure)

' --- Component ---
skinparam component {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
}

' --- Package ---
skinparam package {
  BackgroundColor #F5F5F5
  BorderColor #4A6FA5
  FontColor #333333
}

' --- Class ---
skinparam class {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
  HeaderBackgroundColor #34A853
  HeaderFontColor white
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
  AttributeFontColor #555555
}

' --- Sequence ---
skinparam sequence {
  ArrowColor #4A6FA5
  ActorBorderColor #7C5CFC
  LifeLineBorderColor #CCCCCC
  LifeLineBackgroundColor #F5F5F5
  ParticipantBorderColor #4A6FA5
  ParticipantBackgroundColor #F3EEFF
  ParticipantFontColor #333333
  BoxBorderColor #CCCCCC
  BoxBackgroundColor #F5F5F5
  DividerBackgroundColor #4A6FA5
  DividerFontColor white
}

' --- Activity ---
skinparam activity {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
  DiamondBackgroundColor #F3EEFF
  DiamondBorderColor #7C5CFC
}

' --- Node (deployment) ---
skinparam node {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
}

' --- Database ---
skinparam database {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
}

' --- Entity (ER) ---
skinparam entity {
  BackgroundColor white
  BorderColor #4A6FA5
  FontColor #333333
  HeaderBackgroundColor #4A6FA5
  HeaderFontColor white
}

' --- State ---
skinparam state {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
}

' --- Usecase ---
skinparam usecase {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  ActorBorderColor #E8943A
}

' --- Note ---
skinparam note {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
}

' --- Legend ---
skinparam legend {
  BackgroundColor #F5F5F5
  BorderColor #CCCCCC
  FontColor #333333
}

' --- Stereotypes ---
' <<collector>>   ETL data collectors
' <<transformer>> ETL data transformers
' <<loader>>      ETL data loaders
' <<scheduler>>   APScheduler jobs
' <<rule>>        ML rule evaluator
' <<model>>       ML model
' <<router>>      FastAPI router
' <<service>>     FastAPI service
' <<middleware>>   FastAPI middleware
' <<page>>        Streamlit page
' <<component>>   Streamlit/Plotly component
' <<hypertable>>  TimescaleDB hypertable
' <<phase2>>      Phase 2 planned feature

@enduml


title CryptoBot — Hierarchie ML Rules Engine
caption src/ml/rules/ + src/ml/signal_generator.py

' ============================================================
' Rule Engine Core
' ============================================================
package "rules/engine.py" #F3EEFF {

  class RuleEngine {
    - config_path : Path
    - _RULE_WEIGHTS : dict
    --
    + {static} from_default() : RuleEngine
    + evaluate(symbol, timeframe, indicators, prices) : list[RuleResult]
    + aggregate(symbol, timeframe, results) : dict
    - _infer_rule_key(name) : str
    - _infer_primary_timeframe(results) : str
  }

  class RuleResult <<dataclass>> {
    + rule_name : str
    + direction : str
    + confidence : float
    + timeframe : str
    + details : dict
  }

  note right of RuleEngine
    Poids :
    RSI = 0.25
    Bollinger = 0.25
    Harmonic = 0.30
    Trend = 0.20
  end note
}

' ============================================================
' Evaluators
' ============================================================
package "rules/evaluators/" #FEF3E8 {

  class "evaluate_rsi()" as rsi <<function>> {
    overbought / oversold
    multi-TF convergence
  }

  class "evaluate_bollinger()" as boll <<function>> {
    squeeze detection
    band reversal
  }

  class "evaluate_harmonic()" as harm <<function>> {
    Gartley, Butterfly
    Crab, XAB=CD
  }

  class "evaluate_trend()" as trend <<function>> {
    slope + type
    weekly/monthly
  }

  class "evaluate_rsi_bollinger\n_convergence()" as conv1 <<function>>
  class "evaluate_trend_rsi\n_convergence()" as conv2 <<function>>
  class "evaluate_multi_tf\n_alignment()" as mtf <<function>>
  class "evaluate_supermajority\n_tf_alignment()" as smtf <<function>>
}

' ============================================================
' Signal Generator
' ============================================================
package "signal_generator.py" #ECFDF5 {

  class SignalGenerator {
    - rule_engine : RuleEngine
    - predictor : Predictor | None
    --
    + generate(symbol, tf, indicators, prices, sentiment) : TradingSignal | None
    + save_signal(db, signal) : TradingSignalOrm
    + generate_signals_for_symbols(symbols, ...) : list
    --
    - _evaluate_rules() : dict
    - _ml_predict() : dict | None
    - _blend_confidences(ml, rules) : float
    - _adjust_confidence_by_sentiment(conf, score) : float
    - _suggest_leverage(confidence) : int | None
    - _estimate_fees() : Decimal
  }

  note right of SignalGenerator
    ML Blend :
    Same dir: 60% ML + 40% rules
    Conflict: 40% * min(ml, rules)

    Sentiment: +/- 5pp
    Threshold: >= 0.6
  end note

  interface Predictor <<Protocol>> {
    + predict(features) : list[dict]
  }
}

' ============================================================
' Relations
' ============================================================
RuleEngine --> RuleResult : produces
RuleEngine ..> rsi : calls
RuleEngine ..> boll : calls
RuleEngine ..> harm : calls
RuleEngine ..> trend : calls
RuleEngine ..> conv1 : calls
RuleEngine ..> conv2 : calls
RuleEngine ..> mtf : calls
RuleEngine ..> smtf : calls

SignalGenerator --> RuleEngine : uses
SignalGenerator --> Predictor : optional
rsi --> RuleResult : returns
boll --> RuleResult : returns
harm --> RuleResult : returns
trend --> RuleResult : returns

@enduml
```

## CL05-exceptions
> Explications : [[CryptoBot/avril/architecture/cl05-exceptions]]

```plantuml
@startuml CL05-exceptions
@startuml _common
' ============================================================
' CryptoBot — PlantUML Shared Skin & Stereotypes
' ============================================================

' --- Theme clair (lisible GitHub) ---
skinparam backgroundColor white
skinparam defaultFontName "Segoe UI, Helvetica, Arial, sans-serif"
skinparam defaultFontSize 12
skinparam defaultFontColor #333333
skinparam shadowing false
skinparam roundCorner 6

' --- Palette ---
' Bleu:   #4A6FA5
' Orange: #FEF3E8 (fond) / #E8943A (bordure)
' Vert:   #ECFDF5 (fond) / #34A853 (bordure)
' Violet: #F3EEFF (fond) / #7C5CFC (bordure)
' Gris:   #F5F5F5 (fond) / #CCCCCC (bordure)

' --- Component ---
skinparam component {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
}

' --- Package ---
skinparam package {
  BackgroundColor #F5F5F5
  BorderColor #4A6FA5
  FontColor #333333
}

' --- Class ---
skinparam class {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
  HeaderBackgroundColor #34A853
  HeaderFontColor white
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
  AttributeFontColor #555555
}

' --- Sequence ---
skinparam sequence {
  ArrowColor #4A6FA5
  ActorBorderColor #7C5CFC
  LifeLineBorderColor #CCCCCC
  LifeLineBackgroundColor #F5F5F5
  ParticipantBorderColor #4A6FA5
  ParticipantBackgroundColor #F3EEFF
  ParticipantFontColor #333333
  BoxBorderColor #CCCCCC
  BoxBackgroundColor #F5F5F5
  DividerBackgroundColor #4A6FA5
  DividerFontColor white
}

' --- Activity ---
skinparam activity {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
  DiamondBackgroundColor #F3EEFF
  DiamondBorderColor #7C5CFC
}

' --- Node (deployment) ---
skinparam node {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
}

' --- Database ---
skinparam database {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
}

' --- Entity (ER) ---
skinparam entity {
  BackgroundColor white
  BorderColor #4A6FA5
  FontColor #333333
  HeaderBackgroundColor #4A6FA5
  HeaderFontColor white
}

' --- State ---
skinparam state {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
}

' --- Usecase ---
skinparam usecase {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  ActorBorderColor #E8943A
}

' --- Note ---
skinparam note {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
}

' --- Legend ---
skinparam legend {
  BackgroundColor #F5F5F5
  BorderColor #CCCCCC
  FontColor #333333
}

' --- Stereotypes ---
' <<collector>>   ETL data collectors
' <<transformer>> ETL data transformers
' <<loader>>      ETL data loaders
' <<scheduler>>   APScheduler jobs
' <<rule>>        ML rule evaluator
' <<model>>       ML model
' <<router>>      FastAPI router
' <<service>>     FastAPI service
' <<middleware>>   FastAPI middleware
' <<page>>        Streamlit page
' <<component>>   Streamlit/Plotly component
' <<hypertable>>  TimescaleDB hypertable
' <<phase2>>      Phase 2 planned feature

@enduml


title CryptoBot — Arbre d'Exceptions
caption src/shared/exceptions.py | 13 classes

' ============================================================
' Base
' ============================================================
class CryptoBotError #FEF3E8 {
  + status_code : int = 500
  + message : str
  + detail : Any = None
}

' ============================================================
' Application Exceptions
' ============================================================
class NotFoundError #F3EEFF {
  + status_code = 404
}

class AuthenticationError #F3EEFF {
  + status_code = 401
}

class AuthorizationError #F3EEFF {
  + status_code = 403
}

class ValidationError #F3EEFF {
  + status_code = 422
}

class ConflictError #F3EEFF {
  + status_code = 409
}

class ConfigurationError #F3EEFF {
  + status_code = 500
}

class ExternalAPIError #FEF3E8 {
  + status_code = 502
}

class RateLimitError #FEF3E8 {
  + status_code = 429
}

' ============================================================
' ETL Exceptions
' ============================================================
class ETLError #ECFDF5 {
  + status_code = 500
}

class CollectorError #ECFDF5 {
}

class DataSourceUnavailable #ECFDF5 {
}

class LoaderError #ECFDF5 {
}

class TransformError #ECFDF5 {
}

' ============================================================
' Hierarchy
' ============================================================
CryptoBotError <|-- NotFoundError
CryptoBotError <|-- AuthenticationError
CryptoBotError <|-- AuthorizationError
CryptoBotError <|-- ValidationError
CryptoBotError <|-- ConflictError
CryptoBotError <|-- ConfigurationError
CryptoBotError <|-- ExternalAPIError
ExternalAPIError <|-- RateLimitError

CryptoBotError <|-- ETLError
ETLError <|-- CollectorError
ETLError <|-- LoaderError
ETLError <|-- TransformError
CollectorError <|-- DataSourceUnavailable

' ============================================================
' Legend
' ============================================================
legend bottom right
  |= Couleur |= Categorie |
  | <#FEF3E8> | Base + External |
  | <#F3EEFF> | Application (4xx/5xx) |
  | <#ECFDF5> | ETL specifique |
endlegend

@enduml
```

## DP01-docker-infrastructure
> Explications : [[CryptoBot/avril/architecture/dp01-docker-infrastructure]]

```plantuml
@startuml DP01-docker-infrastructure
@startuml _common
' ============================================================
' CryptoBot — PlantUML Shared Skin & Stereotypes
' ============================================================

' --- Theme clair (lisible GitHub) ---
skinparam backgroundColor white
skinparam defaultFontName "Segoe UI, Helvetica, Arial, sans-serif"
skinparam defaultFontSize 12
skinparam defaultFontColor #333333
skinparam shadowing false
skinparam roundCorner 6

' --- Palette ---
' Bleu:   #4A6FA5
' Orange: #FEF3E8 (fond) / #E8943A (bordure)
' Vert:   #ECFDF5 (fond) / #34A853 (bordure)
' Violet: #F3EEFF (fond) / #7C5CFC (bordure)
' Gris:   #F5F5F5 (fond) / #CCCCCC (bordure)

' --- Component ---
skinparam component {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
}

' --- Package ---
skinparam package {
  BackgroundColor #F5F5F5
  BorderColor #4A6FA5
  FontColor #333333
}

' --- Class ---
skinparam class {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
  HeaderBackgroundColor #34A853
  HeaderFontColor white
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
  AttributeFontColor #555555
}

' --- Sequence ---
skinparam sequence {
  ArrowColor #4A6FA5
  ActorBorderColor #7C5CFC
  LifeLineBorderColor #CCCCCC
  LifeLineBackgroundColor #F5F5F5
  ParticipantBorderColor #4A6FA5
  ParticipantBackgroundColor #F3EEFF
  ParticipantFontColor #333333
  BoxBorderColor #CCCCCC
  BoxBackgroundColor #F5F5F5
  DividerBackgroundColor #4A6FA5
  DividerFontColor white
}

' --- Activity ---
skinparam activity {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
  DiamondBackgroundColor #F3EEFF
  DiamondBorderColor #7C5CFC
}

' --- Node (deployment) ---
skinparam node {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
}

' --- Database ---
skinparam database {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
}

' --- Entity (ER) ---
skinparam entity {
  BackgroundColor white
  BorderColor #4A6FA5
  FontColor #333333
  HeaderBackgroundColor #4A6FA5
  HeaderFontColor white
}

' --- State ---
skinparam state {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
}

' --- Usecase ---
skinparam usecase {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  ActorBorderColor #E8943A
}

' --- Note ---
skinparam note {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
}

' --- Legend ---
skinparam legend {
  BackgroundColor #F5F5F5
  BorderColor #CCCCCC
  FontColor #333333
}

' --- Stereotypes ---
' <<collector>>   ETL data collectors
' <<transformer>> ETL data transformers
' <<loader>>      ETL data loaders
' <<scheduler>>   APScheduler jobs
' <<rule>>        ML rule evaluator
' <<model>>       ML model
' <<router>>      FastAPI router
' <<service>>     FastAPI service
' <<middleware>>   FastAPI middleware
' <<page>>        Streamlit page
' <<component>>   Streamlit/Plotly component
' <<hypertable>>  TimescaleDB hypertable
' <<phase2>>      Phase 2 planned feature

@enduml


title CryptoBot — Infrastructure Docker Compose
caption 12 services | 2 networks | 4 volumes

' ============================================================
' External
' ============================================================
actor "Users" as users
cloud "Internet\nCloudflare DNS" as internet #F5F5F5

' ============================================================
' frontend-net
' ============================================================
package "frontend-net" as fnet #F3EEFF {
  node "nginx\nnginx:alpine\n:80 :443" as nginx
  node "frontend\nStreamlit\n:8501 | 512M" as fe
  node "nginx-exporter\n32M" as ngexp
}

' ============================================================
' backend-net
' ============================================================
package "backend-net" as bnet #FEF3E8 {
  node "api\nFastAPI\n:8000 | 512M" as api

  database "timescaledb\nPG16 | :5433\n1G" as tsdb #ECFDF5
  database "minio\nS3 | :9000 :9001\n512M" as minio #ECFDF5

  node "mlflow\n:5000 | 512M" as mlflow
  node "etl-worker\n1G | no port" as etl
  node "ml-worker\n1G | no port" as mlw

  node "prometheus\nv2.52.0 | :9090\n512M" as prom
  node "grafana\nv10.4.2 | :3000\n256M" as graf
  node "postgres-exporter\n64M" as pgexp
}

' ============================================================
' Volumes
' ============================================================
database "timescaledb-data" as vol_tsdb #ECFDF5
database "minio-data" as vol_minio #ECFDF5
database "prometheus-data" as vol_prom #FEF3E8
database "grafana-data" as vol_graf #FEF3E8

' ============================================================
' Relations — Access
' ============================================================
users --> internet
internet --> nginx : HTTPS

' Nginx routing
nginx --> api : /api/*
nginx --> fe : /crypto/*

' API in both networks
note on link : frontend-net\n+ backend-net

' ============================================================
' Relations — Data
' ============================================================
api --> tsdb : SQL queries
api --> minio : S3 objects

etl --> tsdb : insert batches
etl --> minio : export parquet

mlw --> tsdb : read indicators
mlw --> minio : model artifacts
mlw --> mlflow : experiment tracking

mlflow --> tsdb : metadata store
mlflow --> minio : artifact store

' ============================================================
' Relations — Monitoring
' ============================================================
prom --> api : scrape /metrics
pgexp --> tsdb : pg metrics
ngexp --> nginx : stub_status
graf --> prom : datasource

' ============================================================
' Relations — Volumes
' ============================================================
tsdb --> vol_tsdb
minio --> vol_minio
prom --> vol_prom
graf --> vol_graf

' ============================================================
' Health checks (notes)
' ============================================================
note right of tsdb : pg_isready\n10s interval, 5 retries
note right of api : curl /health\n30s interval, 15s start
note right of fe : curl /_stcore/health
note right of etl : import src.etl\n30s start_period
note right of mlw : import src.ml\n30s start_period, depends mlflow

' ============================================================
' Legend
' ============================================================
legend bottom left
  |= Couleur |= Usage |
  | <#F3EEFF> | frontend-net |
  | <#FEF3E8> | backend-net |
  | <#ECFDF5> | Stockage persistant |
  |= Memoire totale |= ~5.8 GB |
endlegend

@enduml
```

## ER01-database-schema
> Explications : [[CryptoBot/avril/architecture/er01-database-schema]]

```plantuml
@startuml ER01-database-schema
@startuml _common
' ============================================================
' CryptoBot — PlantUML Shared Skin & Stereotypes
' ============================================================

' --- Theme clair (lisible GitHub) ---
skinparam backgroundColor white
skinparam defaultFontName "Segoe UI, Helvetica, Arial, sans-serif"
skinparam defaultFontSize 12
skinparam defaultFontColor #333333
skinparam shadowing false
skinparam roundCorner 6

' --- Palette ---
' Bleu:   #4A6FA5
' Orange: #FEF3E8 (fond) / #E8943A (bordure)
' Vert:   #ECFDF5 (fond) / #34A853 (bordure)
' Violet: #F3EEFF (fond) / #7C5CFC (bordure)
' Gris:   #F5F5F5 (fond) / #CCCCCC (bordure)

' --- Component ---
skinparam component {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
}

' --- Package ---
skinparam package {
  BackgroundColor #F5F5F5
  BorderColor #4A6FA5
  FontColor #333333
}

' --- Class ---
skinparam class {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
  HeaderBackgroundColor #34A853
  HeaderFontColor white
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
  AttributeFontColor #555555
}

' --- Sequence ---
skinparam sequence {
  ArrowColor #4A6FA5
  ActorBorderColor #7C5CFC
  LifeLineBorderColor #CCCCCC
  LifeLineBackgroundColor #F5F5F5
  ParticipantBorderColor #4A6FA5
  ParticipantBackgroundColor #F3EEFF
  ParticipantFontColor #333333
  BoxBorderColor #CCCCCC
  BoxBackgroundColor #F5F5F5
  DividerBackgroundColor #4A6FA5
  DividerFontColor white
}

' --- Activity ---
skinparam activity {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
  DiamondBackgroundColor #F3EEFF
  DiamondBorderColor #7C5CFC
}

' --- Node (deployment) ---
skinparam node {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
}

' --- Database ---
skinparam database {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
}

' --- Entity (ER) ---
skinparam entity {
  BackgroundColor white
  BorderColor #4A6FA5
  FontColor #333333
  HeaderBackgroundColor #4A6FA5
  HeaderFontColor white
}

' --- State ---
skinparam state {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
}

' --- Usecase ---
skinparam usecase {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  ActorBorderColor #E8943A
}

' --- Note ---
skinparam note {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
}

' --- Legend ---
skinparam legend {
  BackgroundColor #F5F5F5
  BorderColor #CCCCCC
  FontColor #333333
}

' --- Stereotypes ---
' <<collector>>   ETL data collectors
' <<transformer>> ETL data transformers
' <<loader>>      ETL data loaders
' <<scheduler>>   APScheduler jobs
' <<rule>>        ML rule evaluator
' <<model>>       ML model
' <<router>>      FastAPI router
' <<service>>     FastAPI service
' <<middleware>>   FastAPI middleware
' <<page>>        Streamlit page
' <<component>>   Streamlit/Plotly component
' <<hypertable>>  TimescaleDB hypertable
' <<phase2>>      Phase 2 planned feature

@enduml


title CryptoBot — Schema Base de Donnees TimescaleDB
caption 9 tables | 2 hypertables | PostgreSQL 16

' ============================================================
' Tables
' ============================================================

entity "users" as users {
  * **id** : UUID <<PK>>
  --
  * username : VARCHAR(100) <<UNIQUE>>
  * email : VARCHAR(255) <<UNIQUE>>
  * password_hash : VARCHAR(255)
  persona_type : VARCHAR(50)
  preferences : JSON
  created_at : TIMESTAMP
  ..
  <<CHECK>> persona_type IN
  ('trader','journalist','investor')
}

entity "crypto_prices" as prices <<hypertable>> {
  * **symbol** : VARCHAR(20) <<PK>>
  * **timeframe** : VARCHAR(10) <<PK>>
  * **timestamp** : TIMESTAMP <<PK>>
  --
  * price_open : NUMERIC(20,8)
  * price_high : NUMERIC(20,8)
  * price_low : NUMERIC(20,8)
  * price_close : NUMERIC(20,8)
  * volume_24h : NUMERIC(20,8)
  market_cap : NUMERIC(20,8)
  * source : VARCHAR(50)
  ..
  <<INDEX>> (symbol, timeframe, timestamp)
  <<HYPERTABLE>> retention=90d, compress=7d
}

entity "indicators" as indicators {
  * **id** : UUID <<PK>>
  --
  * symbol : VARCHAR(20)
  * timeframe : VARCHAR(10)
  * timestamp : TIMESTAMP
  rsi : NUMERIC(5,2)
  bollinger_upper : NUMERIC(20,8)
  bollinger_middle : NUMERIC(20,8)
  bollinger_lower : NUMERIC(20,8)
  price_vs_bollinger : NUMERIC(5,4)
  harmonic_pattern : VARCHAR(50)
  trend_slope : NUMERIC(10,4)
  trend_type : VARCHAR(20)
  metadata : JSON
  ..
  <<INDEX>> (symbol, timeframe, timestamp)
  <<CHECK>> rsi BETWEEN 0 AND 100
  <<CHECK>> price_vs_bollinger BETWEEN -1 AND 1
}

entity "trading_signals" as signals {
  * **id** : UUID <<PK>>
  --
  * symbol : VARCHAR(20)
  * signal_type : VARCHAR(10)
  * confidence_score : NUMERIC(5,4)
  timeframe_primary : VARCHAR(10)
  timeframes_aligned : JSON
  rules_triggered : JSON
  leverage_suggested : INTEGER
  margin_safety : NUMERIC(5,4)
  fees_estimated : NUMERIC(10,8)
  model_version : VARCHAR(50)
  created_at : TIMESTAMP
  ..
  <<CHECK>> signal_type IN ('BUY','SELL','HOLD')
  <<CHECK>> confidence_score BETWEEN 0 AND 1
  <<CHECK>> leverage_suggested BETWEEN 1 AND 20
}

entity "signal_outcomes" as outcomes {
  * **id** : UUID <<PK>>
  --
  * signal_id : UUID <<FK>>
  * price_at_signal : NUMERIC(20,8)
  price_after_1h : NUMERIC(20,8)
  price_after_4h : NUMERIC(20,8)
  price_after_1d : NUMERIC(20,8)
  pnl_simulated : NUMERIC(10,4)
  was_correct : BOOLEAN
  evaluated_at : TIMESTAMP
  ..
  <<INDEX>> (signal_id, was_correct)
}

entity "portfolio" as portfolio {
  * **id** : UUID <<PK>>
  --
  * user_id : UUID <<FK>>
  * symbol : VARCHAR(20)
  * quantity : NUMERIC(20,8)
  * entry_price : NUMERIC(20,8)
  * current_price : NUMERIC(20,8)
  notes : TEXT
  ..
  <<INDEX>> (user_id)
}

entity "watchlist" as watchlist {
  * **id** : UUID <<PK>>
  --
  * user_id : UUID <<FK>>
  * symbol : VARCHAR(20)
  added_at : TIMESTAMP
  ..
  <<UNIQUE>> (user_id, symbol)
}

entity "news_articles" as news {
  * **id** : UUID <<PK>>
  --
  * title : VARCHAR(500)
  content : TEXT
  * source : VARCHAR(100)
  url : VARCHAR(1000) <<UNIQUE>>
  published_at : TIMESTAMP
  sentiment_score : NUMERIC(5,4)
  keywords : JSON
  reliability_score : NUMERIC(5,4)
  ..
  <<INDEX>> (published_at, source)
  <<CHECK>> sentiment_score BETWEEN -1 AND 1
}

entity "text_mining_results" as textmining {
  * **id** : UUID <<PK>>
  --
  * article_id : UUID <<FK>>
  word_cloud : JSON
  * summary : TEXT
  entities : JSON
  topics : JSON
  created_at : TIMESTAMP
}

' ============================================================
' Relations
' ============================================================
users ||--o{ portfolio : "1 user → N entries"
users ||--o{ watchlist : "1 user → N symbols"
signals ||--o| outcomes : "1 signal → 0..1 outcome"
news ||--o| textmining : "1 article → 0..1 mining"

' Foreign key cascades
portfolio }o--|| users : "ON DELETE CASCADE"
watchlist }o--|| users : "ON DELETE CASCADE"
outcomes }o--|| signals : "ON DELETE CASCADE"
textmining }o--|| news : "ON DELETE CASCADE"

' ============================================================
' Legend
' ============================================================
legend bottom right
  |= Annotation |= Signification |
  | <<hypertable>> | TimescaleDB hypertable |
  | <<PK>> | Primary Key |
  | <<FK>> | Foreign Key (CASCADE) |
  | <<UNIQUE>> | Contrainte unique |
  | <<CHECK>> | Contrainte de domaine |
  | <<INDEX>> | Index composite |
endlegend

@enduml
```

## SQ01-auth-jwt-flow
> Explications : [[CryptoBot/avril/architecture/sq01-auth-jwt-flow]]

```plantuml
@startuml SQ01-auth-jwt-flow
@startuml _common
' ============================================================
' CryptoBot — PlantUML Shared Skin & Stereotypes
' ============================================================

' --- Theme clair (lisible GitHub) ---
skinparam backgroundColor white
skinparam defaultFontName "Segoe UI, Helvetica, Arial, sans-serif"
skinparam defaultFontSize 12
skinparam defaultFontColor #333333
skinparam shadowing false
skinparam roundCorner 6

' --- Palette ---
' Bleu:   #4A6FA5
' Orange: #FEF3E8 (fond) / #E8943A (bordure)
' Vert:   #ECFDF5 (fond) / #34A853 (bordure)
' Violet: #F3EEFF (fond) / #7C5CFC (bordure)
' Gris:   #F5F5F5 (fond) / #CCCCCC (bordure)

' --- Component ---
skinparam component {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
}

' --- Package ---
skinparam package {
  BackgroundColor #F5F5F5
  BorderColor #4A6FA5
  FontColor #333333
}

' --- Class ---
skinparam class {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
  HeaderBackgroundColor #34A853
  HeaderFontColor white
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
  AttributeFontColor #555555
}

' --- Sequence ---
skinparam sequence {
  ArrowColor #4A6FA5
  ActorBorderColor #7C5CFC
  LifeLineBorderColor #CCCCCC
  LifeLineBackgroundColor #F5F5F5
  ParticipantBorderColor #4A6FA5
  ParticipantBackgroundColor #F3EEFF
  ParticipantFontColor #333333
  BoxBorderColor #CCCCCC
  BoxBackgroundColor #F5F5F5
  DividerBackgroundColor #4A6FA5
  DividerFontColor white
}

' --- Activity ---
skinparam activity {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
  DiamondBackgroundColor #F3EEFF
  DiamondBorderColor #7C5CFC
}

' --- Node (deployment) ---
skinparam node {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
}

' --- Database ---
skinparam database {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
}

' --- Entity (ER) ---
skinparam entity {
  BackgroundColor white
  BorderColor #4A6FA5
  FontColor #333333
  HeaderBackgroundColor #4A6FA5
  HeaderFontColor white
}

' --- State ---
skinparam state {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
}

' --- Usecase ---
skinparam usecase {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  ActorBorderColor #E8943A
}

' --- Note ---
skinparam note {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
}

' --- Legend ---
skinparam legend {
  BackgroundColor #F5F5F5
  BorderColor #CCCCCC
  FontColor #333333
}

' --- Stereotypes ---
' <<collector>>   ETL data collectors
' <<transformer>> ETL data transformers
' <<loader>>      ETL data loaders
' <<scheduler>>   APScheduler jobs
' <<rule>>        ML rule evaluator
' <<model>>       ML model
' <<router>>      FastAPI router
' <<service>>     FastAPI service
' <<middleware>>   FastAPI middleware
' <<page>>        Streamlit page
' <<component>>   Streamlit/Plotly component
' <<hypertable>>  TimescaleDB hypertable
' <<phase2>>      Phase 2 planned feature

@enduml


title CryptoBot — Authentification JWT
caption POST /api/v1/auth/register + login + me

actor "Client" as client
participant "Nginx" as nginx #F5F5F5
participant "FastAPI\nauth router" as api #FEF3E8
participant "auth_service" as svc #F3EEFF
database "TimescaleDB\nusers" as db #ECFDF5

== Register ==
client -> nginx : POST /api/v1/auth/register
nginx -> api : proxy
api -> svc : register_user(UserCreate)
svc -> svc : hash_password(bcrypt)
svc -> db : INSERT users
db --> svc : UserOrm
svc --> api : UserOrm
api --> client : 201 UserResponse

== Login ==
client -> nginx : POST /api/v1/auth/login
nginx -> api : proxy
api -> svc : authenticate_user(email, password)
svc -> db : SELECT user BY email
db --> svc : UserOrm
svc -> svc : verify_password(bcrypt)
alt Password valid
  svc -> svc : create_access_token(JWT HS256)
  svc --> api : access_token
  api --> client : 200 LoginResponse\n{access_token, token_type: "bearer"}
else Password invalid
  svc --> api : AuthenticationError
  api --> client : 401 Unauthorized
end

== Authenticated Request ==
client -> nginx : GET /api/v1/auth/me\nAuthorization: Bearer <token>
nginx -> api : proxy
api -> api : get_current_user()\ndecode JWT
alt Token valid
  api -> db : SELECT user BY id
  db --> api : UserOrm
  api --> client : 200 UserResponse
else Token expired/invalid
  api --> client : 401 AuthenticationError
end

@enduml
```

## SQ02-dashboard-request
> Explications : [[CryptoBot/avril/architecture/sq02-dashboard-request]]

```plantuml
@startuml SQ02-dashboard-request
@startuml _common
' ============================================================
' CryptoBot — PlantUML Shared Skin & Stereotypes
' ============================================================

' --- Theme clair (lisible GitHub) ---
skinparam backgroundColor white
skinparam defaultFontName "Segoe UI, Helvetica, Arial, sans-serif"
skinparam defaultFontSize 12
skinparam defaultFontColor #333333
skinparam shadowing false
skinparam roundCorner 6

' --- Palette ---
' Bleu:   #4A6FA5
' Orange: #FEF3E8 (fond) / #E8943A (bordure)
' Vert:   #ECFDF5 (fond) / #34A853 (bordure)
' Violet: #F3EEFF (fond) / #7C5CFC (bordure)
' Gris:   #F5F5F5 (fond) / #CCCCCC (bordure)

' --- Component ---
skinparam component {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
}

' --- Package ---
skinparam package {
  BackgroundColor #F5F5F5
  BorderColor #4A6FA5
  FontColor #333333
}

' --- Class ---
skinparam class {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
  HeaderBackgroundColor #34A853
  HeaderFontColor white
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
  AttributeFontColor #555555
}

' --- Sequence ---
skinparam sequence {
  ArrowColor #4A6FA5
  ActorBorderColor #7C5CFC
  LifeLineBorderColor #CCCCCC
  LifeLineBackgroundColor #F5F5F5
  ParticipantBorderColor #4A6FA5
  ParticipantBackgroundColor #F3EEFF
  ParticipantFontColor #333333
  BoxBorderColor #CCCCCC
  BoxBackgroundColor #F5F5F5
  DividerBackgroundColor #4A6FA5
  DividerFontColor white
}

' --- Activity ---
skinparam activity {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
  DiamondBackgroundColor #F3EEFF
  DiamondBorderColor #7C5CFC
}

' --- Node (deployment) ---
skinparam node {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
}

' --- Database ---
skinparam database {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
}

' --- Entity (ER) ---
skinparam entity {
  BackgroundColor white
  BorderColor #4A6FA5
  FontColor #333333
  HeaderBackgroundColor #4A6FA5
  HeaderFontColor white
}

' --- State ---
skinparam state {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
}

' --- Usecase ---
skinparam usecase {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  ActorBorderColor #E8943A
}

' --- Note ---
skinparam note {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
}

' --- Legend ---
skinparam legend {
  BackgroundColor #F5F5F5
  BorderColor #CCCCCC
  FontColor #333333
}

' --- Stereotypes ---
' <<collector>>   ETL data collectors
' <<transformer>> ETL data transformers
' <<loader>>      ETL data loaders
' <<scheduler>>   APScheduler jobs
' <<rule>>        ML rule evaluator
' <<model>>       ML model
' <<router>>      FastAPI router
' <<service>>     FastAPI service
' <<middleware>>   FastAPI middleware
' <<page>>        Streamlit page
' <<component>>   Streamlit/Plotly component
' <<hypertable>>  TimescaleDB hypertable
' <<phase2>>      Phase 2 planned feature

@enduml


title CryptoBot — Chargement Page Dashboard
caption Streamlit -> APIClient -> FastAPI multi-endpoint

actor "Noah" as user
participant "Streamlit\nDashboard" as st #FEF3E8
participant "APIClient" as client #F3EEFF
participant "FastAPI" as api #FEF3E8
participant "crypto_service" as csvc #F3EEFF
participant "signal_service" as ssvc #F3EEFF
database "TimescaleDB" as db #ECFDF5

user -> st : Ouvre Dashboard
st -> st : st.set_page_config()

== Chargement parallele ==
st -> client : get_crypto_list()
client -> api : GET /api/v1/crypto/list
api -> csvc : list_tracked()
csvc --> api : list[CryptoListItem]
api --> client : 200

st -> client : get_prices(symbol, "4h")
client -> api : GET /api/v1/crypto/{symbol}/prices?timeframe=4h
api -> csvc : get_prices(symbol, "4h")
csvc -> db : SELECT crypto_prices
db --> csvc : rows
csvc --> api : list[OHLCVResponse]
api --> client : 200

st -> client : get_indicators(symbol, "4h")
client -> api : GET /api/v1/crypto/{symbol}/indicators
api -> csvc : get_indicators()
csvc -> db : SELECT indicators
db --> csvc : rows
csvc --> api : list[IndicatorResponse]
api --> client : 200

st -> client : get_active_signals()
client -> api : GET /api/v1/signals/active
api -> ssvc : get_active()
ssvc -> db : SELECT signals last 24h
db --> ssvc : rows
ssvc --> api : list[SignalResponse]
api --> client : 200

== Rendu ==
st -> st : CandlestickChart(prices, indicators)
st -> st : SignalCard(signals)
st -> st : IndicatorPanel(indicators)
st --> user : Dashboard complet

@enduml
```

## SQ03-signal-generation
> Explications : [[CryptoBot/avril/architecture/sq03-signal-generation]]

```plantuml
@startuml SQ03-signal-generation
@startuml _common
' ============================================================
' CryptoBot — PlantUML Shared Skin & Stereotypes
' ============================================================

' --- Theme clair (lisible GitHub) ---
skinparam backgroundColor white
skinparam defaultFontName "Segoe UI, Helvetica, Arial, sans-serif"
skinparam defaultFontSize 12
skinparam defaultFontColor #333333
skinparam shadowing false
skinparam roundCorner 6

' --- Palette ---
' Bleu:   #4A6FA5
' Orange: #FEF3E8 (fond) / #E8943A (bordure)
' Vert:   #ECFDF5 (fond) / #34A853 (bordure)
' Violet: #F3EEFF (fond) / #7C5CFC (bordure)
' Gris:   #F5F5F5 (fond) / #CCCCCC (bordure)

' --- Component ---
skinparam component {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
}

' --- Package ---
skinparam package {
  BackgroundColor #F5F5F5
  BorderColor #4A6FA5
  FontColor #333333
}

' --- Class ---
skinparam class {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
  HeaderBackgroundColor #34A853
  HeaderFontColor white
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
  AttributeFontColor #555555
}

' --- Sequence ---
skinparam sequence {
  ArrowColor #4A6FA5
  ActorBorderColor #7C5CFC
  LifeLineBorderColor #CCCCCC
  LifeLineBackgroundColor #F5F5F5
  ParticipantBorderColor #4A6FA5
  ParticipantBackgroundColor #F3EEFF
  ParticipantFontColor #333333
  BoxBorderColor #CCCCCC
  BoxBackgroundColor #F5F5F5
  DividerBackgroundColor #4A6FA5
  DividerFontColor white
}

' --- Activity ---
skinparam activity {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
  DiamondBackgroundColor #F3EEFF
  DiamondBorderColor #7C5CFC
}

' --- Node (deployment) ---
skinparam node {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
}

' --- Database ---
skinparam database {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
}

' --- Entity (ER) ---
skinparam entity {
  BackgroundColor white
  BorderColor #4A6FA5
  FontColor #333333
  HeaderBackgroundColor #4A6FA5
  HeaderFontColor white
}

' --- State ---
skinparam state {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
}

' --- Usecase ---
skinparam usecase {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  ActorBorderColor #E8943A
}

' --- Note ---
skinparam note {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
}

' --- Legend ---
skinparam legend {
  BackgroundColor #F5F5F5
  BorderColor #CCCCCC
  FontColor #333333
}

' --- Stereotypes ---
' <<collector>>   ETL data collectors
' <<transformer>> ETL data transformers
' <<loader>>      ETL data loaders
' <<scheduler>>   APScheduler jobs
' <<rule>>        ML rule evaluator
' <<model>>       ML model
' <<router>>      FastAPI router
' <<service>>     FastAPI service
' <<middleware>>   FastAPI middleware
' <<page>>        Streamlit page
' <<component>>   Streamlit/Plotly component
' <<hypertable>>  TimescaleDB hypertable
' <<phase2>>      Phase 2 planned feature

@enduml


title CryptoBot — Pipeline Generation de Signaux
caption APScheduler -> RuleEngine -> SignalGenerator -> DB

participant "APScheduler" as sched #F5F5F5
participant "SignalGenerator" as gen #FEF3E8
participant "RuleEngine" as engine #F3EEFF
participant "Evaluators\n(RSI, BB, Harm, Trend)" as eval #F3EEFF
participant "Predictor\n(Phase 2)" as ml #FEF3E8
participant "NLP\nSentiment" as nlp #F3EEFF
database "TimescaleDB" as db #ECFDF5

sched -> gen : generate_signals_for_symbols(symbols)

loop for each symbol
  gen -> db : fetch indicators\nmulti-timeframe
  db --> gen : indicators dict

  gen -> engine : evaluate(symbol, indicators)
  engine -> eval : evaluate_rsi()
  eval --> engine : RuleResult | None
  engine -> eval : evaluate_bollinger()
  eval --> engine : RuleResult | None
  engine -> eval : evaluate_harmonic()
  eval --> engine : RuleResult | None
  engine -> eval : evaluate_trend()
  eval --> engine : RuleResult | None
  engine -> eval : convergence checks
  eval --> engine : list[RuleResult]

  engine -> engine : aggregate()\nweighted: RSI=0.25\nBB=0.25, Harm=0.30\nTrend=0.20

  alt confidence >= 0.6
    engine --> gen : RuleResult[]

    opt Predictor available (Phase 2)
      gen -> ml : predict(features)
      ml --> gen : {direction, confidence}
      gen -> gen : blend_confidences()\nsame dir: 60% ML + 40% rules\nconflict: 40% * min
    end

    opt News sentiment available
      gen -> nlp : get_sentiment(symbol)
      nlp --> gen : score [-1, 1]
      gen -> gen : adjust +/- 5pp
    end

    gen -> gen : suggest_leverage(1-20)
    gen -> gen : estimate_fees()
    gen -> gen : verify_margin_safety()

    alt All gates pass
      gen -> db : INSERT trading_signal
      db --> gen : TradingSignalOrm
    else Gate failed
      gen -> gen : discard
    end

  else confidence < 0.6
    engine --> gen : None (below threshold)
  end
end

@enduml
```

## SQ04-chat-llm-flow
> Explications : [[CryptoBot/avril/architecture/sq04-chat-llm-flow]]

```plantuml
@startuml SQ04-chat-llm-flow
@startuml _common
' ============================================================
' CryptoBot — PlantUML Shared Skin & Stereotypes
' ============================================================

' --- Theme clair (lisible GitHub) ---
skinparam backgroundColor white
skinparam defaultFontName "Segoe UI, Helvetica, Arial, sans-serif"
skinparam defaultFontSize 12
skinparam defaultFontColor #333333
skinparam shadowing false
skinparam roundCorner 6

' --- Palette ---
' Bleu:   #4A6FA5
' Orange: #FEF3E8 (fond) / #E8943A (bordure)
' Vert:   #ECFDF5 (fond) / #34A853 (bordure)
' Violet: #F3EEFF (fond) / #7C5CFC (bordure)
' Gris:   #F5F5F5 (fond) / #CCCCCC (bordure)

' --- Component ---
skinparam component {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
}

' --- Package ---
skinparam package {
  BackgroundColor #F5F5F5
  BorderColor #4A6FA5
  FontColor #333333
}

' --- Class ---
skinparam class {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
  HeaderBackgroundColor #34A853
  HeaderFontColor white
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
  AttributeFontColor #555555
}

' --- Sequence ---
skinparam sequence {
  ArrowColor #4A6FA5
  ActorBorderColor #7C5CFC
  LifeLineBorderColor #CCCCCC
  LifeLineBackgroundColor #F5F5F5
  ParticipantBorderColor #4A6FA5
  ParticipantBackgroundColor #F3EEFF
  ParticipantFontColor #333333
  BoxBorderColor #CCCCCC
  BoxBackgroundColor #F5F5F5
  DividerBackgroundColor #4A6FA5
  DividerFontColor white
}

' --- Activity ---
skinparam activity {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
  DiamondBackgroundColor #F3EEFF
  DiamondBorderColor #7C5CFC
}

' --- Node (deployment) ---
skinparam node {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
}

' --- Database ---
skinparam database {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
}

' --- Entity (ER) ---
skinparam entity {
  BackgroundColor white
  BorderColor #4A6FA5
  FontColor #333333
  HeaderBackgroundColor #4A6FA5
  HeaderFontColor white
}

' --- State ---
skinparam state {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
}

' --- Usecase ---
skinparam usecase {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  ActorBorderColor #E8943A
}

' --- Note ---
skinparam note {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
}

' --- Legend ---
skinparam legend {
  BackgroundColor #F5F5F5
  BorderColor #CCCCCC
  FontColor #333333
}

' --- Stereotypes ---
' <<collector>>   ETL data collectors
' <<transformer>> ETL data transformers
' <<loader>>      ETL data loaders
' <<scheduler>>   APScheduler jobs
' <<rule>>        ML rule evaluator
' <<model>>       ML model
' <<router>>      FastAPI router
' <<service>>     FastAPI service
' <<middleware>>   FastAPI middleware
' <<page>>        Streamlit page
' <<component>>   Streamlit/Plotly component
' <<hypertable>>  TimescaleDB hypertable
' <<phase2>>      Phase 2 planned feature

@enduml


title CryptoBot — Flux Chatbot LLM
caption Streamlit -> FastAPI -> ChatService -> LLM

actor "Aleksandar\n(debutant)" as user
participant "Streamlit\nPortfolio page" as st #FEF3E8
participant "ChatbotWidget" as widget #F3EEFF
participant "APIClient" as client #F3EEFF
participant "FastAPI\nchat router" as api #FEF3E8
participant "ChatService" as svc #F3EEFF
participant "LLM\n(Claude / OpenAI)" as llm #F5F5F5
database "TimescaleDB" as db #ECFDF5

user -> st : Ouvre page Portfolio
st -> widget : Affiche chatbot

user -> widget : "Quel est le meilleur\nmoment pour acheter BTC?"
widget -> client : post_chat(message)
client -> api : POST /api/v1/chat\n{message: "..."}

api -> svc : process(message)

svc -> db : Fetch context\n(portfolio, signals, prices)
db --> svc : user context

svc -> llm : Prompt + context\n+ system instructions
note right of llm
  System: "Tu es un assistant
  crypto informatif.
  Ne jamais recommander
  d'acheter ou vendre."
end note

llm --> svc : response text

svc -> svc : Add disclaimer\n"Ceci n'est pas un\nconseil financier"

svc --> api : ChatResponse
api --> client : 200 {response: "..."}
client --> widget : display response
widget --> user : Reponse + disclaimer

@enduml
```

## ST01-signal-states
> Explications : [[CryptoBot/avril/architecture/st01-signal-states]]

```plantuml
@startuml ST01-signal-states
@startuml _common
' ============================================================
' CryptoBot — PlantUML Shared Skin & Stereotypes
' ============================================================

' --- Theme clair (lisible GitHub) ---
skinparam backgroundColor white
skinparam defaultFontName "Segoe UI, Helvetica, Arial, sans-serif"
skinparam defaultFontSize 12
skinparam defaultFontColor #333333
skinparam shadowing false
skinparam roundCorner 6

' --- Palette ---
' Bleu:   #4A6FA5
' Orange: #FEF3E8 (fond) / #E8943A (bordure)
' Vert:   #ECFDF5 (fond) / #34A853 (bordure)
' Violet: #F3EEFF (fond) / #7C5CFC (bordure)
' Gris:   #F5F5F5 (fond) / #CCCCCC (bordure)

' --- Component ---
skinparam component {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
}

' --- Package ---
skinparam package {
  BackgroundColor #F5F5F5
  BorderColor #4A6FA5
  FontColor #333333
}

' --- Class ---
skinparam class {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
  HeaderBackgroundColor #34A853
  HeaderFontColor white
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
  AttributeFontColor #555555
}

' --- Sequence ---
skinparam sequence {
  ArrowColor #4A6FA5
  ActorBorderColor #7C5CFC
  LifeLineBorderColor #CCCCCC
  LifeLineBackgroundColor #F5F5F5
  ParticipantBorderColor #4A6FA5
  ParticipantBackgroundColor #F3EEFF
  ParticipantFontColor #333333
  BoxBorderColor #CCCCCC
  BoxBackgroundColor #F5F5F5
  DividerBackgroundColor #4A6FA5
  DividerFontColor white
}

' --- Activity ---
skinparam activity {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
  DiamondBackgroundColor #F3EEFF
  DiamondBorderColor #7C5CFC
}

' --- Node (deployment) ---
skinparam node {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
}

' --- Database ---
skinparam database {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
}

' --- Entity (ER) ---
skinparam entity {
  BackgroundColor white
  BorderColor #4A6FA5
  FontColor #333333
  HeaderBackgroundColor #4A6FA5
  HeaderFontColor white
}

' --- State ---
skinparam state {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
}

' --- Usecase ---
skinparam usecase {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  ActorBorderColor #E8943A
}

' --- Note ---
skinparam note {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
}

' --- Legend ---
skinparam legend {
  BackgroundColor #F5F5F5
  BorderColor #CCCCCC
  FontColor #333333
}

' --- Stereotypes ---
' <<collector>>   ETL data collectors
' <<transformer>> ETL data transformers
' <<loader>>      ETL data loaders
' <<scheduler>>   APScheduler jobs
' <<rule>>        ML rule evaluator
' <<model>>       ML model
' <<router>>      FastAPI router
' <<service>>     FastAPI service
' <<middleware>>   FastAPI middleware
' <<page>>        Streamlit page
' <<component>>   Streamlit/Plotly component
' <<hypertable>>  TimescaleDB hypertable
' <<phase2>>      Phase 2 planned feature

@enduml


title CryptoBot — Machine a Etats d'un Signal
caption TradingSignal lifecycle

[*] --> Computing : APScheduler trigger

state "Computing" as Computing #FEF3E8 {
  state "Evaluating Rules" as eval
  state "Aggregating" as agg
  state "ML Blend" as blend
  state "Validation" as valid

  eval --> agg : RuleResult[]
  agg --> blend : confidence
  blend --> valid : final score
}

Computing --> Discarded : confidence < 0.6\nor gate failed

state "Active" as Active #ECFDF5 {
  Active : symbol, signal_type
  Active : confidence >= 0.6
  Active : leverage, fees
  Active : model_version
}

Computing --> Active : All gates pass\nPersist to DB

state "Evaluation Windows" as EvalWindows #F3EEFF {
  state "After 1h" as ev1h
  state "After 4h" as ev4h
  state "After 1d" as ev1d

  ev1h --> ev4h
  ev4h --> ev1d
}

Active --> EvalWindows : evaluate_signal_outcomes\n(every 1 hour)

state "Evaluated" as Evaluated #ECFDF5 {
  Evaluated : price_after_1h/4h/1d
  Evaluated : pnl_simulated
  Evaluated : was_correct (bool)
}

EvalWindows --> Evaluated : All windows checked

state "Discarded" as Discarded #F5F5F5 {
  Discarded : Below threshold
  Discarded : or gate failure
}

Evaluated --> [*]
Discarded --> [*]

legend bottom right
  |= Etat |= Signification |
  | <#FEF3E8> | Calcul en cours |
  | <#ECFDF5> | Signal actif / evalue |
  | <#F3EEFF> | Fenetres d'evaluation |
  | <#F5F5F5> | Rejete |
endlegend

@enduml
```

## UC01-personas
> Explications : [[CryptoBot/avril/architecture/uc01-personas]]

```plantuml
@startuml UC01-personas
@startuml _common
' ============================================================
' CryptoBot — PlantUML Shared Skin & Stereotypes
' ============================================================

' --- Theme clair (lisible GitHub) ---
skinparam backgroundColor white
skinparam defaultFontName "Segoe UI, Helvetica, Arial, sans-serif"
skinparam defaultFontSize 12
skinparam defaultFontColor #333333
skinparam shadowing false
skinparam roundCorner 6

' --- Palette ---
' Bleu:   #4A6FA5
' Orange: #FEF3E8 (fond) / #E8943A (bordure)
' Vert:   #ECFDF5 (fond) / #34A853 (bordure)
' Violet: #F3EEFF (fond) / #7C5CFC (bordure)
' Gris:   #F5F5F5 (fond) / #CCCCCC (bordure)

' --- Component ---
skinparam component {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
}

' --- Package ---
skinparam package {
  BackgroundColor #F5F5F5
  BorderColor #4A6FA5
  FontColor #333333
}

' --- Class ---
skinparam class {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
  HeaderBackgroundColor #34A853
  HeaderFontColor white
  ArrowColor #4A6FA5
  StereotypeFontColor #7C5CFC
  AttributeFontColor #555555
}

' --- Sequence ---
skinparam sequence {
  ArrowColor #4A6FA5
  ActorBorderColor #7C5CFC
  LifeLineBorderColor #CCCCCC
  LifeLineBackgroundColor #F5F5F5
  ParticipantBorderColor #4A6FA5
  ParticipantBackgroundColor #F3EEFF
  ParticipantFontColor #333333
  BoxBorderColor #CCCCCC
  BoxBackgroundColor #F5F5F5
  DividerBackgroundColor #4A6FA5
  DividerFontColor white
}

' --- Activity ---
skinparam activity {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
  DiamondBackgroundColor #F3EEFF
  DiamondBorderColor #7C5CFC
}

' --- Node (deployment) ---
skinparam node {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
}

' --- Database ---
skinparam database {
  BackgroundColor #ECFDF5
  BorderColor #34A853
  FontColor #333333
}

' --- Entity (ER) ---
skinparam entity {
  BackgroundColor white
  BorderColor #4A6FA5
  FontColor #333333
  HeaderBackgroundColor #4A6FA5
  HeaderFontColor white
}

' --- State ---
skinparam state {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
  ArrowColor #4A6FA5
}

' --- Usecase ---
skinparam usecase {
  BackgroundColor #F3EEFF
  BorderColor #7C5CFC
  FontColor #333333
  ArrowColor #4A6FA5
  ActorBorderColor #E8943A
}

' --- Note ---
skinparam note {
  BackgroundColor #FEF3E8
  BorderColor #E8943A
  FontColor #333333
}

' --- Legend ---
skinparam legend {
  BackgroundColor #F5F5F5
  BorderColor #CCCCCC
  FontColor #333333
}

' --- Stereotypes ---
' <<collector>>   ETL data collectors
' <<transformer>> ETL data transformers
' <<loader>>      ETL data loaders
' <<scheduler>>   APScheduler jobs
' <<rule>>        ML rule evaluator
' <<model>>       ML model
' <<router>>      FastAPI router
' <<service>>     FastAPI service
' <<middleware>>   FastAPI middleware
' <<page>>        Streamlit page
' <<component>>   Streamlit/Plotly component
' <<hypertable>>  TimescaleDB hypertable
' <<phase2>>      Phase 2 planned feature

@enduml


title CryptoBot — Cas d'Utilisation par Persona
caption 3 personas | 5 pages Streamlit

left to right direction

' ============================================================
' Personas
' ============================================================
actor "Noah\n(Trader independant)" as noah #FEF3E8
actor "Sarah\n(Journaliste financiere)" as sarah #F3EEFF
actor "Aleksandar\n(Investisseur debutant)" as aleksandar #ECFDF5

' ============================================================
' Use Cases
' ============================================================
rectangle "CryptoBot" #F5F5F5 {

  package "Dashboard" #FEF3E8 {
    usecase "Consulter charts\nmulti-timeframe" as uc_charts
    usecase "Voir signaux\nBUY/SELL actifs" as uc_signals
    usecase "Analyser indicateurs\nRSI, Bollinger, Trend" as uc_indic
  }

  package "Veille" #F3EEFF {
    usecase "Suivre actualites\ncrypto en temps reel" as uc_news
    usecase "Recevoir alertes\nreglementaires" as uc_reg
    usecase "Voir sentiment\npar source" as uc_sentiment
  }

  package "Portfolio" #ECFDF5 {
    usecase "Gerer positions\n(CRUD)" as uc_portfolio
    usecase "Calculer P&L\nsimule" as uc_pnl
    usecase "Utiliser chatbot\nassistant IA" as uc_chat
  }

  package "Analytics" #FEF3E8 {
    usecase "Voir heatmaps\ncorrelations" as uc_heatmap
    usecase "Analyser volumes\net microstructure" as uc_volume
  }

  package "Performance" #F3EEFF {
    usecase "Consulter historique\nsignaux" as uc_history
    usecase "Voir win rate\net Sharpe ratio" as uc_perf
  }
}

' ============================================================
' Relations
' ============================================================
noah --> uc_charts
noah --> uc_signals
noah --> uc_indic
noah --> uc_heatmap
noah --> uc_history
noah --> uc_perf

sarah --> uc_news
sarah --> uc_reg
sarah --> uc_sentiment
sarah --> uc_heatmap

aleksandar --> uc_portfolio
aleksandar --> uc_pnl
aleksandar --> uc_chat
aleksandar --> uc_signals
aleksandar --> uc_history

@enduml
```

