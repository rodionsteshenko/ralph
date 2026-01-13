# STRIX-Inspired Slack Agent PRD

## Project Description

A stateful Slack bot agent built on Claude Code SDK (MCP server) that maintains persistent memory, tracks clipboard content, manages user preferences, and includes a dual-agent architecture for self-improvement and testing.

**Branch Name**: `ralph/slack-agent-foundation`

---

## Phase 0: Foundation

### US-001: Project Structure and Dependencies

**Description**: As a developer, I need the basic project structure and dependencies set up so I can start implementing features.

**Acceptance Criteria**:
- Create Python project structure with `pyproject.toml`
- Add dependencies: `slack-sdk`, `anthropic`, `sqlite3`, `pydantic`
- Create directory structure: `mcp_server/`, `state/`, `work/`, `tests/`
- Add `.gitignore` for Python, SQLite, and work directories
- Create `README.md` with project overview
- Typecheck passes

**Priority**: 1

---

### US-002: Basic MCP Server Structure

**Description**: As a developer, I need a basic MCP server structure so I can add tools incrementally.

**Acceptance Criteria**:
- Create `mcp_server/server.py` with MCP server boilerplate
- Implement server initialization and registration
- Create base tool class structure
- Add health check endpoint
- Server can start and respond to ping
- Typecheck passes

**Priority**: 2

---

### US-003: Slack Bot Setup with Socket Mode

**Description**: As a user, I need the bot to connect to Slack so I can interact with it via DM.

**Acceptance Criteria**:
- Create `slack_bot/client.py` with Slack Socket Mode setup
- Implement connection handling and reconnection logic
- Add event listener for messages
- Add basic message handler (echo back for now)
- Bot responds to DM messages
- Store Slack credentials in `.env` file (not committed)
- Typecheck passes

**Priority**: 3

---

### US-004: SQLite Database Setup

**Description**: As a developer, I need the SQLite database schema created so I can store structured data.

**Acceptance Criteria**:
- Create `database/schema.sql` with all table definitions from design
- Tables: `clipboard_entries`, `user_preferences`, `personality_traits`, `test_results`, `memory_blocks`
- Create `database/db.py` with connection management
- Add migration system for schema updates
- Add indexes for common queries
- Database initializes on first run
- Typecheck passes

**Priority**: 4

---

### US-005: File System Structure

**Description**: As a developer, I need the file system structure created so memory can be persisted.

**Acceptance Criteria**:
- Create directories: `state/inbox.md`, `state/today.md`, `state/commitments.md`, `state/patterns.md`
- Create directories: `state/insights/`, `state/research/`, `state/drafts/`, `state/people/`, `state/clipboard/`
- Add `.gitkeep` files to preserve empty directories
- Create utility functions to ensure directories exist
- Add function to initialize state files if missing
- Typecheck passes

**Priority**: 5

---

## Phase 1: Core Memory

### US-006: Memory Block Storage System

**Description**: As a developer, I need a memory block storage system so the agent can maintain persistent state.

**Acceptance Criteria**:
- Create `memory/blocks.py` with memory block CRUD operations
- Implement `get_memory(name)`, `set_memory(name, value)`, `list_memories()`, `create_memory(name, value)`
- Store memory blocks in SQLite `memory_blocks` table
- Support append-only versioning (keep history)
- Load memory blocks on startup
- Typecheck passes

**Priority**: 6

---

### US-007: Core Memory Block Initialization

**Description**: As a developer, I need core memory blocks initialized so the agent has identity and context.

**Acceptance Criteria**:
- Initialize blocks: `persona`, `bot_values`, `communication_style`, `guidelines`, `patterns`, `user_profile`
- Provide default values for each block
- Create configuration file `memory/defaults.json` for initial values
- Load defaults on first run if blocks don't exist
- All core blocks queryable via `get_memory()`
- Typecheck passes

**Priority**: 7

---

### US-008: Index Block System

**Description**: As a developer, I need index blocks that point to files so the agent can reference external state.

**Acceptance Criteria**:
- Initialize index blocks: `recent_insights`, `world_context`, `current_focus`, `schedule`, `clipboard_index`
- Index blocks contain pointers to file paths
- Create utility functions to resolve index block pointers
- Add function to update index blocks when files change
- Typecheck passes

**Priority**: 8

---

### US-009: File Management MCP Tools

**Description**: As an agent, I need file management tools so I can read and write state files.

**Acceptance Criteria**:
- Create `mcp_server/tools/file_tools.py`
- Implement tools: `read_file(path)`, `write_file(path, content)`, `edit_file(path, instructions)`, `list_files(directory)`, `grep(pattern, path)`
- Tools registered with MCP server
- Tools restricted to `state/` directory for safety
- Each tool returns structured result
- Typecheck passes

**Priority**: 9

---

### US-010: Memory MCP Tools

**Description**: As an agent, I need memory tools exposed via MCP so I can access memory blocks.

**Acceptance Criteria**:
- Create `mcp_server/tools/memory_tools.py`
- Implement tools: `get_memory`, `set_memory`, `list_memories`, `create_memory`
- Tools registered with MCP server
- Tools call underlying memory block storage system
- Each tool returns structured result
- Typecheck passes

**Priority**: 10

---

### US-011: Git Integration for State

**Description**: As a developer, I need git integration so state changes are tracked.

**Acceptance Criteria**:
- Create `git_manager/manager.py` with git operations
- Implement auto-commit on memory block updates (optional, configurable)
- Add commit message templates for different operations
- Initialize git repo in `state/` directory if not exists
- Add `.gitignore` for sensitive data
- Typecheck passes

**Priority**: 11

---

## Phase 2: Clipboard Integration (macOS)

### US-012: macOS Clipboard Monitoring

**Description**: As an agent, I need to monitor macOS clipboard so I can ingest copied content.

**Acceptance Criteria**:
- Create `clipboard/monitor.py` with macOS pasteboard monitoring
- Use `pyobjc-framework-Cocoa` or `pyperclip` for clipboard access
- Implement change detection with debouncing (2-3 seconds)
- Add start/stop monitoring functions
- Monitoring runs in background thread
- Privacy: respect user config to disable monitoring
- Typecheck passes

**Priority**: 12

---

### US-013: Clipboard Content Ingestion

**Description**: As an agent, I need to ingest clipboard content so it's searchable later.

**Acceptance Criteria**:
- Create `clipboard/ingest.py` with ingestion logic
- Extract text content from clipboard
- Store in `clipboard_entries` table with timestamp
- Implement deduplication (hash-based)
- Add source tagging ('clipboard', 'slack', etc.)
- Auto-tag content based on type (URL, code, text)
- Typecheck passes

**Priority**: 13

---

### US-014: Clipboard Embeddings and Vector Search

**Description**: As an agent, I need vector embeddings for clipboard content so I can do similarity search.

**Acceptance Criteria**:
- Create `clipboard/embeddings.py` with embedding generation
- Use Claude embeddings API or local model
- Generate embedding for each clipboard entry
- Store embeddings in `clipboard_entries.embedding` column (BLOB)
- Implement vector similarity search function
- Add function to find similar clipboard entries
- Typecheck passes

**Priority**: 14

---

### US-015: Clipboard Search MCP Tools

**Description**: As an agent, I need clipboard search tools so I can retrieve past clipboard content.

**Acceptance Criteria**:
- Create `mcp_server/tools/clipboard_tools.py`
- Implement tools: `get_clipboard()`, `watch_clipboard()`, `ingest_clipboard()`, `search_clipboard(query, filters)`, `tag_clipboard(id, tags)`, `get_clipboard_by_id(id)`
- Tools registered with MCP server
- Search supports: vector similarity, keyword, tag filtering, time filtering
- Each tool returns structured result
- Typecheck passes

**Priority**: 15

---

## Phase 3: Slack Integration

### US-016: Slack Message Sending Tools

**Description**: As an agent, I need tools to send messages to Slack so I can communicate with the user.

**Acceptance Criteria**:
- Create `mcp_server/tools/slack_tools.py`
- Implement tools: `send_message(channel, text, thread_ts=None)`, `react(channel, timestamp, emoji)`, `send_image(channel, image_path, text=None)`
- Tools registered with MCP server
- Tools use Slack Web API client
- Handle rate limiting and errors gracefully
- Typecheck passes

**Priority**: 16

---

### US-017: Slack History Retrieval Tools

**Description**: As an agent, I need tools to retrieve Slack conversation history so I can provide context-aware responses.

**Acceptance Criteria**:
- Implement tools: `get_slack_history(channel, limit=100)`, `get_thread_history(channel, thread_ts)`, `get_user_info(user_id)`, `get_channel_info(channel_id)`
- Tools registered with MCP server
- Add pagination support for large histories
- Cache frequently accessed history
- Typecheck passes

**Priority**: 17

---

### US-018: Slack Event Processing

**Description**: As a developer, I need robust Slack event processing so the bot responds to messages correctly.

**Acceptance Criteria**:
- Create `slack_bot/event_processor.py` with event handling logic
- Handle message events, reactions, file uploads
- Filter out bot's own messages
- Support thread context (thread_ts)
- Log all events for debugging
- Integrate with MCP server to process commands
- Typecheck passes

**Priority**: 18

---

## Phase 4: People Management

### US-019: People File Management

**Description**: As an agent, I need to manage people files so I can track relationships and context.

**Acceptance Criteria**:
- Create `people/manager.py` with people file management
- People files stored as markdown in `state/people/`
- Implement markdown template for person files
- Add functions to create, read, update person files
- Support structured fields: Relationship, Context, Preferences, Recent Interactions, Notes
- Typecheck passes

**Priority**: 19

---

### US-020: People Management MCP Tools

**Description**: As an agent, I need people management tools exposed via MCP so I can update person information.

**Acceptance Criteria**:
- Create `mcp_server/tools/people_tools.py`
- Implement tools: `get_person(name)`, `update_person(name, info)`, `list_people()`, `create_person(name, initial_info)`
- Tools registered with MCP server
- Tools work with markdown format
- Add search function to find people by keywords
- Typecheck passes

**Priority**: 20

---

## Phase 5: Database and Query Tools

### US-021: Database Query MCP Tools

**Description**: As an agent, I need database query tools so I can retrieve structured data.

**Acceptance Criteria**:
- Create `mcp_server/tools/db_tools.py`
- Implement tools: `query_db(query)`, `insert_db(table, data)`, `update_db(table, id, data)`, `search_db(query, filters)`
- Tools registered with MCP server
- Add SQL injection protection
- Restrict to read-only queries by default (require explicit flag for writes)
- Support parameterized queries
- Typecheck passes

**Priority**: 21

---

### US-022: User Preferences System

**Description**: As an agent, I need to track user preferences so I can personalize responses.

**Acceptance Criteria**:
- Create `preferences/manager.py` with preference management
- Implement functions to get, set, update preferences
- Store in `user_preferences` table
- Support confidence scores (0.0 - 1.0)
- Track source: 'explicit', 'inferred', 'confirmed'
- Add preference decay over time (decrease confidence if not reinforced)
- Typecheck passes

**Priority**: 22

---

### US-023: Personality Traits System

**Description**: As an agent, I need a personality traits system so I can maintain consistent behavior.

**Acceptance Criteria**:
- Create `personality/manager.py` with personality trait management
- Define traits: proactivity, verbosity, curiosity, helpfulness, autonomy
- Store in `personality_traits` table
- Support confidence scores and sources
- Add functions to query and update traits
- Traits influence agent behavior (load into context)
- Typecheck passes

**Priority**: 23

---

## Phase 6: Logging and Journaling

### US-024: Event Logging System

**Description**: As an agent, I need an event logging system so I can track all actions and events.

**Acceptance Criteria**:
- Create `logging/logger.py` with structured logging
- Implement log levels: DEBUG, INFO, WARNING, ERROR
- Store logs in `logs/agent.log` (rotated daily)
- Add metadata: timestamp, event_type, message, context
- Support querying logs with jq-like syntax
- Typecheck passes

**Priority**: 24

---

### US-025: Logging MCP Tools

**Description**: As an agent, I need logging tools exposed via MCP so I can log events.

**Acceptance Criteria**:
- Create `mcp_server/tools/logging_tools.py`
- Implement tools: `log_event(type, message, metadata)`, `journal_entry(topics, user_stated, my_intent)`, `query_logs(query)`
- Tools registered with MCP server
- `journal_entry` creates dated entries in `state/insights/`
- `query_logs` supports filtering by type, time, keywords
- Typecheck passes

**Priority**: 25

---

## Phase 7: Test Agent Foundation

### US-026: Test Agent MCP Server Setup

**Description**: As a developer, I need a separate Test Agent MCP server so it can test Main Agent independently.

**Acceptance Criteria**:
- Create `test_agent/server.py` with separate MCP server
- Test Agent has own configuration separate from Main Agent
- Test Agent can receive cloned memory blocks
- Test Agent has tools to validate responses
- Test Agent runs on different port/process
- Typecheck passes

**Priority**: 26

---

### US-027: Memory Cloning for Test Agent

**Description**: As a Main Agent, I need to clone my memory blocks so Test Agent has context for testing.

**Acceptance Criteria**:
- Create `test_agent/memory_clone.py` with cloning logic
- Implement `clone_memory_for_test()` function
- Clone all core memory blocks
- Store cloned memory in separate namespace
- Cloned memory is read-only for Test Agent
- Typecheck passes

**Priority**: 27

---

### US-028: Main Agent to Test Agent Communication

**Description**: As a Main Agent, I need to send test requests to Test Agent so I can validate changes.

**Acceptance Criteria**:
- Create `test_agent/communication.py` with Slack-based communication
- Implement `send_to_test_agent(prompt, cloned_memory)` via Slack DM
- Test Agent receives message with prompt and cloned memory
- Test Agent processes request and responds via Slack
- Add structured message format for test requests
- Typecheck passes

**Priority**: 28

---

### US-029: Test Agent Feedback System

**Description**: As a Test Agent, I need to provide structured feedback so Main Agent can evaluate changes.

**Acceptance Criteria**:
- Create `test_agent/feedback.py` with feedback generation
- Feedback includes: correctness, tone, completeness, alignment scores
- Generate actionable suggestions
- Store feedback in `test_results` table
- Main Agent can retrieve feedback via `get_test_feedback()`
- Typecheck passes

**Priority**: 29

---

### US-030: Test Agent Evaluation Tools

**Description**: As a Main Agent, I need to evaluate Test Agent feedback so I can decide to accept or reject changes.

**Acceptance Criteria**:
- Create `mcp_server/tools/test_tools.py`
- Implement tools: `clone_memory_for_test()`, `send_to_test_agent(prompt, cloned_memory)`, `get_test_feedback()`, `evaluate_test_feedback(feedback)`
- Tools registered with Main Agent MCP server
- `evaluate_test_feedback` accepts "like" or "dislike"
- Evaluation stored in database for learning
- Typecheck passes

**Priority**: 30

---

## Phase 8: Self-Modification

### US-031: Git Repository Cloning

**Description**: As a Main Agent, I need to clone my own repository so I can make changes safely.

**Acceptance Criteria**:
- Create `self_modify/repo_manager.py` with repository management
- Implement `clone_repo(destination)` function
- Clone to `work/` directory with unique name
- Preserve git history
- Set up remote to original repo
- Typecheck passes

**Priority**: 31

---

### US-032: Git Branch Management

**Description**: As a Main Agent, I need to create and manage git branches so I can isolate changes.

**Acceptance Criteria**:
- Implement `create_branch(name)` function
- Branch naming convention: `feature/`, `improve/`, `fix/`
- Ensure branch doesn't already exist
- Switch to new branch after creation
- Track branch in metadata
- Typecheck passes

**Priority**: 32

---

### US-033: Commit and PR Creation

**Description**: As a Main Agent, I need to commit changes and create PRs so user can review my improvements.

**Acceptance Criteria**:
- Implement `commit_changes(message)` function
- Implement `create_pr(title, description)` function
- Use GitHub API for PR creation (via `gh` CLI or PyGitHub)
- PR includes link to Test Agent validation results
- PR tagged with "self-improvement" label
- Notify user via Slack with PR link
- Typecheck passes

**Priority**: 33

---

### US-034: Skill File Updates

**Description**: As a Main Agent, I need to update skill files so I can modify my behavior.

**Acceptance Criteria**:
- Create `self_modify/skill_manager.py` with skill file management
- Implement `update_skill(name, content)` function
- Skills stored in `skills/` directory
- Support JSON and Python skill formats
- Validate skill syntax before saving
- Test via Test Agent before committing
- Typecheck passes

**Priority**: 34

---

### US-035: Self-Modification MCP Tools

**Description**: As a Main Agent, I need self-modification tools exposed via MCP so I can improve myself.

**Acceptance Criteria**:
- Create `mcp_server/tools/self_modify_tools.py`
- Implement tools: `clone_repo(destination)`, `create_branch(name)`, `commit_changes(message)`, `create_pr(title, description)`, `update_skill(name, content)`, `test_changes_via_test_agent()`
- Tools registered with MCP server
- Tools enforce testing before PR creation
- Typecheck passes

**Priority**: 35

---

## Phase 9: Scheduling and Ambient Behavior

### US-036: Job Scheduling System

**Description**: As an agent, I need a job scheduling system so I can run periodic background tasks.

**Acceptance Criteria**:
- Create `scheduler/scheduler.py` with cron-like scheduling
- Use `APScheduler` or similar library
- Support cron expressions for flexible scheduling
- Jobs persist across restarts (stored in database)
- Add job execution logging
- Typecheck passes

**Priority**: 36

---

### US-037: Scheduling MCP Tools

**Description**: As an agent, I need scheduling tools exposed via MCP so I can manage background jobs.

**Acceptance Criteria**:
- Create `mcp_server/tools/scheduler_tools.py`
- Implement tools: `schedule_job(name, cron, prompt)`, `remove_job(name)`, `list_jobs()`, `schedule_daily_improvement(time)`
- Tools registered with MCP server
- Jobs can trigger agent prompts at scheduled times
- Support for "perch time" (periodic ambient checks)
- Typecheck passes

**Priority**: 37

---

### US-038: Perch Time Implementation

**Description**: As an agent, I need perch time behavior so I can proactively maintain state and research.

**Acceptance Criteria**:
- Create `ambient/perch.py` with perch time logic
- Run every 2 hours (configurable)
- Tasks: check inbox.md, update today.md, process clipboard, update people files
- Only message user when meaningful (silence as default)
- Log all perch time activities
- Can be manually triggered via Slack command
- Typecheck passes

**Priority**: 38

---

## Phase 10: RSS and Research

### US-039: RSS Feed Management

**Description**: As an agent, I need to manage RSS feeds so I can stay updated on relevant topics.

**Acceptance Criteria**:
- Create `research/rss_manager.py` with RSS feed management
- Use `feedparser` library
- Store feeds in database or config file
- Implement `add_rss_feed(url, name)`, `fetch_rss_feeds()`, `list_rss_feeds()`
- Cache feed content to avoid re-fetching
- Typecheck passes

**Priority**: 39

---

### US-040: RSS Article Processing

**Description**: As an agent, I need to process RSS articles so I can learn from them.

**Acceptance Criteria**:
- Create `research/article_processor.py` with article processing
- Extract text content from article URLs
- Generate summaries using Claude
- Extract key learnings and insights
- Store processed articles in `state/research/`
- Tag articles by topic
- Typecheck passes

**Priority**: 40

---

### US-041: RSS MCP Tools

**Description**: As an agent, I need RSS tools exposed via MCP so I can manage feeds and process articles.

**Acceptance Criteria**:
- Create `mcp_server/tools/rss_tools.py`
- Implement tools: `add_rss_feed(url, name)`, `fetch_rss_feeds()`, `process_rss_article(url, content)`, `list_rss_feeds()`
- Tools registered with MCP server
- Articles processed asynchronously (don't block)
- Typecheck passes

**Priority**: 41

---

## Phase 11: Daily Self-Improvement Cycle

### US-042: Night-Time Research Scheduler

**Description**: As an agent, I need a night-time research scheduler so I can learn during off-hours.

**Acceptance Criteria**:
- Create `self_improve/night_cycle.py` with night cycle logic
- Schedule to start at 11 PM (configurable)
- Research phase: Fetch all RSS feeds, process new articles
- Store learnings in `state/research/improvements/`
- Focus on: agent architectures, memory systems, MCP servers, Claude updates
- Typecheck passes

**Priority**: 42

---

### US-043: Self-Improvement Thinking Phase

**Description**: As an agent, I need a thinking phase so I can analyze my behavior and plan improvements.

**Acceptance Criteria**:
- Implement thinking phase in night cycle
- Analyze logs: `query_logs("recent failures")`
- Review journal entries and Test Agent feedback history
- Identify patterns: what works, what doesn't
- Plan specific improvements
- Store plan in `work/self-improvement-YYYY-MM-DD/plan.md`
- Typecheck passes

**Priority**: 43

---

### US-044: Self-Improvement Implementation Phase

**Description**: As an agent, I need an implementation phase so I can make planned improvements.

**Acceptance Criteria**:
- Clone repo to `work/self-improvement-YYYY-MM-DD/`
- Make incremental changes based on plan
- Clone memory blocks for testing
- Test each change via Test Agent before proceeding
- Iterate until Test Agent approves changes
- Typecheck passes

**Priority**: 44

---

### US-045: Self-Improvement PR Creation

**Description**: As an agent, I need to create PRs for improvements so user can review and approve.

**Acceptance Criteria**:
- Only create PR if Test Agent feedback is positive
- Create branch: `self-improve-YYYY-MM-DD`
- Commit with message: "Self-improvement: [description]"
- PR includes: detailed description, research sources, Test Agent validation results
- Stop condition: PR created (success or failure stops cycle)
- Send Slack message to user with PR link
- Typecheck passes

**Priority**: 45

---

### US-046: Manual Self-Improvement Trigger

**Description**: As a user, I need to manually trigger self-improvement so I can request improvements on-demand.

**Acceptance Criteria**:
- Add Slack command: `@agent improve yourself`
- Trigger same cycle as night-time improvement
- Immediate execution (don't wait for scheduled time)
- Respond with acknowledgment and progress updates
- Follow same workflow: research → think → implement → test → PR
- Typecheck passes

**Priority**: 46

---

## Phase 12: Testing and Polish

### US-047: Integration Tests for Core Features

**Description**: As a developer, I need integration tests so I can validate core features work correctly.

**Acceptance Criteria**:
- Create `tests/integration/` directory
- Tests for: memory blocks, file management, Slack integration, clipboard
- Use pytest framework
- Mock external APIs (Slack, Claude)
- Tests run via `pytest tests/integration/`
- All tests pass
- Typecheck passes

**Priority**: 47

---

### US-048: Test Agent Validation Suite

**Description**: As a Test Agent, I need a test suite so I can validate Main Agent behavior consistently.

**Acceptance Criteria**:
- Create `test_agent/test_suite.py` with predefined tests
- Test scenarios: response quality, tone consistency, memory coherence, preference alignment
- Store test scenarios in `test_agent/scenarios/`
- Implement `run_test_suite(suite_name)` function
- Test results stored in `test_results` table
- Typecheck passes

**Priority**: 48

---

### US-049: Configuration Management System

**Description**: As a developer, I need a configuration management system so all settings are centralized.

**Acceptance Criteria**:
- Create `config/config.py` with configuration management
- Support `.env` file for secrets
- Support `config.yaml` for non-sensitive settings
- Validation for required settings
- Default values for optional settings
- Documentation for all configuration options
- Typecheck passes

**Priority**: 49

---

### US-050: Documentation and Deployment Guide

**Description**: As a developer, I need comprehensive documentation so the system can be deployed and maintained.

**Acceptance Criteria**:
- Create `DEPLOYMENT.md` with deployment instructions
- Document Slack app setup (Socket Mode, bot tokens, scopes)
- Document API key configuration (Anthropic)
- Document database setup and migrations
- Create `ARCHITECTURE.md` with system architecture
- Create `API.md` with MCP tool documentation
- Include troubleshooting section
- Typecheck passes

**Priority**: 50

---
