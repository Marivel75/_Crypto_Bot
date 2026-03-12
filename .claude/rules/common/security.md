# Security Standards

## Secrets
- Never hardcode secrets, API keys, or passwords
- Never commit `.env` files (must be in `.gitignore`)
- Use environment variables or secret managers
- Rotate keys if accidentally exposed

## Input Validation
- Validate ALL external inputs with Pydantic models
- Parameterized queries only (never string concatenation for SQL)
- Sanitize file paths to prevent traversal attacks

## Error Handling
- Never expose internal errors, stack traces, or system info to users
- Log full errors server-side with `logging`
- Return generic error messages to clients

## API Security
- Rate limiting on all public endpoints
- Authentication on all non-public endpoints
- CORS configured restrictively
- HTTPS only in production

## Dependencies
- Pin dependency versions
- Audit dependencies regularly
- Minimal permissions principle
