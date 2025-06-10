"""
MCP Server

Server implementation for the Model Context Protocol (MCP).
"""
import os
import sys
import json
import logging
import importlib.util
import inspect
import asyncio
import platform
from typing import Dict, List, Any, Callable, Optional, Union
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from zmcp.core.decorators import tool, resource, prompt
from zmcp.core.config import config

logger = logging.getLogger(__name__)


class MCPServer:
    """MCP Server implementation."""

    def __init__(self, server_config: Dict[str, Any]):
        """Initialize MCP server.

        Args:
            server_config: Server configuration
        """
        self.server_config = server_config
        self.app = FastAPI(title="MCP Server",
                          description="Model Context Protocol Server",
                          version="1.0.0")

        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Storage for tools, resources, and prompts
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.resources: Dict[str, Dict[str, Any]] = {}
        self.prompts: Dict[str, Dict[str, Any]] = {}

        # Load built-in tools
        self._load_builtin_tools()

        # Load tools, resources, and prompts from directories
        self._load_from_directories()

        # Set up routes
        self._setup_routes()

    def _load_builtin_tools(self):
        """Load built-in tools."""
        # System info tool
        @tool
        def system_info() -> Dict[str, str]:
            """Get system information.

            Returns:
                Dictionary with system information
            """
            return {
                "system": platform.system(),
                "version": platform.version(),
                "architecture": platform.architecture()[0],
                "processor": platform.processor(),
                "python_version": platform.python_version(),
                "hostname": platform.node()
            }

        # Echo tool
        @tool
        def echo(message: str) -> str:
            """Echo a message back.

            Args:
                message: The message to echo

            Returns:
                The same message
            """
            return message

        # Calculator tool
        @tool
        def calculate(expression: str) -> float:
            """Calculate a mathematical expression.

            Args:
                expression: The expression to calculate (e.g., "2 + 2")

            Returns:
                The result of the calculation
            """
            # Use eval with restricted globals for safety
            allowed_globals = {
                "abs": abs,
                "float": float,
                "int": int,
                "max": max,
                "min": min,
                "pow": pow,
                "round": round,
                "sum": sum
            }

            try:
                return float(eval(expression, {"__builtins__": {}}, allowed_globals))
            except Exception as e:
                raise ValueError(f"Invalid expression: {str(e)}")

        # Register tools
        self._register_tool(system_info)
        self._register_tool(echo)
        self._register_tool(calculate)

        # Add a desktop resource
        @resource
        def desktop() -> List[str]:
            """Get list of files on the desktop.

            Returns:
                List of file names
            """
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            if os.path.exists(desktop_path):
                return os.listdir(desktop_path)
            return []

        # Register resources
        self._register_resource(desktop)

        # Add a simple prompt
        @prompt
        def summarize(text: str) -> str:
            """Summarize the given text.

            Args:
                text: The text to summarize

            Returns:
                Prompt for summarization
            """
            return f"""
            Please summarize the following text in a concise manner:

            {text}
            """

        # Register prompts
        self._register_prompt(summarize)

    def _load_from_directories(self):
        """Load tools, resources, and prompts from directories."""
        # Load tools
        tool_dirs = self.server_config.get("tool_directories", [])
        for tool_dir in tool_dirs:
            self._load_modules_from_directory(tool_dir)

        # Load resources
        resource_dirs = self.server_config.get("resource_directories", [])
        for resource_dir in resource_dirs:
            self._load_modules_from_directory(resource_dir)

        # Load prompts
        prompt_dirs = self.server_config.get("prompt_directories", [])
        for prompt_dir in prompt_dirs:
            self._load_modules_from_directory(prompt_dir)

    def _load_modules_from_directory(self, directory: str):
        """Load Python modules from a directory.

        Args:
            directory: Directory path
        """
        if not os.path.exists(directory):
            logger.warning(f"Directory does not exist: {directory}")
            return

        # Get Python files in directory
        for file_path in Path(directory).glob("**/*.py"):
            try:
                # Load module
                module_name = file_path.stem
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    # Look for decorated functions
                    for name, obj in inspect.getmembers(module):
                        if hasattr(obj, "__mcp_type__"):
                            if obj.__mcp_type__ == "tool":
                                self._register_tool(obj)
                            elif obj.__mcp_type__ == "resource":
                                self._register_resource(obj)
                            elif obj.__mcp_type__ == "prompt":
                                self._register_prompt(obj)

            except Exception as e:
                logger.error(f"Error loading module {file_path}: {str(e)}")

    def _register_tool(self, func: Callable):
        """Register a tool function.

        Args:
            func: Tool function
        """
        if not hasattr(func, "__mcp_type__") or func.__mcp_type__ != "tool":
            logger.warning(f"Function {func.__name__} is not a tool")
            return

        # Get tool metadata
        name = func.__name__
        description = func.__doc__ or ""
        signature = inspect.signature(func)

        # Build parameters schema
        parameters = {}
        for param_name, param in signature.parameters.items():
            param_type = param.annotation
            if param_type is inspect.Parameter.empty:
                param_type = str

            # Convert type to JSON schema type
            type_name = "string"
            if param_type in (int, float):
                type_name = "number"
            elif param_type is bool:
                type_name = "boolean"
            elif param_type in (list, List):
                type_name = "array"
            elif param_type in (dict, Dict):
                type_name = "object"

            parameters[param_name] = {
                "type": type_name,
                "description": ""
            }

        # Register tool
        self.tools[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "function": func
        }

        logger.info(f"Registered tool: {name}")

    def _register_resource(self, func: Callable):
        """Register a resource function.

        Args:
            func: Resource function
        """
        if not hasattr(func, "__mcp_type__") or func.__mcp_type__ != "resource":
            logger.warning(f"Function {func.__name__} is not a resource")
            return

        # Get resource metadata
        name = func.__name__
        description = func.__doc__ or ""

        # Register resource
        self.resources[name] = {
            "name": name,
            "description": description,
            "function": func
        }

        logger.info(f"Registered resource: {name}")

    def _register_prompt(self, func: Callable):
        """Register a prompt function.

        Args:
            func: Prompt function
        """
        if not hasattr(func, "__mcp_type__") or func.__mcp_type__ != "prompt":
            logger.warning(f"Function {func.__name__} is not a prompt")
            return

        # Get prompt metadata
        name = func.__name__
        description = func.__doc__ or ""
        signature = inspect.signature(func)

        # Get template parameter
        template_param = None
        for param_name, param in signature.parameters.items():
            template_param = param_name
            break

        # Register prompt
        self.prompts[name] = {
            "name": name,
            "description": description,
            "template_param": template_param,
            "function": func
        }

        logger.info(f"Registered prompt: {name}")

    def _setup_routes(self):
        """Set up FastAPI routes."""

        @self.app.get("/")
        async def root():
            """Root endpoint."""
            return {"message": "MCP Server"}

        @self.app.get("/capabilities")
        async def get_capabilities():
            """Get server capabilities."""
            # Convert tools to serializable format
            tools_list = []
            for name, tool_data in self.tools.items():
                tools_list.append({
                    "name": tool_data["name"],
                    "description": tool_data["description"],
                    "parameters": tool_data["parameters"]
                })

            # Convert resources to serializable format
            resources_list = []
            for name, resource_data in self.resources.items():
                resources_list.append({
                    "name": resource_data["name"],
                    "description": resource_data["description"]
                })

            # Convert prompts to serializable format
            prompts_list = []
            for name, prompt_data in self.prompts.items():
                prompts_list.append({
                    "name": prompt_data["name"],
                    "description": prompt_data["description"]
                })

            return {
                "tools": tools_list,
                "resources": resources_list,
                "prompts": prompts_list
            }

        @self.app.post("/tools/{tool_name}")
        async def execute_tool(tool_name: str, request: Request):
            """Execute a tool.

            Args:
                tool_name: Tool name
                request: Request object

            Returns:
                Tool execution result
            """
            # Check if tool exists
            if tool_name not in self.tools:
                raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")

            # Get tool data
            tool_data = self.tools[tool_name]
            tool_func = tool_data["function"]

            try:
                # Parse parameters from request body
                params = await request.json()

                # Execute tool
                result = tool_func(**params)

                return result

            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON")
            except TypeError as e:
                raise HTTPException(status_code=400, detail=f"Invalid parameters: {str(e)}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Tool execution error: {str(e)}")

        @self.app.get("/resources/{resource_name}")
        async def get_resource(resource_name: str):
            """Get a resource.

            Args:
                resource_name: Resource name

            Returns:
                Resource data
            """
            # Check if resource exists
            if resource_name not in self.resources:
                raise HTTPException(status_code=404, detail=f"Resource not found: {resource_name}")

            # Get resource data
            resource_data = self.resources[resource_name]
            resource_func = resource_data["function"]

            try:
                # Execute resource function
                result = resource_func()

                return result

            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Resource error: {str(e)}")

        @self.app.post("/prompts/{prompt_name}")
        async def execute_prompt(prompt_name: str, request: Request):
            """Execute a prompt.

            Args:
                prompt_name: Prompt name
                request: Request object

            Returns:
                Generated prompt
            """
            # Check if prompt exists
            if prompt_name not in self.prompts:
                raise HTTPException(status_code=404, detail=f"Prompt not found: {prompt_name}")

            # Get prompt data
            prompt_data = self.prompts[prompt_name]
            prompt_func = prompt_data["function"]
            template_param = prompt_data["template_param"]

            try:
                # Get template from request body
                body = await request.body()
                template = body.decode("utf-8")

                # Execute prompt function
                if template_param:
                    result = prompt_func(**{template_param: template})
                else:
                    result = prompt_func()

                return result

            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Prompt error: {str(e)}")

    def start(self):
        """Start the server."""
        import uvicorn

        host = self.server_config.get("host", "localhost")
        port = self.server_config.get("port", 8000)

        logger.info(f"Starting MCP server on {host}:{port}")

        uvicorn.run(self.app, host=host, port=port)

    def stop(self):
        """Stop the server."""
        logger.info("Stopping MCP server")
        # Server will be stopped when the process ends
