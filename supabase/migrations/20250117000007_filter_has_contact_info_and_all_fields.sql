-- Filter leads by has_contact_info = true and return all fields
-- Migration: 20250117000007_filter_has_contact_info_and_all_fields.sql
-- Changes:
-- 1. Filter only leads where has_contact_info = true
-- 2. Return ALL fields from leads table (not just selected fields)

-- Function: ai_get_leads (Filter by has_contact_info = true, return all fields)
CREATE OR REPLACE FUNCTION ai_get_leads(
    p_user_id UUID,
    p_filters JSONB DEFAULT '{}',
    p_date_from DATE DEFAULT NULL,
    p_date_to DATE DEFAULT NULL,
    p_limit INTEGER DEFAULT NULL,
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
    -- Count total (for stats) - ONLY leads with has_contact_info = true
    SELECT COUNT(*) INTO v_total_count
    FROM leads
    WHERE is_archived = false
    AND has_contact_info = true  -- CRITICAL: Filter only leads with has_contact_info = true
    AND (
        -- Apply filters
        (p_filters->>'category' IS NULL OR category = p_filters->>'category')
        AND (p_filters->>'status' IS NULL OR status = p_filters->>'status')
        AND (p_filters->>'region' IS NULL OR region = p_filters->>'region')
        AND (p_filters->>'platform' IS NULL OR platform = p_filters->>'platform')
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
    
    -- Get leads with ALL fields from leads table
    -- Use subquery to avoid GROUP BY issues with jsonb_agg and ORDER BY
    -- Use to_jsonb(l.*) to automatically include ALL columns from leads table
    SELECT jsonb_agg(lead_data) INTO v_leads
    FROM (
        SELECT to_jsonb(l.*) as lead_data
        FROM leads l
        WHERE l.is_archived = false
        AND l.has_contact_info = true  -- CRITICAL: Only leads with contact info
        AND (
            -- Apply filters
            (p_filters->>'category' IS NULL OR l.category = p_filters->>'category')
            AND (p_filters->>'status' IS NULL OR l.status = p_filters->>'status')
            AND (p_filters->>'region' IS NULL OR l.region = p_filters->>'region')
            AND (p_filters->>'platform' IS NULL OR l.platform = p_filters->>'platform')
        )
        AND (
            -- Date filter - cast created_at_thai to date for comparison
            (p_date_from IS NULL AND p_date_to IS NULL)
            OR (
                l.created_at_thai IS NOT NULL 
                AND (l.created_at_thai::text::timestamp)::date BETWEEN 
                    COALESCE(p_date_from, '1900-01-01'::date) AND 
                    COALESCE(p_date_to, '2100-12-31'::date)
            )
        )
        ORDER BY l.created_at_thai::text::timestamp DESC NULLS LAST
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
        'with_contact', v_total_count  -- All returned leads have contact info
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
            'user_role', p_user_role,
            'filter_by_has_contact_info', true
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
