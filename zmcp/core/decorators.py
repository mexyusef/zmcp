"""
ZMCP Decorators

Decorators for MCP tools, resources, and prompts.
"""
import functools
import inspect
from typing import Any, Callable, Dict, Optional, TypeVar, cast

F = TypeVar('F', bound=Callable[..., Any])


def tool(func: Optional[F] = None) -> F:
    """Decorator to mark a function as an MCP tool.

    Args:
        func: Function to decorate

    Returns:
        Decorated function
    """
    def decorator(f: F) -> F:
        setattr(f, "__mcp_type__", "tool")
        return f

    if func is None:
        return cast(F, decorator)

    return decorator(func)


def resource(func: Optional[F] = None) -> F:
    """Decorator to mark a function as an MCP resource.

    Args:
        func: Function to decorate

    Returns:
        Decorated function
    """
    def decorator(f: F) -> F:
        setattr(f, "__mcp_type__", "resource")
        return f

    if func is None:
        return cast(F, decorator)

    return decorator(func)


def prompt(func: Optional[F] = None) -> F:
    """Decorator to mark a function as an MCP prompt.

    Args:
        func: Function to decorate

    Returns:
        Decorated function
    """
    def decorator(f: F) -> F:
        setattr(f, "__mcp_type__", "prompt")
        return f

    if func is None:
        return cast(F, decorator)

    return decorator(func)
