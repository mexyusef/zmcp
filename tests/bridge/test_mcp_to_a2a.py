"""
Tests for the MCP to A2A bridge.
"""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from zmcp.core.mcp import Tool as MCPTool
from zmcp.a2a.types import AgentCard, AgentSkill
from zmcp.bridge.mcp_to_a2a import MCPToolToA2AAgent, MCPToolExecutor


@pytest.fixture
def mcp_tool():
    """Create a mock MCP tool."""
    async def handler(**kwargs):
        return [{"type": "text", "text": f"Tool response: {kwargs.get('input', '')}"}]

    return MCPTool(
        name="test_tool",
        description="A test tool",
        handler=handler,
        input_schema={
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "Input for the tool"
                }
            }
        }
    )


@pytest.fixture
def mcp_to_a2a_bridge(mcp_tool):
    """Create a bridge from MCP tool to A2A agent."""
    return MCPToolToA2AAgent(mcp_tool)


@pytest.mark.asyncio
async def test_mcp_tool_executor():
    """Test the MCP tool executor."""
    # Create a mock tool
    mock_tool = MagicMock()
    mock_tool.handler = AsyncMock(return_value=[{"type": "text", "text": "Tool response"}])
    mock_tool.name = "test_tool"

    # Create executor
    executor = MCPToolExecutor(mock_tool)

    # Execute task
    task_id = "task123"
    input_data = {"input": "test input"}
    result = await executor.execute(task_id, input_data)

    # Check result
    assert result.status.state == "completed"
    assert result.status.message.parts[0].text == "Tool response"

    # Check that tool handler was called with correct args
    mock_tool.handler.assert_called_once_with(**input_data)


@pytest.mark.asyncio
async def test_create_agent_card():
    """Test creating an agent card from an MCP tool."""
    # Create a mock tool
    mock_tool = MagicMock()
    mock_tool.name = "test_tool"
    mock_tool.description = "A test tool"

    # Create bridge
    bridge = MCPToolToA2AAgent(mock_tool)

    # Get agent card
    agent_card = bridge.create_agent_card()

    # Check agent card
    assert agent_card.id == "test_tool"
    assert agent_card.name == "test_tool"
    assert agent_card.description == "A test tool"
    assert len(agent_card.skills) == 1
    assert agent_card.skills[0].id == "execute"
    assert agent_card.skills[0].name == "execute"


def test_create_app():
    """Test creating a FastAPI app from an MCP tool."""
    # Create a mock tool
    mock_tool = MagicMock()
    mock_tool.name = "test_tool"
    mock_tool.description = "A test tool"

    # Create bridge
    bridge = MCPToolToA2AAgent(mock_tool)

    # Create app
    app = bridge.create_app()

    # Check app
    assert isinstance(app, FastAPI)

    # Test the app with a test client
    client = TestClient(app)

    # Test GET /agent
    response = client.get("/agent")
    assert response.status_code == 200
    agent_card = response.json()
    assert agent_card["id"] == "test_tool"

    # Test POST /message/send
    with patch.object(MCPToolExecutor, "execute", new_callable=AsyncMock) as mock_execute:
        # Set up mock response
        mock_status = MagicMock()
        mock_status.state = "completed"
        mock_status.message.parts = [MagicMock(kind="text", text="Tool response")]

        mock_task = MagicMock()
        mock_task.id = "task123"
        mock_task.status = mock_status

        mock_execute.return_value = mock_task

        # Send message
        message = {
            "kind": "message",
            "messageId": "msg123",
            "role": "user",
            "parts": [{"kind": "text", "text": "test input"}]
        }

        response = client.post(
            "/message/send",
            json={"method": "message/send", "params": {"message": message}}
        )

        # Check response
        assert response.status_code == 200
        result = response.json()
        assert "result" in result
        assert result["result"]["parts"][0]["text"] == "Tool response"
