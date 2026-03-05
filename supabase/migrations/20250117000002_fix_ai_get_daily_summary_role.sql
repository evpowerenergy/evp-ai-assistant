-- Fix ai_get_daily_summary to accept role as parameter instead of querying auth.users
-- Migration: 20250117000002_fix_ai_get_daily_summary_role.sql
-- Fixes: Role query from auth.users doesn't work via REST API, pass role as parameter

-- Function: Get Daily Summary (Fixed version - accepts role parameter)
CREATE OR REPLACE FUNCTION ai_get_daily_summary(
    p_user_id UUID,
    p_date DATE DEFAULT CURRENT_DATE,
    p_user_role TEXT DEFAULT 'staff'
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_result JSONB;
    v_total_leads INTEGER;
    v_new_leads INTEGER;
    v_total_customers INTEGER;
BEGIN
    -- Use provided role (passed from backend JWT token)
    -- No need to query auth.users since we can't access it via REST API
    
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
    IF p_user_role IN ('admin', 'manager') THEN
        v_result := jsonb_build_object(
            'date', p_date,
            'total_leads', v_total_leads,
            'new_leads_today', v_new_leads,
            'total_customers', v_total_customers,
            'role', p_user_role
        );
    ELSE
        -- Staff gets limited summary
        v_result := jsonb_build_object(
            'date', p_date,
            'new_leads_today', v_new_leads,
            'role', p_user_role
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
GRANT EXECUTE ON FUNCTION ai_get_daily_summary(UUID, DATE, TEXT) TO authenticated;
