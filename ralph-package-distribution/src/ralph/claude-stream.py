#!/usr/bin/env python3
"""
Pretty-print Claude Code stream-json output with grouped intent display.

Groups tool calls by the assistant's stated intent, showing a clean
tree structure of what Claude is doing and why.
"""

import json
import sys
import subprocess
import argparse
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


class Colors:
    """ANSI color codes for terminal output."""
    RESET = '\033[0m'
    BOLD = '\033[1m'

    # Bright colors
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    MAGENTA = '\033[95m'
    RED = '\033[91m'
    WHITE = '\033[97m'

    # Dim colors
    DIM = '\033[2m'
    GRAY = '\033[90m'


@dataclass
class ToolCall:
    """Represents a single tool call."""
    name: str
    description: str = ""
    file_path: str = ""
    command: str = ""
    result: str = ""
    is_error: bool = False
    duration_ms: Optional[float] = None
    completed: bool = False


@dataclass
class IntentGroup:
    """A group of tool calls under a single intent."""
    intent: str
    timestamp: str
    tools: List[ToolCall] = field(default_factory=list)
    duration_s: float = 0.0


class StreamProcessor:
    """Processes Claude stream output and groups by intent."""

    def __init__(self) -> None:
        self.groups: List[IntentGroup] = []
        self.current_group: Optional[IntentGroup] = None
        self.pending_tools: Dict[str, ToolCall] = {}  # tool_use_id -> ToolCall
        self.session_start: Optional[datetime] = None
        self.model: str = ""
        self.session_id: str = ""
        self.total_tools: int = 0
        self.total_errors: int = 0

    def _format_timestamp(self) -> str:
        return datetime.now().strftime("%H:%M:%S")

    def _print_header(self) -> None:
        """Print session header."""
        print(f"{Colors.CYAN}╔══════════════════════════════════════════════════════════════════════╗{Colors.RESET}")
        print(f"{Colors.CYAN}║{Colors.RESET}  {Colors.BOLD}RALPH → CLAUDE{Colors.RESET}                                                      {Colors.CYAN}║{Colors.RESET}")
        model_display = self.model[:20] if self.model else "unknown"
        session_display = self.session_id[:8] if self.session_id else "unknown"
        info_line = f"  Model: {model_display}  │  Session: {session_display}"
        padding = 70 - len(info_line)
        print(f"{Colors.CYAN}║{Colors.RESET}{Colors.GRAY}{info_line}{' ' * padding}{Colors.RESET}{Colors.CYAN}║{Colors.RESET}")
        print(f"{Colors.CYAN}╚══════════════════════════════════════════════════════════════════════╝{Colors.RESET}")
        print()

    def _flush_current_group(self) -> None:
        """Close the current group (tools already printed incrementally)."""
        if not self.current_group:
            return

        # Just add a blank line to separate groups
        # (tools were already printed incrementally via _reprint_current_group)
        print()
        self.groups.append(self.current_group)
        self.current_group = None

    def _format_tool_info(self, tool: ToolCall) -> str:
        """Format tool name and key details."""
        name_lower = tool.name.lower()

        if name_lower == "bash":
            cmd = tool.command or tool.description or "command"
            # Truncate long commands
            if len(cmd) > 40:
                cmd = cmd[:37] + "..."
            return f"{Colors.YELLOW}bash:{Colors.RESET} {cmd}"

        elif name_lower in ("write", "edit"):
            path = tool.file_path or "file"
            # Show just filename for brevity
            if "/" in path:
                path = path.split("/")[-1]
            return f"{Colors.GREEN}{tool.name.lower()}:{Colors.RESET} {path}"

        elif name_lower == "read":
            path = tool.file_path or "file"
            if "/" in path:
                path = path.split("/")[-1]
            return f"{Colors.BLUE}read:{Colors.RESET} {path}"

        elif name_lower in ("glob", "grep"):
            return f"{Colors.MAGENTA}{tool.name.lower()}:{Colors.RESET} {tool.description or 'search'}"

        elif name_lower == "task":
            return f"{Colors.CYAN}task:{Colors.RESET} {tool.description or 'subtask'}"

        else:
            return f"{Colors.WHITE}{tool.name}:{Colors.RESET} {tool.description or ''}"

    def _format_tool_status(self, tool: ToolCall) -> str:
        """Format tool completion status."""
        if not tool.completed:
            return ""
            # return f" {Colors.YELLOW}⠸{Colors.RESET}"

        if tool.is_error:
            result_preview = (tool.result or "error")[:30]
            return f" {Colors.RED}✗ {result_preview}{Colors.RESET}"

        # Show brief result for certain tools
        if tool.result:
            result = tool.result.strip()
            # For bash commands, show brief output
            if tool.name.lower() == "bash" and result:
                lines = result.split('\n')
                if len(lines) == 1 and len(result) < 40:
                    return f" {Colors.GREEN}→{Colors.RESET} {Colors.GRAY}{result}{Colors.RESET}"
                elif len(lines) > 1:
                    return f" {Colors.GREEN}→{Colors.RESET} {Colors.GRAY}({len(lines)} lines){Colors.RESET}"

        return f" {Colors.GREEN}✓{Colors.RESET}"

    def _start_new_group(self, intent: str) -> None:
        """Start a new intent group."""
        self._flush_current_group()
        self.current_group = IntentGroup(
            intent=intent,
            timestamp=self._format_timestamp()
        )

    def _add_tool_to_group(self, tool_id: str, tool: ToolCall) -> None:
        """Add a tool call to the current group."""
        if not self.current_group:
            # Create implicit group if needed
            self._start_new_group("Working...")

        if self.current_group:
            self.current_group.tools.append(tool)
        self.pending_tools[tool_id] = tool
        self.total_tools += 1

        # Print in-progress indicator
        self._reprint_current_group()

    def _complete_tool(self, tool_id: str, result: str, is_error: bool) -> None:
        """Mark a tool as completed."""
        if tool_id in self.pending_tools:
            tool = self.pending_tools[tool_id]
            tool.result = result
            tool.is_error = is_error
            tool.completed = True
            if is_error:
                self.total_errors += 1
                # Print error status since original line showed in-progress
                tool_info = self._format_tool_info(tool)
                result_preview = (result or "error")[:50]
                print(f"           {Colors.GRAY}└──{Colors.RESET} {tool_info} {Colors.RED}✗ {result_preview}{Colors.RESET}")
            del self.pending_tools[tool_id]

    def _reprint_current_group(self) -> None:
        """Reprint the current group (for live updates)."""
        if not self.current_group:
            return

        group = self.current_group
        tools = group.tools

        # Move cursor up and clear previous output
        # For simplicity, we'll just print incrementally
        # A full implementation would use terminal control codes

        # Just print the latest tool
        if tools:
            tool = tools[-1]
            is_last = True  # We're printing incrementally
            prefix = "└──" if is_last and tool.completed else "├──"

            tool_info = self._format_tool_info(tool)
            status = self._format_tool_status(tool)

            if len(tools) == 1:
                # First tool - print the group header too
                timestamp = f"[{group.timestamp}]"
                intent_display = group.intent[:60] + "..." if len(group.intent) > 60 else group.intent

                tool_names = [t.name.lower() for t in tools]
                if any("glob" in n or "grep" in n or "read" in n for n in tool_names):
                    icon = "🔍"
                elif any("write" in n or "edit" in n for n in tool_names):
                    icon = "📁"
                elif any("bash" in n for n in tool_names):
                    icon = "⚡"
                else:
                    icon = "▸"

                print(f"\n{Colors.GRAY}{timestamp}{Colors.RESET} {icon} {Colors.BOLD}{intent_display}{Colors.RESET}")

            print(f"           {Colors.GRAY}{prefix}{Colors.RESET} {tool_info}{status}")

    def process_line(self, line: str) -> None:
        """Process a single line from the stream."""
        line = line.strip()
        if not line:
            return

        try:
            data = json.loads(line)
            msg_type = data.get("type")

            if msg_type == "system":
                subtype = data.get("subtype", "")
                if subtype == "init":
                    self.model = data.get("model", "unknown")
                    self.session_id = data.get("session_id", "")
                    self.session_start = datetime.now()
                    self._print_header()

            elif msg_type == "assistant":
                message = data.get("message", {})
                content = message.get("content", [])

                # Process content parts
                for part in content:
                    if isinstance(part, dict):
                        if part.get("type") == "text":
                            text = part.get("text", "").strip()
                            if text:
                                self._start_new_group(text)

                        elif part.get("type") == "tool_use":
                            tool_id = part.get("id", "")
                            tool_name = part.get("name", "unknown")
                            tool_input = part.get("input", {})

                            tool = ToolCall(
                                name=tool_name,
                                description=tool_input.get("description", ""),
                                file_path=tool_input.get("file_path", ""),
                                command=tool_input.get("command", "")
                            )
                            self._add_tool_to_group(tool_id, tool)

            elif msg_type == "user":
                message = data.get("message", {})
                content = message.get("content", [])

                for part in content:
                    if isinstance(part, dict) and part.get("type") == "tool_result":
                        tool_id = part.get("tool_use_id", "")
                        is_error = part.get("is_error", False)
                        result_content = part.get("content", "")

                        # Extract text from content
                        if isinstance(result_content, list):
                            texts = [p.get("text", "") for p in result_content if isinstance(p, dict)]
                            result_content = "\n".join(texts)

                        self._complete_tool(tool_id, str(result_content), is_error)

            elif msg_type == "result":
                self._flush_current_group()
                self._print_footer(data)

        except json.JSONDecodeError:
            pass

    def _print_footer(self, data: Dict[str, Any]) -> None:
        """Print session footer."""
        subtype = data.get("subtype", "")
        duration_ms = data.get("duration_ms", 0)
        duration_s = duration_ms / 1000

        usage = data.get("usage", {})
        total_tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
        cost = data.get("total_cost_usd", 0)

        print()
        print(f"{Colors.GRAY}───────────────────────────────────────────────────────────────────────{Colors.RESET}")

        status_icon = "✓" if subtype == "success" else "✗"
        status_color = Colors.GREEN if subtype == "success" else Colors.RED

        stats = []
        stats.append(f"{self.total_tools} tools")
        if self.total_errors > 0:
            stats.append(f"{Colors.RED}{self.total_errors} errors{Colors.RESET}")
        stats.append(f"{duration_s:.1f}s")
        if total_tokens > 0:
            stats.append(f"{total_tokens:,} tokens")
        if cost:
            stats.append(f"${cost:.4f}")

        print(f"{status_color}{status_icon} Complete{Colors.RESET} │ {' │ '.join(stats)}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run Claude Code with grouped intent display"
    )
    parser.add_argument("-p", "--prompt", help="Prompt to send to Claude")
    parser.add_argument("-f", "--file", help="File containing prompt")
    parser.add_argument("--model", help="Model to use")
    parser.add_argument(
        "--dangerously-skip-permissions",
        action="store_true",
        help="Skip permission prompts"
    )
    parser.add_argument("extra_args", nargs="*", help="Additional arguments to pass to claude")
    parser.add_argument("--show-prompt", action="store_true", help="Show the full prompt in output")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    # Build claude command
    cmd = ["claude", "--output-format", "stream-json", "--verbose"]

    if args.prompt:
        cmd.extend(["-p", args.prompt])
    elif args.file:
        cmd.extend(["-f", args.file])

    if args.model:
        cmd.extend(["--model", args.model])

    if args.dangerously_skip_permissions:
        cmd.append("--dangerously-skip-permissions")

    if args.extra_args:
        cmd.extend(args.extra_args)

    # Process stream
    processor = StreamProcessor()

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        if process.stdout:
            for line in process.stdout:
                processor.process_line(line)
                sys.stdout.flush()

        process.wait()

        if process.returncode != 0:
            print(f"{Colors.RED}✗ Claude exited with code {process.returncode}{Colors.RESET}")
            sys.exit(process.returncode)

    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⚠ Interrupted{Colors.RESET}")
        if process:
            process.terminate()
        sys.exit(130)
    except Exception as e:
        print(f"{Colors.RED}✗ Error: {e}{Colors.RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
