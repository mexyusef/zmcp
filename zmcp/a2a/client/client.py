"""
A2A Client

Core client implementation for the A2A protocol.
"""
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Union, AsyncGenerator

import httpx
from httpx_sse import aconnect_sse, SSEError

from zmcp.a2a.types import (
    AgentCard,
    SendMessageRequest,
    SendMessageResponse,
    GetTaskRequest,
    GetTaskResponse,
    Task,
    Message,
    JSONRPCErrorResponse,
)

logger = logging.getLogger(__name__)


class A2AClientError(Exception):
    """Base exception for A2A client errors."""
    pass


class A2AClientHTTPError(A2AClientError):
    """HTTP-related errors during A2A client operations."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}: {message}")


class A2AClientJSONError(A2AClientError):
    """JSON parsing or validation errors during A2A client operations."""
    pass


class A2ACardResolver:
    """Agent Card resolver."""

    def __init__(
        self,
        httpx_client: httpx.AsyncClient,
        base_url: str,
        agent_card_path: str = '/.well-known/agent.json',
    ):
        """Initialize the A2ACardResolver.

        Args:
            httpx_client: An async HTTP client instance
            base_url: The base URL of the agent's host
            agent_card_path: The path to the agent card endpoint
        """
        self.base_url = base_url.rstrip('/')
        self.agent_card_path = agent_card_path.lstrip('/')
        self.httpx_client = httpx_client

    async def get_agent_card(
        self,
        relative_card_path: Optional[str] = None,
        http_kwargs: Optional[Dict[str, Any]] = None,
    ) -> AgentCard:
        """Fetch an agent card from a specified path.

        Args:
            relative_card_path: Optional path to the agent card endpoint
            http_kwargs: Optional kwargs for the HTTP request

        Returns:
            An AgentCard object

        Raises:
            A2AClientHTTPError: If an HTTP error occurs
            A2AClientJSONError: If JSON parsing fails
        """
        if relative_card_path is None:
            path_segment = self.agent_card_path
        else:
            path_segment = relative_card_path.lstrip('/')

        target_url = f'{self.base_url}/{path_segment}'

        try:
            response = await self.httpx_client.get(
                target_url,
                **(http_kwargs or {}),
            )
            response.raise_for_status()
            agent_card_data = response.json()
            logger.info(
                'Successfully fetched agent card data from %s',
                target_url,
            )
            agent_card = AgentCard.model_validate(agent_card_data)
            return agent_card
        except httpx.HTTPStatusError as e:
            raise A2AClientHTTPError(
                e.response.status_code,
                f'Failed to fetch agent card from {target_url}: {e}',
            ) from e
        except json.JSONDecodeError as e:
            raise A2AClientJSONError(
                f'Failed to parse JSON for agent card from {target_url}: {e}'
            ) from e
        except httpx.RequestError as e:
            raise A2AClientHTTPError(
                503,
                f'Network error fetching agent card from {target_url}: {e}',
            ) from e
        except Exception as e:
            raise A2AClientJSONError(
                f'Failed to validate agent card structure from {target_url}: {str(e)}'
            ) from e


class A2AClient:
    """A2A Client for interacting with an A2A agent."""

    def __init__(
        self,
        httpx_client: httpx.AsyncClient,
        agent_card: Optional[AgentCard] = None,
        url: Optional[str] = None,
    ):
        """Initialize the A2AClient.

        Args:
            httpx_client: An async HTTP client instance
            agent_card: The agent card object (optional)
            url: The direct URL to the agent's A2A RPC endpoint (optional)

        Raises:
            ValueError: If neither agent_card nor url is provided
        """
        if agent_card:
            self.url = agent_card.url
            self.agent_card = agent_card
        elif url:
            self.url = url
            self.agent_card = None
        else:
            raise ValueError('Must provide either agent_card or url')

        self.httpx_client = httpx_client

    @staticmethod
    async def get_client_from_agent_card_url(
        httpx_client: httpx.AsyncClient,
        base_url: str,
        agent_card_path: str = '/.well-known/agent.json',
        http_kwargs: Optional[Dict[str, Any]] = None,
    ) -> 'A2AClient':
        """Fetch the public AgentCard and initialize an A2A client.

        Args:
            httpx_client: An async HTTP client instance
            base_url: The base URL of the agent's host
            agent_card_path: The path to the agent card endpoint
            http_kwargs: Optional kwargs for the HTTP request

        Returns:
            An initialized A2AClient instance

        Raises:
            A2AClientHTTPError: If an HTTP error occurs
            A2AClientJSONError: If JSON parsing fails
        """
        agent_card = await A2ACardResolver(
            httpx_client, base_url=base_url, agent_card_path=agent_card_path
        ).get_agent_card(http_kwargs=http_kwargs)

        return A2AClient(httpx_client=httpx_client, agent_card=agent_card)

    async def send_message(
        self,
        request: SendMessageRequest,
        http_kwargs: Optional[Dict[str, Any]] = None,
    ) -> SendMessageResponse:
        """Send a message to the agent.

        Args:
            request: The SendMessageRequest object
            http_kwargs: Optional kwargs for the HTTP request

        Returns:
            A SendMessageResponse object

        Raises:
            A2AClientHTTPError: If an HTTP error occurs
            A2AClientJSONError: If JSON parsing fails
        """
        if not request.id:
            request.id = str(uuid.uuid4())

        response_data = await self._send_request(
            request.model_dump(mode="json"),
            http_kwargs=http_kwargs,
        )

        try:
            # Check if it's an error response
            if "error" in response_data:
                error_response = JSONRPCErrorResponse.model_validate(response_data)
                return SendMessageResponse.model_validate({"root": error_response})
            else:
                # It's a success response
                return SendMessageResponse.model_validate({"root": response_data})
        except Exception as e:
            raise A2AClientJSONError(f"Failed to parse response: {e}") from e

    async def send_message_streaming(
        self,
        request: SendMessageRequest,
        http_kwargs: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Union[Task, Message], None]:
        """Send a streaming message request to the agent.

        Args:
            request: The SendMessageRequest object
            http_kwargs: Optional kwargs for the HTTP request

        Yields:
            Task or Message objects from the streaming response

        Raises:
            A2AClientHTTPError: If an HTTP error occurs
            A2AClientJSONError: If JSON parsing fails
        """
        if not request.id:
            request.id = str(uuid.uuid4())

        request_payload = request.model_dump(mode="json")
        request_payload["method"] = "message/stream"  # Change to streaming endpoint

        url = self.url
        headers = {"Content-Type": "application/json"}

        try:
            async with self.httpx_client.stream(
                "POST",
                url,
                json=request_payload,
                headers=headers,
                **(http_kwargs or {})
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    try:
                        data = json.loads(line)

                        # Check for error response
                        if "error" in data:
                            error = JSONRPCErrorResponse.model_validate(data)
                            yield error
                            continue

                        # Process result based on type
                        if "result" in data:
                            result = data["result"]
                            if isinstance(result, dict):
                                if result.get("kind") == "task":
                                    yield Task.model_validate(result)
                                elif result.get("kind") == "message":
                                    yield Message.model_validate(result)
                                else:
                                    # Unknown result type
                                    yield result
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse streaming response: {e}")
                    except Exception as e:
                        logger.warning(f"Error processing streaming response: {e}")

        except httpx.HTTPStatusError as e:
            raise A2AClientHTTPError(
                e.response.status_code,
                f"HTTP error during streaming request: {e}",
            ) from e
        except httpx.RequestError as e:
            raise A2AClientHTTPError(
                503,
                f"Network error during streaming request: {e}",
            ) from e

    async def get_task(
        self,
        request: GetTaskRequest,
        http_kwargs: Optional[Dict[str, Any]] = None,
    ) -> GetTaskResponse:
        """Get a task from the agent.

        Args:
            request: The GetTaskRequest object
            http_kwargs: Optional kwargs for the HTTP request

        Returns:
            A GetTaskResponse object

        Raises:
            A2AClientHTTPError: If an HTTP error occurs
            A2AClientJSONError: If JSON parsing fails
        """
        if not request.id:
            request.id = str(uuid.uuid4())

        response_data = await self._send_request(
            request.model_dump(mode="json"),
            http_kwargs=http_kwargs,
        )

        try:
            # Check if it's an error response
            if "error" in response_data:
                error_response = JSONRPCErrorResponse.model_validate(response_data)
                return GetTaskResponse.model_validate({"root": error_response})
            else:
                # It's a success response
                return GetTaskResponse.model_validate({"root": response_data})
        except Exception as e:
            raise A2AClientJSONError(f"Failed to parse response: {e}") from e

    async def _send_request(
        self,
        rpc_request_payload: Dict[str, Any],
        http_kwargs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send a JSON-RPC request to the agent.

        Args:
            rpc_request_payload: The JSON-RPC request payload
            http_kwargs: Optional kwargs for the HTTP request

        Returns:
            The JSON-RPC response payload

        Raises:
            A2AClientHTTPError: If an HTTP error occurs
            A2AClientJSONError: If JSON parsing fails
        """
        url = self.url
        headers = {"Content-Type": "application/json"}

        try:
            response = await self.httpx_client.post(
                url,
                json=rpc_request_payload,
                headers=headers,
                **(http_kwargs or {}),
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise A2AClientHTTPError(
                e.response.status_code,
                f"HTTP error: {e}",
            ) from e
        except json.JSONDecodeError as e:
            raise A2AClientJSONError(f"Failed to parse response JSON: {e}") from e
        except httpx.RequestError as e:
            raise A2AClientHTTPError(
                503,
                f"Network error: {e}",
            ) from e
