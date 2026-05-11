---
type: rncp
bloc: 4
competence: C4.2.2
title: FAQ utilisateurs finaux CryptoBot
project: cryptobot
tags: [cryptobot, rncp38919, bloc4, pilotage, faq, support]
created: 2026-04-14
source_of_truth: rncp/bloc4-pilotage/user-onboarding.md
related: [[rncp/bloc4-pilotage/user-onboarding]], [[rncp/bloc4-pilotage/veille-reglementaire]], [[planning/roadmap]]
---

# FAQ utilisateurs — CryptoBot

FAQ publique publiee sur `/faq`, ton accessible, 20 questions organisees par theme. Elle complete le runbook d'onboarding [[rncp/bloc4-pilotage/user-onboarding]].

## 1. General

**Q1. Qu'est-ce que CryptoBot ?**
CryptoBot est une plateforme **informationnelle** de surveillance et d'analyse crypto. Elle collecte les prix OHLCV (Binance, CoinGecko, CCXT), calcule des indicateurs techniques (RSI, Bollinger, patterns harmoniques, trend lines), emet des signaux BUY/SELL/HOLD avec un score de confiance, et agrege les news RSS avec analyse de sentiment.

**Q2. Le bot trade-t-il a ma place ?**
**Non.** CryptoBot ne passe strictement aucun ordre sur aucune plateforme. Il ne dispose pas de cles API trading, ne detient pas de fonds, et n'a aucune integration broker. Toute decision d'executer un trade vous incombe, sur votre compte personnel.

**Q3. Est-ce que je risque de perdre de l'argent en utilisant CryptoBot ?**
Non de facon directe : la plateforme est en lecture seule. Les signaux sont informationnels. Si vous choisissez de repliquer manuellement un signal sur votre broker, vous assumez pleinement le risque du trade (volatilite, liquidite, levier).

## 2. Compte

**Q4. Comment je m'inscris ?**
Via `/register` : email + mot de passe (8 caracteres minimum avec 1 majuscule, 1 chiffre, 1 special). Choisissez votre persona (trader / journalist / investor) pour pre-configurer seuil et dashboard.

**Q5. J'ai oublie mon mot de passe.**
Cliquez "mot de passe oublie" sur la page login. Un email avec un lien de reset valide 30 min vous est envoye.

**Q6. Comment supprimer mon compte ?**
Page `/settings` > "supprimer mon compte". La suppression est **immediate et irreversible** : votre compte, watchlist, portfolio et signaux personnalises sont effaces (cascade RGPD, voir [[rncp/bloc3-deploiement/rgpd-compliance]]). Un export ZIP de vos donnees vous est propose avant confirmation.

## 3. Signaux

**Q7. Que signifie confidence 0.6 ?**
C'est un score 0-1 representant l'alignement des regles techniques (RSI multi-TF, Bollinger, harmoniques, trend) + pondere sentiment news. Un seuil ≥ 0.6 est requis pour emettre un signal. Noah utilise 0.70, Sarah 0.60, Aleksandar 0.75.

**Q8. Pourquoi je ne recois aucun signal sur XRP ?**
La V1 suit les 13 symboles "priority" (BTC, ETH, USDT, USDC, BNB, XRP, SOL, ADA, AVAX, DOT, DOGE, TRX, ATOM). XRP **est** couvert mais si aucun signal n'apparait c'est qu'aucun setup ne depasse votre seuil sur les 24 dernieres heures. Baissez le seuil (ex. 0.55) pour voir les signaux moins forts (en mode consultatif uniquement).

**Q9. Puis-je filtrer par timeframe ?**
Oui, page `/signals` > filtre "timeframe" : 15 min, 1 h, 2 h, 4 h, 1 j, 1 sem. Vous pouvez combiner plusieurs TF (OR logique).

**Q10. Que faire avec le `leverage_suggested` ?**
C'est un levier **indicatif** calcule par l'engine avec la regle de marge 2× (reserver 2× la marge nominale). Plafonne a 5× en mode debutant, 20× en mode avance. **Ne l'utilisez jamais sans comprendre les consequences d'une liquidation.**

## 4. News et sentiment

**Q11. D'ou viennent les news ?**
Sources RSS : Decrypt, Cointelegraph, PhoenixNews, Alternative.me (Fear & Greed Index). Frequence de collecte : 15 min (news) / 20 min (NLP) / 1 h (fear & greed). Pas de scraping hors RSS officiels.

**Q12. Comment le sentiment modifie un signal ?**
Le score de sentiment des news recentes (< 6 h) sur le symbole ajuste la confidence de ±5 points de pourcentage, cape a 0.95. Exemple : signal BUY confidence 0.72 + sentiment BTC tres positif (+0.8) → confidence ajustee 0.77.

## 5. Portfolio et watchlist

**Q13. Combien de symboles puis-je suivre ?**
Watchlist illimitee parmi les 30 symboles supportes. Portfolio : jusqu'a 50 positions simulees par compte.

**Q14. Puis-je importer mon portefeuille depuis un CSV ?**
Oui, page `/portfolio` > "import CSV". Colonnes attendues : `symbol,quantity,entry_price,entry_date`. Le P&L est recalcule au prix courant a chaque tick ETL.

**Q15. Le P&L affiche est-il reel ?**
Non, c'est un **P&L simule** base sur les prix de marche. Il ne reflete pas un solde broker. Aucun lien avec un compte reel n'existe.

## 6. Performance et backtesting

**Q16. Qu'est-ce que le Sharpe ratio affiche ?**
Mesure standard de rendement ajuste au risque (rendement excedentaire / volatilite). La plateforme le calcule sur l'historique des signaux emis. **Les performances passees ne prejugent pas des performances futures** — disclaimer obligatoire.

**Q17. Le backtest est-il realiste ?**
Il utilise la technique walk-forward avec purging + embargo windows (cf Phase 2 ML). Les fees maker/taker (0.02 % / 0.05 %) et slippage (0.1 %) sont integres dans le calcul. Le kill-switch desactive un signal si les fees cumules ≥ 50 % du gain attendu.

## 7. Securite et donnees

**Q18. Mes donnees sont-elles en securite ?**
- Mots de passe : bcrypt (cost 12).
- JWT : HS256, expiration 24 h.
- Transport : TLS 1.3 obligatoire (certificats Let's Encrypt).
- Hebergement : VPS OVH en France (donnees UE, hors Cloud Act US).
- Pas de revente ni transfert hors UE.

**Q19. Puis-je exporter mes donnees (RGPD) ?**
Oui, `/settings` > "exporter mes donnees" genere un ZIP avec : profil, watchlist, portfolio, signaux consultes, preferences. Conformite article 20 RGPD.

## 8. Facturation

**Q20. C'est gratuit ?**
Oui, projet ecole, hebergement VPS OVH (~15 €/mois a la charge de l'equipe projet). Couts infra detailles dans [[rncp/bloc4-finance/cost-analysis]]. Pas de plan payant prevu sur la V1.

## 9. Support

Pour tout probleme non couvert ici : `support@cryptobot.example`. SLA premiere reponse 48 h ouvrees. Bugs bloquants (P1) : 24 h. Voir plan d'escalation [[rncp/bloc4-pilotage/user-onboarding#handoff-support]].

## 10. Roadmap

Ce qui arrive (extraits [[_other/common/projects/SAP/planning/roadmap]]) :

- **S12-S14** — MFA TOTP, paper trading avance (voir [[CryptoBot/avril/specs/paper-trading-alertes]]).
- **S15-S18** — Phase 2 ML supervised learning (XGBoost, LightGBM, LSTM).
- **S19+** — Alertes email/push configurables, dashboards regimes de marche (K-means), API publique read-only.
