-- Add tel filter support to ai_get_leads
-- Migration: 20250213000002_ai_get_leads_add_tel_filter.sql
-- Enables filtering leads by phone number (e.g. "หาข้อมูลลีดเบอร์ 0886030830")
-- Matches normalized digits (ignores spaces/dashes in stored tel)

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
    v_lead_ids INTEGER[];
    v_creator_ids UUID[];
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
        AND (p_filters->>'tel' IS NULL OR REGEXP_REPLACE(COALESCE(tel,''), '[^0-9]', '', 'g') LIKE '%' || REGEXP_REPLACE(COALESCE(p_filters->>'tel',''), '[^0-9]', '', 'g') || '%')
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
            AND (p_filters->>'tel' IS NULL OR REGEXP_REPLACE(COALESCE(l.tel,''), '[^0-9]', '', 'g') LIKE '%' || REGEXP_REPLACE(COALESCE(p_filters->>'tel',''), '[^0-9]', '', 'g') || '%')
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
            -- No limit if date filter exists (like Edge Function logic)
            WHEN p_date_from IS NOT NULL OR p_date_to IS NOT NULL THEN 100000
            WHEN p_limit IS NULL THEN 100000  -- Very high limit (practically unlimited)
            WHEN p_limit > 0 THEN p_limit
            ELSE 100000  -- Very high limit (practically unlimited)
        END
    ) subquery;
    
    -- Enrich with creator_name and latest_productivity_log (rest of function unchanged)
    IF v_leads IS NOT NULL THEN
        WITH enriched_leads AS (
            SELECT 
                lead_data,
                COALESCE(
                    (
                        SELECT 
                            CASE 
                                WHEN u.first_name IS NOT NULL AND u.last_name IS NOT NULL 
                                THEN TRIM(u.first_name || ' ' || u.last_name)
                                WHEN u.first_name IS NOT NULL 
                                THEN u.first_name
                                WHEN u.last_name IS NOT NULL 
                                THEN u.last_name
                                ELSE 'ไม่ระบุ'
                            END
                        FROM users u
                        WHERE u.id = (lead_data->>'created_by')::UUID
                        LIMIT 1
                    ),
                    'ไม่ระบุ'
                ) as creator_name,
                (
                    SELECT to_jsonb(l.*)
                    FROM lead_productivity_logs l
                    WHERE l.lead_id = (lead_data->>'id')::INTEGER
                    ORDER BY l.created_at_thai::text::timestamp DESC NULLS LAST
                    LIMIT 1
                ) as latest_productivity_log
            FROM jsonb_array_elements(v_leads) AS lead_data
        )
        SELECT jsonb_agg(
            jsonb_set(
                jsonb_set(
                    enriched_leads.lead_data,
                    '{creator_name}',
                    to_jsonb(enriched_leads.creator_name)
                ),
                '{latest_productivity_log}',
                COALESCE(enriched_leads.latest_productivity_log, 'null'::jsonb)
            )
        ) INTO v_leads
        FROM enriched_leads;
    END IF;
    
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
            'filter_by_has_contact_info', true,
            'enriched_with', jsonb_build_object(
                'creator_name', true,
                'latest_productivity_log', true
            )
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
