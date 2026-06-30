-- LINE Integration: link codes + shared session preferences
-- Migration: 20250629000001_line_integration.sql

CREATE TABLE IF NOT EXISTS line_link_codes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    code TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_line_link_codes_code_active
    ON line_link_codes (code)
    WHERE used_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_line_link_codes_user_id ON line_link_codes(user_id);
CREATE INDEX IF NOT EXISTS idx_line_link_codes_expires_at ON line_link_codes(expires_at);

CREATE TABLE IF NOT EXISTS user_chat_preferences (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    active_session_id UUID REFERENCES chat_sessions(id) ON DELETE SET NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_chat_preferences_session
    ON user_chat_preferences(active_session_id);

ALTER TABLE line_link_codes ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_chat_preferences ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own link codes"
    ON line_link_codes FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own link codes"
    ON line_link_codes FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can view their own chat preferences"
    ON user_chat_preferences FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own chat preferences"
    ON user_chat_preferences FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own chat preferences"
    ON user_chat_preferences FOR UPDATE
    USING (auth.uid() = user_id);
