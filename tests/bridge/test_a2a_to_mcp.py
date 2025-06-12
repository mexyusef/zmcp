"""
Tests for the A2A to MCP bridge.
"""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from httpx import Response

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from zmcp.core.mcp import Tool as MCPTool, TextContent
from zmcp.a2a.types import AgentCard, AgentSkill, Message, Role, TextPart
from zmcp.a2a.client.client import A2AClient
from zmcp.bridge.a2a_to_mcp import A2AAgentToMCPTool


@pytest.fixture
def agent_card():
    """Create a mock agent card."""
    return AgentCard(
        id="test_agent",
        name="Test Agent",
        description="A test agent",
        skills=[
            AgentSkill(
                id="skill1",
                name="Skill 1",
                description="A test skill"
            ),
            AgentSkill(
                id="skill2",
                name="Skill 2",
                description="Another test skill"
            )
        ]
    )


@pytest.fixture
def a2a_client():
    """Create a mock A2A client."""
    client = MagicMock()
    client.send_message = AsyncMock()
    return client


@pytest.fixture
def a2a_to_mcp_bridge(agent_card):
    """Create a bridge from A2A agent to MCP tool."""
    with patch("zmcp.bridge.a2a_to_mcp.A2AClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.send_message = AsyncMock()
        mock_client_class.return_value = mock_client

        bridge = A2AAgentToMCPTool(agent_card)
        bridge.client = mock_client
        return bridge


def test_create_tools_from_skills(a2a_to_mcp_bridge, agent_card):
    """Test creating MCP tools from agent skills."""
    # Get tools
    tools = a2a_to_mcp_bridge.get_tools()

    # Check tools
    assert len(tools) == 2
    assert tools[0].name == "skill1"
    assert tools[0].description == "A test skill"
    assert tools[1].name == "skill2"
    assert tools[1].description == "Another test skill"


@pytest.mark.asyncio
async def test_tool_handler_with_text_response(a2a_to_mcp_bridge):
    """Test the tool handler with a text response."""
    # Set up mock response
    mock_response = MagicMock()
    mock_response.root.result.parts = [
        MagicMock(kind="text", text="Agent response")
    ]
    a2a_to_mcp_bridge.client.send_message.return_value = mock_response

    # Get the tool
    tool = a2a_to_mcp_bridge.get_tools()[0]

    # Call the handler
    result = await tool.handler(text="test input")

    # Check result
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert result[0].text == "Agent response"

    # Check that client.send_message was called
    a2a_to_mcp_bridge.client.send_message.assert_called_once()
    call_args = a2a_to_mcp_bridge.client.send_message.call_args[0][0]
    assert call_args.method == "message/send"
    assert call_args.params["message"].parts[0].text == "test input"


@pytest.mark.asyncio
async def test_tool_handler_with_task_response(a2a_to_mcp_bridge):
    """Test the tool handler with a task response."""
    # Set up mock response
    mock_message = MagicMock()
    mock_message.parts = [MagicMock(kind="text", text="Task response")]

    mock_status = MagicMock()
    mock_status.message = mock_message
    mock_status.state = "completed"

    mock_result = MagicMock()
    mock_result.status = mock_status
    mock_result.id = "task123"

    mock_response = MagicMock()
    mock_response.root.result = mock_result

    a2a_to_mcp_bridge.client.send_message.return_value = mock_response

    # Get the tool
    tool = a2a_to_mcp_bridge.get_tools()[0]

    # Call the handler
    result = await tool.handler(text="test input")

    # Check result
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert result[0].text == "Task response"


@pytest.mark.asyncio
async def test_tool_handler_with_error_response(a2a_to_mcp_bridge):
    """Test the tool handler with an error response."""
    # Set up mock response
    mock_response = MagicMock()
    mock_response.root.result = None
    mock_response.root.error = MagicMock(message="Error message")

    a2a_to_mcp_bridge.client.send_message.return_value = mock_response

    # Get the tool
    tool = a2a_to_mcp_bridge.get_tools()[0]

    # Call the handler
    result = await tool.handler(text="test input")

    # Check result
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert result[0].text == "Error: Error message"


@pytest.mark.asyncio
async def test_close(a2a_to_mcp_bridge):
    """Test closing the bridge."""
    # Set up mock httpx client
    a2a_to_mcp_bridge.httpx_client = MagicMock()
    a2a_to_mcp_bridge.httpx_client.aclose = AsyncMock()

    # Close the bridge
    await a2a_to_mcp_bridge.close()

    # Check that httpx client was closed
    a2a_to_mcp_bridge.httpx_client.aclose.assert_called_once()
