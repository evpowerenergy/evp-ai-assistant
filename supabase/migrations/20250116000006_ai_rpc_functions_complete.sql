-- Complete AI RPC Functions (High + Medium Priority)
-- Migration: 20250116000006_ai_rpc_functions_complete.sql
-- Support: Date filtering, Multiple filters, Related data, Stats

-- =============================================================================
-- Function 1: ai_get_service_appointments (High Priority)
-- =============================================================================
-- Get service appointments with filters and date range
CREATE OR REPLACE FUNCTION ai_get_service_appointments(
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
    v_appointments JSONB;
    v_stats JSONB;
BEGIN
    -- Get user role
    SELECT raw_user_meta_data->>'role' INTO v_user_role
    FROM auth.users
    WHERE id = p_user_id;
    
    IF v_user_role IS NULL THEN
        v_user_role := 'staff';
    END IF;
    
    -- Get service appointments
    SELECT jsonb_agg(
        jsonb_build_object(
            'id', sa.id,
            'customer_service_id', sa.customer_service_id,
            'appointment_date', sa.appointment_date,
            'appointment_date_thai', sa.appointment_date_thai,
            'appointment_time', sa.appointment_time,
            'technician_name', sa.technician_name,
            'service_type', sa.service_type,
            'status', sa.status,
            'notes', sa.notes,
            'estimated_duration_minutes', sa.estimated_duration_minutes,
            'created_at_thai', sa.created_at_thai
        )
    ) INTO v_appointments
    FROM service_appointments sa
    WHERE (
        -- Apply filters
        (p_filters->>'status' IS NULL OR sa.status = p_filters->>'status')
        AND (p_filters->>'service_type' IS NULL OR sa.service_type = p_filters->>'service_type')
        AND (p_filters->>'technician_name' IS NULL OR sa.technician_name = p_filters->>'technician_name')
        AND (p_filters->>'customer_service_id' IS NULL OR sa.customer_service_id = (p_filters->>'customer_service_id')::integer)
    )
    AND (
        -- Date filter
        (p_date_from IS NULL AND p_date_to IS NULL)
        OR (DATE(sa.appointment_date) BETWEEN COALESCE(p_date_from, '1900-01-01') AND COALESCE(p_date_to, '2100-12-31'))
    )
    AND (
        -- Type filter
        p_type = 'all'
        OR (p_type = 'upcoming' AND sa.appointment_date >= CURRENT_DATE)
        OR (p_type = 'past' AND sa.appointment_date < CURRENT_DATE)
    )
    ORDER BY sa.appointment_date ASC;
    
    -- Build stats
    v_stats := jsonb_build_object(
        'total', jsonb_array_length(COALESCE(v_appointments, '[]'::jsonb)),
        'upcoming', (
            SELECT COUNT(*)
            FROM service_appointments
            WHERE appointment_date >= CURRENT_DATE
        ),
        'past', (
            SELECT COUNT(*)
            FROM service_appointments
            WHERE appointment_date < CURRENT_DATE
        )
    );
    
    -- Build result
    v_result := jsonb_build_object(
        'success', true,
        'data', jsonb_build_object(
            'appointments', COALESCE(v_appointments, '[]'::jsonb),
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

-- =============================================================================
-- Function 2: ai_get_sales_docs (High Priority)
-- =============================================================================
-- Get sales documents (QT/BL/INV) with filters and date range
CREATE OR REPLACE FUNCTION ai_get_sales_docs(
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
    v_docs JSONB;
    v_stats JSONB;
    v_total_count INTEGER;
BEGIN
    -- Get user role
    SELECT raw_user_meta_data->>'role' INTO v_user_role
    FROM auth.users
    WHERE id = p_user_id;
    
    IF v_user_role IS NULL THEN
        v_user_role := 'staff';
    END IF;
    
    -- Count total
    SELECT COUNT(*) INTO v_total_count
    FROM sales_docs sd
    WHERE (
        (p_filters->>'doc_type' IS NULL OR sd.doc_type = p_filters->>'doc_type')
        AND (p_filters->>'status' IS NULL OR sd.status = p_filters->>'status')
        AND (p_filters->>'customer_id' IS NULL OR sd.customer_id::text = p_filters->>'customer_id')
        AND (p_filters->>'salesperson_id' IS NULL OR sd.salesperson_id::text = p_filters->>'salesperson_id')
    )
    AND (
        (p_date_from IS NULL AND p_date_to IS NULL)
        OR (sd.doc_date BETWEEN COALESCE(p_date_from, '1900-01-01') AND COALESCE(p_date_to, '2100-12-31'))
    );
    
    -- Get sales docs with items
    SELECT jsonb_agg(
        jsonb_build_object(
            'id', sd.id,
            'doc_number', sd.doc_number,
            'doc_type', sd.doc_type,
            'doc_date', sd.doc_date,
            'customer_id', sd.customer_id,
            'salesperson_id', sd.salesperson_id,
            'total_amount', sd.total_amount,
            'note', sd.note,
            'created_at', sd.created_at,
            'items', (
                SELECT jsonb_agg(
                    jsonb_build_object(
                        'id', sdi.id,
                        'product_id', sdi.product_id,
                        'qty', sdi.qty,
                        'unit_price', sdi.unit_price,
                        'total_price', sdi.total_price
                    )
                )
                FROM sales_doc_items sdi
                WHERE sdi.sales_doc_id = sd.id
            )
        )
    ) INTO v_docs
    FROM sales_docs sd
    WHERE (
        (p_filters->>'doc_type' IS NULL OR sd.doc_type = p_filters->>'doc_type')
        AND (p_filters->>'status' IS NULL OR sd.status = p_filters->>'status')
        AND (p_filters->>'customer_id' IS NULL OR sd.customer_id::text = p_filters->>'customer_id')
        AND (p_filters->>'salesperson_id' IS NULL OR sd.salesperson_id::text = p_filters->>'salesperson_id')
    )
    AND (
        (p_date_from IS NULL AND p_date_to IS NULL)
        OR (sd.doc_date BETWEEN COALESCE(p_date_from, '1900-01-01') AND COALESCE(p_date_to, '2100-12-31'))
    )
    ORDER BY sd.doc_date DESC
    LIMIT CASE WHEN p_date_from IS NULL AND p_date_to IS NULL THEN p_limit ELSE 10000 END;
    
    -- Build stats
    v_stats := jsonb_build_object(
        'total', v_total_count,
        'returned', jsonb_array_length(COALESCE(v_docs, '[]'::jsonb)),
        'by_type', (
            SELECT jsonb_object_agg(doc_type, count)
            FROM (
                SELECT doc_type, COUNT(*) as count
                FROM sales_docs
                WHERE (
                    (p_date_from IS NULL AND p_date_to IS NULL)
                    OR (doc_date BETWEEN COALESCE(p_date_from, '1900-01-01') AND COALESCE(p_date_to, '2100-12-31'))
                )
                GROUP BY doc_type
            ) sub
        )
    );
    
    -- Build result
    v_result := jsonb_build_object(
        'success', true,
        'data', jsonb_build_object(
            'sales_docs', COALESCE(v_docs, '[]'::jsonb),
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
-- Function 3: ai_get_quotations (High Priority - Dedicated)
-- =============================================================================
-- Get quotations with filters and date range (dedicated function)
CREATE OR REPLACE FUNCTION ai_get_quotations(
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
    v_quotations JSONB;
    v_stats JSONB;
    v_total_count INTEGER;
BEGIN
    -- Get user role
    SELECT raw_user_meta_data->>'role' INTO v_user_role
    FROM auth.users
    WHERE id = p_user_id;
    
    IF v_user_role IS NULL THEN
        v_user_role := 'staff';
    END IF;
    
    -- Count total
    SELECT COUNT(*) INTO v_total_count
    FROM quotations q
    JOIN lead_productivity_logs l ON q.productivity_log_id = l.id
    WHERE (
        (p_filters->>'has_qt' IS NULL OR q.has_qt = (p_filters->>'has_qt')::boolean)
        AND (p_filters->>'has_inv' IS NULL OR q.has_inv = (p_filters->>'has_inv')::boolean)
        AND (p_filters->>'payment_method' IS NULL OR q.payment_method = p_filters->>'payment_method')
        AND (p_filters->>'sales_id' IS NULL OR l.sale_id = (p_filters->>'sales_id')::integer)
    )
    AND (
        (p_date_from IS NULL AND p_date_to IS NULL)
        OR (
            DATE(l.created_at_thai::timestamp) BETWEEN COALESCE(p_date_from, '1900-01-01') AND COALESCE(p_date_to, '2100-12-31')
        )
    );
    
    -- Get quotations
    SELECT jsonb_agg(
        jsonb_build_object(
            'id', q.id,
            'quotation_number', q.quotation_number,
            'invoice_number', q.invoice_number,
            'total_amount', q.total_amount,
            'has_qt', q.has_qt,
            'has_inv', q.has_inv,
            'payment_method', q.payment_method,
            'installment_amount', q.installment_amount,
            'installment_periods', q.installment_periods,
            'estimate_payment_date', q.estimate_payment_date,
            'estimate_payment_date_thai', q.estimate_payment_date_thai,
            'productivity_log_id', q.productivity_log_id,
            'created_at', (
                SELECT created_at_thai
                FROM lead_productivity_logs
                WHERE id = q.productivity_log_id
            )
        )
    ) INTO v_quotations
    FROM quotations q
    JOIN lead_productivity_logs l ON q.productivity_log_id = l.id
    WHERE (
        (p_filters->>'has_qt' IS NULL OR q.has_qt = (p_filters->>'has_qt')::boolean)
        AND (p_filters->>'has_inv' IS NULL OR q.has_inv = (p_filters->>'has_inv')::boolean)
        AND (p_filters->>'payment_method' IS NULL OR q.payment_method = p_filters->>'payment_method')
        AND (p_filters->>'sales_id' IS NULL OR l.sale_id = (p_filters->>'sales_id')::integer)
    )
    AND (
        (p_date_from IS NULL AND p_date_to IS NULL)
        OR (
            DATE(l.created_at_thai::timestamp) BETWEEN COALESCE(p_date_from, '1900-01-01') AND COALESCE(p_date_to, '2100-12-31')
        )
    )
    ORDER BY l.created_at_thai DESC
    LIMIT CASE WHEN p_date_from IS NULL AND p_date_to IS NULL THEN p_limit ELSE 10000 END;
    
    -- Build stats
    v_stats := jsonb_build_object(
        'total', v_total_count,
        'returned', jsonb_array_length(COALESCE(v_quotations, '[]'::jsonb)),
        'total_amount', (
            SELECT COALESCE(SUM(total_amount), 0)
            FROM quotations q2
            JOIN lead_productivity_logs l2 ON q2.productivity_log_id = l2.id
            WHERE (
                (p_date_from IS NULL AND p_date_to IS NULL)
                OR (
                    DATE(l2.created_at_thai::timestamp) BETWEEN COALESCE(p_date_from, '1900-01-01') AND COALESCE(p_date_to, '2100-12-31')
                )
            )
        ),
        'with_qt', (
            SELECT COUNT(*)
            FROM quotations
            WHERE has_qt = true
        ),
        'with_inv', (
            SELECT COUNT(*)
            FROM quotations
            WHERE has_inv = true
        )
    );
    
    -- Build result
    v_result := jsonb_build_object(
        'success', true,
        'data', jsonb_build_object(
            'quotations', COALESCE(v_quotations, '[]'::jsonb),
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
-- Function 4: ai_get_permit_requests (Medium Priority)
-- =============================================================================
-- Get permit requests with filters and date range
CREATE OR REPLACE FUNCTION ai_get_permit_requests(
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
    v_requests JSONB;
    v_stats JSONB;
    v_total_count INTEGER;
BEGIN
    -- Get user role
    SELECT raw_user_meta_data->>'role' INTO v_user_role
    FROM auth.users
    WHERE id = p_user_id;
    
    IF v_user_role IS NULL THEN
        v_user_role := 'staff';
    END IF;
    
    -- Count total
    SELECT COUNT(*) INTO v_total_count
    FROM permit_requests pr
    WHERE (
        (p_filters->>'main_status' IS NULL OR pr.main_status = p_filters->>'main_status')
        AND (p_filters->>'sub_status' IS NULL OR pr.sub_status = p_filters->>'sub_status')
        AND (p_filters->>'company_name' IS NULL OR LOWER(pr.company_name) LIKE LOWER('%' || (p_filters->>'company_name') || '%'))
        AND (p_filters->>'operator_name' IS NULL OR LOWER(pr.operator_name) LIKE LOWER('%' || (p_filters->>'operator_name') || '%'))
        AND (p_filters->>'permit_number' IS NULL OR pr.permit_number = p_filters->>'permit_number')
    )
    AND (
        (p_date_from IS NULL AND p_date_to IS NULL)
        OR (
            DATE(pr.document_received_date) BETWEEN COALESCE(p_date_from, '1900-01-01') AND COALESCE(p_date_to, '2100-12-31')
            OR DATE(pr.completion_date) BETWEEN COALESCE(p_date_from, '1900-01-01') AND COALESCE(p_date_to, '2100-12-31')
        )
    );
    
    -- Get permit requests
    SELECT jsonb_agg(
        jsonb_build_object(
            'id', pr.id,
            'requester_name', pr.requester_name,
            'operator_name', pr.operator_name,
            'company_name', pr.company_name,
            'document_number', pr.document_number,
            'permit_number', pr.permit_number,
            'main_status', pr.main_status,
            'sub_status', pr.sub_status,
            'document_received_date', pr.document_received_date,
            'completion_date', pr.completion_date,
            'online_date', pr.online_date,
            'connection_type', pr.connection_type,
            'meter_number', pr.meter_number,
            'capacity_kw', pr.capacity_kw,
            'province', pr.province,
            'district', pr.district,
            'phone_number', CASE WHEN v_user_role = 'admin' THEN pr.phone_number ELSE NULL END,  -- Mask PII
            'note', pr.note,
            'created_at', pr.created_at
        )
    ) INTO v_requests
    FROM permit_requests pr
    WHERE (
        (p_filters->>'main_status' IS NULL OR pr.main_status = p_filters->>'main_status')
        AND (p_filters->>'sub_status' IS NULL OR pr.sub_status = p_filters->>'sub_status')
        AND (p_filters->>'company_name' IS NULL OR LOWER(pr.company_name) LIKE LOWER('%' || (p_filters->>'company_name') || '%'))
        AND (p_filters->>'operator_name' IS NULL OR LOWER(pr.operator_name) LIKE LOWER('%' || (p_filters->>'operator_name') || '%'))
        AND (p_filters->>'permit_number' IS NULL OR pr.permit_number = p_filters->>'permit_number')
    )
    AND (
        (p_date_from IS NULL AND p_date_to IS NULL)
        OR (
            DATE(pr.document_received_date) BETWEEN COALESCE(p_date_from, '1900-01-01') AND COALESCE(p_date_to, '2100-12-31')
            OR DATE(pr.completion_date) BETWEEN COALESCE(p_date_from, '1900-01-01') AND COALESCE(p_date_to, '2100-12-31')
        )
    )
    ORDER BY pr.document_received_date DESC
    LIMIT CASE WHEN p_date_from IS NULL AND p_date_to IS NULL THEN p_limit ELSE 10000 END;
    
    -- Build stats
    v_stats := jsonb_build_object(
        'total', v_total_count,
        'returned', jsonb_array_length(COALESCE(v_requests, '[]'::jsonb)),
        'by_status', (
            SELECT jsonb_object_agg(main_status, count)
            FROM (
                SELECT main_status, COUNT(*) as count
                FROM permit_requests
                GROUP BY main_status
            ) sub
        )
    );
    
    -- Build result
    v_result := jsonb_build_object(
        'success', true,
        'data', jsonb_build_object(
            'permit_requests', COALESCE(v_requests, '[]'::jsonb),
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
-- Function 5: ai_get_stock_movements (Medium Priority)
-- =============================================================================
-- Get stock movements with filters and date range
CREATE OR REPLACE FUNCTION ai_get_stock_movements(
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
    v_movements JSONB;
    v_stats JSONB;
    v_total_count INTEGER;
BEGIN
    -- Get user role
    SELECT raw_user_meta_data->>'role' INTO v_user_role
    FROM auth.users
    WHERE id = p_user_id;
    
    IF v_user_role IS NULL THEN
        v_user_role := 'staff';
    END IF;
    
    -- Count total
    SELECT COUNT(*) INTO v_total_count
    FROM stock_movements sm
    WHERE (
        (p_filters->>'movement' IS NULL OR sm.movement::text = p_filters->>'movement')
        AND (p_filters->>'product_id' IS NULL OR sm.product_id = (p_filters->>'product_id')::integer)
        AND (p_filters->>'ref_table' IS NULL OR sm.ref_table = p_filters->>'ref_table')
    )
    AND (
        (p_date_from IS NULL AND p_date_to IS NULL)
        OR (DATE(sm.created_at_thai::timestamp) BETWEEN COALESCE(p_date_from, '1900-01-01') AND COALESCE(p_date_to, '2100-12-31'))
    );
    
    -- Get stock movements
    SELECT jsonb_agg(
        jsonb_build_object(
            'id', sm.id,
            'product_id', sm.product_id,
            'movement', sm.movement,
            'qty', sm.qty,
            'ref_table', sm.ref_table,
            'ref_id', sm.ref_id,
            'note', sm.note,
            'created_at_thai', sm.created_at_thai
        )
    ) INTO v_movements
    FROM stock_movements sm
    WHERE (
        (p_filters->>'movement' IS NULL OR sm.movement::text = p_filters->>'movement')
        AND (p_filters->>'product_id' IS NULL OR sm.product_id = (p_filters->>'product_id')::integer)
        AND (p_filters->>'ref_table' IS NULL OR sm.ref_table = p_filters->>'ref_table')
    )
    AND (
        (p_date_from IS NULL AND p_date_to IS NULL)
        OR (DATE(sm.created_at_thai::timestamp) BETWEEN COALESCE(p_date_from, '1900-01-01') AND COALESCE(p_date_to, '2100-12-31'))
    )
    ORDER BY sm.created_at_thai DESC
    LIMIT CASE WHEN p_date_from IS NULL AND p_date_to IS NULL THEN p_limit ELSE 10000 END;
    
    -- Build stats
    v_stats := jsonb_build_object(
        'total', v_total_count,
        'returned', jsonb_array_length(COALESCE(v_movements, '[]'::jsonb)),
        'by_movement', (
            SELECT jsonb_object_agg(movement::text, count)
            FROM (
                SELECT movement, COUNT(*) as count
                FROM stock_movements
                WHERE (
                    (p_date_from IS NULL AND p_date_to IS NULL)
                    OR (DATE(created_at_thai::timestamp) BETWEEN COALESCE(p_date_from, '1900-01-01') AND COALESCE(p_date_to, '2100-12-31'))
                )
                GROUP BY movement
            ) sub
        )
    );
    
    -- Build result
    v_result := jsonb_build_object(
        'success', true,
        'data', jsonb_build_object(
            'stock_movements', COALESCE(v_movements, '[]'::jsonb),
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
-- Function 6: ai_get_user_info (Medium Priority)
-- =============================================================================
-- Get user information with filters
CREATE OR REPLACE FUNCTION ai_get_user_info(
    p_user_id UUID,
    p_filters JSONB DEFAULT '{}',
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
    v_users JSONB;
    v_stats JSONB;
    v_total_count INTEGER;
    v_requesting_user_role TEXT;
BEGIN
    -- Get requesting user role
    SELECT raw_user_meta_data->>'role' INTO v_requesting_user_role
    FROM auth.users
    WHERE id = p_user_id;
    
    IF v_requesting_user_role IS NULL THEN
        v_requesting_user_role := 'staff';
    END IF;
    
    -- Only admin and manager can view user info
    IF v_requesting_user_role NOT IN ('admin', 'manager') THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', true,
            'message', 'Permission denied. Only admin and manager can view user information.'
        );
    END IF;
    
    -- Count total
    SELECT COUNT(*) INTO v_total_count
    FROM users u
    WHERE (
        (p_filters->>'role' IS NULL OR u.role = p_filters->>'role')
        AND (p_filters->>'department' IS NULL OR u.department = p_filters->>'department')
        AND (p_filters->>'status' IS NULL OR u.status = p_filters->>'status')
        AND (p_filters->>'name' IS NULL OR LOWER(u.first_name || ' ' || u.last_name) LIKE LOWER('%' || (p_filters->>'name') || '%'))
    );
    
    -- Get users
    SELECT jsonb_agg(
        jsonb_build_object(
            'id', u.id,
            'employee_code', u.employee_code,
            'first_name', u.first_name,
            'last_name', u.last_name,
            'nickname', u.nickname,
            'email', u.email,
            'phone', CASE WHEN v_requesting_user_role = 'admin' THEN u.phone ELSE NULL END,  -- Mask PII
            'department', u.department,
            'position', u.position,
            'role', u.role,
            'status', u.status,
            'created_at', u.created_at
        )
    ) INTO v_users
    FROM users u
    WHERE (
        (p_filters->>'role' IS NULL OR u.role = p_filters->>'role')
        AND (p_filters->>'department' IS NULL OR u.department = p_filters->>'department')
        AND (p_filters->>'status' IS NULL OR u.status = p_filters->>'status')
        AND (p_filters->>'name' IS NULL OR LOWER(u.first_name || ' ' || u.last_name) LIKE LOWER('%' || (p_filters->>'name') || '%'))
    )
    ORDER BY u.first_name, u.last_name
    LIMIT p_limit;
    
    -- Build stats
    v_stats := jsonb_build_object(
        'total', v_total_count,
        'returned', jsonb_array_length(COALESCE(v_users, '[]'::jsonb)),
        'by_role', (
            SELECT jsonb_object_agg(role, count)
            FROM (
                SELECT role, COUNT(*) as count
                FROM users
                WHERE (
                    (p_filters->>'department' IS NULL OR department = p_filters->>'department')
                    AND (p_filters->>'status' IS NULL OR status = p_filters->>'status')
                )
                GROUP BY role
            ) sub
        ),
        'by_department', (
            SELECT jsonb_object_agg(department, count)
            FROM (
                SELECT department, COUNT(*) as count
                FROM users
                WHERE (
                    (p_filters->>'role' IS NULL OR role = p_filters->>'role')
                    AND (p_filters->>'status' IS NULL OR status = p_filters->>'status')
                )
                GROUP BY department
            ) sub
        )
    );
    
    -- Build result
    v_result := jsonb_build_object(
        'success', true,
        'data', jsonb_build_object(
            'users', COALESCE(v_users, '[]'::jsonb),
            'stats', v_stats
        ),
        'meta', jsonb_build_object(
            'filters_applied', p_filters,
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

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION ai_get_service_appointments(UUID, JSONB, DATE, DATE, TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION ai_get_sales_docs(UUID, JSONB, DATE, DATE, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION ai_get_quotations(UUID, JSONB, DATE, DATE, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION ai_get_permit_requests(UUID, JSONB, DATE, DATE, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION ai_get_stock_movements(UUID, JSONB, DATE, DATE, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION ai_get_user_info(UUID, JSONB, INTEGER) TO authenticated;
