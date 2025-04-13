import uuid
from typing import List, Optional, Tuple

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from ..config import settings
from ..models import Citation, Conversation, ImageData, Message, RelatedQuery
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

    async def _generate_related_queries(
        self, conversation: Conversation
    ) -> List[RelatedQuery]:
        """Generate related queries based on the conversation history.

        The related queries should be relevant follow-up questions that:
        1. Can be answered using TMDb or comparisons based on chat history
        2. Don't repeat questions already asked
        3. May involve streaming platforms, comparisons, or people mentioned in answers

        Returns:
            List[RelatedQuery]: List of 3 related query suggestions
        """
        if len(conversation.messages) < 2:
            return []

        # Extract user questions from history
        user_questions = [
            msg.content for msg in conversation.messages if msg.role == "user"
        ]

        # Extract assistant responses
        assistant_responses = [
            msg.content for msg in conversation.messages if msg.role == "assistant"
        ]

        # Create a prompt for generating related queries
        related_query_prompt = f"""
        Based on the conversation history, generate 3 related queries that the user might want to ask next.
        
        Previous user questions:
        {user_questions}
        
        Latest assistant response:
        {assistant_responses[-1]}
        
        The related queries should:
        1. Be answerable using movie database information or based on the current conversation context
        2. Not repeat questions already asked
        3. Focus on one of these categories:
           - Streaming availability (e.g., "What streaming platform is this movie available on?")
           - Comparisons between movies mentioned (e.g., "Compare [movie1] with [movie2]")
           - Information about directors/actors mentioned (e.g., "Tell me more about [director/actor]")
           - Similar movies or recommendations
        
        Return exactly 3 related queries in a clear, direct format.
        """

        # Create messages for the query generation
        messages = [
            SystemMessage(
                content="You are a helpful assistant that generates relevant follow-up questions about movies."
            ),
            HumanMessage(content=related_query_prompt),
        ]

        # Generate related queries
        response = await self.llm.agenerate([messages])
        response_text = response.generations[0][0].text

        # Parse the response into individual queries (assuming one per line or numbered format)
        query_texts = []
        for line in response_text.strip().split("\n"):
            # Remove numbers, dashes, etc. at the beginning of the line
            clean_line = line.strip()
            if (
                clean_line
                and not clean_line.startswith("```")
                and not clean_line.endswith("```")
            ):
                # Remove any numbered prefixes like "1. ", "2. ", etc.
                if (
                    clean_line[0].isdigit()
                    and len(clean_line) > 2
                    and clean_line[1:3] in [". ", ") "]
                ):
                    clean_line = clean_line[3:].strip()
                query_texts.append(clean_line)

        # Ensure we have exactly 3 queries
        query_texts = query_texts[:3]
        while len(query_texts) < 3:
            query_texts.append(
                f"Tell me more about another movie like {user_questions[-1]}"
            )

        # Convert to RelatedQuery objects
        return [RelatedQuery(text=text) for text in query_texts]

    async def get_response(
        self, message: str, conversation_id: Optional[str] = None
    ) -> Tuple[
        str,
        str,
        Optional[List[Citation]],
        Optional[List[ImageData]],
        Optional[List[RelatedQuery]],
    ]:
        """Get response from the LLM for a given message.

        Returns:
            Tuple containing:
            - response text
            - conversation ID
            - list of citations
            - list of images
            - list of related queries
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
                await self.tmdb_service.process_movie_query(message, conversation_id)
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

            # Generate related queries based on conversation history
            related_queries = await self._generate_related_queries(
                self.conversations[conversation_id]
            )

            # Return response with citations, images, and related queries if available
            return response_text, conversation_id, citations, images, related_queries

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
