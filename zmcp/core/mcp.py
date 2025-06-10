"""
ZMCP MCP Core

Core implementation of the Model Context Protocol (MCP).
"""
import asyncio
import json
import logging
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union

logger = logging.getLogger(__name__)


class ContentType(Enum):
    """Content types supported by MCP."""
    TEXT = "text"
    IMAGE = "image"
    RESOURCE = "resource"


class Content:
    """Base class for MCP content."""
    content_type: ContentType

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to MCP-compatible dictionary."""
        raise NotImplementedError("Subclasses must implement this")


class TextContent(Content):
    """Text content for MCP."""
    content_type = ContentType.TEXT

    def __init__(self, text: str, **kwargs):
        self.text = text
        super().__init__(**kwargs)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.content_type.value,
            "text": self.text
        }


class ImageContent(Content):
    """Image content for MCP."""
    content_type = ContentType.IMAGE

    def __init__(self, url: str, mime_type: str, **kwargs):
        self.url = url
        self.mime_type = mime_type
        super().__init__(**kwargs)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.content_type.value,
            "url": self.url,
            "mediaType": self.mime_type
        }


class EmbeddedResource(Content):
    """Embedded resource for MCP."""
    content_type = ContentType.RESOURCE

    def __init__(self, url: str, **kwargs):
        self.url = url
        super().__init__(**kwargs)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.content_type.value,
            "url": self.url
        }


class Tool:
    """MCP Tool definition."""

    def __init__(self,
                 name: str,
                 description: str,
                 handler: Optional[Callable] = None,
                 input_schema: Optional[Dict[str, Any]] = None):
        """
        Initialize tool definition.

        Args:
            name: Tool name
            description: Tool description
            handler: Function to handle tool calls
            input_schema: JSON Schema for tool inputs
        """
        self.name = name
        self.description = description
        self.handler = handler
        self.input_schema = input_schema or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to MCP-compatible dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema
        }


class Resource:
    """MCP Resource definition."""

    def __init__(self,
                 uri_template: str,
                 description: str,
                 handler: Optional[Callable] = None):
        """
        Initialize resource definition.

        Args:
            uri_template: URI template for resource
            description: Resource description
            handler: Function to handle resource requests
        """
        self.uri_template = uri_template
        self.description = description
        self.handler = handler

    def to_dict(self) -> Dict[str, Any]:
        """Convert to MCP-compatible dictionary."""
        return {
            "uriTemplate": self.uri_template,
            "description": self.description,
        }


class Prompt:
    """MCP Prompt definition."""

    def __init__(self,
                 name: str,
                 description: str,
                 handler: Optional[Callable] = None):
        """
        Initialize prompt definition.

        Args:
            name: Prompt name
            description: Prompt description
            handler: Function to handle prompt requests
        """
        self.name = name
        self.description = description
        self.handler = handler

    def to_dict(self) -> Dict[str, Any]:
        """Convert to MCP-compatible dictionary."""
        return {
            "name": self.name,
            "description": self.description,
        }
