# PRD Management Tools

Python utilities for programmatic manipulation of `prd.json` files. Avoids manual JSON editing and reduces errors.

## Quick Reference

```bash
# Get summary of PRD progress
python prd_tools.py summary prd-slack-agent.json

# List all incomplete stories in phase 1
python prd_tools.py list-stories prd-slack-agent.json --phase 1 --status incomplete

# Update a story's phase
python prd_tools.py update-story prd-slack-agent.json US-040 --phase 1

# Mark a story as complete
python prd_tools.py update-story prd-slack-agent.json US-040 --status complete

# Bulk update phases from JSON file
python prd_tools.py update-phases prd-slack-agent.json phase_mapping.json
```

## Python API Usage

For programmatic use in scripts:

```python
from prd_tools import PRDManager

# Load PRD
manager = PRDManager('prd-slack-agent.json')

# Update a single story's phase
manager.update_story_phase('US-040', 1)

# Bulk update phases
phase_mapping = {
    'US-040': 1,
    'US-041': 1,
    'US-042': 1,
    'US-043': 1,
    'US-048': 1
}
manager.bulk_update_phases(phase_mapping)

# Reorganize entire phase structure
new_structure = {
    1: {
        'name': 'RSS & Testing',
        'description': 'RSS feeds, article processing, and integration tests',
        'story_ids': ['US-040', 'US-041', 'US-042', 'US-043', 'US-048']
    },
    2: {
        'name': 'Self-Improvement',
        'description': 'Job scheduling, git operations, and full improvement cycle',
        'story_ids': ['US-037', 'US-038', 'US-039', 'US-032', 'US-033',
                      'US-034', 'US-035', 'US-036', 'US-044', 'US-045', 'US-046']
    },
    3: {
        'name': 'Test Agent & Slack',
        'description': 'Dual-agent architecture, Test Agent validation, Slack integration',
        'story_ids': ['US-030', 'US-031', 'US-049', 'US-017', 'US-018',
                      'US-019', 'US-029', 'US-047']
    }
}
manager.reorganize_phases(new_structure)

# Save changes
manager.save()

# Get summary statistics
summary = manager.get_summary()
print(f"Progress: {summary['completion_percentage']}%")
```

## Common Operations

### 1. Reorganizing Phases

When you need to restructure phases (like we just did), use the `reorganize_phases` method:

```python
from prd_tools import PRDManager

manager = PRDManager('prd-slack-agent.json')

# Define new phase structure
phases = {
    1: {
        'name': 'RSS & Testing',
        'description': 'RSS feeds and integration tests',
        'story_ids': ['US-040', 'US-041', 'US-042', 'US-043', 'US-048']
    },
    2: {
        'name': 'Self-Improvement',
        'description': 'Full self-improvement cycle',
        'story_ids': ['US-037', 'US-038', 'US-039', 'US-032', 'US-033',
                      'US-034', 'US-035', 'US-036', 'US-044', 'US-045', 'US-046']
    },
    3: {
        'name': 'Test Agent & Slack',
        'description': 'Advanced features',
        'story_ids': ['US-030', 'US-031', 'US-049', 'US-017', 'US-018',
                      'US-019', 'US-029', 'US-047']
    }
}

manager.reorganize_phases(phases)
manager.save()
```

### 2. Tracking Progress

```python
from prd_tools import PRDManager

manager = PRDManager('prd-slack-agent.json')

# Get incomplete stories for next phase
next_phase_stories = manager.list_stories(phase=1, status='incomplete')
for story in next_phase_stories:
    print(f"{story['id']}: {story['title']}")

# Get summary
summary = manager.get_summary()
print(f"Overall progress: {summary['completion_percentage']}%")
print(f"Phase 1 remaining: {summary['by_phase'][1]['remaining']}")
```

### 3. Updating Story Status

```python
from prd_tools import PRDManager

manager = PRDManager('prd-slack-agent.json')

# Mark story as complete
manager.update_story_status('US-040', passes=True)
manager.save()
```

## Integration with Ralph

You can use these tools in Ralph's execution loop:

```python
# In ralph.py or custom scripts
from prd_tools import PRDManager

def mark_story_complete(story_id: str):
    """Mark a story as complete after successful execution."""
    manager = PRDManager('prd.json')
    manager.update_story_status(story_id, passes=True)
    manager.save()
    print(f"✅ Marked {story_id} as complete")
```

## PRDManager API Reference

### Methods

- `__init__(prd_path: str)` - Load PRD from file path
- `save()` - Save changes back to file (updates lastUpdatedAt)
- `update_story_phase(story_id: str, new_phase: int) -> bool` - Update single story's phase
- `update_story_status(story_id: str, passes: bool) -> bool` - Update story completion status
- `bulk_update_phases(phase_mapping: Dict[str, int]) -> List[str]` - Update multiple story phases
- `update_phase_metadata(phase_definitions: Dict)` - Update phases metadata section
- `list_stories(phase: Optional[int], status: Optional[str]) -> List[Dict]` - List/filter stories
- `get_summary() -> Dict` - Get progress statistics
- `reorganize_phases(new_phase_structure: Dict)` - Complete phase reorganization

## Examples

### Example: Move all RSS stories to Phase 1

```python
from prd_tools import PRDManager

manager = PRDManager('prd-slack-agent.json')

rss_stories = ['US-040', 'US-041', 'US-042', 'US-043']
for story_id in rss_stories:
    manager.update_story_phase(story_id, 1)

manager.save()
```

### Example: Generate progress report

```python
from prd_tools import PRDManager

manager = PRDManager('prd-slack-agent.json')
summary = manager.get_summary()

print(f"\n📊 Project Progress Report")
print(f"=" * 60)
print(f"Completed: {summary['completed_stories']}/{summary['total_stories']} ({summary['completion_percentage']}%)")
print(f"\nBy Phase:")

for phase_num in sorted(summary['by_phase'].keys()):
    phase_info = summary['by_phase'][phase_num]
    phase_meta = manager.data['metadata']['phases'].get(str(phase_num), {})
    phase_name = phase_meta.get('name', f'Phase {phase_num}')

    print(f"\n  Phase {phase_num}: {phase_name}")
    print(f"    {phase_info['completed']}/{phase_info['total']} complete")
    print(f"    {phase_info['remaining']} remaining")
```

## Why Use These Tools?

1. **Avoid JSON syntax errors** - No manual editing means no typos or broken JSON
2. **Atomic updates** - Changes are applied consistently across story data and metadata
3. **Validation** - Tools ensure phase numbers, story IDs, and metadata stay in sync
4. **Reusability** - Scripts can be called from Ralph, CI/CD, or other automation
5. **Type safety** - Python type hints help catch errors early

## Future Enhancements

Potential additions to these tools:

- [ ] Story dependency validation
- [ ] Phase transition rules (e.g., can't move to Phase 2 until Phase 1 is 100% complete)
- [ ] Story estimation tracking (compare estimated vs actual duration)
- [ ] Export to Markdown summary
- [ ] Integration with git commits (auto-commit PRD changes)
- [ ] Interactive CLI with prompts
- [ ] Story filtering by priority, tags, or keywords
