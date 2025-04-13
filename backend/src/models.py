from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

### Flow of the models ###
# 1. User sends a message → ChatRequest is created
# 2. Backend processes it using ChatService which maintains Conversation objects
# 3. Each message is stored as a Message object in the conversation
# 4. Response is sent back as a ChatResponse
# 5. Frontend displays the messages using the Message interface


class Citation(BaseModel):
    """
    Represents a citation in a message, containing the source text and URL.

    Attributes:
        text (str): The text content of the citation
        url (str): The URL of the source
        title (Optional[str]): Optional title of the source
    """

    text: str
    url: str
    title: Optional[str] = None


class ImageData(BaseModel):
    """
    Represents an image in a message, containing the image URL and metadata.

    Attributes:
        url (str): The URL of the image
        alt (str): Alternative text for the image
        caption (Optional[str]): Optional caption for the image
    """

    url: str
    alt: str
    caption: Optional[str] = None


class RelatedQuery(BaseModel):
    """
    Represents a related query suggestion that can be shown to the user after a response.

    Attributes:
        text (str): The text of the suggested query
    """

    text: str


class Message(BaseModel):
    """
    Represents a single message in a conversation between a user and the AI assistant.

    This model is used throughout the application for both storing and displaying messages.
    It's used in the frontend for rendering the chat interface and in the backend for
    maintaining conversation history.

    Attributes:
        role (str): The sender of the message, either "user" or "assistant"
        content (str): The actual text content of the message
        timestamp (datetime): When the message was sent, defaults to current time
        error (Optional[bool]): Whether the message represents an error
        citations (Optional[List[Citation]]): Optional list of citations
        images (Optional[List[ImageData]]): Optional list of images
    """

    role: str
    content: str
    timestamp: datetime = datetime.now()
    error: Optional[bool] = None
    citations: Optional[List[Citation]] = None
    images: Optional[List[ImageData]] = None


class ChatRequest(BaseModel):
    """
    Represents the data sent from the frontend to the backend when a user sends a message.

    This model is used as the request body for the /chat endpoint. It allows for both
    new conversations and continuing existing ones through the optional conversation_id.

    Attributes:
        message (str): The text message sent by the user
        conversation_id (Optional[str]): ID of an existing conversation to continue,
                                       or None to start a new conversation
    """

    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    """
    Represents the response sent from the backend to the frontend after processing a message.

    This model is used as the response model for the /chat endpoint. It includes both
    the AI's response and the conversation context.

    Attributes:
        response (str): The AI assistant's response text
        conversation_id (str): The ID of the conversation this response belongs to
        timestamp (datetime): When the response was generated, defaults to current time
        citations (Optional[List[Citation]]): Optional list of citations
        images (Optional[List[ImageData]]): Optional list of images
        related_queries (Optional[List[RelatedQuery]]): Optional list of related query suggestions
    """

    response: str
    conversation_id: str
    timestamp: datetime = datetime.now()
    citations: Optional[List[Citation]] = None
    images: Optional[List[ImageData]] = None
    related_queries: Optional[List[RelatedQuery]] = None


class Conversation(BaseModel):
    """
    Represents a complete chat conversation between a user and the AI assistant.

    This model is used by the ChatService to maintain conversation state and history.
    It stores all messages in a conversation and tracks when the conversation was
    created and last updated.

    Attributes:
        id (str): Unique identifier for the conversation
        messages (List[Message]): List of all messages in the conversation
        created_at (datetime): When the conversation was started, defaults to current time
        updated_at (datetime): When the conversation was last modified, defaults to current time
    """

    id: str
    messages: List[Message]
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
