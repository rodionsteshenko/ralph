# STRIX-Inspired Slack Agent Design

## Overview

A stateful Slack bot agent built on Claude Code SDK (MCP server) that maintains persistent memory, tracks clipboard content, manages user preferences, and includes a dual-agent architecture for self-improvement and testing.

**Core Concept**: Like STRIX, this agent maintains identity and continuity across conversations through structured memory, proactive behavior, and self-modification capabilities.

---

## Architecture Overview

### Two-Agent System

1. **Main Agent** (Primary)
   - Handles user interactions via Slack (single-user DM)
   - Maintains memory and state
   - Self-modifying via git branches/PRs
   - Clones own repo, makes changes, tests via Test Agent
   - Proactive behavior (ambient "perch time")
   - Daily self-improvement cycle (night → morning PR)

2. **Test Agent** (Secondary)
   - Tests Main Agent's behavior and responses
   - Receives cloned memory from Main Agent for testing
   - Provides feedback loop for improvement
   - Runs tests, validates responses, checks quality
   - **Cannot modify Main Agent** (only user can modify Main Agent)
   - Communicates with Main Agent via Slack

### Communication Flow

```
User → Slack DM → Main Agent → [Memory/State] → Response
                              ↓
                    Main Agent clones repo
                              ↓
                    Main Agent makes changes
                              ↓
                    Main Agent → Slack → Test Agent (with cloned memory)
                              ↓
                    Test Agent validates & provides feedback
                              ↓
                    Main Agent evaluates feedback (like/dislike)
                              ↓
                    Main Agent creates branch/PR
                              ↓
                    User reviews & merges
```

**Key Constraint**: Only the user can modify Main Agent. Test Agent only tests and provides feedback.

---

## Core Components

### 1. MCP Server (Claude Code SDK)

The MCP server exposes tools to Claude. Based on STRIX's architecture:

#### Slack Tools
- `send_message` - Send message to Slack channel/DM
- `react` - Add reaction (👍, ✅, etc.)
- `send_image` - Send AI-generated or rendered images
- `get_slack_history` - Retrieve conversation history

#### Memory Tools (Letta-style)
- `get_memory(name)` - Retrieve memory block
- `set_memory(name, value)` - Update memory block
- `list_memories()` - List all memory blocks
- `create_memory(name, value)` - Create new memory block

#### Clipboard Tools (macOS only)
- `get_clipboard()` - Get current clipboard content (macOS)
- `watch_clipboard()` - Monitor clipboard changes (macOS pasteboard)
- `ingest_clipboard()` - Add clipboard content to RAG store
- `search_clipboard(query)` - Search clipboard history

#### Database Tools
- `query_db(query)` - Query structured database
- `insert_db(table, data)` - Insert into database
- `update_db(table, id, data)` - Update database record
- `search_db(query, filters)` - Search with filters

#### File Management Tools
- `read_file(path)` - Read file
- `write_file(path, content)` - Write file
- `edit_file(path, instructions)` - Edit file
- `list_files(directory)` - List files
- `grep(pattern, path)` - Search files

#### People Management Tools (File-based)
- `get_person(name)` - Get person file (markdown format)
- `update_person(name, info)` - Update person info
- `list_people()` - List all people files
- `create_person(name, initial_info)` - Create person file
- **Format**: Markdown files (`.md`) - Claude works best with markdown for structured human-readable data

#### Test Agent Tools
- `clone_memory_for_test()` - Clone Main Agent's memory blocks for Test Agent
- `send_to_test_agent(prompt, cloned_memory)` - Send prompt + cloned memory to Test Agent via Slack
- `get_test_feedback()` - Get Test Agent's validation feedback
- `evaluate_test_feedback(feedback)` - Like/dislike Test Agent's feedback
- `run_test_suite(suite_name)` - Run specific test suite via Test Agent
- **Note**: Test Agent receives cloned memory so it has context to test against

#### Scheduling Tools
- `schedule_job(name, cron, prompt)` - Schedule cron job
- `remove_job(name)` - Remove scheduled job
- `list_jobs()` - List all scheduled jobs
- `schedule_daily_improvement(time)` - Schedule daily self-improvement cycle

#### RSS Feed Tools
- `add_rss_feed(url, name)` - Add RSS feed to monitor
- `fetch_rss_feeds()` - Fetch latest from all RSS feeds
- `process_rss_article(url, content)` - Process article for learning
- `list_rss_feeds()` - List all monitored RSS feeds

#### Self-Modification Tools
- `clone_repo(destination)` - Clone own repository to work directory
- `create_branch(name)` - Create git branch for changes
- `commit_changes(message)` - Commit changes
- `create_pr(title, description)` - Create pull request
- `update_skill(name, content)` - Update skill file
- `test_changes_via_test_agent()` - Test changes using Test Agent before PR

#### Logging Tools
- `log_event(type, message, metadata)` - Log event
- `journal_entry(topics, user_stated, my_intent)` - Journal entry
- `query_logs(query)` - Query logs with jq

---

## Memory Architecture (Three-Tier System)

### Tier 1: Core Memory Blocks (Always Loaded)

Stored in Letta-style memory blocks, always present in context:

- **persona** - User background, relationship, working style
- **bot_values** - Agent identity, name, behavioral principles
- **communication_style** - How agent speaks (tone, formality, emoji usage)
- **guidelines** - Operating rules, integrity requirements
- **patterns** - User behavioral patterns (preferences, habits)
- **user_profile** - Structured facts about user (interests, preferences, relationships)

### Tier 2: Index Blocks (Always Loaded, Point to Files)

- **recent_insights** - Points to dated insight files
- **world_context** - External context pointers
- **current_focus** - What user and agent are working on
- **schedule** - Events affecting operating mode
- **clipboard_index** - Recent clipboard entries index

### Tier 3: Files (Loaded On Demand)

```
state/
├── inbox.md              # Unprocessed tasks
├── today.md              # Current priorities (max 3)
├── commitments.md        # Deadlines and promises
├── patterns.md           # Behavioral observations
├── insights/             # Dated insight files
│   ├── 2025-01-15.md
│   └── 2025-01-16.md
├── research/             # Project research
├── drafts/               # Work in progress
├── people/               # One file per person (markdown format)
│   ├── john.md           # Markdown format - Claude-friendly
│   └── sarah.md
└── clipboard/            # Clipboard history
    └── entries.jsonl     # JSONL for structured data
```

---

## Database Schema

### Queryable Database (SQLite)

```sql
-- Clipboard entries
CREATE TABLE clipboard_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    source TEXT,  -- 'clipboard', 'slack', etc.
    tags TEXT,    -- JSON array of tags
    embedding BLOB  -- Vector embedding for search
);

-- User preferences
CREATE TABLE user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    value TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    source TEXT,  -- 'explicit', 'inferred', 'confirmed'
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Agent personality traits
CREATE TABLE personality_traits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trait TEXT NOT NULL,
    value TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    source TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Test results
CREATE TABLE test_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_name TEXT NOT NULL,
    agent_version TEXT,
    passed BOOLEAN,
    result TEXT,
    feedback TEXT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Memory blocks (append-only)
CREATE TABLE memory_blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    value TEXT,
    sort INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

---

## Test Agent Architecture

### Purpose

The Test Agent provides:
1. **Quality Assurance** - Tests Main Agent responses for correctness, tone, adherence to guidelines
2. **Self-Improvement Loop** - Main Agent clones repo, makes changes, tests via Test Agent before PR
3. **Regression Testing** - Ensures changes don't break existing behavior
4. **Behavioral Validation** - Checks that Main Agent follows its personality and values

### Test Agent Capabilities

- **Response Testing**: Given a prompt and Main Agent's response, validate:
  - Correctness
  - Tone/style adherence
  - Completeness
  - User preference alignment

- **Scenario Testing**: Run predefined scenarios:
  - "User asks about X"
  - "User shares clipboard content Y"
  - "User requests reminder"

- **Regression Testing**: Compare current behavior vs. previous versions

- **Feedback Generation**: Provide actionable feedback to Main Agent

### Main Agent → Test Agent Workflow

```python
# Main Agent workflow:
1. Clone own repository to work directory
2. Make changes (code, memory blocks, skills)
3. Clone memory blocks for Test Agent
4. Send test prompts + cloned memory to Test Agent via Slack
5. Test Agent validates changes and provides feedback
6. Main Agent evaluates feedback (like/dislike)
7. If feedback is good → create branch and PR
8. If feedback is bad → iterate on changes
```

### Example Flow

```
Main Agent: "I want to improve my response quality"
  ↓
Main Agent: clone_repo("work/improvement-test")
  ↓
Main Agent: Makes changes to communication_style memory block
  ↓
Main Agent: clone_memory_for_test() → sends to Test Agent
  ↓
Main Agent: send_to_test_agent("Test this new style", cloned_memory)
  ↓
Test Agent (via Slack): Validates response quality
  ↓
Test Agent: "Response quality improved 15%, but tone is too formal"
  ↓
Main Agent: evaluate_test_feedback("dislike") → iterates
  ↓
Main Agent: Adjusts communication_style further
  ↓
Main Agent: Re-tests via Test Agent
  ↓
Test Agent: "✅ All tests passing, tone is perfect"
  ↓
Main Agent: evaluate_test_feedback("like")
  ↓
Main Agent: create_branch("improve-response-quality")
  ↓
Main Agent: commit_changes("Improve response quality based on test feedback")
  ↓
Main Agent: create_pr("Improve Response Quality", "Based on Test Agent validation")
  ↓
User: Reviews PR, merges if approved
```

### Key Constraints

- **Test Agent cannot modify Main Agent** - Only user can modify Main Agent
- **Test Agent receives cloned memory** - So it has context to test against
- **Communication via Slack** - Both agents communicate through Slack DMs
- **Main Agent evaluates feedback** - Can like/dislike Test Agent's validation

---

## Clipboard Integration (macOS)

### How It Works

1. **Monitoring**: Agent monitors macOS pasteboard via `NSPasteboard` API
   - Uses `pyobjc` or `pyperclip` with pasteboard change notifications
   - Monitors `generalPasteboard` for text changes
   - Debounced to avoid excessive ingestion

2. **Ingestion**: When clipboard changes:
   - Extract text content (ignore images/binary for now)
   - Generate embedding (via Claude embeddings API)
   - Store in SQLite database (`clipboard_entries` table)
   - Add to RAG vector store (for similarity search)
   - Auto-tag based on content (using Claude to infer tags)
   - Link to source if possible (e.g., URL if clipboard contains URL)

3. **Retrieval**: Clipboard content searchable via:
   - Vector similarity search (embeddings)
   - Keyword search (SQLite FTS)
   - Tag filtering
   - Time-based filtering
   - Source filtering

### Clipboard Tools (macOS)

- `watch_clipboard()` - Start monitoring macOS pasteboard
- `get_clipboard()` - Get current clipboard content
- `ingest_clipboard()` - Manually ingest current clipboard
- `search_clipboard(query, filters)` - Search clipboard history
- `tag_clipboard(id, tags)` - Add tags to clipboard entry
- `get_clipboard_by_id(id)` - Get specific clipboard entry

### Implementation Notes

- **macOS Only**: Uses `NSPasteboard` via PyObjC or `pyperclip`
- **Debouncing**: Wait 2-3 seconds after clipboard change before ingesting
- **Deduplication**: Check if content already exists (hash-based)
- **Privacy**: User can disable clipboard monitoring via config

---

## Slack Integration

### Replacing Discord with Slack

**Slack API Features Needed:**
- WebSocket RTM or Socket Mode for real-time events
- Slack Events API for message handling
- Slack Web API for sending messages/reactions
- File uploads for images
- Thread support for conversations

### Slack-Specific Tools

```python
# Message handling
send_message(channel, text, thread_ts=None)
react(channel, timestamp, emoji)
send_image(channel, image_path, text=None)

# History
get_slack_history(channel, limit=100)
get_thread_history(channel, thread_ts)

# User info
get_user_info(user_id)
get_channel_info(channel_id)
```

---

## Ambient "Perch Time"

Like STRIX's 2-hour ticks, the agent runs periodic background tasks:

1. **Check inbox.md** - Process unprocessed tasks
2. **Update state files** - Refresh today.md, commitments.md
3. **Research** - Deep dive on topics from backlog
4. **Self-improvement** - Run tests, analyze logs, update skills
5. **Clipboard processing** - Process new clipboard entries
6. **People file updates** - Update person files with new context

**Key Principle**: Silence as default - only message when meaningful.

---

## Self-Modification Workflow

Based on STRIX's git-based approach:

### Daily Self-Improvement Cycle

**Trigger**: Starts at night (configurable time, e.g., 11 PM)
**Goal**: Create one PR by morning
**Process**:

1. **Research Phase**: 
   - Fetch RSS feeds
   - Read new articles/papers
   - Gather information about improvements

2. **Thinking Phase**:
   - Analyze current behavior
   - Identify improvement opportunities
   - Plan changes

3. **Implementation Phase**:
   - Clone repository: `clone_repo("work/self-improvement-YYYY-MM-DD")`
   - Make changes: Edit files, update skills, modify memory blocks
   - Clone memory for Test Agent: `clone_memory_for_test()`

4. **Testing Phase**:
   - Send changes to Test Agent: `send_to_test_agent(prompt, cloned_memory)`
   - Receive feedback: `get_test_feedback()`
   - Evaluate feedback: `evaluate_test_feedback(feedback)`
   - Iterate if needed

5. **PR Creation**:
   - Create branch: `create_branch("self-improve-YYYY-MM-DD")`
   - Commit: `commit_changes("Self-improvement: [description]")`
   - Create PR: `create_pr("Daily Self-Improvement", "Description")`
   - **Stop condition**: PR created → cycle stops

6. **User Review**: User reviews PR in morning, merges if approved

**Manual Trigger**: Can also be manually triggered by user via Slack command: `@agent improve yourself`

**Stop Condition**: Cycle stops when PR is created (success or failure)

### Daily Self-Improvement Cycle Details

#### Research Phase
- Fetch all RSS feeds: `fetch_rss_feeds()`
- Process new articles: `process_rss_article(url, content)`
- Extract learnings and insights
- Store in `state/research/improvements/` directory
- Focus on: agent architectures, memory systems, MCP servers, Claude updates

#### Thinking Phase
- Analyze current behavior via logs: `query_logs("recent failures")`
- Review journal entries: `journal_entry()` analysis
- Identify patterns: What works? What doesn't?
- Review Test Agent feedback history
- Plan specific improvements

#### Implementation Phase
- Work in isolated directory: `work/self-improvement-YYYY-MM-DD/`
- Clone memory blocks for testing
- Make incremental changes
- Test each change via Test Agent before proceeding

#### Testing Phase
- Send comprehensive test suite to Test Agent
- Test Agent validates:
  - Response quality
  - Tone/style consistency
  - Memory coherence
  - User preference alignment
- Main Agent evaluates feedback
- Iterate until Test Agent approves

#### PR Creation
- Only create PR if Test Agent feedback is positive
- Include detailed description of changes
- Link to research sources
- Link to Test Agent validation results

### Regular Self-Modification (On-Demand)

1. **Clone repo**: `clone_repo("work/feature-name")`
2. **Make changes**: Edit files, update skills, modify memory blocks
3. **Test via Test Agent**: Send to Test Agent with cloned memory
4. **Evaluate feedback**: Like/dislike Test Agent's validation
5. **Create branch**: `create_branch("feature-name")`
6. **Commit**: `commit_changes("Description")`
7. **Create PR**: `create_pr("Title", "Description")`
8. **Notify user**: Send Slack message with PR link
9. **User reviews**: User approves/merges PR
10. **Deploy**: Manual deployment (agent doesn't have sudo)

---

## Personality & Preferences System

### User Preferences Storage

```python
# Structured storage
user_preferences = {
    "communication_style": {
        "formality": "casual",
        "emoji_usage": "moderate",
        "response_length": "concise"
    },
    "interests": ["AI", "agents", "memory systems"],
    "dislikes": ["overly technical jargon"],
    "working_hours": {"start": "09:00", "end": "17:00"},
    "timezone": "America/New_York"
}
```

### Agent Personality Traits

```python
personality_traits = {
    "proactivity": "high",  # Proactive vs reactive
    "verbosity": "low",    # Silence as default
    "curiosity": "high",   # Research interests
    "helpfulness": "high",
    "autonomy": "high"     # Self-directed behavior
}
```

### Learning Mechanism

1. **Explicit**: User says "I prefer X"
2. **Inferred**: Agent observes patterns
3. **Confirmed**: Agent asks "Do you prefer X?" → User confirms
4. **Decay**: Confidence decreases over time if not reinforced

---

## Implementation Phases

### Phase 0: Foundation
- [ ] Slack bot setup (Socket Mode)
- [ ] Basic MCP server structure
- [ ] Memory block system (Letta-style)
- [ ] File system structure
- [ ] Basic agent loop

### Phase 1: Core Memory
- [ ] Three-tier memory system
- [ ] Core memory blocks
- [ ] Index blocks
- [ ] File management
- [ ] Git integration

### Phase 2: Clipboard Integration
- [ ] Clipboard monitoring
- [ ] Database schema
- [ ] Vector embeddings
- [ ] RAG integration
- [ ] Search functionality

### Phase 3: Test Agent
- [ ] Test Agent MCP server
- [ ] Test framework
- [ ] Main ↔ Test Agent communication
- [ ] Feedback loop
- [ ] Test result storage

### Phase 4: Self-Modification
- [ ] Git branch management
- [ ] PR creation
- [ ] Skill modification
- [ ] Self-testing workflow

### Phase 5: Personality System
- [ ] User preference tracking
- [ ] Personality trait system
- [ ] Learning mechanisms
- [ ] Preference inference

### Phase 6: Ambient Behavior
- [ ] Perch time scheduler (2-hour ticks)
- [ ] Background task system
- [ ] Proactive messaging
- [ ] Research capabilities

### Phase 7: Daily Self-Improvement Cycle
- [ ] RSS feed integration
- [ ] Night-time scheduler (11 PM start)
- [ ] Research phase (fetch RSS, read articles)
- [ ] Thinking phase (analyze, plan improvements)
- [ ] Implementation + testing via Test Agent
- [ ] PR creation by morning
- [ ] Manual trigger capability

---

## Key Design Principles (from STRIX)

1. **Proactive, not reactive** - Updates state before responding
2. **Silence as default** - Only messages when meaningful
3. **Self-modifying** - Can edit own skills via branches/PRs
4. **Memory is structure** - Three-tier system prevents collapse
5. **Identity scaffolding** - Core blocks provide negentropy flux
6. **Everything traceable** - Git provides provenance
7. **Tools, not scripts** - Tools always visible, scripts only when needed

---

## Clarifications (Answered)

✅ **Test Agent Scope**: Test Agent cannot modify Main Agent. Only user can modify Main Agent. Test Agent only tests and provides feedback.

✅ **Clipboard Monitoring**: macOS only (using macOS pasteboard APIs)

✅ **People Storage**: File-based, markdown format (`.md`) - Claude works best with markdown for structured human-readable data

✅ **Test Agent Memory**: Test Agent receives cloned memory from Main Agent when testing, so it has context to test against

✅ **Self-Improvement Trigger**: 
   - Daily cycle: Starts at night, does research (RSS feeds), thinking, tries to improve, creates PR by morning
   - Stops when PR is created
   - Can be manually triggered

✅ **Slack Setup**: Single-user DM (easiest, no multi-thread management needed)

✅ **Deployment**: Local machine

✅ **Model**: Claude Opus 4.5 (like STRIX)

---

## File Format Decision: Markdown for People Files

**Rationale**: 
- STRIX uses markdown files for people (`state/people/*.md`)
- Claude Code SDK works excellently with markdown
- Human-readable and editable
- Easy to parse and update programmatically
- Supports structured data with headers, lists, etc.

**Format Example**:
```markdown
# John Doe

## Relationship
Friend, coworker

## Context
Met at AI conference 2024. Works on agent systems.

## Preferences
- Prefers concise communication
- Interested in memory architectures

## Recent Interactions
- 2025-01-15: Discussed STRIX architecture
- 2025-01-10: Asked about MCP servers

## Notes
Very technical, asks detailed questions.
```

---

## Next Steps

1. ✅ **Clarifications answered** - All questions resolved
2. **Create detailed MCP server spec** with tool schemas (JSON Schema)
3. **Design Test Agent API** and Slack communication protocol
4. **Create database schema** with indexes (SQLite)
5. **Design file structure** and git workflow
6. **Create PRD** for implementation using Ralph
7. **Design daily self-improvement cycle** scheduler
