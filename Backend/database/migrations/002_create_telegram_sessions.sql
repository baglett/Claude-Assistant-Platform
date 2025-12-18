-- ============================================================================
-- Migration: 002_create_telegram_sessions.sql
-- Description: Creates the telegram_sessions table to map Telegram chat IDs
--              to internal chat sessions.
-- ============================================================================

-- ============================================================================
-- Table: messaging.telegram_sessions
-- Description: Maps Telegram chat IDs to internal chat UUIDs. Allows users
--              to create new chat sessions via /new command while maintaining
--              the Telegram chat ID association.
-- ============================================================================
CREATE TABLE messaging.telegram_sessions (
    -- Primary key: Telegram chat ID (unique per Telegram chat)
    telegram_chat_id BIGINT PRIMARY KEY,

    -- The Telegram user ID who owns this session
    telegram_user_id BIGINT NOT NULL,

    -- Foreign key to the current active chat session
    active_chat_id UUID NOT NULL REFERENCES messaging.chats(id) ON DELETE CASCADE,

    -- Timestamp when the session was created
    created_on TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Timestamp when the session was last used or modified
    modified_on TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Index on telegram_user_id for user-based queries
CREATE INDEX idx_telegram_sessions_user_id ON messaging.telegram_sessions (telegram_user_id);

-- Index on active_chat_id for reverse lookups
CREATE INDEX idx_telegram_sessions_chat_id ON messaging.telegram_sessions (active_chat_id);

-- Add table and column comments
COMMENT ON TABLE messaging.telegram_sessions IS 'Maps Telegram chat IDs to internal chat sessions';
COMMENT ON COLUMN messaging.telegram_sessions.telegram_chat_id IS 'Telegram chat ID (unique identifier for the Telegram conversation)';
COMMENT ON COLUMN messaging.telegram_sessions.telegram_user_id IS 'Telegram user ID who owns this session';
COMMENT ON COLUMN messaging.telegram_sessions.active_chat_id IS 'Reference to the currently active internal chat session';
COMMENT ON COLUMN messaging.telegram_sessions.created_on IS 'Timestamp when the Telegram session mapping was created';
COMMENT ON COLUMN messaging.telegram_sessions.modified_on IS 'Timestamp when the session was last modified';

-- ============================================================================
-- Function: messaging.update_telegram_session_modified_on
-- Description: Automatically updates modified_on timestamp when session changes
-- ============================================================================
CREATE OR REPLACE FUNCTION messaging.update_telegram_session_modified_on()
RETURNS TRIGGER AS $$
BEGIN
    NEW.modified_on = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update modified_on on updates
CREATE TRIGGER trg_update_telegram_session_modified_on
    BEFORE UPDATE ON messaging.telegram_sessions
    FOR EACH ROW
    EXECUTE FUNCTION messaging.update_telegram_session_modified_on();

COMMENT ON FUNCTION messaging.update_telegram_session_modified_on() IS 'Trigger function to update telegram_sessions modified_on timestamp';
