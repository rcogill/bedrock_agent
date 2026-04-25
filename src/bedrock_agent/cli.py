"""Command-line interface for the Bedrock Agent with markdown rendering."""

import argparse
import sys
from pathlib import Path

from prompt_toolkit import PromptSession
from rich.console import Console
from rich.markdown import Markdown

from .agent import BedrockAgent
from .config import load_config

# Initialize Rich console for formatted output
console = Console()


def print_help():
    """Print available commands."""
    print("\nAvailable commands:")
    print("  /help          - Show this help message")
    print("  /save <file>   - Save conversation to a JSON file")
    print("  /load <file>   - Load conversation from a JSON file")
    print("  /clear         - Clear conversation history")
    print("  /exit, /quit   - Exit the application")
    print()


def print_tool_call(name: str, args: dict, result: str) -> None:
    """Display a tool call and its result.
    
    Args:
        name: The name of the tool being called
        args: Dictionary of arguments passed to the tool
        result: The result returned by the tool
    """
    # Format arguments as key="value" pairs
    args_str = ", ".join(f'{k}="{v}"' for k, v in args.items())
    if len(args_str) > 100:
        args_str = args_str[:100] + "..."

    print(f"\n[Tool: {name}({args_str})]")
    
    # Indent the result for readability
    indented_result = "  " + result.replace("\n", "\\n")
    
    # Truncate long results
    if len(indented_result) > 100:
        indented_result = indented_result[:100] + "..."
    
    print(indented_result)


def print_response(response: str) -> None:
    """Display an agent response with markdown rendering.
    
    Args:
        response: The response text from the agent
    """
    console.print()
    console.print("[bold]Agent:[/bold]")
    md = Markdown(response)
    console.print(md)
    console.print()


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Bedrock Agent CLI - Run agentic workflows using AWS Bedrock"
    )
    parser.add_argument(
        "--config", "-c",
        type=str,
        help="Path to the agent configuration file (YAML)",
        default=None,
    )
    
    args = parser.parse_args()
    
    # Load configuration
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Initialize agent
    try:
        agent = BedrockAgent(config)
    except Exception as e:
        print(f"Error initializing agent: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Set up prompt session with in-memory history for the current session
    session: PromptSession = PromptSession()
    
    print("\nBedrock Agent CLI")
    print(f"Model: {config.model.model_id}")
    print(f"Tools: {', '.join(config.tools) if config.tools else 'None'}")
    print("Type /help for available commands, /exit to quit.\n")
    
    while True:
        try:
            user_input = session.prompt("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        
        if not user_input:
            continue
        
        # Handle special commands
        if user_input.lower() in ("/exit", "/quit"):
            print("Goodbye!")
            break
        
        if user_input.lower() == "/help":
            print_help()
            continue
        
        if user_input.lower() == "/clear":
            agent.clear_conversation()
            print("Conversation history cleared.\n")
            continue
        
        if user_input.lower().startswith("/save"):
            parts = user_input.split(maxsplit=1)
            if len(parts) < 2:
                print("Usage: /save <filename>\n")
                continue
            filepath = parts[1]
            try:
                agent.save_conversation(filepath)
                print(f"Conversation saved to '{filepath}'.\n")
            except Exception as e:
                print(f"Error saving conversation: {e}\n")
            continue
        
        if user_input.lower().startswith("/load"):
            parts = user_input.split(maxsplit=1)
            if len(parts) < 2:
                print("Usage: /load <filename>\n")
                continue
            filepath = parts[1]
            try:
                agent.load_conversation(filepath)
                print(f"Conversation loaded from '{filepath}'.\n")
            except Exception as e:
                print(f"Error loading conversation: {e}\n")
            continue
        
        if user_input.startswith("/"):
            print(f"Unknown command: {user_input}")
            print_help()
            continue
        
        # Process regular chat input
        try:
            response = agent.chat(user_input, on_tool_call=print_tool_call)
            print_response(response)
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
