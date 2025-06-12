"""
A2A to MCP Bridge

Convert A2A agents to MCP tools.
"""
import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Union, Callable

import httpx

from zmcp.core.mcp import Tool as MCPTool, TextContent
from zmcp.a2a.client.client import A2AClient
from zmcp.a2a.types import (
    AgentCard,
    Message,
    SendMessageRequest,
    Role,
    TextPart,
)

logger = logging.getLogger(__name__)


class A2AAgentToMCPTool:
    """Converts an A2A agent to an MCP tool."""

    def __init__(
        self,
        agent_card: AgentCard,
        httpx_client: Optional[httpx.AsyncClient] = None,
    ):
        """Initialize with an A2A agent card.

        Args:
            agent_card: The agent card
            httpx_client: Optional HTTP client
        """
        self.agent_card = agent_card
        self.httpx_client = httpx_client or httpx.AsyncClient()
        self.client = A2AClient(httpx_client=self.httpx_client, agent_card=agent_card)

        # Create MCP tools from agent skills
        self.tools = []
        for skill in agent_card.skills:
            tool = self._create_tool_from_skill(skill)
            self.tools.append(tool)

    def _create_tool_from_skill(self, skill: "AgentSkill") -> MCPTool:
        """Create an MCP tool from an agent skill.

        Args:
            skill: The agent skill

        Returns:
            An MCP tool
        """
        # Create a handler function that calls the A2A agent
        async def handler(**kwargs) -> List[TextContent]:
            # Convert kwargs to text
            if "text" in kwargs:
                text = kwargs["text"]
            else:
                text = json.dumps(kwargs)

            # Create a message
            message = Message(
                kind="message",
                messageId=str(uuid.uuid4()),
                role=Role.user,
                parts=[TextPart(kind="text", text=text)],
            )

            # Create a request
            request = SendMessageRequest(
                method="message/send",
                params={"message": message},
            )

            # Send the message
            response = await self.client.send_message(request)

            # Extract the response text
            if hasattr(response.root, "result"):
                result = response.root.result
                if hasattr(result, "parts"):
                    # It's a Message
                    parts = result.parts
                    text_parts = []
                    for part in parts:
                        if hasattr(part, "kind") and part.kind == "text":
                            text_parts.append(part.text)
                    response_text = "\n".join(text_parts)
                elif hasattr(result, "status") and hasattr(result.status, "message"):
                    # It's a Task with a message
                    if result.status.message and hasattr(result.status.message, "parts"):
                        parts = result.status.message.parts
                        text_parts = []
                        for part in parts:
                            if hasattr(part, "kind") and part.kind == "text":
                                text_parts.append(part.text)
                        response_text = "\n".join(text_parts)
                    else:
                        response_text = f"Task {result.id} is in state {result.status.state}"
                else:
                    # Unknown result type
                    response_text = str(result)
            else:
                # Error response
                if hasattr(response.root, "error"):
                    response_text = f"Error: {response.root.error.message}"
                else:
                    response_text = "Unknown error"

            # Return as TextContent
            return [TextContent(type="text", text=response_text)]

        # Create input schema
        input_schema = {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": f"Input for the {skill.name} skill",
                }
            }
        }

        # Create the tool
        return MCPTool(
            name=skill.id,
            description=skill.description,
            handler=handler,
            input_schema=input_schema,
        )

    def get_tools(self) -> List[MCPTool]:
        """Get the MCP tools created from the agent skills.

        Returns:
            A list of MCP tools
        """
        return self.tools

    async def close(self) -> None:
        """Close the HTTP client."""
        if self.httpx_client:
            await self.httpx_client.aclose()
