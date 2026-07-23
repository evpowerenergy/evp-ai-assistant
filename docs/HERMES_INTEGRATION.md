# Hermes Integration Runbook

## Current rollout state

- LangGraph remains the default and fallback engine.
- Hermes and the MCP gateway run in separate containers.
- The first MCP surface is read-only: CRM summary/search, closed and
  unsuccessful sales, marketing dashboard, and knowledge search.
- Supabase remains the canonical chat-history and audit store.

## Local ports

| Service | Port |
|---|---:|
| Next.js | 3000 |
| EVP FastAPI | 8000 |
| EVP MCP gateway | 8001 |
| Hermes API | 8642 |

## One-time key setup

Generate an Ed25519 capability key pair outside the repository:

```bash
openssl genpkey -algorithm Ed25519 -out evp-execution-private.pem
openssl pkey -in evp-execution-private.pem -pubout -out evp-execution-public.pem
```

Store the private key only in the backend Secret Manager configuration. Store
the public key in the backend/MCP verifier configuration. Never commit either
production key.

## Startup order

1. Apply `20260719000001_agent_runtime_audit.sql` to Supabase.
2. Configure backend JWT verification. Legacy HS256 Supabase projects require
   `SUPABASE_JWT_SECRET`; asymmetric projects use JWKS automatically.
3. Build and run `mcp-gateway`, pointing `EVP_BACKEND_URL` at FastAPI.
4. Complete Hermes provider setup in a persistent `/opt/data` directory.
5. Add the `evp` MCP entry from `hermes-runtime/config.example.yaml`.
6. Build and run `hermes-runtime` with `API_SERVER_KEY`.
7. Configure FastAPI with the Hermes URL/key and execution signing keys.
8. Keep `AI_PRIMARY_ENGINE=langgraph` while validating staging/shadow traffic.
9. Set `AI_PRIMARY_ENGINE=hermes` only after the read-only evaluation passes.

## Security contract

FastAPI signs a two-minute EdDSA capability. The capability travels in
`X-EVP-Execution-Token`, is bound to the HMAC-scoped Hermes session, and is
injected into MCP arguments after model tool selection. The patched schema
hides this argument from the model. MCP and the backend verify scope again;
model-provided identity fields are ignored.

`X-Hermes-Session-Id` is intentionally not sent. Sending it would make Hermes
prefer its local SQLite transcript. FastAPI instead sends the complete
Supabase conversation plus an opaque `X-Hermes-Session-Key`.

## Verification

```bash
cd backend
venv/bin/python -m pytest -q

cd ../frontend
npm run build

cd ..
docker build -t evp-mcp-gateway:test mcp-gateway
docker build -t evp-hermes-runtime:test hermes-runtime
```

Do not enable write/external tools until approval, idempotency, and unknown
outcome handling are implemented.
# Local development

Start the Backend with Hermes credentials, both execution-token keys, and the
research-safe timeout policy:

```bash
./scripts/dev-backend.sh
```

The script sets the Hermes turn timeout and execution-token TTL to 900 seconds.
