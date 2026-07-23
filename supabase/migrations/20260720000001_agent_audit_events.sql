-- Structured, request-correlated audit timeline for Hermes/LangGraph runs.
-- This migration is intentionally additive and can be applied after
-- 20260719000001_agent_runtime_audit.sql.

ALTER TABLE ai_agent_runs
    ADD COLUMN IF NOT EXISTS trace_id UUID,
    ADD COLUMN IF NOT EXISTS parent_run_id UUID REFERENCES ai_agent_runs(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS request_type TEXT,
    ADD COLUMN IF NOT EXISTS primary_status TEXT NOT NULL DEFAULT 'queued',
    ADD COLUMN IF NOT EXISTS fallback_engine TEXT,
    ADD COLUMN IF NOT EXISTS fallback_status TEXT,
    ADD COLUMN IF NOT EXISTS fallback_reason TEXT,
    ADD COLUMN IF NOT EXISTS timeout_seconds INTEGER,
    ADD COLUMN IF NOT EXISTS timed_out_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS late_completion BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS late_completed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS response_source TEXT,
    ADD COLUMN IF NOT EXISTS response_message_id UUID,
    ADD COLUMN IF NOT EXISTS hermes_session_id TEXT,
    ADD COLUMN IF NOT EXISTS input_chars INTEGER,
    ADD COLUMN IF NOT EXISTS output_chars INTEGER,
    ADD COLUMN IF NOT EXISTS total_tool_calls INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS total_skill_calls INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS total_model_calls INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS estimated_cost_usd NUMERIC,
    ADD COLUMN IF NOT EXISTS last_event_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS ai_agent_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID NOT NULL REFERENCES ai_agent_runs(id) ON DELETE CASCADE,
    request_id UUID NOT NULL,
    sequence_no BIGINT NOT NULL,
    event_type TEXT NOT NULL CHECK (
        event_type IN ('run', 'engine', 'model', 'skill', 'subagent', 'tool',
                       'mcp', 'fallback', 'response', 'security', 'artifact')
    ),
    event_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('queued', 'started', 'running', 'completed', 'failed',
                   'timed_out', 'cancelled', 'skipped', 'completed_late')
    ),
    actor_type TEXT,
    actor_id TEXT,
    parent_actor_id TEXT,
    duration_ms INTEGER,
    model TEXT,
    metadata JSONB NOT NULL DEFAULT '{}',
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (run_id, sequence_no)
);

ALTER TABLE ai_tool_executions
    ADD COLUMN IF NOT EXISTS engine TEXT,
    ADD COLUMN IF NOT EXISTS actor_id TEXT,
    ADD COLUMN IF NOT EXISTS parent_actor_id TEXT,
    ADD COLUMN IF NOT EXISTS scope TEXT,
    ADD COLUMN IF NOT EXISTS http_status INTEGER,
    ADD COLUMN IF NOT EXISTS failure_code TEXT,
    ADD COLUMN IF NOT EXISTS token_age_seconds INTEGER,
    ADD COLUMN IF NOT EXISTS token_expires_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS attempt INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS provider TEXT,
    ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS ai_agent_artifacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID NOT NULL REFERENCES ai_agent_runs(id) ON DELETE CASCADE,
    artifact_type TEXT NOT NULL,
    filename TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    mime_type TEXT,
    size_bytes BIGINT,
    status TEXT NOT NULL DEFAULT 'created'
        CHECK (status IN ('created', 'uploaded', 'failed', 'deleted')),
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_agent_runs_status_created
    ON ai_agent_runs(primary_status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_agent_runs_trace
    ON ai_agent_runs(trace_id);
CREATE INDEX IF NOT EXISTS idx_ai_agent_events_run_sequence
    ON ai_agent_events(run_id, sequence_no);
CREATE INDEX IF NOT EXISTS idx_ai_agent_events_request_time
    ON ai_agent_events(request_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_ai_agent_events_type_time
    ON ai_agent_events(event_type, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_tool_executions_failure
    ON ai_tool_executions(failure_code, created_at DESC)
    WHERE failure_code IS NOT NULL;

ALTER TABLE ai_agent_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_agent_artifacts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view events for their own agent runs"
    ON ai_agent_events FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM ai_agent_runs run
            WHERE run.id = ai_agent_events.run_id
              AND run.user_id = auth.uid()
        )
    );
CREATE POLICY "Users can view artifacts for their own agent runs"
    ON ai_agent_artifacts FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM ai_agent_runs run
            WHERE run.id = ai_agent_artifacts.run_id
              AND run.user_id = auth.uid()
        )
    );
