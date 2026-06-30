-- RAG eval cases (extends prompt_test_cases if table exists)

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'prompt_test_cases'
    ) THEN
        INSERT INTO public.prompt_test_cases (user_message, expected_intent, expected_tool, notes)
        VALUES
            ('ขั้นตอนการขอลามีอะไรบ้าง', 'rag_query', NULL, 'RAG eval: HR policy'),
            ('นโยบายการลาป่วยเป็นอย่างไร', 'rag_query', NULL, 'RAG eval: policy'),
            ('วิธีใช้งานระบบ CRM สำหรับลีดใหม่', 'rag_query', NULL, 'RAG eval: manual'),
            ('SOP การปิดการขายมีขั้นตอนอะไร', 'rag_query', NULL, 'RAG eval: SOP'),
            ('คู่มือการอนุมัติใบเสนอราคา', 'rag_query', NULL, 'RAG eval: manual'),
            ('procedure onboarding พนักงานใหม่', 'rag_query', NULL, 'RAG eval: EN keyword'),
            ('รายละเอียด QT2026030013', 'db_query', 'get_sales_docs', 'RAG negative: sales doc'),
            ('ใบแจ้งหนี้เดือนนี้มีอะไรบ้าง', 'db_query', 'get_sales_docs', 'RAG negative: invoice'),
            ('ลีดวันนี้มีกี่ราย', 'db_query', 'search_leads', 'RAG negative: leads'),
            ('ยอดขายเดือนนี้เท่าไหร่', 'db_query', 'get_sales_closed', 'RAG negative: sales'),
            ('เอกสารการขาย QT ล่าสุด', 'db_query', 'get_sales_docs', 'RAG negative: เอกสารการขาย'),
            ('ปิดการขายได้กี่รายเดือนนี้', 'db_query', 'get_sales_closed', 'RAG negative'),
            ('ทีมขาย KPI เดือนนี้', 'db_query', 'get_sales_team_overview', 'RAG negative'),
            ('Marketing dashboard ROAS', 'db_query', 'get_marketing_dashboard', 'RAG negative'),
            ('นัดหมายวันนี้', 'db_query', 'get_appointments', 'RAG negative'),
            ('Permit requests สถานะ', 'db_query', 'get_permit_requests', 'RAG negative'),
            ('แนวทางการติดตามลูกค้าหลังขาย package', 'rag_query', NULL, 'RAG eval'),
            ('กระบวนการอนุมัติส่วนลดพิเศษ', 'rag_query', NULL, 'RAG eval'),
            ('วิธีสร้างใบเสนอราคาในระบบ', 'rag_query', NULL, 'RAG eval: how-to'),
            ('ขั้นตอนการเบิกค่าใช้จ่าย', 'rag_query', NULL, 'RAG eval')
        ON CONFLICT DO NOTHING;
    END IF;
END $$;
