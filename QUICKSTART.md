# Ralph Python - Quick Start Guide

Get Ralph running in 5 minutes.

## Prerequisites

```bash
# Install Python 3.8+
python --version

# Install dependencies (uses UV for fast installation)
uv pip install -r requirements.txt
```

## Step 1: Create a PRD

Create a structured PRD file in JSON:

```bash
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
        "Add priority column: 'high' | 'medium' | 'low' (default 'medium')",
        "Generate and run migration",
        "Typecheck passes"
      ],
      "priority": 1,
      "passes": false,
      "notes": ""
    },
    {
      "id": "US-002",
      "title": "Display priority badge",
      "description": "As a user, I want to see task priority.",
      "acceptanceCriteria": [
        "Show colored badge on task cards",
        "Badge colors: red=high, yellow=medium, gray=low",
        "Typecheck passes"
      ],
      "priority": 2,
      "passes": false,
      "notes": ""
    }
  ],
  "metadata": {
    "createdAt": "2024-01-01T12:00:00",
    "lastUpdatedAt": "2024-01-01T12:00:00",
    "totalStories": 2,
    "completedStories": 0,
    "currentIteration": 0
  }
}
EOF
```

If you prefer, you can also generate `prd.json` from a PRD document:

```bash
python ralph.py process-prd tasks/prd-task-priority.txt
```

## Step 2: Initialize Configuration (Optional)

```bash
python ralph.py init
```

Edit `.ralph/config.json` to match your project:

```json
{
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
  }
}
```

## Step 3: Run Ralph

```bash
# With max iterations
python ralph.py execute-plan --max-iterations 10

# Unlimited (until done or 3 failures)
python ralph.py execute-plan --max-iterations 0
```

Ralph will:
1. Pick a story
2. Implement it with Claude
3. Run quality gates
4. Commit if passing
5. Repeat until done

## Step 5: Monitor Progress

```bash
# Check status
python ralph.py status

# View progress log
cat progress.txt

# View PRD status
cat prd.json | jq '.userStories[] | {id, title, passes}'
```

## Stop Conditions

Ralph stops when:
- ✅ All stories complete
- ⏱️ Max iterations reached (if set)
- ❌ 3 consecutive failures
- 🛑 You press Ctrl+C

## Troubleshooting

### "Quality gates failing"
Check your commands in `.ralph/config.json` match your project.

### "Git not found"
```bash
git init
git config user.name "Ralph"
git config user.email "ralph@example.com"
```

## Example Output

```
🚀 Starting Ralph Loop
   Max iterations: 10
   Stories to complete: 4

============================================================
  Iteration 1 - US-001: Add priority field to database
============================================================
🤖 Spawning Claude agent for story US-001...
🔍 Running quality gates...
✅ typecheck passed (12.3s)
✅ lint passed (8.1s)
✅ tests passed (45.2s)
   ✅ Committed: feat: US-001 - Add priority field to database
✅ Story US-001 completed (65.6s)

============================================================
  Iteration 2 - US-002: Display priority badge
============================================================
...

📊 Final Status: 4/4 stories completed
```

## Next Steps

- Check the repository documentation for deeper details

## Tips

1. **Keep stories small**: Each should be completable in one iteration
2. **Clear acceptance criteria**: Make them verifiable
3. **Test your config**: Run quality gates manually first
4. **Monitor progress**: Check `progress.txt` regularly
5. **Review commits**: Treat Ralph output like a PR

Happy coding! 🚀
