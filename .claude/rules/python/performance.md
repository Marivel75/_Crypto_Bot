# Python Performance

## Profiling First
- Profile before optimizing: `cProfile`, `line_profiler`, `memory_profiler`
- Benchmark with `timeit` for micro-optimizations
- Use `py-spy` for production profiling without code changes

## Data Processing
```python
# Prefer list comprehensions over loops for simple transforms
squares = [x**2 for x in range(1000)]

# Use generators for large datasets (lazy evaluation)
def process_rows(rows: Iterable[dict]) -> Generator[ProcessedRow, None, None]:
    for row in rows:
        yield transform(row)

# NumPy for numerical operations — vectorized over loops
import numpy as np
result = np.sum(arr * weights)  # not: sum(a * w for a, w in zip(arr, weights))
```

## Pandas
```python
# Vectorized operations — never iterate rows with iterrows()
df["new_col"] = df["a"] + df["b"]  # good
for idx, row in df.iterrows(): ...  # bad

# Use .loc/.iloc for row selection
df.loc[df["status"] == "active", "score"] *= 1.1

# Read only needed columns
df = pd.read_csv("data.csv", usecols=["id", "price", "volume"])
```

## Async I/O
```python
# Parallel async tasks
async def fetch_all(urls: list[str]) -> list[dict]:
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_one(session, url) for url in urls]
        return await asyncio.gather(*tasks)
```

## Caching
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_computation(n: int) -> float:
    ...

# For async: use aiocache or manual dict cache
```

## Memory
- Use `__slots__` on high-volume dataclasses
- `del` large objects when done; use generators instead of lists for large pipelines
- `gc.collect()` only if profiling shows GC pressure
