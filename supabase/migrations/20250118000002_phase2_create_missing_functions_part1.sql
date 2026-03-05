-- Phase 2: Create Missing RPC Functions (Part 1)
-- Migration: 20250118000002_phase2_create_missing_functions_part1.sql
-- Changes:
-- 1. Create ai_get_my_leads - Get leads assigned to current user (sale_owner_id or post_sales_owner_id)
-- 2. Create ai_get_sales_team - Get sales team with metrics (currentLeads, totalLeads, closedLeads, conversionRate)
-- 3. Create ai_get_sales_team_list - Get simple sales team list for dropdown

-- =============================================================================
-- Function 1: ai_get_my_leads
-- =============================================================================
-- Edge Function Reference: core-my-leads-my-leads
-- Logic:
-- 1. Get user data from users (by auth_user_id)
-- 2. Get sales member from sales_team_with_user_info (by user_id)
-- 3. Query leads where sale_owner_id = salesMember.id AND has_contact_info = true AND category = p_category
-- 4. Query leads where post_sales_owner_id = salesMember.id AND has_contact_info = true AND category = p_category
-- 5. Combine and distinct leads
-- 6. Enrich with creator_name
-- 7. Enrich with latest_productivity_log
-- 8. Calculate statistics (totalLeads, leadsWithContact, byStatus, byPlatform)
CREATE OR REPLACE FUNCTION ai_get_my_leads(
    p_user_id UUID,
    p_category TEXT DEFAULT 'Package',
    p_filters JSONB DEFAULT '{}',
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
    v_user_data JSONB;
    v_sales_member JSONB;
    v_leads JSONB;
    v_stats JSONB;
    v_user_internal_id UUID;
    v_sales_member_id INTEGER;
BEGIN
    -- Get user data (by auth_user_id)
    SELECT to_jsonb(u.*) INTO v_user_data
    FROM users u
    WHERE u.auth_user_id = p_user_id
    LIMIT 1;
    
    -- If user not found, return empty result
    IF v_user_data IS NULL THEN
        RETURN jsonb_build_object(
            'success', true,
            'data', jsonb_build_object(
                'leads', '[]'::jsonb,
                'user', NULL,
                'salesMember', NULL
            ),
            'stats', jsonb_build_object(
                'totalLeads', 0,
                'leadsWithContact', 0,
                'byStatus', '{}'::jsonb,
                'byPlatform', '{}'::jsonb
            )
        );
    END IF;
    
    -- Extract internal user_id
    v_user_internal_id := (v_user_data->>'id')::UUID;
    
    -- Get sales member data
    SELECT to_jsonb(st.*) INTO v_sales_member
    FROM sales_team_with_user_info st
    WHERE st.user_id = v_user_internal_id
    LIMIT 1;
    
    -- If sales member not found, still return user data but no leads
    IF v_sales_member IS NULL THEN
        -- Add name and role to sales member object
        v_sales_member := jsonb_build_object(
            'id', NULL,
            'user_id', v_user_internal_id,
            'status', NULL,
            'current_leads', 0,
            'name', COALESCE(
                TRIM((v_user_data->>'first_name') || ' ' || (v_user_data->>'last_name')),
                'Unknown User'
            ),
            'role', v_user_data->>'role'
        );
        
        RETURN jsonb_build_object(
            'success', true,
            'data', jsonb_build_object(
                'leads', '[]'::jsonb,
                'user', v_user_data,
                'salesMember', v_sales_member
            ),
            'stats', jsonb_build_object(
                'totalLeads', 0,
                'leadsWithContact', 0,
                'byStatus', '{}'::jsonb,
                'byPlatform', '{}'::jsonb
            )
        );
    END IF;
    
    -- Add name and role to sales member object
    v_sales_member := jsonb_set(
        jsonb_set(
            v_sales_member,
            '{name}',
            to_jsonb(COALESCE(
                TRIM((v_user_data->>'first_name') || ' ' || (v_user_data->>'last_name')),
                'Unknown User'
            ))
        ),
        '{role}',
        to_jsonb(v_user_data->>'role')
    );
    
    -- Extract sales member id
    v_sales_member_id := (v_sales_member->>'id')::INTEGER;
    
    -- Get leads for this sales member (both sale_owner_id and post_sales_owner_id)
    -- Use DISTINCT ON to avoid duplicates when a lead has both sale_owner_id and post_sales_owner_id pointing to same member
    WITH owner_leads AS (
        SELECT to_jsonb(l.*) as lead_data
        FROM leads l
        WHERE l.is_archived = false
        AND l.has_contact_info = true
        AND l.category = p_category
        AND l.sale_owner_id = v_sales_member_id
        AND (
            (p_date_from IS NULL AND p_date_to IS NULL)
            OR (
                l.created_at_thai IS NOT NULL 
                AND (l.created_at_thai::text::timestamp)::date BETWEEN 
                    COALESCE(p_date_from, '1900-01-01'::date) AND 
                    COALESCE(p_date_to, '2100-12-31'::date)
            )
        )
    ),
    post_sales_leads AS (
        SELECT to_jsonb(l.*) as lead_data
        FROM leads l
        WHERE l.is_archived = false
        AND l.has_contact_info = true
        AND l.category = p_category
        AND l.post_sales_owner_id = v_sales_member_id
        AND (
            (p_date_from IS NULL AND p_date_to IS NULL)
            OR (
                l.created_at_thai IS NOT NULL 
                AND (l.created_at_thai::text::timestamp)::date BETWEEN 
                    COALESCE(p_date_from, '1900-01-01'::date) AND 
                    COALESCE(p_date_to, '2100-12-31'::date)
            )
        )
    ),
    combined_leads AS (
        SELECT DISTINCT ON ((lead_data->>'id')::INTEGER) lead_data
        FROM (
            SELECT lead_data FROM owner_leads
            UNION ALL
            SELECT lead_data FROM post_sales_leads
        ) combined
        ORDER BY (lead_data->>'id')::INTEGER, (lead_data->>'updated_at_thai')::text::timestamp DESC
    )
    SELECT jsonb_agg(lead_data ORDER BY (lead_data->>'updated_at_thai')::text::timestamp DESC) INTO v_leads
    FROM combined_leads;
    
    -- Enrich with creator_name and latest_productivity_log
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
                ) as creator_name,
                -- Enrich with latest_productivity_log
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
            ORDER BY (enriched_leads.lead_data->>'updated_at_thai')::text::timestamp DESC
        ) INTO v_leads
        FROM enriched_leads;
    END IF;
    
    -- Calculate statistics
    IF v_leads IS NULL THEN
        v_leads := '[]'::jsonb;
    END IF;
    
    WITH stats_data AS (
        SELECT 
            COUNT(*) as total_leads,
            COUNT(*) FILTER (WHERE (lead->>'tel') IS NOT NULL AND (lead->>'tel') != '' AND (lead->>'tel') != 'ไม่ระบุ') as leads_with_contact,
            COUNT(*) FILTER (WHERE (lead->>'status') = 'กำลังติดตาม') as status_following,
            COUNT(*) FILTER (WHERE (lead->>'status') = 'ปิดการขาย') as status_closed,
            COUNT(*) FILTER (WHERE (lead->>'operation_status') = 'ปิดการขายแล้ว') as op_status_closed,
            COUNT(*) FILTER (WHERE (lead->>'operation_status') = 'ปิดการขายไม่สำเร็จ') as op_status_failed,
            COUNT(*) FILTER (WHERE (lead->>'platform') = 'Facebook') as platform_facebook,
            COUNT(*) FILTER (WHERE (lead->>'platform') = 'Line') as platform_line,
            COUNT(*) FILTER (WHERE (lead->>'platform') = 'Website') as platform_website,
            COUNT(*) FILTER (WHERE (lead->>'platform') = 'Phone') as platform_phone
        FROM jsonb_array_elements(v_leads) AS lead
    )
    SELECT jsonb_build_object(
        'totalLeads', total_leads,
        'leadsWithContact', leads_with_contact,
        'byStatus', jsonb_build_object(
            'กำลังติดตาม', status_following,
            'ปิดการขาย', status_closed,
            'ปิดการขายแล้ว', op_status_closed,
            'ปิดการขายไม่สำเร็จ', op_status_failed
        ),
        'byPlatform', jsonb_build_object(
            'Facebook', platform_facebook,
            'Line', platform_line,
            'Website', platform_website,
            'Phone', platform_phone
        )
    ) INTO v_stats
    FROM stats_data;
    
    -- Build result
    RETURN jsonb_build_object(
        'success', true,
        'data', jsonb_build_object(
            'leads', COALESCE(v_leads, '[]'::jsonb),
            'user', v_user_data,
            'salesMember', v_sales_member
        ),
        'stats', v_stats
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
-- Function 2: ai_get_sales_team
-- =============================================================================
-- Edge Function Reference: core-sales-team-sales-team
-- Logic:
-- 1. Get sales team from sales_team_with_user_info
-- 2. Get all leads (sale_owner_id OR post_sales_owner_id)
-- 3. Filter by has_contact_info = true
-- 4. Filter by status IN ('กำลังติดตาม', 'ปิดการขาย') for currentLeads
-- 5. Get all leads for conversion rate calculation
-- 6. Get productivity logs where status = 'ปิดการขายแล้ว'
-- 7. Calculate metrics per member (currentLeads, totalLeads, closedLeads, conversionRate, leadsWithContact, contactRate)
-- 8. Calculate overall statistics
CREATE OR REPLACE FUNCTION ai_get_sales_team(
    p_user_id UUID,
    p_category TEXT DEFAULT NULL,
    p_filters JSONB DEFAULT '{}',
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
    v_current_leads JSONB;
    v_productivity_logs JSONB;
    v_sales_owner_ids INTEGER[];
    v_stats JSONB;
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
    
    -- Get all leads for conversion rate calculation (including all statuses)
    -- รวมทั้ง sale_owner_id และ post_sales_owner_id
    SELECT jsonb_agg(to_jsonb(l.*)) INTO v_all_leads
    FROM leads l
    WHERE l.is_archived = false
    AND l.has_contact_info = true
    AND (
        l.sale_owner_id = ANY(COALESCE(v_sales_owner_ids, ARRAY[]::INTEGER[]))
        OR l.post_sales_owner_id = ANY(COALESCE(v_sales_owner_ids, ARRAY[]::INTEGER[]))
    )
    AND (p_category IS NULL OR l.category = p_category)
    AND (
        (p_date_from IS NULL AND p_date_to IS NULL)
        OR (
            l.created_at_thai IS NOT NULL 
            AND (l.created_at_thai::text::timestamp)::date BETWEEN 
                COALESCE(p_date_from, '1900-01-01'::date) AND 
                COALESCE(p_date_to, '2100-12-31'::date)
        )
    );
    
    -- Get leads for current_leads (filtered by status)
    SELECT jsonb_agg(to_jsonb(l.*)) INTO v_current_leads
    FROM leads l
    WHERE l.is_archived = false
    AND l.has_contact_info = true
    AND l.status IN ('กำลังติดตาม', 'ปิดการขาย')
    AND (
        l.sale_owner_id = ANY(COALESCE(v_sales_owner_ids, ARRAY[]::INTEGER[]))
        OR l.post_sales_owner_id = ANY(COALESCE(v_sales_owner_ids, ARRAY[]::INTEGER[]))
    )
    AND (p_category IS NULL OR l.category = p_category);
    
    -- Get productivity logs where status = 'ปิดการขายแล้ว'
    -- ใช้ sale_id จาก productivity logs แทน sale_owner_id จาก leads
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
    
    -- Calculate metrics per member using CTEs
    WITH member_metrics AS (
        SELECT 
            (member->>'id')::INTEGER as member_id,
            -- Count current leads (from v_current_leads)
            (
                SELECT COUNT(*)
                FROM jsonb_array_elements(COALESCE(v_current_leads, '[]'::jsonb)) AS lead
                WHERE 
                    ((lead->>'sale_owner_id')::INTEGER = (member->>'id')::INTEGER)
                    OR ((lead->>'post_sales_owner_id')::INTEGER = (member->>'id')::INTEGER)
            ) as current_leads,
            -- Count total leads (from v_all_leads)
            (
                SELECT COUNT(*)
                FROM jsonb_array_elements(COALESCE(v_all_leads, '[]'::jsonb)) AS lead
                WHERE 
                    ((lead->>'sale_owner_id')::INTEGER = (member->>'id')::INTEGER)
                    OR ((lead->>'post_sales_owner_id')::INTEGER = (member->>'id')::INTEGER)
            ) as total_leads,
            -- Count closed leads (from productivity logs using sale_id)
            (
                SELECT COUNT(*)
                FROM jsonb_array_elements(COALESCE(v_productivity_logs, '[]'::jsonb)) AS log
                WHERE (log->>'sale_id')::INTEGER = (member->>'id')::INTEGER
            ) as closed_leads,
            -- Count leads with contact
            (
                SELECT COUNT(*)
                FROM jsonb_array_elements(COALESCE(v_all_leads, '[]'::jsonb)) AS lead
                WHERE 
                    (
                        ((lead->>'sale_owner_id')::INTEGER = (member->>'id')::INTEGER)
                        OR ((lead->>'post_sales_owner_id')::INTEGER = (member->>'id')::INTEGER)
                    )
                    AND (lead->>'tel') IS NOT NULL 
                    AND (lead->>'tel') != '' 
                    AND (lead->>'tel') != 'ไม่ระบุ'
            ) as leads_with_contact,
            member
        FROM jsonb_array_elements(v_sales_team_temp) AS member
    )
    SELECT jsonb_agg(
        jsonb_set(
            jsonb_set(
                jsonb_set(
                    jsonb_set(
                        jsonb_set(
                            jsonb_set(
                                member,
                                '{currentLeads}',
                                to_jsonb(current_leads)
                            ),
                            '{totalLeads}',
                            to_jsonb(total_leads)
                        ),
                        '{closedLeads}',
                        to_jsonb(closed_leads)
                    ),
                    '{conversionRate}',
                    to_jsonb(
                        CASE 
                            WHEN total_leads > 0 THEN ROUND((closed_leads::NUMERIC / total_leads::NUMERIC) * 100, 2)
                            ELSE 0
                        END
                    )
                ),
                '{leadsWithContact}',
                to_jsonb(leads_with_contact)
            ),
            '{contactRate}',
            to_jsonb(
                CASE 
                    WHEN total_leads > 0 THEN ROUND((leads_with_contact::NUMERIC / total_leads::NUMERIC) * 100, 2)
                    ELSE 0
                END
            )
        )
    ) INTO v_sales_team
    FROM member_metrics;
    
    -- Calculate overall statistics
    WITH overall_stats AS (
        SELECT 
            (SELECT COUNT(*) FROM jsonb_array_elements(COALESCE(v_sales_team_temp, '[]'::jsonb))) as total_members,
            (SELECT COUNT(*) FROM jsonb_array_elements(COALESCE(v_sales_team_temp, '[]'::jsonb)) WHERE (member->>'status') = 'active') as active_members,
            (SELECT COUNT(*) FROM jsonb_array_elements(COALESCE(v_current_leads, '[]'::jsonb))) as total_leads,
            (SELECT COUNT(*) FROM jsonb_array_elements(COALESCE(v_productivity_logs, '[]'::jsonb))) as total_closed_leads,
            (SELECT COUNT(*) FROM jsonb_array_elements(COALESCE(v_all_leads, '[]'::jsonb))) as total_all_leads
    )
    SELECT jsonb_build_object(
        'totalMembers', total_members,
        'activeMembers', active_members,
        'totalLeads', total_leads,
        'totalClosedLeads', total_closed_leads,
        'averageLeadsPerMember', 
            CASE 
                WHEN total_members > 0 THEN ROUND((total_leads::NUMERIC / total_members::NUMERIC), 2)
                ELSE 0
            END,
        'overallConversionRate',
            CASE 
                WHEN total_all_leads > 0 THEN ROUND((total_closed_leads::NUMERIC / total_all_leads::NUMERIC) * 100, 2)
                ELSE 0
            END
    ) INTO v_stats
    FROM overall_stats;
    
    -- Build result
    RETURN jsonb_build_object(
        'success', true,
        'data', COALESCE(v_sales_team, '[]'::jsonb),
        'stats', v_stats
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
-- Function 3: ai_get_sales_team_list
-- =============================================================================
-- Edge Function Reference: core-leads-sales-team-list
-- Logic:
-- 1. Simple query from sales_team_with_user_info
-- 2. Filter by status = p_status
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

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION ai_get_my_leads(UUID, TEXT, JSONB, DATE, DATE, TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION ai_get_sales_team(UUID, TEXT, JSONB, DATE, DATE, TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION ai_get_sales_team_list(UUID, TEXT, TEXT, TEXT) TO authenticated;
