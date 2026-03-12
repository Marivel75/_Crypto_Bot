# Performance (Common)

## Principles
- Measure before optimizing — profile first, optimize hotspots
- Prefer algorithmic improvements (O(n) → O(log n)) over micro-optimizations
- Cache at the right layer: CDN → app cache → DB query cache

## Database
- Index foreign keys and frequently queried columns
- Use SELECT with explicit columns, never SELECT *
- Paginate large result sets (LIMIT/OFFSET or cursor-based)
- Avoid N+1 queries — use joins or batch fetching

## API / Network
- Batch API calls where possible
- Use connection pooling for database connections
- Compress responses (gzip/brotli) for large payloads
- Set appropriate timeouts on all outbound calls

## Async / Concurrency
- Use async I/O for network and file operations
- Avoid blocking the event loop in Node.js
- Use worker queues for CPU-intensive tasks
