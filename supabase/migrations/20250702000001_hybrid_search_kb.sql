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
