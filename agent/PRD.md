# PRD: STRIX-Inspired Slack Agent

## Project Overview

Build a stateful Slack bot agent (single-user DM) that maintains persistent memory, tracks macOS clipboard content, manages user preferences, and includes a dual-agent architecture for self-improvement and testing. Based on STRIX architecture but adapted for Slack and enhanced with self-improvement capabilities.

## User Stories

### US-001: Foundation - Slack Bot Setup and Basic MCP Server
**Description**: As a developer, I want a Slack bot that connects via Socket Mode and exposes basic MCP server tools so that the agent can receive messages and respond.

**Acceptance Criteria**:
- Slack bot connects via Socket Mode (single-user DM)
- Basic MCP server structure with Claude Code SDK
- `send_message` tool works (send to Slack DM)
- `react` tool works (add emoji reactions)
- Agent can receive and respond to messages
- Typecheck passes

### US-002: Foundation - Memory Block System (Letta-style)
**Description**: As a developer, I want a memory block system similar to Letta so that the agent can maintain persistent identity across conversations.

**Acceptance Criteria**:
- SQLite database for memory blocks (append-only)
- `get_memory(name)` tool retrieves memory block
- `set_memory(name, value)` tool updates memory block
- `list_memories()` tool lists all memory blocks
- `create_memory(name, value)` tool creates new memory block
- Core memory blocks loaded into every conversation (persona, bot_values, communication_style)
- Typecheck passes

### US-003: Foundation - File System Structure
**Description**: As a developer, I want a structured file system for state management so that the agent can organize its memory and knowledge.

**Acceptance Criteria**:
- Create `state/` directory structure:
  - `state/inbox.md` - Unprocessed tasks
  - `state/today.md` - Current priorities
  - `state/commitments.md` - Deadlines
  - `state/patterns.md` - Behavioral observations
  - `state/insights/` - Dated insight files
  - `state/research/` - Research outputs
  - `state/people/` - People files (markdown)
  - `state/drafts/` - Work in progress
- File management tools: `read_file`, `write_file`, `edit_file`, `list_files`, `grep`
- Typecheck passes

### US-004: Foundation - Basic Agent Loop
**Description**: As a developer, I want a basic agent loop that processes Slack messages and maintains context so that the agent can have coherent conversations.

**Acceptance Criteria**:
- Agent receives Slack message events
- Builds context from memory blocks and recent history
- Calls Claude Opus 4.5 API with context
- Responds via Slack
- Maintains conversation history (last 50 messages)
- Typecheck passes

### US-005: Core Memory - Three-Tier Memory System
**Description**: As a developer, I want a three-tier memory system (Core/Indices/Files) so that the agent can efficiently manage identity, knowledge, and details.

**Acceptance Criteria**:
- Tier 1 (Core): Always-loaded memory blocks (persona, bot_values, communication_style, guidelines, patterns, user_profile)
- Tier 2 (Indices): Always-loaded index blocks pointing to files (recent_insights, world_context, current_focus, schedule, clipboard_index)
- Tier 3 (Files): On-demand file loading
- Context building logic loads core + indices, then selectively loads files
- Typecheck passes

### US-006: Core Memory - Index Block Management
**Description**: As a developer, I want index blocks that point to files so that the agent knows what it knows without loading everything.

**Acceptance Criteria**:
- `recent_insights` index points to dated insight files
- `world_context` index points to external context files
- `current_focus` index tracks what user and agent are working on
- `schedule` index tracks events
- `clipboard_index` tracks recent clipboard entries
- Index blocks are small (pointers only) but informative
- Typecheck passes

### US-007: Core Memory - Git Integration
**Description**: As a developer, I want git integration for file versioning so that all state changes are traceable and reversible.

**Acceptance Criteria**:
- All files in `state/` are tracked in git
- Agent commits changes with descriptive messages
- Git history provides provenance for "why do you know this?" queries
- `git log` accessible via tools
- Typecheck passes

### US-008: Clipboard Integration - macOS Clipboard Monitoring
**Description**: As a developer, I want the agent to monitor macOS clipboard so that clipboard content can be automatically ingested into memory.

**Acceptance Criteria**:
- Monitor macOS pasteboard using NSPasteboard API (via pyobjc or pyperclip)
- Detect clipboard changes (debounced 2-3 seconds)
- Extract text content (ignore images/binary for now)
- `watch_clipboard()` tool starts monitoring
- `get_clipboard()` tool gets current clipboard
- `ingest_clipboard()` tool manually ingests clipboard
- Typecheck passes

### US-009: Clipboard Integration - Database Schema and Storage
**Description**: As a developer, I want a SQLite database to store clipboard entries so that clipboard history is queryable and searchable.

**Acceptance Criteria**:
- SQLite database with `clipboard_entries` table:
  - id, content, timestamp, source, tags (JSON), embedding (BLOB)
- Auto-ingest clipboard changes into database
- Deduplication (hash-based check)
- `search_clipboard(query, filters)` tool searches history
- `tag_clipboard(id, tags)` tool adds tags
- Typecheck passes

### US-010: Clipboard Integration - Vector Embeddings and RAG
**Description**: As a developer, I want clipboard content to be searchable via vector similarity so that the agent can find relevant clipboard entries.

**Acceptance Criteria**:
- Generate embeddings for clipboard content (via Claude embeddings API)
- Store embeddings in database
- Vector similarity search via `search_clipboard()`
- RAG integration - clipboard content included in retrieval
- Keyword search (SQLite FTS) as fallback
- Typecheck passes

### US-011: Test Agent - Test Agent MCP Server
**Description**: As a developer, I want a Test Agent MCP server so that the Main Agent can test its changes before creating PRs.

**Acceptance Criteria**:
- Separate Test Agent MCP server instance
- Test Agent connects to Slack (separate DM or channel)
- Test Agent receives cloned memory from Main Agent
- Test Agent validates responses for correctness, tone, completeness
- `clone_memory_for_test()` tool clones Main Agent memory
- `send_to_test_agent(prompt, cloned_memory)` tool sends test to Test Agent
- Typecheck passes

### US-012: Test Agent - Test Framework and Validation
**Description**: As a developer, I want a test framework so that Test Agent can validate Main Agent's behavior systematically.

**Acceptance Criteria**:
- Test Agent validates:
  - Response correctness
  - Tone/style adherence
  - Completeness
  - User preference alignment
- `get_test_feedback()` tool retrieves Test Agent feedback
- `evaluate_test_feedback(feedback)` tool allows Main Agent to like/dislike feedback
- `run_test_suite(suite_name)` tool runs predefined test suites
- Test results stored in database
- Typecheck passes

### US-013: Test Agent - Main ↔ Test Agent Communication
**Description**: As a developer, I want Main Agent and Test Agent to communicate via Slack so that testing happens in a natural environment.

**Acceptance Criteria**:
- Both agents connected to Slack
- Main Agent sends test prompts to Test Agent via Slack DM
- Test Agent responds with validation feedback
- Main Agent can evaluate feedback (like/dislike reactions)
- Communication protocol defined and documented
- Typecheck passes

### US-014: Self-Modification - Git Branch Management
**Description**: As a developer, I want the agent to clone its own repo and create branches so that it can make changes safely.

**Acceptance Criteria**:
- `clone_repo(destination)` tool clones repository to work directory
- `create_branch(name)` tool creates git branch
- Work happens in isolated directory
- Branch naming convention: `self-improve-YYYY-MM-DD` or `feature-name`
- Typecheck passes

### US-015: Self-Modification - PR Creation Workflow
**Description**: As a developer, I want the agent to create PRs after testing so that changes can be reviewed before merging.

**Acceptance Criteria**:
- `commit_changes(message)` tool commits changes
- `create_pr(title, description)` tool creates pull request
- PR includes:
  - Detailed description of changes
  - Links to research sources (if applicable)
  - Links to Test Agent validation results
- Agent notifies user via Slack with PR link
- Typecheck passes

### US-016: Self-Modification - Skill Modification
**Description**: As a developer, I want the agent to modify its own skills so that it can improve its capabilities.

**Acceptance Criteria**:
- Skills stored in `.claude/skills/` directory
- `update_skill(name, content)` tool updates skill file
- Agent can read, modify, and write skill files
- Skills are version-controlled in git
- Typecheck passes

### US-017: Self-Modification - Self-Testing Workflow
**Description**: As a developer, I want the agent to test its changes via Test Agent before creating PRs so that only validated changes are proposed.

**Acceptance Criteria**:
- Agent clones repo → makes changes → clones memory for Test Agent
- Agent sends changes to Test Agent via `send_to_test_agent()`
- Agent receives feedback via `get_test_feedback()`
- Agent evaluates feedback via `evaluate_test_feedback()`
- Agent iterates if feedback is negative
- Agent creates PR only if feedback is positive
- Typecheck passes

### US-018: Personality System - User Preference Tracking
**Description**: As a developer, I want the agent to track user preferences so that it can adapt its behavior over time.

**Acceptance Criteria**:
- SQLite `user_preferences` table stores preferences
- Preferences have confidence scores and sources (explicit/inferred/confirmed)
- `get_user_preference(key)` tool retrieves preference
- `set_user_preference(key, value, source)` tool sets preference
- Preferences decay over time if not reinforced
- Typecheck passes

### US-019: Personality System - Personality Trait System
**Description**: As a developer, I want the agent to maintain personality traits so that it has consistent behavior.

**Acceptance Criteria**:
- SQLite `personality_traits` table stores traits
- Traits include: proactivity, verbosity, curiosity, helpfulness, autonomy
- Traits influence agent behavior (prompt injection)
- Traits can be updated by agent (with user approval)
- Typecheck passes

### US-020: Personality System - Learning Mechanisms
**Description**: As a developer, I want the agent to learn user preferences automatically so that it improves over time.

**Acceptance Criteria**:
- Agent infers preferences from user behavior
- Agent asks for confirmation: "Do you prefer X?"
- Agent updates preferences based on explicit user statements
- Confidence scores adjust based on reinforcement
- Learning logged for transparency
- Typecheck passes

### US-021: Personality System - Preference Inference
**Description**: As a developer, I want the agent to infer preferences from patterns so that it can learn implicitly.

**Acceptance Criteria**:
- Agent analyzes conversation patterns
- Agent identifies preferences (e.g., "user always asks for concise responses")
- Agent creates inferred preferences with low confidence
- Agent asks for confirmation before using inferred preferences
- Typecheck passes

### US-022: Ambient Behavior - Perch Time Scheduler
**Description**: As a developer, I want the agent to run periodic background tasks so that it can be proactive.

**Acceptance Criteria**:
- Scheduler runs every 2 hours ("perch time")
- Agent checks `state/inbox.md` for unprocessed tasks
- Agent updates state files (`today.md`, `commitments.md`)
- Agent only messages when meaningful (silence as default)
- `schedule_job(name, cron, prompt)` tool schedules cron jobs
- Typecheck passes

### US-023: Ambient Behavior - Background Task System
**Description**: As a developer, I want the agent to run background tasks so that it can do research and maintenance.

**Acceptance Criteria**:
- Background tasks run during perch time
- Tasks include: research, state file updates, people file updates
- Tasks don't interrupt user conversations
- Task results logged
- Typecheck passes

### US-024: Ambient Behavior - Proactive Messaging
**Description**: As a developer, I want the agent to message proactively when it has meaningful updates so that it's helpful without being annoying.

**Acceptance Criteria**:
- Agent messages only when:
  - Important deadline approaching
  - Research findings relevant to user
  - Task completed that user requested
  - Significant insight discovered
- Agent uses reactions (👍, ✅) instead of messages when appropriate
- Silence as default principle enforced
- Typecheck passes

### US-025: Ambient Behavior - Research Capabilities
**Description**: As a developer, I want the agent to do deep research during perch time so that it can provide valuable insights.

**Acceptance Criteria**:
- Agent researches topics from `state/inbox.md` or `state/research/`
- Agent uses web search tools when needed
- Agent synthesizes findings into insight files
- Research stored in `state/research/` directory
- Research results shared with user when relevant
- Typecheck passes

### US-026: Daily Self-Improvement - RSS Feed Integration
**Description**: As a developer, I want the agent to fetch RSS feeds so that it can learn from external sources.

**Acceptance Criteria**:
- `add_rss_feed(url, name)` tool adds RSS feed
- `fetch_rss_feeds()` tool fetches latest from all feeds
- `process_rss_article(url, content)` tool processes articles
- RSS feeds stored in config
- Articles processed for learning (agent architectures, memory systems, MCP servers)
- Typecheck passes

### US-027: Daily Self-Improvement - Night-Time Scheduler
**Description**: As a developer, I want the agent to start daily self-improvement cycle at night so that it creates a PR by morning.

**Acceptance Criteria**:
- Scheduler triggers at 11 PM (configurable)
- `schedule_daily_improvement(time)` tool schedules cycle
- Cycle can be manually triggered: `@agent improve yourself`
- Cycle stops when PR is created
- Typecheck passes

### US-028: Daily Self-Improvement - Research Phase
**Description**: As a developer, I want the agent to research improvements during the daily cycle so that it learns from external sources.

**Acceptance Criteria**:
- Agent fetches all RSS feeds
- Agent processes new articles
- Agent extracts learnings and insights
- Agent stores research in `state/research/improvements/`
- Agent focuses on: agent architectures, memory systems, MCP servers, Claude updates
- Typecheck passes

### US-029: Daily Self-Improvement - Thinking Phase
**Description**: As a developer, I want the agent to analyze its behavior and plan improvements during the daily cycle.

**Acceptance Criteria**:
- Agent analyzes current behavior via logs (`query_logs("recent failures")`)
- Agent reviews journal entries
- Agent identifies patterns (what works, what doesn't)
- Agent reviews Test Agent feedback history
- Agent plans specific improvements
- Thinking phase results stored
- Typecheck passes

### US-030: Daily Self-Improvement - Implementation and Testing
**Description**: As a developer, I want the agent to implement improvements and test them via Test Agent during the daily cycle.

**Acceptance Criteria**:
- Agent works in isolated directory: `work/self-improvement-YYYY-MM-DD/`
- Agent clones memory blocks for testing
- Agent makes incremental changes
- Agent tests each change via Test Agent before proceeding
- Agent iterates based on Test Agent feedback
- Agent only proceeds if Test Agent approves
- Typecheck passes

### US-031: Daily Self-Improvement - PR Creation by Morning
**Description**: As a developer, I want the agent to create a PR by morning so that I can review improvements daily.

**Acceptance Criteria**:
- Agent creates PR only if Test Agent feedback is positive
- PR includes detailed description of changes
- PR links to research sources
- PR links to Test Agent validation results
- Agent notifies user via Slack with PR link
- Cycle stops when PR is created
- Typecheck passes

### US-032: Daily Self-Improvement - Manual Trigger
**Description**: As a developer, I want to manually trigger the self-improvement cycle so that I can request improvements on demand.

**Acceptance Criteria**:
- User can trigger via Slack: `@agent improve yourself`
- Manual trigger follows same workflow as scheduled cycle
- Manual trigger can interrupt scheduled cycle
- Manual trigger results logged
- Typecheck passes
