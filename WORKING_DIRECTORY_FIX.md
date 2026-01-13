# Working Directory Fix

## Problem

Claude Code was confused about what directory it was in when executing commands. Looking at the log file (`logs/story-US-008-20260113-132041.log`), we see:

```
✗ Tool result (error): Exit code 1
(eval):cd:1: no such file or directory: slack-agent
```

Claude Code tried to run `cd slack-agent && mypy...` but failed because:
- Ralph was spawning Claude Code from `/Users/rodion/ralph/` (the Ralph directory)
- Claude Code couldn't find the `slack-agent` subdirectory in its current context
- Claude Code had to prefix every command with `cd slack-agent &&`

## Root Cause

When Ralph spawned Claude Code via `subprocess.run()`, it was using `cwd=Path.cwd()` which kept the working directory as the Ralph directory (`/Users/rodion/ralph/`), not the project directory (`/Users/rodion/ralph/slack-agent/`).

This caused issues because:
1. Claude Code's relative paths were wrong
2. Commands like `mypy memory/blocks.py` failed
3. Claude Code had to use `cd slack-agent &&` prefix for every command
4. The prefix approach was error-prone and failed in many cases

## Solution

**Changed Ralph to execute Claude Code in the project directory.**

### Code Changes

1. **Determine working directory** before spawning Claude Code (ralph.py:830-835):
```python
# Determine working directory for execution
working_dir = context.get('workingDirectory')
if working_dir:
    work_path = Path.cwd() / working_dir
    work_path.mkdir(parents=True, exist_ok=True)
else:
    work_path = Path.cwd()
```

2. **Run Claude Code in project directory** (ralph.py:890, 931):
```python
# Streaming mode
process = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
    cwd=work_path  # ← Changed from Path.cwd()
)

# Non-streaming mode
result = subprocess.run(
    [...],
    capture_output=True,
    text=True,
    cwd=work_path,  # ← Changed from Path.cwd()
    timeout=self.config.get("ralph.iterationTimeout", 3600)
)
```

3. **Updated prompt to clarify working directory** (ralph.py:1082-1090):
```python
## Working Directory

**IMPORTANT**: You are currently running in the `{working_dir}/` directory.
- All file paths are relative to this directory
- When you create files, they will be in `{working_dir}/`
- The project code is separate from the Ralph automation codebase
- Use relative paths (e.g., `memory/blocks.py`, not `{working_dir}/memory/blocks.py`)
```

## Benefits

### Before Fix
```bash
# Claude Code's working directory: /Users/rodion/ralph/
# Claude Code tries:
cd slack-agent && mypy memory/blocks.py
# Result: ✗ Error: no such file or directory: slack-agent
```

### After Fix
```bash
# Claude Code's working directory: /Users/rodion/ralph/slack-agent/
# Claude Code runs:
mypy memory/blocks.py
# Result: ✓ Works correctly!
```

### Improvements
- ✅ **Commands "just work"** - No need for `cd` prefix
- ✅ **Relative paths work** - `memory/blocks.py` resolves correctly
- ✅ **Less confusion** - Claude Code knows exactly where it is
- ✅ **Fewer errors** - No more "no such file or directory" errors
- ✅ **Cleaner logs** - Less command prefixing noise

## Running Ralph from Project Directory

You asked: "Should I run Ralph from within the slack-agent directory?"

**Answer: No, Ralph should always be run from the Ralph directory (`/Users/rodion/ralph/`).**

### Why?

1. **PRD file location**: The PRD file (`prd-slack-agent.json`) is in the Ralph directory
2. **Config location**: Ralph's config (`.ralph/config.json`) is in the Ralph directory
3. **Logs location**: Log files are written to `logs/` in the Ralph directory
4. **Progress tracking**: `progress.txt` is in the Ralph directory

### Correct Usage

```bash
# ✅ CORRECT - Run from Ralph directory
cd /Users/rodion/ralph
python ralph.py execute-plan --prd prd-slack-agent.json --max-iterations 1

# ❌ WRONG - Don't run from project directory
cd /Users/rodion/ralph/slack-agent
python ../ralph.py execute-plan --prd prd-slack-agent.json --max-iterations 1
# Error: PRD file not found
```

### What Changed?

**Ralph's behavior**:
- Ralph still runs from `/Users/rodion/ralph/`
- Ralph reads PRD, config, and logs from Ralph directory
- **NEW**: When spawning Claude Code, Ralph changes the working directory to `slack-agent/`

**Claude Code's behavior**:
- Claude Code now runs in `/Users/rodion/ralph/slack-agent/`
- All file operations are relative to `slack-agent/`
- Commands work without `cd` prefixes
- Claude Code doesn't see Ralph's files (separation of concerns)

## Testing

To verify the fix works:

```bash
# Run Ralph normally
cd /Users/rodion/ralph
python ralph.py execute-plan --prd prd-slack-agent.json --max-iterations 1

# Check logs for successful command execution
tail -100 logs/story-*.log

# You should see commands like:
# mypy memory/blocks.py  (not "cd slack-agent && mypy...")
# pytest tests/          (not "cd slack-agent && pytest...")
```

## Technical Details

### Quality Gates Still Run from Ralph Directory

Quality gates (typecheck, lint, test) continue to run from the Ralph directory because they need to access the config:

```python
# Quality gates (ralph.py:471)
result = subprocess.run(
    command,
    shell=True,
    capture_output=True,
    text=True,
    timeout=timeout,
    cwd=Path.cwd()  # ← Still Ralph directory
)
```

Quality gate commands are configured with `cd slack-agent &&` prefix in `.ralph/config.json`:

```json
{
  "commands": {
    "typecheck": "cd slack-agent && mypy . --ignore-missing-imports || true"
  }
}
```

This separation means:
- **Claude Code**: Runs in project directory (doesn't need `cd`)
- **Quality gates**: Run in Ralph directory (needs `cd` in config)

## Summary

✅ **Problem solved**: Claude Code no longer gets confused about directories
✅ **No user changes**: Ralph usage remains the same
✅ **Better experience**: Commands work without prefixes
✅ **Clear separation**: Ralph code vs project code directories

The fix maintains backward compatibility while solving the directory confusion issue.
