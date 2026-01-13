# Test Slack Agent - Minimal PRD

## Project Description

A minimal test of a Slack bot agent with basic memory and file management capabilities.

**Branch Name**: `ralph/test-minimal`

---

## User Stories

### US-001: Project Structure Setup

**Description**: As a developer, I need the basic project structure and dependencies set up so I can start implementing features.

**Acceptance Criteria**:
- Create Python project with `pyproject.toml`
- Add dependencies: `slack-sdk`, `anthropic`, `pydantic`
- Create directory structure: `src/`, `tests/`
- Add `.gitignore` for Python
- Create basic `README.md`
- Typecheck passes

**Priority**: 1

---

### US-002: Memory Block System

**Description**: As a developer, I need a simple memory block storage system so the agent can maintain state.

**Acceptance Criteria**:
- Create `src/memory.py` with memory storage
- Implement `get_memory(name)` and `set_memory(name, value)` functions
- Store memory in JSON file (`state/memory.json`)
- Initialize with default memory blocks: `persona`, `bot_values`
- Add unit tests in `tests/test_memory.py`
- All tests pass
- Typecheck passes

**Priority**: 2

---

### US-003: Basic Slack Bot Connection

**Description**: As a user, I need the bot to connect to Slack so I can send it messages.

**Acceptance Criteria**:
- Create `src/slack_bot.py` with Slack Socket Mode setup
- Implement connection handling
- Add message event listener
- Bot echoes back received messages
- Store Slack token in `.env` file (gitignored)
- Add integration test (mocked)
- All tests pass
- Typecheck passes

**Priority**: 3

---

### US-004: File Management Tools

**Description**: As an agent, I need basic file management so I can read and write state files.

**Acceptance Criteria**:
- Create `src/file_tools.py` with file operations
- Implement `read_file(path)` and `write_file(path, content)` functions
- Restrict operations to `state/` directory for safety
- Add error handling for missing files
- Add unit tests
- All tests pass
- Typecheck passes

**Priority**: 4

---
