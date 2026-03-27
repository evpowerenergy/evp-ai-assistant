-- Drop unused RPC functions that are no longer exposed in AI flow.
-- Safe to run multiple times.

DROP FUNCTION IF EXISTS ai_get_my_leads(UUID, TEXT, JSONB, DATE, DATE, TEXT);
DROP FUNCTION IF EXISTS ai_get_user_info(UUID, JSONB, INTEGER);
DROP FUNCTION IF EXISTS ai_get_lead_status(TEXT, UUID);
DROP FUNCTION IF EXISTS ai_get_lead_management(UUID, TEXT, BOOLEAN, BOOLEAN, BOOLEAN, DATE, DATE, INTEGER, TEXT);
