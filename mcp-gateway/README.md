# EVP MCP Gateway

Streamable HTTP MCP adapter for read-only EVP business tools. Hermes injects
the short-lived `evp_execution_token` after tool selection; the patched Hermes
schema hides that infrastructure argument from the model.

Local endpoint: `http://localhost:8001/mcp`

```bash
docker build -t evp-mcp-gateway:dev mcp-gateway
docker run --rm -p 8001:8001 \
  -e PORT=8001 \
  -e EVP_BACKEND_URL=http://host.docker.internal:8000 \
  -e EVP_EXECUTION_PUBLIC_KEY="<public PEM>" \
  evp-mcp-gateway:dev
```
