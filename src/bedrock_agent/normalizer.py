"""Normalization utilities for tool call formats across LLM providers."""

import json
from typing import Any


# The canonical internal format this codebase expects:
# {
#     "id": str,           # may be a generated fallback
#     "name": str,
#     "args": dict,
# }


def _is_pydantic(obj: Any) -> bool:
    """Return True if obj is a Pydantic v1 or v2 model instance."""
    return hasattr(obj, "model_dump") or hasattr(obj, "dict")


def _parse_args(args: Any) -> dict:
    """Coerce tool arguments into a dict regardless of how they arrived.
    
    Handles:
      - Already a dict (Claude / normalized LangChain)
      - A JSON string (OpenAI-compatible models)
      - A Pydantic model instance
      - None or empty (tools that take no arguments)
    """
    if args is None:
        return {}
    if isinstance(args, dict):
        return args
    if isinstance(args, str):
        try:
            parsed = json.loads(args)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    if _is_pydantic(args):
        fn = getattr(args, "model_dump", None) or getattr(args, "dict")
        return fn()
    # Last resort: try casting to dict
    try:
        return dict(args)
    except (TypeError, ValueError):
        return {}


def _extract_id(tool_call: Any, index: int) -> str:
    """Extract a tool call ID, falling back to a positional placeholder.

    Claude always provides an ID. Other providers may omit it or nest it
    differently. The fallback ensures ToolMessage construction never breaks,
    though replaying the conversation against a model that requires real IDs
    may still fail — that is a provider constraint, not something we can paper over.
    """
    fallback = f"tool_call_{index}"

    # Plain dict (Claude / LangChain normalized)
    if isinstance(tool_call, dict):
        return tool_call.get("id") or fallback

    # Object with a direct .id attribute
    if hasattr(tool_call, "id"):
        return tool_call.id or fallback

    return fallback


def _extract_name(tool_call: Any) -> str:
    """Extract the tool name, handling both flat and nested schemas.

    Flat  (Claude / LangChain):   tool_call["name"]
    Nested (raw OpenAI):          tool_call.function.name
    """
    # Flat dict
    if isinstance(tool_call, dict):
        if "name" in tool_call:
            return tool_call["name"]
        # Some dicts nest under a "function" key
        fn = tool_call.get("function", {})
        return fn.get("name", "") if isinstance(fn, dict) else ""

    # Object with direct .name
    if hasattr(tool_call, "name"):
        return tool_call.name

    # Object with nested .function.name (raw OpenAI SDK objects)
    if hasattr(tool_call, "function"):
        fn = tool_call.function
        if hasattr(fn, "name"):
            return fn.name

    return ""


def _extract_args(tool_call: Any) -> dict:
    """Extract tool arguments, handling both flat and nested schemas.

    Flat  (Claude / LangChain):   tool_call["args"]        (already a dict)
    Nested (raw OpenAI):          tool_call.function.arguments  (JSON string)
    """
    # Flat dict
    if isinstance(tool_call, dict):
        if "args" in tool_call:
            return _parse_args(tool_call["args"])
        fn = tool_call.get("function", {})
        if isinstance(fn, dict):
            return _parse_args(fn.get("arguments"))

    # Object with direct .args
    if hasattr(tool_call, "args"):
        return _parse_args(tool_call.args)

    # Object with nested .function.arguments
    if hasattr(tool_call, "function"):
        fn = tool_call.function
        if hasattr(fn, "arguments"):
            return _parse_args(fn.arguments)

    return {}


def normalize_tool_call(tool_call: Any, index: int = 0) -> dict:
    """Normalize a single tool call from any provider into the canonical format.

    Args:
        tool_call: A tool call in any supported format.
        index:     Position in the tool_calls list, used only for ID fallback.

    Returns:
        A plain dict: {"id": str, "name": str, "args": dict}

    Raises:
        ValueError: If a tool name cannot be extracted (indicates an unsupported
                    format that needs an explicit case added here).
    """
    name = _extract_name(tool_call)
    if not name:
        raise ValueError(
            f"Could not extract a tool name from tool_call at index {index}. "
            f"Unsupported format: {type(tool_call)!r}. "
            "Add an explicit case to `_extract_name`."
        )

    return {
        "id": _extract_id(tool_call, index),
        "name": name,
        "args": _extract_args(tool_call),
    }


def normalize_tool_calls(tool_calls: list[Any]) -> list[dict]:
    """Normalize an entire list of tool calls.

    Args:
        tool_calls: List of tool calls in any supported format.

    Returns:
        List of normalized dicts in canonical format.
    """
    return [normalize_tool_call(tc, i) for i, tc in enumerate(tool_calls)]


def serialize_tool_calls(tool_calls: list[Any]) -> list[dict]:
    """Produce a JSON-safe representation of tool_calls for save_conversation.

    Handles Pydantic model objects that would otherwise cause json.dump to fail.

    Args:
        tool_calls: Raw tool_calls from an AIMessage (any provider format).

    Returns:
        A list of plain dicts safe to pass to json.dump.
    """
    result = []
    for tc in tool_calls:
        if isinstance(tc, dict):
            result.append(tc)
        elif _is_pydantic(tc):
            fn = getattr(tc, "model_dump", None) or getattr(tc, "dict")
            result.append(fn())
        else:
            # Best-effort: normalize to canonical form rather than losing data
            try:
                result.append(normalize_tool_call(tc))
            except ValueError:
                result.append({"id": "", "name": str(tc), "args": {}})
    return result

def normalize_response_content(content: str | list) -> str:
    """Normalize response content to a plain string regardless of provider.

    Different providers return AIMessage.content in different formats:
      - Claude:             a plain string
      - OpenAI-compatible:  a list of content block dicts, e.g.
                            [{"type": "text", "text": "..."}, ...]
      - Mistral:            usually a string, occasionally a list
      - Amazon Nova:        a list of content block dicts

    Only "text" blocks are extracted. Other block types (tool_use, image,
    document, etc.) are intentionally ignored here — tool_use blocks are
    already handled upstream in the agentic loop before this method is
    ever called, so by the time we normalize the final response those
    blocks will not be present.

    Args:
        content: The raw content field from an AIMessage.

    Returns:
        A single concatenated string of all text content, stripped of
        leading/trailing whitespace. Returns an empty string if no text
        content is found.
    """
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        text_parts = []
        for block in content:
            # Some providers return plain strings inside the list
            if isinstance(block, str):
                text_parts.append(block)
            # Most providers return dicts with a "type" discriminator field
            elif isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "")
                if text:
                    text_parts.append(text)
            # Pydantic content block objects (some LangChain versions)
            elif _is_pydantic(block):
                block_dict = (
                    block.model_dump() if hasattr(block, "model_dump") else block.dict()
                )
                if block_dict.get("type") == "text":
                    text = block_dict.get("text", "")
                    if text:
                        text_parts.append(text)

        return " ".join(text_parts).strip()

    return str(content).strip()