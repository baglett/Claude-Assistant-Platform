-- ============================================================================
-- Migration: 004_create_agent_executions_table.sql
-- Description: Creates the agent_executions table for tracking agent thinking,
--              tool calls, and execution metrics. Supports nested agent calls
--              and links to both conversations and todos.
-- ============================================================================

-- Create the agents schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS agents;

-- ============================================================================
-- Table: agents.executions
-- Description: Stores detailed execution logs for all agent invocations.
--              Each row represents a single agent execution with its thinking
--              process, tool calls, results, and performance metrics.
-- ============================================================================
CREATE TABLE agents.executions (
    -- Primary key using UUID for globally unique identification
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- -------------------------------------------------------------------------
    -- Context Linking
    -- -------------------------------------------------------------------------
    -- Link to the conversation where this execution occurred
    chat_id UUID REFERENCES messaging.chats(id) ON DELETE SET NULL,

    -- Link to the todo being executed (if applicable)
    todo_id UUID REFERENCES tasks.todos(id) ON DELETE SET NULL,

    -- Parent execution for tracking nested agent calls
    -- When TodoAgent calls GitHubAgent, the GitHubAgent execution
    -- references the TodoAgent execution as its parent
    parent_execution_id UUID REFERENCES agents.executions(id) ON DELETE SET NULL,

    -- -------------------------------------------------------------------------
    -- Agent Information
    -- -------------------------------------------------------------------------
    -- Name of the agent that executed
    -- Values: orchestrator, todo, github, email, calendar, obsidian
    agent_name VARCHAR(50) NOT NULL,

    -- Status of the execution
    -- pending: Started but not complete
    -- running: Currently executing
    -- completed: Finished successfully
    -- failed: Finished with error
    -- cancelled: Manually cancelled
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),

    -- -------------------------------------------------------------------------
    -- Execution Details
    -- -------------------------------------------------------------------------
    -- The task or instruction given to the agent
    task_description TEXT,

    -- Context passed to the agent (recent messages, relevant todos, etc.)
    -- Stored as JSONB for flexibility
    input_context JSONB DEFAULT '{}',

    -- The agent's reasoning/thinking process
    -- This is the internal thought process before taking action
    thinking TEXT,

    -- Tool calls made by the agent during execution
    -- Array of {tool_name, input, output, duration_ms}
    tool_calls JSONB DEFAULT '[]',

    -- The final result/output of the agent's execution
    result TEXT,

    -- Error message if execution failed
    error_message TEXT,

    -- -------------------------------------------------------------------------
    -- Performance Metrics
    -- -------------------------------------------------------------------------
    -- Token usage for this execution
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,

    -- Total execution time in milliseconds
    execution_time_ms INTEGER,

    -- Number of LLM API calls made during this execution
    llm_calls INTEGER DEFAULT 0,

    -- -------------------------------------------------------------------------
    -- Timestamps
    -- -------------------------------------------------------------------------
    -- When the execution started
    started_at TIMESTAMP WITH TIME ZONE,

    -- When the execution completed (success or failure)
    completed_at TIMESTAMP WITH TIME ZONE,

    -- When this record was created
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- -------------------------------------------------------------------------
    -- Constraints
    -- -------------------------------------------------------------------------
    -- Ensure completed_at is set for terminal states
    CONSTRAINT valid_completion CHECK (
        (status IN ('completed', 'failed', 'cancelled') AND completed_at IS NOT NULL)
        OR (status IN ('pending', 'running') AND completed_at IS NULL)
    )
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

-- Index on chat_id for finding all executions in a conversation
CREATE INDEX idx_executions_chat_id ON agents.executions (chat_id)
    WHERE chat_id IS NOT NULL;

-- Index on todo_id for finding executions related to a specific todo
CREATE INDEX idx_executions_todo_id ON agents.executions (todo_id)
    WHERE todo_id IS NOT NULL;

-- Index on parent_execution_id for tracing nested calls
CREATE INDEX idx_executions_parent_id ON agents.executions (parent_execution_id)
    WHERE parent_execution_id IS NOT NULL;

-- Index on agent_name for filtering by agent type
CREATE INDEX idx_executions_agent_name ON agents.executions (agent_name);

-- Index on status for finding active/failed executions
CREATE INDEX idx_executions_status ON agents.executions (status);

-- Index on created_at for time-based queries
CREATE INDEX idx_executions_created_at ON agents.executions (created_at DESC);

-- Composite index for common query: recent executions by agent
CREATE INDEX idx_executions_agent_recent ON agents.executions (agent_name, created_at DESC);

-- GIN index on tool_calls for querying specific tools used
CREATE INDEX idx_executions_tool_calls ON agents.executions USING GIN (tool_calls);

-- ============================================================================
-- Comments for Documentation
-- ============================================================================
COMMENT ON TABLE agents.executions IS 'Execution logs for all agent invocations with thinking, tools, and metrics';

COMMENT ON COLUMN agents.executions.id IS 'Unique identifier for the execution';
COMMENT ON COLUMN agents.executions.chat_id IS 'Reference to the conversation context';
COMMENT ON COLUMN agents.executions.todo_id IS 'Reference to the todo being executed (if applicable)';
COMMENT ON COLUMN agents.executions.parent_execution_id IS 'Parent execution for nested agent calls';
COMMENT ON COLUMN agents.executions.agent_name IS 'Name of the executing agent';
COMMENT ON COLUMN agents.executions.status IS 'Current execution status';
COMMENT ON COLUMN agents.executions.task_description IS 'The task or instruction given to the agent';
COMMENT ON COLUMN agents.executions.input_context IS 'Context passed to the agent (messages, todos, metadata)';
COMMENT ON COLUMN agents.executions.thinking IS 'Agent reasoning and thought process';
COMMENT ON COLUMN agents.executions.tool_calls IS 'Array of tool invocations with inputs and outputs';
COMMENT ON COLUMN agents.executions.result IS 'Final execution result/output';
COMMENT ON COLUMN agents.executions.error_message IS 'Error details if execution failed';
COMMENT ON COLUMN agents.executions.input_tokens IS 'Total input tokens used';
COMMENT ON COLUMN agents.executions.output_tokens IS 'Total output tokens used';
COMMENT ON COLUMN agents.executions.execution_time_ms IS 'Total execution duration in milliseconds';
COMMENT ON COLUMN agents.executions.llm_calls IS 'Number of LLM API calls made';
COMMENT ON COLUMN agents.executions.started_at IS 'When execution began';
COMMENT ON COLUMN agents.executions.completed_at IS 'When execution finished';
COMMENT ON COLUMN agents.executions.created_at IS 'When this record was created';
