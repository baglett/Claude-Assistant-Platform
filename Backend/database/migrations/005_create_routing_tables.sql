-- =============================================================================
-- Migration 005: Create Routing Tables
-- =============================================================================
-- Description: Creates the routing schema with tables for agent routing,
--              tool definitions, and routing decision logging.
--              Uses pgvector extension for embedding similarity search.
--
-- Dependencies:
--   - PostgreSQL 15+
--   - pgvector extension
--
-- Tables Created:
--   - routing.agents: Agent routing definitions with embeddings
--   - routing.tools: Tool definitions with embeddings (Phase 2+)
--   - routing.decisions: Routing decision logs for analytics
--
-- Author: Claude Assistant Platform
-- Date: 2025-01-11
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Enable pgvector Extension
-- -----------------------------------------------------------------------------
-- pgvector provides vector similarity search capabilities for embeddings.
-- Must be installed on the PostgreSQL server: CREATE EXTENSION vector;
CREATE EXTENSION IF NOT EXISTS vector;

-- -----------------------------------------------------------------------------
-- Create Routing Schema
-- -----------------------------------------------------------------------------
-- Separate schema for routing-related tables to maintain organization.
CREATE SCHEMA IF NOT EXISTS routing;

-- -----------------------------------------------------------------------------
-- Routing Agents Table
-- -----------------------------------------------------------------------------
-- Stores agent definitions with routing metadata including:
--   - Keywords for BM25 text matching
--   - Regex patterns for fast Tier 1 matching
--   - Embeddings for semantic similarity (Tier 2)
--
-- This table is the primary data source for the 3-tier routing system.
CREATE TABLE routing.agents (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Agent identification
    name VARCHAR(50) UNIQUE NOT NULL,           -- Internal name: "github", "todo", etc.
    display_name VARCHAR(100) NOT NULL,         -- Human-readable: "GitHub Agent"

    -- Routing data
    description TEXT NOT NULL,                   -- Full description for embedding generation
    keywords TEXT[] NOT NULL,                    -- BM25 keywords: ARRAY['github', 'issue', 'pr']
    regex_patterns TEXT[],                       -- Fast-path regex patterns for Tier 1

    -- Embedding for semantic similarity (Tier 2)
    -- Using 1536 dimensions for OpenAI text-embedding-3-small
    embedding vector(1536),

    -- Configuration
    enabled BOOLEAN DEFAULT true,                -- Enable/disable agent for routing
    priority INTEGER DEFAULT 100,                -- Lower = higher priority (for tie-breaking)

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Comment on table and columns for documentation
COMMENT ON TABLE routing.agents IS 'Agent routing definitions for the 3-tier hybrid router';
COMMENT ON COLUMN routing.agents.name IS 'Internal agent name used in code (e.g., github, todo)';
COMMENT ON COLUMN routing.agents.keywords IS 'Keywords for BM25 text matching in Tier 2';
COMMENT ON COLUMN routing.agents.regex_patterns IS 'Regex patterns for fast Tier 1 matching';
COMMENT ON COLUMN routing.agents.embedding IS 'OpenAI text-embedding-3-small vector (1536 dims)';
COMMENT ON COLUMN routing.agents.priority IS 'Routing priority - lower values = higher priority';

-- -----------------------------------------------------------------------------
-- Routing Tools Table (Phase 2+)
-- -----------------------------------------------------------------------------
-- Stores tool definitions for future tool-level routing.
-- Currently unused but schema is prepared for Phase 2 expansion.
CREATE TABLE routing.tools (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Tool identification
    agent_name VARCHAR(50) NOT NULL REFERENCES routing.agents(name) ON DELETE CASCADE,
    tool_name VARCHAR(100) NOT NULL,

    -- Routing data
    description TEXT NOT NULL,                   -- Full description for embedding
    keywords TEXT[],                             -- BM25 keywords

    -- Embedding for semantic similarity
    embedding vector(1536),

    -- Tool schema (from Claude API tool definitions)
    input_schema JSONB NOT NULL,

    -- Configuration
    enabled BOOLEAN DEFAULT true,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    UNIQUE(agent_name, tool_name)
);

-- Comment on table
COMMENT ON TABLE routing.tools IS 'Tool definitions for future tool-level routing (Phase 2+)';

-- -----------------------------------------------------------------------------
-- Routing Decisions Log Table
-- -----------------------------------------------------------------------------
-- Logs all routing decisions for analytics, debugging, and improvement.
-- Used to track:
--   - Which tier made the decision
--   - Confidence scores from each tier
--   - Latency metrics
--   - Correctness feedback (for future model training)
CREATE TABLE routing.decisions (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Context
    chat_id UUID REFERENCES messaging.chats(id) ON DELETE SET NULL,
    user_message TEXT NOT NULL,

    -- Routing result
    tier_used INTEGER NOT NULL,                  -- 1=regex, 2=hybrid, 3=llm
    selected_agent VARCHAR(50),                  -- NULL if routed to orchestrator
    confidence FLOAT,                            -- Confidence score (0.0-1.0)

    -- Detailed scores for debugging
    bm25_scores JSONB,                           -- {"github": 0.8, "todo": 0.2, ...}
    embedding_scores JSONB,                      -- {"github": 0.9, "todo": 0.1, ...}

    -- Performance metrics
    latency_ms INTEGER,                          -- Total routing time in milliseconds

    -- Feedback (populated later)
    correct BOOLEAN,                             -- NULL until user provides feedback

    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Comment on table
COMMENT ON TABLE routing.decisions IS 'Routing decision logs for analytics and improvement';
COMMENT ON COLUMN routing.decisions.tier_used IS '1=regex, 2=hybrid (BM25+embedding), 3=llm (Haiku)';
COMMENT ON COLUMN routing.decisions.correct IS 'User feedback on routing correctness (NULL until feedback)';

-- -----------------------------------------------------------------------------
-- Indexes
-- -----------------------------------------------------------------------------

-- Agent indexes
CREATE INDEX idx_routing_agents_name ON routing.agents(name);
CREATE INDEX idx_routing_agents_enabled ON routing.agents(enabled) WHERE enabled = true;

-- Vector similarity index for agents (ivfflat for small datasets)
-- lists=10 is appropriate for <100 vectors
CREATE INDEX idx_routing_agents_embedding ON routing.agents
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);

-- Tool indexes
CREATE INDEX idx_routing_tools_agent ON routing.tools(agent_name);
CREATE INDEX idx_routing_tools_enabled ON routing.tools(enabled) WHERE enabled = true;

-- Vector similarity index for tools
-- lists=50 is appropriate for <1000 vectors
CREATE INDEX idx_routing_tools_embedding ON routing.tools
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);

-- Decision log indexes
CREATE INDEX idx_routing_decisions_created ON routing.decisions(created_at DESC);
CREATE INDEX idx_routing_decisions_chat ON routing.decisions(chat_id);
CREATE INDEX idx_routing_decisions_tier ON routing.decisions(tier_used);
CREATE INDEX idx_routing_decisions_agent ON routing.decisions(selected_agent);

-- -----------------------------------------------------------------------------
-- Trigger for updated_at
-- -----------------------------------------------------------------------------
-- Automatically update updated_at timestamp on row modification

-- Create trigger function if not exists
CREATE OR REPLACE FUNCTION routing.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to agents table
CREATE TRIGGER update_routing_agents_updated_at
    BEFORE UPDATE ON routing.agents
    FOR EACH ROW
    EXECUTE FUNCTION routing.update_updated_at_column();

-- Apply trigger to tools table
CREATE TRIGGER update_routing_tools_updated_at
    BEFORE UPDATE ON routing.tools
    FOR EACH ROW
    EXECUTE FUNCTION routing.update_updated_at_column();

-- -----------------------------------------------------------------------------
-- Seed Data: Initial Agent Definitions
-- -----------------------------------------------------------------------------
-- Insert the 5 core agents with their routing metadata.
-- Embeddings will be generated at application startup.

INSERT INTO routing.agents (name, display_name, description, keywords, regex_patterns, priority) VALUES
(
    'github',
    'GitHub Agent',
    'Manages GitHub repositories, issues, pull requests, branches, and code operations. Use for creating issues, reviewing PRs, managing branches, merging code, and repository tasks. Handles all GitHub API operations including listing repositories, creating branches, and checking pull request status.',
    ARRAY['github', 'gh', 'issue', 'issues', 'pull request', 'pr', 'prs', 'repository', 'repo', 'repos', 'branch', 'branches', 'merge', 'commit', 'commits', 'code', 'review'],
    ARRAY['\b(github|gh)\b', '\b(issue|issues)\b', '\b(pull\s*request|pr|prs)\b', '\b(repo|repository|repos)\b', '\b(branch|branches|merge|commit)\b'],
    10
),
(
    'todo',
    'Todo Agent',
    'Manages todo items, tasks, and reminders. Use for creating tasks, listing todos, updating task status, marking items complete, and managing your task list. Handles task prioritization, due dates, and task assignments.',
    ARRAY['todo', 'todos', 'task', 'tasks', 'reminder', 'reminders', 'remind', 'list', 'checklist', 'item', 'items', 'complete', 'done', 'pending'],
    ARRAY['\b(todo|todos|task|tasks)\b', '\b(remind|reminder|reminders)\b', '\b(add|create).*(task|todo)\b', '\b(complete|done|finish).*task\b'],
    20
),
(
    'email',
    'Email Agent',
    'Manages Gmail operations including reading, searching, and sending emails. Use for inbox management, drafting messages, email organization, labeling, archiving, and replying to messages. Handles all Gmail API operations.',
    ARRAY['email', 'emails', 'mail', 'inbox', 'gmail', 'send', 'draft', 'drafts', 'message', 'messages', 'reply', 'forward', 'label', 'archive', 'compose'],
    ARRAY['\b(email|emails|mail|inbox|gmail)\b', '\b(send|draft|reply|forward).*(message|email|mail)\b', '\b(compose|write).*email\b'],
    30
),
(
    'calendar',
    'Google Calendar Agent',
    'Manages Google Calendar events and scheduling. Use for creating meetings, checking availability, scheduling appointments, managing your calendar, setting up recurring events, and finding free time slots. Handles all Google Calendar API operations.',
    ARRAY['calendar', 'schedule', 'scheduling', 'meeting', 'meetings', 'event', 'events', 'appointment', 'appointments', 'available', 'availability', 'free', 'busy', 'book', 'slot', 'time'],
    ARRAY['\b(calendar|schedule|scheduling)\b', '\b(meeting|meetings|appointment|appointments)\b', '\b(event|events)\b', '\b(free|busy|available|availability)\b', '\bbook.*(time|slot|meeting)\b'],
    40
),
(
    'motion',
    'Motion Agent',
    'Manages Motion app tasks and projects with AI-powered scheduling. Use for Motion-specific task management, project organization, and intelligent task scheduling. Handles Motion API operations for tasks and projects.',
    ARRAY['motion', 'motion task', 'motion project', 'motion app'],
    ARRAY['\bmotion\b', '\bmotion.*(task|project)\b'],
    50
);

-- -----------------------------------------------------------------------------
-- Verification Queries
-- -----------------------------------------------------------------------------
-- Run these queries to verify the migration was successful:
--
-- SELECT count(*) FROM routing.agents;  -- Should return 5
-- SELECT name, display_name, array_length(keywords, 1) as keyword_count FROM routing.agents;
-- SELECT * FROM pg_extension WHERE extname = 'vector';  -- Should show pgvector
