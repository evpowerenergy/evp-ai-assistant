-- Vector Search RPC Function
-- Migration: 20250116000004_vector_search_rpc.sql

-- Function: Match KB Chunks (Vector Similarity Search)
CREATE OR REPLACE FUNCTION match_kb_chunks(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 5
)
RETURNS TABLE (
    id uuid,
    content text,
    document_id uuid,
    chunk_index integer,
    distance float,
    metadata jsonb
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT
        kb_chunks.id,
        kb_chunks.content,
        kb_chunks.document_id,
        kb_chunks.chunk_index,
        1 - (kb_chunks.embedding <=> query_embedding) as distance,  -- Cosine distance
        kb_chunks.metadata
    FROM kb_chunks
    WHERE kb_chunks.embedding IS NOT NULL
    AND (1 - (kb_chunks.embedding <=> query_embedding)) >= match_threshold
    ORDER BY kb_chunks.embedding <=> query_embedding  -- Order by distance (ascending = most similar)
    LIMIT match_count;
END;
$$;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION match_kb_chunks(vector, float, int) TO authenticated;
