# Security Rules

These rules apply to ALL code in this project.

## Secrets Management

- **NEVER** commit `.env` files to git
- **NEVER** hardcode API keys, tokens, passwords, or credentials in code
- **NEVER** log sensitive values (tokens, passwords, API keys)
- **ALWAYS** use environment variables for secrets
- **ALWAYS** update `.env.example` when adding new environment variables
- Use placeholder values in examples: `your-api-key-here`, `<YOUR_TOKEN>`

## Input Validation

- Validate ALL user inputs at API boundaries
- Use Pydantic models for request validation
- Sanitize inputs before database operations
- Use parameterized queries (SQLAlchemy handles this automatically)
- Validate file paths to prevent directory traversal

## Telegram Security

- Whitelist authorized users via `TELEGRAM_ALLOWED_USER_IDS`
- Log unauthorized access attempts (but don't respond to them)
- Require explicit confirmation for destructive actions
- Never expose internal error details to users

## API Security

- Use HTTPS in production
- Validate authentication tokens
- Rate limit endpoints where appropriate
- Return generic error messages to clients (log details internally)

## Database Security

- Never construct SQL queries with string concatenation
- Use ORM methods or parameterized queries exclusively
- Validate UUIDs before database lookups
- Handle missing records gracefully (don't expose existence)

## Docker Security

- Run containers as non-root users where possible
- Don't expose unnecessary ports
- Use internal Docker network for service communication
- Don't mount sensitive host directories

## Code Review Checklist

Before committing, verify:
- [ ] No hardcoded secrets or credentials
- [ ] `.env.example` updated if new env vars added
- [ ] Input validation on all user-facing endpoints
- [ ] Error messages don't leak internal details
- [ ] Logging doesn't include sensitive data

## Anti-Patterns

- **DON'T** commit `.env` files or any file containing real credentials
- **DON'T** hardcode secrets in code, configs, or Dockerfiles
- **DON'T** log tokens, passwords, API keys, or user credentials
- **DON'T** construct SQL queries with string concatenation or f-strings
- **DON'T** expose stack traces or internal error details to API clients
- **DON'T** trust user input without validation at API boundaries
- **DON'T** respond to unauthorized Telegram users (log silently)
- **DON'T** expose unnecessary ports or mount sensitive host directories
- **DON'T** run containers as root when avoidable
