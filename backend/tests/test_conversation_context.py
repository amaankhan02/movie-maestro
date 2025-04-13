import asyncio
import os
import sys
from pathlib import Path

# Add the parent directory to the sys.path
parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))

from langchain_openai import ChatOpenAI
from src.config import settings
from src.services.tmdb_service import TMDbService


async def test_conversation_context():
    """Test the improved conversation history features.

    This tests the system's ability to:
    1. Handle implicit references to previously discussed movies
    2. Include appropriate citations for both new and previously discussed movies
    3. Maintain context across multiple turns in a conversation
    """
    # Create LLM instance
    llm = ChatOpenAI(
        model_name=settings.MODEL_NAME,
        temperature=settings.MODEL_TEMPERATURE,
        openai_api_key=settings.OPENAI_API_KEY,
    )

    # Create TMDb service instance
    tmdb_service = TMDbService(api_key=settings.TMDB_API_KEY, llm=llm)

    # Create a test conversation ID
    conversation_id = "test-conversation-context"

    # Test 1: Initial movie query
    print("\n" + "=" * 80)
    print("TEST 1: INITIAL MOVIE QUERY")
    print("=" * 80)

    initial_query = "Compare Inception and Interstellar"
    response, citations, images = await tmdb_service.process_movie_query(
        initial_query, conversation_id
    )

    print(f"Query: {initial_query}")
    print("=" * 80)
    print("Number of citations:", len(citations) if citations else 0)
    print("Response summary:", response[:200] + "..." if response else "No response")
    print("=" * 80)
    print(
        "Conversation movies tracked:",
        tmdb_service.conversation_movies.get(conversation_id, []),
    )

    # Test 2: Follow-up query with implicit references
    print("\n" + "=" * 80)
    print("TEST 2: FOLLOW-UP WITH IMPLICIT REFERENCES")
    print("=" * 80)

    followup_query = (
        "What about The Dark Knight? How does it compare to those previous movies?"
    )
    response, citations, images = await tmdb_service.process_movie_query(
        followup_query, conversation_id
    )

    print(f"Query: {followup_query}")
    print("=" * 80)
    print("Number of citations:", len(citations) if citations else 0)
    print("=" * 80)
    print("Citations:")
    if citations:
        for i, citation in enumerate(citations):
            print(f"[{i+1}] {citation.title}")
    else:
        print("No citations")
    print("=" * 80)
    print("Response summary:", response[:200] + "..." if response else "No response")

    # Test 3: Follow-up query with only implicit references
    print("\n" + "=" * 80)
    print("TEST 3: QUERY WITH ONLY IMPLICIT REFERENCES")
    print("=" * 80)

    implicit_query = "Which of these movies had the highest box office success?"
    response, citations, images = await tmdb_service.process_movie_query(
        implicit_query, conversation_id
    )

    print(f"Query: {implicit_query}")
    print("=" * 80)
    print("Number of citations:", len(citations) if citations else 0)
    print("=" * 80)
    print("Citations:")
    if citations:
        for i, citation in enumerate(citations):
            print(f"[{i+1}] {citation.title}")
    else:
        print("No citations")
    print("=" * 80)
    print("Response summary:", response[:200] + "..." if response else "No response")


if __name__ == "__main__":
    asyncio.run(test_conversation_context())
