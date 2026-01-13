# Ralph Logging Enhancements

## Summary of Changes

Enhanced Ralph with comprehensive logging and rich terminal formatting for better visibility and debugging.

## Key Features Added

### 1. Detailed Per-Story Log Files

Each story execution now creates a detailed log file in `logs/` directory:

```
logs/story-US-001-20260113-123456.log
```

**Contents:**
- Full prompt sent to Claude Code
- Complete streaming output from Claude Code (in real-time)
- Quality gate results (JSON format)
- Timestamps and return codes

**Benefits:**
- Review complete execution history after the fact
- Debug issues without re-running
- Track what Claude Code actually did
- Audit trail for all changes

### 2. Rich Terminal Formatting

When `rich` library is installed, Ralph displays:

**Story Selection Panel:**
```
┌─── 📋 Story Selection ─────────────┐
│ Iteration 1                        │
│                                    │
│ Story ID: US-001                   │
│ Title: Project Structure Setup     │
│ Priority: 1                        │
│ Remaining: 50 stories              │
└────────────────────────────────────┘
```

**Claude Code Agent Panel:**
```
┌─── 🤖 Claude Code Agent ───────────┐
│ Story US-001: Project Structure    │
│ Iteration 1                        │
│ Log file: logs/story-US-001...     │
└────────────────────────────────────┘
```

**Quality Gates with Command Display:**
```
▶ Running typecheck...
  Command: cd slack-agent && mypy . --ignore-missing-imports

✓ typecheck passed (12.3s)
```

**Git Commit Panel:**
```
┌─── 📦 Git Commit ──────────────────┐
│ ✓ Changes committed                │
│                                    │
│ Branch: ralph/slack-agent-found... │
│ Message: feat: US-001 - Project...│
│ Working directory: /path/to/slack..│
└────────────────────────────────────┘
```

**Success Summary:**
```
┌─── 🎉 Success ─────────────────────┐
│ ✓ Story US-001 completed success..│
│                                    │
│ Title: Project Structure Setup     │
│ Total time: 45.6s                  │
│ Log file: logs/story-US-001...     │
└────────────────────────────────────┘
```

**Final Status:**
```
┌─── 📊 Final Status ────────────────┐
│ 4/50 stories completed             │
│                                    │
│ Completed: 4                       │
│ Remaining: 46                      │
│ Iterations: 4                      │
│ Logs directory: /path/to/logs      │
└────────────────────────────────────┘
```

### 3. Enhanced Quality Gate Output

**Shows command being run:**
```
▶ Running typecheck...
  Command: cd slack-agent && mypy . --ignore-missing-imports || true
```

**For failures, shows first 20 lines of output:**
```
┌─── typecheck Output (first 20 lines) ───┐
│ error: Cannot find implementation...     │
│ error: Module 'foo' has no attribute..  │
│ ...                                      │
└──────────────────────────────────────────┘
```

### 4. Real-time Log Writing

- Claude Code output streams to both terminal AND log file simultaneously
- No need to wait until completion to see logs
- Logs preserved even if process is interrupted

## File Locations

### Detailed Logs
```
logs/
├── story-US-001-20260113-120000.log
├── story-US-002-20260113-120530.log
├── story-US-003-20260113-121015.log
└── ...
```

### Summary Log
```
progress.txt  # Still contains iteration summaries
```

## Usage

### With Rich Formatting (Recommended)
```bash
# Rich is auto-installed with Ralph
python ralph.py execute-plan --prd prd.json --max-iterations 5
```

### Without Rich (Fallback)
If rich is not available, Ralph falls back to plain text output with minimal formatting.

## Log File Format

Each story log contains:

```
================================================================================
Story: US-001 - Project Structure and Dependencies
Iteration: 1
Started: 2026-01-13T12:00:00.000000
================================================================================

PROMPT:
--------------------------------------------------------------------------------
You are an autonomous coding agent working on a software project...
[Full prompt content]
--------------------------------------------------------------------------------

CLAUDE CODE OUTPUT:
--------------------------------------------------------------------------------
[Streaming output from Claude Code in real-time]
--------------------------------------------------------------------------------

Completed: 2026-01-13T12:05:30.000000
Return code: 0
================================================================================

QUALITY GATES:
--------------------------------------------------------------------------------
{
  "status": "PASS",
  "gates": {
    "typecheck": {
      "status": "PASS",
      "duration": 12.3,
      "output": "...",
      "returnCode": 0
    }
  },
  "totalDuration": 45.6
}
--------------------------------------------------------------------------------
```

## Benefits

1. **Better Debugging**: Full logs available for every story
2. **Progress Visibility**: Rich formatting makes it easier to follow execution
3. **Command Transparency**: See exactly what commands are being run
4. **Audit Trail**: Complete record of all executions
5. **Error Analysis**: Detailed output for failed quality gates
6. **Post-Mortem Analysis**: Review logs after execution completes

## Configuration

Optional config in `.ralph/config.json`:

```json
{
  "ralph": {
    "useStreaming": true,    // Enable real-time streaming (default: true)
    "verboseOutput": true     // Show more details (default: true)
  }
}
```

## Migration

- Existing `progress.txt` still works as before
- New `logs/` directory created automatically
- No breaking changes to existing workflows
- Rich formatting is optional (automatic fallback)

## Dependencies

- `rich>=10.0.0` - For terminal formatting (auto-installed)
- Fallback to plain text if not available
