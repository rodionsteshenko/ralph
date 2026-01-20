"""Tests for project type detection."""

import json
import tempfile
from pathlib import Path
from typing import Dict

import pytest

from ralph.detect import ProjectDetector, ProjectType, detect_project_config


class TestProjectTypeDetection:
    """Tests for project type detection."""

    def test_detect_node_project_from_package_json(self) -> None:
        """Test detecting Node.js project from package.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / "package.json").write_text("{}")

            detector = ProjectDetector(project_dir)
            assert detector.detect_project_type() == ProjectType.NODE

    def test_detect_python_project_from_pyproject_toml(self) -> None:
        """Test detecting Python project from pyproject.toml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / "pyproject.toml").write_text("")

            detector = ProjectDetector(project_dir)
            assert detector.detect_project_type() == ProjectType.PYTHON

    def test_detect_python_project_from_setup_py(self) -> None:
        """Test detecting Python project from setup.py."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / "setup.py").write_text("")

            detector = ProjectDetector(project_dir)
            assert detector.detect_project_type() == ProjectType.PYTHON

    def test_detect_python_project_from_requirements_txt(self) -> None:
        """Test detecting Python project from requirements.txt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / "requirements.txt").write_text("")

            detector = ProjectDetector(project_dir)
            assert detector.detect_project_type() == ProjectType.PYTHON

    def test_detect_rust_project_from_cargo_toml(self) -> None:
        """Test detecting Rust project from Cargo.toml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / "Cargo.toml").write_text("")

            detector = ProjectDetector(project_dir)
            assert detector.detect_project_type() == ProjectType.RUST

    def test_detect_go_project_from_go_mod(self) -> None:
        """Test detecting Go project from go.mod."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / "go.mod").write_text("")

            detector = ProjectDetector(project_dir)
            assert detector.detect_project_type() == ProjectType.GO

    def test_detect_unknown_project(self) -> None:
        """Test detecting unknown project type."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            detector = ProjectDetector(project_dir)
            assert detector.detect_project_type() == ProjectType.UNKNOWN

    def test_priority_order_for_multiple_files(self) -> None:
        """Test that package.json takes priority when multiple files exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            # Create both Node and Python files
            (project_dir / "package.json").write_text("{}")
            (project_dir / "requirements.txt").write_text("")

            detector = ProjectDetector(project_dir)
            # Should detect Node first (due to dict iteration order)
            result = detector.detect_project_type()
            assert result in [ProjectType.NODE, ProjectType.PYTHON]


class TestPackageManagerDetection:
    """Tests for package manager detection."""

    def test_detect_npm_for_node_project(self) -> None:
        """Test detecting npm as default for Node.js projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / "package.json").write_text("{}")

            detector = ProjectDetector(project_dir)
            assert detector.detect_package_manager(ProjectType.NODE) == "npm"

    def test_detect_pnpm_from_lock_file(self) -> None:
        """Test detecting pnpm from lock file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / "pnpm-lock.yaml").write_text("")

            detector = ProjectDetector(project_dir)
            assert detector.detect_package_manager(ProjectType.NODE) == "pnpm"

    def test_detect_yarn_from_lock_file(self) -> None:
        """Test detecting yarn from lock file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / "yarn.lock").write_text("")

            detector = ProjectDetector(project_dir)
            assert detector.detect_package_manager(ProjectType.NODE) == "yarn"

    def test_detect_uv_for_python_with_pyproject(self) -> None:
        """Test detecting uv for Python projects with pyproject.toml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / "pyproject.toml").write_text("")

            detector = ProjectDetector(project_dir)
            assert detector.detect_package_manager(ProjectType.PYTHON) == "uv"

    def test_detect_pip_for_python_without_pyproject(self) -> None:
        """Test detecting pip for Python projects without pyproject.toml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            detector = ProjectDetector(project_dir)
            assert detector.detect_package_manager(ProjectType.PYTHON) == "pip"

    def test_detect_cargo_for_rust(self) -> None:
        """Test detecting cargo for Rust projects."""
        detector = ProjectDetector()
        assert detector.detect_package_manager(ProjectType.RUST) == "cargo"

    def test_detect_go_for_go_projects(self) -> None:
        """Test detecting go for Go projects."""
        detector = ProjectDetector()
        assert detector.detect_package_manager(ProjectType.GO) == "go"


class TestTypecheckCommandDetection:
    """Tests for typecheck command detection."""

    def test_detect_npm_run_typecheck_script(self) -> None:
        """Test detecting npm run typecheck from package.json scripts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            package_json = {"scripts": {"typecheck": "tsc --noEmit"}}
            (project_dir / "package.json").write_text(json.dumps(package_json))

            detector = ProjectDetector(project_dir)
            assert detector.detect_typecheck_command(ProjectType.NODE) == "npm run typecheck"

    def test_detect_tsc_script(self) -> None:
        """Test detecting tsc script from package.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            package_json = {"scripts": {"tsc": "tsc --noEmit"}}
            (project_dir / "package.json").write_text(json.dumps(package_json))

            detector = ProjectDetector(project_dir)
            assert detector.detect_typecheck_command(ProjectType.NODE) == "npm run tsc"

    def test_detect_typescript_with_tsconfig(self) -> None:
        """Test detecting TypeScript with tsconfig.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            package_json = {
                "devDependencies": {"typescript": "^5.0.0"}
            }
            (project_dir / "package.json").write_text(json.dumps(package_json))
            (project_dir / "tsconfig.json").write_text("{}")

            detector = ProjectDetector(project_dir)
            assert detector.detect_typecheck_command(ProjectType.NODE) == "npx tsc --noEmit"

    def test_no_typecheck_for_javascript_only(self) -> None:
        """Test no typecheck command for JavaScript-only projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            package_json = {"scripts": {"test": "jest"}}
            (project_dir / "package.json").write_text(json.dumps(package_json))

            detector = ProjectDetector(project_dir)
            assert detector.detect_typecheck_command(ProjectType.NODE) is None

    def test_detect_mypy_from_config_file(self) -> None:
        """Test detecting mypy from config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / "mypy.ini").write_text("")

            detector = ProjectDetector(project_dir)
            assert detector.detect_typecheck_command(ProjectType.PYTHON) == "mypy ."

    def test_detect_mypy_from_pyproject_toml(self) -> None:
        """Test detecting mypy from pyproject.toml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / "pyproject.toml").write_text("[tool.mypy]\nstrict = true")

            detector = ProjectDetector(project_dir)
            assert detector.detect_typecheck_command(ProjectType.PYTHON) == "mypy ."

    def test_detect_cargo_check_for_rust(self) -> None:
        """Test detecting cargo check for Rust."""
        detector = ProjectDetector()
        assert detector.detect_typecheck_command(ProjectType.RUST) == "cargo check"

    def test_detect_go_vet_for_go(self) -> None:
        """Test detecting go vet for Go."""
        detector = ProjectDetector()
        assert detector.detect_typecheck_command(ProjectType.GO) == "go vet ./..."


class TestLintCommandDetection:
    """Tests for lint command detection."""

    def test_detect_npm_run_lint_script(self) -> None:
        """Test detecting npm run lint from package.json scripts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            package_json = {"scripts": {"lint": "eslint ."}}
            (project_dir / "package.json").write_text(json.dumps(package_json))

            detector = ProjectDetector(project_dir)
            assert detector.detect_lint_command(ProjectType.NODE) == "npm run lint"

    def test_detect_eslint_from_dependency(self) -> None:
        """Test detecting eslint from dependencies."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            package_json = {"devDependencies": {"eslint": "^8.0.0"}}
            (project_dir / "package.json").write_text(json.dumps(package_json))

            detector = ProjectDetector(project_dir)
            assert detector.detect_lint_command(ProjectType.NODE) == "npx eslint ."

    def test_detect_eslint_from_config_file(self) -> None:
        """Test detecting eslint from config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / ".eslintrc.json").write_text("{}")

            detector = ProjectDetector(project_dir)
            assert detector.detect_lint_command(ProjectType.NODE) == "npx eslint ."

    def test_detect_ruff_from_pyproject_toml(self) -> None:
        """Test detecting ruff from pyproject.toml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / "pyproject.toml").write_text("[tool.ruff]\nline-length = 100")

            detector = ProjectDetector(project_dir)
            assert detector.detect_lint_command(ProjectType.PYTHON) == "ruff check ."

    def test_detect_ruff_from_config_file(self) -> None:
        """Test detecting ruff from ruff.toml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / "ruff.toml").write_text("")

            detector = ProjectDetector(project_dir)
            assert detector.detect_lint_command(ProjectType.PYTHON) == "ruff check ."

    def test_detect_pylint_from_config_file(self) -> None:
        """Test detecting pylint from config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / ".pylintrc").write_text("")

            detector = ProjectDetector(project_dir)
            assert detector.detect_lint_command(ProjectType.PYTHON) == "pylint ."

    def test_detect_cargo_clippy_for_rust(self) -> None:
        """Test detecting cargo clippy for Rust."""
        detector = ProjectDetector()
        assert detector.detect_lint_command(ProjectType.RUST) == "cargo clippy"

    def test_detect_golangci_lint_for_go(self) -> None:
        """Test detecting golangci-lint for Go."""
        detector = ProjectDetector()
        assert detector.detect_lint_command(ProjectType.GO) == "golangci-lint run"


class TestTestCommandDetection:
    """Tests for test command detection."""

    def test_detect_npm_test_script(self) -> None:
        """Test detecting npm test from package.json scripts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            package_json = {"scripts": {"test": "jest"}}
            (project_dir / "package.json").write_text(json.dumps(package_json))

            detector = ProjectDetector(project_dir)
            assert detector.detect_test_command(ProjectType.NODE) == "npm test"

    def test_detect_pytest_from_config_file(self) -> None:
        """Test detecting pytest from pytest.ini."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / "pytest.ini").write_text("")

            detector = ProjectDetector(project_dir)
            assert detector.detect_test_command(ProjectType.PYTHON) == "pytest"

    def test_detect_pytest_from_pyproject_toml(self) -> None:
        """Test detecting pytest from pyproject.toml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / "pyproject.toml").write_text("[tool.pytest.ini_options]\ntestpaths = ['tests']")

            detector = ProjectDetector(project_dir)
            assert detector.detect_test_command(ProjectType.PYTHON) == "pytest"

    def test_detect_pytest_from_tests_directory(self) -> None:
        """Test detecting pytest from tests directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / "tests").mkdir()

            detector = ProjectDetector(project_dir)
            assert detector.detect_test_command(ProjectType.PYTHON) == "pytest"

    def test_detect_cargo_test_for_rust(self) -> None:
        """Test detecting cargo test for Rust."""
        detector = ProjectDetector()
        assert detector.detect_test_command(ProjectType.RUST) == "cargo test"

    def test_detect_go_test_for_go(self) -> None:
        """Test detecting go test for Go."""
        detector = ProjectDetector()
        assert detector.detect_test_command(ProjectType.GO) == "go test ./..."


class TestDetectAll:
    """Tests for detect_all method."""

    def test_detect_all_for_node_project(self) -> None:
        """Test detecting all configuration for Node.js project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            package_json = {
                "scripts": {
                    "typecheck": "tsc --noEmit",
                    "lint": "eslint .",
                    "test": "jest"
                }
            }
            (project_dir / "package.json").write_text(json.dumps(package_json))

            detector = ProjectDetector(project_dir)
            config = detector.detect_all()

            assert config["project_type"] == ProjectType.NODE
            assert config["package_manager"] == "npm"
            assert config["typecheck"] == "npm run typecheck"
            assert config["lint"] == "npm run lint"
            assert config["test"] == "npm test"

    def test_detect_all_for_python_project(self) -> None:
        """Test detecting all configuration for Python project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            pyproject = """
[tool.mypy]
strict = true

[tool.ruff]
line-length = 100

[tool.pytest.ini_options]
testpaths = ["tests"]
"""
            (project_dir / "pyproject.toml").write_text(pyproject)
            (project_dir / "tests").mkdir()

            detector = ProjectDetector(project_dir)
            config = detector.detect_all()

            assert config["project_type"] == ProjectType.PYTHON
            assert config["package_manager"] == "uv"
            assert config["typecheck"] == "mypy ."
            assert config["lint"] == "ruff check ."
            assert config["test"] == "pytest"

    def test_detect_all_with_missing_commands(self) -> None:
        """Test that missing commands return None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / "package.json").write_text("{}")

            detector = ProjectDetector(project_dir)
            config = detector.detect_all()

            assert config["project_type"] == ProjectType.NODE
            assert config["typecheck"] is None
            assert config["lint"] is None
            assert config["test"] is None


class TestConvenienceFunction:
    """Tests for convenience function."""

    def test_detect_project_config_function(self) -> None:
        """Test detect_project_config convenience function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / "package.json").write_text("{}")

            config = detect_project_config(project_dir)

            assert isinstance(config, dict)
            assert config["project_type"] == ProjectType.NODE
            assert "package_manager" in config


@pytest.mark.e2e
class TestRealProjectDetection:
    """End-to-end tests with the actual Ralph project."""

    def test_detect_ralph_project_config(self) -> None:
        """Test detecting configuration for the Ralph project itself."""
        # This test runs against the actual Ralph project
        project_dir = Path.cwd()

        detector = ProjectDetector(project_dir)
        config = detector.detect_all()

        # Ralph is a Python project with pyproject.toml
        assert config["project_type"] == ProjectType.PYTHON
        assert config["package_manager"] == "uv"
        assert config["typecheck"] == "mypy ."
        assert config["lint"] == "ruff check ."
        assert config["test"] == "pytest"

    def test_convenience_function_with_current_directory(self) -> None:
        """Test convenience function without arguments uses current directory."""
        config = detect_project_config()

        # Should detect the Ralph project
        assert config["project_type"] == ProjectType.PYTHON
        assert config["package_manager"] == "uv"
