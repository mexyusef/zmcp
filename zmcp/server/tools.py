"""
ZMCP Server Tools

Built-in tools for MCP server.
"""
import os
import sys
import json
import math
import time
import socket
import platform
import subprocess
from typing import Dict, Any, List, Optional, Callable
import logging

from zmcp.core.mcp import Tool

logger = logging.getLogger(__name__)


class ToolHandler:
    """Handler for a tool."""

    def __init__(self, name: str, description: str, handler: Callable, input_schema: Dict[str, Any] = None):
        """Initialize tool handler."""
        self.name = name
        self.description = description
        self.handler = handler
        self.input_schema = input_schema or {}

    def to_tool(self) -> Tool:
        """Convert to Tool object."""
        return Tool(
            name=self.name,
            description=self.description,
            input_schema=self.input_schema
        )


# Web fetch tool
async def web_fetch_handler(url: str) -> Dict[str, Any]:
    """Fetch a URL."""
    import aiohttp

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                content_type = response.headers.get("Content-Type", "")
                if "text/html" in content_type or "application/json" in content_type or "text/plain" in content_type:
                    text = await response.text()
                    return {"content": text, "status": response.status}
                else:
                    return {"error": f"Unsupported content type: {content_type}", "status": response.status}
    except Exception as e:
        return {"error": str(e)}

WEB_FETCH = ToolHandler(
    name="web_fetch",
    description="Fetch content from a URL",
    handler=web_fetch_handler,
    input_schema={
        "type": "object",
        "required": ["url"],
        "properties": {
            "url": {
                "type": "string",
                "description": "URL to fetch"
            }
        }
    }
)


# System info tool
async def system_info_handler() -> Dict[str, Any]:
    """Get system information."""
    return {
        "platform": platform.system() + "-" + platform.release() + "-" + platform.machine(),
        "python_version": platform.python_version() + " (" + platform.python_implementation() + ")",
        "processor": platform.processor(),
        "hostname": socket.gethostname(),
        "time": time.strftime("%Y-%m-%dT%H:%M:%S.%f%z")
    }

SYSTEM_INFO = ToolHandler(
    name="system_info",
    description="Get system information",
    handler=system_info_handler,
    input_schema={
        "type": "object",
        "properties": {}
    }
)


# File manager tool
async def file_manager_handler(action: str, path: str = None, content: str = None) -> Dict[str, Any]:
    """Manage files."""
    try:
        if action == "list":
            if not path:
                path = os.getcwd()
            files = []
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                files.append({
                    "name": item,
                    "type": "directory" if os.path.isdir(item_path) else "file",
                    "size": os.path.getsize(item_path) if os.path.isfile(item_path) else 0
                })
            return {"files": files, "path": path}
        elif action == "read":
            if not path:
                return {"error": "Path is required for read action"}
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return {"content": content, "path": path}
        elif action == "write":
            if not path:
                return {"error": "Path is required for write action"}
            if content is None:
                return {"error": "Content is required for write action"}
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return {"success": True, "path": path}
        else:
            return {"error": f"Unknown action: {action}"}
    except Exception as e:
        return {"error": str(e)}

FILE_MANAGER = ToolHandler(
    name="file_manager",
    description="Manage files (list, read, write)",
    handler=file_manager_handler,
    input_schema={
        "type": "object",
        "required": ["action"],
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list", "read", "write"],
                "description": "Action to perform"
            },
            "path": {
                "type": "string",
                "description": "File or directory path"
            },
            "content": {
                "type": "string",
                "description": "Content to write (for write action)"
            }
        }
    }
)


# Process manager tool
async def process_manager_handler(action: str, command: str = None, pid: int = None) -> Dict[str, Any]:
    """Execute and manages processes."""
    try:
        if action == "execute":
            if not command:
                return {"error": "Command is required for execute action"}
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()
            return {
                "pid": process.pid,
                "returncode": process.returncode,
                "stdout": stdout,
                "stderr": stderr
            }
        elif action == "list":
            import psutil
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'username']):
                processes.append(proc.info)
            return {"processes": processes}
        elif action == "kill":
            if pid is None:
                return {"error": "PID is required for kill action"}
            import psutil
            process = psutil.Process(pid)
            process.terminate()
            return {"success": True, "pid": pid}
        else:
            return {"error": f"Unknown action: {action}"}
    except Exception as e:
        return {"error": str(e)}

PROCESS_MANAGER = ToolHandler(
    name="process_manager",
    description="Executes and manages processes",
    handler=process_manager_handler,
    input_schema={
        "type": "object",
        "required": ["action"],
        "properties": {
            "action": {
                "type": "string",
                "enum": ["execute", "list", "kill"],
                "description": "Action to perform"
            },
            "command": {
                "type": "string",
                "description": "Command to execute (for execute action)"
            },
            "pid": {
                "type": "integer",
                "description": "Process ID (for kill action)"
            }
        }
    }
)


# Memory tool
async def memory_handler(action: str, key: str = None, content: str = None, query: str = None) -> Dict[str, Any]:
    """Stores and retrieves memories."""
    from zmcp.core.memory import memory_store

    try:
        if action == "store":
            if key is None:
                return {"error": "Key is required for store action"}
            if content is None:
                return {"error": "Content is required for store action"}
            memory_store[key] = content
            return {"success": True, "key": key}
        elif action == "retrieve":
            if query is not None:
                # Search for keys containing the query
                results = {}
                for k, v in memory_store.items():
                    if query.lower() in k.lower() or query.lower() in v.lower():
                        results[k] = v
                return {"memories": results}
            elif key is not None:
                # Retrieve specific key
                if key in memory_store:
                    return {"key": key, "content": memory_store[key]}
                else:
                    return {"error": f"Key not found: {key}"}
            else:
                # List all keys
                return {"keys": list(memory_store.keys())}
        else:
            return {"error": f"Unknown action: {action}"}
    except Exception as e:
        return {"error": str(e)}

MEMORY = ToolHandler(
    name="memory",
    description="Stores and retrieves memories",
    handler=memory_handler,
    input_schema={
        "type": "object",
        "required": ["action"],
        "properties": {
            "action": {
                "type": "string",
                "enum": ["store", "retrieve"],
                "description": "Action to perform"
            },
            "key": {
                "type": "string",
                "description": "Memory key"
            },
            "content": {
                "type": "string",
                "description": "Content to store (for store action)"
            },
            "query": {
                "type": "string",
                "description": "Search query (for retrieve action)"
            }
        }
    }
)


# Windows specific tools
async def windows_run_handler(program: str, arguments: str = "") -> Dict[str, Any]:
    """Run a Windows program."""
    if platform.system() != "Windows":
        return {"error": "This tool is only available on Windows"}

    try:
        full_command = f'"{program}" {arguments}'
        process = subprocess.Popen(
            full_command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NEW_CONSOLE if "cmd.exe" in program.lower() else 0
        )

        # For GUI applications, don't wait for output
        if program.lower().endswith(('.exe', '.bat', '.com')) and not program.lower().endswith('cmd.exe'):
            return {
                "pid": process.pid,
                "program": program,
                "arguments": arguments,
                "status": "launched"
            }

        # For console applications, get output
        stdout, stderr = process.communicate()
        return {
            "pid": process.pid,
            "returncode": process.returncode,
            "stdout": stdout,
            "stderr": stderr
        }
    except Exception as e:
        return {"error": str(e)}

WINDOWS_RUN = ToolHandler(
    name="windows_run",
    description="Run a Windows program (cmd.exe, explorer.exe, notepad.exe, etc.)",
    handler=windows_run_handler,
    input_schema={
        "type": "object",
        "required": ["program"],
        "properties": {
            "program": {
                "type": "string",
                "description": "Program to run (e.g., cmd.exe, explorer.exe, notepad.exe)"
            },
            "arguments": {
                "type": "string",
                "description": "Command line arguments"
            }
        }
    }
)


# Calculator tool
async def calculate_handler(expression: str) -> Dict[str, Any]:
    """Calculate a mathematical expression."""
    try:
        # Create a safe environment for eval
        safe_globals = {
            "abs": abs,
            "float": float,
            "int": int,
            "max": max,
            "min": min,
            "pow": pow,
            "round": round,
            "sum": sum,
            "math": math
        }

        # Add math functions
        for name in dir(math):
            if not name.startswith("_"):
                safe_globals[name] = getattr(math, name)

        # Evaluate expression
        result = eval(expression, {"__builtins__": {}}, safe_globals)
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}

CALCULATE = ToolHandler(
    name="calculate",
    description="Calculate a mathematical expression",
    handler=calculate_handler,
    input_schema={
        "type": "object",
        "required": ["expression"],
        "properties": {
            "expression": {
                "type": "string",
                "description": "Mathematical expression to evaluate"
            }
        }
    }
)


# Echo tool
async def echo_handler(message: str) -> Dict[str, Any]:
    """Echo a message."""
    return {"message": message}

ECHO = ToolHandler(
    name="echo",
    description="Echo a message",
    handler=echo_handler,
    input_schema={
        "type": "object",
        "required": ["message"],
        "properties": {
            "message": {
                "type": "string",
                "description": "Message to echo"
            }
        }
    }
)


# List of available tools
AVAILABLE_TOOLS = [
    WEB_FETCH,
    SYSTEM_INFO,
    FILE_MANAGER,
    PROCESS_MANAGER,
    MEMORY,
    WINDOWS_RUN,
    CALCULATE,
    ECHO
]

# Map of tool names to handlers
TOOL_HANDLERS = {tool.name: tool.handler for tool in AVAILABLE_TOOLS}
