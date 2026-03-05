-- Fix ai_get_daily_summary and ai_get_customer_info functions
-- Migration: 20250117000001_fix_ai_get_daily_summary.sql
-- Fixes: Remove dependency on is_active column that doesn't exist

-- Function: Get Daily Summary (Fixed version)
-- Returns summary statistics for a specific date
CREATE OR REPLACE FUNCTION ai_get_daily_summary(
    p_user_id UUID,
    p_date DATE DEFAULT CURRENT_DATE
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_result JSONB;
    v_user_role TEXT;
    v_total_leads INTEGER;
    v_new_leads INTEGER;
    v_total_customers INTEGER;
BEGIN
    -- Get user role
    SELECT raw_user_meta_data->>'role' INTO v_user_role
    FROM auth.users
    WHERE id = p_user_id;
    
    IF v_user_role IS NULL THEN
        v_user_role := 'staff';
    END IF;
    
    -- Count total leads (non-archived)
    SELECT COUNT(*) INTO v_total_leads
    FROM leads
    WHERE is_archived = false;
    
    -- Count new leads created on date
    SELECT COUNT(*) INTO v_new_leads
    FROM leads
    WHERE DATE(created_at_thai::timestamp) = p_date
    AND is_archived = false;
    
    -- Count total customers (from customer_services)
    -- Note: Skip if table or column doesn't exist to avoid errors
    BEGIN
        -- Check if table exists first
        IF EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'customer_services'
        ) THEN
            -- Try to count with is_active column if it exists
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'customer_services' 
                AND column_name = 'is_active'
            ) THEN
                SELECT COUNT(*) INTO v_total_customers
                FROM customer_services
                WHERE is_active = true;
            -- Try with is_archived column as fallback
            ELSIF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'customer_services' 
                AND column_name = 'is_archived'
            ) THEN
                SELECT COUNT(*) INTO v_total_customers
                FROM customer_services
                WHERE is_archived = false;
            -- If no status column, count all
            ELSE
                SELECT COUNT(*) INTO v_total_customers
                FROM customer_services;
            END IF;
        ELSE
            v_total_customers := 0;
        END IF;
    EXCEPTION
        WHEN OTHERS THEN
            -- If any error occurs, set to 0 and continue
            v_total_customers := 0;
    END;
    
    -- Build result based on role
    IF v_user_role IN ('admin', 'manager') THEN
        v_result := jsonb_build_object(
            'date', p_date,
            'total_leads', v_total_leads,
            'new_leads_today', v_new_leads,
            'total_customers', v_total_customers,
            'role', v_user_role
        );
    ELSE
        -- Staff gets limited summary
        v_result := jsonb_build_object(
            'date', p_date,
            'new_leads_today', v_new_leads,
            'role', v_user_role
        );
    END IF;
    
    RETURN v_result;
EXCEPTION
    WHEN OTHERS THEN
        RETURN jsonb_build_object(
            'error', true,
            'message', SQLERRM
        );
END;
$$;

-- Function: Get Customer Info (Fixed version)
-- Searches for customer by name
CREATE OR REPLACE FUNCTION ai_get_customer_info(
    p_customer_name TEXT,
    p_user_id UUID
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_result JSONB;
    v_user_role TEXT;
    v_customer_record RECORD;
BEGIN
    -- Get user role
    SELECT raw_user_meta_data->>'role' INTO v_user_role
    FROM auth.users
    WHERE id = p_user_id;
    
    IF v_user_role IS NULL THEN
        v_user_role := 'staff';
    END IF;
    
    -- Search for customer
    -- Handle missing is_active column gracefully
    BEGIN
        -- Try with is_active column if it exists
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'customer_services' 
            AND column_name = 'is_active'
        ) THEN
            SELECT 
                id,
                customer_name,
                tel,
                line_id,
                service_type,
                status,
                created_at,
                updated_at
            INTO v_customer_record
            FROM customer_services
            WHERE LOWER(customer_name) LIKE LOWER('%' || p_customer_name || '%')
            AND is_active = true
            ORDER BY updated_at DESC
            LIMIT 1;
        -- Try with is_archived column as fallback
        ELSIF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'customer_services' 
            AND column_name = 'is_archived'
        ) THEN
            SELECT 
                id,
                customer_name,
                tel,
                line_id,
                service_type,
                status,
                created_at,
                updated_at
            INTO v_customer_record
            FROM customer_services
            WHERE LOWER(customer_name) LIKE LOWER('%' || p_customer_name || '%')
            AND is_archived = false
            ORDER BY updated_at DESC
            LIMIT 1;
        -- If no status column, just search without filter
        ELSE
            SELECT 
                id,
                customer_name,
                tel,
                line_id,
                service_type,
                status,
                created_at,
                updated_at
            INTO v_customer_record
            FROM customer_services
            WHERE LOWER(customer_name) LIKE LOWER('%' || p_customer_name || '%')
            ORDER BY updated_at DESC
            LIMIT 1;
        END IF;
    EXCEPTION
        WHEN undefined_table THEN
            -- If customer_services table doesn't exist, set record to null
            v_customer_record := NULL;
        WHEN OTHERS THEN
            -- If any error, set record to null
            v_customer_record := NULL;
    END;
    
    IF v_customer_record.id IS NULL THEN
        v_result := jsonb_build_object(
            'found', false,
            'message', 'Customer not found'
        );
        RETURN v_result;
    END IF;
    
    -- Build result (mask PII for non-admin)
    IF v_user_role = 'admin' THEN
        v_result := jsonb_build_object(
            'found', true,
            'customer_id', v_customer_record.id,
            'customer_name', v_customer_record.customer_name,
            'tel', v_customer_record.tel,
            'line_id', v_customer_record.line_id,
            'service_type', v_customer_record.service_type,
            'status', v_customer_record.status,
            'created_at', v_customer_record.created_at,
            'updated_at', v_customer_record.updated_at
        );
    ELSE
        -- Mask PII for non-admin
        v_result := jsonb_build_object(
            'found', true,
            'customer_id', v_customer_record.id,
            'customer_name', v_customer_record.customer_name,
            'service_type', v_customer_record.service_type,
            'status', v_customer_record.status
        );
    END IF;
    
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
GRANT EXECUTE ON FUNCTION ai_get_daily_summary(UUID, DATE) TO authenticated;
GRANT EXECUTE ON FUNCTION ai_get_customer_info(TEXT, UUID) TO authenticated;
