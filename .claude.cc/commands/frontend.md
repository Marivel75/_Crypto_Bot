# Frontend / UI Team Context

You are working as the Frontend/UI agent for crypto-bot.

## Your Scope

- **Code**: `src/frontend/`
- **Doc**: `docs/04-frontend-ui.md`
- **Commit scope**: `frontend`
- **Do NOT touch**: `src/api/`, `src/etl/`, `src/ml/`

## Architecture

```
src/frontend/
  app.py               # Streamlit multi-page app entry point
  pages/               # dashboard.py, news.py, portfolio.py, analytics.py, performance.py
  components/          # candlestick.py, signal_card.py, indicator_overlay.py
  api_client.py        # ALL backend calls go through here
```

## Data Access Rules

- NEVER connect to TimescaleDB, MinIO, or MLflow directly
- NEVER import from `src/etl/`, `src/ml/`, `src/api/`
- ALL data flows through `api_client.py` which calls the FastAPI backend
- Use `@st.cache_data(ttl=60)` for API responses (respect freshness needs)
- Handle API errors gracefully — show user-friendly messages, never raw stack traces

## Pages

| Page | Persona | Key widgets |
|------|---------|-------------|
| Dashboard | Noah (trader) | Candlestick + indicators, live signals, symbol selector |
| Veille | Sarah (analyst) | News feed, sentiment score, Fear & Greed index |
| Portfolio | Aleksandar (PM) | Holdings tracker, chatbot, P&L chart |
| Analytics | All | Correlation heatmap, cross-asset comparison |
| Performance | All | Signal history, win rate, drawdown chart |

## Charting

- Plotly for all charts (candlestick, line, heatmap, bar)
- Dark theme preferred: `plotly.graph_objects` with `template="plotly_dark"`
- Responsive: use `use_container_width=True`
- Overlay RSI, Bollinger Bands on candlestick charts

## Streamlit Best Practices

- Use `st.session_state` for state that persists across reruns
- Use `st.cache_data` for data fetching, `st.cache_resource` for connections
- Use `st.columns()` for layout — avoid nested columns more than 2 levels deep
- Use `st.empty()` for real-time updating widgets
- Log errors with `logger.error()` — display `st.error()` to user without technical details

## Workflow

1. Read `docs/04-frontend-ui.md` for full UI spec and wireframes
2. Read `src/frontend/api_client.py` to understand available API calls
3. Read `docs/03-backend-api.md` to know what endpoints exist
4. Implement page in `src/frontend/pages/`
5. Extract reusable chart/component to `src/frontend/components/`
6. Run: `ruff check src/frontend/ && mypy src/frontend/ && pytest tests/unit/test_frontend/ -v`
