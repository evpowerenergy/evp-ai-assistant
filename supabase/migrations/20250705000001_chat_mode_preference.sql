-- Shared chat mode preference (web + LINE): crm | kb

ALTER TABLE public.user_chat_preferences
    ADD COLUMN IF NOT EXISTS chat_mode TEXT NOT NULL DEFAULT 'crm'
        CHECK (chat_mode IN ('crm', 'kb'));
