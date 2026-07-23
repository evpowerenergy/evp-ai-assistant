# EVP Hermes Runtime

Hermes is deliberately isolated from the legacy FastAPI virtual environment.
The image is pinned to `v2026.7.7.2` and applies a small audited patch that
passes the signed EVP capability to the `evp` MCP server without exposing the
token to the model or its tool schemas.

Build from the repository root:

```bash
docker build -t evp-hermes-runtime:dev hermes-runtime
```

Required runtime configuration:

- `API_SERVER_KEY`
- an LLM provider key/config supported by Hermes
- `/opt/data/config.yaml` containing the `evp` remote MCP server
- `EVP_MCP_SERVER_NAME=evp`

The container listens on Cloud Run's conventional port `8080`. For local use,
publish it as `-p 8642:8080`; FastAPI can keep using
`HERMES_BASE_URL=http://127.0.0.1:8642`.

The patch intentionally fails the image build when the pinned upstream source
no longer matches. Upgrade Hermes only after rebasing the patch and running the
runtime contract tests.
