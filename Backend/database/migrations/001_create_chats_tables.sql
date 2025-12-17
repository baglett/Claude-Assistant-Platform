-- ============================================================================
-- Migration: 001_create_chats_tables.sql
-- Description: Creates the chats and chat_messages tables for conversation
--              tracking with LLM metadata support.
-- ============================================================================

-- Create the messaging schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS messaging;

-- ============================================================================
-- Table: messaging.chats
-- Description: Stores chat/conversation sessions. Each chat can contain
--              multiple messages exchanged between the user and assistant.
-- ============================================================================
CREATE TABLE messaging.chats (
    -- Primary key using UUID for globally unique identification
    -- gen_random_uuid() is built-in to PostgreSQL 13+ (no extension required)
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Timestamp when the chat was initially created
    created_on TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Timestamp when the chat was last modified (new message added, etc.)
    modified_on TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Index on created_on for sorting chats by creation date
CREATE INDEX idx_chats_created_on ON messaging.chats (created_on DESC);

-- Index on modified_on for sorting chats by recent activity
CREATE INDEX idx_chats_modified_on ON messaging.chats (modified_on DESC);

-- Add table comment for documentation
COMMENT ON TABLE messaging.chats IS 'Stores chat/conversation sessions between users and the AI assistant';
COMMENT ON COLUMN messaging.chats.id IS 'Unique identifier for the chat session';
COMMENT ON COLUMN messaging.chats.created_on IS 'Timestamp when the chat was initially created';
COMMENT ON COLUMN messaging.chats.modified_on IS 'Timestamp when the chat was last modified';

-- ============================================================================
-- Table: messaging.chat_messages
-- Description: Stores individual messages within a chat. Uses a linked-list
--              structure via previous_message_id for deterministic ordering.
-- ============================================================================
CREATE TABLE messaging.chat_messages (
    -- Primary key using UUID for globally unique identification
    -- gen_random_uuid() is built-in to PostgreSQL 13+ (no extension required)
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Foreign key to the parent chat
    chat_id UUID NOT NULL REFERENCES messaging.chats(id) ON DELETE CASCADE,

    -- Reference to the previous message in the conversation chain
    -- NULL indicates this is the first message in the chat
    previous_message_id UUID REFERENCES messaging.chat_messages(id) ON DELETE SET NULL,

    -- The role of the message sender (user, assistant, system, tool)
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),

    -- The actual message content
    content TEXT NOT NULL,

    -- The LLM model used to generate this message (NULL for user messages)
    -- Examples: 'claude-opus-4-5-20251101', 'claude-sonnet-4-20250514'
    llm_model VARCHAR(100),

    -- JSONB column for storing LLM response metadata including token usage
    -- Structure follows the Claude Agent SDK response format (usage, stop_reason, etc.)
    -- See: https://docs.anthropic.com/en/docs/agents-and-tools/claude-agent-sdk
    message_metadata JSONB,

    -- Timestamp when the message was created
    created_on TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Index on chat_id for efficient lookup of messages within a chat
CREATE INDEX idx_chat_messages_chat_id ON messaging.chat_messages (chat_id);

-- Index on previous_message_id for traversing the message chain
CREATE INDEX idx_chat_messages_previous_message_id ON messaging.chat_messages (previous_message_id);

-- Index on created_on for time-based queries
CREATE INDEX idx_chat_messages_created_on ON messaging.chat_messages (created_on DESC);

-- Composite index for common query pattern: get messages for a chat ordered by time
CREATE INDEX idx_chat_messages_chat_id_created_on ON messaging.chat_messages (chat_id, created_on);

-- GIN index on message_metadata for efficient JSONB queries
CREATE INDEX idx_chat_messages_metadata ON messaging.chat_messages USING GIN (message_metadata);

-- Add table and column comments for documentation
COMMENT ON TABLE messaging.chat_messages IS 'Stores individual messages within chat conversations';
COMMENT ON COLUMN messaging.chat_messages.id IS 'Unique identifier for the message';
COMMENT ON COLUMN messaging.chat_messages.chat_id IS 'Reference to the parent chat session';
COMMENT ON COLUMN messaging.chat_messages.previous_message_id IS 'Reference to the previous message for deterministic ordering (NULL for first message)';
COMMENT ON COLUMN messaging.chat_messages.role IS 'The role of the message sender: user, assistant, system, or tool';
COMMENT ON COLUMN messaging.chat_messages.content IS 'The actual text content of the message';
COMMENT ON COLUMN messaging.chat_messages.llm_model IS 'The LLM model identifier used to generate assistant responses';
COMMENT ON COLUMN messaging.chat_messages.message_metadata IS 'JSONB containing LLM token usage and other response metadata';
COMMENT ON COLUMN messaging.chat_messages.created_on IS 'Timestamp when the message was created';

-- ============================================================================
-- Function: messaging.update_chat_modified_on
-- Description: Automatically updates the modified_on timestamp of the parent
--              chat when a new message is inserted.
-- ============================================================================
CREATE OR REPLACE FUNCTION messaging.update_chat_modified_on()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE messaging.chats
    SET modified_on = NOW()
    WHERE id = NEW.chat_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update chat's modified_on when a message is added
CREATE TRIGGER trg_update_chat_modified_on
    AFTER INSERT ON messaging.chat_messages
    FOR EACH ROW
    EXECUTE FUNCTION messaging.update_chat_modified_on();

COMMENT ON FUNCTION messaging.update_chat_modified_on() IS 'Trigger function to update chat modified_on timestamp when messages are added';
