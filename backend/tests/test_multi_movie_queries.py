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


async def test_multi_movie_queries():
    """Test the multi-movie query feature and conversation history."""
    # Create LLM instance
    llm = ChatOpenAI(
        model_name=settings.MODEL_NAME,
        temperature=settings.MODEL_TEMPERATURE,
        openai_api_key=settings.OPENAI_API_KEY,
    )

    # Create TMDb service instance
    tmdb_service = TMDbService(api_key=settings.TMDB_API_KEY, llm=llm)

    # Create a test conversation ID
    conversation_id = "test-conversation-1"

    # Test 1: Multi-movie query
    print("\n" + "=" * 50)
    print("TEST 1: MULTI-MOVIE QUERY")
    print("=" * 50)

    multi_movie_query = "Compare Inception to Interstellar"
    response, citations, images = await tmdb_service.process_movie_query(
        multi_movie_query, conversation_id
    )

    print(f"Query: {multi_movie_query}")
    print("=" * 50)
    print("Response:")
    print(response)
    print("=" * 50)
    print("Citations:")
    if citations:
        print(f"Number of citations: {len(citations)}")
        for i, citation in enumerate(citations):
            print(f"{i+1} - {citation.title}: {citation.text[:100]}...")
    else:
        print("No citations")

    print("=" * 50)
    print("Images:")
    if images:
        print(f"Number of images: {len(images)}")
        for i, image in enumerate(images):
            print(f"{i+1} - {image.alt}: {image.url}")
    else:
        print("No images")

    # Test 2: Follow-up query referencing previously queried movie
    print("\n" + "=" * 50)
    print("TEST 2: FOLLOW-UP QUERY")
    print("=" * 50)

    followup_query = "Now tell me about The Dark Knight and compare it to Inception"
    response, citations, images = await tmdb_service.process_movie_query(
        followup_query, conversation_id
    )

    print(f"Query: {followup_query}")
    print("=" * 50)
    print("Response:")
    print(response)
    print("=" * 50)
    print("Citations:")
    if citations:
        print(f"Number of citations: {len(citations)}")
        for i, citation in enumerate(citations):
            print(f"{i+1} - {citation.title}: {citation.text[:100]}...")
    else:
        print("No citations")

    # Test 3: Follow-up query with only previously queried movies
    print("\n" + "=" * 50)
    print("TEST 3: QUERY WITH ONLY PREVIOUSLY QUERIED MOVIES")
    print("=" * 50)

    previous_movies_query = "Compare Inception, Interstellar, and The Dark Knight"
    response, citations, images = await tmdb_service.process_movie_query(
        previous_movies_query, conversation_id
    )

    print(f"Query: {previous_movies_query}")
    print("=" * 50)
    print("Response:")
    print(response)
    print("=" * 50)
    print("Citations:")
    if citations:
        print(f"Number of citations: {len(citations)}")
        for i, citation in enumerate(citations):
            print(f"{i+1} - {citation.title}")
    else:
        print("No citations")


if __name__ == "__main__":
    # Run the multi-movie test
    asyncio.run(test_multi_movie_queries())
