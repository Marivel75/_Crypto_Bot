# Git Workflow

## Commits
Format: `type(scope): description`

Types:
- `feat` : new feature
- `fix` : bug fix
- `refactor` : code change that neither fixes nor adds
- `test` : adding or updating tests
- `docs` : documentation only
- `chore` : maintenance, deps, CI

Example: `feat(backtest): add walk-forward validation`

## Branches
Format: `scope/feature-name`

Examples:
- `crypto/harmonic-patterns`
- `agency/n8n-webhook-handler`
- `infra/docker-health-checks`

## Pull Requests
- PR required for merges to main/master
- Description must include: what changed, why, how to test
- Squash merge preferred for feature branches

## Rules
- Never force push to main/master
- Never commit .env, secrets, or credentials
- Keep commits atomic: one logical change per commit
