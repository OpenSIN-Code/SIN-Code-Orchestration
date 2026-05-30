# Configuration

The orchestrator reads `config.yaml` (or `.sin/orchestration.yaml`).

## Sections

### `orchestration`
- `mode`: `hierarchical` | `parallel` | `reactive`
- `max_concurrent_agents`: int
- `timeout_seconds`: int

### `context_store`
- `backend`: `redis` | `memory` | `sqlite`
- `redis_url`: connection string (redis backend)
- `namespace`: key prefix (redis backend)
- `db_path`: path to SQLite file (sqlite backend)
- `ttl_seconds`: entry TTL (redis backend)

### `roles`
Per-role definition with `model`, `tools`, `max_iterations`, `sandbox`,
`require_approval`, `strict_mode`.

### `verification`
- `enabled`: bool
- `cycle`: pipeline label
- `max_retries`: int
- `escalate_on_failure`: bool

### `logging`
- `level`, `format`, `output`
