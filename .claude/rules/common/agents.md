# Agents (Common)

## Agent Roster

| Agent | Model | Purpose |
|-------|-------|---------|
| python-ml | sonnet | Python ML, backtesting, scikit-learn, ccxt |
| crypto | sonnet | Crypto trading strategies, technical analysis |
| devops | sonnet | Docker, VPS, CI/CD, Nginx, systemd |
| content-closing | sonnet | Instagram content, DM closing, copywriting |
| oracle-fusion | sonnet | Oracle ERP, FBDI, SOAP/REST APIs, PL/SQL |
| n8n-automations | sonnet | n8n workflows, webhooks, integrations |
| nextjs-typescript | sonnet | Next.js App Router, TypeScript, Supabase |
| debug | sonnet | Bug investigation and fix orchestration |
| code | sonnet | Feature implementation coordinator |
| optimize | sonnet | Performance optimization |
| bmad-* | sonnet | BMAD methodology (architect, dev, pm, qa) |
| requirements-* | sonnet | Requirements gathering and generation |

## Model Selection
- **opus**: deep reasoning tasks (complex algo design, architecture decisions)
- **sonnet**: default for all development tasks (cost-efficient, fast)
- **haiku**: subagent tasks, simple lookups, quick transforms (`CLAUDE_CODE_SUBAGENT_MODEL=haiku`)

## Agent Usage Patterns
- Delegate to specialized agent when task matches its domain
- Use `bmad-orchestrator` for multi-agent coordination
- Use `debug` for systematic bug investigation
- Use `code` for feature implementation with review loop
