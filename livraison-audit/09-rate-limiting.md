# Rate Limiting & API Throttling

**Status**: Phase 3 (Medium priority) documentation  
**Date**: 2026-03-12  
**Category**: C5 — DevOps/API documentation

---

## Overview

Rate limiting protects the Crypto Bot API from abuse and ensures fair resource allocation. This document explains the limits, how to handle throttling, and procedures for whitelisting trusted clients.

**Architecture**: Multi-layer enforcement
- **Nginx** (reverse proxy, immediate rejection at edge)
- **FastAPI** (per-endpoint rate limiting via SQLAlchemy)
- **Response headers** (client-side adaptive throttling)

---

## Rate Limits by Endpoint Category

### Public Endpoints (Unauthenticated)

| Category | Limit | Window | Response Code | Notes |
|----------|-------|--------|---|---------|
| General API | 30 requests/sec | Per client IP | 429 | Nginx `api_limit` zone |
| Auth (login, register) | 5 requests/min | Per client IP | 429 | Nginx `auth_limit` zone (stricter) |
| Health check | No limit | — | 200 | Used for monitoring (exempt) |

### Authenticated Endpoints (User)

| Category | Limit | Window | Response Code | Notes |
|----------|-------|--------|---|---------|
| Data queries (OHLCV, signals) | 60 requests/min | Per user | 429 | Tracked via JWT token |
| Watchlist operations | 100 requests/min | Per user | 429 | Add/remove/list |
| Portfolio operations | 100 requests/min | Per user | 429 | Create/update positions |
| Chat/LLM endpoints | 10 requests/min | Per user | 429 | Expensive (high latency) |

### Administrative Endpoints (Authenticated + Admin Role)

| Category | Limit | Window | Response Code | Notes |
|----------|-------|--------|---|---------|
| System admin operations | 1000 requests/min | Per admin user | 429 | Migrations, user management |

---

## Nginx Configuration (Edge Layer)

Defined in `infra/nginx/nginx.conf`:

```nginx
# Rate limiting zones
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=30r/s;
limit_req_zone $binary_remote_addr zone=auth_limit:10m rate=5r/m;

# General API proxy — 30 req/sec with burst of 20
location /api/ {
    limit_req zone=api_limit burst=20 nodelay;
    proxy_pass http://api/;
    ...
}

# Auth endpoints — 5 req/min with burst of 3
location /api/auth/ {
    limit_req zone=auth_limit burst=3 nodelay;
    proxy_pass http://api/auth/;
    ...
}
```

**Key parameters**:
- `zone=api_limit` — 10-minute window, tracks by `$binary_remote_addr` (client IP)
- `rate=30r/s` — 30 requests per second sustained
- `burst=20` — allow 20 additional requests in a burst (absorbed from rate bucket)
- `nodelay` — reject requests immediately when limit exceeded (vs. queue them)

---

## Response Headers (HTTP/1.1 Standard)

All responses include rate limit information in headers:

```http
HTTP/1.1 200 OK
Content-Type: application/json
RateLimit-Limit: 30
RateLimit-Remaining: 27
RateLimit-Reset: 1678886400

{
    "success": true,
    "data": [...]
}
```

| Header | Meaning | Example |
|--------|---------|---------|
| `RateLimit-Limit` | Total requests per window | `30` |
| `RateLimit-Remaining` | Requests left in current window | `27` |
| `RateLimit-Reset` | Unix timestamp when limit resets | `1678886400` |

**Client Implementation** (pseudocode):

```python
import time

def make_request(url):
    response = requests.get(url)
    
    if response.status_code == 429:
        reset_time = int(response.headers.get("RateLimit-Reset", time.time()))
        wait_seconds = reset_time - time.time()
        print(f"Rate limited. Waiting {wait_seconds}s...")
        time.sleep(wait_seconds + 1)
        return make_request(url)  # retry
    
    # Proactive backoff
    remaining = int(response.headers.get("RateLimit-Remaining", 0))
    if remaining < 5:
        print("Approaching limit, backing off...")
        time.sleep(0.5)
    
    return response.json()
```

---

## 429 Handling (Throttling)

When a client exceeds the rate limit, the API responds:

```json
{
    "success": false,
    "error": "Rate limit exceeded. Retry after 60 seconds.",
    "data": null
}
```

### Recommended Client Behavior

1. **Read retry time from header**: `Retry-After` (seconds) or `RateLimit-Reset` (Unix timestamp)
2. **Backoff exponentially**: 1s → 2s → 4s → 8s (with jitter)
3. **Queue requests**: Use a task queue instead of spinning requests in a loop
4. **Fallback to cache**: If stale data is acceptable, serve from cache

### Frontend (Streamlit) Example

```python
import streamlit as st
from datetime import datetime, timedelta

def get_signals_with_retry(symbol):
    """Fetch signals with automatic retry on 429."""
    @st.cache_data(ttl=300)  # cache for 5 minutes
    def _fetch(symbol):
        response = api_client.get_signals(symbol)
        if response is None:
            st.error("Failed to fetch signals")
            return []
        return response
    
    return _fetch(symbol)
```

---

## Whitelisting Trusted Clients

For internal services or high-volume partners, IP whitelisting can bypass rate limits.

### Configuration

Edit `infra/nginx/nginx.conf`:

```nginx
# Whitelist trusted IPs (internal services, partners)
geo $rate_limit_bypass {
    default 0;
    
    # Internal Docker network
    172.16.0.0/12 1;
    
    # Partner IP addresses
    203.0.113.50 1;   # Partner A
    198.51.100.100 1; # Partner B
    
    # Localhost
    127.0.0.1 1;
}

# Rate limiting zones — whitelisted clients skip entirely
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=30r/s;

location /api/ {
    if ($rate_limit_bypass = 1) {
        # Skip rate limiting for whitelisted IPs
        proxy_pass http://api/;
    }
    
    limit_req zone=api_limit burst=20 nodelay;
    proxy_pass http://api/;
}
```

Then reload Nginx:

```bash
# On VPS
docker-compose exec nginx nginx -s reload

# Or via Ansible
ansible-playbook -i infra/ansible/inventories/production.ini \
  infra/ansible/playbooks/configure-nginx.yml
```

### Adding a Partner IP

1. **Request**: Partner provides static IP or IP range
2. **Document**: Add to whitelist with comment (partner name, date, ticket)
3. **Reload**: `docker-compose exec nginx nginx -s reload`
4. **Verify**: Test from partner IP:
   ```bash
   curl -H "X-Forwarded-For: 203.0.113.50" https://crypto-bot.example.com/api/crypto/list
   ```
5. **Monitor**: Check logs for abuse
   ```bash
   tail -f /var/log/docker/nginx-access.log | grep "203.0.113.50"
   ```

---

## Monitoring & Alerting

### Key Metrics

Log these via Prometheus to detect abuse or DDoS:

- **429 response rate**: Should be < 0.1% for legitimate traffic
- **Unique IPs hitting limit**: Normal = 0-5/day; suspicious > 50/day
- **Most-limited endpoints**: Track which endpoints consume quota

### Nginx Access Log Format

```
$remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent" limit_req: $limit_req_status
```

Example parsing:

```bash
# Find clients being rate-limited
tail -f /var/log/docker/nginx-access.log | grep "limit_req: 429"

# Count 429s by hour
awk '{print $4}' /var/log/docker/nginx-access.log | sort | uniq -c

# Top IPs hitting rate limit
grep "429" /var/log/docker/nginx-access.log | awk '{print $1}' | sort | uniq -c | sort -rn | head -10
```

### Alerting Rules (Grafana)

See `infra/grafana/provisioning/alertmanager.yml` for threshold-based alerts:

- **API error rate > 0.1%**: Check for 429s or 5xxs
- **API p95 latency > 2s**: May indicate resource exhaustion from rate limit queue
- **Unique IPs hitting limit > 50/hour**: Potential DDoS

---

## Exemptions & Special Cases

### Health Checks (Always Exempt)

The `/api/health` endpoint is excluded from rate limiting (used for monitoring):

```nginx
location /health {
    access_log off;  # Don't log (noisy)
    proxy_pass http://api/health;
}
```

### Internal Services (Bypass via Whitelist)

Services within Docker Compose (frontend, ETL worker) are on the internal Docker network and should be whitelisted:

```nginx
geo $rate_limit_bypass {
    default 0;
    172.16.0.0/12 1;  # Docker internal network
}
```

### Development Mode

In development (docker-compose), rate limits are less strict. Override in `docker-compose.override.yml`:

```yaml
services:
  nginx:
    environment:
      NGINX_WORKER_CONNECTIONS: 1024  # dev: higher concurrency
      API_RATE_LIMIT: "1000r/s"       # dev: no practical limit
```

---

## Burst & Queue Behavior

The Nginx `burst` parameter allows temporary overages:

```nginx
limit_req zone=api_limit burst=20 nodelay;
```

- **burst=20**: Up to 20 requests can be queued above the sustained rate
- **nodelay**: Reject excess immediately (no queueing) — client must retry

**Example timeline**:

```
Time  Requests  Action
0s    30        OK (sustained rate)
0.1s  30        OK (burst +5 remaining)
0.2s  25        QUEUE (burst +15 remaining)
0.3s  25        QUEUE (burst +10 remaining)
0.4s  25        QUEUE (burst +5 remaining)
0.5s  5         REJECT (429, burst exhausted)
0.6s  OK        Refresh, new tokens available
```

---

## Testing Rate Limits

### Load Testing Tool (Apache Bench)

```bash
# Send 100 requests as fast as possible
ab -n 100 -c 10 http://localhost:8000/api/crypto/list

# Expected: Most requests after ~30 succeed, remainder get 429
```

### Curl with Headers

```bash
# Check rate limit headers
curl -v http://localhost:8000/api/crypto/list 2>&1 | grep "RateLimit"

# Expect output:
# < RateLimit-Limit: 30
# < RateLimit-Remaining: 29
# < RateLimit-Reset: 1678886400
```

### Python Script

```python
import requests
import time

BASE_URL = "http://localhost:8000"

for i in range(50):
    response = requests.get(f"{BASE_URL}/api/crypto/list")
    print(f"Request {i+1}: {response.status_code} | "
          f"Remaining: {response.headers.get('RateLimit-Remaining')}")
    
    if response.status_code == 429:
        reset = int(response.headers.get("RateLimit-Reset", time.time()))
        wait = reset - time.time()
        print(f"Rate limited. Reset in {wait:.1f}s")
        time.sleep(wait + 1)
        continue
    
    time.sleep(0.01)  # small delay to not saturate
```

---

## Troubleshooting

### "429 Too Many Requests" When Normal Traffic

**Cause**: Legitimate spikes exceed burst capacity.

**Fix**:
1. Increase `burst` parameter in Nginx (up to ~100)
2. Whitelist internal IPs
3. Implement caching on frontend (Streamlit)

```nginx
limit_req zone=api_limit burst=50 nodelay;
```

### Partner Reports 429 But Traffic is Light

**Cause**: Multiple users behind same proxy (NAT/corporate firewall).

**Fix**: Whitelist the partner's IP range:

```nginx
geo $rate_limit_bypass {
    203.0.113.0/24 1;  # Partner's network
}
```

### Nginx Reload Fails After Config Change

**Cause**: Syntax error in nginx.conf.

**Fix**:
```bash
# Test configuration
docker-compose exec nginx nginx -t

# Review logs
docker-compose logs nginx
```

---

## Production Best Practices

- [ ] Monitor 429 rates daily — should be < 0.1% of traffic
- [ ] Whitelist internal services (Docker network)
- [ ] Whitelist known partners (documented with ticket ID)
- [ ] Document all whitelist entries (who, when, why)
- [ ] Adjust limits based on observed traffic patterns (quarterly review)
- [ ] Set up alerting for DDoS detection (> 50 unique IPs/hour hitting limit)
- [ ] Implement Cloudflare or similar WAF for edge DDoS protection
- [ ] Test rate limit handling in smoke tests (CI/CD)

---

## Next Steps

1. **Local testing**: Use `ab` or `curl` to verify limits work
2. **Staging deployment**: Deploy to VPS, monitor for 24 hours
3. **Incident response**: See PRODUCTION_RUNBOOK.md § Rate Limit Abuse
4. **Quarterly review**: Analyze logs to identify needed adjustments

