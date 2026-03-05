-- Fix ai_get_leads date filter SQL error
-- Migration: 20250117000004_fix_ai_get_leads_date_filter.sql
-- Fixes: "column must appear in GROUP BY clause" error when using DATE() function

-- Function: ai_get_leads (Fixed version - simplified date filter)
CREATE OR REPLACE FUNCTION ai_get_leads(
    p_user_id UUID,
    p_filters JSONB DEFAULT '{}',
    p_date_from DATE DEFAULT NULL,
    p_date_to DATE DEFAULT NULL,
    p_limit INTEGER DEFAULT 100,
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
    -- Use provided role (passed from backend JWT token)
    -- No need to query auth.users since we can't access it via REST API
    
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
    
    -- Get leads (mask PII based on role)
    -- Use subquery to avoid aggregation issues
    SELECT jsonb_agg(lead_data) INTO v_leads
    FROM (
        SELECT 
            jsonb_build_object(
                'id', id,
                'full_name', full_name,
                'display_name', display_name,
                'tel', CASE WHEN p_user_role = 'admin' THEN tel ELSE NULL END,
                'line_id', CASE WHEN p_user_role = 'admin' THEN line_id ELSE NULL END,
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
        LIMIT CASE WHEN p_date_from IS NULL AND p_date_to IS NULL THEN p_limit ELSE 10000 END
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
