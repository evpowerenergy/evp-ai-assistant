-- RUN_KB_PRODUCTION_MIGRATION.sql — idempotent; safe if RLS fix already applied
-- See docs/RAG_PRODUCTION_RUNBOOK.md

-- ========== 20250701000001_kb_production_schema.sql ==========
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

-- ========== 20250702000001_hybrid_search_kb.sql ==========
-- Hybrid search: vector + full-text with Reciprocal Rank Fusion

CREATE OR REPLACE FUNCTION public.hybrid_search_kb(
    query_embedding vector(1536),
    query_text text,
    match_count int DEFAULT 20,
    similarity_threshold float DEFAULT 0.65,
    category_filter text DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    content text,
    document_id uuid,
    chunk_index integer,
    chunk_level text,
    parent_chunk_id uuid,
    metadata jsonb,
    vector_score float,
    keyword_score float,
    fused_score float
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    rrf_k constant int := 60;
BEGIN
    RETURN QUERY
    WITH vector_hits AS (
        SELECT
            c.id,
            c.content,
            c.document_id,
            c.chunk_index,
            c.chunk_level,
            c.parent_chunk_id,
            c.metadata,
            (1 - (c.embedding <=> query_embedding))::float AS vscore,
            ROW_NUMBER() OVER (ORDER BY c.embedding <=> query_embedding) AS vrank
        FROM public.kb_chunks c
        JOIN public.kb_documents d ON d.id = c.document_id
        WHERE c.embedding IS NOT NULL
          AND c.chunk_level = 'child'
          AND d.status = 'ready'
          AND (category_filter IS NULL OR d.category = category_filter)
          AND (1 - (c.embedding <=> query_embedding)) >= similarity_threshold
        ORDER BY c.embedding <=> query_embedding
        LIMIT match_count
    ),
    keyword_hits AS (
        SELECT
            c.id,
            c.content,
            c.document_id,
            c.chunk_index,
            c.chunk_level,
            c.parent_chunk_id,
            c.metadata,
            ts_rank_cd(c.content_tsv, plainto_tsquery('simple', query_text))::float AS kscore,
            ROW_NUMBER() OVER (
                ORDER BY ts_rank_cd(c.content_tsv, plainto_tsquery('simple', query_text)) DESC
            ) AS krank
        FROM public.kb_chunks c
        JOIN public.kb_documents d ON d.id = c.document_id
        WHERE c.content_tsv @@ plainto_tsquery('simple', query_text)
          AND c.chunk_level = 'child'
          AND d.status = 'ready'
          AND (category_filter IS NULL OR d.category = category_filter)
        ORDER BY kscore DESC
        LIMIT match_count
    ),
    combined AS (
        SELECT
            COALESCE(v.id, k.id) AS cid,
            COALESCE(v.content, k.content) AS ccontent,
            COALESCE(v.document_id, k.document_id) AS cdocument_id,
            COALESCE(v.chunk_index, k.chunk_index) AS cchunk_index,
            COALESCE(v.chunk_level, k.chunk_level) AS cchunk_level,
            COALESCE(v.parent_chunk_id, k.parent_chunk_id) AS cparent_chunk_id,
            COALESCE(v.metadata, k.metadata) AS cmetadata,
            COALESCE(v.vscore, 0)::float AS cvscore,
            COALESCE(k.kscore, 0)::float AS ckscore,
            (COALESCE(1.0 / (rrf_k + v.vrank), 0) + COALESCE(1.0 / (rrf_k + k.krank), 0))::float AS cfused
        FROM vector_hits v
        FULL OUTER JOIN keyword_hits k ON v.id = k.id
    )
    SELECT
        cid,
        ccontent,
        cdocument_id,
        cchunk_index,
        cchunk_level,
        cparent_chunk_id,
        cmetadata,
        cvscore,
        ckscore,
        cfused
    FROM combined
    ORDER BY cfused DESC
    LIMIT match_count;
END;
$$;

GRANT EXECUTE ON FUNCTION public.hybrid_search_kb(vector, text, int, float, text) TO authenticated;
GRANT EXECUTE ON FUNCTION public.hybrid_search_kb(vector, text, int, float, text) TO service_role;

-- ========== 20250703000001_hnsw_index.sql ==========
-- HNSW index for kb_chunks embeddings (run after sufficient data; safe to recreate)

DROP INDEX IF EXISTS public.idx_kb_chunks_embedding;

CREATE INDEX IF NOT EXISTS idx_kb_chunks_embedding_hnsw
    ON public.kb_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- ========== 20250704000001_seed_rag_eval_cases.sql ==========
-- RAG eval cases (extends prompt_test_cases if table exists)

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'prompt_test_cases'
    ) THEN
        INSERT INTO public.prompt_test_cases (user_message, expected_intent, expected_tool, notes)
        VALUES
            ('ขั้นตอนการขอลามีอะไรบ้าง', 'rag_query', NULL, 'RAG eval: HR policy'),
            ('นโยบายการลาป่วยเป็นอย่างไร', 'rag_query', NULL, 'RAG eval: policy'),
            ('วิธีใช้งานระบบ CRM สำหรับลีดใหม่', 'rag_query', NULL, 'RAG eval: manual'),
            ('SOP การปิดการขายมีขั้นตอนอะไร', 'rag_query', NULL, 'RAG eval: SOP'),
            ('คู่มือการอนุมัติใบเสนอราคา', 'rag_query', NULL, 'RAG eval: manual'),
            ('procedure onboarding พนักงานใหม่', 'rag_query', NULL, 'RAG eval: EN keyword'),
            ('รายละเอียด QT2026030013', 'db_query', 'get_sales_docs', 'RAG negative: sales doc'),
            ('ใบแจ้งหนี้เดือนนี้มีอะไรบ้าง', 'db_query', 'get_sales_docs', 'RAG negative: invoice'),
            ('ลีดวันนี้มีกี่ราย', 'db_query', 'search_leads', 'RAG negative: leads'),
            ('ยอดขายเดือนนี้เท่าไหร่', 'db_query', 'get_sales_closed', 'RAG negative: sales'),
            ('เอกสารการขาย QT ล่าสุด', 'db_query', 'get_sales_docs', 'RAG negative: เอกสารการขาย'),
            ('ปิดการขายได้กี่รายเดือนนี้', 'db_query', 'get_sales_closed', 'RAG negative'),
            ('ทีมขาย KPI เดือนนี้', 'db_query', 'get_sales_team_overview', 'RAG negative'),
            ('Marketing dashboard ROAS', 'db_query', 'get_marketing_dashboard', 'RAG negative'),
            ('นัดหมายวันนี้', 'db_query', 'get_appointments', 'RAG negative'),
            ('Permit requests สถานะ', 'db_query', 'get_permit_requests', 'RAG negative'),
            ('แนวทางการติดตามลูกค้าหลังขาย package', 'rag_query', NULL, 'RAG eval'),
            ('กระบวนการอนุมัติส่วนลดพิเศษ', 'rag_query', NULL, 'RAG eval'),
            ('วิธีสร้างใบเสนอราคาในระบบ', 'rag_query', NULL, 'RAG eval: how-to'),
            ('ขั้นตอนการเบิกค่าใช้จ่าย', 'rag_query', NULL, 'RAG eval')
        ON CONFLICT DO NOTHING;
    END IF;
END $$;
