"""Page 5 — ML & Backtesting : évaluation walk-forward des modèles de prédiction."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[2])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import plotly.graph_objects as go
import streamlit as st

from frontend.api_client import APIClient
from frontend.i18n import t

_client = APIClient()

_MODEL_LABELS = {
    "random_forest": "Random Forest",
    "logistic_regression": "Régression Logistique",
    "dummy": "Dummy (référence)",
}

# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------

st.header(t("ml.header"))

with st.expander(t("ml.what_is_title"), expanded=False):
    st.markdown(t("ml.what_is_body"))

st.divider()

# ---------------------------------------------------------------------------
# Sidebar — paramètres
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown(f"### {t('ml.params_title')}")

    @st.cache_data(ttl=300)
    def _fetch_symbols():
        data = _client.fetch_symbols()
        if not data:
            return [], []
        symbols = sorted({r["symbol"] for r in data})
        timeframes = sorted({r["timeframe"] for r in data})
        return symbols, timeframes

    symbols, timeframes = _fetch_symbols()
    symbol = st.selectbox(t("ml.symbol"), symbols or ["BTC/USDT"])
    timeframe = st.selectbox(t("ml.timeframe"), timeframes or ["1d"])
    model_type = st.selectbox(
        t("ml.model_type"),
        list(_MODEL_LABELS.keys()),
        format_func=lambda k: _MODEL_LABELS[k],
    )
    train_window = st.slider(t("ml.train_window"), min_value=30, max_value=365, value=60, step=10)
    test_window = st.slider(t("ml.test_window"), min_value=7, max_value=90, value=15, step=7)

    # Diagnostique : timestamps uniques disponibles (après déduplication des fetches multiples)
    @st.cache_data(ttl=60)
    def _count_unique(sym: str, tf: str) -> int:
        return _client.fetch_distinct_count(sym, tf)

    n_unique = _count_unique(symbol, timeframe)
    min_needed = train_window + 1 + test_window + 1  # 1 fold minimum
    # Estimation conservatrice : retire 60 bougies de warmup indicateurs
    n_usable = max(0, n_unique - 60)
    folds_est = max(0, (n_usable - min_needed) // min_needed + 1) if n_usable >= min_needed else 0
    if n_unique == 0:
        st.warning("Aucune donnée — lancez `fetch_history.py`.")
    elif n_usable < min_needed:
        st.warning(f"{n_unique} bougies uniques ({n_usable} utiles) — il en faut ≥ {min_needed + 60} pour 1 fold.")
    else:
        st.info(f"{n_unique} bougies uniques → ~{folds_est} fold(s) estimé(s).")

    run = st.button(t("ml.run_button"), type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Résultats
# ---------------------------------------------------------------------------

if not run:
    st.info("Configurez les paramètres dans la barre latérale et cliquez sur **Lancer le backtest**.")
    st.stop()

with st.spinner(t("ml.running")):
    result = _client.run_backtest(
        symbol=symbol,
        timeframe=timeframe,
        model_type=model_type,
        train_window=train_window,
        test_window=test_window,
    )

if result is None:
    st.error(t("api.unavailable"))
    st.stop()

if "error" in result:
    st.error(result["error"])
    if "jours" in result["error"] or "données" in result["error"].lower():
        st.info(
            "Réduisez les fenêtres d'entraînement et de test dans la barre latérale, "
            "ou collectez plus de données avec `python main.py`."
        )
    st.stop()

if result.get("summary", {}).get("n_folds", 0) == 0:
    st.warning(t("ml.not_enough_data"))
    st.stop()

summary = result["summary"]
baseline = result["baseline"]
folds = result["folds"]

st.markdown(f"### {t('ml.results_title')}")
st.caption(
    f"{result['symbol']} · {result['timeframe']} · "
    f"{_MODEL_LABELS.get(result['model_type'], result['model_type'])} · "
    f"{result['n_candles']} bougies · {summary['n_folds']} fold(s)"
)

# ---------------------------------------------------------------------------
# KPI cards
# ---------------------------------------------------------------------------

st.markdown(f"#### {t('ml.metrics_title')}")
c1, c2, c3, c4, c5, c6 = st.columns(6)

def _color(val: float, good_above: float = 0, bad_below: float | None = None) -> str:
    if bad_below is not None and val < bad_below:
        return "inverse"
    return "normal" if val >= good_above else "inverse"

with c1, st.container(border=True):
    st.metric(t("ml.metric_sharpe"), f"{summary['sharpe']:.2f}")
with c2, st.container(border=True):
    st.metric(t("ml.metric_winrate"), f"{summary['win_rate']:.1%}")
with c3, st.container(border=True):
    st.metric(t("ml.metric_pnl"), f"{summary['total_pnl']:+.4f}")
with c4, st.container(border=True):
    st.metric(t("ml.metric_drawdown"), f"{summary['max_drawdown']:.1%}")
with c5, st.container(border=True):
    st.metric(t("ml.metric_accuracy"), f"{summary['accuracy']:.1%}")
with c6, st.container(border=True):
    pf = summary.get("profit_factor") or 0.0
    st.metric(t("ml.metric_pf"), "∞" if pf >= 999 else f"{pf:.2f}")

with st.expander(t("ml.metrics_explain_title"), expanded=False):
    st.markdown(t("ml.metrics_explain_body"))

st.divider()

# ---------------------------------------------------------------------------
# Stratégie vs Buy-and-Hold
# ---------------------------------------------------------------------------

st.markdown(f"#### {t('ml.baseline_title')}")
col_chart, col_values = st.columns([2, 1])

with col_chart:
    strat_pnl = baseline["strategy_pnl"]
    bah_return = baseline["baseline_return"]
    excess = baseline["excess_return"]

    colors = ["#22c55e" if strat_pnl >= 0 else "#ef4444", "#94a3b8"]
    fig = go.Figure(go.Bar(
        x=[t("ml.baseline_strategy"), t("ml.baseline_bah")],
        y=[strat_pnl, bah_return],
        marker_color=colors,
        text=[f"{strat_pnl:+.4f}", f"{bah_return:+.4f}"],
        textposition="outside",
    ))
    fig.update_layout(
        height=280,
        yaxis_title="Rendement cumulé",
        yaxis_zeroline=True,
        paper_bgcolor="#0d1117",
        plot_bgcolor="#0d1117",
        font={"color": "#e6edf3"},
        margin={"t": 20, "b": 20},
    )
    st.plotly_chart(fig, use_container_width=True)

with col_values:
    st.markdown("<br>", unsafe_allow_html=True)
    excess_color = "#22c55e" if excess >= 0 else "#ef4444"
    st.markdown(
        f"**{t('ml.baseline_excess')}**<br>"
        f'<span style="font-size:1.6em;font-weight:700;color:{excess_color}">'
        f"{excess:+.4f}</span>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Positif = la stratégie ML surperforme le buy-and-hold. "
        "Négatif = mieux vaut ne rien faire."
    )

st.divider()

# ---------------------------------------------------------------------------
# PnL par fold
# ---------------------------------------------------------------------------

st.markdown(f"#### {t('ml.folds_title')}")

fold_nums = [f"Fold {f['fold']}" for f in folds]
fold_pnls = [f["pnl"] for f in folds]
fold_colors = ["#22c55e" if p >= 0 else "#ef4444" for p in fold_pnls]

fig2 = go.Figure(go.Bar(
    x=fold_nums,
    y=fold_pnls,
    marker_color=fold_colors,
    text=[f"{p:+.4f}" for p in fold_pnls],
    textposition="outside",
))
fig2.update_layout(
    height=260,
    yaxis_title="PnL (log-returns)",
    yaxis_zeroline=True,
    paper_bgcolor="#0d1117",
    plot_bgcolor="#0d1117",
    font={"color": "#e6edf3"},
    margin={"t": 10, "b": 10},
)
st.plotly_chart(fig2, use_container_width=True)

# Tableau détaillé
import pandas as pd

df_folds = pd.DataFrame([{
    "Fold": f["fold"],
    "Test début": str(f["test_start"])[:10],
    "Test fin": str(f["test_end"])[:10],
    "n train": f["n_train"],
    "n test": f["n_test"],
    "Accuracy": f"{f['accuracy']:.1%}",
    "Win rate": f"{f['win_rate']:.1%}",
    "PnL": f"{f['pnl']:+.4f}",
    "Sharpe": f"{f['sharpe']:.2f}",
    "Drawdown": f"{f['max_drawdown']:.1%}",
} for f in folds])

st.dataframe(df_folds, use_container_width=True, hide_index=True)
