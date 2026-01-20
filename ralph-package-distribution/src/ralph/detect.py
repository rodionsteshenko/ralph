"""Project type detection utilities."""

import json
from pathlib import Path
from typing import Dict, Optional


class ProjectType:
    """Project type constants."""

    NODE = "node"
    PYTHON = "python"
    RUST = "rust"
    GO = "go"
    UNKNOWN = "unknown"


class ProjectDetector:
    """Detects project type and configuration from project files."""

    # Project type detection patterns
    PROJECT_FILES: Dict[str, str] = {
        "package.json": ProjectType.NODE,
        "pyproject.toml": ProjectType.PYTHON,
        "setup.py": ProjectType.PYTHON,
        "requirements.txt": ProjectType.PYTHON,
        "Cargo.toml": ProjectType.RUST,
        "go.mod": ProjectType.GO,
    }

    def __init__(self, project_dir: Optional[Path] = None) -> None:
        """
        Initialize project detector.

        Args:
            project_dir: Project directory to scan. Defaults to current directory.
        """
        self.project_dir = project_dir or Path.cwd()

    def detect_project_type(self) -> str:
        """
        Detect project type from files in directory.

        Returns:
            Project type string (node, python, rust, go, or unknown)
        """
        for filename, project_type in self.PROJECT_FILES.items():
            if (self.project_dir / filename).exists():
                return project_type

        return ProjectType.UNKNOWN

    def detect_package_manager(self, project_type: str) -> str:
        """
        Detect package manager for a given project type.

        Args:
            project_type: Project type string

        Returns:
            Package manager name (npm, pnpm, yarn, pip, uv, cargo, go)
        """
        if project_type == ProjectType.NODE:
            # Check for lock files to determine package manager
            if (self.project_dir / "pnpm-lock.yaml").exists():
                return "pnpm"
            elif (self.project_dir / "yarn.lock").exists():
                return "yarn"
            else:
                return "npm"

        elif project_type == ProjectType.PYTHON:
            # Prefer uv if pyproject.toml exists, otherwise pip
            if (self.project_dir / "pyproject.toml").exists():
                return "uv"
            return "pip"

        elif project_type == ProjectType.RUST:
            return "cargo"

        elif project_type == ProjectType.GO:
            return "go"

        return "unknown"

    def detect_typecheck_command(self, project_type: str) -> Optional[str]:
        """
        Detect typecheck command for a project.

        Args:
            project_type: Project type string

        Returns:
            Typecheck command string or None if not applicable
        """
        if project_type == ProjectType.NODE:
            # Check for TypeScript
            package_json_path = self.project_dir / "package.json"
            if package_json_path.exists():
                with open(package_json_path, "r") as f:
                    try:
                        package_data = json.load(f)
                        scripts = package_data.get("scripts", {})

                        # Check for explicit typecheck script
                        if "typecheck" in scripts:
                            return "npm run typecheck"

                        # Check for tsc in scripts
                        if "tsc" in scripts:
                            return "npm run tsc"

                        # Check if typescript is a dependency
                        deps = {**package_data.get("dependencies", {}),
                                **package_data.get("devDependencies", {})}
                        if "typescript" in deps:
                            # Check for tsconfig.json
                            if (self.project_dir / "tsconfig.json").exists():
                                return "npx tsc --noEmit"
                    except json.JSONDecodeError:
                        pass

            return None

        elif project_type == ProjectType.PYTHON:
            # Check for mypy configuration
            has_mypy_config = (
                (self.project_dir / "mypy.ini").exists()
                or (self.project_dir / ".mypy.ini").exists()
            )

            # Check pyproject.toml for mypy config
            pyproject_path = self.project_dir / "pyproject.toml"
            if pyproject_path.exists():
                with open(pyproject_path, "r") as f:
                    content = f.read()
                    if "[tool.mypy]" in content:
                        has_mypy_config = True

            if has_mypy_config:
                return "mypy ."

            return None

        elif project_type == ProjectType.RUST:
            return "cargo check"

        elif project_type == ProjectType.GO:
            return "go vet ./..."

        return None

    def detect_lint_command(self, project_type: str) -> Optional[str]:
        """
        Detect lint command for a project.

        Args:
            project_type: Project type string

        Returns:
            Lint command string or None if not applicable
        """
        if project_type == ProjectType.NODE:
            package_json_path = self.project_dir / "package.json"
            if package_json_path.exists():
                with open(package_json_path, "r") as f:
                    try:
                        package_data = json.load(f)
                        scripts = package_data.get("scripts", {})

                        # Check for explicit lint script
                        if "lint" in scripts:
                            return "npm run lint"

                        # Check for eslint
                        deps = {**package_data.get("dependencies", {}),
                                **package_data.get("devDependencies", {})}
                        if "eslint" in deps:
                            return "npx eslint ."
                    except json.JSONDecodeError:
                        pass

            # Check for eslint config files
            eslint_configs = [
                ".eslintrc",
                ".eslintrc.js",
                ".eslintrc.json",
                ".eslintrc.yml",
                "eslint.config.js",
            ]
            for config in eslint_configs:
                if (self.project_dir / config).exists():
                    return "npx eslint ."

            return None

        elif project_type == ProjectType.PYTHON:
            # Check pyproject.toml for ruff config
            pyproject_path = self.project_dir / "pyproject.toml"
            if pyproject_path.exists():
                with open(pyproject_path, "r") as f:
                    content = f.read()
                    if "[tool.ruff]" in content:
                        return "ruff check ."

            # Check for ruff.toml
            if (self.project_dir / "ruff.toml").exists():
                return "ruff check ."

            # Check for pylint config
            pylint_configs = [".pylintrc", "pylintrc", "pyproject.toml"]
            for config in pylint_configs:
                config_path = self.project_dir / config
                if config_path.exists():
                    if config == "pyproject.toml":
                        with open(config_path, "r") as f:
                            if "[tool.pylint]" in f.read():
                                return "pylint ."
                    else:
                        return "pylint ."

            return None

        elif project_type == ProjectType.RUST:
            return "cargo clippy"

        elif project_type == ProjectType.GO:
            return "golangci-lint run"

        return None

    def detect_test_command(self, project_type: str) -> Optional[str]:
        """
        Detect test command for a project.

        Args:
            project_type: Project type string

        Returns:
            Test command string or None if not applicable
        """
        if project_type == ProjectType.NODE:
            package_json_path = self.project_dir / "package.json"
            if package_json_path.exists():
                with open(package_json_path, "r") as f:
                    try:
                        package_data = json.load(f)
                        scripts = package_data.get("scripts", {})

                        # Check for explicit test script
                        if "test" in scripts:
                            return "npm test"
                    except json.JSONDecodeError:
                        pass

            return None

        elif project_type == ProjectType.PYTHON:
            # Check for pytest
            if (self.project_dir / "pytest.ini").exists():
                return "pytest"

            # Check pyproject.toml for pytest config
            pyproject_path = self.project_dir / "pyproject.toml"
            if pyproject_path.exists():
                with open(pyproject_path, "r") as f:
                    content = f.read()
                    if "[tool.pytest" in content:
                        return "pytest"

            # Check if tests directory exists
            if (self.project_dir / "tests").exists():
                return "pytest"

            return None

        elif project_type == ProjectType.RUST:
            return "cargo test"

        elif project_type == ProjectType.GO:
            return "go test ./..."

        return None

    def detect_all(self) -> Dict[str, Optional[str]]:
        """
        Detect all project configuration.

        Returns:
            Dictionary with detected configuration:
            - project_type: Detected project type
            - package_manager: Detected package manager
            - typecheck: Typecheck command (or None)
            - lint: Lint command (or None)
            - test: Test command (or None)
        """
        project_type = self.detect_project_type()
        package_manager = self.detect_package_manager(project_type)

        return {
            "project_type": project_type,
            "package_manager": package_manager,
            "typecheck": self.detect_typecheck_command(project_type),
            "lint": self.detect_lint_command(project_type),
            "test": self.detect_test_command(project_type),
        }


def detect_project_config(project_dir: Optional[Path] = None) -> Dict[str, Optional[str]]:
    """
    Convenience function to detect project configuration.

    Args:
        project_dir: Project directory to scan. Defaults to current directory.

    Returns:
        Dictionary with detected configuration
    """
    detector = ProjectDetector(project_dir)
    return detector.detect_all()
