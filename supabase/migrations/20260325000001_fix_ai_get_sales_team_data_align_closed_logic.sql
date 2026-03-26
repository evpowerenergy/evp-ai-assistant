-- Fix: Align ai_get_sales_team_data closed-sale metrics with ai_get_sales_closed
-- Date: 2026-03-25
-- Goal:
-- 1) Use the same closed success conditions as ai_get_sales_closed
-- 2) Use quotation_documents + quotation-only filter
-- 3) Dedupe quotations by normalized document_number per productivity log
-- 4) Compute per-member deals_closed and pipeline_value from the same base

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
    v_sales_team JSONB;
    v_all_leads JSONB;
    v_quotations JSONB;
BEGIN
    -- Active sales team
    SELECT jsonb_agg(to_jsonb(st.*)) INTO v_sales_team
    FROM sales_team_with_user_info st
    WHERE st.status = 'active';

    IF v_sales_team IS NULL THEN
        v_sales_team := '[]'::jsonb;
    END IF;

    -- Keep lead list behavior for compatibility (used by existing UI/reporting)
    WITH sales_owner_ids AS (
        SELECT ARRAY_AGG((member->>'id')::INTEGER) AS owner_ids
        FROM jsonb_array_elements(v_sales_team) AS member
    )
    SELECT jsonb_agg(to_jsonb(l.*)) INTO v_all_leads
    FROM leads l
    CROSS JOIN sales_owner_ids so
    WHERE l.is_archived = false
      AND l.has_contact_info = true
      AND (
        l.sale_owner_id = ANY(COALESCE(so.owner_ids, ARRAY[]::INTEGER[]))
        OR l.post_sales_owner_id = ANY(COALESCE(so.owner_ids, ARRAY[]::INTEGER[]))
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

    IF v_all_leads IS NULL THEN
        v_all_leads := '[]'::jsonb;
    END IF;

    -- Raw quotations list for compatibility (already deduped using closed logic)
    WITH sales_owner_ids AS (
        SELECT ARRAY_AGG((member->>'id')::INTEGER) AS owner_ids
        FROM jsonb_array_elements(v_sales_team) AS member
    ),
    closed_logs AS (
        SELECT
            lpl.id AS log_id,
            lpl.sale_id
        FROM lead_productivity_logs lpl
        CROSS JOIN sales_owner_ids so
        WHERE lpl.status = 'ปิดการขายแล้ว'
          AND (
              lpl.sale_chance_status = 'win'
              OR (
                  lpl.sale_chance_status = 'win + สินเชื่อ'
                  AND lpl.credit_approval_status = 'อนุมัติ'
              )
          )
          AND lpl.sale_id = ANY(COALESCE(so.owner_ids, ARRAY[]::INTEGER[]))
          AND (
            (p_date_from IS NULL AND p_date_to IS NULL)
            OR (
              lpl.created_at_thai IS NOT NULL
              AND (lpl.created_at_thai::text::timestamp)::date BETWEEN
                  COALESCE(p_date_from, '1900-01-01'::date) AND
                  COALESCE(p_date_to, '2100-12-31'::date)
            )
          )
    ),
    dedup_q AS (
        SELECT DISTINCT ON (
            qd.productivity_log_id,
            LOWER(REPLACE(COALESCE(qd.document_number, ''), ' ', ''))
        )
            to_jsonb(qd.*) AS q_json
        FROM quotation_documents qd
        JOIN closed_logs cl
          ON cl.log_id = qd.productivity_log_id
        WHERE qd.document_type::text = 'quotation'
          AND COALESCE(TRIM(qd.document_number), '') != ''
        ORDER BY
            qd.productivity_log_id,
            LOWER(REPLACE(COALESCE(qd.document_number, ''), ' ', '')),
            qd.created_at_thai DESC
    )
    SELECT jsonb_agg(q_json) INTO v_quotations
    FROM dedup_q;

    IF v_quotations IS NULL THEN
        v_quotations := '[]'::jsonb;
    END IF;

    -- Build per-member metrics with same closed logic as ai_get_sales_closed
    WITH members AS (
        SELECT
            (member->>'id')::INTEGER AS member_id,
            member AS member_json
        FROM jsonb_array_elements(v_sales_team) AS member
    ),
    total_leads_per_member AS (
        SELECT
            m.member_id,
            COUNT(*) FILTER (WHERE lead.lead_json IS NOT NULL)::INTEGER AS total_leads
        FROM members m
        LEFT JOIN jsonb_array_elements(v_all_leads) AS lead(lead_json) ON (
            (lead.lead_json->>'sale_owner_id')::INTEGER = m.member_id
            OR (lead.lead_json->>'post_sales_owner_id')::INTEGER = m.member_id
        )
        GROUP BY m.member_id
    ),
    closed_logs AS (
        SELECT
            lpl.id AS log_id,
            lpl.sale_id
        FROM lead_productivity_logs lpl
        JOIN members m
          ON m.member_id = lpl.sale_id
        WHERE lpl.status = 'ปิดการขายแล้ว'
          AND (
              lpl.sale_chance_status = 'win'
              OR (
                  lpl.sale_chance_status = 'win + สินเชื่อ'
                  AND lpl.credit_approval_status = 'อนุมัติ'
              )
          )
          AND (
            (p_date_from IS NULL AND p_date_to IS NULL)
            OR (
              lpl.created_at_thai IS NOT NULL
              AND (lpl.created_at_thai::text::timestamp)::date BETWEEN
                  COALESCE(p_date_from, '1900-01-01'::date) AND
                  COALESCE(p_date_to, '2100-12-31'::date)
            )
          )
    ),
    dedup_quotation_per_log AS (
        SELECT DISTINCT ON (
            qd.productivity_log_id,
            LOWER(REPLACE(COALESCE(qd.document_number, ''), ' ', ''))
        )
            qd.productivity_log_id,
            COALESCE(qd.amount, 0)::NUMERIC AS amount
        FROM quotation_documents qd
        JOIN closed_logs cl
          ON cl.log_id = qd.productivity_log_id
        WHERE qd.document_type::text = 'quotation'
          AND COALESCE(TRIM(qd.document_number), '') != ''
        ORDER BY
            qd.productivity_log_id,
            LOWER(REPLACE(COALESCE(qd.document_number, ''), ' ', '')),
            qd.created_at_thai DESC
    ),
    per_log_metrics AS (
        SELECT
            cl.sale_id AS member_id,
            cl.log_id,
            COUNT(dq.productivity_log_id)::INTEGER AS qt_count,
            COALESCE(SUM(dq.amount), 0)::NUMERIC AS qt_amount
        FROM closed_logs cl
        LEFT JOIN dedup_quotation_per_log dq
          ON dq.productivity_log_id = cl.log_id
        GROUP BY cl.sale_id, cl.log_id
    ),
    per_member_closed AS (
        SELECT
            pl.member_id,
            COALESCE(SUM(pl.qt_count), 0)::INTEGER AS deals_closed,
            COALESCE(SUM(pl.qt_amount), 0)::NUMERIC AS pipeline_value
        FROM per_log_metrics pl
        GROUP BY pl.member_id
    )
    SELECT jsonb_agg(
        jsonb_set(
            jsonb_set(
                jsonb_set(
                    jsonb_set(
                        m.member_json,
                        '{deals_closed}',
                        to_jsonb(COALESCE(pmc.deals_closed, 0))
                    ),
                    '{pipeline_value}',
                    to_jsonb(COALESCE(pmc.pipeline_value, 0))
                ),
                '{conversion_rate}',
                to_jsonb(
                    CASE
                        WHEN COALESCE(tl.total_leads, 0) > 0 THEN
                            ROUND((COALESCE(pmc.deals_closed, 0)::NUMERIC / tl.total_leads::NUMERIC) * 100, 2)
                        ELSE 0
                    END
                )
            ),
            '{total_leads}',
            to_jsonb(COALESCE(tl.total_leads, 0))
        )
    ) INTO v_sales_team
    FROM members m
    LEFT JOIN total_leads_per_member tl
      ON tl.member_id = m.member_id
    LEFT JOIN per_member_closed pmc
      ON pmc.member_id = m.member_id;

    IF v_sales_team IS NULL THEN
        v_sales_team := '[]'::jsonb;
    END IF;

    RETURN jsonb_build_object(
        'success', true,
        'data', jsonb_build_object(
            'salesTeam', v_sales_team,
            'leads', v_all_leads,
            'quotations', v_quotations
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

GRANT EXECUTE ON FUNCTION ai_get_sales_team_data(UUID, DATE, DATE, TEXT) TO authenticated;
