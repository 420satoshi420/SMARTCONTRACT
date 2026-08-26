# Access Control Knowledge Deep Dive

### High-Value Vectors
- `tx.origin` used in payment splitters or wallet recovery modules
- Unprotected `initialize()` functions on proxy implementations
- Missing `onlyRole(DEFAULT_ADMIN_ROLE)` on fee withdrawal or contract pause functions
