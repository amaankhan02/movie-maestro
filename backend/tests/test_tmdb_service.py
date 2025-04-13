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


async def test_tmdb_service():
    # Create LLM instance
    llm = ChatOpenAI(
        model_name=settings.MODEL_NAME,
        temperature=settings.MODEL_TEMPERATURE,
        openai_api_key=settings.OPENAI_API_KEY,
    )

    # Create TMDb service instance
    tmdb_service = TMDbService(api_key=settings.TMDB_API_KEY, llm=llm)

    # Test movie-related query
    movie_query = "Tell me about the movie Interstellar"
    response, citations, images = await tmdb_service.process_movie_query(movie_query)

    print("=" * 50)
    print(f"Query: {movie_query}")
    print("=" * 50)
    print("Response:")
    print(response)
    print("=" * 50)
    print("Citations:")
    if citations:
        for citation in citations:
            print(f"- {citation.title}: {citation.text[:100]}...")
    else:
        print("No citations")
    print("=" * 50)
    print("Images:")
    if images:
        for image in images:
            print(f"- {image.alt}: {image.url}")
    else:
        print("No images")

    # Test non-movie query
    non_movie_query = "What is the capital of France?"
    response, citations, images = await tmdb_service.process_movie_query(
        non_movie_query
    )

    print("=" * 50)
    print(f"Query: {non_movie_query}")
    print("=" * 50)
    print("Response: ")
    print(response)

    if response is None:
        print("Correct: Non-movie query was detected")
    else:
        print("Error: Non-movie query was misidentified as movie-related")


if __name__ == "__main__":
    asyncio.run(test_tmdb_service())
