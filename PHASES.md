# Ralph Phase System

## Overview

The PRD now includes a `phase` field for each story, allowing you to implement features in stages. Use the `--phase` flag to execute only stories in a specific phase.

## Phase Breakdown

### Phase 0: Foundation
**27 stories completed, 1 story remaining**

All foundational work is done:
- Project structure, dependencies
- MCP server infrastructure
- Database schema and connections
- Memory block system (core + index blocks)
- File management tools
- Clipboard monitoring and vector search
- CLI testing interface (single-message mode)
- Git integration for state

**New Addition:**
- US-053: Interactive REPL CLI Interface (clean terminal display with colored output)

### Phase 1: Main Agent Core (CLI)
**16 stories remaining**

Core agent features testable entirely via CLI (no Slack, no Test Agent):

**Self-Modification Infrastructure:**
- US-032: Git Repository Cloning
- US-033: Git Branch Management
- US-034: Commit and PR Creation
- US-035: Skill File Updates
- US-036: Self-Modification MCP Tools

**Scheduling & Background Tasks:**
- US-037: Job Scheduling System
- US-038: Scheduling MCP Tools
- US-039: Perch Time Implementation

**RSS & Research:**
- US-040: RSS Feed Management
- US-041: RSS Article Processing
- US-042: RSS MCP Tools

**Self-Improvement Workflow:**
- US-043: Night-Time Research Scheduler
- US-044: Self-Improvement Thinking Phase
- US-045: Self-Improvement Implementation Phase
- US-046: Self-Improvement PR Creation

**Testing:**
- US-048: Integration Tests for Core Features

### Phase 2: Test Agent Infrastructure
**3 stories remaining**

Dual-agent architecture (CLI-based communication):
- US-030: Test Agent Feedback System
- US-031: Test Agent Evaluation Tools
- US-049: Test Agent Validation Suite

*Note: US-027 and US-028 already completed*

### Phase 3: Slack/SAC Integration
**5 stories remaining**

Wire up Slack Socket Mode and agent communication:
- US-017: Slack Message Sending Tools
- US-018: Slack History Retrieval Tools
- US-019: Slack Event Processing
- US-029: Test Agent Slack Communication
- US-047: Manual Self-Improvement Trigger

### Phase 4: Documentation
**1 story remaining**

Final deployment documentation:
- US-051: Documentation and Deployment Guide

## Usage

### Execute Phase 1 Only (Main Agent Core)
```bash
python ralph.py execute-plan --phase 1 --max-iterations 20
```

This will execute ONLY the 16 stories in Phase 1, ignoring Test Agent and Slack integration.

### Execute Phase 2 (Test Agent)
```bash
python ralph.py execute-plan --phase 2 --max-iterations 10
```

### Execute Phase 3 (Slack Integration)
```bash
python ralph.py execute-plan --phase 3 --max-iterations 10
```

### Execute All Remaining Stories (No Phase Filter)
```bash
python ralph.py execute-plan --max-iterations 50
```

Without `--phase`, Ralph executes all incomplete stories regardless of phase.

## Strategy

**Recommended approach for your use case:**

1. **Start with Phase 1** - Build the complete main agent with all core features, testable via CLI
2. **Skip Phase 2 for now** - Test Agent can come later when you want the dual-agent architecture
3. **Skip Phase 3 for now** - Slack integration is the last step
4. **Phase 4 when ready** - Write deployment docs after testing everything

**Command to focus on Phase 1 only:**
```bash
python ralph.py execute-plan --phase 1
```

This gets you a fully functional autonomous agent with:
- Self-modification capabilities
- Scheduled background tasks
- RSS research and learning
- Self-improvement workflow
- All testable from the command line

Then later you can add Test Agent (Phase 2) and Slack (Phase 3) when needed.

## Checking Status

To see what's in each phase:
```bash
cat prd-slack-agent.json | jq '.metadata.phases'
```

To see incomplete stories in Phase 1:
```bash
cat prd-slack-agent.json | jq -r '.userStories[] | select(.passes == false and .phase == 1) | "\(.id): \(.title)"'
```
