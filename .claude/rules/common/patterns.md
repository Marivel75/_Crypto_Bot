# Patterns (Common)

## Design Patterns to Use
- **Repository**: abstract data access behind interfaces
- **Factory**: for complex object creation
- **Strategy**: swappable algorithms/behaviors
- **Observer/Event**: decouple producers from consumers

## Patterns to Avoid
- **God objects**: classes that do everything
- **Premature abstraction**: DRY only after 3+ repetitions
- **Deep inheritance**: prefer composition over inheritance
- **Singleton abuse**: prefer dependency injection

## API Design
- RESTful resources: nouns not verbs (`/users`, not `/getUsers`)
- Consistent error format: `{ "error": { "code": "...", "message": "..." } }`
- Versioning: `/api/v1/` prefix
- Idempotent PUT/DELETE; POST for non-idempotent creates

## Data Flow
- Validate at boundaries (API entry, external data)
- Transform once, use everywhere
- Immutable data structures where possible
