-- KB Production schema: storage metadata, ingest jobs, chunk enhancements

-- kb_documents extensions
ALTER TABLE public.kb_documents
    ADD COLUMN IF NOT EXISTS storage_bucket TEXT DEFAULT 'kb-documents',
    ADD COLUMN IF NOT EXISTS storage_path TEXT,
    ADD COLUMN IF NOT EXISTS file_size BIGINT,
    ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'ready'
        CHECK (status IN ('queued', 'processing', 'ready', 'failed')),
    ADD COLUMN IF NOT EXISTS error_message TEXT,
    ADD COLUMN IF NOT EXISTS chunk_count INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS content_hash TEXT,
    ADD COLUMN IF NOT EXISTS category TEXT,
    ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1,
    ADD COLUMN IF NOT EXISTS indexed_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_kb_documents_status ON public.kb_documents(status);
CREATE INDEX IF NOT EXISTS idx_kb_documents_content_hash ON public.kb_documents(content_hash);
CREATE INDEX IF NOT EXISTS idx_kb_documents_category ON public.kb_documents(category);

-- kb_chunks extensions
ALTER TABLE public.kb_chunks
    ADD COLUMN IF NOT EXISTS content_tsv tsvector,
    ADD COLUMN IF NOT EXISTS parent_chunk_id UUID REFERENCES public.kb_chunks(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS chunk_level TEXT DEFAULT 'child'
        CHECK (chunk_level IN ('parent', 'child'));

CREATE INDEX IF NOT EXISTS idx_kb_chunks_parent ON public.kb_chunks(parent_chunk_id);
CREATE INDEX IF NOT EXISTS idx_kb_chunks_level ON public.kb_chunks(chunk_level);

-- Full-text search on chunks
CREATE OR REPLACE FUNCTION public.kb_chunks_content_tsv_trigger()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.content_tsv := to_tsvector('simple', coalesce(NEW.content, ''));
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS kb_chunks_content_tsv_update ON public.kb_chunks;
CREATE TRIGGER kb_chunks_content_tsv_update
    BEFORE INSERT OR UPDATE OF content ON public.kb_chunks
    FOR EACH ROW
    EXECUTE FUNCTION public.kb_chunks_content_tsv_trigger();

-- Backfill existing rows
UPDATE public.kb_chunks
SET content_tsv = to_tsvector('simple', coalesce(content, ''))
WHERE content_tsv IS NULL;

CREATE INDEX IF NOT EXISTS idx_kb_chunks_content_tsv ON public.kb_chunks USING GIN(content_tsv);

-- Ingest jobs
CREATE TABLE IF NOT EXISTS public.kb_ingest_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES public.kb_documents(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'processing', 'completed', 'failed')),
    progress_pct INTEGER DEFAULT 0 CHECK (progress_pct >= 0 AND progress_pct <= 100),
    error_message TEXT,
    created_by UUID,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kb_ingest_jobs_document ON public.kb_ingest_jobs(document_id);
CREATE INDEX IF NOT EXISTS idx_kb_ingest_jobs_status ON public.kb_ingest_jobs(status);

ALTER TABLE public.kb_ingest_jobs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Authenticated can view ingest jobs" ON public.kb_ingest_jobs;
CREATE POLICY "Authenticated can view ingest jobs"
    ON public.kb_ingest_jobs FOR SELECT
    TO authenticated
    USING (auth.role() = 'authenticated');

-- Storage bucket (private)
INSERT INTO storage.buckets (id, name, public)
VALUES ('kb-documents', 'kb-documents', false)
ON CONFLICT (id) DO UPDATE SET public = false;

-- RLS fix for kb_documents (drop broken auth.users policy if exists)
DROP POLICY IF EXISTS "Admins can manage documents" ON public.kb_documents;

DROP POLICY IF EXISTS "AI managers can insert kb documents" ON public.kb_documents;
CREATE POLICY "AI managers can insert kb documents"
    ON public.kb_documents FOR INSERT TO authenticated
    WITH CHECK (public.is_admin_or_manager());

DROP POLICY IF EXISTS "AI managers can update kb documents" ON public.kb_documents;
CREATE POLICY "AI managers can update kb documents"
    ON public.kb_documents FOR UPDATE TO authenticated
    USING (public.is_admin_or_manager())
    WITH CHECK (public.is_admin_or_manager());

DROP POLICY IF EXISTS "AI managers can delete kb documents" ON public.kb_documents;
CREATE POLICY "AI managers can delete kb documents"
    ON public.kb_documents FOR DELETE TO authenticated
    USING (public.is_admin_or_manager());

DROP POLICY IF EXISTS "AI managers can manage kb chunks" ON public.kb_chunks;
CREATE POLICY "AI managers can manage kb chunks"
    ON public.kb_chunks FOR INSERT TO authenticated
    WITH CHECK (public.is_admin_or_manager());

DROP POLICY IF EXISTS "AI managers can update kb chunks" ON public.kb_chunks;
CREATE POLICY "AI managers can update kb chunks"
    ON public.kb_chunks FOR UPDATE TO authenticated
    USING (public.is_admin_or_manager())
    WITH CHECK (public.is_admin_or_manager());

DROP POLICY IF EXISTS "AI managers can delete kb chunks" ON public.kb_chunks;
CREATE POLICY "AI managers can delete kb chunks"
    ON public.kb_chunks FOR DELETE TO authenticated
    USING (public.is_admin_or_manager());
