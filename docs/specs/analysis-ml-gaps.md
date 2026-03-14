# Analyse des Manques ML — CryptoBot

**Auteur :** Analyst ML
**Date :** 2026-03-14
**Scope :** `src/ml/`
**Status :** Analyse détaillée des trois composantes ML manquantes

---

## Contexte & Découverte

Le cadrage PDF V2 (p.4, tableau "Modélisation et algorithmes de machine learning") exige explicitement **trois pistes à explorer** :
- Apprentissage **supervisé** (✓ en place : XGBoost, LightGBM)
- Apprentissage **non supervisé** (✗ manquant : clustering)
- Apprentissage **par renforcement** (✗ manquant : RL pour paper trading)

Actuellement, le projet est à **67% de conformité**. Les trois manques ML représentent la majorité du 33% restant.

L'ADR du projet exclut les "algorithmes RL dépréciés" (Monte Carlo tabular, Q-learning), mais le cadrage PDF demande explicitement le RL. Cette analyse propose une résolution compatible avec les deux contraintes : RL moderne (DQN) + cadrage formel pour paper trading.

---

## 1. DEEP LEARNING LSTM — Capture des Dépendances Temporelles

### 1.1 Justification Métier

**Problème fondamental :** Les signaux de trading dépendent de **séquences temporelles**, pas d'observations isolées.

Le rule engine actuel traite chaque timeframe indépendamment. Une RSI overbought à 4h n'a pas le même sens si elle s'améliore vs se détériore. Les LSTMs capturent cette **dynamique temporelle** dans les séries d'indicateurs.

**Cadrage :** RF-ML-012 (Priorité COULD — Phase 2+)

### 1.2 Architecture Technique

#### 1.2.1 Lookback Window & Sequence Length
- **Longueur séquence :** 20 candles (80 heures @ 4h candles)
- **Justification :** ~3.3 jours d'historique = période pertinente pour convergences multi-TF sans surapprentissage
- **Features par timestep :** 24 features (voir section 1.2.2)

#### 1.2.2 Features d'Entrée

**Données normalisées (MinMaxScaler par timeframe)** :
```
Per timeframe (1h, 4h, 1D):
- RSI (0-100 → 0-1)
- Bollinger position (-1 to +1)
- Bollinger bandwidth (0-1)
- Trend slope (normalized)
- Volume ratio (log-normalized)

Synthétiques:
- RSI gap (adjacent TFs)
- Bollinger squeeze flag
- Harmonic pattern one-hot (4 catégories)

Cross-asset:
- Fear & Greed index (-1 to 1)
- News sentiment (-1 to 1)

Total: 8 * 3TF + 4 synthetic + 2 sentiment = ~30 features
```

**Preprocessing critique :**
- Temporal scaling : normaliser par rolling mean/std per symbol (volatility-adjusted)
- **PAS de data leakage** : scaler fit sur train window UNIQUEMENT
- Missing values : forward-fill max 2 candles, then drop

#### 1.2.3 Architecture LSTM

```python
Input: (batch, lookback=20, features=30)
    ↓
LSTM Layer 1: units=64, return_sequences=True
    + Dropout(0.3) — prevent overfitting
    ↓
LSTM Layer 2: units=64, return_sequences=False
    + Dropout(0.3)
    ↓
Dense Layer: units=128, activation=ReLU
    + BatchNormalization
    + Dropout(0.2)
    ↓
Dense Layer: units=3, activation=softmax
Output: (batch, 3) → [P(BUY), P(SELL), P(HOLD)]
```

**Rationale architecture :**
- 2 LSTM layers : capture patterns à court + long terme
- 64 units : trade-off entre expressivité et overfitting (données limitées)
- Dropout = 0.3-0.2 : regulatory overfitting on sequences
- Output softmax : probabilité classe (compatible signal_generator blending)

#### 1.2.4 Training Configuration

```python
Loss function: categorical_crossentropy
  (multi-class classification)

Optimizer: Adam(learning_rate=1e-3, beta_1=0.9, beta_2=0.999)
  + Gradient clipping (max_norm=1.0) — prevent exploding gradients on sequences

Batch size: 32
  (balance memory vs gradient stability)

Callbacks:
  - EarlyStopping(monitor='val_loss', patience=15, restore_best_weights=True)
  - ModelCheckpoint(save_best_only=True, save_weights_only=False)
  - ReduceLROnPlateau(factor=0.5, patience=5) — adaptive learning

Epochs: 200 (early stopping typically stops ~80-100)

Validation: temporal split
  - Train: [0:0.8 * n_sequences]
  - Validation: [0.8 * n_sequences:n_sequences]
  (NEVER random split on time-series)
```

#### 1.2.5 Target Variable

**Label construction (from rules engine output) :**
```python
rule_direction = rule_engine.evaluate(...)  # "BUY", "SELL", "HOLD"
confidence = rule_direction["confidence"]

# Multi-label target: only if confidence >= 0.6 (cadre condition)
if confidence >= 0.6 and rule_direction in ["BUY", "SELL"]:
    label = 0 if rule_direction == "BUY" else 1  # binary classification
else:
    label = 2  # HOLD (null class)
```

**Why three classes :**
- LSTM must learn to output HOLD (low confidence) as well
- Signal generator filters by confidence ≥ 0.6 anyway
- Prevents model from always forcing BUY/SELL

#### 1.2.6 Integration with Signal Generator

```python
# In signal_generator.py, add optional LSTM predictor

class LSTMPredictor(Predictor):  # implements Protocol
    def __init__(self, model_path: str, scaler_path: str):
        self._model = tf.keras.models.load_model(model_path)
        self._scaler = joblib.load(scaler_path)

    def predict(self, features: pd.DataFrame) -> list[dict[str, Any]]:
        """
        features: (n_samples, lookback, n_features) from feature_engineering
        returns: [{"direction": "BUY"|"SELL"|"HOLD", "confidence": float, "source": "lstm_v1"}]
        """
        normalized = self._scaler.transform(features)
        proba = self._model.predict(normalized[np.newaxis, ...])  # (1, 3)

        class_idx = np.argmax(proba[0])
        direction = ["BUY", "SELL", "HOLD"][class_idx]
        confidence = float(proba[0, class_idx])

        return [{
            "direction": direction,
            "confidence": confidence,
            "source": "lstm_v1"
        }]
```

### 1.3 File Structure & Dependencies

**New files to create :**
```
src/ml/models/
  ├── lstm_trainer.py          (NEW — training orchestration)
  ├── lstm_predictor.py        (NEW — inference wrapper)
  └── scaler_manager.py        (NEW — feature normalization lifecycle)

src/ml/
  ├── config/
  │   └── lstm_config.yaml     (NEW — hyperparams, validation splits)
  └── features/
      └── sequence_builder.py  (NEW — convert flat indicators → sequences)

tests/unit/
  ├── test_lstm_trainer.py     (NEW)
  ├── test_lstm_predictor.py   (NEW)
  └── test_sequence_builder.py (NEW)

tests/integration/
  └── test_lstm_integration.py (NEW — e2e with backtesting)
```

**Python dependencies (add to `src/ml/requirements.txt`) :**
```
tensorflow>=2.13,<3.0    # or torch>=2.0 (see 1.4)
keras-core>=0.3.0         # backend abstraction
scikit-learn>=1.4,<2.0    # MinMaxScaler (already present)
joblib>=1.3,<2.0          # scaler serialization (already present)
```

**Alternative: PyTorch**
```
torch>=2.0,<3.0
torch-tb-profiler>=0.2    # for GPU profiling
```

### 1.4 TensorFlow vs PyTorch Decision

| Criterion | TensorFlow | PyTorch |
|-----------|-----------|---------|
| **Cadrage fit** | Excellent (explicit in stack) | Good (no mention) |
| **Ease of use** | Sequential API simplest | More boilerplate |
| **MLflow integration** | `mlflow.tensorflow.log_model()` | `mlflow.pytorch.log_model()` |
| **Production serving** | TF Serving, SavedModel native | ONNX conversion needed |
| **Debugging** | Less transparent | Eager execution easier |
| **Team familiarity** | Unknown (assume MLflow users know TF) | Higher learning curve |
| **Performance** | Similar | Similar |

**Recommendation :** **TensorFlow** (explicit in PDF stack table, MLflow integration mature, no PyTorch in cadrage).

---

## 2. CLUSTERING NON-SUPERVISÉ — Segmentation & Détection de Régimes

### 2.1 Justification Métier

**Insight fondamental :** Les cryptos ne réagissent pas uniformément aux mêmes signaux techniques.

Un RSI à 70 sur BTC (asset stable, cap 1.3T) vs DOGE (asset volatile, cap 10B) nécessite des thresholds différents.

**Use cases :**
1. **Clustering par volatilité :** segmenter 30 cryptos en 3-4 régimes (quiet, normal, volatile) → adapter thresholds RSI per cluster
2. **Détection de regime shift :** quand la dynamique de marché change → retrain models
3. **Portfolio construction :** correlated assets risk warning
4. **Anomaly detection :** crypto with unusual volume/price pattern → "wait for clarity"

### 2.2 Architecture Technique

#### 2.2.1 Clustering par Volatilité (K-Means)

**Objective :** Segmenter les 30 cryptos en K clusters basés sur profils de volatilité/liquidité.

**Features (computed rolling over last 90 days) :**
```
Per symbol:
1. Volatility (annualized std of returns)
2. Log-returns mean (drift direction)
3. Sharpe ratio (risk-adjusted return)
4. Volume ratio (24h volume / market cap)
5. Price autocorrelation lag-1 (mean reversion indicator)
6. Drawdown max (recent peak-to-trough)
7. Correlation with BTC (market systemic risk)
8. Liquidity score (bid-ask spread proxy from order book)

Total: 8 features
```

**Preprocessing :**
```python
# Temporal window: rolling 90-day statistics
# Updated daily

features_df = pd.DataFrame({
    'symbol': [...],
    'volatility': [...],        # annualized
    'drift': [...],             # mean return
    ...
})

# StandardScaler: center + scale each feature
scaler = StandardScaler()
X_scaled = scaler.fit_transform(features_df)

# Optimal K via Elbow method + Silhouette score
# Expected: K=3 or K=4 clusters
```

**K-Means Configuration :**
```python
KMeans(
    n_clusters=3,          # start with 3 regimes: quiet, normal, volatile
    init='k-means++',      # stable initialization
    max_iter=300,
    random_state=42,       # reproducibility
    n_init=10,             # try 10 different centroids
)
```

**Output :**
```python
# Daily job (APScheduler)
clusters_df = pd.DataFrame({
    'symbol': [...],
    'cluster_id': [0, 0, 1, 2, ...],  # quiet, normal, volatile
    'date': [2026-03-14, ...],
})
# Persist to: trading_signal_clusters (new table)
```

**Integration with rule engine :**
```python
# In rule_engine.py
def evaluate(self, symbol: str, indicators: dict, cluster_id: int = None):
    # Load cluster-specific thresholds from YAML
    cluster_cfg = self.config.get(f"cluster_{cluster_id}", {})
    rsi_thresholds = cluster_cfg.get("rsi_thresholds", self.config["rsi"])

    # Apply cluster-adjusted thresholds
    rule_results = evaluate_rsi(symbol, indicators, rsi_thresholds)
    ...
```

#### 2.2.2 Regime Detection (DBSCAN)

**Objective :** Detect anomalous market conditions (e.g., flash crash, halted trading).

**When to use DBSCAN instead of K-Means :**
- Detects outliers (cryptos with abnormal intra-day behavior)
- No need to pre-specify K (advantage for online learning)
- Asymmetric clusters (market regimes are not spherical)

**Features (intra-day, per symbol) :**
```
Computed every 4 hours:
1. 4h candle return (close[t] - close[t-1]) / close[t-1]
2. Intra-hour volatility (max-min price / close)
3. Volume acceleration (vol[t] / vol[t-1])
4. RSI momentum (RSI[t] - RSI[t-1])
5. Order book imbalance (bid volume - ask volume) / total
6. Funding rate (if perpetuals)
7. Price distance from MA200 (% deviation)
8. VIX-like (fear & greed index deviation)

Total: 8 features (real-time)
```

**DBSCAN Configuration :**
```python
DBSCAN(
    eps=0.5,              # neighborhood radius (tuned via silhouette)
    min_samples=2,        # min points in neighborhood
    metric='euclidean',
)
```

**Output :**
- Cluster label -1 = outlier/anomaly → trigger alert: "Unusual market condition"
- Cluster 0, 1, 2, ... = normal regimes

**Live streaming :**
```python
# Every 4h: cluster current OHLCV state
# If label == -1 → log warning, maybe suppress new signals
logger.warning("Regime anomaly detected for %s — suppressing signals", symbol)
```

#### 2.2.3 Correlation-Based Clustering (Hierarchical)

**Objective :** Identify groups of correlated cryptos for portfolio risk warnings.

**When to use :**
- Portfolio dashboard (frontend): show clusters of "correlated assets"
- Risk assessment: if you own BTC + ETH (same cluster), you have concentrated risk

**Method : Agglomerative Clustering**
```python
from sklearn.cluster import AgglomerativeClustering
from scipy.spatial.distance import pdist, squareform

# 90-day rolling correlation matrix (30 x 30)
corr_matrix = ohlcv_df.groupby('symbol')['returns'].corr()

# Distance = 1 - correlation
distance_matrix = 1 - corr_matrix
linkage = 'ward'  # minimize within-cluster variance

clustering = AgglomerativeClustering(
    n_clusters=4,           # 4-5 groups of cryptos
    linkage='ward',
    metric='euclidean',
)

# Returns: (30,) array of cluster labels
portfolio_clusters = clustering.fit_predict(corr_matrix)
```

**Output : Portfolio Correlation Matrix with Dendrogram**
```python
# Visualization (frontend Analytics page)
# Heatmap: 30x30 correlation, with vertical/horizontal dendrograms
# Color-coded by hierarchical cluster
```

### 2.3 File Structure & Dependencies

**New files :**
```
src/ml/clustering/
  ├── __init__.py
  ├── volatility_clusterer.py    (K-Means per symbol)
  ├── regime_detector.py          (DBSCAN real-time)
  └── correlation_analyzer.py     (Hierarchical clustering)

src/ml/
  ├── config/
  │   └── clustering_config.yaml  (NEW — K values, DBSCAN eps)
  └── repositories/
      └── clustering_repository.py (NEW — persist clusters to DB)

tests/unit/
  ├── test_volatility_clusterer.py
  ├── test_regime_detector.py
  └── test_correlation_analyzer.py

tests/integration/
  └── test_clustering_pipeline.py (daily job simulation)
```

**Python dependencies (already in requirements.txt) :**
```
scikit-learn>=1.4,<2.0   # KMeans, DBSCAN, AgglomerativeClustering
scipy>=1.13,<2.0         # linkage, pdist (already imported by sklearn)
```

**Database schema (new table) :**
```sql
CREATE TABLE crypto_clusters (
    id UUID PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    cluster_id INT,                 -- 0, 1, 2 for K-Means
    cluster_type VARCHAR(50),       -- "volatility" | "regime" | "correlation"
    confidence DECIMAL(4, 3),       -- silhouette score
    computed_at TIMESTAMP NOT NULL,
    UNIQUE(symbol, cluster_type, computed_at)
);

CREATE INDEX idx_crypto_clusters_date ON crypto_clusters(computed_at DESC);
```

### 2.4 Integration with Frontend

**New page :** `src/frontend/pages/5_Analytics.py` (enhancement)

```python
# Extend existing Analytics dashboard
st.header("Market Regimes & Clustering")

# 1. Volatility clusters (current day)
clusters_today = api_client.get_clusters(cluster_type="volatility")
# Display: 3 columns, cluster members, avg volatility per cluster

# 2. Correlation heatmap with dendrogram
corr_matrix = api_client.get_correlation_matrix()
# Plotly: heatmap(z=corr_matrix, colorscale='RdBu')

# 3. Regime anomalies (last 7 days)
anomalies = api_client.get_anomalies()
# Display: table with symbol, timestamp, reason
```

**API endpoints (new) :**
```python
# in src/api/routers/clustering.py (NEW)

@router.get("/api/v1/clusters")
async def get_clusters(cluster_type: str = "volatility"):
    """Returns current symbol->cluster mapping."""
    # GET /api/v1/clusters?cluster_type=volatility
    # Response: { "clusters": { "0": ["BTC", "ETH"], "1": [...], ... } }

@router.get("/api/v1/correlation-matrix")
async def get_correlation_matrix():
    """Returns 30x30 correlation matrix (JSON)."""
    # { "symbols": ["BTC", "ETH", ...], "matrix": [[1.0, 0.8, ...], ...] }

@router.get("/api/v1/regime-anomalies")
async def get_regime_anomalies(days: int = 7):
    """Returns recent anomalies from DBSCAN."""
    # { "anomalies": [{"symbol": "XRP", "timestamp": ..., "features": {...}}] }
```

---

## 3. REINFORCEMENT LEARNING — Paper Trading Automation

### 3.1 Justification Métier

**Problème :** Les signaux actuels sont **informatifs** (BUY/SELL/HOLD). Mais un trader a aussi besoin de :
- **Entry sizing** : si confiance est 0.7 vs 0.9, quelle taille position ?
- **Exit timing** : quand clôturer un trade ? À TP, SL, ou avant ?
- **Position management** : traîner un SL ? Prendre partiels ?

Ces décisions nécessitent **apprentissage par essais-erreurs** dans un environnement simulé. Le RL permet au modèle d'apprendre une **policy** (stratégie) plutôt qu'une simple direction.

**Cadrage :** Non explicite dans RF-ML, mais exigé par "Caractéristiques & Fonctionnalités" (p.2 du cadrage) : "Apprentissage par renforcement pour automatisation du trading (buy, sell, hold)".

### 3.2 Architecture Technique

#### 3.2.1 Environment Design (OpenAI Gym Compatible)

**State space :**
```python
class TradingEnv(gym.Env):
    """
    Simulated trading environment for RL agent.
    Reward signal: P&L (profit & loss) adjusted by risk metrics.
    """

    observation_space = Box(
        low=-np.inf,
        high=np.inf,
        shape=(state_dim,),  # see below
        dtype=np.float32,
    )
    # state_dim = 30 features (indicators) + 5 portfolio state

    action_space = Discrete(n_actions)
    # n_actions = 6 for discrete (or 2 for Box if continuous)
    # see 3.2.2 below
```

**State vector (per timestep) :**
```
1. Indicator features (30):
   - RSI[1h, 2h, 4h, 1D]           (4)
   - Bollinger pos[1h, 4h, 1D]     (3)
   - Trend slope[1h, 4h, 1D]       (3)
   - Volume ratio[1h, 4h]          (2)
   - Harmonic flags[1h, 4h]        (2)
   - Sentiment score               (1)
   - Fear & Greed                  (1)
   - Price momentum (4h return)    (1)
   - Price distance to MA200       (1)
   - Correlation with BTC          (1)
   - Plus: 10 derived features (RSI gaps, volatility, etc.)

2. Portfolio state (5):
   - Position size (0.0-1.0)       (1) — fraction of portfolio
   - Entry price (normalized)      (1)
   - Current price (normalized)    (1)
   - Unrealized P&L (%)            (1)
   - Days in position              (1)

Total: 30 + 5 = 35-dim state
```

**Observation normalization :**
```python
# All features normalized to [-1, 1] via MinMaxScaler
# Fitted on historical data (2 years) separately for each symbol
# Applied identically during training and inference
```

#### 3.2.2 Action Space

**Option A: Discrete (simpler, recommended for Phase 1)**
```python
action_space = Discrete(6)
# 0: HOLD (do nothing)
# 1: BUY with size 0.25  → position += 0.25 of portfolio
# 2: BUY with size 0.50
# 3: BUY with size 1.00  (full size)
# 4: SELL (close 50% of position)
# 5: SELL (close 100%, exit)
```

**Option B: Continuous (advanced, Phase 2+)**
```python
action_space = Box(
    low=np.array([-1.0, 0.0]),     # [action, size]
    high=np.array([1.0, 1.0]),
    dtype=np.float32,
)
# action ∈ [-1, 1]: -1=SELL, 0=HOLD, 1=BUY
# size ∈ [0, 1]: position sizing
```

**Recommendation :** **Discrete (6 actions)** for initial implementation. Cleaner, easier to debug, works well with DQN.

#### 3.2.3 Reward Function

**Goal :** Agent learns to maximize risk-adjusted returns, not raw P&L.

```python
def compute_reward(
    prev_portfolio_value: float,
    current_portfolio_value: float,
    trades_this_episode: int,
    max_drawdown_this_episode: float,
    sharpe_ratio_rolling: float,
) -> float:
    """
    Composite reward signal.

    Components:
    1. P&L reward: change in portfolio value
    2. Risk penalty: max drawdown
    3. Efficiency penalty: number of trades (transaction costs)
    4. Consistency bonus: Sharpe ratio
    """

    # 1. P&L (main signal)
    pnl = (current_portfolio_value - prev_portfolio_value) / prev_portfolio_value
    pnl_reward = pnl * 100  # scale to [-100, 100]

    # 2. Risk penalty (discourage large drawdowns)
    risk_penalty = -max_drawdown_this_episode * 50

    # 3. Efficiency penalty (transaction costs ~0.17% per trade)
    trade_cost = -trades_this_episode * 0.0017

    # 4. Sharpe bonus (reward consistency)
    sharpe_bonus = sharpe_ratio_rolling * 5 if sharpe_ratio_rolling > 0 else 0

    # Composite
    reward = pnl_reward + risk_penalty + trade_cost + sharpe_bonus

    # Clip to [-10, 10] for training stability
    return np.clip(reward, -10.0, 10.0)
```

**Reward clipping rationale :**
- Prevents agent from overfitting to extreme P&L swings
- Encourages steady, moderate profits over binary win/loss
- Compatible with DQN (Q-values bounded)

#### 3.2.4 Environment Lifecycle

```python
class TradingEnv(gym.Env):

    def reset(self) -> tuple[np.ndarray, dict]:
        """Reset to start of episode (daily trading session)."""
        self.position_size = 0.0
        self.entry_price = None
        self.portfolio_value = 10000.0  # $10k starting capital
        self.trades = 0
        self.drawdown_max = 0.0
        self.episode_rewards = []

        # Current timestep in episode (4h candles, typically 6 per day)
        self.t = 0
        self.episode_length = 6  # one trading day

        obs = self._get_observation()
        return obs, {}

    def step(self, action: int) -> tuple[np.ndarray, float, bool, bool, dict]:
        """
        Execute one timestep.

        action: 0-5 (see 3.2.2)
        returns: (obs, reward, terminated, truncated, info)
        """
        obs_prev = self._get_observation()
        price_prev = self.price_current

        # Execute action (change position)
        self._execute_action(action)
        self.trades += 1 if action != 0 else 0

        # Advance time (fetch next OHLCV bar)
        self.t += 1
        self.price_current = self._fetch_next_candle_close()

        # Update portfolio
        unrealized_pnl = (self.price_current - self.entry_price) / self.entry_price if self.position_size > 0 else 0
        portfolio_value_new = 10000 * (1 + unrealized_pnl * self.position_size)
        self.drawdown_max = max(self.drawdown_max, (self.portfolio_value - portfolio_value_new) / self.portfolio_value)

        # Compute reward
        reward = self.compute_reward(...)
        self.episode_rewards.append(reward)

        # Terminal condition: end of trading day
        terminated = (self.t >= self.episode_length)

        obs = self._get_observation()
        info = {"trades": self.trades, "portfolio_value": portfolio_value_new}

        return obs, reward, terminated, False, info

    def _execute_action(self, action: int) -> None:
        """Translate action ID to position change."""
        if action == 0:        # HOLD
            pass
        elif action == 1:      # BUY 0.25
            self.position_size = min(1.0, self.position_size + 0.25)
            self.entry_price = self.price_current
        elif action == 2:      # BUY 0.50
            self.position_size = min(1.0, self.position_size + 0.50)
            self.entry_price = self.price_current
        elif action == 3:      # BUY 1.00
            self.position_size = 1.0
            self.entry_price = self.price_current
        elif action == 4:      # SELL 0.50
            self.position_size = max(0.0, self.position_size - 0.50)
        elif action == 5:      # SELL 1.00 (exit)
            self.position_size = 0.0
```

#### 3.2.5 Algorithm: Deep Q-Network (DQN)

**Why DQN (not tabular Q-learning, not Monte Carlo):**
- Continuous state space (35 dims) → table-based methods won't work
- DQN scales to modern environments
- Still simple enough for educational project
- Pytorch / TensorFlow support mature

**Architecture :**
```python
class DQNAgent:
    def __init__(self, state_dim: int, n_actions: int):
        self.Q_network = DQN(
            input_dim=state_dim,
            hidden_units=[256, 256],
            output_dim=n_actions,
        )
        self.target_network = copy.deepcopy(self.Q_network)
        self.optimizer = Adam(lr=1e-4)
        self.memory = ReplayBuffer(capacity=100000)
        self.epsilon = 1.0  # exploration rate
        self.gamma = 0.99   # discount factor

    def choose_action(self, obs: np.ndarray, training: bool = True) -> int:
        """Epsilon-greedy action selection."""
        if training and np.random.rand() < self.epsilon:
            return np.random.randint(0, 6)  # explore
        else:
            q_values = self.Q_network(torch.FloatTensor(obs))
            return torch.argmax(q_values).item()  # exploit

    def update(self, batch_size: int = 32) -> float:
        """Experience replay + DQN loss."""
        states, actions, rewards, next_states, dones = self.memory.sample(batch_size)

        # Current Q-values
        q_vals = self.Q_network(states)[range(batch_size), actions]

        # Target Q-values (frozen target network)
        with torch.no_grad():
            q_next = self.target_network(next_states).max(dim=1).values
            q_target = rewards + (1 - dones) * self.gamma * q_next

        # MSE loss
        loss = ((q_vals - q_target) ** 2).mean()

        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.Q_network.parameters(), 1.0)
        self.optimizer.step()

        # Decay epsilon
        self.epsilon = max(0.01, self.epsilon * 0.995)

        # Update target network every N steps
        if self.step % 1000 == 0:
            self.target_network.load_state_dict(self.Q_network.state_dict())

        return float(loss.item())
```

**Training loop :**
```python
def train_dqn(
    env: TradingEnv,
    agent: DQNAgent,
    n_episodes: int = 500,
):
    """Train agent for n_episodes (each = one trading day)."""

    for episode in range(n_episodes):
        obs, _ = env.reset()
        episode_reward = 0.0

        while True:
            action = agent.choose_action(obs, training=True)
            obs_next, reward, terminated, _, info = env.step(action)

            agent.memory.push((obs, action, reward, obs_next, terminated))

            # Update Q-network every 4 steps
            if len(agent.memory) > 32 and agent.step % 4 == 0:
                agent.update(batch_size=32)

            episode_reward += reward
            obs = obs_next

            if terminated:
                break

        # Log episode
        logger.info(
            "Episode %d: return=%.2f trades=%d sharpe=%.2f",
            episode,
            episode_reward,
            info["trades"],
            compute_sharpe([...]),
        )

        # MLflow logging
        mlflow.log_metric("episode_return", episode_reward, step=episode)
        mlflow.log_metric("epsilon", agent.epsilon, step=episode)
```

#### 3.2.6 Walk-Forward Backtesting with RL

**Problem :** RL agents overfit to training data. Must validate on hold-out test period.

**Solution : Walk-forward with RL**
```python
def walk_forward_rl(
    ohlcv_data: pd.DataFrame,  # 2 years historical
    n_folds: int = 5,
):
    """Walk-forward RL training."""

    fold_results = []

    for fold_id in range(n_folds):
        # Split: 6 months train, 1 month test, purge/embargo as per RF-ML-013
        train_end_idx = int((fold_id + 1) * len(ohlcv_data) / n_folds * 0.8)
        test_start_idx = int((fold_id + 1) * len(ohlcv_data) / n_folds)
        test_end_idx = int((fold_id + 2) * len(ohlcv_data) / n_folds * 0.8)

        train_data = ohlcv_data.iloc[:train_end_idx]
        test_data = ohlcv_data.iloc[test_start_idx:test_end_idx]

        # Train agent on this fold's training data
        env = TradingEnv(data=train_data)
        agent = DQNAgent(state_dim=35, n_actions=6)
        train_dqn(env, agent, n_episodes=100)

        # Evaluate on test data (no exploration)
        env_test = TradingEnv(data=test_data)
        obs, _ = env_test.reset()
        test_reward = 0.0

        while True:
            action = agent.choose_action(obs, training=False)  # greedy
            obs, reward, terminated, _, _ = env_test.step(action)
            test_reward += reward
            if terminated:
                break

        fold_results.append({
            "fold_id": fold_id,
            "train_return": ...,
            "test_return": test_reward,
            "model_path": save_agent_checkpoint(agent, fold_id),
        })

    return fold_results
```

### 3.3 File Structure & Dependencies

**New files :**
```
src/ml/rl/
  ├── __init__.py
  ├── environment.py               (OpenAI Gym environment)
  ├── agent_dqn.py                 (DQN implementation)
  ├── replay_buffer.py             (experience replay)
  ├── rl_trainer.py                (training loop orchestration)
  └── policy_wrapper.py            (inference wrapper)

src/ml/
  ├── config/
  │   └── rl_config.yaml           (NEW — hyperparams, reward weights)
  └── backtesting/
      └── rl_backtest_engine.py    (NEW — walk-forward for RL)

tests/unit/
  ├── test_environment.py
  ├── test_agent_dqn.py
  └── test_replay_buffer.py

tests/integration/
  └── test_rl_training.py          (e2e train + backtest)
```

**Python dependencies (add to `src/ml/requirements.txt`) :**
```
torch>=2.0,<3.0           # DQN implementation
gym>=0.26.0,<1.0          # OpenAI Gym environment
```

Alternatively, if TensorFlow chosen for LSTM:
```
tensorflow>=2.13,<3.0     # both LSTM + RL via tf.keras + tf-agents
tf-agents>=0.17.0         # DQN, policies, etc.
```

**Decision :** **Recommend PyTorch** for RL (clearer, more popular for RL than TensorFlow). **TensorFlow for LSTM**. (Or unified in PyTorch if preferred.)

### 3.4 Integration with Signal Generator & Paper Trading

**Paper Trading Flow :**
```
1. Rule engine generates signal (BUY, confidence 0.72)

2. RL agent consulted for:
   - Position sizing (use DQN Q-values to infer risk appetite)
   - Entry price acceptance (Q-values > threshold → accept)
   - SL/TP placement (agent trained on portfolio-optimal SL/TP)

3. Decision combined:
   - Rule: "Strong BUY signal"
   - RL: "Market conditions favorable, size 0.75 of max"
   - Output: "Execute 0.75 size at market, SL at -2%, TP at +5%"

4. Simulated execution (paper trading)
   - Log trade (symbol, side, size, entry, SL, TP)
   - Monitor until close
   - Record outcome (win/loss)

5. Backfeed to RL (next training):
   - Outcome becomes reward signal
   - Agent learns from live trading experience
```

**Code integration :**
```python
# In signal_generator.py (enhancement)

class SignalGenerator:
    def __init__(
        self,
        rule_engine: RuleEngine,
        predictor: Predictor | None = None,
        rl_agent: RLAgent | None = None,  # NEW
    ):
        self._rules = rule_engine
        self._predictor = predictor
        self._rl_agent = rl_agent

    def generate(
        self,
        symbol: str,
        indicators: dict[str, Any],
        news_sentiment: float | None = None,
        current_position: float = 0.0,  # portfolio fraction
    ) -> TradingSignal | None:
        # ... existing rule evaluation ...

        # NEW: RL-enhanced sizing
        if self._rl_agent is not None and direction in ["BUY", "SELL"]:
            obs = self._build_observation(symbol, indicators, current_position)
            rl_q_values = self._rl_agent.get_q_values(obs)

            # Use Q-values to adjust sizing
            sizing = self._rl_suggest_size(rl_q_values, direction)

            signal.leverage_suggested *= sizing  # adjust leverage by RL sizing
```

### 3.5 Constraint Resolution: Deprecated RL vs. Cadrage

**Conflict :**
- `.claude/rules/ml.md` says: "DO NOT use deprecated RL algorithms (Monte Carlo, tabular Q-learning)"
- Cadrage PDF p.2 says: "Apprentissage par renforcement" (RL required)

**Resolution :**
- **DQN is NOT deprecated.** It's modern, widely used (AlphaGo, trading systems, robotics).
- **Monte Carlo + tabular Q-learning ARE deprecated** (tabular methods fail on continuous spaces).
- DQN + policy gradient (A3C, PPO) are the industry standard for RL.

**Action :** Update `.claude/rules/ml.md` to clarify:
```diff
- "Use deprecated RL algorithms (Monte Carlo, tabular Q-learning)"
+ "Use deprecated RL algorithms (tabular Q-learning, SARSA, Monte Carlo on discrete state spaces).
+  Prefer DQN, PPO, or A3C for continuous/high-dimensional environments."
```

---

## 4. Implementation Roadmap & Dependencies

### 4.1 Phase Dependencies

```
Phase 1 (Current):
├── Rule Engine (✓ done)
└── XGBoost + LightGBM (✓ done)

Phase 2 (MUST implement for 100% compliance):
├── LSTM (RF-ML-012, COULD priority)
├── Clustering (IMPLICIT from cadrage, NEW)
└── RL/DQN (IMPLICIT from cadrage, NEW)
```

### 4.2 Suggested Implementation Order

**Why this order:**

1. **LSTM first (1-2 weeks):**
   - Self-contained (no external dependencies on other new modules)
   - Integrates directly into signal_generator via Predictor protocol
   - Testing straightforward (sequence generation, model inference)
   - Can run in parallel with ongoing rule engine work

2. **Clustering second (1 week):**
   - Depends only on existing OHLCV data
   - No impact on signal generation (purely advisory)
   - Can be added to Analytics frontend independently
   - Lower risk (read-only data flow)

3. **RL third (2-3 weeks):**
   - Most complex (environment design, agent training, RL-specific testing)
   - Depends on signal_generator being mature
   - Requires careful integration (cannot destabilize existing signals)
   - Longest iteration time (training takes hours)

### 4.3 Effort Estimation

| Component | Effort | Duration | Dependencies |
|-----------|--------|----------|--------------|
| **LSTM** | 150-200 LOC | 1-2 weeks | TensorFlow, feature_engineering |
| **Clustering** | 200-250 LOC | 1 week | scikit-learn (existing) |
| **RL/DQN** | 400-500 LOC | 2-3 weeks | PyTorch, gym, signal_generator |
| **Tests** | 600-800 LOC | 1 week | pytest, fixtures |
| **Documentation** | 2000-3000 words | 3-5 days | — |
| **Total** | ~1500-1800 LOC | **5-6 weeks** | — |

### 4.4 Python Dependency Summary

**Add to `src/ml/requirements.txt` :**
```
# Deep Learning (LSTM)
tensorflow>=2.13,<3.0
keras-core>=0.3.0

# Reinforcement Learning (DQN)
torch>=2.0,<3.0
gym>=0.26.0,<1.0

# Clustering (already present)
# scikit-learn>=1.4,<2.0
# scipy>=1.13,<2.0

# MLflow integration (already present)
# mlflow>=2.10,<3.0
```

**Total new dependencies :** 4 major packages (tensorflow, keras, torch, gym)

### 4.5 Testing Strategy

**Per component :**

| Component | Unit Tests | Integration Tests |
|-----------|------------|-------------------|
| **LSTM** | sequence_builder, trainer, inference | e2e with signal_generator |
| **Clustering** | algorithm correctness, scaler fit/transform | daily job, API endpoints |
| **RL/DQN** | environment step(), agent.update(), replay buffer | full training loop, backtest |

**Minimum coverage :** 80% (existing project standard)

---

## 5. Risks & Mitigation

### 5.1 LSTM Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **Overfitting on limited data** | Model memorizes noise | Dropout 0.3, early stopping, temporal validation |
| **Data leakage (future look)** | Inflated backtest metrics | Scaler fit only on train, no future data in features |
| **Sequence alignment** | Wrong labels for sequences | Build sequences from rolling window, align with rule output |
| **GPU memory** | Training fails on CPU-only systems | Batch size 32, gradient checkpointing, CPU fallback to NumPy inference |

### 5.2 Clustering Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **K-Means instability (K=3 vs 4)** | Cluster assignments shift | Elbow method + Silhouette score, log to MLflow, document K choice |
| **Outdated clusters (stale data)** | Thresholds don't match reality | Daily recompute, alert if Silhouette < 0.4 |
| **Causation confusion** | Frontend shows correlation, not causation | Clear UI labels: "Cluster based on volatility, not performance" |

### 5.3 RL Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **Catastrophic forgetting** | Agent reverses earlier learning | Experience replay, target network freeze, separate models per symbol |
| **Non-convergence** | Agent never learns stable policy | Reward clipping, learning rate schedule, tensorboard monitoring |
| **Overfitting to training period** | Performs well in backtest, fails live | Walk-forward validation mandatory, hold-out test period, Sharpe ratio cross-validation |
| **Simulation-to-reality gap** | Environment too simplified | Commission/slippage modeled, limit order simulation, liquidity constraints |
| **Computational cost** | Training takes days | Use smaller networks (2 hidden layers), shorter training, GPU required |

---

## 6. Success Criteria & Acceptance

### 6.1 LSTM

- [ ] Model trains without errors on 6+ months of data
- [ ] Validation loss < training loss (no overfitting)
- [ ] Inference time < 50 ms per symbol
- [ ] MLflow logs model + scaler + config
- [ ] Integration test: signal_generator accepts LSTM predictor
- [ ] 80%+ code coverage (tests)

### 6.2 Clustering

- [ ] K-Means clusters 30 symbols in 3 groups with Silhouette > 0.4
- [ ] DBSCAN detects at least 1 anomaly in backtest period
- [ ] Hierarchical clustering generates valid dendrogram
- [ ] Clusters persist to database daily
- [ ] API endpoints return valid JSON
- [ ] Frontend displays heatmap + cluster labels
- [ ] 80%+ code coverage

### 6.3 RL/DQN

- [ ] DQN agent trains for 500 episodes without divergence
- [ ] Episode returns > -10 (reward clipping working)
- [ ] Epsilon decay from 1.0 to 0.01 as expected
- [ ] Walk-forward test shows positive Sharpe on test periods
- [ ] Agent can be saved/loaded from checkpoint
- [ ] Backtest integration: trades logged, P&L computed
- [ ] 80%+ code coverage

### 6.4 Cross-Component

- [ ] All quality gates pass:
  - `ruff check src/ml/`
  - `mypy src/ml/ --strict`
  - `pytest tests/ --cov=src/ml --cov-fail-under=80`
- [ ] No print() statements (logging only)
- [ ] All type hints present
- [ ] Documentation complete (docstrings + this analysis)
- [ ] Code review approved

---

## 7. Conclusion

The three ML gaps (LSTM, Clustering, RL) are **essential for full cadrage compliance**. Each addresses distinct requirements:

1. **LSTM :** Temporal dependencies in technical indicators (RF-ML-012)
2. **Clustering :** Regime detection + portfolio risk (implicit in cadrage "analytics")
3. **RL :** Automated strategy learning + paper trading (explicit in cadrage "renforcement learning")

**Effort:** ~5-6 weeks for a single ML engineer, or 2-3 weeks for a team of 2-3.

**Timeline:** Can be executed in parallel with ongoing API/frontend work, provided team boundaries are respected (`src/ml/` only).

**Risk:** Low, given modular design and existing ML infrastructure (MLflow, backtesting, signal pipeline).

---

## Appendix: Code Snippet Examples

### A.1 LSTM Trainer (sketch)

```python
# src/ml/models/lstm_trainer.py (NEW)

from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dropout, Dense, BatchNormalization

def build_lstm_model(lookback: int, n_features: int) -> Sequential:
    model = Sequential([
        LSTM(64, return_sequences=True, input_shape=(lookback, n_features)),
        Dropout(0.3),
        LSTM(64, return_sequences=False),
        Dropout(0.3),
        Dense(128, activation='relu'),
        BatchNormalization(),
        Dropout(0.2),
        Dense(3, activation='softmax'),  # BUY, SELL, HOLD
    ])
    model.compile(loss='categorical_crossentropy', optimizer='adam')
    return model
```

### A.2 K-Means Clustering (sketch)

```python
# src/ml/clustering/volatility_clusterer.py (NEW)

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

def cluster_symbols_by_volatility(
    features_df: pd.DataFrame,
    n_clusters: int = 3,
) -> np.ndarray:
    """Returns cluster labels for each symbol."""
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(features_df[FEATURE_COLS])

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)

    return labels
```

### A.3 DQN Agent (sketch)

```python
# src/ml/rl/agent_dqn.py (NEW)

class DQNAgent:
    def __init__(self, state_dim: int, n_actions: int):
        self.q_network = DQNNetwork(state_dim, n_actions).to('cuda')
        self.target_network = DQNNetwork(state_dim, n_actions).to('cuda')
        self.optimizer = torch.optim.Adam(self.q_network.parameters(), lr=1e-4)
        self.memory = ReplayBuffer(100000)

    def update(self, batch_size: int = 32) -> float:
        states, actions, rewards, next_states, dones = self.memory.sample(batch_size)

        q_vals = self.q_network(states)[range(batch_size), actions]
        with torch.no_grad():
            q_next = self.target_network(next_states).max(dim=1).values
            q_target = rewards + (1 - dones) * 0.99 * q_next

        loss = ((q_vals - q_target) ** 2).mean()
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        return float(loss.item())
```

---

**Document Version :** 1.0
**Last Updated :** 2026-03-14
**Status :** Ready for Technical Review

