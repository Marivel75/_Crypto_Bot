# Python Coding Style

## Type Safety (mandatory)
- Type hints on ALL function signatures — params and return type
- `from __future__ import annotations` at top of every file
- Use `typing` for complex types: `Optional[T]`, `Union[A, B]`, `list[T]`, `dict[K, V]`
- Pydantic v2 `BaseModel` for all data structures

## Code Quality
- `ruff check --fix` for linting
- `ruff format` for formatting (replaces black + isort)
- `mypy --strict` for type checking
- Max 200-400 lines per file; max 50 lines per function; max 3 indent levels

## Naming
- `snake_case`: functions, variables, modules
- `PascalCase`: classes
- `UPPER_SNAKE_CASE`: constants, env var names
- Descriptive: `calculate_position_size()` not `calc_ps()`

## Imports
```python
# Order: stdlib → third-party → local (ruff enforces this)
from __future__ import annotations
import asyncio
from pathlib import Path
from typing import Optional

import pydantic
import httpx

from myapp.models import User
```
- Absolute imports only, no relative imports across packages
- `pathlib.Path` only, never `os.path`
- `logging` only, never `print()` in production code

## Functions
```python
def process_data(
    data: list[dict[str, Any]],
    *,
    batch_size: int = 100,
) -> list[ProcessedRecord]:
    """Process raw data records.

    Parameters
    ----------
    data : list[dict[str, Any]]
        Raw input records from API.
    batch_size : int
        Number of records per processing batch.

    Returns
    -------
    list[ProcessedRecord]
        Validated and transformed records.
    """
    ...
```
