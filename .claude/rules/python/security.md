# Python Security

## Secrets Management
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    api_key: str
    secret_key: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()  # validates on startup, fails fast if missing
```

## Input Validation
- ALL external inputs via Pydantic models — no raw `dict` access
- Sanitize file paths: use `Path(user_input).resolve()` and check it stays within allowed dir
- Never use `eval()` or `exec()` with user input
- SQL: always use parameterized queries via ORM or `cursor.execute(sql, params)`

## Process Execution
```python
import subprocess

# Safe: use list args with subprocess.run, never shell=True with user input
result = subprocess.run(
    ["git", "log", "--oneline", branch_name],
    capture_output=True,
    text=True,
    check=True,
)
```

## Cryptography
```python
# Passwords: bcrypt via passlib
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"])
hashed = pwd_context.hash(plain_password)

# Symmetric encryption: Fernet
from cryptography.fernet import Fernet
key = Fernet.generate_key()
f = Fernet(key)
token = f.encrypt(b"secret data")
```

## File Operations
```python
# Validate paths to prevent directory traversal
def safe_read(base_dir: Path, filename: str) -> str:
    resolved = (base_dir / filename).resolve()
    if not resolved.is_relative_to(base_dir.resolve()):
        raise ValueError("Path traversal detected")
    return resolved.read_text()
```

## Error Handling
- Never expose stack traces or system info to users
- Log full context server-side with `logger.error(..., exc_info=True)`
- Return generic messages to clients: `{"error": "Internal server error"}`
