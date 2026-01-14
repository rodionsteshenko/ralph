#!/usr/bin/env python3
"""
Example: Reorganize PRD phases programmatically

This script demonstrates how to reorganize phases in the PRD
without manually editing JSON.
"""

from prd_tools import PRDManager

def main():
    # Load the PRD
    manager = PRDManager('prd-slack-agent.json')

    # Define the new phase structure
    new_phases = {
        1: {
            'name': 'RSS & Testing',
            'description': 'RSS feeds, article processing, research scheduling, and integration tests',
            'story_ids': ['US-040', 'US-041', 'US-042', 'US-043', 'US-048']
        },
        2: {
            'name': 'Self-Improvement',
            'description': 'Job scheduling, perch time, git operations, self-modification tools, and full improvement cycle',
            'story_ids': [
                'US-037', 'US-038', 'US-039',  # Scheduling
                'US-032', 'US-033', 'US-034', 'US-035', 'US-036',  # Git & self-mod tools
                'US-044', 'US-045', 'US-046'  # Self-improvement cycle
            ]
        },
        3: {
            'name': 'Test Agent & Slack',
            'description': 'Dual-agent architecture, Test Agent validation, Slack integration, and manual triggers',
            'story_ids': [
                'US-030', 'US-031', 'US-049',  # Test Agent
                'US-017', 'US-018', 'US-019', 'US-029', 'US-047'  # Slack
            ]
        },
        4: {
            'name': 'Documentation',
            'description': 'Deployment guide and architecture documentation',
            'story_ids': ['US-051']
        }
    }

    # Apply the reorganization
    print("🔄 Reorganizing phases...")
    manager.reorganize_phases(new_phases)

    # Save changes
    manager.save()
    print("✅ Phases reorganized successfully!")

    # Show summary
    summary = manager.get_summary()
    print(f"\n📊 Summary:")
    print(f"Total stories: {summary['total_stories']}")
    print(f"Completed: {summary['completed_stories']}")
    print(f"Remaining: {summary['remaining_stories']}")
    print(f"\nBy phase:")

    for phase_num in sorted(summary['by_phase'].keys()):
        phase_info = summary['by_phase'][phase_num]
        phase_meta = manager.data['metadata']['phases'].get(str(phase_num), {})
        phase_name = phase_meta.get('name', f'Phase {phase_num}')

        remaining = phase_info['remaining']
        total = phase_info['total']
        print(f"  Phase {phase_num} ({phase_name}): {remaining}/{total} remaining")


if __name__ == '__main__':
    main()
