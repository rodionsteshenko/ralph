# Ralph Python - Quick Start Guide

Get Ralph running in 5 minutes.

## Prerequisites

```bash
# Install Python 3.8+
python --version

# Install dependencies (uses UV for fast installation)
make install
# Or manually: uv pip install -r requirements.txt

# Set API key
export ANTHROPIC_API_KEY=your_key_here
```

## Step 1: Create a PRD

Create a markdown file with your feature description:

```markdown
# Task Priority Feature

Add priority levels to tasks.

## User Stories

### US-001: Add priority field to database
**Description**: As a developer, I need to store task priority.

**Acceptance Criteria**:
- Add priority column: 'high' | 'medium' | 'low' (default 'medium')
- Generate and run migration
- Typecheck passes

### US-002: Display priority badge
**Description**: As a user, I want to see task priority.

**Acceptance Criteria**:
- Show colored badge on task cards
- Badge colors: red=high, yellow=medium, gray=low
- Typecheck passes
```

Save as `tasks/prd-task-priority.md`

## Step 2: Convert PRD to Plan

```bash
python ralph.py process-prd tasks/prd-task-priority.md
```

This creates `prd.json` with structured user stories.

## Step 3: Initialize Configuration (Optional)

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

## Step 4: Run Ralph

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

### "API key not set"
```bash
export ANTHROPIC_API_KEY=your_key_here
```

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

- Read `ralph_python_README.md` for full documentation
- Check `DESIGN.md` for architecture details
- See `IMPLEMENTATION_SUMMARY.md` for implementation notes

## Tips

1. **Keep stories small**: Each should be completable in one iteration
2. **Clear acceptance criteria**: Make them verifiable
3. **Test your config**: Run quality gates manually first
4. **Monitor progress**: Check `progress.txt` regularly
5. **Review commits**: Treat Ralph output like a PR

Happy coding! 🚀
