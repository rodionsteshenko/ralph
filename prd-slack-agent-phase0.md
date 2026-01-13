# STRIX-Inspired Slack Agent - Phase 0: Foundation

## Project Description

Foundation phase for a stateful Slack bot agent: basic project structure, MCP server setup, Slack connection, database, and file system.

**Branch Name**: `ralph/slack-agent-phase0`

---

## User Stories

### US-001: Project Structure and Dependencies

**Description**: As a developer, I need the basic project structure and dependencies set up so I can start implementing features.

**Acceptance Criteria**:
- Create Python project structure with `pyproject.toml`
- Add dependencies: `slack-sdk`, `anthropic`, `sqlite3`, `pydantic`, `apscheduler`
- Create directory structure: `mcp_server/`, `state/`, `work/`, `tests/`, `src/`
- Add `.gitignore` for Python, SQLite, `.env`, and `work/` directories
- Create `README.md` with project overview and setup instructions
- Typecheck passes

**Priority**: 1

---

### US-002: Basic MCP Server Structure

**Description**: As a developer, I need a basic MCP server structure so I can add tools incrementally.

**Acceptance Criteria**:
- Create `mcp_server/server.py` with MCP server boilerplate
- Implement server initialization and tool registration system
- Create base tool class structure in `mcp_server/base_tool.py`
- Add health check mechanism
- Server can start and respond to basic requests
- Add configuration management in `mcp_server/config.py`
- Typecheck passes

**Priority**: 2

---

### US-003: Slack Bot Setup with Socket Mode

**Description**: As a user, I need the bot to connect to Slack so I can interact with it via DM.

**Acceptance Criteria**:
- Create `src/slack_bot/client.py` with Slack Socket Mode setup
- Implement connection handling with automatic reconnection logic
- Add event listener for messages and reactions
- Implement basic message handler (echo back for testing)
- Bot successfully responds to DM messages
- Store Slack credentials securely in `.env` file (not committed)
- Add error handling and logging for connection issues
- Typecheck passes

**Priority**: 3

---

### US-004: SQLite Database Setup

**Description**: As a developer, I need the SQLite database schema created so I can store structured data.

**Acceptance Criteria**:
- Create `database/schema.sql` with table definitions: `clipboard_entries`, `user_preferences`, `personality_traits`, `test_results`, `memory_blocks`
- Create `database/db.py` with connection management and query helpers
- Implement migration system for schema updates in `database/migrations.py`
- Add indexes for common queries (timestamps, lookups)
- Database automatically initializes on first run
- Add database health check function
- Typecheck passes

**Priority**: 4

---

### US-005: File System Structure

**Description**: As a developer, I need the file system structure created so memory can be persisted to files.

**Acceptance Criteria**:
- Create directory structure: `state/insights/`, `state/research/`, `state/drafts/`, `state/people/`, `state/clipboard/`
- Create initial state files: `state/inbox.md`, `state/today.md`, `state/commitments.md`, `state/patterns.md`
- Add `.gitkeep` files to preserve empty directories in git
- Create utility module `src/file_utils.py` with functions to ensure directories exist
- Add initialization function to create all required directories and files with templates
- Document file structure in `docs/FILE_STRUCTURE.md`
- Typecheck passes

**Priority**: 5

---
