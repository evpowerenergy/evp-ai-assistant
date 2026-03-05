-- Create RPC: ai_get_sales_unsuccessful (ตรงกับ /reports/sales-unsuccessful)
-- Reference: getUnsuccessfulSalesDataInPeriod in salesUtils.ts

CREATE OR REPLACE FUNCTION ai_get_sales_unsuccessful(
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
    v_logs JSONB;
    v_quotations JSONB;
    v_leads JSONB;
    v_total_val NUMERIC := 0;
    v_count INTEGER := 0;
    v_log_ids INTEGER[];
BEGIN
    SELECT jsonb_agg(row_data) INTO v_logs FROM (
        SELECT jsonb_build_object(
            'log_id', lpl.id, 'lead_id', lpl.lead_id, 'sale_id', lpl.sale_id,
            'created_at_thai', lpl.created_at_thai,
            'lead', jsonb_build_object('id', l.id, 'sale_owner_id', l.sale_owner_id,
                'category', l.category, 'platform', l.platform, 'full_name', l.full_name,
                'display_name', l.display_name, 'tel', l.tel, 'line_id', l.line_id, 'status', l.status)
        ) AS row_data
        FROM lead_productivity_logs lpl
        INNER JOIN leads l ON l.id = lpl.lead_id
        WHERE lpl.status = 'ปิดการขายไม่สำเร็จ'
        AND ((p_date_from IS NULL AND p_date_to IS NULL)
            OR (lpl.created_at_thai IS NOT NULL
                AND lpl.created_at_thai >= COALESCE(p_date_from, '1900-01-01'::timestamptz)
                AND lpl.created_at_thai <= COALESCE(p_date_to, '2100-12-31'::timestamptz)))
        AND (p_sales_member_id IS NULL OR lpl.sale_id = p_sales_member_id)
        ORDER BY lpl.created_at_thai DESC
    ) x;
    IF v_logs IS NULL THEN v_logs := '[]'::jsonb; END IF;

    SELECT COUNT(DISTINCT (log->>'lead_id')::INTEGER) INTO v_count
    FROM jsonb_array_elements(v_logs) AS log WHERE (log->>'lead_id')::INTEGER IS NOT NULL;

    SELECT ARRAY_AGG(DISTINCT (log->>'log_id')::INTEGER) INTO v_log_ids
    FROM jsonb_array_elements(v_logs) AS log WHERE (log->>'log_id')::INTEGER IS NOT NULL;

    IF v_log_ids IS NOT NULL AND array_length(v_log_ids, 1) > 0 THEN
        SELECT jsonb_agg(jsonb_build_object('id', qd.id, 'productivity_log_id', qd.productivity_log_id,
            'document_number', qd.document_number, 'amount', qd.amount, 'created_at_thai', qd.created_at_thai))
        INTO v_quotations
        FROM quotation_documents qd
        WHERE qd.productivity_log_id = ANY(v_log_ids) AND qd.document_type::text = 'quotation';
    END IF;
    IF v_quotations IS NULL THEN v_quotations := '[]'::jsonb; END IF;

    WITH logs_q AS (
        SELECT (log->>'log_id')::INTEGER AS log_id, (log->>'lead_id')::INTEGER AS lead_id,
            (log->>'sale_id')::INTEGER AS sale_id, log->>'created_at_thai' AS log_date, log->'lead' AS lead_data,
            (SELECT jsonb_agg(q) FROM jsonb_array_elements(v_quotations) q
             WHERE (q->>'productivity_log_id')::INTEGER = (log->>'log_id')::INTEGER) AS log_q
        FROM jsonb_array_elements(v_logs) AS log
    ),
    dedup AS (
        SELECT log_id, lead_id, sale_id, log_date, lead_data,
            COALESCE((SELECT jsonb_agg(uq.q ORDER BY (uq.q->>'created_at_thai')::timestamp DESC)
                FROM (SELECT DISTINCT ON (LOWER(REPLACE(COALESCE(q->>'document_number',''),' ',''))) q
                    FROM jsonb_array_elements(COALESCE(log_q,'[]'::jsonb)) q
                    WHERE q->>'document_number' IS NOT NULL AND q->>'document_number' != ''
                    ORDER BY LOWER(REPLACE(COALESCE(q->>'document_number',''),' ','')), (q->>'created_at_thai')::timestamp DESC
                ) uq(q)), '[]'::jsonb) AS uq
        FROM logs_q
    )
    SELECT jsonb_agg(jsonb_build_object(
        'leadId', lead_id, 'logId', log_id, 'saleId', sale_id,
        'displayName', lead_data->>'display_name', 'fullName', lead_data->>'full_name',
        'category', lead_data->>'category', 'platform', lead_data->>'platform',
        'tel', lead_data->>'tel', 'lineId', lead_data->>'line_id', 'leadStatus', lead_data->>'status',
        'saleOwnerId', (lead_data->>'sale_owner_id')::INTEGER, 'lastActivityDate', log_date,
        'totalQuotationAmount', COALESCE((SELECT SUM((q->>'amount')::NUMERIC) FROM jsonb_array_elements(uq) q), 0),
        'totalQuotationCount', COALESCE(jsonb_array_length(uq), 0),
        'quotationNumbers', COALESCE((SELECT jsonb_agg(q->>'document_number') FROM jsonb_array_elements(uq) q WHERE q->>'document_number' IS NOT NULL), '[]'::jsonb),
        'quotationDocuments', COALESCE(uq, '[]'::jsonb)
    )) INTO v_leads FROM dedup;
    IF v_leads IS NULL THEN v_leads := '[]'::jsonb; END IF;

    SELECT COALESCE(SUM((l->>'totalQuotationAmount')::NUMERIC), 0) INTO v_total_val
    FROM jsonb_array_elements(v_leads) l;

    v_result := jsonb_build_object('success', true, 'data', jsonb_build_object(
        'unsuccessfulLeads', v_leads, 'unsuccessfulLogs', v_logs, 'quotations', v_quotations,
        'unsuccessfulCount', v_count, 'totalQuotationValue', v_total_val));
    RETURN v_result;
EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object('success', false, 'error', true, 'message', SQLERRM);
END;
$$;

GRANT EXECUTE ON FUNCTION ai_get_sales_unsuccessful(UUID, TIMESTAMP WITH TIME ZONE, TIMESTAMP WITH TIME ZONE, INTEGER, TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION ai_get_sales_unsuccessful(UUID, TIMESTAMP WITH TIME ZONE, TIMESTAMP WITH TIME ZONE, INTEGER, TEXT) TO anon;
