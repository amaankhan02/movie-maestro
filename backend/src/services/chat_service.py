import uuid
from typing import List, Optional, Tuple

from langchain.memory import ConversationBufferMemory
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from ..config import settings
from ..models import Citation, Conversation, ImageData, Message
from .tmdb_service import TMDbService


class ChatService:
    def __init__(self):
        self.llm = ChatOpenAI(
            model_name=settings.MODEL_NAME,
            temperature=settings.MODEL_TEMPERATURE,
            openai_api_key=settings.OPENAI_API_KEY,
        )
        self.conversations: dict[str, Conversation] = {}

        # Initialize TMDb service
        self.tmdb_service = TMDbService(api_key=settings.TMDB_API_KEY, llm=self.llm)

    def _create_system_prompt(self) -> str:
        """Create the system prompt for the LLM."""
        return """You are an expert on Movies and a helpful AI assistant assisting in movie-related queries. 
        Provide accurate and helpful responses. If you don't know something, say so. 
        Be concise but informative. When citing information from sources like TMDb, use 
        attribution indicators like [TMDb] at the end of the sentence."""

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
            - list of citations
            - list of images
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

        try:
            # First, try to process as a movie query using TMDb service
            tmdb_response, citations, images = (
                await self.tmdb_service.process_movie_query(message)
            )

            if tmdb_response:
                # If we got a response from TMDb, use it
                response_text = tmdb_response
            else:
                # Otherwise, fall back to regular LLM response
                # Format messages for LLM
                messages = self._format_messages(self.conversations[conversation_id])

                # Get response from LLM
                response = await self.llm.agenerate([messages])
                response_text = response.generations[0][0].text
                citations = None
                images = None

            # Add assistant message to conversation
            assistant_message = Message(
                role="assistant",
                content=response_text,
                citations=citations,
                images=images,
            )
            self.conversations[conversation_id].messages.append(assistant_message)

            # Return response with citations and images if available
            return response_text, conversation_id, citations, images

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
