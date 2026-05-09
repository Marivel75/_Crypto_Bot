# Paper Trading — Cahier des charges spécifique

**Projet** : Crypto Bot  
**Auteurs** : Jules Willard — Mikaël Jayet
**Date** : Mai 2026  

---

## 1. Contexte et objectif

Le cadrage initial du projet (octobre 2025) identifie le paper trading comme une fonctionnalité clé :

> *"Trading : Passage d'ordre en paper trading pour simuler le trading"*

Ce document précise le périmètre, le fonctionnement et les spécifications techniques de cette fonctionnalité, absente du cadrage V2.

Le **paper trading** (trading sur papier) permet à un utilisateur de simuler des décisions d'investissement sur les marchés crypto avec un capital fictif, sans risque financier réel. L'objectif est double :

- **Pédagogique** : comprendre les mécanismes du trading sans perdre d'argent
- **Évaluation des stratégies** : valider en conditions réelles les signaux générés par les modèles ML du projet

---

## 2. Personas ciblés

| Persona | Usage paper trading |
|---------|---------------------|
| **Noah** (trader indépendant) | Valider un setup signal avant de l'exécuter en réel sur un DEX |
| **Aleksandar** (investisseur débutant) | Apprendre à investir en crypto sans risque, suivre son "portefeuille fictif" |
| **Sarah** (journaliste) | Illustrer des analyses avec des simulations chiffrées |

---

## 3. Fonctionnement général

### 3.1 Initialisation du portefeuille

L'utilisateur crée un portefeuille fictif en définissant :
- Un **nom** (ex : "Stratégie BTC Q2 2026")
- Un **capital de départ** en USDT (ex : 10 000 USDT)

Le système crée un portefeuille avec 100 % du capital en cash (USDT) et aucune position ouverte.

### 3.2 Passer un ordre BUY

1. L'utilisateur sélectionne un actif (ex : BTC/USDT)
2. Choisit une quantité (ex : 0.1 BTC) **ou** un montant en USDT (ex : 1 000 USDT)
3. Le système enregistre le trade au **prix de clôture de la dernière bougie connue** en base
4. Le cash disponible est débité du montant de l'ordre
5. La position apparaît dans le tableau "Positions ouvertes"

> **Contrainte** : le système vérifie que le cash disponible est suffisant avant d'ouvrir la position.

### 3.3 Suivi de la position ouverte

Tant que la position est OPEN :
- Le **P&L latent** est affiché en temps réel : `(prix_actuel − prix_entrée) × quantité`
- Le **P&L en %** : `((prix_actuel − prix_entrée) / prix_entrée) × 100`
- Le prix actuel est celui de la dernière bougie disponible en base

### 3.4 Fermer une position (SELL)

1. L'utilisateur clique "Fermer" sur une position ouverte  
   **ou** un signal ML/technique déclenche la fermeture (mode semi-auto)
2. Le système enregistre le prix de sortie = dernière bougie connue
3. Calcul du P&L réalisé : `(prix_sortie − prix_entrée) × quantité`
4. Le cash est crédité : `cash += quantité × prix_sortie`
5. La position passe en statut CLOSED dans l'historique

### 3.5 Vue portefeuille

| Indicateur | Calcul |
|------------|--------|
| Capital total | `cash_disponible + Σ(quantité × prix_actuel)` pour positions ouvertes |
| P&L total réalisé | `Σ pnl` sur trades CLOSED |
| P&L latent | `Σ (prix_actuel − prix_entrée) × quantité` sur trades OPEN |
| Win rate | `trades_positifs / total_trades_fermés × 100` |
| Meilleur trade | Trade CLOSED avec P&L le plus élevé |
| Pire trade | Trade CLOSED avec P&L le plus bas |

---

## 4. Modes de déclenchement

### Mode Manuel
L'utilisateur place et ferme chaque ordre depuis l'interface Streamlit.

### Mode Semi-automatique
Les signaux techniques (`/signals`) ou ML (`/ml/backtest`) génèrent une **suggestion** d'ordre. L'utilisateur valide ou rejette avant exécution.  
Source du signal tracée dans `signal_source` du trade.

### Mode Automatique *(bonus — si temps disponible)*
Le modèle XGBoost place automatiquement les ordres BUY/SELL sur la base des prédictions, sans validation manuelle. Repose sur le backtester walk-forward existant adapté en mode "live".

---

## 5. Modèle de données

### Table `paper_portfolios`

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | String(36) | UUID |
| `name` | String(100) | Nom du portefeuille |
| `initial_capital` | Float | Capital de départ en USDT |
| `cash` | Float | Cash disponible actuel |
| `created_at` | DateTime | Date de création |

### Table `paper_trades`

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | String(36) | UUID |
| `portfolio_id` | String(36) | FK → paper_portfolios |
| `symbol` | String(20) | Ex : BTC/USDT |
| `side` | String(4) | BUY ou SELL |
| `quantity` | Float | Quantité d'actif |
| `entry_price` | Float | Prix d'entrée (dernière bougie) |
| `entry_time` | DateTime | Timestamp d'entrée |
| `exit_price` | Float (nullable) | Prix de sortie |
| `exit_time` | DateTime (nullable) | Timestamp de sortie |
| `status` | String(6) | OPEN ou CLOSED |
| `pnl` | Float (nullable) | P&L réalisé en USDT |
| `pnl_pct` | Float (nullable) | P&L en % |
| `signal_source` | String(50) | "manual", "technical", "xgboost", etc. |
| `signal_score` | Float (nullable) | Score du signal déclencheur |
| `created_at` | DateTime | Date de création |

---

## 6. API

### Endpoints

| Méthode | Route | Description |
|---------|-------|-------------|
| `POST` | `/paper-trading/portfolios` | Créer un portefeuille |
| `GET` | `/paper-trading/portfolios` | Lister les portefeuilles |
| `GET` | `/paper-trading/portfolios/{id}` | Détail + résumé P&L |
| `POST` | `/paper-trading/orders` | Ouvrir une position |
| `POST` | `/paper-trading/orders/{id}/close` | Fermer une position |
| `GET` | `/paper-trading/orders` | Historique des trades |

---

## 7. Interface utilisateur (Streamlit)

**Page 6 — Paper Trading** (`frontend/pages/6_paper_trading.py`)

### Sections

1. **Sélecteur de portefeuille** — choisir ou créer un portefeuille fictif
2. **Résumé du portefeuille** — capital total, P&L total, win rate (métriques en haut de page)
3. **Positions ouvertes** — tableau avec P&L latent en temps réel, bouton "Fermer"
4. **Passer un ordre** — formulaire : symbol / side / quantité → bouton "Placer l'ordre"
5. **Historique des trades** — tableau filtrable par symbol, statut, période
6. **Courbe de performance** — évolution du capital dans le temps (Plotly)

---

## 8. Règles métier

- **Prix d'exécution** : toujours le `close` de la dernière bougie disponible en base pour le symbol/timeframe 1d
- **Pas de short** (vente à découvert) dans la V1 — uniquement BUY puis SELL de la position
- **Un seul portefeuille actif** par session utilisateur en V1
- **Pas de frais de transaction** simulés en V1 (simplification pédagogique)
- **Quantité minimale** : 0.0001 unité d'actif
- **Cash insuffisant** : l'ordre est rejeté avec un message explicite

---

## 9. Contraintes techniques

- Prix récupéré depuis la table `ohlcv` locale (pas d'appel API externe au moment de l'ordre)
- P&L latent recalculé à chaque rechargement de la page Streamlit
- Compatible SQLite (dev) et PostgreSQL (prod)
- Aucun vrai ordre ne doit être passé sur un exchange réel

---

