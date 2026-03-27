-- =============================================================================
-- Function: ai_get_qt_doc_detail
-- =============================================================================
-- QT document detail for assistant use-cases:
-- - filter by document number (exact/partial)
-- - include customer + sales owner + lead status + amount
-- - keep response shape aligned with get_sales_docs formatter
CREATE OR REPLACE FUNCTION ai_get_qt_doc_detail(
    p_user_id UUID,
    p_document_number TEXT DEFAULT NULL,
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
    v_docs JSONB;
    v_result JSONB;
    v_source_total INTEGER;
BEGIN
    -- Count source rows after filters (for meta/stats)
    SELECT COUNT(*) INTO v_source_total
    FROM quotation_documents qd
    LEFT JOIN lead_productivity_logs lpl ON lpl.id = qd.productivity_log_id
    WHERE (
        COALESCE(TRIM(qd.document_type), '') = ''
        OR LOWER(TRIM(qd.document_type)) IN ('quotation', 'qt')
    )
    AND (
        p_document_number IS NULL
        OR LOWER(COALESCE(qd.document_number, '')) LIKE '%' || LOWER(p_document_number) || '%'
    )
    AND (
        (p_date_from IS NULL AND p_date_to IS NULL)
        OR (
            lpl.created_at_thai::date BETWEEN
            COALESCE(p_date_from, DATE '1900-01-01')
            AND COALESCE(p_date_to, DATE '2100-12-31')
        )
    );

    -- Main payload rows
    SELECT COALESCE(
        jsonb_agg(
            jsonb_build_object(
                'id', qd.id,
                'doc_number', qd.document_number,
                'doc_type', 'QT',
                'doc_date', lpl.created_at_thai,
                'total_amount', qd.amount,
                'lead_id', lpl.lead_id,
                'customer_name', l.display_name,
                'lead_status', l.status,
                'sale_id', lpl.sale_id,
                'sale_name', st.name,
                'sale_email', st.email,
                'sale_phone', st.phone,
                'productivity_log_id', qd.productivity_log_id,
                'source', 'ai_get_qt_doc_detail'
            )
            ORDER BY lpl.created_at_thai DESC NULLS LAST, qd.id DESC
        ),
        '[]'::jsonb
    ) INTO v_docs
    FROM (
        SELECT *
        FROM quotation_documents
        WHERE (
            COALESCE(TRIM(document_type), '') = ''
            OR LOWER(TRIM(document_type)) IN ('quotation', 'qt')
        )
        AND (
            p_document_number IS NULL
            OR LOWER(COALESCE(document_number, '')) LIKE '%' || LOWER(p_document_number) || '%'
        )
        ORDER BY id DESC
        LIMIT GREATEST(COALESCE(p_limit, 100), 1)
    ) qd
    LEFT JOIN lead_productivity_logs lpl ON lpl.id = qd.productivity_log_id
    LEFT JOIN leads l ON l.id = lpl.lead_id
    LEFT JOIN sales_team_with_user_info st ON st.id = lpl.sale_id
    WHERE (
        (p_date_from IS NULL AND p_date_to IS NULL)
        OR (
            lpl.created_at_thai::date BETWEEN
            COALESCE(p_date_from, DATE '1900-01-01')
            AND COALESCE(p_date_to, DATE '2100-12-31')
        )
    );

    v_result := jsonb_build_object(
        'success', true,
        'data', jsonb_build_object(
            'sales_docs', v_docs,
            'stats', jsonb_build_object(
                'returned', jsonb_array_length(v_docs),
                'source_total', v_source_total
            )
        ),
        'meta', jsonb_build_object(
            'source_rpc', 'ai_get_qt_doc_detail',
            'document_number_filter', p_document_number,
            'doc_type_filter', 'QT',
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

GRANT EXECUTE ON FUNCTION ai_get_qt_doc_detail(UUID, TEXT, DATE, DATE, INTEGER) TO authenticated;
