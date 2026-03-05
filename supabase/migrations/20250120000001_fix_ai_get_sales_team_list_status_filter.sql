-- Fix ai_get_sales_team_list to support status='all' (NULL)
-- Migration: 20250120000001_fix_ai_get_sales_team_list_status_filter.sql
-- Issue: RPC function doesn't support status='all' because it uses exact match
-- Fix: Change WHERE clause to support NULL (get all statuses)

-- =============================================================================
-- Function: ai_get_sales_team_list (Fixed)
-- =============================================================================
-- Edge Function Reference: core-leads-sales-team-list
-- Logic:
-- 1. Simple query from sales_team_with_user_info
-- 2. Filter by status = p_status (if p_status IS NULL, get all statuses)
-- 3. Return: id, user_id, current_leads, status, name, email, phone, department, position
CREATE OR REPLACE FUNCTION ai_get_sales_team_list(
    p_user_id UUID,
    p_category TEXT DEFAULT NULL,
    p_status TEXT DEFAULT 'active',
    p_user_role TEXT DEFAULT 'staff'
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_result JSONB;
    v_sales_team JSONB;
BEGIN
    -- Get sales team from sales_team_with_user_info
    -- Filter by status (if p_status is NULL, get all statuses)
    -- Note: Edge Function hardcodes status='active', but RPC allows parameter
    -- If p_status = NULL, WHERE clause becomes: WHERE (NULL IS NULL OR st.status = NULL)
    -- Which evaluates to: WHERE TRUE (get all records)
    SELECT jsonb_agg(
        jsonb_build_object(
            'id', st.id,
            'user_id', st.user_id,
            'current_leads', st.current_leads,
            'status', st.status,
            'name', COALESCE(st.name, 'Unknown User'),
            'email', st.email,
            'phone', st.phone,
            'department', st.department,
            'position', st.position
        )
    ) INTO v_sales_team
    FROM sales_team_with_user_info st
    WHERE (p_status IS NULL OR st.status = p_status);
    
    -- If no results, return empty array
    IF v_sales_team IS NULL THEN
        v_sales_team := '[]'::jsonb;
    END IF;
    
    -- Build result
    RETURN jsonb_build_object(
        'success', true,
        'data', jsonb_build_object(
            'salesTeam', v_sales_team
        )
    );
EXCEPTION
    WHEN OTHERS THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', true,
            'message', SQLERRM
        );
END;
$$;

-- Grant execute permissions (already granted, but ensure it's there)
GRANT EXECUTE ON FUNCTION ai_get_sales_team_list(UUID, TEXT, TEXT, TEXT) TO authenticated;
