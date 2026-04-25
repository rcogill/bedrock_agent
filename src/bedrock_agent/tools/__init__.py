"""Tools for the Bedrock Agent."""

from .filesystem import (
    list_directory,
    read_file,
    write_file,
    create_directory,
    TOOL_REGISTRY as FILESYSTEM_TOOL_REGISTRY,
)

from .research import (
    web_search,
    fetch_webpage,
    fetch_pdf,
    RESEARCH_TOOL_REGISTRY,
)

# Combined registry of all available tools
TOOL_REGISTRY = {
    **FILESYSTEM_TOOL_REGISTRY,
    **RESEARCH_TOOL_REGISTRY,
}

__all__ = [
    # Filesystem tools
    "list_directory",
    "read_file", 
    "write_file",
    "create_directory",
    # Research tools
    "web_search",
    "fetch_webpage",
    "fetch_pdf",
    # Registries
    "TOOL_REGISTRY",
    "FILESYSTEM_TOOL_REGISTRY",
    "RESEARCH_TOOL_REGISTRY",
]
