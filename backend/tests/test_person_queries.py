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


async def test_person_queries():
    """
    Test the functionality for querying information about actors and directors.
    """
    # Create LLM instance
    llm = ChatOpenAI(
        model_name=settings.MODEL_NAME,
        temperature=settings.MODEL_TEMPERATURE,
        openai_api_key=settings.OPENAI_API_KEY,
    )

    # Create TMDb service instance
    tmdb_service = TMDbService(api_key=settings.TMDB_API_KEY, llm=llm)

    # Test basic person query (actor)
    actor_query = "Who is Tom Hanks?"
    print("\n" + "=" * 50)
    print(f"QUERY: {actor_query}")
    print("=" * 50)

    response, citations, images = await tmdb_service.process_movie_query(actor_query)

    print("RESPONSE:")
    print(response)
    print("\nCITATIONS:")
    if citations:
        for i, citation in enumerate(citations):
            print(f"[{i+1}] {citation.title}: {citation.text[:100]}...")
    else:
        print("No citations")

    print("\nIMAGES:")
    if images:
        for image in images:
            print(f"- {image.alt}: {image.url}")
    else:
        print("No images")

    # Test basic person query (director)
    director_query = "Tell me about Steven Spielberg"
    print("\n" + "=" * 50)
    print(f"QUERY: {director_query}")
    print("=" * 50)

    response, citations, images = await tmdb_service.process_movie_query(director_query)

    print("RESPONSE:")
    print(response)
    print("\nCITATIONS:")
    if citations:
        for i, citation in enumerate(citations):
            print(f"[{i+1}] {citation.title}: {citation.text[:100]}...")
    else:
        print("No citations")

    print("\nIMAGES:")
    if images:
        for image in images:
            print(f"- {image.alt}: {image.url}")
    else:
        print("No images")

    # Test query about a person's filmography
    filmography_query = "What movies has Christopher Nolan directed?"
    print("\n" + "=" * 50)
    print(f"QUERY: {filmography_query}")
    print("=" * 50)

    response, citations, images = await tmdb_service.process_movie_query(
        filmography_query
    )

    print("RESPONSE:")
    print(response)
    print("\nCITATIONS:")
    if citations:
        for i, citation in enumerate(citations):
            print(f"[{i+1}] {citation.title}: {citation.text[:100]}...")
    else:
        print("No citations")

    print("\nIMAGES:")
    if images:
        for image in images:
            print(f"- {image.alt}: {image.url}")
    else:
        print("No images")

    # Test comparison query
    comparison_query = "Compare Martin Scorsese and Quentin Tarantino"
    print("\n" + "=" * 50)
    print(f"QUERY: {comparison_query}")
    print("=" * 50)

    response, citations, images = await tmdb_service.process_movie_query(
        comparison_query
    )

    print("RESPONSE:")
    print(response)
    print("\nCITATIONS:")
    if citations:
        for i, citation in enumerate(citations):
            print(f"[{i+1}] {citation.title}: {citation.text[:100]}...")
    else:
        print("No citations")

    print("\nIMAGES:")
    if images:
        for image in images:
            print(f"- {image.alt}: {image.url}")
    else:
        print("No images")

    # Test conversation context (referring to previous people)
    conversation_id = "test-conversation-123"

    # First query
    first_query = "Who is Meryl Streep?"
    print("\n" + "=" * 50)
    print(f"CONVERSATION QUERY 1: {first_query}")
    print("=" * 50)

    response, citations, images = await tmdb_service.process_movie_query(
        first_query, conversation_id=conversation_id
    )

    print("RESPONSE:")
    print(response)

    # Follow-up query referring to previous person
    followup_query = "What awards has she won?"
    print("\n" + "=" * 50)
    print(f"CONVERSATION QUERY 2: {followup_query}")
    print("=" * 50)

    response, citations, images = await tmdb_service.process_movie_query(
        followup_query, conversation_id=conversation_id
    )

    print("RESPONSE:")
    print(response)
    print("\nCITATIONS:")
    if citations:
        for i, citation in enumerate(citations):
            print(f"[{i+1}] {citation.title}: {citation.text[:100]}...")
    else:
        print("No citations")


async def test_person_search():
    """
    Test the low-level person search functionality.
    """
    # Create a minimal LLM instance - we won't use it for the low-level tests,
    # but TMDbService requires one for initialization
    llm = ChatOpenAI(
        model_name=settings.MODEL_NAME,
        temperature=settings.MODEL_TEMPERATURE,
        openai_api_key=settings.OPENAI_API_KEY,
    )

    tmdb_service = TMDbService(api_key=settings.TMDB_API_KEY, llm=llm)

    # Test search_person method
    print("\n" + "=" * 50)
    print("Testing search_person method")
    print("=" * 50)

    search_results = tmdb_service.search_person("Leonardo DiCaprio")
    if (
        search_results
        and "results" in search_results
        and len(search_results["results"]) > 0
    ):
        top_result = search_results["results"][0]
        print(f"Top result: {top_result.get('name')} (ID: {top_result.get('id')})")
        print(f"Known for: {top_result.get('known_for_department')}")
        print(f"Popularity: {top_result.get('popularity')}")
    else:
        print("No results found")

    # Test fetch_person_data method
    print("\n" + "=" * 50)
    print("Testing fetch_person_data method")
    print("=" * 50)

    # Leonardo DiCaprio's ID
    person_id = (
        6193
        if search_results
        and "results" in search_results
        and len(search_results["results"]) > 0
        else 6193
    )

    person_data = tmdb_service.fetch_person_data(person_id)
    if person_data:
        print(f"Name: {person_data.get('name')}")
        print(
            f"Biography excerpt: {person_data.get('biography', 'No biography')[:200]}..."
        )
        print(f"Birthday: {person_data.get('birthday')}")
        print(f"Place of birth: {person_data.get('place_of_birth')}")

        # Print movie credits
        if "movie_credits" in person_data and "cast" in person_data["movie_credits"]:
            print("\nTop 5 acting credits (by popularity):")
            cast = sorted(
                person_data["movie_credits"]["cast"],
                key=lambda x: x.get("popularity", 0),
                reverse=True,
            )
            for i, movie in enumerate(cast[:5]):
                print(
                    f"{i+1}. {movie.get('title')} ({movie.get('release_date', 'Unknown')[:4]})"
                )
    else:
        print("No person data found")

    # Test format_person_data method
    print("\n" + "=" * 50)
    print("Testing format_person_data method")
    print("=" * 50)

    if person_data:
        formatted_data = tmdb_service.format_person_data(person_data)
        print(formatted_data)
    else:
        print("No person data to format")


if __name__ == "__main__":
    # Run the tests
    print("\nRunning person query tests...")
    asyncio.run(test_person_queries())

    print("\nRunning person search tests...")
    asyncio.run(test_person_search())
