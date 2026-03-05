-- Phase 1: Enhance Existing RPC Functions
-- Migration: 20250118000001_phase1_enhance_rpc_functions.sql
-- Changes:
-- 1. Enhance ai_get_leads - Add creator_name and latest_productivity_log enrichment
-- 2. Enhance ai_get_lead_detail - Add all logs, timeline, relations (credit_evaluation, lead_products, quotation_documents)
-- 3. Enhance ai_get_appointments - Add sales member filter and lead info mapping
-- 4. Enhance ai_get_customer_info - Use customer_services_extended view and add filters
-- 5. Enhance ai_get_team_kpi - Add per-member metrics and conversion rate

-- =============================================================================
-- Function 1: ai_get_leads (Enhanced with creator_name and latest_productivity_log)
-- =============================================================================
-- Enhancements:
-- 1. Add creator_name enrichment (join with users table)
-- 2. Add latest_productivity_log enrichment (join with lead_productivity_logs)
-- 3. Add limit logic (no limit if date filter exists, else use limit)
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
            -- No limit if date filter exists (like Edge Function logic)
            WHEN p_date_from IS NOT NULL OR p_date_to IS NOT NULL THEN 100000
            WHEN p_limit IS NULL THEN 100000  -- Very high limit (practically unlimited)
            WHEN p_limit > 0 THEN p_limit
            ELSE 100000  -- Very high limit (practically unlimited)
        END
    ) subquery;
    
    -- Enrich with creator_name and latest_productivity_log
    -- Use simpler approach: build enriched leads directly with subqueries
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

-- =============================================================================
-- Function 2: ai_get_lead_detail (Enhanced with all logs, timeline, relations)
-- =============================================================================
-- Enhancements:
-- 1. Add all productivity logs query (not just latest)
-- 2. Add credit_evaluation relation
-- 3. Add lead_products relation
-- 4. Add quotation_documents relation
CREATE OR REPLACE FUNCTION ai_get_lead_detail(
    p_lead_id INTEGER,
    p_user_id UUID,
    p_include_related BOOLEAN DEFAULT true
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_result JSONB;
    v_user_role TEXT;
    v_lead JSONB;
    v_latest_log JSONB;
    v_all_logs JSONB;
    v_appointments JSONB;
    v_quotations JSONB;
    v_quotation_documents JSONB;
    v_log_ids INTEGER[];
BEGIN
    -- Get user role
    SELECT raw_user_meta_data->>'role' INTO v_user_role
    FROM auth.users
    WHERE id = p_user_id;
    
    IF v_user_role IS NULL THEN
        v_user_role := 'staff';
    END IF;
    
    -- Get lead
    SELECT to_jsonb(l.*) INTO v_lead
    FROM leads l
    WHERE l.id = p_lead_id
    AND l.is_archived = false;
    
    IF v_lead IS NULL THEN
        RETURN jsonb_build_object(
            'success', false,
            'found', false,
            'message', 'Lead not found'
        );
    END IF;
    
    -- Mask PII for non-admin
    IF v_user_role != 'admin' THEN
        v_lead := v_lead - 'tel' - 'line_id' - 'email';
    END IF;
    
    -- Get related data if requested
    IF p_include_related THEN
        -- Latest productivity log with relations (like Edge Function action=latest-log)
        SELECT to_jsonb(l.*) INTO v_latest_log
        FROM lead_productivity_logs l
        WHERE l.lead_id = p_lead_id
        ORDER BY l.created_at_thai::text::timestamp DESC NULLS LAST
        LIMIT 1;
        
        -- All productivity logs (not just latest)
        SELECT jsonb_agg(to_jsonb(l.*) ORDER BY l.created_at_thai::text::timestamp DESC NULLS LAST) INTO v_all_logs
        FROM lead_productivity_logs l
        WHERE l.lead_id = p_lead_id;
        
        -- Get log IDs for related queries
        SELECT ARRAY_AGG(id) INTO v_log_ids
        FROM lead_productivity_logs
        WHERE lead_id = p_lead_id;
        
        -- Appointments
        SELECT jsonb_agg(to_jsonb(a.*) ORDER BY a.date ASC NULLS LAST) INTO v_appointments
        FROM appointments a
        WHERE a.productivity_log_id = ANY(COALESCE(v_log_ids, ARRAY[]::INTEGER[]))
        ORDER BY a.date ASC NULLS LAST;
        
        -- Quotations
        SELECT jsonb_agg(to_jsonb(q.*) ORDER BY q.created_at DESC NULLS LAST) INTO v_quotations
        FROM quotations q
        WHERE q.productivity_log_id = ANY(COALESCE(v_log_ids, ARRAY[]::INTEGER[]))
        ORDER BY q.created_at DESC NULLS LAST;
        
        -- Quotation documents (if latest log exists)
        IF v_latest_log IS NOT NULL AND (v_latest_log->>'id') IS NOT NULL THEN
            SELECT jsonb_agg(to_jsonb(qd.*)) INTO v_quotation_documents
            FROM quotation_documents qd
            WHERE qd.productivity_log_id = (v_latest_log->>'id')::INTEGER;
        END IF;
        
        -- Enrich latest log with relations (like Edge Function)
        IF v_latest_log IS NOT NULL THEN
            -- Add appointments to latest log
            SELECT jsonb_set(
                v_latest_log,
                '{appointments}',
                COALESCE(
                    (SELECT jsonb_agg(to_jsonb(a.*)) FROM appointments a WHERE a.productivity_log_id = (v_latest_log->>'id')::INTEGER),
                    '[]'::jsonb
                )
            ) INTO v_latest_log;
            
            -- Add credit_evaluation to latest log (if exists)
            SELECT jsonb_set(
                v_latest_log,
                '{credit_evaluation}',
                COALESCE(
                    (SELECT jsonb_agg(to_jsonb(ce.*)) FROM credit_evaluation ce WHERE ce.productivity_log_id = (v_latest_log->>'id')::INTEGER),
                    '[]'::jsonb
                )
            ) INTO v_latest_log;
            
            -- Add lead_products with products relation to latest log (if exists)
            SELECT jsonb_set(
                v_latest_log,
                '{lead_products}',
                COALESCE(
                    (
                        SELECT jsonb_agg(
                            jsonb_build_object(
                                'id', lp.id,
                                'lead_id', lp.lead_id,
                                'productivity_log_id', lp.productivity_log_id,
                                'product_id', lp.product_id,
                                'quantity', lp.quantity,
                                'unit_price', lp.unit_price,
                                'total_price', lp.total_price,
                                'created_at', lp.created_at,
                                'product', to_jsonb(p.*)
                            )
                        )
                        FROM lead_products lp
                        LEFT JOIN products p ON lp.product_id = p.id
                        WHERE lp.productivity_log_id = (v_latest_log->>'id')::INTEGER
                    ),
                    '[]'::jsonb
                )
            ) INTO v_latest_log;
            
            -- Add quotations and quotation_documents to latest log
            SELECT jsonb_set(
                jsonb_set(
                    v_latest_log,
                    '{quotations}',
                    COALESCE(v_quotations, '[]'::jsonb)
                ),
                '{quotation_documents}',
                COALESCE(v_quotation_documents, '[]'::jsonb)
            ) INTO v_latest_log;
        END IF;
    END IF;
    
    -- Build result
    v_result := jsonb_build_object(
        'success', true,
        'found', true,
        'data', jsonb_build_object(
            'lead', v_lead,
            'latest_productivity_log', COALESCE(v_latest_log, 'null'::jsonb),
            'all_productivity_logs', COALESCE(v_all_logs, '[]'::jsonb),
            'appointments', COALESCE(v_appointments, '[]'::jsonb),
            'quotations', COALESCE(v_quotations, '[]'::jsonb),
            'quotation_documents', COALESCE(v_quotation_documents, '[]'::jsonb)
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

-- =============================================================================
-- Function 3: ai_get_appointments (Enhanced with sales member filter and lead info)
-- =============================================================================
-- Enhancements:
-- 1. Add sales member filtering (salesMemberId parameter)
-- 2. Add lead info mapping from productivity logs
-- 3. Add latest log per lead logic (group by lead_id)
CREATE OR REPLACE FUNCTION ai_get_appointments(
    p_user_id UUID,
    p_filters JSONB DEFAULT '{}',
    p_date_from DATE DEFAULT NULL,
    p_date_to DATE DEFAULT NULL,
    p_type TEXT DEFAULT 'all',  -- 'upcoming', 'past', 'all'
    p_sales_member_id INTEGER DEFAULT NULL  -- NEW: Filter by sales member
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_result JSONB;
    v_user_role TEXT;
    v_engineer JSONB;
    v_follow_up JSONB;
    v_payment JSONB;
    v_stats JSONB;
    v_log_ids INTEGER[];
    v_latest_logs JSONB;
BEGIN
    -- Get user role
    SELECT raw_user_meta_data->>'role' INTO v_user_role
    FROM auth.users
    WHERE id = p_user_id;
    
    IF v_user_role IS NULL THEN
        v_user_role := 'staff';
    END IF;
    
    -- If sales_member_id is provided, get latest logs per lead for that sales member
    -- This matches Edge Function logic: query logs by sale_id, group by lead_id, get latest
    IF p_sales_member_id IS NOT NULL THEN
        -- Get log IDs for this sales member (latest log per lead)
        -- Use subquery because DISTINCT ON cannot be used directly in ARRAY_AGG
        SELECT ARRAY_AGG(l.id)
        INTO v_log_ids
        FROM (
            SELECT DISTINCT ON (lead_id) id
            FROM lead_productivity_logs
            WHERE sale_id = p_sales_member_id
            ORDER BY lead_id, created_at DESC
        ) l;
        
        -- Get latest logs with lead info for enrichment
        SELECT jsonb_agg(
            jsonb_build_object(
                'id', l.id,
                'lead_id', l.lead_id,
                'lead', to_jsonb(leads.*)
            )
        ) INTO v_latest_logs
        FROM (
            SELECT DISTINCT ON (lead_id) *
            FROM lead_productivity_logs
            WHERE sale_id = p_sales_member_id
            ORDER BY lead_id, created_at DESC
        ) l
        LEFT JOIN leads ON leads.id = l.lead_id;
    END IF;
    
    -- Get engineer appointments
    SELECT jsonb_agg(
        CASE 
            WHEN p_sales_member_id IS NOT NULL THEN
                -- Enrich with lead info from latest logs
                jsonb_set(
                    jsonb_set(
                        to_jsonb(a.*),
                        '{lead}',
                        COALESCE(
                            (
                                SELECT (latest_log->>'lead')::jsonb
                                FROM jsonb_array_elements(COALESCE(v_latest_logs, '[]'::jsonb)) AS latest_log
                                WHERE (latest_log->>'id')::INTEGER = a.productivity_log_id
                                LIMIT 1
                            ),
                            jsonb_build_object('id', 0, 'full_name', 'Unknown')
                        )
                    ),
                    '{source}',
                    '"appointment"'::jsonb
                )
            ELSE
                to_jsonb(a.*)
        END
        ORDER BY (CASE WHEN p_sales_member_id IS NOT NULL THEN (to_jsonb(a.*)->>'date')::DATE ELSE a.date END) ASC NULLS LAST
    ) INTO v_engineer
    FROM appointments a
    JOIN lead_productivity_logs l ON a.productivity_log_id = l.id
    WHERE a.appointment_type = 'engineer'
    AND (
        (p_sales_member_id IS NULL OR a.productivity_log_id = ANY(COALESCE(v_log_ids, ARRAY[]::INTEGER[])))
        AND (p_filters->>'appointment_type' IS NULL OR a.appointment_type = p_filters->>'appointment_type')
        AND (p_filters->>'status' IS NULL OR a.status = p_filters->>'status')
        AND (p_filters->>'sales_id' IS NULL OR l.sale_id = (p_filters->>'sales_id')::integer)
    )
    AND (
        (p_date_from IS NULL AND p_date_to IS NULL)
        OR (DATE(a.date) BETWEEN COALESCE(p_date_from, '1900-01-01') AND COALESCE(p_date_to, '2100-12-31'))
    )
    AND (
        p_type = 'all'
        OR (p_type = 'upcoming' AND a.date >= CURRENT_DATE)
        OR (p_type = 'past' AND a.date < CURRENT_DATE)
    )
    AND a.date IS NOT NULL;
    
    -- Get follow-up appointments
    SELECT jsonb_agg(
        CASE 
            WHEN p_sales_member_id IS NOT NULL THEN
                -- Enrich with lead info from latest logs
                jsonb_set(
                    jsonb_set(
                        jsonb_set(
                            jsonb_set(
                                to_jsonb(a.*),
                                '{type}',
                                '"follow-up"'::jsonb
                            ),
                            '{details}',
                            COALESCE(to_jsonb(a.note), 'null'::jsonb)
                        ),
                        '{lead}',
                        COALESCE(
                            (
                                SELECT (latest_log->>'lead')::jsonb
                                FROM jsonb_array_elements(COALESCE(v_latest_logs, '[]'::jsonb)) AS latest_log
                                WHERE (latest_log->>'id')::INTEGER = a.productivity_log_id
                                LIMIT 1
                            ),
                            jsonb_build_object('id', 0, 'full_name', 'Unknown')
                        )
                    ),
                    '{source}',
                    '"appointment"'::jsonb
                )
            ELSE
                to_jsonb(a.*)
        END
        ORDER BY (CASE WHEN p_sales_member_id IS NOT NULL THEN (to_jsonb(a.*)->>'date')::DATE ELSE a.date END) ASC NULLS LAST
    ) INTO v_follow_up
    FROM appointments a
    JOIN lead_productivity_logs l ON a.productivity_log_id = l.id
    WHERE a.appointment_type = 'follow-up'
    AND (
        (p_sales_member_id IS NULL OR a.productivity_log_id = ANY(COALESCE(v_log_ids, ARRAY[]::INTEGER[])))
        AND (p_filters->>'appointment_type' IS NULL OR a.appointment_type = p_filters->>'appointment_type')
        AND (p_filters->>'status' IS NULL OR a.status = p_filters->>'status')
        AND (p_filters->>'sales_id' IS NULL OR l.sale_id = (p_filters->>'sales_id')::integer)
    )
    AND (
        (p_date_from IS NULL AND p_date_to IS NULL)
        OR (DATE(a.date) BETWEEN COALESCE(p_date_from, '1900-01-01') AND COALESCE(p_date_to, '2100-12-31'))
    )
    AND (
        p_type = 'all'
        OR (p_type = 'upcoming' AND a.date >= CURRENT_DATE)
        OR (p_type = 'past' AND a.date < CURRENT_DATE)
    )
    AND a.date IS NOT NULL;
    
    -- Get payment appointments (from quotations)
    SELECT jsonb_agg(
        CASE 
            WHEN p_sales_member_id IS NOT NULL THEN
                -- Enrich with lead info from latest logs
                jsonb_set(
                    jsonb_set(
                        jsonb_set(
                            jsonb_set(
                                jsonb_build_object(
                                    'id', q.id,
                                    'date', q.estimate_payment_date,
                                    'total_amount', q.total_amount,
                                    'payment_method', q.payment_method,
                                    'type', 'payment'
                                ),
                                '{lead}',
                                COALESCE(
                                    (
                                        SELECT (latest_log->>'lead')::jsonb
                                        FROM jsonb_array_elements(COALESCE(v_latest_logs, '[]'::jsonb)) AS latest_log
                                        WHERE (latest_log->>'id')::INTEGER = q.productivity_log_id
                                        LIMIT 1
                                    ),
                                    jsonb_build_object('id', 0, 'full_name', 'Unknown')
                                )
                            ),
                            '{source}',
                            '"quotation"'::jsonb
                        ),
                        '{date}',
                        to_jsonb(q.estimate_payment_date)
                    ),
                    '{estimate_payment_date}',
                    to_jsonb(q.estimate_payment_date)
                )
            ELSE
                to_jsonb(q.*)
        END
        ORDER BY q.estimate_payment_date ASC NULLS LAST
    ) INTO v_payment
    FROM quotations q
    JOIN lead_productivity_logs l ON q.productivity_log_id = l.id
    WHERE q.estimate_payment_date IS NOT NULL
    AND (
        (p_sales_member_id IS NULL OR q.productivity_log_id = ANY(COALESCE(v_log_ids, ARRAY[]::INTEGER[])))
        AND (p_filters->>'sales_id' IS NULL OR l.sale_id = (p_filters->>'sales_id')::integer)
    )
    AND (
        (p_date_from IS NULL AND p_date_to IS NULL)
        OR (DATE(q.estimate_payment_date) BETWEEN COALESCE(p_date_from, '1900-01-01') AND COALESCE(p_date_to, '2100-12-31'))
    )
    AND (
        p_type = 'all'
        OR (p_type = 'upcoming' AND q.estimate_payment_date >= CURRENT_DATE)
        OR (p_type = 'past' AND q.estimate_payment_date < CURRENT_DATE)
    );
    
    -- Build stats
    v_stats := jsonb_build_object(
        'total', 
        jsonb_array_length(COALESCE(v_engineer, '[]'::jsonb)) +
        jsonb_array_length(COALESCE(v_follow_up, '[]'::jsonb)) +
        jsonb_array_length(COALESCE(v_payment, '[]'::jsonb)),
        'engineer', jsonb_array_length(COALESCE(v_engineer, '[]'::jsonb)),
        'follow_up', jsonb_array_length(COALESCE(v_follow_up, '[]'::jsonb)),
        'payment', jsonb_array_length(COALESCE(v_payment, '[]'::jsonb))
    );
    
    -- Build result (match Edge Function structure: { followUp, engineer, payment })
    v_result := jsonb_build_object(
        'success', true,
        'data', jsonb_build_object(
            'followUp', COALESCE(v_follow_up, '[]'::jsonb),
            'engineer', COALESCE(v_engineer, '[]'::jsonb),
            'payment', COALESCE(v_payment, '[]'::jsonb),
            'stats', v_stats
        ),
        'meta', jsonb_build_object(
            'filters_applied', p_filters,
            'date_from', p_date_from,
            'date_to', p_date_to,
            'type', p_type,
            'sales_member_id', p_sales_member_id
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

-- =============================================================================
-- Function 4: ai_get_customer_info (Enhanced with filters and list query)
-- =============================================================================
-- Enhancements:
-- 1. Use customer_services_extended view instead of table
-- 2. Add all filters (search, province, sale, installerName, serviceVisits)
-- 3. Support both single (by id) and list queries
CREATE OR REPLACE FUNCTION ai_get_customer_info(
    p_user_id UUID,
    p_customer_name TEXT DEFAULT NULL,
    p_filters JSONB DEFAULT '{}',
    p_customer_id INTEGER DEFAULT NULL  -- NEW: Support single query by id
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_result JSONB;
    v_user_role TEXT;
    v_customer JSONB;
    v_customers JSONB;
    v_query TEXT;
BEGIN
    -- Get user role
    SELECT raw_user_meta_data->>'role' INTO v_user_role
    FROM auth.users
    WHERE id = p_user_id;
    
    IF v_user_role IS NULL THEN
        v_user_role := 'staff';
    END IF;
    
    -- Single customer query by id
    IF p_customer_id IS NOT NULL THEN
        -- Use customer_services_extended view (like Edge Function)
        SELECT to_jsonb(cs.*) INTO v_customer
        FROM customer_services_extended cs
        WHERE cs.id = p_customer_id;
        
        IF v_customer IS NULL THEN
            RETURN jsonb_build_object(
                'success', false,
                'found', false,
                'message', 'Customer service not found'
            );
        END IF;
        
        -- Mask PII for non-admin
        IF v_user_role != 'admin' THEN
            v_customer := v_customer - 'tel' - 'line_id' - 'email';
        END IF;
        
        RETURN jsonb_build_object(
            'success', true,
            'found', true,
            'data', v_customer,
            'isDetail', true
        );
    END IF;
    
    -- List query with filters (like Edge Function)
    -- Use customer_services_extended view
    SELECT jsonb_agg(to_jsonb(cs.*) ORDER BY cs.id ASC)
    INTO v_customers
    FROM customer_services_extended cs
    WHERE (
        -- Search filter (ilike on customer_group, tel, installer_name)
        (p_filters->>'search' IS NULL OR 
         cs.customer_group ILIKE '%' || (p_filters->>'search') || '%' OR
         cs.tel ILIKE '%' || (p_filters->>'search') || '%' OR
         cs.installer_name ILIKE '%' || (p_filters->>'search') || '%')
        -- Customer name filter (if provided)
        AND (p_customer_name IS NULL OR 
             cs.customer_group ILIKE '%' || p_customer_name || '%' OR
             cs.installer_name ILIKE '%' || p_customer_name || '%')
        -- Province filter
        AND (p_filters->>'province' IS NULL OR p_filters->>'province' = 'all' OR cs.province = p_filters->>'province')
        -- Sale filter
        AND (p_filters->>'sale' IS NULL OR p_filters->>'sale' = 'all' OR cs.sale = p_filters->>'sale')
        -- Installer name filter
        AND (p_filters->>'installerName' IS NULL OR p_filters->>'installerName' = 'all' OR cs.installer_name = p_filters->>'installerName')
        -- Service visit filters (boolean)
        AND (p_filters->>'serviceVisit1' IS NULL OR cs.service_visit_1 = (p_filters->>'serviceVisit1')::boolean)
        AND (p_filters->>'serviceVisit2' IS NULL OR cs.service_visit_2 = (p_filters->>'serviceVisit2')::boolean)
        AND (p_filters->>'serviceVisit3' IS NULL OR cs.service_visit_3 = (p_filters->>'serviceVisit3')::boolean)
        AND (p_filters->>'serviceVisit4' IS NULL OR cs.service_visit_4 = (p_filters->>'serviceVisit4')::boolean)
        AND (p_filters->>'serviceVisit5' IS NULL OR cs.service_visit_5 = (p_filters->>'serviceVisit5')::boolean)
    );
    
    -- Mask PII for non-admin (if list)
    IF v_user_role != 'admin' AND v_customers IS NOT NULL THEN
        SELECT jsonb_agg(
            customer_data - 'tel' - 'line_id' - 'email'
        ) INTO v_customers
        FROM jsonb_array_elements(v_customers) AS customer_data;
    END IF;
    
    -- Build result
    v_result := jsonb_build_object(
        'success', true,
        'found', CASE WHEN v_customers IS NOT NULL AND jsonb_array_length(v_customers) > 0 THEN true ELSE false END,
        'data', COALESCE(v_customers, '[]'::jsonb),
        'meta', jsonb_build_object(
            'filters_applied', p_filters,
            'total_services', jsonb_array_length(COALESCE(v_customers, '[]'::jsonb)),
            'isDetail', false
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

-- =============================================================================
-- Function 5: ai_get_team_kpi (Enhanced with per-member metrics)
-- =============================================================================
-- Enhancements:
-- 1. Return sales team list with per-member metrics
-- 2. Add conversion rate calculation
-- 3. Add contact rate calculation
CREATE OR REPLACE FUNCTION ai_get_team_kpi(
    p_user_id UUID,
    p_team_id INTEGER DEFAULT NULL,
    p_category TEXT DEFAULT NULL,
    p_date_from DATE DEFAULT NULL,
    p_date_to DATE DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_result JSONB;
    v_user_role TEXT;
    v_sales_team JSONB;
    v_sales_team_temp JSONB;  -- Temporary variable to hold original sales team
    v_total_leads INTEGER;
    v_active_leads INTEGER;
    v_sales_owner_ids INTEGER[];
    v_all_leads JSONB;
    v_productivity_logs JSONB;
    v_current_leads JSONB;  -- For filtered leads (status IN ('กำลังติดตาม', 'ปิดการขาย'))
    v_stats JSONB;  -- For statistics
BEGIN
    -- Get user role
    SELECT raw_user_meta_data->>'role' INTO v_user_role
    FROM auth.users
    WHERE id = p_user_id;
    
    IF v_user_role IS NULL THEN
        v_user_role := 'staff';
    END IF;
    
    -- Only admin and manager can view team KPI
    IF v_user_role NOT IN ('admin', 'manager') THEN
        RETURN jsonb_build_object(
            'error', true,
            'message', 'Permission denied. Only admin and manager can view team KPI.'
        );
    END IF;
    
    -- Get sales team list
    SELECT jsonb_agg(to_jsonb(st.*)) INTO v_sales_team
    FROM sales_team_with_user_info st
    WHERE (p_team_id IS NULL OR st.id = p_team_id)
    AND st.status = 'active';
    
    IF v_sales_team IS NULL THEN
        v_sales_team := '[]'::jsonb;
    END IF;
    
    -- Store original sales team in temp variable (for later use in FROM clause)
    v_sales_team_temp := v_sales_team;
    
    -- Extract sales owner IDs
    SELECT ARRAY_AGG((member->>'id')::INTEGER) INTO v_sales_owner_ids
    FROM jsonb_array_elements(v_sales_team) AS member;
    
    -- Get all leads for conversion rate calculation (including all statuses)
    -- รวมทั้ง sale_owner_id และ post_sales_owner_id (like Edge Function)
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
    -- Use v_current_leads variable (not v_stats which is for statistics)
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
    
    -- Get productivity logs for closed leads (for conversion rate)
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
    
    -- Calculate per-member metrics (like Edge Function)
    -- Use CTE to build member with metrics to avoid deeply nested jsonb_set
    WITH member_metrics AS (
        SELECT 
            member,
            -- Calculate currentLeads
            COALESCE((
                SELECT COUNT(*)
                FROM jsonb_array_elements(COALESCE(v_current_leads, '[]'::jsonb)) AS lead
                WHERE (lead->>'sale_owner_id')::INTEGER = (member->>'id')::INTEGER
                   OR (lead->>'post_sales_owner_id')::INTEGER = (member->>'id')::INTEGER
            ), 0) AS current_leads,
            -- Calculate totalLeads
            COALESCE((
                SELECT COUNT(*)
                FROM jsonb_array_elements(COALESCE(v_all_leads, '[]'::jsonb)) AS lead
                WHERE (lead->>'sale_owner_id')::INTEGER = (member->>'id')::INTEGER
                   OR (lead->>'post_sales_owner_id')::INTEGER = (member->>'id')::INTEGER
            ), 0) AS total_leads,
            -- Calculate closedLeads
            COALESCE((
                SELECT COUNT(*)
                FROM jsonb_array_elements(COALESCE(v_productivity_logs, '[]'::jsonb)) AS log
                WHERE (log->>'sale_id')::INTEGER = (member->>'id')::INTEGER
            ), 0) AS closed_leads,
            -- Calculate leadsWithContact
            COALESCE((
                SELECT COUNT(*)
                FROM jsonb_array_elements(COALESCE(v_all_leads, '[]'::jsonb)) AS lead
                WHERE ((lead->>'sale_owner_id')::INTEGER = (member->>'id')::INTEGER
                   OR (lead->>'post_sales_owner_id')::INTEGER = (member->>'id')::INTEGER)
                AND (lead->>'tel') IS NOT NULL 
                     AND (lead->>'tel') != '' 
                     AND (lead->>'tel') != 'ไม่ระบุ'
            ), 0) AS leads_with_contact,
            -- Calculate conversionRate
            CASE 
                WHEN COALESCE((
                    SELECT COUNT(*)
                    FROM jsonb_array_elements(COALESCE(v_all_leads, '[]'::jsonb)) AS lead
                    WHERE (lead->>'sale_owner_id')::INTEGER = (member->>'id')::INTEGER
                       OR (lead->>'post_sales_owner_id')::INTEGER = (member->>'id')::INTEGER
                ), 0) > 0 THEN
                    ROUND(
                        (
                            COALESCE((
                                SELECT COUNT(*)
                                FROM jsonb_array_elements(COALESCE(v_productivity_logs, '[]'::jsonb)) AS log
                                WHERE (log->>'sale_id')::INTEGER = (member->>'id')::INTEGER
                            ), 0)::NUMERIC /
                            COALESCE((
                                SELECT COUNT(*)
                                FROM jsonb_array_elements(COALESCE(v_all_leads, '[]'::jsonb)) AS lead
                                WHERE (lead->>'sale_owner_id')::INTEGER = (member->>'id')::INTEGER
                                   OR (lead->>'post_sales_owner_id')::INTEGER = (member->>'id')::INTEGER
                            ), 1)::NUMERIC
                        ) * 100,
                        2
                    )
                ELSE 0
            END AS conversion_rate,
            -- Calculate contactRate
            CASE 
                WHEN COALESCE((
                    SELECT COUNT(*)
                    FROM jsonb_array_elements(COALESCE(v_all_leads, '[]'::jsonb)) AS lead
                    WHERE (lead->>'sale_owner_id')::INTEGER = (member->>'id')::INTEGER
                       OR (lead->>'post_sales_owner_id')::INTEGER = (member->>'id')::INTEGER
                ), 0) > 0 THEN
                    ROUND(
                        (
                            COALESCE((
                                SELECT COUNT(*)
                                FROM jsonb_array_elements(COALESCE(v_all_leads, '[]'::jsonb)) AS lead
                                WHERE ((lead->>'sale_owner_id')::INTEGER = (member->>'id')::INTEGER
                                   OR (lead->>'post_sales_owner_id')::INTEGER = (member->>'id')::INTEGER)
                                AND (lead->>'tel') IS NOT NULL 
                                     AND (lead->>'tel') != '' 
                                     AND (lead->>'tel') != 'ไม่ระบุ'
                            ), 0)::NUMERIC /
                            COALESCE((
                                SELECT COUNT(*)
                                FROM jsonb_array_elements(COALESCE(v_all_leads, '[]'::jsonb)) AS lead
                                WHERE (lead->>'sale_owner_id')::INTEGER = (member->>'id')::INTEGER
                                   OR (lead->>'post_sales_owner_id')::INTEGER = (member->>'id')::INTEGER
                            ), 1)::NUMERIC
                        ) * 100,
                        2
                    )
                ELSE 0
            END AS contact_rate
        FROM jsonb_array_elements(v_sales_team_temp) AS member
    )
    SELECT jsonb_agg(
        jsonb_set(
            jsonb_set(
                jsonb_set(
                    jsonb_set(
                        jsonb_set(
                            jsonb_set(
                                member_metrics.member,
                                '{currentLeads}',
                                to_jsonb(member_metrics.current_leads)
                            ),
                            '{totalLeads}',
                            to_jsonb(member_metrics.total_leads)
                        ),
                        '{closedLeads}',
                        to_jsonb(member_metrics.closed_leads)
                    ),
                    '{leadsWithContact}',
                    to_jsonb(member_metrics.leads_with_contact)
                ),
                '{conversionRate}',
                to_jsonb(member_metrics.conversion_rate)
            ),
            '{contactRate}',
            to_jsonb(member_metrics.contact_rate)
        )
    ) INTO v_sales_team
    FROM member_metrics;
    
    -- Count total leads
    SELECT COUNT(*) INTO v_total_leads
    FROM leads
    WHERE is_archived = false;
    
    -- Count active leads (status not 'closed' or 'cancelled')
    SELECT COUNT(*) INTO v_active_leads
    FROM leads
    WHERE is_archived = false
    AND status NOT IN ('closed', 'cancelled', 'completed');
    
    -- Calculate overall statistics
    v_stats := jsonb_build_object(
        'totalMembers', jsonb_array_length(v_sales_team),
        'activeMembers', (
            SELECT COUNT(*)
            FROM jsonb_array_elements(v_sales_team) AS member
            WHERE (member->>'status') = 'active'
        ),
        'totalLeads', v_total_leads,
        'activeLeads', v_active_leads,
        'totalClosedLeads', jsonb_array_length(COALESCE(v_productivity_logs, '[]'::jsonb)),
        'averageLeadsPerMember', 
            CASE 
                WHEN jsonb_array_length(v_sales_team) > 0 THEN
                    ROUND(v_total_leads::NUMERIC / jsonb_array_length(v_sales_team)::NUMERIC, 2)
                ELSE 0
            END,
        'overallConversionRate',
            CASE 
                WHEN jsonb_array_length(COALESCE(v_all_leads, '[]'::jsonb)) > 0 THEN
                    ROUND(
                        (jsonb_array_length(COALESCE(v_productivity_logs, '[]'::jsonb))::NUMERIC / 
                         jsonb_array_length(COALESCE(v_all_leads, '[]'::jsonb))::NUMERIC) * 100,
                        2
                    )
                ELSE 0
            END
    );
    
    -- Build result
    v_result := jsonb_build_object(
        'success', true,
        'data', v_sales_team,
        'stats', v_stats,
        'meta', jsonb_build_object(
            'team_id', p_team_id,
            'category', p_category,
            'date_from', p_date_from,
            'date_to', p_date_to,
            'user_role', v_user_role
        )
    );
    
    RETURN v_result;
EXCEPTION
    WHEN OTHERS THEN
        RETURN jsonb_build_object(
            'error', true,
            'message', SQLERRM
        );
END;
$$;

-- Grant execute permissions
-- Note: Function signatures must match exactly (including parameter order)
GRANT EXECUTE ON FUNCTION ai_get_leads(UUID, JSONB, DATE, DATE, INTEGER, TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION ai_get_lead_detail(INTEGER, UUID, BOOLEAN) TO authenticated;
GRANT EXECUTE ON FUNCTION ai_get_appointments(UUID, JSONB, DATE, DATE, TEXT, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION ai_get_customer_info(UUID, TEXT, JSONB, INTEGER) TO authenticated;  -- Fixed: p_user_id (UUID) comes first, not p_customer_name (TEXT)
GRANT EXECUTE ON FUNCTION ai_get_team_kpi(UUID, INTEGER, TEXT, DATE, DATE) TO authenticated;
