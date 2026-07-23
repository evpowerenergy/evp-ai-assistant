-- Hermes/LangGraph runtime observability and idempotent tool execution.

CREATE TABLE IF NOT EXISTS ai_agent_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    request_id UUID NOT NULL UNIQUE,
    session_id UUID REFERENCES chat_sessions(id) ON DELETE SET NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    source TEXT NOT NULL CHECK (source IN ('web', 'line', 'system', 'test')),
    primary_engine TEXT NOT NULL,
    actual_engine TEXT,
    model TEXT,
    status TEXT NOT NULL CHECK (status IN ('started', 'completed', 'failed', 'cancelled')),
    fallback_used BOOLEAN NOT NULL DEFAULT FALSE,
    shadow BOOLEAN NOT NULL DEFAULT FALSE,
    usage JSONB NOT NULL DEFAULT '{}',
    timings JSONB NOT NULL DEFAULT '{}',
    error_class TEXT,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS ai_tool_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID REFERENCES ai_agent_runs(id) ON DELETE CASCADE,
    request_id UUID NOT NULL,
    tool_call_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    risk_level TEXT NOT NULL DEFAULT 'read'
        CHECK (risk_level IN ('read', 'generate', 'write', 'external')),
    status TEXT NOT NULL CHECK (status IN ('started', 'completed', 'failed', 'unknown')),
    input_data JSONB NOT NULL DEFAULT '{}',
    output_data JSONB,
    duration_ms INTEGER,
    idempotency_key TEXT,
    error_class TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    UNIQUE (request_id, tool_call_id)
);

CREATE INDEX IF NOT EXISTS idx_ai_agent_runs_user_created
    ON ai_agent_runs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_agent_runs_session_created
    ON ai_agent_runs(session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_tool_executions_run
    ON ai_tool_executions(run_id, created_at);

ALTER TABLE ai_agent_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_tool_executions ENABLE ROW LEVEL SECURITY;

-- Backend writes with the service role. Authenticated users may only inspect
-- their own run metadata; raw tool execution data remains backend/admin only.
CREATE POLICY "Users can view their own agent runs"
    ON ai_agent_runs FOR SELECT
    USING (auth.uid() = user_id);
