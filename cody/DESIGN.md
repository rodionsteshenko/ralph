# Cody: Personal AI Assistant Design Document

## Overview

Cody is a stateful, personal AI assistant inspired by [Strix](https://timkellogg.me/blog/2025/12/15/strix). It maintains persistent memory, temporal awareness, and proactive behavior through a skill-based architecture. Unlike typical conversational AI, Cody remembers context across sessions, understands who you are, and can access external information streams.

**Core Philosophy**: "If you didn't write it down, you won't remember it next message."

## Technology Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Orchestrator | Python | Uses [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python) |
| Skills | Python (or any CLI) | In-process MCP servers preferred, subprocess fallback |
| Memory | File-based (JSON/Markdown) | Simple, versionable, no external deps |
| Interface | CLI → Slack | Start simple, add interfaces later |

```bash
pip install claude-agent-sdk
```

**Why Python?**
- Official Claude Agent SDK with full feature parity
- Already the language of this project (Ralph)
- Great ecosystem: `feedparser` for RSS, `requests`, `rich` for CLI
- In-process MCP servers = no subprocess overhead for skills
- Type hints for safety, async/await for streaming

**Skills as In-Process MCP Servers:**
```python
from claude_agent_sdk import tool, create_sdk_mcp_server

@tool("fetch_weather", "Get current weather", {"location": str})
async def fetch_weather(args):
    # Direct Python - no subprocess needed
    weather = await get_weather_api(args["location"])
    return {"content": [{"type": "text", "text": weather}]}
```

Skills can also be external CLI utilities if needed (polyglot), but in-process is preferred for performance.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI / Slack Interface                    │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Orchestrator (Python)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Message   │  │   Memory    │  │   Context Builder       │  │
│  │   Window    │  │   Manager   │  │   (40 messages + state) │  │
│  │   (N=40)    │  │             │  │                         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│              Claude Agent SDK (claude-agent-sdk)                 │
│                  (ClaudeSDKClient + MCP servers)                 │
└─────────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
              ┌──────────┐  ┌──────────┐  ┌──────────┐
              │  Skills  │  │  Tools   │  │  Memory  │
              │  (in-    │  │  (reply, │  │  Files   │
              │  process │  │  journal │  │  (md/json│
              │  MCP)    │  │  etc.)   │  │  files)  │
              └──────────┘  └──────────┘  └──────────┘
```

## Core Components

### 1. Orchestrator (Outer Loop)

The orchestrator is the main control loop that:
- Maintains the message window (last N=40 messages)
- Builds context for each Claude invocation
- Manages skill loading and availability
- Persists conversation state between sessions
- Injects temporal context (current time, timezone)

```python
from dataclasses import dataclass
from datetime import datetime
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, create_sdk_mcp_server

@dataclass
class CodyConfig:
    user_timezone: str
    paths: dict

class Orchestrator:
    """Main control loop managing conversation state and Claude invocations."""

    def __init__(self, config: CodyConfig):
        self.config = config
        self.message_window = MessageWindow(max_messages=40)
        self.memory = MemoryManager(config.paths["memory"])
        self.skills = SkillRegistry(config.paths["skills"])

    async def process_message(self, user_input: str) -> str:
        # 1. Add timestamp to message
        message = Message(
            role="user",
            content=user_input,
            timestamp=datetime.now(),
            timezone=self.config.user_timezone,
        )
        self.message_window.add(message)

        # 2. Build context (memory blocks + journal + temporal)
        context = await self.build_context(message)

        # 3. Get all skill tools (always available)
        mcp_server = self.skills.get_mcp_server()

        # 4. Invoke Claude via Agent SDK
        options = ClaudeAgentOptions(
            mcp_servers={"skills": mcp_server},
            system_prompt=context,
        )
        async with ClaudeSDKClient(options=options) as client:
            await client.query(user_input)
            async for msg in client.receive_response():
                # 5. Process tool calls (reply, memory updates, etc.)
                await self.handle_message(msg)

        # 6. Persist state changes
        await self.message_window.persist(self.config.paths["messages"])
```

### 2. Message Window

Maintains a sliding window of the last N messages for context continuity.

```python
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import json

@dataclass
class Message:
    role: str  # "user" | "assistant"
    content: str
    timestamp: datetime
    timezone: str

class MessageWindow:
    """Sliding window of recent conversation messages."""

    def __init__(self, max_messages: int = 40):
        self.max_messages = max_messages
        self.messages: list[Message] = []

    def add(self, message: Message) -> None:
        self.messages.append(message)
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)

    def get_context(self) -> list[Message]:
        return self.messages.copy()

    async def persist(self, path: str) -> None:
        data = [
            {
                "role": m.role,
                "content": m.content,
                "timestamp": m.timestamp.isoformat(),
                "timezone": m.timezone,
            }
            for m in self.messages
        ]
        Path(path).write_text(json.dumps(data, indent=2))

    async def load(self, path: str) -> None:
        data = json.loads(Path(path).read_text())
        self.messages = [
            Message(
                role=m["role"],
                content=m["content"],
                timestamp=datetime.fromisoformat(m["timestamp"]),
                timezone=m["timezone"],
            )
            for m in data
        ]
```

### 3. Memory Architecture (Three-Tier)

#### Tier 1: Memory Blocks (Identity)
Persistent identity data loaded into every prompt:

| Block | Purpose |
|-------|---------|
| `persona.md` | Who Cody is, personality traits, communication style |
| `user.md` | Who the user is, preferences, context |
| `current_focus.md` | What we're currently working on |
| `patterns.md` | Learned behavioral patterns |
| `limitations.md` | What Cody should/shouldn't do |

```
.cody/
├── memory/
│   ├── persona.md
│   ├── user.md
│   ├── current_focus.md
│   ├── patterns.md
│   └── limitations.md
```

#### Tier 2: Journal (Temporal Awareness)
JSONL entries tracking events over time. Recent entries (last 40) injected per message.

```json
{
  "timestamp": "2025-01-14T10:30:00-05:00",
  "type": "observation",
  "topics": ["project", "deadline"],
  "content": "User mentioned Ralph demo is Friday",
  "user_stated": "Demo is this Friday",
  "agent_intent": "Track deadline, remind Thursday"
}
```

Journal enables:
- Long-range pattern recognition
- Temporal coherence ("yesterday you said...")
- Proactive reminders

#### Tier 3: State Files (Working Memory)
Files the agent can read/write for task tracking:

```
.cody/
├── state/
│   ├── inbox.md          # Incoming tasks/items
│   ├── today.md          # Today's focus
│   ├── commitments.md    # Promises made
│   └── projects/         # Per-project state
```

### 4. Skills System

Skills are modular capabilities. All skills are always loaded - Claude decides when to use them.

#### Skill Registration

```python
from claude_agent_sdk import tool, create_sdk_mcp_server

# All skills registered together
skills = [
    # Core (fundamental to the loop)
    reply_tool,
    memory_read_tool,
    memory_write_tool,
    journal_tool,

    # Capabilities
    weather_tool,
    search_tool,
    fetch_rss_tool,
    get_clipboard_tool,
    generate_image_tool,
]

mcp_server = create_sdk_mcp_server(
    name="cody-skills",
    version="1.0.0",
    tools=skills,
)
```

#### Available Skills

| Skill | Purpose |
|-------|---------|
| `reply` | Send messages to user (enables streaming updates) |
| `memory_read` | Read memory blocks (persona, user, focus, etc.) |
| `memory_write` | Update memory blocks |
| `journal` | Add journal entries for temporal awareness |
| `weather` | Get current weather and forecasts |
| `search` | Web search |
| `fetch_rss` | Fetch articles from RSS feeds |
| `get_clipboard` | Access clipboard contents |
| `generate_image` | Generate images |

#### Skill Implementation Pattern

Each skill is a decorated async function:

```python
@tool("weather", "Get current weather for a location", {
    "location": str,
    "units": str,  # "metric" | "imperial"
})
async def weather_tool(args):
    location = args["location"]
    units = args.get("units", "imperial")

    # Call weather API
    data = await fetch_weather_api(location, units)

    return {
        "content": [{
            "type": "text",
            "text": f"{data['temp']}°, {data['conditions']} in {location}"
        }]
    }
```

Claude sees the tool name and description, then decides when to use it. If more context is needed about a skill's capabilities, Claude can ask or the skill can return detailed help.

### 5. Reply Tool

A critical design decision: **replies are a tool, not just the final output**.

This enables:
- Streaming updates during long operations
- Multiple messages in one turn
- Silence as a valid response
- Reactions/acknowledgments separate from full responses

```python
from claude_agent_sdk import tool

@tool("reply", "Send a message to the user", {
    "message": str,
    "style": str,  # "normal" | "thinking" | "update" | "error"
})
async def reply_tool(args, context):
    """
    Send a message to the user immediately.
    Enables streaming updates during long operations.
    """
    message = args["message"]
    style = args.get("style", "normal")

    # Get the interface from context (CLI or Slack)
    interface = context.get("interface")
    await interface.send(message, style=style)

    return {"content": [{"type": "text", "text": f"Sent: {message[:50]}..."}]}
```

Example usage in conversation:
```
User: "Summarize the news about AI this week"

[Cody thinking...]
→ reply(style="update"): "Checking RSS feeds..."
→ reply(style="update"): "Found 23 articles, analyzing..."
→ reply(style="normal"): "Here are the key AI stories this week: ..."
```

### 6. Temporal Awareness

Every message includes temporal context:

```python
@dataclass
class TemporalContext:
    current_time: datetime
    user_timezone: str  # e.g., "America/New_York"
    day_of_week: str
    is_weekend: bool
    time_of_day: str  # "morning", "afternoon", "evening", "night"
```

Injected into system prompt:
```
Current time: Tuesday, January 14, 2025 at 10:30 AM (Eastern)
Time of day: Morning
```

This enables:
- Time-aware responses ("Good morning!")
- Deadline awareness ("That's in 3 days")
- Scheduling and reminders

## Data Flow

### Message Processing Flow

```
1. User Input
   │
   ├─► Add timestamp + timezone
   │
2. Context Building
   │
   ├─► Load memory blocks (persona, user, focus)
   ├─► Load recent journal entries (last 40)
   ├─► Load message window (last 40 messages)
   ├─► Inject temporal context
   ├─► All skills available (Claude decides usage)
   │
3. Claude Invocation
   │
   ├─► System prompt + context
   ├─► Available tools (from active skills)
   ├─► Conversation history
   │
4. Response Processing
   │
   ├─► Execute tool calls (reply, memory updates, etc.)
   ├─► Update journal if needed
   ├─► Add assistant message to window
   │
5. Persist State
   │
   └─► Save message window, memory changes, journal
```

## Interface Layer

### Phase 1: CLI

Simple terminal-based chat interface:

```
$ cody

╭─ Cody ────────────────────────────────────────╮
│ Good morning! Ready to help.                  │
╰───────────────────────────────────────────────╯

You: What's on my calendar today?

[thinking...] Checking your focus for today...

╭─ Cody ────────────────────────────────────────╮
│ Based on your current focus:                  │
│ • Ralph demo prep (priority)                  │
│ • Review PR #42                               │
│ • You mentioned a 2pm meeting yesterday       │
╰───────────────────────────────────────────────╯

You:
```

### Phase 2: Slack

Slack bot interface enabling:
- Multi-channel awareness
- Thread replies
- Reactions as feedback
- File/image sharing
- Ambient presence (can be pinged from anywhere)

## Configuration

```yaml
# .cody/config.yaml

user:
  name: "Rodion"
  timezone: "America/New_York"

assistant:
  name: "Cody"

context:
  message_window_size: 40
  journal_entries_per_context: 40

claude:
  model: "claude-sonnet-4-20250514"
  max_tokens: 8192

skills:
  # All skills always loaded - Claude decides when to use them
  rss:
    feeds:
      - name: "HN"
        url: "https://hnrss.org/frontpage"
      - name: "Tech"
        url: "..."

  weather:
    default_location: "New York, NY"
    units: "imperial"

  images:
    provider: "replicate"  # or "openai", etc.

paths:
  memory: ".cody/memory"
  state: ".cody/state"
  skills: ".cody/skills"
  journal: ".cody/journal.jsonl"
  messages: ".cody/messages.json"
```

## Implementation Phases

### Phase 1: Core Loop (Foundation)
- [ ] Orchestrator with message window
- [ ] Memory block loading (persona, user)
- [ ] Temporal context injection
- [ ] Basic CLI interface
- [ ] Reply tool for streaming updates
- [ ] Message persistence between sessions

### Phase 2: Memory & Journal
- [ ] Full memory block system
- [ ] Journal entries (write + inject recent)
- [ ] Memory skill (read/write blocks)
- [ ] State file management

### Phase 3: Skills Infrastructure
- [ ] Skill definition format
- [ ] Skill registry and loading
- [ ] Trigger-based conditional loading
- [ ] Skill hot-reloading

### Phase 4: Core Skills
- [ ] `infostream` - RSS + clipboard access
- [ ] `search` - Web search capability
- [ ] `weather` - Weather data access
- [ ] `images` - Image generation

### Phase 5: Slack Interface
- [ ] Slack bot setup
- [ ] Message handling
- [ ] Thread support
- [ ] Reaction handling
- [ ] File sharing

## File Structure

```
.cody/
├── config.yaml           # Main configuration
├── messages.json         # Persisted message window
├── journal.jsonl         # Journal entries
│
├── memory/               # Memory blocks (identity)
│   ├── persona.md
│   ├── user.md
│   ├── current_focus.md
│   ├── patterns.md
│   └── limitations.md
│
├── state/                # Working memory
│   ├── inbox.md
│   ├── today.md
│   ├── commitments.md
│   └── projects/
│
├── skills/               # Skill implementations (Python modules)
│   ├── __init__.py       # Exports all skill tools
│   ├── core.py           # reply, memory, journal
│   ├── weather.py        # weather tool
│   ├── search.py         # web search tool
│   ├── infostream.py     # RSS + clipboard tools
│   └── images.py         # image generation tool
│
└── data/                 # Skill-specific data
    ├── rss/              # Cached RSS articles
    └── clipboard/        # Clipboard history
```

## Key Design Decisions

### 1. Skills over Hardcoded Tools
Skills are defined in markdown files, making them:
- Easy to add/modify without code changes
- Self-documenting
- Shareable between users
- Versionable in git

### 2. Reply as Tool
Making replies a tool (not just final output) enables:
- Progress updates during long operations
- Multiple messages per turn
- Silence as valid response
- Separation of "thinking" vs "responding"

### 3. Three-Tier Memory
Separating identity (blocks), temporal (journal), and working (state) memory:
- Blocks: Always loaded, rarely changed
- Journal: Append-only, temporal awareness
- State: Frequently updated, task tracking

### 4. All Skills Always Available
All skills loaded for every interaction:
- Claude decides when to use each skill
- No fragile keyword detection
- Simpler implementation
- Can add conditional loading later if context limits become an issue

### 5. Time-First Context
Every interaction includes temporal context:
- Enables time-aware responses
- Supports deadline tracking
- Natural conversation ("yesterday you said...")

## Future Considerations

### Perch Time (Ambient Ticks)
Like Strix, periodic autonomous activation:
- Every N hours, Cody "wakes up"
- Reviews state, journal, commitments
- May send proactive messages
- Handles recurring tasks

### Self-Modification
Agent ability to edit own skills:
- Must go through review process
- Git branch + PR workflow
- Human approval required

### Multi-User Support
For Slack deployment:
- Per-user memory isolation
- Shared organizational context
- Permission scoping

---

## Appendix: Strix Inspiration

Key concepts borrowed from [Strix](https://timkellogg.me/blog/2025/12/15/strix):

- **Patient ambush predator model**: Strike only when there's signal
- **Three-tier memory**: Blocks, journal, state files
- **Reply as tool**: Flexibility in response timing/style
- **Temporal awareness**: Timezone handling, journal injection
- **Skill-based architecture**: Modular tool organization
- **"If you didn't write it down, you won't remember it"**: Explicit state management
