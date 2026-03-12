# Frontend / UI Rules

## Scope: `src/frontend/`

## Streamlit
- App entry point: `src/frontend/app.py`
- Pages in `src/frontend/pages/` (multi-page Streamlit app)
- Reusable components in `src/frontend/components/`
- API client in `src/frontend/api_client.py`

## Data Access
- NEVER access the database directly
- ALL data flows through the FastAPI backend via `api_client.py`
- Use `st.cache_data` for API responses with appropriate TTL
- Handle API errors gracefully with user-friendly messages

## Plotly Charts
- Candlestick charts with OHLCV data
- Indicator overlays (RSI, Bollinger bands)
- Responsive layouts
- Dark theme preferred

## Pages
1. Dashboard (Noah) — bougies, indicateurs, signaux
2. Veille (Sarah) — fil de news, sentiment, alertes
3. Portfolio (Aleksandar) — suivi portefeuille, chatbot
4. Analytics — heatmap, correlations
5. Performance — historique signaux, metriques

## DO NOT
- Import from `src/etl/`, `src/ml/`, `src/api/`
- Connect to TimescaleDB, MinIO, or MLflow directly
- Use JavaScript frameworks (React, Vue) — Streamlit only
