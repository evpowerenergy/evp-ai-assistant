# Supabase Migrations

This directory contains database migrations for the AI Assistant system.

## Migration Files

1. **20250116000001_initial_schema.sql** - Initial database schema
   - Tables: `chat_sessions`, `chat_messages`, `audit_logs`
   - Tables: `kb_documents`, `kb_chunks` (with pgvector)
   - Table: `line_identities`
   - RLS policies

2. **20250116000002_initial_rpc_functions.sql** - Initial RPC functions
   - `ai_get_lead_status`
   - `ai_get_daily_summary`
   - `ai_get_customer_info`

## Running Migrations

### Using Supabase CLI

```bash
# Apply migrations
supabase db push

# Or apply specific migration
supabase migration up
```

### Using Supabase Dashboard

1. Go to Supabase Dashboard
2. Navigate to SQL Editor
3. Run migration files in order

## Notes

- All RPC functions use `SECURITY DEFINER` to bypass RLS
- RLS policies are enforced at table level
- pgvector extension is required for document embeddings
- UUID extension is required for primary keys
