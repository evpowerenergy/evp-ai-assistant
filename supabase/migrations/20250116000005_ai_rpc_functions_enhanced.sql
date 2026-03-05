-- Enhanced AI RPC Functions (ตาม Pattern จาก Edge Functions)
-- Migration: 20250116000005_ai_rpc_functions_enhanced.sql
-- Support: Date filtering, Multiple filters, Related data, Stats

-- =============================================================================
-- Function 1: ai_get_leads (Enhanced)
-- =============================================================================
-- Enhanced version of ai_get_lead_status
-- Support: filters (JSONB), date range, limit, related data
CREATE OR REPLACE FUNCTION ai_get_leads(
    p_user_id UUID,
    p_filters JSONB DEFAULT '{}',
    p_date_from DATE DEFAULT NULL,
    p_date_to DATE DEFAULT NULL,
    p_limit INTEGER DEFAULT 100
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_result JSONB;
    v_user_role TEXT;
    v_query TEXT;
    v_leads JSONB;
    v_total_count INTEGER;
    v_stats JSONB;
BEGIN
    -- Get user role
    SELECT raw_user_meta_data->>'role' INTO v_user_role
    FROM auth.users
    WHERE id = p_user_id;
    
    IF v_user_role IS NULL THEN
        v_user_role := 'staff';
    END IF;
    
    -- Build query based on filters
    -- Note: This is a simplified version - in production, use dynamic SQL or query builder
    
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
        -- Date filter
        (p_date_from IS NULL AND p_date_to IS NULL)
        OR (DATE(created_at_thai::timestamp) BETWEEN COALESCE(p_date_from, '1900-01-01') AND COALESCE(p_date_to, '2100-12-31'))
    );
    
    -- Get leads
    SELECT jsonb_agg(
        jsonb_build_object(
            'id', id,
            'full_name', full_name,
            'display_name', display_name,
            'tel', CASE WHEN v_user_role = 'admin' THEN tel ELSE NULL END,  -- Mask PII
            'line_id', CASE WHEN v_user_role = 'admin' THEN line_id ELSE NULL END,  -- Mask PII
            'status', status,
            'category', category,
            'region', region,
            'platform', platform,
            'operation_status', operation_status,
            'created_at_thai', created_at_thai,
            'updated_at_thai', updated_at_thai
        )
    ) INTO v_leads
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
        -- Date filter
        (p_date_from IS NULL AND p_date_to IS NULL)
        OR (DATE(created_at_thai::timestamp) BETWEEN COALESCE(p_date_from, '1900-01-01') AND COALESCE(p_date_to, '2100-12-31'))
    )
    ORDER BY created_at_thai DESC
    LIMIT CASE WHEN p_date_from IS NULL AND p_date_to IS NULL THEN p_limit ELSE 10000 END;
    
    -- Build stats
    v_stats := jsonb_build_object(
        'total', v_total_count,
        'returned', jsonb_array_length(COALESCE(v_leads, '[]'::jsonb)),
        'with_contact', (
            SELECT COUNT(*)
            FROM leads
            WHERE is_archived = false
            AND (tel IS NOT NULL OR line_id IS NOT NULL)
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
            'total_returned', jsonb_array_length(COALESCE(v_leads, '[]'::jsonb))
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
-- Function 2: ai_get_lead_detail (Enhanced)
-- =============================================================================
-- Get lead detail with related data (productivity logs, appointments, quotations)
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
    v_appointments JSONB;
    v_quotations JSONB;
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
        -- Latest productivity log
        SELECT to_jsonb(l.*) INTO v_latest_log
        FROM lead_productivity_logs l
        WHERE l.lead_id = p_lead_id
        ORDER BY l.created_at_thai DESC
        LIMIT 1;
        
        -- Appointments
        SELECT jsonb_agg(to_jsonb(a.*)) INTO v_appointments
        FROM appointments a
        WHERE a.productivity_log_id IN (
            SELECT id FROM lead_productivity_logs WHERE lead_id = p_lead_id
        )
        ORDER BY a.date ASC;
        
        -- Quotations
        SELECT jsonb_agg(to_jsonb(q.*)) INTO v_quotations
        FROM quotations q
        WHERE q.productivity_log_id IN (
            SELECT id FROM lead_productivity_logs WHERE lead_id = p_lead_id
        )
        ORDER BY q.created_at DESC;
    END IF;
    
    -- Build result
    v_result := jsonb_build_object(
        'success', true,
        'found', true,
        'data', jsonb_build_object(
            'lead', v_lead,
            'latest_productivity_log', COALESCE(v_latest_log, 'null'::jsonb),
            'appointments', COALESCE(v_appointments, '[]'::jsonb),
            'quotations', COALESCE(v_quotations, '[]'::jsonb)
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
-- Function 3: ai_get_sales_performance (Enhanced)
-- =============================================================================
-- Get sales performance with date range and metrics
CREATE OR REPLACE FUNCTION ai_get_sales_performance(
    p_sales_id INTEGER,
    p_user_id UUID,
    p_date_from DATE DEFAULT NULL,
    p_date_to DATE DEFAULT NULL,
    p_period TEXT DEFAULT 'month'
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_result JSONB;
    v_user_role TEXT;
    v_sales_member JSONB;
    v_metrics JSONB;
    v_total_leads INTEGER;
    v_deals_closed INTEGER;
    v_pipeline_value NUMERIC;
    v_conversion_rate NUMERIC;
BEGIN
    -- Get user role
    SELECT raw_user_meta_data->>'role' INTO v_user_role
    FROM auth.users
    WHERE id = p_user_id;
    
    IF v_user_role IS NULL THEN
        v_user_role := 'staff';
    END IF;
    
    -- Only admin and manager can view sales performance
    IF v_user_role NOT IN ('admin', 'manager') THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', true,
            'message', 'Permission denied. Only admin and manager can view sales performance.'
        );
    END IF;
    
    -- Get sales member info
    SELECT to_jsonb(st.*) INTO v_sales_member
    FROM sales_team_with_user_info st
    WHERE st.id = p_sales_id;
    
    IF v_sales_member IS NULL THEN
        RETURN jsonb_build_object(
            'success', false,
            'found', false,
            'message', 'Sales member not found'
        );
    END IF;
    
    -- Calculate metrics
    -- Total leads (assigned to this sales)
    SELECT COUNT(*) INTO v_total_leads
    FROM leads
    WHERE is_archived = false
    AND (sale_owner_id = p_sales_id OR post_sales_owner_id = p_sales_id)
    AND (
        (p_date_from IS NULL AND p_date_to IS NULL)
        OR (DATE(created_at_thai::timestamp) BETWEEN COALESCE(p_date_from, '1900-01-01') AND COALESCE(p_date_to, '2100-12-31'))
    );
    
    -- Deals closed (quotations from closed logs)
    SELECT COUNT(*) INTO v_deals_closed
    FROM quotations q
    JOIN lead_productivity_logs l ON q.productivity_log_id = l.id
    WHERE l.sale_id = p_sales_id
    AND l.status = 'ปิดการขายแล้ว'
    AND (
        (p_date_from IS NULL AND p_date_to IS NULL)
        OR (DATE(l.created_at_thai::timestamp) BETWEEN COALESCE(p_date_from, '1900-01-01') AND COALESCE(p_date_to, '2100-12-31'))
    );
    
    -- Pipeline value
    SELECT COALESCE(SUM(q.total_amount), 0) INTO v_pipeline_value
    FROM quotations q
    JOIN lead_productivity_logs l ON q.productivity_log_id = l.id
    WHERE l.sale_id = p_sales_id
    AND l.status = 'ปิดการขายแล้ว'
    AND (
        (p_date_from IS NULL AND p_date_to IS NULL)
        OR (DATE(l.created_at_thai::timestamp) BETWEEN COALESCE(p_date_from, '1900-01-01') AND COALESCE(p_date_to, '2100-12-31'))
    );
    
    -- Conversion rate
    v_conversion_rate := CASE 
        WHEN v_total_leads > 0 THEN (v_deals_closed::NUMERIC / v_total_leads::NUMERIC) * 100
        ELSE 0
    END;
    
    -- Build metrics
    v_metrics := jsonb_build_object(
        'total_leads', v_total_leads,
        'deals_closed', v_deals_closed,
        'pipeline_value', v_pipeline_value,
        'conversion_rate', ROUND(v_conversion_rate, 2)
    );
    
    -- Build result
    v_result := jsonb_build_object(
        'success', true,
        'data', jsonb_build_object(
            'sales_member', v_sales_member,
            'metrics', v_metrics
        ),
        'meta', jsonb_build_object(
            'period', p_period,
            'date_from', p_date_from,
            'date_to', p_date_to
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
-- Function 4: ai_get_inventory_status (Enhanced)
-- =============================================================================
-- Get inventory status with filters
CREATE OR REPLACE FUNCTION ai_get_inventory_status(
    p_user_id UUID,
    p_filters JSONB DEFAULT '{}',
    p_date_from DATE DEFAULT NULL,
    p_date_to DATE DEFAULT NULL,
    p_limit INTEGER DEFAULT 100
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_result JSONB;
    v_user_role TEXT;
    v_products JSONB;
    v_stats JSONB;
    v_total_products INTEGER;
    v_low_stock_count INTEGER;
BEGIN
    -- Get user role
    SELECT raw_user_meta_data->>'role' INTO v_user_role
    FROM auth.users
    WHERE id = p_user_id;
    
    IF v_user_role IS NULL THEN
        v_user_role := 'staff';
    END IF;
    
    -- Get products
    SELECT jsonb_agg(
        jsonb_build_object(
            'id', id,
            'name', name,
            'description', description,
            'sku', sku,
            'category', category,
            'stock_total', stock_total,
            'stock_available', stock_available,
            'unit_price', unit_price,
            'is_active', is_active
        )
    ) INTO v_products
    FROM products
    WHERE (
        (p_filters->>'product_name' IS NULL OR LOWER(name) LIKE LOWER('%' || (p_filters->>'product_name') || '%'))
        AND (p_filters->>'category' IS NULL OR category = p_filters->>'category')
        AND (p_filters->>'is_active' IS NULL OR is_active = (p_filters->>'is_active')::boolean)
        AND (
            p_filters->>'low_stock' IS NULL 
            OR (p_filters->>'low_stock')::boolean = (stock_available < 10)
        )
    )
    ORDER BY name
    LIMIT CASE WHEN p_date_from IS NULL AND p_date_to IS NULL THEN p_limit ELSE 10000 END;
    
    -- Calculate stats
    SELECT COUNT(*) INTO v_total_products
    FROM products
    WHERE (
        (p_filters->>'product_name' IS NULL OR LOWER(name) LIKE LOWER('%' || (p_filters->>'product_name') || '%'))
        AND (p_filters->>'category' IS NULL OR category = p_filters->>'category')
        AND (p_filters->>'is_active' IS NULL OR is_active = (p_filters->>'is_active')::boolean)
    );
    
    SELECT COUNT(*) INTO v_low_stock_count
    FROM products
    WHERE stock_available < 10
    AND (
        (p_filters->>'product_name' IS NULL OR LOWER(name) LIKE LOWER('%' || (p_filters->>'product_name') || '%'))
        AND (p_filters->>'category' IS NULL OR category = p_filters->>'category')
        AND (p_filters->>'is_active' IS NULL OR is_active = (p_filters->>'is_active')::boolean)
    );
    
    v_stats := jsonb_build_object(
        'total_products', v_total_products,
        'low_stock_count', v_low_stock_count,
        'returned', jsonb_array_length(COALESCE(v_products, '[]'::jsonb))
    );
    
    -- Build result
    v_result := jsonb_build_object(
        'success', true,
        'data', jsonb_build_object(
            'products', COALESCE(v_products, '[]'::jsonb),
            'stats', v_stats
        ),
        'meta', jsonb_build_object(
            'filters_applied', p_filters,
            'date_from', p_date_from,
            'date_to', p_date_to,
            'limit', p_limit
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
-- Function 5: ai_get_appointments (Enhanced)
-- =============================================================================
-- Get appointments with filters and date range
CREATE OR REPLACE FUNCTION ai_get_appointments(
    p_user_id UUID,
    p_filters JSONB DEFAULT '{}',
    p_date_from DATE DEFAULT NULL,
    p_date_to DATE DEFAULT NULL,
    p_type TEXT DEFAULT 'all'  -- 'upcoming', 'past', 'all'
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
BEGIN
    -- Get user role
    SELECT raw_user_meta_data->>'role' INTO v_user_role
    FROM auth.users
    WHERE id = p_user_id;
    
    IF v_user_role IS NULL THEN
        v_user_role := 'staff';
    END IF;
    
    -- Get engineer appointments
    SELECT jsonb_agg(to_jsonb(a.*)) INTO v_engineer
    FROM appointments a
    JOIN lead_productivity_logs l ON a.productivity_log_id = l.id
    WHERE a.appointment_type = 'engineer'
    AND (
        (p_filters->>'appointment_type' IS NULL OR a.appointment_type = p_filters->>'appointment_type')
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
    ORDER BY a.date ASC;
    
    -- Get follow-up appointments
    SELECT jsonb_agg(to_jsonb(a.*)) INTO v_follow_up
    FROM appointments a
    JOIN lead_productivity_logs l ON a.productivity_log_id = l.id
    WHERE a.appointment_type = 'follow-up'
    AND (
        (p_filters->>'appointment_type' IS NULL OR a.appointment_type = p_filters->>'appointment_type')
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
    ORDER BY a.date ASC;
    
    -- Get payment appointments (from quotations)
    SELECT jsonb_agg(to_jsonb(q.*)) INTO v_payment
    FROM quotations q
    JOIN lead_productivity_logs l ON q.productivity_log_id = l.id
    WHERE q.estimate_payment_date IS NOT NULL
    AND (
        (p_filters->>'sales_id' IS NULL OR l.sale_id = (p_filters->>'sales_id')::integer)
    )
    AND (
        (p_date_from IS NULL AND p_date_to IS NULL)
        OR (DATE(q.estimate_payment_date) BETWEEN COALESCE(p_date_from, '1900-01-01') AND COALESCE(p_date_to, '2100-12-31'))
    )
    AND (
        p_type = 'all'
        OR (p_type = 'upcoming' AND q.estimate_payment_date >= CURRENT_DATE)
        OR (p_type = 'past' AND q.estimate_payment_date < CURRENT_DATE)
    )
    ORDER BY q.estimate_payment_date ASC;
    
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
    
    -- Build result
    v_result := jsonb_build_object(
        'success', true,
        'data', jsonb_build_object(
            'engineer', COALESCE(v_engineer, '[]'::jsonb),
            'follow_up', COALESCE(v_follow_up, '[]'::jsonb),
            'payment', COALESCE(v_payment, '[]'::jsonb),
            'stats', v_stats
        ),
        'meta', jsonb_build_object(
            'filters_applied', p_filters,
            'date_from', p_date_from,
            'date_to', p_date_to,
            'type', p_type
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
GRANT EXECUTE ON FUNCTION ai_get_leads(UUID, JSONB, DATE, DATE, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION ai_get_lead_detail(INTEGER, UUID, BOOLEAN) TO authenticated;
GRANT EXECUTE ON FUNCTION ai_get_sales_performance(INTEGER, UUID, DATE, DATE, TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION ai_get_inventory_status(UUID, JSONB, DATE, DATE, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION ai_get_appointments(UUID, JSONB, DATE, DATE, TEXT) TO authenticated;
