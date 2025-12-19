-- ============================================================================
-- Migration: 003_create_todos_table.sql
-- Description: Creates the todos table for task tracking and LLM agent execution.
--              Supports agent assignment, scheduling, and execution result storage.
-- ============================================================================

-- Create the tasks schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS tasks;

-- ============================================================================
-- Table: tasks.todos
-- Description: Stores todo items that can be created, tracked, and executed
--              by the orchestrator and sub-agents. Each todo can be assigned
--              to a specific agent for execution and stores the result.
-- ============================================================================
CREATE TABLE tasks.todos (
    -- Primary key using UUID for globally unique identification
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Core task data
    -- Title is the short description shown in lists
    title VARCHAR(500) NOT NULL,
    -- Description contains detailed information about the task
    description TEXT,

    -- Status tracking
    -- pending: Created but not started
    -- in_progress: Currently being executed by an agent
    -- completed: Successfully finished
    -- failed: Execution failed (see error_message)
    -- cancelled: Manually cancelled by user
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'cancelled')),

    -- Agent assignment for execution routing
    -- NULL means orchestrator handles directly or user decides later
    -- Valid agents: github, email, calendar, obsidian, orchestrator
    assigned_agent VARCHAR(50)
        CHECK (assigned_agent IS NULL OR assigned_agent IN ('github', 'email', 'calendar', 'obsidian', 'orchestrator')),

    -- Priority for ordering execution (1 = highest/critical, 5 = lowest)
    priority INTEGER NOT NULL DEFAULT 3
        CHECK (priority >= 1 AND priority <= 5),

    -- Execution scheduling
    -- NULL means manual trigger or immediate execution
    -- Set to a future timestamp to schedule execution
    scheduled_at TIMESTAMP WITH TIME ZONE,

    -- Execution results
    -- Result contains the agent's output/response after successful execution
    result TEXT,
    -- Error message contains details if execution failed
    error_message TEXT,
    -- Track retry attempts for failed executions
    execution_attempts INTEGER NOT NULL DEFAULT 0
        CHECK (execution_attempts >= 0),

    -- Context linking
    -- Link to the conversation where this todo was created
    chat_id UUID REFERENCES messaging.chats(id) ON DELETE SET NULL,
    -- Parent todo for subtask relationships (enables hierarchical todos)
    parent_todo_id UUID REFERENCES tasks.todos(id) ON DELETE CASCADE,

    -- Flexible metadata storage for agent-specific parameters
    -- Named task_metadata to avoid ORM conflicts with SQLAlchemy's reserved 'metadata'
    -- Examples: {"repo": "owner/repo", "labels": ["bug"]}, {"recipients": ["user@example.com"]}
    task_metadata JSONB NOT NULL DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    -- When execution actually started (set when status changes to in_progress)
    started_at TIMESTAMP WITH TIME ZONE,
    -- When execution finished (set when status changes to completed/failed/cancelled)
    completed_at TIMESTAMP WITH TIME ZONE,

    -- User/source tracking for audit and multi-user support
    -- Examples: "telegram:123456", "api:user@example.com", "orchestrator"
    created_by VARCHAR(100),

    -- Constraint: completed_at should be set when status is terminal
    CONSTRAINT valid_completion CHECK (
        (status IN ('completed', 'failed', 'cancelled') AND completed_at IS NOT NULL)
        OR (status IN ('pending', 'in_progress') AND completed_at IS NULL)
    )
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

-- Index on status for filtering todos by state (most common query)
CREATE INDEX idx_todos_status ON tasks.todos (status);

-- Index on assigned_agent for filtering todos by responsible agent
CREATE INDEX idx_todos_assigned_agent ON tasks.todos (assigned_agent)
    WHERE assigned_agent IS NOT NULL;

-- Index on priority for ordering todos
CREATE INDEX idx_todos_priority ON tasks.todos (priority);

-- Index on scheduled_at for finding todos ready for execution
CREATE INDEX idx_todos_scheduled_at ON tasks.todos (scheduled_at)
    WHERE scheduled_at IS NOT NULL;

-- Index on chat_id for finding todos from a specific conversation
CREATE INDEX idx_todos_chat_id ON tasks.todos (chat_id)
    WHERE chat_id IS NOT NULL;

-- Index on parent_todo_id for finding subtasks
CREATE INDEX idx_todos_parent_id ON tasks.todos (parent_todo_id)
    WHERE parent_todo_id IS NOT NULL;

-- Index on created_at for sorting by creation time (default list order)
CREATE INDEX idx_todos_created_at ON tasks.todos (created_at DESC);

-- Composite index for common query: pending todos ready for execution
-- Used by the background executor to find work
-- Note: The scheduled_at <= NOW() check must be done at query time, not in the index
-- predicate, since NOW() is not IMMUTABLE
CREATE INDEX idx_todos_pending_execution ON tasks.todos (priority, scheduled_at, created_at)
    WHERE status = 'pending';

-- GIN index on task_metadata for efficient JSONB queries
CREATE INDEX idx_todos_task_metadata ON tasks.todos USING GIN (task_metadata);

-- ============================================================================
-- Trigger: Auto-update updated_at Timestamp
-- ============================================================================
CREATE OR REPLACE FUNCTION tasks.update_todo_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_todos_updated_at
    BEFORE UPDATE ON tasks.todos
    FOR EACH ROW
    EXECUTE FUNCTION tasks.update_todo_updated_at();

-- ============================================================================
-- Comments for Documentation
-- ============================================================================
COMMENT ON TABLE tasks.todos IS 'Task tracking table for LLM agent execution with scheduling and result storage';

COMMENT ON COLUMN tasks.todos.id IS 'Unique identifier for the todo';
COMMENT ON COLUMN tasks.todos.title IS 'Short description of the task (displayed in lists)';
COMMENT ON COLUMN tasks.todos.description IS 'Detailed information about what needs to be done';
COMMENT ON COLUMN tasks.todos.status IS 'Current state: pending, in_progress, completed, failed, cancelled';
COMMENT ON COLUMN tasks.todos.assigned_agent IS 'Sub-agent responsible for execution: github, email, calendar, obsidian, orchestrator';
COMMENT ON COLUMN tasks.todos.priority IS 'Execution priority: 1 (critical) to 5 (lowest)';
COMMENT ON COLUMN tasks.todos.scheduled_at IS 'When to execute (NULL for manual/immediate)';
COMMENT ON COLUMN tasks.todos.result IS 'Agent output after successful execution';
COMMENT ON COLUMN tasks.todos.error_message IS 'Error details if execution failed';
COMMENT ON COLUMN tasks.todos.execution_attempts IS 'Number of execution attempts (for retry tracking)';
COMMENT ON COLUMN tasks.todos.chat_id IS 'Reference to originating conversation';
COMMENT ON COLUMN tasks.todos.parent_todo_id IS 'Parent task ID for subtask hierarchies';
COMMENT ON COLUMN tasks.todos.task_metadata IS 'JSONB storage for agent-specific parameters';
COMMENT ON COLUMN tasks.todos.created_at IS 'When the todo was created';
COMMENT ON COLUMN tasks.todos.updated_at IS 'When the todo was last modified';
COMMENT ON COLUMN tasks.todos.started_at IS 'When execution began';
COMMENT ON COLUMN tasks.todos.completed_at IS 'When execution finished (success or failure)';
COMMENT ON COLUMN tasks.todos.created_by IS 'User or source that created this todo';

COMMENT ON FUNCTION tasks.update_todo_updated_at() IS 'Trigger function to auto-update updated_at timestamp';
