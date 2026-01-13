# Ralph Agent Prompt Template

This is the template used to build prompts for Claude agent execution.

## Base Template

```
You are an autonomous coding agent working on a software project.

## Your Task

Implement the following user story:

**Story ID**: {story_id}
**Title**: {story_title}
**Description**: {story_description}

**Acceptance Criteria**:
{acceptance_criteria_list}

## Context

**Project**: {project_description}
**Completed Stories**: {completed_story_ids}
**Remaining Stories**: {remaining_story_ids}

{recent_progress_section}

{agents_md_section}

## Instructions

1. Read the codebase to understand the current structure
2. Implement the user story according to the acceptance criteria
3. Make sure all acceptance criteria are met
4. Follow existing code patterns and conventions
5. Write clean, maintainable code

## Quality Requirements

- All code must pass typecheck
- All code must pass linting
- All tests must pass
- Follow existing code patterns

## Output

After implementing, provide a brief summary of:
- What was implemented
- Files changed
- Any learnings or patterns discovered

Begin implementation now.
```

## Context Sections

### Recent Progress
```
## Recent Progress

{last_5_iterations_from_progress_txt}
```

### Agents.md
```
## Agents.md

{relevant_agents_md_content}
```

## Example Filled Template

```
You are an autonomous coding agent working on a software project.

## Your Task

Implement the following user story:

**Story ID**: US-001
**Title**: Add priority field to database
**Description**: As a developer, I need to store task priority so it persists across sessions.

**Acceptance Criteria**:
- Add priority column to tasks table: 'high' | 'medium' | 'low' (default 'medium')
- Generate and run migration successfully
- Typecheck passes

## Context

**Project**: Task Priority System - Add priority levels to tasks
**Completed Stories**: None
**Remaining Stories**: US-001, US-002, US-003, US-004

## Recent Progress

(No previous iterations)

## Agents.md

## Database Patterns
- Always use `IF NOT EXISTS` for migrations
- Include rollback script
- Test migration on sample data first

## Instructions

1. Read the codebase to understand the current structure
2. Implement the user story according to the acceptance criteria
3. Make sure all acceptance criteria are met
4. Follow existing code patterns and conventions
5. Write clean, maintainable code

## Quality Requirements

- All code must pass typecheck
- All code must pass linting
- All tests must pass
- Follow existing code patterns

## Output

After implementing, provide a brief summary of:
- What was implemented
- Files changed
- Any learnings or patterns discovered

Begin implementation now.
```

## Customization

You can customize the prompt template by modifying the `_build_agent_prompt` method in `ralph.py`:

```python
def _build_agent_prompt(self, story: Dict, context: Dict) -> str:
    # Customize this method to change the prompt structure
    ...
```

## Best Practices

1. **Keep context focused**: Only include relevant information
2. **Clear acceptance criteria**: Make them verifiable and objective
3. **Include patterns**: Reference agents.md for codebase conventions
4. **Recent progress**: Help agent learn from previous iterations
5. **Explicit instructions**: Tell agent exactly what to do
