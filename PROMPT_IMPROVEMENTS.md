# Ralph Prompt Improvements

## Summary

Enhanced the prompt that Ralph sends to Claude Code to provide better guidance on implementation strategy, testing requirements, and quality standards.

## What Changed

### 1. Better Context on Completed Work

**Before:**
```
**Completed Stories**: US-001, US-002, US-003
```

**After:**
```
## What's Already Built

The following user stories have been completed and their code is in the codebase:
- US-001
- US-002
- US-003

**IMPORTANT**: Before implementing, read the existing code to understand:
- What patterns are being used
- What utilities/helpers already exist
- How similar features are implemented
- What dependencies are available
```

**Why:** Explicitly reminds Claude Code to explore the codebase first and understand what's already there before implementing. This reduces duplicate code and ensures consistency.

### 2. Incremental Implementation Strategy

**Added:**
```
## Implementation Strategy

Follow this incremental approach:

1. **Explore First** (5-10 minutes)
   - Read existing codebase to understand structure and patterns
   - Identify what utilities/helpers already exist
   - Check what dependencies are available
   - Understand how similar features are implemented

2. **Plan Implementation** (2-3 minutes)
   - Break down acceptance criteria into concrete tasks
   - Identify which files need to be created/modified
   - Determine what tests are needed
   - Consider edge cases and error handling

3. **Implement Incrementally** (iterative)
   - Start with core functionality first
   - Build one acceptance criterion at a time
   - Test each piece as you build it
   - Follow existing code patterns and conventions

4. **Verify Quality** (before finishing)
   - Run all acceptance criteria against your implementation
   - Ensure code is clean and maintainable
   - Check that tests exist and pass
   - Verify type safety and error handling
```

**Why:** Provides a clear, step-by-step approach to implementation. This ensures Claude Code doesn't jump straight into coding without exploring, and builds incrementally rather than trying to do everything at once.

### 3. Comprehensive Testing Guidance

**Before:**
```
## Quality Requirements

- All code must pass typecheck
- All code must pass linting
- All tests must pass
- Follow existing code patterns
```

**After:**
```
## Quality Requirements & Testing

**CRITICAL**: After implementation, your code will be tested with quality gates. All gates must pass.

### Type Safety
- Add type hints to all function signatures
- Use strict typing (no `Any` unless absolutely necessary)
- Ensure mypy/pyright passes with no errors
- Import types from `typing` module as needed

### Testing Strategy
- **Unit tests**: Test individual functions and classes in isolation
- **Integration tests**: Test how components work together
- **Edge cases**: Test boundary conditions, empty inputs, error states
- **Mock external dependencies**: Don't make real API calls or database connections in tests
- Test file naming: `test_<module_name>.py` or `<module_name>_test.py`

### Code Quality
- Follow existing code patterns and conventions
- Keep functions small and focused (< 50 lines)
- Use descriptive variable and function names
- Add docstrings for public functions and classes
- Handle errors gracefully with try/except where appropriate
- No commented-out code or debug print statements
- Clean up imports (no unused imports)

### Linting & Formatting
- Code must pass linting (ruff, pylint, or project-specific linter)
- Follow PEP 8 style guidelines
- Use consistent formatting (spaces, line breaks, etc.)
- Maximum line length: 100-120 characters
```

**Why:**
- Much more specific about what "quality" means
- Explicitly calls out testing requirements (unit, integration, edge cases)
- Emphasizes type safety with concrete rules
- Provides clear code quality standards
- Mentions mocking external dependencies to prevent side effects

### 4. Self-Review Checklist

**Added:**
```
### Self-Review Checklist

Before finishing, verify:
- [ ] All acceptance criteria are met
- [ ] Type hints added to all functions
- [ ] Tests written and passing
- [ ] No obvious bugs or edge cases missed
- [ ] Error handling is appropriate
- [ ] Code follows existing patterns
- [ ] No debug code or print statements left in
- [ ] Documentation/comments added where needed
```

**Why:** Gives Claude Code a checklist to review before considering the work done. This catches common issues before quality gates run.

### 5. File Size and Modularity Guidance

**Added:**
```
## File Size and Modularity

**CRITICAL**: Keep code files small, focused, and maintainable.

### File Size Limits
- **Maximum file size**: 500 lines (including imports, docstrings, and whitespace)
- **Target file size**: 200-300 lines for most files
- **If a file exceeds 500 lines**: Refactor it immediately into smaller modules

### When to Split Files
Split a file when:
- It exceeds 500 lines
- It contains multiple unrelated responsibilities
- It has more than 5-7 classes or 10-15 functions
- It handles multiple distinct concerns

### How to Refactor Large Files
1. **Identify logical groupings**: Group related functions/classes together
2. **Extract into separate modules**: Create new files for each logical grouping
3. **Use clear naming**: Module names should clearly indicate their purpose
4. **Update imports**: Ensure all imports are updated correctly
5. **Maintain public API**: Use `__init__.py` to re-export if needed

### Examples of Good File Organization
[Examples showing bad 800-line file vs good split into 6 focused modules]

### Proactive Refactoring
- Check if existing files are approaching 500 lines before adding code
- Refactor large files first before adding new functionality
- Check file size first when adding to existing files

### File Size Check
1. Check line count: `wc -l <file>`
2. If any file exceeds 500 lines, refactor into smaller modules
3. Ensure each module has a single, clear responsibility
4. Update all imports and ensure tests still pass
```

**Why:**
- Prevents creation of monolithic, hard-to-maintain files
- Encourages proactive refactoring before files become too large
- Provides concrete examples of good file organization
- Makes files easier to read, test, and modify
- Includes specific command (`wc -l`) to check file sizes
- Added to self-review checklist to ensure it's checked
- Added to output format so Claude Code reports on file sizes

### 6. Structured Output Format

**Before:**
```
## Output

After implementing, provide a brief summary of:
- What was implemented
- Files changed
- Any learnings or patterns discovered
```

**After:**
```
## Output Format

After implementing, provide a summary with:

**✅ Implemented:**
- List of acceptance criteria met
- Key files created/modified
- File sizes (line counts) for all new/modified code files

**🧪 Tests:**
- Test files created
- Test coverage areas
- How to run the tests

**🔧 Refactoring:**
- Any files that were split/refactored due to size
- Any proactive refactoring done to keep files under 500 lines

**📝 Notes:**
- Any important patterns or decisions made
- Dependencies added
- Known limitations or future improvements needed
```

**Why:**
- Structured format makes it easier to parse the output and understand what was done
- Explicitly asks for test information which is often missing
- Requires reporting on file sizes to ensure 500-line limit is respected
- Dedicated refactoring section encourages proactive file splitting
- Makes it clear that refactoring is part of the implementation process

## Expected Impact

### Better Quality Code
- Type hints consistently added
- Better error handling
- Cleaner, more maintainable code
- Fewer quality gate failures
- **All files under 500 lines - easier to read, test, and modify**

### Better File Organization
- **Modular codebase with focused, single-responsibility files**
- **Proactive refactoring prevents technical debt accumulation**
- **Easier to navigate and understand the codebase**
- **Simpler code review process (smaller, focused files)**
- **Reduced merge conflicts (smaller files = less overlap)**

### Better Tests
- Unit tests for all new functions
- Integration tests for feature flows
- Edge cases covered
- Proper mocking of external dependencies
- **Easier to test (smaller files = more focused tests)**

### Better Implementation Process
1. Claude Code explores codebase first (reduces duplication)
2. Plans implementation before coding (better architecture)
3. Implements incrementally (easier to debug)
4. **Checks file sizes and refactors proactively (prevents large files)**
5. Self-reviews before finishing (catches issues early)

### Reduced Failures
- Fewer quality gate failures due to missing type hints
- Fewer quality gate failures due to missing tests
- Better code reuse (exploring existing code first)
- Fewer bugs due to better error handling and edge case testing
- **Fewer maintenance issues (small files are easier to maintain)**

## Usage

The improved prompt is automatically used when running:

```bash
python ralph.py execute-plan --prd prd-slack-agent.json --max-iterations 1
```

No changes needed to existing workflows.

## Future Improvements

Consider adding:
- Example code snippets showing the desired patterns
- Performance considerations (when to optimize)
- Security best practices (input validation, sanitization, etc.)
- Accessibility requirements (if applicable)
- Documentation requirements (when to update README, when to add comments)
- Git commit message guidelines (conventional commits, etc.)
- API design guidelines (REST, GraphQL, etc.)

## Testing the Improvements

To see the improvements in action:

1. Run Ralph on a new story
2. Observe Claude Code exploring the codebase first
3. Check if tests are written
4. Verify type hints are added
5. **Check file sizes: `wc -l slack-agent/**/*.py`**
6. **Verify all files are under 500 lines**
7. Review the structured output summary with file sizes

Compare to previous runs to see the difference in:
- Quality gate pass rate
- Test coverage
- Code quality
- **File sizes and modularity**
- Implementation time (may be slightly longer due to exploration, but should reduce overall time due to fewer failures)

### File Size Verification

```bash
# Check all Python files in the project
find slack-agent -name "*.py" -exec wc -l {} \; | sort -rn | head -20

# Find any files over 500 lines
find slack-agent -name "*.py" -exec wc -l {} \; | awk '$1 > 500 {print}'

# Get average file size
find slack-agent -name "*.py" -exec wc -l {} \; | awk '{sum+=$1; count++} END {print "Average:", sum/count, "lines"}'
```
