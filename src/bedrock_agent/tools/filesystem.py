"""Filesystem tools for the coding agent."""

import os
from pathlib import Path
from typing import Annotated

from langchain_core.tools import tool


@tool
def list_directory(
    path: Annotated[str, "The directory path to list. Defaults to current directory."] = "."
) -> str:
    """List the contents of a directory, showing files and subdirectories."""
    try:
        target_path = Path(path).resolve()
        
        if not target_path.exists():
            return f"Error: Directory '{path}' does not exist."
        
        if not target_path.is_dir():
            return f"Error: '{path}' is not a directory."
        
        contents = []
        for item in sorted(target_path.iterdir()):
            if item.is_dir():
                contents.append(f"  {item.name}/ (directory)")
            else:
                size = item.stat().st_size
                contents.append(f"  {item.name} ({size} bytes)")
        
        if not contents:
            return f"Directory '{path}' is empty."
        
        return f"Contents of '{path}':\n" + "\n".join(contents)
    
    except PermissionError:
        return f"Error: Permission denied to access '{path}'."
    except Exception as e:
        return f"Error listing directory: {str(e)}"


@tool
def read_file(
    path: Annotated[str, "The path to the file to read."]
) -> str:
    """Read and return the contents of a file."""
    try:
        target_path = Path(path).resolve()
        
        if not target_path.exists():
            return f"Error: File '{path}' does not exist."
        
        if not target_path.is_file():
            return f"Error: '{path}' is not a file."
        
        # Check file size to avoid reading very large files
        size = target_path.stat().st_size
        if size > 1_000_000:  # 1MB limit
            return f"Error: File '{path}' is too large ({size} bytes). Maximum size is 1MB."
        
        content = target_path.read_text(encoding="utf-8")
        return f"Contents of '{path}':\n\n{content}"
    
    except PermissionError:
        return f"Error: Permission denied to read '{path}'."
    except UnicodeDecodeError:
        return f"Error: File '{path}' is not a valid text file."
    except Exception as e:
        return f"Error reading file: {str(e)}"


@tool
def write_file(
    path: Annotated[str, "The path where the file should be written."],
    content: Annotated[str, "The content to write to the file."]
) -> str:
    """Write content to a file. Creates the file if it doesn't exist, overwrites if it does."""
    try:
        target_path = Path(path).resolve()
        
        # Create parent directories if they don't exist
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        target_path.write_text(content, encoding="utf-8")
        
        return f"Successfully wrote {len(content)} characters to '{path}'."
    
    except PermissionError:
        return f"Error: Permission denied to write to '{path}'."
    except Exception as e:
        return f"Error writing file: {str(e)}"


@tool
def append_file(
    path: Annotated[str, "The path to the file to append to."],
    content: Annotated[str, "The content to append to the file."]
) -> str:
    """Append content to an existing file."""
    try:
        target_path = Path(path).resolve()
        
        if not target_path.exists():
            return f"Error: File '{path}' does not exist. Use write_file to create a new file."
        
        if not target_path.is_file():
            return f"Error: '{path}' is not a file."
        
        with open(target_path, "a", encoding="utf-8") as f:
            f.write(content)
        
        return f"Successfully appended {len(content)} characters to '{path}'."
    
    except PermissionError:
        return f"Error: Permission denied to append to '{path}'."
    except Exception as e:
        return f"Error appending to file: {str(e)}"


@tool
def create_directory(
    path: Annotated[str, "The path of the directory to create."]
) -> str:
    """Create a new directory. Creates parent directories if they don't exist."""
    try:
        target_path = Path(path).resolve()
        
        if target_path.exists():
            if target_path.is_dir():
                return f"Directory '{path}' already exists."
            else:
                return f"Error: '{path}' exists but is not a directory."
        
        target_path.mkdir(parents=True, exist_ok=True)
        
        return f"Successfully created directory '{path}'."
    
    except PermissionError:
        return f"Error: Permission denied to create '{path}'."
    except Exception as e:
        return f"Error creating directory: {str(e)}"


# Registry of all available tools
TOOL_REGISTRY = {
    "list_directory": list_directory,
    "read_file": read_file,
    "write_file": write_file,
    "append_file": append_file,
    "create_directory": create_directory,
}
