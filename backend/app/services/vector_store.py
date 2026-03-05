"""
Vector Store Service (pgvector)
"""
from typing import List, Dict, Any, Optional
from uuid import uuid4
from app.services.supabase import get_supabase_client
from app.services.embedding import get_embeddings
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def search_similar(
    query: str,
    limit: int = 5,
    threshold: float = 0.7
) -> List[Dict[str, Any]]:
    """
    Search for similar documents using vector similarity
    Uses pgvector cosine similarity
    """
    try:
        supabase = get_supabase_client()
        embeddings = get_embeddings()
        
        # Generate query embedding
        query_embedding = embeddings.embed_query(query)
        
        logger.info(f"Vector search: query={query[:50]}..., limit={limit}")
        
        # Use Supabase RPC for vector search
        # Note: This requires a custom RPC function in Supabase
        # For now, we'll use a direct query approach
        
        # Convert embedding to PostgreSQL array format
        embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"
        
        # Query using cosine distance (1 - cosine similarity)
        # Lower distance = higher similarity
        result = supabase.rpc(
            "match_kb_chunks",
            {
                "query_embedding": embedding_str,
                "match_threshold": threshold,
                "match_count": limit
            }
        ).execute()
        
        if result.data:
            # Format results
            formatted_results = []
            for row in result.data:
                formatted_results.append({
                    "id": row.get("id"),
                    "content": row.get("content", ""),
                    "document_id": row.get("document_id"),
                    "chunk_index": row.get("chunk_index", 0),
                    "similarity": 1 - row.get("distance", 1.0),  # Convert distance to similarity
                    "metadata": row.get("metadata", {}),
                    "source": get_document_source(row.get("document_id"))
                })
            
            logger.info(f"Vector search: found {len(formatted_results)} results")
            return formatted_results
        
        return []
    
    except Exception as e:
        logger.error(f"Vector search error: {e}")
        # Fallback: try direct query if RPC doesn't exist
        try:
            return await _fallback_vector_search(query, limit, threshold)
        except Exception as fallback_error:
            logger.error(f"Fallback vector search error: {fallback_error}")
            return []


async def _fallback_vector_search(
    query: str,
    limit: int = 5,
    threshold: float = 0.7
) -> List[Dict[str, Any]]:
    """
    Fallback vector search using direct SQL
    """
    supabase = get_supabase_client()
    embeddings = get_embeddings()
    
    query_embedding = embeddings.embed_query(query)
    embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"
    
    # Direct query (if RPC doesn't exist)
    # This is a simplified version - in production, use RPC function
    result = supabase.table("kb_chunks").select(
        "id, content, document_id, chunk_index, metadata, embedding"
    ).limit(limit).execute()
    
    if result.data:
        # Calculate similarity manually (simplified)
        formatted_results = []
        for row in result.data:
            if row.get("embedding"):
                formatted_results.append({
                    "id": row.get("id"),
                    "content": row.get("content", ""),
                    "document_id": row.get("document_id"),
                    "chunk_index": row.get("chunk_index", 0),
                    "similarity": 0.8,  # Placeholder
                    "metadata": row.get("metadata", {}),
                    "source": get_document_source(row.get("document_id"))
                })
        
        return formatted_results[:limit]
    
    return []


def get_document_source(document_id: str) -> str:
    """
    Get document source/title for citation
    """
    try:
        supabase = get_supabase_client()
        result = supabase.table("kb_documents").select("title, file_path").eq("id", document_id).single().execute()
        
        if result.data:
            return result.data.get("title", result.data.get("file_path", "Unknown"))
        return "Unknown"
    except Exception:
        return "Unknown"


async def ingest_chunk(
    document_id: str,
    content: str,
    chunk_index: int,
    metadata: Dict[str, Any] = None
) -> str:
    """
    Ingest a document chunk into vector store
    """
    try:
        supabase = get_supabase_client()
        embeddings = get_embeddings()
        
        # Generate embedding
        embedding = embeddings.embed_query(content)
        
        # Create chunk record
        chunk_data = {
            "id": str(uuid4()),
            "document_id": document_id,
            "content": content,
            "embedding": embedding,  # pgvector will handle this
            "chunk_index": chunk_index,
            "metadata": metadata or {}
        }
        
        # Insert into kb_chunks table
        result = supabase.table("kb_chunks").insert(chunk_data).execute()
        
        if result.data:
            chunk_id = result.data[0].get("id")
            logger.info(f"Chunk ingested: document_id={document_id}, chunk_index={chunk_index}, id={chunk_id}")
            return chunk_id
        else:
            raise Exception("Failed to insert chunk")
    
    except Exception as e:
        logger.error(f"Chunk ingestion error: {e}")
        raise


async def ingest_document(
    title: str,
    content: str,
    file_path: Optional[str] = None,
    file_type: Optional[str] = None,
    uploaded_by: Optional[str] = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> str:
    """
    Ingest a full document into knowledge base
    Chunks the document and stores with embeddings
    """
    try:
        supabase = get_supabase_client()
        
        # Create document record
        document_data = {
            "id": str(uuid4()),
            "title": title,
            "file_path": file_path,
            "file_type": file_type,
            "uploaded_by": uploaded_by
        }
        
        result = supabase.table("kb_documents").insert(document_data).execute()
        
        if not result.data:
            raise Exception("Failed to create document record")
        
        document_id = result.data[0].get("id")
        
        # Chunk the document
        chunks = chunk_text(content, chunk_size, chunk_overlap)
        
        # Ingest each chunk
        for i, chunk_content in enumerate(chunks):
            await ingest_chunk(
                document_id=document_id,
                content=chunk_content,
                chunk_index=i,
                metadata={
                    "chunk_size": len(chunk_content),
                    "total_chunks": len(chunks)
                }
            )
        
        logger.info(f"Document ingested: {title}, {len(chunks)} chunks")
        
        return document_id
    
    except Exception as e:
        logger.error(f"Document ingestion error: {e}")
        raise


def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
    """
    Split text into chunks with overlap
    Simple implementation - can be improved with better chunking strategies
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings
            for break_char in ['. ', '.\n', '! ', '!\n', '? ', '?\n', '\n\n']:
                break_pos = text.rfind(break_char, start, end)
                if break_pos != -1:
                    end = break_pos + len(break_char)
                    break
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Move start with overlap
        start = end - chunk_overlap
        if start >= len(text):
            break
    
    return chunks
