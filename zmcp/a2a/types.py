"""
A2A Types

Core data models for the A2A protocol.
"""
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Literal
from pydantic import BaseModel, Field, RootModel


class Role(str, Enum):
    """Message sender's role."""
    agent = 'agent'
    user = 'user'


class PartBase(BaseModel):
    """Base properties common to all message parts."""
    metadata: Dict[str, Any] = None


class TextPart(PartBase):
    """Represents a text segment within parts."""
    kind: Literal["text"] = "text"
    text: str


class FileBase(BaseModel):
    """Represents the base entity for FileParts."""
    mimeType: Optional[str] = None
    name: Optional[str] = None


class FileWithBytes(FileBase):
    """Define the variant where 'bytes' is present and 'uri' is absent."""
    bytes: str  # base64 encoded content


class FileWithUri(FileBase):
    """Define the variant where 'uri' is present and 'bytes' is absent."""
    uri: str


class FilePart(PartBase):
    """Represents a File segment within parts."""
    kind: Literal["file"] = "file"
    file: Union[FileWithBytes, FileWithUri]


class DataPart(PartBase):
    """Represents a structured data segment within a message part."""
    kind: Literal["data"] = "data"
    data: Dict[str, Any]


class Part(RootModel):
    """Union type for all part types."""
    root: Union[TextPart, FilePart, DataPart]


class TaskState(str, Enum):
    """Represents the possible states of a Task."""
    submitted = 'submitted'
    working = 'working'
    input_required = 'input-required'
    completed = 'completed'
    canceled = 'canceled'
    failed = 'failed'
    rejected = 'rejected'
    auth_required = 'auth-required'
    unknown = 'unknown'


class TaskStatus(BaseModel):
    """TaskState and accompanying message."""
    state: TaskState
    timestamp: Optional[str] = None
    message: Optional["Message"] = None


class Message(BaseModel):
    """Represents a single message exchanged between user and agent."""
    kind: Literal["message"] = "message"
    messageId: str
    role: Role
    parts: List[Part]
    taskId: Optional[str] = None
    contextId: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    extensions: Optional[List[str]] = None
    referenceTaskIds: Optional[List[str]] = None


class Artifact(BaseModel):
    """Represents an artifact generated for a task."""
    artifactId: str
    parts: List[Part]
    name: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    extensions: Optional[List[str]] = None


class Task(BaseModel):
    """Represents a task in the A2A protocol."""
    kind: Literal["task"] = "task"
    id: str
    contextId: str
    status: TaskStatus
    history: Optional[List[Message]] = None
    artifacts: Optional[List[Artifact]] = None
    metadata: Optional[Dict[str, Any]] = None


class AgentSkill(BaseModel):
    """Represents a unit of capability that an agent can perform."""
    id: str
    name: str
    description: str
    tags: List[str]
    examples: Optional[List[str]] = None
    inputModes: Optional[List[str]] = None
    outputModes: Optional[List[str]] = None


class AgentProvider(BaseModel):
    """Represents the service provider of an agent."""
    organization: str
    url: str


class AgentCapabilities(BaseModel):
    """Defines optional capabilities supported by an agent."""
    streaming: Optional[bool] = None
    pushNotifications: Optional[bool] = None
    stateTransitionHistory: Optional[bool] = None
    extensions: Optional[List["AgentExtension"]] = None


class AgentExtension(BaseModel):
    """A declaration of an extension supported by an Agent."""
    uri: str
    description: Optional[str] = None
    required: Optional[bool] = None
    params: Optional[Dict[str, Any]] = None


class SecuritySchemeBase(BaseModel):
    """Base properties shared by all security schemes."""
    description: Optional[str] = None


class APIKeySecurityScheme(SecuritySchemeBase):
    """API Key security scheme."""
    type: Literal["apiKey"] = "apiKey"
    in_: Literal["query", "header", "cookie"] = Field(..., alias='in')
    name: str


class HTTPAuthSecurityScheme(SecuritySchemeBase):
    """HTTP Authentication security scheme."""
    type: Literal["http"] = "http"
    scheme: str
    bearerFormat: Optional[str] = None


class SecurityScheme(RootModel):
    """Union of all security scheme types."""
    root: Union[APIKeySecurityScheme, HTTPAuthSecurityScheme]


class AgentCard(BaseModel):
    """
    An AgentCard conveys key information about an agent:
    - Overall details (version, name, description, uses)
    - Skills: A set of capabilities the agent can perform
    - Default modalities/content types supported by the agent
    - Authentication requirements
    """
    name: str
    description: str
    url: str
    version: str
    defaultInputModes: List[str]
    defaultOutputModes: List[str]
    skills: List[AgentSkill]
    capabilities: AgentCapabilities
    provider: Optional[AgentProvider] = None
    iconUrl: Optional[str] = None
    documentationUrl: Optional[str] = None
    security: Optional[List[Dict[str, List[str]]]] = None
    securitySchemes: Optional[Dict[str, SecurityScheme]] = None
    supportsAuthenticatedExtendedCard: Optional[bool] = None


# JSON-RPC 2.0 related types
class JSONRPCMessage(BaseModel):
    """Base interface for any JSON-RPC 2.0 request or response."""
    jsonrpc: Literal["2.0"] = "2.0"
    id: Optional[Union[str, int]] = None


class JSONRPCRequest(JSONRPCMessage):
    """Represents a JSON-RPC 2.0 Request object."""
    method: str
    params: Optional[Dict[str, Any]] = None


class JSONRPCError(BaseModel):
    """Represents a JSON-RPC 2.0 Error object."""
    code: int
    message: str
    data: Optional[Any] = None


class JSONRPCErrorResponse(JSONRPCMessage):
    """Represents a JSON-RPC 2.0 Error Response object."""
    error: JSONRPCError


class JSONRPCSuccessResponse(JSONRPCMessage):
    """Represents a JSON-RPC 2.0 Success Response object."""
    result: Any


class MessageSendParams(BaseModel):
    """Parameters for sending a message."""
    message: Message
    metadata: Optional[Dict[str, Any]] = None
    configuration: Optional[Dict[str, Any]] = None


class SendMessageRequest(JSONRPCRequest):
    """JSON-RPC request model for the 'message/send' method."""
    method: Literal["message/send"] = "message/send"
    params: MessageSendParams


class SendMessageSuccessResponse(JSONRPCSuccessResponse):
    """JSON-RPC success response model for the 'message/send' method."""
    result: Union[Task, Message]


class SendMessageResponse(RootModel):
    """Response to a send message request."""
    root: Union[JSONRPCErrorResponse, SendMessageSuccessResponse]


# Add TaskIdParams for task operations
class TaskIdParams(BaseModel):
    """Parameters containing only a task ID."""
    id: str
    metadata: Optional[Dict[str, Any]] = None


class GetTaskRequest(JSONRPCRequest):
    """JSON-RPC request model for the 'tasks/get' method."""
    method: Literal["tasks/get"] = "tasks/get"
    params: TaskIdParams


class GetTaskSuccessResponse(JSONRPCSuccessResponse):
    """JSON-RPC success response for the 'tasks/get' method."""
    result: Task


class GetTaskResponse(RootModel):
    """Response to a get task request."""
    root: Union[JSONRPCErrorResponse, GetTaskSuccessResponse]


# Additional types from a2a-python and adk-python libraries

class TaskQueryParams(BaseModel):
    """Parameters for querying a task, including optional history length."""
    id: str
    historyLength: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class CancelTaskRequest(JSONRPCRequest):
    """JSON-RPC request model for the 'tasks/cancel' method."""
    method: Literal["tasks/cancel"] = "tasks/cancel"
    params: TaskIdParams


class CancelTaskSuccessResponse(JSONRPCSuccessResponse):
    """JSON-RPC success response model for the 'tasks/cancel' method."""
    result: Task


class CancelTaskResponse(RootModel):
    """Response to a cancel task request."""
    root: Union[JSONRPCErrorResponse, CancelTaskSuccessResponse]


class PushNotificationAuthenticationInfo(BaseModel):
    """Defines authentication details for push notifications."""
    schemes: List[str]
    credentials: Optional[str] = None


class PushNotificationConfig(BaseModel):
    """Configuration for setting up push notifications for task updates."""
    url: str
    id: Optional[str] = None
    token: Optional[str] = None
    authentication: Optional[PushNotificationAuthenticationInfo] = None


class TaskPushNotificationConfig(BaseModel):
    """Parameters for setting or getting push notification configuration for a task."""
    taskId: str
    pushNotificationConfig: PushNotificationConfig


class SetTaskPushNotificationConfigRequest(JSONRPCRequest):
    """JSON-RPC request model for the 'tasks/pushNotificationConfig/set' method."""
    method: Literal["tasks/pushNotificationConfig/set"] = "tasks/pushNotificationConfig/set"
    params: TaskPushNotificationConfig


class SetTaskPushNotificationConfigSuccessResponse(JSONRPCSuccessResponse):
    """JSON-RPC success response model for the 'tasks/pushNotificationConfig/set' method."""
    result: TaskPushNotificationConfig


class SetTaskPushNotificationConfigResponse(RootModel):
    """Response to a set task push notification config request."""
    root: Union[JSONRPCErrorResponse, SetTaskPushNotificationConfigSuccessResponse]


class GetTaskPushNotificationConfigRequest(JSONRPCRequest):
    """JSON-RPC request model for the 'tasks/pushNotificationConfig/get' method."""
    method: Literal["tasks/pushNotificationConfig/get"] = "tasks/pushNotificationConfig/get"
    params: TaskIdParams


class GetTaskPushNotificationConfigSuccessResponse(JSONRPCSuccessResponse):
    """JSON-RPC success response model for the 'tasks/pushNotificationConfig/get' method."""
    result: TaskPushNotificationConfig


class GetTaskPushNotificationConfigResponse(RootModel):
    """Response to a get task push notification config request."""
    root: Union[JSONRPCErrorResponse, GetTaskPushNotificationConfigSuccessResponse]


class TaskResubscriptionRequest(JSONRPCRequest):
    """JSON-RPC request model for the 'tasks/resubscribe' method."""
    method: Literal["tasks/resubscribe"] = "tasks/resubscribe"
    params: TaskIdParams


class StreamingMode(str, Enum):
    """Streaming mode options."""
    NONE = 'none'
    SSE = 'sse'
    BIDI = 'bidi'


class MessageSendConfiguration(BaseModel):
    """Configuration for the send message request."""
    acceptedOutputModes: List[str]
    blocking: Optional[bool] = None
    historyLength: Optional[int] = None
    pushNotificationConfig: Optional[PushNotificationConfig] = None


class SendStreamingMessageRequest(JSONRPCRequest):
    """JSON-RPC request model for the 'message/stream' method."""
    method: Literal["message/stream"] = "message/stream"
    params: MessageSendParams


class TaskStatusUpdateEvent(BaseModel):
    """Sent by server during sendStream or subscribe requests."""
    kind: Literal["status-update"] = "status-update"
    taskId: str
    contextId: str
    status: TaskStatus
    final: bool
    metadata: Optional[Dict[str, Any]] = None


class TaskArtifactUpdateEvent(BaseModel):
    """Sent by server during sendStream or subscribe requests."""
    kind: Literal["artifact-update"] = "artifact-update"
    taskId: str
    contextId: str
    artifact: Artifact
    append: Optional[bool] = None
    lastChunk: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class SendStreamingMessageSuccessResponse(JSONRPCSuccessResponse):
    """JSON-RPC success response model for the 'message/stream' method."""
    result: Union[Task, Message, TaskStatusUpdateEvent, TaskArtifactUpdateEvent]


class SendStreamingMessageResponse(RootModel):
    """Response to a send streaming message request."""
    root: Union[JSONRPCErrorResponse, SendStreamingMessageSuccessResponse]


# Error types
class TaskNotFoundError(BaseModel):
    """A2A specific error indicating the requested task ID was not found."""
    code: Literal[-32001] = -32001
    message: str = "Task not found"
    data: Optional[Any] = None


class TaskNotCancelableError(BaseModel):
    """A2A specific error indicating the task is in a state where it cannot be canceled."""
    code: Literal[-32002] = -32002
    message: str = "Task cannot be canceled"
    data: Optional[Any] = None


class PushNotificationNotSupportedError(BaseModel):
    """A2A specific error indicating the agent does not support push notifications."""
    code: Literal[-32003] = -32003
    message: str = "Push Notification is not supported"
    data: Optional[Any] = None


class UnsupportedOperationError(BaseModel):
    """A2A specific error indicating the requested operation is not supported by the agent."""
    code: Literal[-32004] = -32004
    message: str = "This operation is not supported"
    data: Optional[Any] = None


class ContentTypeNotSupportedError(BaseModel):
    """A2A specific error indicating incompatible content types between request and agent capabilities."""
    code: Literal[-32005] = -32005
    message: str = "Incompatible content types"
    data: Optional[Any] = None


class InvalidAgentResponseError(BaseModel):
    """A2A specific error indicating agent returned invalid response for the current method."""
    code: Literal[-32006] = -32006
    message: str = "Invalid agent response"
    data: Optional[Any] = None
