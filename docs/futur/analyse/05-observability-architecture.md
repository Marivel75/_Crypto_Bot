# Architecture Observability — CryptoBot

**Date:** 2026-03-15
**Status:** A implementer

## Probleme

Seul FastAPI expose /metrics. ETL, ML, Streamlit sont aveugles.

## Solution recommandee

| Composant | Outil | Effort |
|-----------|-------|--------|
| Metriques ETL/ML/Frontend | prometheus_client + HTTP server ports 8081/8082/8083 | 10h |
| Logs centralises | Loki + Promtail (Grafana-natif) | 3.5h |
| Traces distribuees | Phase 1: Correlation IDs, Phase 2: Grafana Tempo | 3h + 4h |
| Dashboards | 3 nouveaux (ETL health, ML signals, Operations Hub) | 6h |
| Alerting | Prometheus AlertManager (8 regles) | 3h |

## Metriques par service

### ETL Worker (port 8081)
- etl_job_duration_seconds (histogram par job)
- etl_records_ingested_total (counter par collector)
- etl_api_errors_total (counter par source)
- etl_rate_limit_hits_total (counter par API)
- etl_data_freshness_seconds (gauge par symbole)

### ML Worker (port 8082)
- ml_signals_generated_total (counter par symbole/direction)
- ml_signal_confidence (histogram)
- ml_model_training_duration_seconds (histogram)
- ml_rule_triggers_total (counter par regle)

### Frontend (port 8083)
- frontend_page_views_total (counter par page)
- frontend_api_latency_ms (histogram par endpoint)
- frontend_errors_total (counter)

## Docker services a ajouter
- loki (256MB)
- promtail (128MB)
- alertmanager (128MB)
- node-exporter (64MB)
- tempo (256MB, optionnel)

## Priorite pour la soutenance
Phase 1 (8h) : metriques ETL/ML + Loki + 3 dashboards = 80% d'impact
