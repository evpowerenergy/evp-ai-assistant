# RAG Production Runbook

## Prerequisites

1. Run SQL migrations on the shared Supabase project (in order):
   - `supabase/scripts/run/RUN_FIX_KB_DOCUMENTS_RLS.sql` (if not already applied)
   - **Or run all remaining migrations in one file:** `supabase/scripts/run/RUN_KB_PRODUCTION_MIGRATION.sql`
     (skips duplicate RLS section; idempotent `DROP POLICY IF EXISTS` where needed)

   Individual files if you prefer:
   - `supabase/migrations/20250701000001_kb_production_schema.sql`
   - `supabase/migrations/20250702000001_hybrid_search_kb.sql`
   - `supabase/migrations/20250703000001_hnsw_index.sql` (after ~100+ chunks indexed)
   - `supabase/migrations/20250704000001_seed_rag_eval_cases.sql`
   - `supabase/migrations/20250705000001_chat_mode_preference.sql` (shared CRM/KB mode for web + LINE)

2. Backend env: `SUPABASE_SERVICE_ROLE_KEY` must be the **service role** key (not anon).

3. Docker image includes `tesseract-ocr` + `tesseract-ocr-tha` for scanned PDF OCR.

## Upload documents (super_admin)

1. Open `/admin/documents`
2. Upload PDF, DOCX, TXT, or MD (max 20MB)
3. Status flow: `queued` → `processing` → `ready` (or `failed`)
4. Original file stored in private bucket `kb-documents`

## API endpoints

| Method | Path | Role |
|--------|------|------|
| POST | `/api/v1/ingest` | super_admin |
| GET | `/api/v1/documents` | AI assistant roles |
| GET | `/api/v1/documents/{id}/status` | AI assistant roles |
| GET | `/api/v1/documents/{id}/download` | super_admin |
| DELETE | `/api/v1/documents/{id}` | super_admin |
| POST | `/api/v1/documents/{id}/reindex` | super_admin |

## Troubleshooting

### `permission denied for table users`

Run `RUN_FIX_KB_DOCUMENTS_RLS.sql`. Use backend API for document list (not direct Supabase client).

### PDF upload fails / empty text

- Text-based PDF: should work via pymupdf
- Scanned PDF: requires OCR (`KB_ENABLE_OCR=true`) and tesseract in container
- Convert to `.docx` or `.txt` if OCR quality is poor

### Ingest stuck in `processing`

- Check backend logs for `document_id`
- Stale jobs (>30 min): mark failed and use **Reindex**
- Cloud Run: ensure enough memory (1Gi+) and timeout

### RAG returns no results

- Confirm document `status=ready` and `chunk_count > 0`
- Check chat metadata field `rag` for retrieval scores
- Lower `KB_SIMILARITY_THRESHOLD` in config if needed

### Reindex after chunking changes

1. DELETE not required — use **Reindex** button
2. Reindex re-downloads original from Storage and rebuilds chunks/embeddings

## Eval before deploy

1. Run prompt tests at `/admin/prompt-tests`
2. Verify RAG eval cases (intent routing)
3. Manual test: upload SOP → ask related question → citation appears
4. Manual test: ask `QT2026030013` → must use CRM tools, not RAG

## Chat mode (CRM vs เอกสารบริษัท)

- **Web:** segmented toggle above the message input (CRM vs เอกสารบริษัท)
- **LINE:** Quick Reply buttons on bot replies, or text commands `MODE CRM` / `MODE KB`
- Preference is stored in `user_chat_preferences.chat_mode` (shared across web and LINE)
- **CRM mode:** CRM router/tools only — no RAG
- **KB mode:** RAG only — CRM-style questions get a hint to switch modes

Smoke tests:
1. Web CRM + `ลีดวันนี้` → CRM tools
2. Web KB + company reference question → citation from documents
3. Web KB + `ลีดวันนี้` → switch-mode hint (no CRM data)
4. Switch mode on web → same mode on LINE for the same user

## Config reference (`backend/.env`)

```
KB_MAX_FILE_BYTES=20000000
KB_MAX_CHUNKS=500
KB_SIMILARITY_THRESHOLD=0.38
KB_ENABLE_HYBRID_SEARCH=true
KB_ENABLE_RERANK=true
KB_ENABLE_OCR=true
KB_ENABLE_QUERY_REWRITE=true
```
