#!/usr/bin/env python3
"""
Pretty-print Claude Code stream-json output with real-time progress indicators.
"""

import json
import sys
import subprocess
import argparse
from datetime import datetime
from typing import Dict, Any, Optional


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


def format_timestamp() -> str:
    """Get formatted timestamp."""
    return datetime.now().strftime("%H:%M:%S")


def print_header(text: str, color: str = Colors.CYAN):
    """Print a formatted header."""
    print(f"{color}{Colors.BOLD}▶ {text}{Colors.RESET}")


def print_info(text: str, indent: int = 0):
    """Print info text."""
    indent_str = "  " * indent
    print(f"{Colors.GRAY}{indent_str}{text}{Colors.RESET}")


def print_success(text: str, indent: int = 0):
    """Print success text."""
    indent_str = "  " * indent
    print(f"{Colors.GREEN}{indent_str}✓ {text}{Colors.RESET}")


def print_warning(text: str, indent: int = 0):
    """Print warning text."""
    indent_str = "  " * indent
    print(f"{Colors.YELLOW}{indent_str}⚠ {text}{Colors.RESET}")


def print_error(text: str, indent: int = 0):
    """Print error text."""
    indent_str = "  " * indent
    print(f"{Colors.RED}{indent_str}✗ {text}{Colors.RESET}")


def print_tool_call(tool_name: str, args: Optional[Dict] = None):
    """Print tool call information."""
    print(f"{Colors.MAGENTA}{Colors.BOLD}🔧 Tool: {tool_name}{Colors.RESET}")
    if args:
        args_str = json.dumps(args, indent=2)
        # Truncate very long arguments
        if len(args_str) > 200:
            args_str = args_str[:200] + "..."
        print_info(f"Args: {args_str}", indent=1)


def print_tool_result(result_type: str, is_error: bool, duration: Optional[float] = None):
    """Print tool result information."""
    if is_error:
        print_error(f"Result: {result_type} (failed)", indent=1)
    else:
        duration_str = f" ({duration:.1f}ms)" if duration else ""
        print_success(f"Result: {result_type}{duration_str}", indent=1)


def print_message(content: str, role: str = "assistant"):
    """Print message content."""
    if role == "assistant":
        print(f"{Colors.CYAN}{Colors.BOLD}💬 Assistant:{Colors.RESET}")
    else:
        print(f"{Colors.BLUE}{Colors.BOLD}👤 User:{Colors.RESET}")
    
    # Print content with indentation
    lines = content.split('\n')
    for line in lines[:10]:  # Show first 10 lines
        print_info(line, indent=1)
    if len(lines) > 10:
        print_info(f"... ({len(lines) - 10} more lines)", indent=1)


def process_stream_line(line: str):
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
                print_header(f"Initializing Claude Code session")
                print_info(f"Model: {data.get('model', 'unknown')}")
                print_info(f"Session ID: {data.get('session_id', 'unknown')[:8]}...")
                tools = data.get("tools", [])
                if tools:
                    print_info(f"Available tools: {', '.join(tools[:5])}{'...' if len(tools) > 5 else ''}")
        
        elif msg_type == "assistant":
            message = data.get("message", {})
            content = message.get("content", [])
            
            # Extract text content and tool uses
            text_parts = []
            for part in content:
                if isinstance(part, dict):
                    if part.get("type") == "text":
                        text_parts.append(part.get("text", ""))
                    elif part.get("type") == "tool_use":
                        tool_name = part.get("name", "unknown")
                        tool_id = part.get("id", "")
                        tool_input = part.get("input", {})
                        print_tool_call(tool_name, tool_input)
            
            if text_parts:
                print_message("".join(text_parts), "assistant")
        
        elif msg_type == "tool_call":
            tool_name = data.get("tool_name", "unknown")
            args = data.get("arguments", {})
            print_tool_call(tool_name, args)
        
        elif msg_type == "tool_result":
            result_type = data.get("subtype", "unknown")
            is_error = data.get("is_error", False)
            duration = data.get("duration_ms")
            print_tool_result(result_type, is_error, duration)
        
        elif msg_type == "user":
            # User messages often contain tool results
            message = data.get("message", {})
            content = message.get("content", [])
            
            for part in content:
                if isinstance(part, dict):
                    if part.get("type") == "tool_result":
                        tool_use_id = part.get("tool_use_id", "")
                        result_content = part.get("content", "")
                        is_error = part.get("is_error", False)
                        
                        if is_error:
                            print_error(f"Tool result (error): {str(result_content)[:100]}", indent=1)
                        else:
                            # Show a summary of the result
                            result_str = str(result_content)
                            if len(result_str) > 150:
                                result_str = result_str[:150] + "..."
                            print_success(f"Tool result received: {result_str}", indent=1)
        
        elif msg_type == "result":
            subtype = data.get("subtype", "")
            is_error = data.get("is_error", False)
            duration = data.get("duration_ms", 0) / 1000  # Convert to seconds
            
            if subtype == "success":
                print_success(f"Completed successfully ({duration:.2f}s)")
            elif subtype == "error":
                print_error(f"Failed ({duration:.2f}s)")
            
            # Show usage if available
            usage = data.get("usage", {})
            if usage:
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)
                print_info(f"Tokens: {input_tokens} in, {output_tokens} out")
            
            # Show cost if available
            cost = data.get("total_cost_usd")
            if cost:
                print_info(f"Cost: ${cost:.6f}")
        
        elif msg_type == "error":
            error_msg = data.get("message", "Unknown error")
            print_error(f"Error: {error_msg}")
        
        else:
            # Unknown type - only show if it's not a common internal type
            if msg_type not in ["user"]:  # Skip user messages, we handle them above
                print_info(f"Type: {msg_type}")
                # Only show a summary for unknown types
                data_str = json.dumps(data, indent=2)
                if len(data_str) > 300:
                    data_str = data_str[:300] + "..."
                print_info(data_str, indent=1)
    
    except json.JSONDecodeError:
        # Not JSON, print as-is
        if line:
            print_info(line)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run Claude Code with pretty-printed stream output"
    )
    parser.add_argument(
        "-p", "--prompt",
        help="Prompt to send to Claude"
    )
    parser.add_argument(
        "-f", "--file",
        help="File containing prompt"
    )
    parser.add_argument(
        "--model",
        help="Model to use"
    )
    parser.add_argument(
        "--dangerously-skip-permissions",
        action="store_true",
        help="Skip permission prompts"
    )
    parser.add_argument(
        "extra_args",
        nargs="*",
        help="Additional arguments to pass to claude"
    )
    parser.add_argument(
        "--show-prompt",
        action="store_true",
        help="Show the full prompt in output (default: hidden)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output from Claude"
    )

    args = parser.parse_args()

    # Build claude command
    cmd = ["claude", "--output-format", "stream-json"]

    # --verbose is required when using -p with stream-json output format
    if args.prompt or args.file or args.verbose:
        cmd.append("--verbose")

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

    # Run claude and process output
    if args.show_prompt:
        print_header(f"Running: {' '.join(cmd)}")
    else:
        # Show command without the prompt (which can be very long)
        display_cmd = [c for c in cmd if c != args.prompt] if args.prompt else cmd
        if args.prompt:
            display_cmd = display_cmd[:-1]  # Remove the -p flag too
            display_cmd.append("-p <prompt hidden>")
        print_header(f"Running: {' '.join(display_cmd)}")
    print()
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        for line in process.stdout:
            process_stream_line(line)
            sys.stdout.flush()
        
        process.wait()
        
        if process.returncode != 0:
            print_error(f"Claude exited with code {process.returncode}")
            sys.exit(process.returncode)
    
    except KeyboardInterrupt:
        print_warning("\nInterrupted by user")
        if process:
            process.terminate()
        sys.exit(130)
    except Exception as e:
        print_error(f"Error running claude: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
