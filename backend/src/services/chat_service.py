import uuid
from typing import List, Optional, Tuple

from langchain.memory import ConversationBufferMemory
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from ..config import settings
from ..models import Citation, Conversation, ImageData, Message


class ChatService:
    def __init__(self):
        self.llm = ChatOpenAI(
            model_name=settings.MODEL_NAME,
            temperature=settings.MODEL_TEMPERATURE,
            openai_api_key=settings.OPENAI_API_KEY,
        )
        self.conversations: dict[str, Conversation] = {}

        # Placeholder for RAG system
        self.vector_store = None  # TODO: To be implemented
        self.retriever = None  # TODO: To be implemented

    def _create_system_prompt(self) -> str:
        """Create the system prompt for the LLM."""
        # TODO: Enhance this with RAG context when implemented
        return """You are an expert on Movies and a helpful AI assistant assisting in movie-related queries. Provide accurate and helpful responses.
        If you don't know something, say so. Be concise but informative."""

    def _format_messages(
        self, conversation: Conversation
    ) -> List[SystemMessage | HumanMessage | AIMessage]:
        """Format conversation messages for the LLM."""
        messages = [SystemMessage(content=self._create_system_prompt())]

        for msg in conversation.messages:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                messages.append(AIMessage(content=msg.content))

        return messages

    async def get_response(
        self, message: str, conversation_id: Optional[str] = None
    ) -> Tuple[str, str, Optional[List[Citation]], Optional[List[ImageData]]]:
        """Get response from the LLM for a given message.

        Returns:
            Tuple containing:
            - response text
            - conversation ID
            - list of citations (None for now)
            - list of images (None for now)
        """
        # Generate new conversation ID if none provided
        if not conversation_id:
            conversation_id = str(uuid.uuid4())

        # Create conversation memory if the conversation ID is not in the dictionary
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = Conversation(
                id=conversation_id, messages=[]
            )

        # Add user message to conversation
        user_message = Message(role="user", content=message)
        self.conversations[conversation_id].messages.append(user_message)

        # Format messages for LLM
        messages = self._format_messages(self.conversations[conversation_id])

        try:
            # Get response from LLM
            response = await self.llm.agenerate([messages])
            response_text = response.generations[0][0].text

            # Add assistant message to conversation
            assistant_message = Message(role="assistant", content=response_text)
            self.conversations[conversation_id].messages.append(assistant_message)

            # Return response with None for citations and images for now
            return response_text, conversation_id, None, None

        except Exception as e:
            # Add error message to conversation
            error_message = Message(
                role="assistant", content=f"Error: {str(e)}", error=True
            )
            self.conversations[conversation_id].messages.append(error_message)
            raise e

    def get_conversation_history(self, conversation_id: str) -> Optional[List[Message]]:
        """Get conversation history for a given conversation ID."""
        if conversation_id in self.conversations:
            return self.conversations[conversation_id].messages
        return None
