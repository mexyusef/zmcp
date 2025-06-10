"""
ZMCP HTTP Server

HTTP Server implementation for ZMCP.
"""
import asyncio
import json
import logging
from typing import Dict, List, Optional, Any

from aiohttp import web
from aiohttp.web import Request, Response, json_response

from zmcp.core.mcp import Content, TextContent
from zmcp.server.base import MCPServer
from zmcp.server.tools import AVAILABLE_TOOLS, TOOL_HANDLERS

logger = logging.getLogger(__name__)


class MCPHTTPServer:
    """HTTP server for MCP."""

    def __init__(self, server: MCPServer, host: str = "localhost", port: int = 8000):
        """
        Initialize HTTP server.

        Args:
            server: MCP server instance
            host: Host to bind to
            port: Port to bind to
        """
        self.server = server
        self.host = host
        self.port = port
        self.app = web.Application()
        self._setup_routes()
        self._initialize_tools()

    def _setup_routes(self):
        """Set up HTTP routes."""
        self.app.add_routes([
            web.get("/", self.handle_root),
            web.get("/list-tools", self.handle_list_tools),
            web.get("/list-resources", self.handle_list_resources),
            web.get("/list-prompts", self.handle_list_prompts),
            web.post("/tool/{tool_name}", self.handle_tool_request),
            web.get("/resource/{uri:.*}", self.handle_resource_request),
            web.post("/prompt/{prompt_name}", self.handle_prompt_request),
        ])

    def _initialize_tools(self):
        """Initialize predefined tools."""
        for tool in AVAILABLE_TOOLS:
            self.server.add_tool(tool)

    async def start(self):
        """Start HTTP server."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        logger.info(f"MCP HTTP server running at http://{self.host}:{self.port}")

    async def handle_root(self, request: Request) -> Response:
        """Handle root endpoint request."""
        return json_response({
            "name": self.server.name,
            "description": self.server.description,
            "endpoints": {
                "list-tools": "/list-tools",
                "list-resources": "/list-resources",
                "list-prompts": "/list-prompts",
                "tool": "/tool/{tool_name}",
                "resource": "/resource/{uri}",
                "prompt": "/prompt/{prompt_name}"
            }
        })

    async def handle_list_tools(self, request: Request) -> Response:
        """Handle list tools request."""
        tools = self.server.get_tools_list()
        return json_response(tools)

    async def handle_list_resources(self, request: Request) -> Response:
        """Handle list resources request."""
        resources = self.server.get_resources_list()
        return json_response(resources)

    async def handle_list_prompts(self, request: Request) -> Response:
        """Handle list prompts request."""
        prompts = self.server.get_prompts_list()
        return json_response(prompts)

    async def handle_tool_request(self, request: Request) -> Response:
        """Handle tool request."""
        tool_name = request.match_info["tool_name"]

        try:
            body = await request.json()
        except json.JSONDecodeError:
            return json_response({"error": "Invalid JSON"}, status=400)

        try:
            # Use custom handler if available, otherwise use server's handler
            if tool_name in TOOL_HANDLERS:
                handler = TOOL_HANDLERS[tool_name]
                result = handler(**body)
                if asyncio.iscoroutine(result):
                    result = await result
            else:
                result = await self.server.handle_tool_request(tool_name, body)

            return json_response([c.to_dict() for c in result])
        except ValueError as e:
            return json_response({"error": str(e)}, status=400)
        except Exception as e:
            logger.error(f"Error handling tool request: {e}")
            return json_response({"error": "Internal server error"}, status=500)

    async def handle_resource_request(self, request: Request) -> Response:
        """Handle resource request."""
        uri = request.match_info["uri"]

        try:
            result = await self.server.handle_resource_request(uri)
            return json_response([c.to_dict() for c in result])
        except ValueError as e:
            return json_response({"error": str(e)}, status=400)
        except Exception as e:
            logger.error(f"Error handling resource request: {e}")
            return json_response({"error": "Internal server error"}, status=500)

    async def handle_prompt_request(self, request: Request) -> Response:
        """Handle prompt request."""
        prompt_name = request.match_info["prompt_name"]

        try:
            body = await request.json()
        except json.JSONDecodeError:
            return json_response({"error": "Invalid JSON"}, status=400)

        if "text" not in body:
            return json_response({"error": "Missing required field 'text'"}, status=400)

        try:
            result = await self.server.handle_prompt_request(prompt_name, body["text"])
            return json_response([c.to_dict() for c in result])
        except ValueError as e:
            return json_response({"error": str(e)}, status=400)
        except Exception as e:
            logger.error(f"Error handling prompt request: {e}")
            return json_response({"error": "Internal server error"}, status=500)


async def start_http_server(server: MCPServer, host: str = "localhost", port: int = 8000) -> MCPHTTPServer:
    """
    Start HTTP server for MCP.

    Args:
        server: MCP server instance
        host: Host to bind to
        port: Port to bind to

    Returns:
        HTTP server instance
    """
    http_server = MCPHTTPServer(server, host, port)
    await http_server.start()
    return http_server
