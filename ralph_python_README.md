# Ralph Python Implementation

A Python-based implementation of the Ralph autonomous AI agent loop using Claude API.

## Overview

This implementation recreates the Ralph pattern from the original bash/Amp version, but uses:
- **Python** for the outer loop orchestration
- **Claude API** (via Anthropic SDK) for the agent execution
- **Structured configuration** via JSON files
- **Quality gates** that run statically (outside agent control)

## Installation

```bash
# Install dependencies (uses UV for fast installation)
uv pip install -r requirements.txt

# Make ralph.py executable
chmod +x ralph.py
```

## Quick Start

### 1. Process a PRD

Convert a PRD document into a structured `prd.json`:

```bash
python ralph.py process-prd tasks/prd-my-feature.txt
# or
python ralph.py process-prd tasks/prd-my-feature.txt --output prd.json
```

This uses Claude to parse your PRD and extract user stories with proper sizing and ordering.

### 2. Execute the Plan

Run Ralph to execute the plan:

```bash
# With max iterations
python ralph.py execute-plan --max-iterations 20

# Unlimited iterations (until completion or failure threshold)
python ralph.py execute-plan --max-iterations 0

# With custom PRD file
python ralph.py execute-plan --prd my-prd.json --max-iterations 10
```

### 3. Check Status

```bash
python ralph.py status
# or
python ralph.py status --prd prd.json
```

## Configuration

### Initialize Configuration

```bash
python ralph.py init
```

This creates `.ralph/config.json` with default settings. Edit this file to customize:

- **Commands**: How to run typecheck, lint, tests
- **Quality Gates**: Which gates to run, timeouts, requirements
- **Git**: Commit message format, auto-push settings
- **Ralph**: Max iterations, failure thresholds, timeouts
- **Claude**: Model, temperature, max tokens

### Example Configuration

```json
{
  "project": {
    "name": "MyApp",
    "type": "node",
    "packageManager": "npm"
  },
  "commands": {
    "typecheck": "npm run typecheck",
    "lint": "npm run lint",
    "test": "npm run test"
  },
  "qualityGates": {
    "typecheck": {
      "command": "npm run typecheck",
      "required": true,
      "timeout": 300
    },
    "lint": {
      "command": "npm run lint",
      "required": true,
      "timeout": 120
    },
    "test": {
      "command": "npm run test",
      "required": true,
      "timeout": 600
    }
  },
  "ralph": {
    "maxIterations": 20,
    "iterationTimeout": 3600,
    "maxFailures": 3,
    "updateAgentsMd": true
  },
  "claude": {
    "model": "claude-3-5-sonnet-20241022",
    "maxTokens": 8192,
    "temperature": 0.7
  }
}
```

## How It Works

### The Loop

1. **Load PRD**: Read `prd.json` and find stories where `passes: false`
2. **Select Story**: Pick next story by priority and dependency order
3. **Spawn Agent**: Create fresh Claude API call with story context
4. **Agent Implements**: Claude writes code to implement the story
5. **Run Quality Gates**: Statically run tests, lint, typecheck (outside agent)
6. **Commit if Passing**: If all gates pass, commit changes and mark story complete
7. **Log Progress**: Append to `progress.txt` with metrics
8. **Repeat**: Continue until all stories complete or stop conditions met

### Stop Conditions

Ralph stops when:

1. ✅ **All stories complete** (`passes: true` for all)
2. ⏱️ **Max iterations reached** (if `maxIterations > 0`)
3. ❌ **Consecutive failures** (default: 3 failures in a row)
4. 🛑 **Manual interruption** (Ctrl+C)

### Quality Gates

Quality gates run **statically** (outside agent control) after each implementation:

- **Typecheck**: Catches type errors
- **Lint**: Catches style issues
- **Tests**: Verifies functionality

All gates must pass before committing. If any gate fails, the agent can retry in the next iteration.

## File Structure

```
.
├── ralph.py                 # Main Python script
├── prd.json                 # Generated PRD with user stories
├── progress.txt            # Append-only progress log
├── .ralph/
│   ├── config.json         # Ralph configuration
│   └── skills/            # Project-specific skills
├── AGENTS.md               # Codebase patterns (auto-updated)
└── archive/               # Archived runs
```

## Differences from Original

### Original (Bash + Amp)
- Uses `amp` CLI tool
- Bash script for loop
- Amp handles agent execution
- Context managed by Amp

### Python Version
- Uses Claude API directly
- Python for orchestration
- More control over context building
- Easier to customize and extend

## Key Features

✅ **PRD Processing**: Convert PRD documents to structured JSON  
✅ **Autonomous Loop**: Execute stories until completion  
✅ **Quality Gates**: Static validation (tests, lint, typecheck)  
✅ **Progress Logging**: Detailed logs with timing metrics  
✅ **Failure Handling**: Automatic retry with failure tracking  
✅ **Stop Conditions**: Multiple ways to stop (completion, failures, max iterations)  
✅ **Git Integration**: Automatic commits when gates pass  
✅ **Configuration**: Flexible JSON-based configuration  

## Example Workflow

```bash
# 1. Create a PRD file (JSON)
cat > prd.json << EOF
{
  "project": "Task Priority Feature",
  "branchName": "ralph/task-priority",
  "description": "Add priority levels to tasks.",
  "userStories": [
    {
      "id": "US-001",
      "title": "Add priority field to database",
      "description": "As a developer, I need to store task priority.",
      "acceptanceCriteria": [
        "Add priority column: 'high' | 'medium' | 'low'",
        "Run migration",
        "Typecheck passes"
      ],
      "priority": 1,
      "passes": false,
      "notes": ""
    }
  ],
  "metadata": {
    "createdAt": "2024-01-01T12:00:00",
    "lastUpdatedAt": "2024-01-01T12:00:00",
    "totalStories": 1,
    "completedStories": 0,
    "currentIteration": 0
  }
}
EOF

# 2. Execute
python ralph.py execute-plan --max-iterations 10

# 3. Check status
python ralph.py status
```

## Troubleshooting

### Quality Gates Failing
Check your `config.json` commands match your project setup:
```bash
python ralph.py init --detect-config  # Auto-detect (future feature)
```

### Stories Too Large
Split stories in your PRD - each should be completable in one iteration.

### Git Errors
Ensure you're in a git repository:
```bash
git init
git config user.name "Ralph"
git config user.email "ralph@example.com"
```

## Advanced Usage

### Custom Configuration Path
```bash
python ralph.py execute-plan --config .ralph/custom-config.json
```

### Unlimited Iterations
```bash
python ralph.py execute-plan --max-iterations 0
```

### Custom PRD Path
```bash
python ralph.py execute-plan --prd features/my-feature.json
```

## Future Enhancements

- [ ] Auto-detect project configuration
- [ ] Browser testing integration
- [ ] PR creation automation
- [ ] Metrics dashboard
- [ ] Multi-agent coordination
- [ ] Skill file management
- [ ] Better agents.md parsing

## License

Same as original Ralph project.
