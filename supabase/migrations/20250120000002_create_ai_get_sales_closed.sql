-- Create RPC function for Sales Closed (ยอดขายที่ปิดแล้ว)
-- Migration: 20250120000002_create_ai_get_sales_closed.sql
-- Purpose: ดึงข้อมูลยอดขายที่ปิดการขายสำเร็จจาก productivity logs (เหมือน Sales Closed page)
-- Edge Function Reference: getSalesDataInPeriod in salesUtils.ts

-- =============================================================================
-- Function: ai_get_sales_closed
-- =============================================================================
-- Logic:
-- 1. ดึง productivity logs ที่มี status = 'ปิดการขายแล้ว'
-- 2. Filter: sale_chance_status = 'win' OR ('win + สินเชื่อ' AND credit_approval_status = 'อนุมัติ')
-- 3. Filter ตาม created_at_thai ของ log (ไม่ใช่ created_at_thai ของ lead)
-- 4. Join กับ leads table เพื่อดึงข้อมูล lead
-- 5. Join กับ quotation_documents เพื่อดึงข้อมูล QT
-- 6. Deduplicate quotations โดยใช้ document_number
-- 7. Return: salesLeads, totalSalesValue, salesCount, quotations

CREATE OR REPLACE FUNCTION ai_get_sales_closed(
    p_user_id UUID,
    p_date_from TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    p_date_to TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    p_sales_member_id INTEGER DEFAULT NULL,
    p_user_role TEXT DEFAULT 'staff'
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_result JSONB;
    v_sales_logs JSONB;
    v_quotations JSONB;
    v_sales_leads JSONB;
    v_total_sales_value NUMERIC := 0;
    v_sales_count INTEGER := 0;
    v_log_ids INTEGER[];
BEGIN
    -- Step 1: ดึง productivity logs ที่มี status = 'ปิดการขายแล้ว'
    -- และ sale_chance_status = 'win' OR ('win + สินเชื่อ' AND credit_approval_status = 'อนุมัติ')
    -- IMPORTANT: apply ORDER BY inside a subquery (avoid GROUP BY error with jsonb_agg)
    SELECT jsonb_agg(row_data) INTO v_sales_logs
    FROM (
        SELECT jsonb_build_object(
            'log_id', lpl.id,
            'lead_id', lpl.lead_id,
            'sale_id', lpl.sale_id,
            'created_at_thai', lpl.created_at_thai,
            'sale_chance_status', lpl.sale_chance_status,
            'credit_approval_status', lpl.credit_approval_status,
            'lead', jsonb_build_object(
                'id', l.id,
                'sale_owner_id', l.sale_owner_id,
                'category', l.category,
                'platform', l.platform,
                'full_name', l.full_name,
                'display_name', l.display_name,
                'tel', l.tel,
                'line_id', l.line_id,
                'is_from_ppa_project', l.is_from_ppa_project
            )
        ) AS row_data
        FROM lead_productivity_logs lpl
        INNER JOIN leads l ON l.id = lpl.lead_id
        WHERE lpl.status = 'ปิดการขายแล้ว'
        AND (
            lpl.sale_chance_status = 'win'
            OR (
                lpl.sale_chance_status = 'win + สินเชื่อ'
                AND lpl.credit_approval_status = 'อนุมัติ'
            )
        )
        AND (
            -- Date filter on log's created_at_thai (not lead's created_at_thai)
            (p_date_from IS NULL AND p_date_to IS NULL)
            OR (
                lpl.created_at_thai IS NOT NULL
                AND lpl.created_at_thai >= COALESCE(p_date_from, '1900-01-01'::timestamp with time zone)
                AND lpl.created_at_thai <= COALESCE(p_date_to, '2100-12-31'::timestamp with time zone)
            )
        )
        AND (
            -- Sales member filter
            (p_sales_member_id IS NULL OR lpl.sale_id = p_sales_member_id)
        )
        ORDER BY lpl.created_at_thai DESC
    ) ordered_rows;
    
    IF v_sales_logs IS NULL THEN
        v_sales_logs := '[]'::jsonb;
    END IF;
    
    -- Step 2: ดึง quotation_documents จาก productivity logs
    -- NOTE: v_sales_logs is JSONB, so we aggregate IDs from JSON (lpl alias is not in scope here).
    SELECT ARRAY_AGG(DISTINCT (log->>'log_id')::INTEGER) INTO v_log_ids
    FROM jsonb_array_elements(v_sales_logs) AS log
    WHERE (log->>'log_id')::INTEGER IS NOT NULL;
    
    IF v_log_ids IS NOT NULL AND array_length(v_log_ids, 1) > 0 THEN
        SELECT jsonb_agg(
            jsonb_build_object(
                'id', qd.id,
                'productivity_log_id', qd.productivity_log_id,
                'document_number', qd.document_number,
                'amount', qd.amount,
                'created_at_thai', qd.created_at_thai
            )
        ) INTO v_quotations
        FROM quotation_documents qd
        WHERE qd.productivity_log_id = ANY(v_log_ids)
        AND qd.document_type::text = 'quotation';
    END IF;
    
    IF v_quotations IS NULL THEN
        v_quotations := '[]'::jsonb;
    END IF;
    
    -- Step 3: สร้าง salesLeads โดย join logs กับ quotations และ deduplicate
    -- Logic: แยกตาม log แต่ละตัว (ไม่ group by leadId)
    -- แต่ละ log = 1 หรือหลาย QT (deduplicate ใน log เดียวกัน)
    WITH sales_logs_with_quotations AS (
        SELECT 
            (log->>'log_id')::INTEGER as log_id,
            (log->>'lead_id')::INTEGER as lead_id,
            (log->>'sale_id')::INTEGER as sale_id,
            log->>'created_at_thai' as log_date,
            log->'lead' as lead_data,
            -- Get quotations for this log
            (
                SELECT jsonb_agg(q)
                FROM jsonb_array_elements(v_quotations) AS q
                WHERE (q->>'productivity_log_id')::INTEGER = (log->>'log_id')::INTEGER
            ) as log_quotations
        FROM jsonb_array_elements(v_sales_logs) AS log
    ),
    deduplicated_logs AS (
        SELECT 
            log_id,
            lead_id,
            sale_id,
            log_date,
            lead_data,
            -- Deduplicate quotations by normalized document_number within each log
            -- Keep only the latest quotation per document_number
            (
                SELECT jsonb_agg(q ORDER BY (q->>'created_at_thai')::timestamp DESC)
                FROM (
                    SELECT DISTINCT ON (LOWER(REPLACE(q->>'document_number', ' ', ''))) q
                    FROM jsonb_array_elements(log_quotations) AS q
                    WHERE q->>'document_number' IS NOT NULL
                    AND q->>'document_number' != ''
                    ORDER BY LOWER(REPLACE(q->>'document_number', ' ', '')), (q->>'created_at_thai')::timestamp DESC
                ) AS unique_q
            ) as unique_quotations
        FROM sales_logs_with_quotations
        WHERE log_quotations IS NOT NULL
        AND jsonb_array_length(log_quotations) > 0
    )
    SELECT jsonb_agg(
        jsonb_build_object(
            'leadId', lead_id,
            'logId', log_id,
            'saleId', sale_id,
            'displayName', lead_data->>'display_name',
            'fullName', lead_data->>'full_name',
            'category', lead_data->>'category',
            'platform', lead_data->>'platform',
            'tel', lead_data->>'tel',
            'lineId', lead_data->>'line_id',
            'is_from_ppa_project', COALESCE((lead_data->>'is_from_ppa_project')::BOOLEAN, false),
            'saleOwnerId', (lead_data->>'sale_owner_id')::INTEGER,
            'lastActivityDate', log_date,
            'totalQuotationAmount', COALESCE((
                SELECT SUM((q->>'amount')::NUMERIC)
                FROM jsonb_array_elements(unique_quotations) AS q
            ), 0),
            'totalQuotationCount', COALESCE(jsonb_array_length(unique_quotations), 0),
            'quotationNumbers', COALESCE((
                SELECT jsonb_agg(q->>'document_number')
                FROM jsonb_array_elements(unique_quotations) AS q
                WHERE q->>'document_number' IS NOT NULL
            ), '[]'::jsonb),
            'quotationDocuments', COALESCE(unique_quotations, '[]'::jsonb)
        )
    ) INTO v_sales_leads
    FROM deduplicated_logs;
    
    IF v_sales_leads IS NULL THEN
        v_sales_leads := '[]'::jsonb;
    END IF;
    
    -- Step 4: คำนวณ totalSalesValue และ salesCount
    SELECT 
        COALESCE(SUM((lead->>'totalQuotationAmount')::NUMERIC), 0),
        COALESCE(SUM((lead->>'totalQuotationCount')::INTEGER), 0)
    INTO v_total_sales_value, v_sales_count
    FROM jsonb_array_elements(v_sales_leads) AS lead;
    
    -- Build result
    v_result := jsonb_build_object(
        'success', true,
        'data', jsonb_build_object(
            'salesLeads', v_sales_leads,
            'salesLogs', v_sales_logs,
            'quotations', v_quotations,
            'totalSalesValue', v_total_sales_value,
            'salesCount', v_sales_count
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

-- Grant execute permission
GRANT EXECUTE ON FUNCTION ai_get_sales_closed(UUID, TIMESTAMP WITH TIME ZONE, TIMESTAMP WITH TIME ZONE, INTEGER, TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION ai_get_sales_closed(UUID, TIMESTAMP WITH TIME ZONE, TIMESTAMP WITH TIME ZONE, INTEGER, TEXT) TO anon;
