-- Seed marketing routing prompt test cases for admin /admin/prompt-tests regression
-- Migration: 20250601000001_seed_marketing_prompt_test_cases.sql

INSERT INTO prompt_test_cases (user_message, expected_intent, expected_tool, notes)
SELECT * FROM (VALUES
  -- Positive: should route to get_marketing_dashboard
  ('ROAS เดือนนี้เท่าไหร่', 'db_query', 'get_marketing_dashboard', 'marketing-routing: ROAS'),
  ('งบ Facebook Ads ฝั่ง Package เดือนนี้', 'db_query', 'get_marketing_dashboard', 'marketing-routing: Facebook Ads budget'),
  ('Marketing dashboard วันนี้', 'db_query', 'get_marketing_dashboard', 'marketing-routing: dashboard today'),
  ('Inbox จาก Ads วันนี้กี่ราย', 'db_query', 'get_marketing_dashboard', 'marketing-routing: inbox from ads'),
  ('Win Rate QT ฝั่ง Wholesales', 'db_query', 'get_marketing_dashboard', 'marketing-routing: win rate QT'),
  ('Conversion Rate Lead เดือนนี้', 'db_query', 'get_marketing_dashboard', 'marketing-routing: conversion rate'),
  ('ค่า Ads ต่อ Lead แยก Package/Wholesales', 'db_query', 'get_marketing_dashboard', 'marketing-routing: cost per lead'),
  ('Lead ใหม่ Package เดือนนี้กี่ราย', 'db_query', 'get_marketing_dashboard', 'marketing-routing: new leads package'),
  ('โฆษณาใช้เงินไปเท่าไหร่เดือนนี้', 'db_query', 'get_marketing_dashboard', 'marketing-routing: Thai ads spend'),
  ('Google Ads งบเท่าไหร่เดือนนี้', 'db_query', 'get_marketing_dashboard', 'marketing-routing: Google Ads budget'),
  ('แคมเปญโฆษณา ROAS เดือนนี้', 'db_query', 'get_marketing_dashboard', 'marketing-routing: campaign ROAS'),
  ('หน้า marketing ยอดขาย Package เดือนนี้', 'db_query', 'get_marketing_dashboard', 'marketing-routing: marketing page sales'),
  ('วันนี้ยิงแอดไปเท่าไหร่', 'db_query', 'get_marketing_dashboard', 'marketing-routing: Thai slang ยิงแอด'),
  ('งบแอดวันนี้', 'db_query', 'get_marketing_dashboard', 'marketing-routing: งบแอด today'),
  -- Negative: should NOT route to get_marketing_dashboard
  ('ลีดวันนี้มีกี่ราย', 'db_query', 'search_leads', 'marketing-routing-negative: leads count'),
  ('ยอดขายที่ปิดแล้วเดือนนี้', 'db_query', 'get_sales_closed', 'marketing-routing-negative: sales closed'),
  ('ทีมขาย KPI เดือนนี้', 'db_query', 'get_sales_team_overview', 'marketing-routing-negative: team KPI')
) AS v(user_message, expected_intent, expected_tool, notes)
WHERE NOT EXISTS (
  SELECT 1 FROM prompt_test_cases p WHERE p.user_message = v.user_message
);
