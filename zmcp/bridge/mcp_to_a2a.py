"""
MCP to A2A Bridge

Convert MCP tools to A2A agents.
"""
import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Union

import httpx
from fastapi import FastAPI

from zmcp.core.mcp import Tool as MCPTool, Content, TextContent
from zmcp.a2a.types import (
    AgentCard,
    AgentSkill,
    Message,
    Task,
    TaskState,
    Role,
    TextPart,
)
from zmcp.a2a.server.agent_executor import AgentExecutor, EventQueue, RequestContext
from zmcp.a2a.server.app import create_a2a_app

logger = logging.getLogger(__name__)


class MCPToolExecutor(AgentExecutor):
    """Agent executor that delegates to an MCP tool."""

    def __init__(self, tool: MCPTool):
        """Initialize the executor with an MCP tool.

        Args:
            tool: The MCP tool to delegate to
        """
        self.tool = tool

    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """Execute the agent's logic by calling the MCP tool.

        Args:
            context: The request context
            event_queue: The queue to publish events to
        """
        try:
            # Create initial task
            task = self.create_task_from_context(
                context,
                state=TaskState.working,
                message="Processing request...",
            )
            await event_queue.publish(task)

            # Extract text from message parts
            text_parts = []
            for part in context.message.parts:
                # Check if it's a TextPart
                if hasattr(part, "kind") and part.kind == "text":
                    text_parts.append(part.text)

            # Join text parts
            text = " ".join(text_parts)

            # Parse as JSON if it looks like JSON
            arguments = {}
            if text.strip().startswith("{") and text.strip().endswith("}"):
                try:
                    arguments = json.loads(text)
                except json.JSONDecodeError:
                    # Not valid JSON, use as-is
                    arguments = {"text": text}
            else:
                arguments = {"text": text}

            # Call the MCP tool
            result = await self.tool.handler(**arguments)

            # Convert result to message
            if isinstance(result, list):
                # It's a list of Content objects
                response_text = ""
                for content in result:
                    if isinstance(content, TextContent):
                        response_text += content.text + "\n"
            elif isinstance(result, str):
                response_text = result
            else:
                response_text = str(result)

            # Create response message
            response = self.create_response_message(context, response_text)

            # Update task
            task.status.state = TaskState.completed
            task.status.message = response

            # Publish the updated task
            await event_queue.publish(task)

        except Exception as e:
            logger.exception(f"Error executing MCP tool: {e}")

            # Create error message
            error_message = self.create_response_message(
                context,
                f"Error executing tool: {str(e)}",
            )

            # Update task with error
            task = self.create_task_from_context(
                context,
                state=TaskState.failed,
                message=f"Error executing tool: {str(e)}",
            )

            # Publish the error
            await event_queue.publish(task)

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """Cancel the task.

        Args:
            context: The request context
            event_queue: The queue to publish events to
        """
        # Create cancellation message
        task = self.create_task_from_context(
            context,
            state=TaskState.canceled,
            message="Task canceled by user.",
        )

        # Publish the cancellation
        await event_queue.publish(task)


class MCPToolToA2AAgent:
    """Converts an MCP tool to an A2A agent."""

    def __init__(self, tool: MCPTool):
        """Initialize with an MCP tool.

        Args:
            tool: The MCP tool to convert
        """
        self.tool = tool
        self.executor = MCPToolExecutor(tool)

    def create_agent_card(self) -> AgentCard:
        """Create an A2A agent card from the MCP tool.

        Returns:
            An AgentCard object
        """
        # Create a skill from the tool
        skill = AgentSkill(
            id=self.tool.name,
            name=self.tool.name,
            description=self.tool.description,
            tags=["mcp-tool"],
            examples=[],
        )

        # Create the agent card
        return AgentCard(
            name=self.tool.name,
            description=self.tool.description,
            url=f"/a2a/tools/{self.tool.name}",
            version="1.0.0",
            defaultInputModes=["text/plain"],
            defaultOutputModes=["text/plain"],
            skills=[skill],
            capabilities={
                "streaming": True,
                "pushNotifications": False,
                "stateTransitionHistory": True,
            },
        )

    def create_app(self) -> FastAPI:
        """Create a FastAPI application for the A2A agent.

        Returns:
            A FastAPI application
        """
        return create_a2a_app(
            agent_executor=self.executor,
            agent_name=self.tool.name,
            agent_description=self.tool.description,
        )
