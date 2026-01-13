# Design Summary - STRIX-Inspired Slack Agent

## Quick Reference

### Core Concept
A stateful Slack bot (single-user DM) that maintains persistent memory, tracks clipboard (macOS), and includes a dual-agent system for self-improvement.

### Two Agents
1. **Main Agent**: Handles user interactions, self-modifies via git/PRs
2. **Test Agent**: Tests Main Agent's changes, provides feedback (cannot modify Main Agent)

### Key Features
- ✅ Slack integration (single-user DM)
- ✅ Three-tier memory system (Core/Indices/Files)
- ✅ macOS clipboard monitoring & ingestion
- ✅ Queryable database (SQLite)
- ✅ People files (text format)
- ✅ Self-modification via git branches/PRs
- ✅ Daily self-improvement cycle (night → morning PR)
- ✅ Test Agent validation loop
- ✅ RSS feed integration for learning
- ✅ Claude Opus 4.5

### Memory Architecture
- **Tier 1 (Core)**: Always-loaded identity blocks (persona, values, style)
- **Tier 2 (Indices)**: Pointers to files (recent_insights, current_focus)
- **Tier 3 (Files)**: On-demand detailed storage (people/, research/, insights/)

### Self-Improvement Workflow
1. Clone repo → Make changes → Clone memory for Test Agent
2. Send to Test Agent via Slack → Get feedback
3. Evaluate feedback (like/dislike) → Iterate if needed
4. Create branch → Commit → PR → User reviews

### Daily Cycle
- **Start**: Night (11 PM)
- **Research**: Fetch RSS feeds, read articles
- **Thinking**: Analyze behavior, plan improvements
- **Implement**: Make changes, test via Test Agent
- **PR**: Create PR by morning
- **Stop**: When PR is created

### File Formats
- **People**: Text (`.txt`) - Claude-friendly
- **State files**: Text (`.txt`)
- **Database**: SQLite for structured data
- **Logs**: JSONL for queryable logs

### Platform
- **Deployment**: Local machine
- **Clipboard**: macOS only (NSPasteboard)
- **Model**: Claude Opus 4.5

### Key Constraints
- Only user can modify Main Agent
- Test Agent only tests and provides feedback
- Test Agent receives cloned memory for context
- Both agents communicate via Slack
- Manual deployment (agent doesn't have sudo)

---

## Next Steps
1. Create detailed MCP server spec with tool schemas
2. Design Test Agent API and Slack protocol
3. Create PRD for implementation
4. Implement Phase 0 (Foundation)
