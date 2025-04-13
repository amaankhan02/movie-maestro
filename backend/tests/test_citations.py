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


async def test_numbered_citations():
    """Test the numbered citations feature."""
    # Create LLM instance
    llm = ChatOpenAI(
        model_name=settings.MODEL_NAME,
        temperature=settings.MODEL_TEMPERATURE,
        openai_api_key=settings.OPENAI_API_KEY,
    )

    # Create TMDb service instance
    tmdb_service = TMDbService(api_key=settings.TMDB_API_KEY, llm=llm)

    # Create a test conversation ID
    conversation_id = "test-citations-1"

    # Test with a multi-movie query
    query = "Compare The Dark Knight and Inception"
    response, citations, images = await tmdb_service.process_movie_query(
        query, conversation_id
    )

    print("=" * 80)
    print(f"Query: {query}")
    print("=" * 80)
    print("Response:")
    print(response)
    print("=" * 80)
    print("Citations:")
    if citations:
        for i, citation in enumerate(citations):
            print(f"[{i+1}] {citation.title}")
    else:
        print("No citations")


if __name__ == "__main__":
    asyncio.run(test_numbered_citations())
