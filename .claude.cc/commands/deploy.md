# Deploy to VPS

Deploy the crypto-bot application to the production VPS using Ansible.

## Steps
1. Run linting and type checks: `cd /Users/amaury/Desktop/jules/crypto-bot && ruff check src/ && mypy src/`
2. Run tests: `pytest tests/ -x --tb=short`
3. Build Docker images: `docker-compose build`
4. Deploy with Ansible: `ansible-playbook -i infra/ansible/inventories/production.ini infra/ansible/playbooks/deploy.yml`
5. Verify deployment: `curl -f https://YOUR_DOMAIN/api/health`

## Pre-deploy Checklist
- [ ] All tests pass
- [ ] No ruff/mypy errors
- [ ] `.env` is up to date on VPS
- [ ] Docker images build successfully
- [ ] No secrets in code
