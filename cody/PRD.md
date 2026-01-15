# Cody: Personal AI Assistant PRD

## Project Overview

**Project**: Cody Personal Assistant
**Branch**: ralph/cody-assistant
**Description**: A stateful, personal AI assistant with persistent memory, temporal awareness, and skill-based architecture. Built on Claude Agent SDK (Python) with a CLI interface initially, expanding to Slack.

## Development Strategy

**Two Execution Modes**:
1. **Non-Interactive Mode**: Single message → agent response → exit. No long-running processes. Ideal for testing and scripting.
2. **Interactive Mode**: REPL with ongoing conversation. Long-running with message history.

**Testing Philosophy**:
- Build non-interactive mode first (testable)
- E2E tests validate real Claude Agent SDK calls
- Each phase ends with E2E validation stories
- Unit tests use mocks; E2E tests use real APIs

**Logging Strategy**:
- Log EVERY Claude interaction to JSONL files
- Log format: timestamp, prompt (full), response, tools_called, duration, tokens
- Logs are append-only, never deleted during development
- Build log parsers to review interactions during development
- Logs enable debugging, prompt tuning, and regression testing

---

## Phase 1: Core Loop (Foundation)

### US-001: Project Structure and Dependencies

**Description**: As a developer, I need the basic project structure and dependencies set up so I can start implementing features.

**Acceptance Criteria**:
- Create Python project in `cody/` directory with `pyproject.toml`
- Add dependencies: `claude-agent-sdk`, `pyyaml`, `rich` (for CLI), `pytest`
- Create directory structure: `cody/src/`, `cody/tests/`, `.cody/`
- Add `.gitignore` for Python, `.cody/data/`, `__pycache__`
- Create `Makefile` with: `install`, `test`, `typecheck`, `lint`, `format`
- Create basic `README.md` with project overview and setup instructions
- Run `make install` successfully
- Typecheck passes

### US-002: Configuration System

**Description**: As a developer, I need a configuration system so settings are centralized and easy to modify.

**Acceptance Criteria**:
- Create `cody/src/config.py` with CodyConfig class
- Support `.cody/config.yaml` for settings
- Load user timezone, assistant name, context window size (default: 40)
- Load paths for memory, state, skills, journal
- Default values for all optional settings
- Validation for required settings with clear error messages
- Environment variable overrides for secrets
- Unit tests for config loading
- Typecheck passes

### US-003: Message Data Structures

**Description**: As a developer, I need message data structures so conversation history can be tracked.

**Acceptance Criteria**:
- Create `cody/src/messages.py` with Message dataclass
- Fields: role (user/assistant), content, timestamp, timezone
- Create MessageWindow class with sliding window logic
- Implement add(), get_context(), clear() methods
- Max messages configurable (default: 40)
- Unit tests for window behavior (add, overflow, clear)
- Typecheck passes

### US-004: Message Persistence

**Description**: As a developer, I need message persistence so conversations survive restarts.

**Acceptance Criteria**:
- Add persist(path) method to MessageWindow
- Add load(path) method to MessageWindow
- Store as JSON in `.cody/messages.json`
- Handle missing file gracefully (start empty)
- Handle corrupted file gracefully (start empty, log warning)
- Unit tests for persistence round-trip
- Typecheck passes

### US-005: Temporal Context

**Description**: As a developer, I need temporal context so the agent knows the current time.

**Acceptance Criteria**:
- Create `cody/src/temporal.py` with TemporalContext class
- Include: current_time, user_timezone, day_of_week, is_weekend, time_of_day
- Format time in human-readable format for system prompt
- Support "morning", "afternoon", "evening", "night" labels
- Method to generate context string for prompt injection
- Unit tests for time-of-day classification
- Typecheck passes

### US-006: Non-Interactive CLI Mode

**Description**: As a developer, I need a non-interactive CLI mode so I can test the agent with single messages.

**Acceptance Criteria**:
- Create `cody/src/cli.py` with main entry point
- Accept single message as argument: `python -m cody.src.cli "Hello"`
- Print agent response to stdout
- Exit with code 0 on success, non-zero on error
- No interactive prompts or loops
- Support `--verbose` flag for debug output
- Support `--config` flag for custom config path
- Typecheck passes

### US-007: Orchestrator Core Loop (Non-Interactive)

**Description**: As a developer, I need the orchestrator to process a single message and return the response.

**Acceptance Criteria**:
- Create `cody/src/orchestrator.py` with Orchestrator class
- Method: `process_message(user_input: str) -> str`
- Build context with temporal info
- Invoke Claude via Agent SDK
- Return final assistant response as string
- No side effects beyond response (no persistence yet)
- Unit tests with mocked Claude SDK
- Typecheck passes

### US-008: Claude Agent SDK Integration

**Description**: As a developer, I need Claude Agent SDK integration so the orchestrator can call Claude.

**Acceptance Criteria**:
- Create `cody/src/claude_client.py` with ClaudeClient class
- Use `claude-agent-sdk` ClaudeSDKClient
- Support system prompt injection
- Handle streaming responses
- Return final response text
- Handle API errors with clear error messages
- Typecheck passes

### US-008A: Interaction Logging Infrastructure

**Description**: As a developer, I need all Claude interactions logged so I can review and debug prompts.

**Acceptance Criteria**:
- Create `cody/src/logging.py` with InteractionLogger class
- Log to `.cody/logs/interactions.jsonl` (append-only)
- Log entry fields: timestamp, request_id (UUID), system_prompt, user_message, full_context, response, tools_called[], duration_ms, error (if any)
- Each interaction gets unique request_id for tracing
- Log BEFORE sending to Claude (intent) and AFTER receiving (result)
- Rotate logs by date: `interactions-YYYY-MM-DD.jsonl`
- Never delete logs automatically
- Unit tests for log format
- Typecheck passes

### US-008B: Log Parser CLI Tool

**Description**: As a developer, I need a CLI tool to parse and view interaction logs so I can review Claude conversations.

**Acceptance Criteria**:
- Create `cody/src/log_parser.py` with LogParser class
- Command: `python -m cody.src.log_parser .cody/logs/interactions.jsonl`
- Support `--last N` to show last N interactions
- Support `--request-id UUID` to show specific interaction
- Support `--errors` to show only failed interactions
- Support `--json` for machine-readable output
- Support `--prompts-only` to show just the prompts sent
- Pretty-print with colors (using rich)
- Typecheck passes

### US-008C: Log Summary Statistics

**Description**: As a developer, I need log summary statistics so I can understand usage patterns.

**Acceptance Criteria**:
- Add `--stats` flag to log_parser
- Show: total interactions, success/error counts, avg duration
- Show: most common tools called
- Show: date range of logs
- Show: estimated token usage (based on prompt length heuristic)
- Format output clearly with headers
- Typecheck passes

### US-009: Phase 1 E2E Validation - Basic Chat

**Description**: As a developer, I need E2E tests for basic chat so I can validate the core loop works.

**Acceptance Criteria**:
- Create `cody/tests/e2e/test_basic_chat.py`
- Test non-interactive CLI with real Claude Agent SDK
- Test: simple greeting returns response
- Test: question about time includes temporal awareness
- Test: error handling for invalid input
- Verify interaction logged to JSONL file
- Use log_parser to verify log format is correct
- Mark tests with `@pytest.mark.e2e`
- Skip if Claude CLI not authenticated
- Tests pass with `pytest -m e2e`
- Typecheck passes

### US-010: Phase 1 E2E Validation - Message Window

**Description**: As a developer, I need E2E tests for message history so I can validate context is maintained.

**Acceptance Criteria**:
- Create `cody/tests/e2e/test_message_context.py`
- Test: two sequential messages, second references first
- Test: agent recalls information from previous message
- Test: message window persists between CLI invocations
- Test: window overflow drops oldest messages
- Verify all interactions logged with full context in JSONL
- Parse logs to verify context includes previous messages
- Mark tests with `@pytest.mark.e2e`
- Tests pass with `pytest -m e2e`
- Typecheck passes

### US-010A: Phase 1 E2E Validation - Logging Infrastructure

**Description**: As a developer, I need E2E tests for logging so I can validate all interactions are captured.

**Acceptance Criteria**:
- Create `cody/tests/e2e/test_logging.py`
- Test: interaction creates log entry with all required fields
- Test: log_parser can read and display the entry
- Test: multiple interactions append to same log file
- Test: log rotation creates new file on date change
- Test: --stats flag produces valid output
- Test: --errors flag filters correctly
- Mark tests with `@pytest.mark.e2e`
- Tests pass with `pytest -m e2e`
- Typecheck passes

---

## Phase 2: Memory & Journal

### US-011: Memory Block Storage

**Description**: As a developer, I need a memory block storage system so the agent can maintain persistent identity.

**Acceptance Criteria**:
- Create `cody/src/memory.py` with MemoryManager class
- Store memory blocks as markdown files in `.cody/memory/`
- Implement get_memory(name), set_memory(name, content), list_memories()
- Track last_updated timestamp per block (in frontmatter or separate metadata)
- Handle missing blocks gracefully
- Unit tests for CRUD operations
- Typecheck passes

### US-012: Core Memory Block Initialization

**Description**: As a developer, I need default memory blocks initialized so the agent has identity.

**Acceptance Criteria**:
- Create default `persona.md` with assistant personality
- Create default `user.md` with user profile template
- Create default `current_focus.md` (empty initially)
- Create default `patterns.md` for learned behaviors
- Create default `limitations.md` for boundaries
- Create `cody/src/memory/defaults/` with default content
- Initialize on first run if blocks don't exist
- Unit tests for initialization
- Typecheck passes

### US-013: Memory Context Integration

**Description**: As a developer, I need memory blocks loaded into context so the agent has access to identity.

**Acceptance Criteria**:
- Update Orchestrator to load memory blocks on startup
- Inject memory blocks into system prompt
- Format blocks with clear section headers
- Limit total memory context size (configurable, default: 4000 tokens estimate)
- Prioritize: persona > user > current_focus > others
- Unit tests for context building
- Typecheck passes

### US-014: Memory MCP Tools

**Description**: As an agent, I need memory tools so I can read and update memory blocks.

**Acceptance Criteria**:
- Create `cody/src/skills/core.py` with memory tools
- Implement memory_read tool using @tool decorator
- Implement memory_write tool using @tool decorator
- Implement memory_list tool using @tool decorator
- Tools registered with MCP server via SkillRegistry
- memory_write updates file and timestamp
- Unit tests for tool execution
- Typecheck passes

### US-015: Journal System

**Description**: As a developer, I need a journal system so the agent has temporal awareness of past events.

**Acceptance Criteria**:
- Create `cody/src/journal.py` with JournalManager class
- Store entries as JSONL in `.cody/journal.jsonl`
- Entry fields: timestamp, type, topics[], content, user_stated, agent_intent
- Implement add_entry(), get_recent(n), search(query)
- Handle missing file gracefully
- Unit tests for journal operations
- Typecheck passes

### US-016: Journal Context Integration

**Description**: As a developer, I need recent journal entries in context so the agent has temporal awareness.

**Acceptance Criteria**:
- Update Orchestrator to load recent journal entries
- Inject last N entries into system prompt (default: 40)
- Format entries with timestamps and topics
- Limit journal context size
- Unit tests for journal context building
- Typecheck passes

### US-017: Journal MCP Tool

**Description**: As an agent, I need a journal tool so I can record observations and intentions.

**Acceptance Criteria**:
- Add journal_entry tool to core.py
- Accept: type, topics (array), content, user_stated (optional), agent_intent (optional)
- Append to journal.jsonl with timestamp
- Return confirmation with entry ID
- Unit tests for tool execution
- Typecheck passes

### US-018: State File Management

**Description**: As an agent, I need state files so I can track tasks and commitments.

**Acceptance Criteria**:
- Create `.cody/state/` directory structure
- Initialize: inbox.md, today.md, commitments.md
- Create `cody/src/state.py` with StateManager class
- Implement read_state(name), write_state(name, content), list_states()
- Add state_read and state_write MCP tools
- Unit tests for state operations
- Typecheck passes

### US-019: Phase 2 E2E Validation - Memory

**Description**: As a developer, I need E2E tests for memory so I can validate persistence works.

**Acceptance Criteria**:
- Create `cody/tests/e2e/test_memory.py`
- Test: agent can read persona block
- Test: agent can update user block via tool
- Test: updated memory persists between sessions
- Test: agent behavior reflects persona content
- Verify logs show memory_read and memory_write tool calls
- Parse logs to confirm memory content was in context
- Mark tests with `@pytest.mark.e2e`
- Tests pass with `pytest -m e2e`
- Typecheck passes

### US-020: Phase 2 E2E Validation - Journal

**Description**: As a developer, I need E2E tests for journal so I can validate temporal awareness works.

**Acceptance Criteria**:
- Create `cody/tests/e2e/test_journal.py`
- Test: agent can create journal entry via tool
- Test: journal entry appears in subsequent context
- Test: agent can reference "yesterday I noted..." from journal
- Test: journal search returns relevant entries
- Verify logs show journal_entry tool calls with correct params
- Parse logs to confirm journal entries injected in context
- Mark tests with `@pytest.mark.e2e`
- Tests pass with `pytest -m e2e`
- Typecheck passes

---

## Phase 3: Skills Infrastructure

### US-021: Skill Registry

**Description**: As a developer, I need a skill registry so all tools are organized and loadable.

**Acceptance Criteria**:
- Create `cody/src/skills/__init__.py` with SkillRegistry class
- Auto-discover skill modules from skills/ directory
- Collect all @tool decorated functions from modules
- Create unified MCP server with all tools
- Method: get_mcp_server() returns configured server
- Method: list_tools() returns tool names and descriptions
- Unit tests for discovery and registration
- Typecheck passes

### US-022: Reply Tool

**Description**: As an agent, I need a reply tool so I can send messages to the user during processing.

**Acceptance Criteria**:
- Add reply tool to core.py
- Parameters: message (str), style (str: "normal"|"thinking"|"update")
- In non-interactive mode: print to stdout immediately
- In interactive mode: display with appropriate formatting
- Return confirmation
- Unit tests for tool execution
- Typecheck passes

### US-023: Context Builder

**Description**: As a developer, I need a context builder so prompts include all relevant state.

**Acceptance Criteria**:
- Create `cody/src/context.py` with ContextBuilder class
- Combine: memory blocks, recent journal, temporal context, skill descriptions
- Format as structured system prompt with clear sections
- Include user profile and current focus prominently
- Estimate token count and warn if over limit
- Method: build() returns formatted system prompt string
- Unit tests for context assembly
- Typecheck passes

### US-024: Interactive CLI Mode (REPL)

**Description**: As a user, I need an interactive REPL mode so I can have ongoing conversations.

**Acceptance Criteria**:
- Add `--repl` flag to CLI
- Display welcome message on startup
- Prompt: `You: ` for user input
- Display agent responses with rich formatting
- Show thinking indicator while processing
- Support conversation history within session
- Exit with "exit", "quit", or Ctrl+D
- Handle interrupts (Ctrl+C) gracefully
- Typecheck passes

### US-025: Phase 3 E2E Validation - Skills

**Description**: As a developer, I need E2E tests for skill infrastructure so I can validate tools work.

**Acceptance Criteria**:
- Create `cody/tests/e2e/test_skills.py`
- Test: agent can call reply tool to send update
- Test: agent can call memory tools
- Test: agent can call journal tool
- Test: all tools listed in tool descriptions
- Verify logs capture all tool calls with parameters
- Parse logs to verify tool results are recorded
- Mark tests with `@pytest.mark.e2e`
- Tests pass with `pytest -m e2e`
- Typecheck passes

### US-026: Phase 3 E2E Validation - REPL

**Description**: As a developer, I need E2E tests for REPL so I can validate interactive mode works.

**Acceptance Criteria**:
- Create `cody/tests/e2e/test_repl.py`
- Test: REPL starts and shows welcome message
- Test: multi-turn conversation maintains context
- Test: REPL exits cleanly on "exit" command
- Test: REPL handles Ctrl+C gracefully
- Use subprocess to test REPL as black box
- Mark tests with `@pytest.mark.e2e`
- Tests pass with `pytest -m e2e`
- Typecheck passes

---

## Phase 4: Core Skills

### US-027: Weather Skill

**Description**: As an agent, I need a weather skill so I can check weather conditions.

**Acceptance Criteria**:
- Create `cody/src/skills/weather.py`
- Implement weather tool with location parameter
- Use free weather API (wttr.in or Open-Meteo)
- Return current conditions: temp, conditions, humidity
- Return forecast summary if available
- Support default location from config
- Handle API errors gracefully with user-friendly message
- Unit tests with mocked API
- Typecheck passes

### US-028: RSS Feed Management

**Description**: As an agent, I need RSS feed management so I can track news sources.

**Acceptance Criteria**:
- Create `cody/src/skills/infostream.py`
- Implement add_feed tool: add RSS feed URL with name
- Implement list_feeds tool: show configured feeds
- Store feed config in `.cody/data/rss/feeds.json`
- Use feedparser library for parsing
- Unit tests for feed management
- Typecheck passes

### US-029: RSS Article Fetching

**Description**: As an agent, I need to fetch RSS articles so I can access news content.

**Acceptance Criteria**:
- Implement fetch_feeds tool: fetch all configured feeds
- Cache articles in `.cody/data/rss/cache.json`
- Deduplicate by article URL
- Store: title, link, summary, published, feed_name
- Only fetch articles from last 24 hours
- Implement search_articles tool: search cached articles by keyword
- Unit tests for fetch and cache
- Typecheck passes

### US-030: Clipboard Skill

**Description**: As an agent, I need a clipboard skill so I can access copied content.

**Acceptance Criteria**:
- Add get_clipboard tool to infostream.py
- Use pyperclip for cross-platform clipboard access
- Return current clipboard contents (text only)
- Truncate very long content (>10000 chars) with note
- Handle empty clipboard gracefully
- Handle non-text clipboard gracefully
- Unit tests with mocked clipboard
- Typecheck passes

### US-031: Web Search Skill

**Description**: As an agent, I need a search skill so I can find information online.

**Acceptance Criteria**:
- Create `cody/src/skills/search.py`
- Implement web_search tool with query parameter
- Use DuckDuckGo instant answer API or similar free service
- Return top N results (default: 5) with titles and snippets
- Handle rate limiting with retry
- Handle API errors gracefully
- Unit tests with mocked API
- Typecheck passes

### US-032: Image Generation Skill

**Description**: As an agent, I need an image generation skill so I can create visuals.

**Acceptance Criteria**:
- Create `cody/src/skills/images.py`
- Implement generate_image tool with prompt parameter
- Support configurable provider in config (replicate, openai)
- Require API key in environment variable
- Save generated images to `.cody/data/images/` with timestamp name
- Return file path
- Handle API errors gracefully
- Unit tests with mocked API
- Typecheck passes

### US-033: Phase 4 E2E Validation - External Skills

**Description**: As a developer, I need E2E tests for external skills so I can validate API integrations work.

**Acceptance Criteria**:
- Create `cody/tests/e2e/test_external_skills.py`
- Test: weather tool returns real weather data
- Test: RSS fetch retrieves real articles
- Test: clipboard tool reads real clipboard
- Test: web search returns real results
- Verify logs capture external API call metadata
- Parse logs to verify tool parameters and responses
- Skip tests if required API keys not set
- Mark tests with `@pytest.mark.e2e`
- Tests pass with `pytest -m e2e`
- Typecheck passes

### US-034: Phase 4 E2E Validation - Full Agent Loop

**Description**: As a developer, I need E2E tests for the full agent loop so I can validate all skills work together.

**Acceptance Criteria**:
- Create `cody/tests/e2e/test_full_agent.py`
- Test: "What's the weather?" triggers weather tool and returns result
- Test: "What's in my clipboard?" triggers clipboard tool
- Test: "Remember that I prefer dark mode" updates user memory
- Test: "What did we discuss?" references conversation history
- Review logs after each test to verify correct tool selection
- Parse logs to verify full prompt context is correct
- Log review checklist: context size, tools available, tool calls made
- Mark tests with `@pytest.mark.e2e`
- Tests pass with `pytest -m e2e`
- Typecheck passes

---

## Phase 5: Slack Interface

### US-035: Slack Bot Setup

**Description**: As a developer, I need Slack bot infrastructure so Cody can be accessed via Slack.

**Acceptance Criteria**:
- Create `cody/src/slack/client.py` with SlackClient class
- Use slack-sdk library with Socket Mode
- Implement connection handling and auto-reconnection
- Store credentials in environment variables (SLACK_BOT_TOKEN, SLACK_APP_TOKEN)
- Add health check method
- Log connection events
- Typecheck passes

### US-036: Slack Message Handler

**Description**: As a user, I need Cody to respond to Slack messages so I can chat via Slack.

**Acceptance Criteria**:
- Create `cody/src/slack/handler.py` with MessageHandler class
- Listen for message events in DMs
- Listen for @mentions in channels
- Filter out bot's own messages
- Pass message content through orchestrator
- Send response back to same channel/DM
- Handle errors gracefully (send error message to user)
- Typecheck passes

### US-037: Slack Thread Support

**Description**: As a user, I need Cody to support threads so conversations stay organized.

**Acceptance Criteria**:
- Track thread_ts for threaded conversations
- Reply in thread when message is in thread
- Maintain separate message window per thread (keyed by thread_ts)
- Start new context for new threads
- Clean up old thread contexts after 24 hours
- Unit tests for thread tracking
- Typecheck passes

### US-038: Slack Reaction Tool

**Description**: As an agent, I need to add reactions so I can provide quick feedback.

**Acceptance Criteria**:
- Create `cody/src/skills/slack.py`
- Add react tool: add emoji reaction to message
- Parameters: channel, timestamp, emoji
- Support common emojis: eyes, thumbsup, thumbsdown, white_check_mark
- Handle reaction errors gracefully
- Unit tests with mocked Slack API
- Typecheck passes

### US-039: Slack File Sharing Tool

**Description**: As an agent, I need to share files so I can send images and documents.

**Acceptance Criteria**:
- Add send_file tool to slack.py
- Parameters: channel, file_path, message (optional)
- Support uploading local files from `.cody/data/`
- Support sharing generated images
- Handle upload size limits
- Handle upload errors gracefully
- Unit tests with mocked Slack API
- Typecheck passes

### US-040: Slack Entry Point

**Description**: As a developer, I need a Slack bot entry point so the bot can be run as a service.

**Acceptance Criteria**:
- Create `cody/src/slack/main.py` as entry point
- Command: `python -m cody.src.slack.main`
- Initialize orchestrator with Slack-specific config
- Start Socket Mode connection
- Handle graceful shutdown on SIGINT/SIGTERM
- Log startup and shutdown events
- Typecheck passes

### US-041: Phase 5 E2E Validation - Slack Connection

**Description**: As a developer, I need E2E tests for Slack connection so I can validate bot setup works.

**Acceptance Criteria**:
- Create `cody/tests/e2e/test_slack_connection.py`
- Test: bot connects to Slack successfully
- Test: bot receives test message
- Test: bot sends response
- Test: bot handles reconnection after disconnect
- Require SLACK_BOT_TOKEN and SLACK_APP_TOKEN
- Skip if tokens not set
- Mark tests with `@pytest.mark.e2e`
- Typecheck passes

### US-042: Phase 5 E2E Validation - Full Slack Integration

**Description**: As a developer, I need E2E tests for full Slack integration so I can validate all features work.

**Acceptance Criteria**:
- Create `cody/tests/e2e/test_slack_full.py`
- Test: DM conversation works end-to-end
- Test: channel @mention triggers response
- Test: thread replies stay in thread
- Test: reactions can be added
- Test: files can be uploaded
- Use test Slack workspace
- Mark tests with `@pytest.mark.e2e`
- Typecheck passes
