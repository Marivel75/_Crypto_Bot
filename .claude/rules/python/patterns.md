# Python Patterns

## Pydantic v2 Data Models
```python
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Annotated

class TradeSignal(BaseModel):
    symbol: str = Field(min_length=2, max_length=20)
    side: Literal["BUY", "SELL"]
    quantity: Annotated[float, Field(gt=0)]
    price: Annotated[float, Field(gt=0)]

    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, v: str) -> str:
        return v.upper()

    @model_validator(mode="after")
    def check_notional(self) -> "TradeSignal":
        if self.quantity * self.price < 10:
            raise ValueError("Notional too small")
        return self
```

## Repository Pattern
```python
class UserRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_id(self, user_id: str) -> Optional[User]:
        return self._db.query(User).filter(User.id == user_id).first()

    def save(self, user: User) -> User:
        self._db.add(user)
        self._db.flush()
        return user
```

## Dependency Injection
```python
# Use constructor injection, not global singletons
class OrderService:
    def __init__(
        self,
        repo: OrderRepository,
        exchange: ExchangeClient,
        logger: logging.Logger,
    ) -> None:
        self._repo = repo
        self._exchange = exchange
        self._logger = logger
```

## Async Patterns
```python
# Context manager for resources
async with aiohttp.ClientSession() as session:
    response = await session.get(url)
    data = await response.json()

# Gather with error handling
results = await asyncio.gather(*tasks, return_exceptions=True)
errors = [r for r in results if isinstance(r, Exception)]
```

## Logging
```python
import logging

logger = logging.getLogger(__name__)

# Structured logging — not f-strings with sensitive data
logger.info("Order created", extra={"order_id": order.id, "symbol": order.symbol})
logger.error("Exchange error", exc_info=True, extra={"exchange": "binance"})
```
