import asyncio
import re
import uuid
from typing import List, Optional, Tuple

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from ..config import settings
from ..models import Citation, Conversation, ImageData, Message, RelatedQuery
from .query_router_service import QueryRouterService
from .tmdb_service import TMDbService
from .wikipedia_service import WikipediaService


class ChatService:
    def __init__(self):
        self.llm = ChatOpenAI(
            model_name=settings.MODEL_NAME,
            temperature=settings.MODEL_TEMPERATURE,
            openai_api_key=settings.OPENAI_API_KEY,
        )
        self.conversations: dict[str, Conversation] = {}

        # Initialize services
        self.tmdb_service = TMDbService(api_key=settings.TMDB_API_KEY, llm=self.llm)
        self.wikipedia_service = WikipediaService(llm=self.llm)
        self.query_router = QueryRouterService(llm=self.llm)

    def _create_system_prompt(self) -> str:
        """Create the system prompt for the LLM."""
        return """You are an expert on Movies and a helpful AI assistant assisting in movie-related queries. 
        Provide accurate and helpful responses. If you don't know something, say so. 
        Be concise but informative. When citing information from sources, use 
        numbered citations like [1], [2], etc. at the end of sentences containing factual information.
        The numbered citations will reference the source in the citation list at the end of your response."""

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
        1. Can be answered using TMDb, Wikipedia, or comparisons based on chat history
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
        1. Be answerable using one or more of these sources:
           - Movie database information (e.g., cast, ratings, release dates)
           - Wikipedia (e.g., film history, cultural context, themes, analysis)
           - Current conversation context
        2. Not repeat questions already asked
        3. Focus on one of these categories:
           - Streaming availability (e.g., "What streaming platform is this movie available on?")
           - Historical context or cultural impact of movies mentioned
           - Thematic analysis or comparisons between movies mentioned
           - Information about directors/actors mentioned
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

    async def _combine_data_sources(
        self,
        query: str,
        tmdb_result: Optional[Tuple[str, List[Citation], List[ImageData]]] = None,
        wikipedia_result: Optional[Tuple[str, List[Citation], List[ImageData]]] = None,
    ) -> Tuple[str, List[Citation], List[ImageData]]:
        """Combine data from multiple sources and generate a comprehensive response.

        Args:
            query: The user's query
            tmdb_result: Optional result from the TMDb service
            wikipedia_result: Optional result from the Wikipedia service

        Returns:
            Tuple containing:
            - combined response text
            - combined list of citations
            - combined list of images
        """
        all_data = []
        all_citations = []
        all_images = []

        # Add TMDb data if available
        if tmdb_result:
            tmdb_response, tmdb_citations, tmdb_images = tmdb_result
            if tmdb_response:
                all_data.append("TMDb Information:\n" + tmdb_response)
                all_citations.extend(tmdb_citations or [])
                all_images.extend(tmdb_images or [])

        # Add Wikipedia data if available
        if wikipedia_result:
            wiki_data, wiki_citations, wiki_images = wikipedia_result
            if wiki_data:
                all_data.append(wiki_data)
                # Replace any existing citations with new ones, with updated indices
                wiki_citation_count = len(wiki_citations or [])
                if wiki_citation_count > 0:
                    # Update citation indices for Wikipedia
                    for i, citation in enumerate(wiki_citations):
                        # Update the citation title to include the source
                        if "Wikipedia" not in citation.title:
                            citation.title = f"{citation.title} - Wikipedia"
                    all_citations.extend(wiki_citations)
                    all_images.extend(wiki_images or [])

        # If we don't have any data, return None
        if not all_data:
            return "", [], []

        # Create a prompt to generate a combined response
        template = """
        You are a helpful AI assistant with access to movie information from multiple sources.
        
        User query: {query}
        
        Available information:
        {data}
        
        Provide a concise, focused answer to the user's query using only the most relevant information provided.
        Keep your response under 500 words unless extensive detail is absolutely necessary.
        
        When citing specific facts, include a numbered citation like [1], [2], etc. at the end of the sentence containing information from the sources.
        DO NOT use source names like [TMDb] or [Wikipedia] in the main text, use only numbered citations.
        
        Make sure each source has its own citation number, and maintain consistency throughout your answer.
        For example:
        - "Inception was directed by Christopher Nolan [1]."
        - "The film explores themes of reality and dreams [2]."
        
        Focus on directly answering the query with the most important information first.
        If information is available from both sources, prioritize the most relevant details rather than including everything.
        
        Only mention contradictions between sources if they are significant and relevant to the query.
        
        Your answer:
        """

        prompt = PromptTemplate.from_template(template)
        combined_data = "\n\n".join(all_data)

        # Generate the combined response
        response = await (prompt | self.llm | StrOutputParser()).ainvoke(
            {"query": query, "data": combined_data}
        )

        return response, all_citations, all_images

    def _filter_unused_citations(
        self, response_text: str, citations: List[Citation]
    ) -> List[Citation]:
        """Filter citations to only include ones that are actually referenced in the response.

        Args:
            response_text: The generated response text
            citations: List of all available citations

        Returns:
            List of citations that are actually used in the response
        """
        if not citations:
            return []

        # Extract citation numbers from response text using regex
        citation_pattern = r"\[(\d+)\]"
        citation_matches = re.findall(citation_pattern, response_text)

        used_citation_indices = set(int(idx) for idx in citation_matches)

        used_citations = []
        for idx in used_citation_indices:
            # Citation numbers are 1-indexed, but list indices are 0-indexed
            citation_idx = idx - 1
            if 0 <= citation_idx < len(citations):
                used_citations.append(citations[citation_idx])

        return used_citations

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
            # First, route the query to determine which data sources to use
            routing_decision = await self.query_router.route_query(message)

            # Apply config settings to routing decision
            use_tmdb = routing_decision.get("use_tmdb", True) and settings.ENABLE_TMDB
            use_wikipedia = (
                routing_decision.get("use_wikipedia", False)
                and settings.ENABLE_WIKIPEDIA
            )

            print(f"Using data sources - TMDB: {use_tmdb}, Wikipedia: {use_wikipedia}")

            tmdb_result = None
            wikipedia_result = None

            # Use asyncio.gather to process data sources in parallel when possible
            data_source_tasks = []

            # Process with TMDb if needed
            if use_tmdb:
                print("Fetching data from TMDb...")
                tmdb_task = self.tmdb_service.process_movie_query(
                    message, conversation_id
                )
                data_source_tasks.append(tmdb_task)

            # Process with Wikipedia if needed
            if use_wikipedia:
                print("Fetching data from Wikipedia...")
                wiki_task = self.wikipedia_service.process_wikipedia_query(
                    message, conversation_id
                )
                data_source_tasks.append(wiki_task)

            # Wait for all data source tasks to complete
            if data_source_tasks:
                results = await asyncio.gather(*data_source_tasks)

                # Assign results to their respective variables
                result_index = 0
                if use_tmdb:
                    tmdb_result = results[result_index]
                    result_index += 1
                if use_wikipedia:
                    wikipedia_result = results[result_index]

            # If we have data from at least one source, combine them
            if tmdb_result or wikipedia_result:
                response_text, citations, images = await self._combine_data_sources(
                    message, tmdb_result, wikipedia_result
                )

                # Filter out unused citations
                if citations:
                    citations = self._filter_unused_citations(response_text, citations)
            else:
                # If no special data is needed, fall back to regular LLM response
                messages = self._format_messages(self.conversations[conversation_id])
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
