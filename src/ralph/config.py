"""Ralph configuration management."""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from ralph.detect import detect_project_config


class RalphConfig:
    """Configuration for Ralph execution.

    Ralph uses a centralized .ralph/ directory structure:
        project/
        ├── .ralph/
        │   ├── config.json      # Configuration (optional)
        │   ├── prd.json         # PRD file
        │   ├── progress.md      # Progress tracking
        │   ├── guardrails.md    # Learned failures
        │   ├── logs/            # Detailed iteration logs
        │   └── skills/          # Project-specific skills
        ├── .claude/
        │   └── skills/          # Claude Code skills (build, test, etc.)
        └── AGENTS.md            # Codebase patterns

    When running Ralph, point it to the project directory (containing .ralph/).
    """

    def __init__(self, project_dir: Optional[Path] = None, config_path: Optional[Path] = None) -> None:
        """Initialize Ralph configuration.

        Args:
            project_dir: Project directory containing .ralph/
            config_path: Legacy config path (deprecated, use project_dir instead)
        """
        # Support both old (config_path) and new (project_dir) initialization
        if project_dir:
            self.project_dir = Path(project_dir).resolve()
        elif config_path:
            # Legacy: derive project_dir from config_path
            self.project_dir = Path(config_path).parent.parent.resolve()
        else:
            self.project_dir = Path.cwd().resolve()

        self.ralph_dir = self.project_dir / ".ralph"
        self.config_path = self.ralph_dir / "config.json"
        self._config = self._load_config()
        self._ensure_directories()

    @property
    def prd_path(self) -> Path:
        """Path to PRD file."""
        return self.ralph_dir / "prd.json"

    @property
    def progress_path(self) -> Path:
        """Path to progress file."""
        return self.ralph_dir / "progress.md"

    @property
    def guardrails_path(self) -> Path:
        """Path to guardrails file."""
        return self.ralph_dir / "guardrails.md"

    @property
    def logs_dir(self) -> Path:
        """Path to logs directory."""
        return self.ralph_dir / "logs"

    @property
    def skills_dir(self) -> Path:
        """Path to Ralph skills directory."""
        return self.ralph_dir / "skills"

    @property
    def claude_skills_dir(self) -> Path:
        """Path to Claude Code skills directory."""
        return self.project_dir / ".claude" / "skills"

    @property
    def agents_md_path(self) -> Path:
        """Path to AGENTS.md file."""
        return self.project_dir / "AGENTS.md"

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default with auto-detection."""
        # If config.json exists, load it
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                loaded: Dict[str, Any] = json.load(f)
                return loaded

        # Auto-detect project configuration
        detected = detect_project_config(self.project_dir)

        # Build quality gates from detected commands
        quality_gates: Dict[str, Any] = {}

        if detected.get("typecheck"):
            quality_gates["typecheck"] = {
                "command": detected["typecheck"],
                "required": True,
                "timeout": 300
            }

        if detected.get("lint"):
            quality_gates["lint"] = {
                "command": detected["lint"],
                "required": True,
                "timeout": 120
            }

        if detected.get("test"):
            quality_gates["test"] = {
                "command": detected["test"],
                "required": True,
                "timeout": 600
            }

        # Build commands dict
        commands: Dict[str, Any] = {}
        if detected.get("typecheck"):
            commands["typecheck"] = detected["typecheck"]
        if detected.get("lint"):
            commands["lint"] = detected["lint"]
        if detected.get("test"):
            commands["test"] = detected["test"]

        # Default configuration with auto-detected values
        return {
            "project": {
                "name": self.project_dir.name,
                "type": detected.get("project_type", "unknown"),
                "packageManager": detected.get("package_manager", "unknown")
            },
            "commands": commands,
            "qualityGates": quality_gates,
            "git": {
                "baseBranch": "main",
                "commitMessageFormat": "feat: {story_id} - {story_title}",
                "autoPush": False,
                "createPR": False
            },
            "ralph": {
                "maxIterations": 0,  # 0 = unlimited
                "iterationTimeout": 3600,
                "maxFailures": 3,
                "updateAgentsMd": True,
                "createSkills": True,
                "enableMetrics": True,
                "useStreaming": True,
                "useAISelection": True,
                "workingDirectory": None  # None = use project_dir
            },
            "claude": {
                "model": "claude-sonnet-4-5-20250929",
                "maxTokens": 8192,
                "temperature": 0.7
            },
            "paths": {
                "prdFile": "prd.json",
                "agentsMdFile": "AGENTS.md"
            }
        }

    def _ensure_directories(self) -> None:
        """Ensure required directories exist."""
        self.ralph_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.claude_skills_dir.mkdir(parents=True, exist_ok=True)

    def save(self) -> None:
        """Save configuration to file."""
        self.ralph_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self._config, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation.

        Args:
            key: Configuration key in dot notation (e.g., "ralph.maxIterations")
            default: Default value if key doesn't exist

        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value: Any = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        """Set configuration value using dot notation.

        Args:
            key: Configuration key in dot notation (e.g., "ralph.maxIterations")
            value: Value to set
        """
        keys = key.split('.')
        config: Any = self._config

        # Navigate to the parent dict
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        # Set the final key
        config[keys[-1]] = value
