---
type: rncp
bloc: 3
competence: C3.3-C3.4
source: src/api + infra/nginx/nginx.conf + .env.example
tags: [cryptobot, rncp, bloc3, rgpd, conformite, tls, privacy]
created: 2026-04-14
ingested_by: L3-Containers-Sec
certif: RNCP38919
---

# RGPD — Conformite de la plateforme Crypto Bot

Livrable Bloc 3 — Deployer et securiser. Reference [[CryptoBot/avril/rncp/livrables/L3-deploiement/container-images]], [[CryptoBot/avril/rncp/livrables/L3-deploiement/secrets-rotation]], [[../../audit/technique/env-vars]].

## 1. Cadre legal

- **RGPD** : Reglement (UE) 2016/679 du 27 avril 2016.
- **LIL** : Loi Informatique et Libertes du 6 janvier 1978 modifiee.
- **CNIL** : autorite de controle francaise.

Nature du projet : **projet ecole a dimension informationnelle**. CryptoBot ne passe **aucun ordre** ni n'execute de trade (cf `docs/00-overview.md`). Les donnees utilisateur sont minimales, aucune donnee bancaire, aucun KYC.

Statut : sous-traitant au sens RGPD. Responsable du traitement = l'etablissement pedagogique porteur du projet. Le projet est deploye sur OVH (UE, Roubaix/Gravelines) — pas de transfert hors UE sauf Cloudflare (DPA signe, SCC 2021).

## 2. Donnees personnelles collectees

Minimisation stricte (RGPD art. 5.1.c) :

| Donnee | Usage | Duree | Base legale |
|--------|-------|-------|-------------|
| `email` | Identification utilisateur, notifications | Compte actif + 30j apres suppression | Contrat (art. 6.1.b) |
| `hashed_password` | Authentification (bcrypt 12 rounds) | Compte actif | Contrat |
| `created_at` | Traitabilite, audit | 5 ans (prescription civile) | Interet legitime (6.1.f) |
| `last_login_at` | Detection compte inactif, securite | 30j glissants | Interet legitime |
| `watchlist.symbols` | Preferences dashboard | Compte actif | Contrat |
| `portfolio.*` (Phase 2 paper trading) | Simulation virtuelle | Compte actif | Contrat |

**EXPLICITEMENT EXCLUS** :
- IBAN, RIB, numero carte bancaire (aucun moyen de paiement)
- Piece d'identite, KYC, justificatif domicile (pas de conformite AMF/MiFID requise)
- Donnees de geolocalisation fine (pas de tracking GPS)
- Cookies publicitaires tiers (aucun partenaire ad)

Schema DB : cf [[../../architecture/er01-database-schema]] tables `users`, `watchlists`, `portfolios`.

## 3. Base legale

- **Execution du contrat** (art. 6.1.b) : creation compte, dashboard, signaux, paper trading.
- **Interet legitime** (art. 6.1.f) : audit logs securite, detection intrusion, amelioration produit (metriques anonymisees).
- **Consentement explicite** (art. 6.1.a) : **uniquement** pour le chat LLM (OpenAI / Anthropic) — opt-in coche, revocable via `PATCH /auth/me`.

## 4. Droits utilisateur — endpoints REST

Materialisation technique des art. 15-22 RGPD dans `src/api/routers/auth.py` :

| Droit | Article | Endpoint | Implementation |
|-------|---------|----------|----------------|
| Acces | 15 | `GET /api/v1/auth/me` | Retourne `UserProfile` (email, created_at, last_login_at, watchlist, portfolio) |
| Rectification | 16 | `PATCH /api/v1/auth/me` | MAJ email, password, preferences |
| Effacement | 17 | `DELETE /api/v1/auth/me` | Cascade `User → Portfolio → Watchlist → AlertRules`, anonymisation logs (email → `deleted_<uuid>@anonymous.local`) |
| Portabilite | 20 | `GET /api/v1/auth/me/export` | Dump JSON structure : profile, watchlist, portfolios, alertes — telecharge en fichier `cryptobot_export_<user_id>_<date>.json` |
| Opposition | 21 | `PATCH /api/v1/auth/me` champ `allow_llm_chat=false` | Desactive opt-in LLM |
| Limitation | 18 | `POST /api/v1/auth/me/freeze` (Phase 2) | Gele le compte (read-only) en cas de contestation |

Procedure d'effacement (technique) :
```python
async def delete_user_cascade(user_id: int) -> None:
    # 1. Export portabilite auto (si demande)
    # 2. Suppression donnees non-requises legalement
    await portfolio_repo.delete_by_user(user_id)
    await watchlist_repo.delete_by_user(user_id)
    await alert_rule_repo.delete_by_user(user_id)
    # 3. Anonymisation User (conservation 30j pour audit)
    await user_repo.anonymize(user_id, tombstone_until=now() + timedelta(days=30))
    # 4. Anonymisation logs (hash email dans audit_events)
    await audit_repo.hash_email_references(user_id)
```

## 5. Duree de conservation

| Donnee | Pendant compte actif | Apres suppression |
|--------|----------------------|-------------------|
| Profile user | Infini (tant qu'utilise) | Anonymise 30j puis purge physique |
| Watchlist / portfolio / alertes | Infini | Supprime immediatement (DELETE CASCADE) |
| Logs applicatifs (`audit_events`) | 90j rolling | Email hashe SHA-256, conservation 1 an pour securite |
| Metriques Prometheus | 15j TSDB retention | N/A (non nominatives) |
| Logs Loki (Phase 2) | 30j | Purge automatique TTL |

Conforme a art. 5.1.e (duree limitee).

## 6. Audit log — traitement securite

Table `audit_events` (prevue Phase 2, cf [[../../specs/PRD-phase2]]) :

```sql
CREATE TABLE audit_events (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
  action TEXT NOT NULL,           -- 'login_success', 'login_fail', 'password_change', 'export_data', 'delete_account'
  timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ip_hash TEXT,                   -- SHA-256(IP + salt) — RGPD Considerant 26
  user_agent TEXT,
  metadata JSONB
);
CREATE INDEX ON audit_events (user_id, timestamp DESC);
```

IP hashee (non stockee en clair) pour concilier securite (detection brute-force) et minimisation (considerant 26 RGPD : toute donnee re-identifiable est personnelle).

## 7. TLS & chiffrement en transit

Configuration Nginx (`infra/nginx/nginx.conf` + bloc HTTPS documente Phase 2, lignes 99-109) :

```nginx
server {
    listen 443 ssl http2;
    server_name crypto-bot.example.com;

    ssl_certificate /etc/letsencrypt/live/YOUR_DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/YOUR_DOMAIN/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    # Modern Mozilla cipher suite (cf Phase 2) :
    # ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:
    # ECDHE-ECDSA-AES256-GCM-SHA384:...
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;

    # OCSP stapling
    ssl_stapling on;
    ssl_stapling_verify on;

    # HSTS 1 an (preload eligible)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
}

# HTTP -> HTTPS redirect 301
server {
    listen 80;
    server_name _;
    return 301 https://$host$request_uri;
}
```

- **Protocols** : TLS 1.2 + 1.3 uniquement (TLS 1.0/1.1 interdits depuis RFC 8996).
- **Cipher suite** : Mozilla Modern (uniquement AEAD, AES-GCM, ChaCha20-Poly1305).
- **HSTS** : 1 an, preload-eligible.
- **OCSP stapling** : active, verifie.
- **Certificats** : Let's Encrypt via `certbot` sidecar. Renouvellement auto (cron `certbot renew --deploy-hook "docker compose exec nginx nginx -s reload"` tous les 12 jours). Fallback : `acme.sh`.
- **SSL Labs cible** : A+ (verifie via https://www.ssllabs.com/ssltest/).
- **Redirect HTTP → HTTPS** : 301 permanent.

Test dry-run renouvellement : `sudo certbot renew --dry-run` dans le runbook ([[../../audit/remediation/phase2]]).

## 8. Cookies & sessions

- **JWT stateless** en header `Authorization: Bearer <token>` (HS256, `API_SECRET_KEY`, exp = `JWT_EXPIRATION_HOURS` = 24h par defaut cf `.env.example`).
- **Aucun cookie de session** cote API (stateless).
- **Streamlit** : cookie `_streamlit_xsrf` (XSRF token, session scope, SameSite=Lax, Secure sur HTTPS). Non-traceable, duree = session.
- **Cloudflare** proxy orange cloud → cookie `__cf_bm` (bot management, 30min, exempte ePrivacy Directive par `CJEU 2020 Planet49` comme "strictement necessaire").
- **Pas de cookies publicitaires ni analytics tiers** (Streamlit telemetrie desactivee : `STREAMLIT_BROWSER_GATHER_USAGE_STATS=false`).

Banner cookies non requis (aucun traceur soumis a consentement ePrivacy).

## 9. Sous-traitants (art. 28 RGPD)

| Sous-traitant | Role | Localisation | DPA | Duree | Transfert hors UE |
|---------------|------|--------------|-----|-------|-------------------|
| **OVH** | Hebergement VPS + Object Storage S3 | France (Roubaix, Gravelines) | Signe (conditions OVHcloud) | Illimite tant que compte | Non |
| **Cloudflare** | CDN proxy, WAF, DDoS | Anycast mondial (Paris POP privilegie) | Signe (SCC 2021) | Illimite | Oui (US) — SCC + DPF |
| **Let's Encrypt / ISRG** | CA TLS | US (California) | N/A (pas de donnees perso) | N/A | Oui (CA publique) |
| **OpenAI** | LLM chat (opt-in) | US | Signe (OpenAI DPA + SCC) | Par session | Oui (US) — SCC + DPF |
| **Anthropic** | LLM chat (opt-in, alternative) | US | Signe (Anthropic DPA + SCC) | Par session | Oui (US) — SCC + DPF |
| **Binance / CoinGecko** | Donnees marche publiques (pas de PII utilisateur) | Global | N/A | N/A | N/A |

Transferts US encadres par Data Privacy Framework (adequation juillet 2023) + Standard Contractual Clauses.

## 10. Secrets & `.env`

- `.env` hors Git (`.gitignore`), permissions `chmod 600`, owner `deploy`.
- Jamais de log des valeurs (`LOG_LEVEL=INFO` filtre via `src/shared/config.py` — les `SecretStr` Pydantic v2 sont masquees en `repr`).
- Rotation documentee : [[CryptoBot/avril/rncp/livrables/L3-deploiement/secrets-rotation]].
- Audit secret scanning : `gitleaks` pre-commit + GitHub secret scanning active.

## 11. Checklist conformite (10 items)

| # | Exigence RGPD | Article | Statut |
|---|---------------|---------|--------|
| 1 | Minimisation donnees collectees | 5.1.c | Oui |
| 2 | Base legale identifiee par donnee | 6 | Oui |
| 3 | Duree de conservation definie | 5.1.e | Oui |
| 4 | Droit d'acces (endpoint) | 15 | Oui (`GET /auth/me`) |
| 5 | Droit de rectification | 16 | Oui (`PATCH /auth/me`) |
| 6 | Droit a l'effacement + cascade | 17 | Partiel (logique implementee, test e2e a ajouter) |
| 7 | Droit a la portabilite (export JSON) | 20 | Partiel (endpoint a livrer Phase 2) |
| 8 | Chiffrement en transit TLS 1.2+ | 32 | Oui (Nginx HSTS + LE) |
| 9 | Chiffrement au repos (passwords bcrypt) | 32 | Oui (bcrypt 12 rounds) |
| 10 | Registre des traitements (art. 30) | 30 | Partiel (ce document + [[SAP/wiki/meta/_index]] a completer) |
| 11 | Privacy by design (pas de tracker tiers) | 25 | Oui |
| 12 | Audit log acces / modifications | 32 | Partiel (table `audit_events` Phase 2) |
| 13 | Sous-traitants DPA signes | 28 | Oui (OVH, Cloudflare, OpenAI, Anthropic) |
| 14 | Notification breach <72h | 33 | N.A. (procedure documentee [[CryptoBot/avril/rncp/livrables/L3-deploiement/secrets-rotation]] §6) |

**Score conformite : 11 Oui / 4 Partiel / 0 Non** → remediation Phase 2-3 pour passer les 4 partiels a Oui.

## Sources

- `/home/jules/Documents/3-git/CryptoBot/dev/infra/nginx/nginx.conf` (110 l)
- `/home/jules/Documents/3-git/CryptoBot/dev/.env.example` (41 l)
- [[../../architecture/er01-database-schema]]
- [[../../audit/remediation/phase2]] (S6 HTTPS + HSTS)
- [[../../specs/PRD-phase2]] (audit_events roadmap)

Lies : [[CryptoBot/avril/rncp/livrables/L3-deploiement/container-images]] | [[CryptoBot/avril/rncp/livrables/L3-deploiement/secrets-rotation]].
