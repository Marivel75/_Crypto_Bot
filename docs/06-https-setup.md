# HTTPS Setup with Let's Encrypt

**Author**: DevOps Team  
**Status**: Implementation Guide (S6 Audit Fix)  
**Date**: 2026-03-12

## Overview

This guide explains how to enable HTTPS with Let's Encrypt SSL certificates on your production VPS. All traffic is automatically redirected from HTTP to HTTPS once configured.

## Prerequisites

- Public domain name (e.g., `crypto-bot.example.com`)
- Domain pointing to VPS IP address (A record)
- VPS with Nginx (via Docker Compose)
- Port 80 open for Let's Encrypt validation

## Quick Start

### 1. Run HTTPS Setup Playbook

```bash
ansible-playbook -i infra/ansible/inventories/production.ini \
  infra/ansible/playbooks/setup-https.yml \
  -e "domain=crypto-bot.example.com" \
  -e "email=admin@example.com"
```

This playbook:
- Installs `certbot` and dependencies
- Requests initial certificate from Let's Encrypt
- Sets up automatic renewal (systemd timer + cron)
- Validates certificate installation

### 2. Update Docker Compose

Add the Let's Encrypt volume mount to the Nginx service in `docker-compose.yml`:

```yaml
nginx:
  volumes:
    - ./infra/nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    - /etc/letsencrypt:/etc/letsencrypt:ro  # Add this line
```

Also create the certbot validation directory:

```bash
mkdir -p /var/www/certbot/.well-known/acme-challenge
chmod 755 /var/www/certbot
```

### 3. Update Nginx Config

Edit `infra/nginx/nginx.conf` and ensure the `server_name` directive matches your domain:

```nginx
server {
    listen 443 ssl http2;
    server_name crypto-bot.example.com;  # Replace with your domain
    ssl_certificate /etc/letsencrypt/live/crypto-bot.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/crypto-bot.example.com/privkey.pem;
    # ... rest of config
}
```

### 4. Restart Services

```bash
docker compose down
docker compose up -d

# Verify HTTPS is working
curl -v https://crypto-bot.example.com
```

## Certificate Renewal

Certificates are renewed **automatically** via:

1. **Systemd Timer** — runs twice daily at 02:00 and 14:00 UTC
2. **Cron Fallback** — same schedule as fallback

To check renewal status:

```bash
# View systemd timer status
systemctl status certbot-renew.timer

# View renewal logs
journalctl -u certbot-renew.service -n 20

# Manual renewal test
certbot renew --dry-run

# Check certificate expiration
openssl x509 -in /etc/letsencrypt/live/crypto-bot.example.com/fullchain.pem \
  -noout -dates
```

## Troubleshooting

### Certificate Not Obtained

**Problem**: Certbot fails with "DNS problem" or "Connection refused"

**Solutions**:
1. Verify port 80 is accessible: `curl -i http://crypto-bot.example.com`
2. Check DNS resolution: `nslookup crypto-bot.example.com`
3. Check firewall: `sudo ufw status`
4. Review certbot logs: `tail -f /var/log/letsencrypt/letsencrypt.log`

### Nginx Can't Find Certificates

**Problem**: Nginx fails to start with "no such file or directory"

**Solutions**:
1. Verify certificate exists: `ls -la /etc/letsencrypt/live/crypto-bot.example.com/`
2. Check docker-compose.yml volume mount
3. Ensure Nginx config uses correct domain name
4. Restart Nginx: `docker compose restart nginx`

### Mixed Content Warning

**Problem**: Browser warns "This page includes other resources which are not secure"

**Solutions**:
1. Update all API URLs in frontend to use `https://`
2. Check CSP header in nginx.conf (should allow https: for external resources)
3. Verify all static assets are served over HTTPS

## Certificate Files Location

```
/etc/letsencrypt/
├── live/
│   └── crypto-bot.example.com/
│       ├── fullchain.pem  # Server certificate chain
│       ├── privkey.pem    # Private key (keep secure!)
│       ├── cert.pem       # Server certificate only
│       └── chain.pem      # Intermediate certificates
├── archive/               # Previous certificate versions (backup)
└── renewal/               # Renewal configuration
```

**Important**: Backup the entire `/etc/letsencrypt` directory regularly!

## Certificate Validity

- **Duration**: 90 days
- **Auto-renewal**: Begins 30 days before expiration
- **Grace period**: 14 days to renew before expiration

Monitor with:
```bash
# Show all certificates
certbot certificates

# Show specific certificate expiration
echo | openssl s_client -servername crypto-bot.example.com -connect crypto-bot.example.com:443 2>/dev/null | openssl x509 -noout -dates
```

## Security Best Practices

1. **Never expose `/etc/letsencrypt/live/*/privkey.pem`** — Keep private keys secure
2. **Use HTTPS redirect** — All HTTP traffic auto-redirects to HTTPS (configured in nginx.conf)
3. **Enable HSTS** — Browsers cache HTTPS preference (max-age=31536000, already enabled)
4. **Backup certificates** — Regularly backup `/etc/letsencrypt/archive/`
5. **Monitor renewal** — Set calendar reminders or alerts for certificate expiration

## Advanced: Manual Certificate Management

```bash
# Renew all certificates immediately
certbot renew --force-renewal

# Revoke a certificate
certbot revoke --cert-path /etc/letsencrypt/live/crypto-bot.example.com/fullchain.pem

# Delete a certificate
certbot delete --cert-name crypto-bot.example.com

# Add additional domain (SAN)
certbot certonly --cert-name crypto-bot.example.com -d crypto-bot.example.com -d www.crypto-bot.example.com
```

## Nginx Configuration Details

### HTTP to HTTPS Redirect
```nginx
location / {
    return 301 https://$host$request_uri;
}
```

### ACME Challenge (for renewal)
```nginx
location /.well-known/acme-challenge/ {
    root /var/www/certbot;
}
```

### TLS Configuration
- **Minimum TLS**: 1.2
- **Supported**: TLS 1.2 and TLS 1.3
- **Ciphers**: ECDHE-based (perfect forward secrecy)
- **HSTS**: 1 year with subdomains and preload

## Monitoring & Alerts

Recommended monitoring:
1. **Certificate expiration** — Alert 30 days before
2. **Renewal failures** — Monitor `/var/log/letsencrypt/letsencrypt.log`
3. **HTTPS availability** — Health check on `/health` endpoint via HTTPS
4. **SSL labs grade** — Monitor at https://www.ssllabs.com/ssltest/

## Related Files

- Nginx config: `/infra/nginx/nginx.conf`
- Docker Compose: `/docker-compose.yml`
- Ansible playbook: `/infra/ansible/playbooks/setup-https.yml`
- Renewal script: `/usr/local/bin/certbot-renew.sh` (created on VPS)

## Audit Compliance

This implementation addresses audit finding **S6** — Enable HTTPS + Let's Encrypt:
- Eliminates man-in-the-middle vulnerability
- Protects credentials and tokens in transit
- Enables secure WebSocket (WSS) for Streamlit
- Satisfies GDPR/security compliance requirements

## Support

For issues:
1. Check `/var/log/letsencrypt/letsencrypt.log`
2. Review Docker Compose logs: `docker compose logs nginx`
3. Test connectivity: `curl -v https://crypto-bot.example.com`
4. Consult Let's Encrypt docs: https://certbot.eff.org/
