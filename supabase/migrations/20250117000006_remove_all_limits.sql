-- Remove all limits from ai_get_leads function
-- Migration: 20250117000006_remove_all_limits.sql
-- Allows unlimited results based on user query

-- Function: ai_get_leads (No limit version)
CREATE OR REPLACE FUNCTION ai_get_leads(
    p_user_id UUID,
    p_filters JSONB DEFAULT '{}',
    p_date_from DATE DEFAULT NULL,
    p_date_to DATE DEFAULT NULL,
    p_limit INTEGER DEFAULT NULL,  -- NULL = no limit, get all results
    p_user_role TEXT DEFAULT 'staff'
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_result JSONB;
    v_leads JSONB;
    v_total_count INTEGER;
    v_stats JSONB;
BEGIN
    -- Count total (for stats)
    SELECT COUNT(*) INTO v_total_count
    FROM leads
    WHERE is_archived = false
    AND (
        -- Apply filters
        (p_filters->>'category' IS NULL OR category = p_filters->>'category')
        AND (p_filters->>'status' IS NULL OR status = p_filters->>'status')
        AND (p_filters->>'region' IS NULL OR region = p_filters->>'region')
        AND (p_filters->>'platform' IS NULL OR platform = p_filters->>'platform')
        AND (
            p_filters->>'has_contact_info' IS NULL 
            OR (p_filters->>'has_contact_info')::boolean = (tel IS NOT NULL OR line_id IS NOT NULL)
        )
    )
    AND (
        -- Date filter - cast created_at_thai to date for comparison
        (p_date_from IS NULL AND p_date_to IS NULL)
        OR (
            created_at_thai IS NOT NULL 
            AND (created_at_thai::text::timestamp)::date BETWEEN 
                COALESCE(p_date_from, '1900-01-01'::date) AND 
                COALESCE(p_date_to, '2100-12-31'::date)
        )
    );
    
    -- Get leads (show all data - no PII masking, no limit)
    -- Use subquery to avoid aggregation issues
    SELECT jsonb_agg(lead_data) INTO v_leads
    FROM (
        SELECT 
            jsonb_build_object(
                'id', id,
                'full_name', full_name,
                'display_name', display_name,
                'tel', tel,  -- Show all data - no masking
                'line_id', line_id,  -- Show all data - no masking
                'status', status,
                'category', category,
                'region', region,
                'platform', platform,
                'operation_status', operation_status,
                'created_at_thai', created_at_thai,
                'updated_at_thai', updated_at_thai
            ) as lead_data
        FROM leads
        WHERE is_archived = false
        AND (
            -- Apply filters
            (p_filters->>'category' IS NULL OR category = p_filters->>'category')
            AND (p_filters->>'status' IS NULL OR status = p_filters->>'status')
            AND (p_filters->>'region' IS NULL OR region = p_filters->>'region')
            AND (p_filters->>'platform' IS NULL OR platform = p_filters->>'platform')
            AND (
                p_filters->>'has_contact_info' IS NULL 
                OR (p_filters->>'has_contact_info')::boolean = (tel IS NOT NULL OR line_id IS NOT NULL)
            )
        )
        AND (
            -- Date filter - cast created_at_thai to date for comparison
            (p_date_from IS NULL AND p_date_to IS NULL)
            OR (
                created_at_thai IS NOT NULL 
                AND (created_at_thai::text::timestamp)::date BETWEEN 
                    COALESCE(p_date_from, '1900-01-01'::date) AND 
                    COALESCE(p_date_to, '2100-12-31'::date)
            )
        )
        ORDER BY created_at_thai::text::timestamp DESC NULLS LAST
        -- No limit by default - return all matching results
        -- If p_limit is provided and > 0, use it; otherwise return all (use very high limit)
        LIMIT CASE 
            WHEN p_limit IS NULL THEN 100000  -- Very high limit (practically unlimited)
            WHEN p_limit > 0 THEN p_limit
            ELSE 100000  -- Very high limit (practically unlimited)
        END
    ) subquery;
    
    -- Build stats
    v_stats := jsonb_build_object(
        'total', v_total_count,
        'returned', jsonb_array_length(COALESCE(v_leads, '[]'::jsonb)),
        'with_contact', (
            SELECT COUNT(*)
            FROM leads
            WHERE is_archived = false
            AND (tel IS NOT NULL OR line_id IS NOT NULL)
            AND (
                (p_date_from IS NULL AND p_date_to IS NULL)
                OR (
                    created_at_thai IS NOT NULL 
                    AND (created_at_thai::text::timestamp)::date BETWEEN 
                        COALESCE(p_date_from, '1900-01-01'::date) AND 
                        COALESCE(p_date_to, '2100-12-31'::date)
                )
            )
        )
    );
    
    -- Build result
    v_result := jsonb_build_object(
        'success', true,
        'data', jsonb_build_object(
            'leads', COALESCE(v_leads, '[]'::jsonb),
            'stats', v_stats
        ),
        'meta', jsonb_build_object(
            'filters_applied', p_filters,
            'date_from', p_date_from,
            'date_to', p_date_to,
            'limit', p_limit,
            'total_returned', jsonb_array_length(COALESCE(v_leads, '[]'::jsonb)),
            'user_role', p_user_role
        )
    );
    
    RETURN v_result;
EXCEPTION
    WHEN OTHERS THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', true,
            'message', SQLERRM
        );
END;
$$;

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION ai_get_leads(UUID, JSONB, DATE, DATE, INTEGER, TEXT) TO authenticated;
