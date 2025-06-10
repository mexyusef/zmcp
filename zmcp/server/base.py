"""
ZMCP Server Base Implementation

Base classes for MCP server implementation.
"""
import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union

from zmcp.core.mcp import Content, Resource, TextContent, Tool, Prompt

logger = logging.getLogger(__name__)


class MCPServer:
    """Base MCP Server implementation."""

    def __init__(self, name: str, description: str = ""):
        """
        Initialize MCP server.

        Args:
            name: Server name
            description: Server description
        """
        self.name = name
        self.description = description
        self.tools: Dict[str, Tool] = {}
        self.resources: Dict[str, Resource] = {}
        self.prompts: Dict[str, Prompt] = {}

    def add_tool(self, tool: Tool) -> None:
        """
        Add a tool to the server.

        Args:
            tool: Tool instance
        """
        if tool.name in self.tools:
            logger.warning(f"Tool {tool.name} already exists, replacing")
        self.tools[tool.name] = tool

    def tool(self, name: str, description: str, input_schema: Optional[Dict[str, Any]] = None):
        """
        Tool decorator for registering tool handlers.

        Args:
            name: Tool name
            description: Tool description
            input_schema: JSON Schema for tool inputs

        Returns:
            Decorator function
        """
        def decorator(func: Callable):
            self.add_tool(Tool(name, description, func, input_schema))
            return func
        return decorator

    def add_resource(self, resource: Resource) -> None:
        """
        Add a resource to the server.

        Args:
            resource: Resource instance
        """
        if resource.uri_template in self.resources:
            logger.warning(f"Resource {resource.uri_template} already exists, replacing")
        self.resources[resource.uri_template] = resource

    def resource(self, uri_template: str, description: str):
        """
        Resource decorator for registering resource handlers.

        Args:
            uri_template: URI template for resource
            description: Resource description

        Returns:
            Decorator function
        """
        def decorator(func: Callable):
            self.add_resource(Resource(uri_template, description, func))
            return func
        return decorator

    def add_prompt(self, prompt: Prompt) -> None:
        """
        Add a prompt to the server.

        Args:
            prompt: Prompt instance
        """
        if prompt.name in self.prompts:
            logger.warning(f"Prompt {prompt.name} already exists, replacing")
        self.prompts[prompt.name] = prompt

    def prompt(self, name: str, description: str):
        """
        Prompt decorator for registering prompt handlers.

        Args:
            name: Prompt name
            description: Prompt description

        Returns:
            Decorator function
        """
        def decorator(func: Callable):
            self.add_prompt(Prompt(name, description, func))
            return func
        return decorator

    async def handle_tool_request(self, tool_name: str, arguments: Dict[str, Any]) -> List[Content]:
        """
        Handle a tool request.

        Args:
            tool_name: Name of tool to call
            arguments: Arguments for tool call

        Returns:
            List of Content objects

        Raises:
            ValueError: If tool not found or error in processing
        """
        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} not found")

        tool = self.tools[tool_name]
        if not tool.handler:
            raise ValueError(f"No handler for tool {tool_name}")

        try:
            result = tool.handler(**arguments)
            if asyncio.iscoroutine(result):
                result = await result

            if isinstance(result, str):
                return [TextContent(result)]
            elif isinstance(result, list):
                if all(isinstance(item, Content) for item in result):
                    return result
                else:
                    return [TextContent(json.dumps(result))]
            else:
                return [TextContent(json.dumps(result))]
        except Exception as e:
            logger.error(f"Error handling tool {tool_name}: {e}")
            raise ValueError(f"Error handling tool {tool_name}: {str(e)}")

    async def handle_resource_request(self, uri: str) -> List[Content]:
        """
        Handle a resource request.

        Args:
            uri: Resource URI

        Returns:
            List of Content objects

        Raises:
            ValueError: If resource not found or error in processing
        """
        for uri_template, resource in self.resources.items():
            # Simple URI template matching - could be enhanced with more complex matching
            if uri.startswith(uri_template.split("{")[0]):
                if not resource.handler:
                    raise ValueError(f"No handler for resource {uri_template}")

                try:
                    result = resource.handler(uri)
                    if asyncio.iscoroutine(result):
                        result = await result

                    if isinstance(result, str):
                        return [TextContent(result)]
                    elif isinstance(result, list):
                        if all(isinstance(item, Content) for item in result):
                            return result
                        else:
                            return [TextContent(json.dumps(result))]
                    else:
                        return [TextContent(json.dumps(result))]
                except Exception as e:
                    logger.error(f"Error handling resource {uri}: {e}")
                    raise ValueError(f"Error handling resource {uri}: {str(e)}")

        raise ValueError(f"Resource {uri} not found")

    async def handle_prompt_request(self, prompt_name: str, text: str) -> List[Content]:
        """
        Handle a prompt request.

        Args:
            prompt_name: Name of prompt
            text: Prompt text

        Returns:
            List of Content objects

        Raises:
            ValueError: If prompt not found or error in processing
        """
        if prompt_name not in self.prompts:
            raise ValueError(f"Prompt {prompt_name} not found")

        prompt = self.prompts[prompt_name]
        if not prompt.handler:
            raise ValueError(f"No handler for prompt {prompt_name}")

        try:
            result = prompt.handler(text)
            if asyncio.iscoroutine(result):
                result = await result

            if isinstance(result, str):
                return [TextContent(result)]
            elif isinstance(result, list):
                if all(isinstance(item, Content) for item in result):
                    return result
                else:
                    return [TextContent(json.dumps(result))]
            else:
                return [TextContent(json.dumps(result))]
        except Exception as e:
            logger.error(f"Error handling prompt {prompt_name}: {e}")
            raise ValueError(f"Error handling prompt {prompt_name}: {str(e)}")

    def get_tools_list(self) -> List[Dict[str, Any]]:
        """Get list of tools as dictionaries."""
        return [tool.to_dict() for tool in self.tools.values()]

    def get_resources_list(self) -> List[Dict[str, Any]]:
        """Get list of resources as dictionaries."""
        return [resource.to_dict() for resource in self.resources.values()]

    def get_prompts_list(self) -> List[Dict[str, Any]]:
        """Get list of prompts as dictionaries."""
        return [prompt.to_dict() for prompt in self.prompts.values()]
