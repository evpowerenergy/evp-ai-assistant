-- Prompt E2E Test System
-- Migration: 20250213000001_create_prompt_test_tables.sql

-- Test Cases: user_message, expected values, metadata
CREATE TABLE IF NOT EXISTS prompt_test_cases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_message TEXT NOT NULL,
    expected_intent TEXT,
    expected_tool TEXT,
    expected_message TEXT,
    similarity_threshold DECIMAL(3,2) DEFAULT 0.70,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Test Runs: batch execution metadata
CREATE TABLE IF NOT EXISTS prompt_test_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    total INTEGER NOT NULL DEFAULT 0,
    passed INTEGER NOT NULL DEFAULT 0,
    failed INTEGER NOT NULL DEFAULT 0,
    run_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    notes TEXT
);

-- Test Results: per-case result for each run
CREATE TABLE IF NOT EXISTS prompt_test_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID NOT NULL REFERENCES prompt_test_runs(id) ON DELETE CASCADE,
    test_case_id UUID NOT NULL REFERENCES prompt_test_cases(id) ON DELETE CASCADE,
    actual_intent TEXT,
    actual_tool TEXT,
    ai_message TEXT,
    similarity_score DECIMAL(5,4),
    pass_fail TEXT NOT NULL CHECK (pass_fail IN ('pass', 'fail')),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prompt_test_results_run_id ON prompt_test_results(run_id);
CREATE INDEX IF NOT EXISTS idx_prompt_test_results_test_case_id ON prompt_test_results(test_case_id);
CREATE INDEX IF NOT EXISTS idx_prompt_test_runs_run_at ON prompt_test_runs(run_at DESC);

-- RLS
ALTER TABLE prompt_test_cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE prompt_test_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE prompt_test_results ENABLE ROW LEVEL SECURITY;

-- Backend uses service role key and bypasses RLS.
-- Permissive policies for any direct access (e.g. admin tools):
CREATE POLICY "Allow all for prompt_test_cases" ON prompt_test_cases FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for prompt_test_runs" ON prompt_test_runs FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for prompt_test_results" ON prompt_test_results FOR ALL USING (true) WITH CHECK (true);
