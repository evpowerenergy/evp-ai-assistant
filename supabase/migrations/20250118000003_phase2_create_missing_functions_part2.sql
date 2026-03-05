-- Phase 2: Create Missing RPC Functions (Part 2)
-- Migration: 20250118000003_phase2_create_missing_functions_part2.sql
-- Changes:
-- 4. Create ai_get_sales_team_data - Get sales team with metrics and data (leads, quotations)
-- 5. Create ai_validate_phone - Validate phone number for duplicates
-- 6. Create ai_get_lead_management - Get Lead Management page data

-- =============================================================================
-- Function 4: ai_get_sales_team_data
-- =============================================================================
-- Edge Function Reference: core-sales-team-sales-team-data
-- Logic:
-- 1. Get sales team from sales_team_with_user_info
-- 2. Get leads (sale_owner_id OR post_sales_owner_id)
-- 3. Filter by has_contact_info = true
-- 4. Filter by platforms (EV + Partner platforms)
-- 5. Filter by date range (if provided)
-- 6. Get productivity logs where status = 'ปิดการขายแล้ว'
-- 7. Get quotations from closed logs
-- 8. Calculate metrics per member (deals_closed, pipeline_value, conversion_rate, total_leads)
-- 9. Return leads and quotations data
CREATE OR REPLACE FUNCTION ai_get_sales_team_data(
    p_user_id UUID,
    p_date_from DATE DEFAULT NULL,
    p_date_to DATE DEFAULT NULL,
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
    v_sales_team_temp JSONB;
    v_all_leads JSONB;
    v_productivity_logs JSONB;
    v_quotations JSONB;
    v_sales_owner_ids INTEGER[];
    v_closed_log_ids INTEGER[];
BEGIN
    -- Get sales team from sales_team_with_user_info
    SELECT jsonb_agg(to_jsonb(st.*)) INTO v_sales_team
    FROM sales_team_with_user_info st
    WHERE st.status = 'active';
    
    IF v_sales_team IS NULL THEN
        v_sales_team := '[]'::jsonb;
    END IF;
    
    -- Store original sales team in temp variable
    v_sales_team_temp := v_sales_team;
    
    -- Extract sales owner IDs
    SELECT ARRAY_AGG((member->>'id')::INTEGER) INTO v_sales_owner_ids
    FROM jsonb_array_elements(v_sales_team) AS member;
    
    -- Define EV + Partner platforms (like Edge Function)
    -- EV platforms
    -- Partner platforms: 'Huawei', 'ATMOCE', 'Solar Edge', 'Sigenergy'
    -- Note: PostgreSQL array must use exact string match
    -- Use IN clause with array of platforms
    
    -- Get leads data for all sales members with date filter
    -- Filter by has_contact_info = true
    -- Filter by EV + Partner platforms
    -- Include both sale_owner_id and post_sales_owner_id
    SELECT jsonb_agg(to_jsonb(l.*)) INTO v_all_leads
    FROM leads l
    WHERE l.is_archived = false
    AND l.has_contact_info = true
    AND (
        l.sale_owner_id = ANY(COALESCE(v_sales_owner_ids, ARRAY[]::INTEGER[]))
        OR l.post_sales_owner_id = ANY(COALESCE(v_sales_owner_ids, ARRAY[]::INTEGER[]))
    )
    AND l.platform IN (
        'Facebook', 'Line', 'Website', 'TikTok', 'IG', 'YouTube', 
        'Shopee', 'Lazada', 'แนะนำ', 'Outbound', 'โทร', 'ลูกค้าเก่า service ครบ',
        'Huawei', 'ATMOCE', 'Solar Edge', 'Sigenergy'
    )
    AND (
        (p_date_from IS NULL AND p_date_to IS NULL)
        OR (
            l.created_at_thai IS NOT NULL 
            AND (l.created_at_thai::text::timestamp)::date BETWEEN 
                COALESCE(p_date_from, '1900-01-01'::date) AND 
                COALESCE(p_date_to, '2100-12-31'::date)
        )
    );
    
    -- Get productivity logs where status = 'ปิดการขายแล้ว'
    SELECT jsonb_agg(to_jsonb(l.*)) INTO v_productivity_logs
    FROM lead_productivity_logs l
    WHERE l.status = 'ปิดการขายแล้ว'
    AND l.sale_id = ANY(COALESCE(v_sales_owner_ids, ARRAY[]::INTEGER[]))
    AND (
        (p_date_from IS NULL AND p_date_to IS NULL)
        OR (
            l.created_at_thai IS NOT NULL 
            AND (l.created_at_thai::text::timestamp)::date BETWEEN 
                COALESCE(p_date_from, '1900-01-01'::date) AND 
                COALESCE(p_date_to, '2100-12-31'::date)
        )
    );
    
    -- Extract closed log IDs for quotations query
    IF v_productivity_logs IS NOT NULL THEN
        SELECT ARRAY_AGG((log->>'id')::INTEGER) INTO v_closed_log_ids
        FROM jsonb_array_elements(v_productivity_logs) AS log;
    END IF;
    
    -- Get quotations from closed logs
    IF v_closed_log_ids IS NOT NULL AND array_length(v_closed_log_ids, 1) > 0 THEN
        SELECT jsonb_agg(to_jsonb(q.*)) INTO v_quotations
        FROM quotations q
        WHERE q.productivity_log_id = ANY(v_closed_log_ids);
    END IF;
    
    -- Calculate metrics per member using CTEs
    WITH member_metrics AS (
        SELECT 
            (member->>'id')::INTEGER as member_id,
            -- Count total leads (from v_all_leads)
            (
                SELECT COUNT(*)
                FROM jsonb_array_elements(COALESCE(v_all_leads, '[]'::jsonb)) AS lead
                WHERE 
                    ((lead->>'sale_owner_id')::INTEGER = (member->>'id')::INTEGER)
                    OR ((lead->>'post_sales_owner_id')::INTEGER = (member->>'id')::INTEGER)
            ) as total_leads,
            -- Get member closed logs
            (
                SELECT jsonb_agg(log)
                FROM jsonb_array_elements(COALESCE(v_productivity_logs, '[]'::jsonb)) AS log
                WHERE (log->>'sale_id')::INTEGER = (member->>'id')::INTEGER
            ) as member_closed_logs,
            member
        FROM jsonb_array_elements(v_sales_team_temp) AS member
    ),
    member_quotations AS (
        SELECT 
            member_id,
            total_leads,
            member_closed_logs,
            member,
            -- Extract log IDs from member_closed_logs
            (
                SELECT ARRAY_AGG((log->>'id')::INTEGER)
                FROM jsonb_array_elements(COALESCE(member_closed_logs, '[]'::jsonb)) AS log
            ) as member_log_ids
        FROM member_metrics
    )
    SELECT jsonb_agg(
        jsonb_set(
            jsonb_set(
                jsonb_set(
                    jsonb_set(
                        member,
                        '{deals_closed}',
                        to_jsonb(
                            CASE 
                                WHEN member_log_ids IS NOT NULL AND array_length(member_log_ids, 1) > 0 THEN
                                    (
                                        SELECT COUNT(*)
                                        FROM jsonb_array_elements(COALESCE(v_quotations, '[]'::jsonb)) AS q
                                        WHERE (q->>'productivity_log_id')::INTEGER = ANY(member_log_ids)
                                    )
                                ELSE 0
                            END
                        )
                    ),
                    '{pipeline_value}',
                    to_jsonb(
                        CASE 
                            WHEN member_log_ids IS NOT NULL AND array_length(member_log_ids, 1) > 0 THEN
                                COALESCE((
                                    SELECT SUM(COALESCE((q->>'total_amount')::NUMERIC, 0))
                                    FROM jsonb_array_elements(COALESCE(v_quotations, '[]'::jsonb)) AS q
                                    WHERE (q->>'productivity_log_id')::INTEGER = ANY(member_log_ids)
                                ), 0)
                            ELSE 0
                        END
                    )
                ),
                '{conversion_rate}',
                to_jsonb(
                    CASE 
                        WHEN total_leads > 0 THEN
                            ROUND((
                                CASE 
                                    WHEN member_log_ids IS NOT NULL AND array_length(member_log_ids, 1) > 0 THEN
                                        (
                                            SELECT COUNT(*)::NUMERIC
                                            FROM jsonb_array_elements(COALESCE(v_quotations, '[]'::jsonb)) AS q
                                            WHERE (q->>'productivity_log_id')::INTEGER = ANY(member_log_ids)
                                        )
                                    ELSE 0
                                END
                                / total_leads::NUMERIC
                            ) * 100, 2)
                        ELSE 0
                    END
                )
            ),
            '{total_leads}',
            to_jsonb(total_leads)
        )
    ) INTO v_sales_team
    FROM member_quotations;
    
    -- Build result
    RETURN jsonb_build_object(
        'success', true,
        'data', jsonb_build_object(
            'salesTeam', COALESCE(v_sales_team, '[]'::jsonb),
            'leads', COALESCE(v_all_leads, '[]'::jsonb),
            'quotations', COALESCE(v_quotations, '[]'::jsonb)
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

-- =============================================================================
-- Function 5: ai_validate_phone
-- =============================================================================
-- Edge Function Reference: core-leads-phone-validation
-- Logic:
-- 1. Normalize phone number (remove all non-digits)
-- 2. Fetch all leads with phone numbers (not null, not empty, not whitespace-only)
-- 3. Normalize existing phone numbers
-- 4. Compare normalized input with normalized existing phones
-- 5. Exclude current lead if exclude_lead_id is provided
-- 6. Return { isDuplicate: boolean, phone: string, existingLead?: Lead }
CREATE OR REPLACE FUNCTION ai_validate_phone(
    p_phone TEXT,
    p_exclude_lead_id INTEGER DEFAULT NULL,
    p_user_id UUID DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_result JSONB;
    v_normalized_input TEXT;
    v_existing_lead JSONB;
    v_is_duplicate BOOLEAN := false;
    v_normalized_existing TEXT;
    v_lead_record RECORD;
BEGIN
    -- Validate input
    IF p_phone IS NULL OR TRIM(p_phone) = '' THEN
        RETURN jsonb_build_object(
            'isDuplicate', false,
            'phone', COALESCE(p_phone, ''),
            'error', 'Phone number is required'
        );
    END IF;
    
    -- Normalize input phone number (remove all non-digits)
    v_normalized_input := REGEXP_REPLACE(TRIM(p_phone), '[^0-9]', '', 'g');
    
    -- If normalized input is empty, return false (no duplicate)
    IF v_normalized_input = '' THEN
        RETURN jsonb_build_object(
            'isDuplicate', false,
            'phone', p_phone
        );
    END IF;
    
    -- Fetch all leads with phone numbers (not null, not empty, not whitespace-only)
    -- Filter out null, empty strings, and whitespace-only values
    FOR v_lead_record IN
        SELECT id, tel, full_name, display_name
        FROM leads
        WHERE tel IS NOT NULL
        AND tel != ''
        AND TRIM(tel) != ''
        AND (p_exclude_lead_id IS NULL OR id != p_exclude_lead_id)
    LOOP
        -- Normalize existing phone number (remove all non-digits)
        v_normalized_existing := REGEXP_REPLACE(TRIM(v_lead_record.tel), '[^0-9]', '', 'g');
        
        -- Compare normalized phone numbers
        IF v_normalized_existing = v_normalized_input THEN
            -- Found duplicate
            v_is_duplicate := true;
            v_existing_lead := jsonb_build_object(
                'id', v_lead_record.id,
                'tel', v_lead_record.tel,
                'full_name', v_lead_record.full_name,
                'display_name', v_lead_record.display_name
            );
            EXIT; -- Exit loop on first match
        END IF;
    END LOOP;
    
    -- Build result
    IF v_is_duplicate THEN
        RETURN jsonb_build_object(
            'isDuplicate', true,
            'phone', p_phone,
            'existingLead', v_existing_lead
        );
    ELSE
        RETURN jsonb_build_object(
            'isDuplicate', false,
            'phone', p_phone
        );
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RETURN jsonb_build_object(
            'isDuplicate', false,
            'phone', COALESCE(p_phone, ''),
            'error', SQLERRM
        );
END;
$$;

-- =============================================================================
-- Function 6: ai_get_lead_management
-- =============================================================================
-- Edge Function Reference: core-leads-lead-management
-- Logic:
-- 1. Parallel queries:
--    - Get user data (if include_user_data = true)
--    - Get sales team data (if include_sales_team = true)
--    - Get leads data (if include_leads = true)
-- 2. Leads query:
--    - Filter by category
--    - Filter by has_contact_info = true
--    - Date range filtering (no limit if date filter exists)
--    - Enrich with creator_name
-- 3. Calculate statistics (totalLeads, assignedLeads, unassignedLeads, assignmentRate, leadsWithContact, contactRate)
-- 4. Return: { leads, salesTeam, user, salesMember, stats }
CREATE OR REPLACE FUNCTION ai_get_lead_management(
    p_user_id UUID,
    p_category TEXT DEFAULT 'Package',
    p_include_user_data BOOLEAN DEFAULT true,
    p_include_sales_team BOOLEAN DEFAULT true,
    p_include_leads BOOLEAN DEFAULT true,
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
    v_user_data JSONB;
    v_sales_team JSONB;
    v_sales_member JSONB;
    v_leads JSONB;
    v_stats JSONB;
    v_user_internal_id UUID;
BEGIN
    -- Initialize result structure
    v_result := jsonb_build_object(
        'leads', '[]'::jsonb,
        'salesTeam', '[]'::jsonb,
        'user', NULL,
        'salesMember', NULL,
        'stats', '{}'::jsonb
    );
    
    -- 1. Get user data (if include_user_data = true)
    IF p_include_user_data THEN
        SELECT to_jsonb(u.*) INTO v_user_data
        FROM users u
        WHERE u.auth_user_id = p_user_id
        LIMIT 1;
        
        IF v_user_data IS NOT NULL THEN
            v_result := jsonb_set(v_result, '{user}', v_user_data);
            -- Extract internal user_id for sales member lookup
            v_user_internal_id := (v_user_data->>'id')::UUID;
        END IF;
    END IF;
    
    -- 2. Get sales team data (if include_sales_team = true)
    IF p_include_sales_team THEN
        SELECT jsonb_agg(to_jsonb(st.*)) INTO v_sales_team
        FROM sales_team_with_user_info st
        WHERE st.status = 'active';
        
        IF v_sales_team IS NULL THEN
            v_sales_team := '[]'::jsonb;
        END IF;
        
        v_result := jsonb_set(v_result, '{salesTeam}', v_sales_team);
        
        -- Get sales member for current user (if user data was fetched)
        IF v_user_internal_id IS NOT NULL THEN
            SELECT to_jsonb(st.*) INTO v_sales_member
            FROM sales_team_with_user_info st
            WHERE st.user_id = v_user_internal_id
            LIMIT 1;
            
            IF v_sales_member IS NOT NULL THEN
                v_result := jsonb_set(v_result, '{salesMember}', v_sales_member);
            END IF;
        END IF;
    END IF;
    
    -- 3. Get leads data (if include_leads = true)
    IF p_include_leads THEN
        -- Get leads with ALL fields from leads table
        -- Filter by category and has_contact_info = true
        -- Date range filtering (no limit if date filter exists)
        SELECT jsonb_agg(lead_data) INTO v_leads
        FROM (
            SELECT to_jsonb(l.*) as lead_data
            FROM leads l
            WHERE l.is_archived = false
            AND l.has_contact_info = true
            AND l.category = p_category
            AND (
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
        
        -- Enrich with creator_name
        IF v_leads IS NOT NULL THEN
            WITH enriched_leads AS (
                SELECT 
                    lead_data,
                    -- Enrich with creator_name
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
                    ) as creator_name
                FROM jsonb_array_elements(v_leads) AS lead_data
            )
            SELECT jsonb_agg(
                jsonb_set(
                    enriched_leads.lead_data,
                    '{creator_name}',
                    to_jsonb(enriched_leads.creator_name)
                )
                ORDER BY (enriched_leads.lead_data->>'created_at_thai')::text::timestamp DESC
            ) INTO v_leads
            FROM enriched_leads;
        END IF;
        
        IF v_leads IS NULL THEN
            v_leads := '[]'::jsonb;
        END IF;
        
        v_result := jsonb_set(v_result, '{leads}', v_leads);
        
        -- Calculate statistics
        WITH stats_data AS (
            SELECT 
                COUNT(*) as total_leads,
                COUNT(*) FILTER (WHERE (lead->>'sale_owner_id') IS NOT NULL) as assigned_leads,
                COUNT(*) FILTER (WHERE (lead->>'sale_owner_id') IS NULL) as unassigned_leads,
                COUNT(*) FILTER (WHERE (lead->>'tel') IS NOT NULL AND (lead->>'tel') != '' AND (lead->>'tel') != 'ไม่ระบุ') as leads_with_contact
            FROM jsonb_array_elements(v_leads) AS lead
        )
        SELECT jsonb_build_object(
            'totalLeads', total_leads,
            'assignedLeads', assigned_leads,
            'unassignedLeads', unassigned_leads,
            'assignmentRate', 
                CASE 
                    WHEN total_leads > 0 THEN ROUND((assigned_leads::NUMERIC / total_leads::NUMERIC) * 100, 2)
                    ELSE 0
                END,
            'leadsWithContact', leads_with_contact,
            'contactRate',
                CASE 
                    WHEN total_leads > 0 THEN ROUND((leads_with_contact::NUMERIC / total_leads::NUMERIC) * 100, 2)
                    ELSE 0
                END
        ) INTO v_stats
        FROM stats_data;
        
        v_result := jsonb_set(v_result, '{stats}', v_stats);
    END IF;
    
    -- Build final result
    RETURN jsonb_build_object(
        'success', true,
        'data', v_result
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

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION ai_get_sales_team_data(UUID, DATE, DATE, TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION ai_validate_phone(TEXT, INTEGER, UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION ai_get_lead_management(UUID, TEXT, BOOLEAN, BOOLEAN, BOOLEAN, DATE, DATE, INTEGER, TEXT) TO authenticated;
