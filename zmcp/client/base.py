"""
ZMCP Client Base Implementation

Base classes for MCP client implementation.
"""
import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Set, Type, Union
import aiohttp

from zmcp.core.mcp import Content, Resource, TextContent, Tool, Prompt

logger = logging.getLogger(__name__)


class MCPClient:
    """Base MCP Client implementation."""

    def __init__(self, server_url: str):
        """
        Initialize MCP client.

        Args:
            server_url: URL of MCP server
        """
        self.server_url = server_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.tools: List[Tool] = []
        self.resources: List[Resource] = []
        self.prompts: List[Prompt] = []

    async def __aenter__(self):
        """Context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.disconnect()

    async def connect(self) -> None:
        """Connect to MCP server."""
        self.session = aiohttp.ClientSession()
        await self.fetch_capabilities()

    async def disconnect(self) -> None:
        """Disconnect from MCP server."""
        if self.session:
            await self.session.close()
            self.session = None

    async def fetch_capabilities(self) -> None:
        """Fetch server capabilities (tools, resources, prompts)."""
        await self.fetch_tools()
        await self.fetch_resources()
        await self.fetch_prompts()

    async def fetch_tools(self) -> None:
        """Fetch available tools from server."""
        if not self.session:
            raise RuntimeError("Not connected to server")

        try:
            async with self.session.get(f"{self.server_url}/list-tools") as response:
                response.raise_for_status()
                tools_data = await response.json()
                self.tools = [
                    Tool(
                        name=tool_data["name"],
                        description=tool_data["description"],
                        input_schema=tool_data.get("inputSchema", {})
                    )
                    for tool_data in tools_data
                ]
        except (aiohttp.ClientError, json.JSONDecodeError) as e:
            logger.error(f"Failed to fetch tools: {e}")
            self.tools = []

    async def fetch_resources(self) -> None:
        """Fetch available resources from server."""
        if not self.session:
            raise RuntimeError("Not connected to server")

        try:
            async with self.session.get(f"{self.server_url}/list-resources") as response:
                response.raise_for_status()
                resources_data = await response.json()
                self.resources = [
                    Resource(
                        uri_template=resource_data["uriTemplate"],
                        description=resource_data["description"]
                    )
                    for resource_data in resources_data
                ]
        except (aiohttp.ClientError, json.JSONDecodeError) as e:
            logger.error(f"Failed to fetch resources: {e}")
            self.resources = []

    async def fetch_prompts(self) -> None:
        """Fetch available prompts from server."""
        if not self.session:
            raise RuntimeError("Not connected to server")

        try:
            async with self.session.get(f"{self.server_url}/list-prompts") as response:
                response.raise_for_status()
                prompts_data = await response.json()
                self.prompts = [
                    Prompt(
                        name=prompt_data["name"],
                        description=prompt_data["description"]
                    )
                    for prompt_data in prompts_data
                ]
        except (aiohttp.ClientError, json.JSONDecodeError) as e:
            logger.error(f"Failed to fetch prompts: {e}")
            self.prompts = []

    async def call_tool(self, tool_name: str, **kwargs) -> List[Content]:
        """
        Call a tool on the server.

        Args:
            tool_name: Name of tool to call
            **kwargs: Arguments for tool call

        Returns:
            List of Content objects from response

        Raises:
            ValueError: If tool not found or error in processing
        """
        if not self.session:
            raise RuntimeError("Not connected to server")

        try:
            async with self.session.post(
                f"{self.server_url}/tool/{tool_name}",
                json=kwargs
            ) as response:
                if response.status == 400:
                    error_data = await response.json()
                    raise ValueError(error_data["error"])
                response.raise_for_status()
                content_data = await response.json()
                return self._parse_content_list(content_data)
        except aiohttp.ClientError as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            raise ValueError(f"Error calling tool {tool_name}: {str(e)}")

    async def request_resource(self, resource_uri: str) -> List[Content]:
        """
        Request a resource from the server.

        Args:
            resource_uri: Resource URI

        Returns:
            List of Content objects from response

        Raises:
            ValueError: If resource not found or error in processing
        """
        if not self.session:
            raise RuntimeError("Not connected to server")

        try:
            async with self.session.get(
                f"{self.server_url}/resource/{resource_uri}"
            ) as response:
                if response.status == 400:
                    error_data = await response.json()
                    raise ValueError(error_data["error"])
                response.raise_for_status()
                content_data = await response.json()
                return self._parse_content_list(content_data)
        except aiohttp.ClientError as e:
            logger.error(f"Error requesting resource {resource_uri}: {e}")
            raise ValueError(f"Error requesting resource {resource_uri}: {str(e)}")

    async def send_prompt(self, prompt_name: str, text: str) -> List[Content]:
        """
        Send a prompt to the server.

        Args:
            prompt_name: Name of prompt
            text: Prompt text

        Returns:
            List of Content objects from response

        Raises:
            ValueError: If prompt not found or error in processing
        """
        if not self.session:
            raise RuntimeError("Not connected to server")

        try:
            async with self.session.post(
                f"{self.server_url}/prompt/{prompt_name}",
                json={"text": text}
            ) as response:
                if response.status == 400:
                    error_data = await response.json()
                    raise ValueError(error_data["error"])
                response.raise_for_status()
                content_data = await response.json()
                return self._parse_content_list(content_data)
        except aiohttp.ClientError as e:
            logger.error(f"Error sending prompt {prompt_name}: {e}")
            raise ValueError(f"Error sending prompt {prompt_name}: {str(e)}")

    def _parse_content_list(self, content_data: List[Dict[str, Any]]) -> List[Content]:
        """
        Parse content list from server response.

        Args:
            content_data: Content data from server

        Returns:
            List of Content objects
        """
        result = []
        for item in content_data:
            content_type = item.get("type")
            if content_type == "text":
                result.append(TextContent(text=item["text"]))
            # Additional content types can be added here as needed

        return result
