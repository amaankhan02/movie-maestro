import json
import os
from typing import Any, Dict, Optional

import requests
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_community.llms import OpenAI
from langchain_openai import ChatOpenAI


# Reuse your existing TMDB API functions
def fetch_tmdb_data(api_key: str, movie_id: int):
    """Retrieve movie data from TMDB API"""
    url = f"https://api.themoviedb.org/3/movie/{movie_id}"
    params = {
        "api_key": api_key,
        "append_to_response": "images,credits,keywords,watch/providers",
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as err:
        print(f"HTTP Error: {err}")
        return None


def search_tmdb(api_key: str, query: str):
    """Search for movies in TMDB API"""
    url = f"https://api.themoviedb.org/3/search/movie"
    params = {"api_key": api_key, "query": query}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as err:
        print(f"HTTP Error: {err}")
        return None


# Create a chain to determine if we need to query TMDB
def create_query_analyzer_chain(llm):
    """Creates a chain that decides if a query requires movie data"""
    template = """
    Analyze the following query and determine:
    1) Is the query asking about a specific movie or movies in general?
    2) If yes, what movie title should be searched for?

    Query: {query}

    Response format (JSON):
    {{
      "needs_movie_data": true/false,
      "movie_title": "movie name to search for or empty string"
    }}
    """

    prompt = PromptTemplate(input_variables=["query"], template=template)
    return LLMChain(llm=llm, prompt=prompt)


# Format the movie data for the context
def format_movie_data(movie_data: Dict[str, Any]) -> str:
    """Format movie data into a string for context"""
    # Extract directors
    directors = [
        crew["name"]
        for crew in movie_data["credits"]["crew"]
        if crew["job"] == "Director"
    ]

    # Extract cast members
    cast = [member["name"] for member in movie_data["credits"]["cast"][:5]]

    # Extract themes/keywords
    themes = [kw["name"] for kw in movie_data["keywords"]["keywords"]]

    # Extract watch providers if available
    watch_providers = []
    if (
        "watch/providers" in movie_data
        and "results" in movie_data["watch/providers"]
        and "US" in movie_data["watch/providers"]["results"]
        and "flatrate" in movie_data["watch/providers"]["results"]["US"]
    ):
        watch_providers = [
            p["provider_name"]
            for p in movie_data["watch/providers"]["results"]["US"]["flatrate"]
        ]

    # Format the data
    formatted_data = [
        f"Title: {movie_data['title']}",
        f"Overview: {movie_data['overview']}",
        f"Director(s): {', '.join(directors)}",
        f"Main Cast: {', '.join(cast)}",
        f"Release Date: {movie_data.get('release_date', 'Unknown')}",
        f"Genres: {', '.join([g['name'] for g in movie_data.get('genres', [])])}",
        f"Themes/Keywords: {', '.join(themes)}",
        f"Rating: {movie_data.get('vote_average', 'N/A')}/10",
    ]

    if watch_providers:
        formatted_data.append(f"Available on: {', '.join(watch_providers)}")

    return "\n".join(formatted_data)


# Create a chain to generate responses with citations
def create_response_generator_chain(llm):
    """Creates a chain that generates responses with movie data citations"""
    template = """
    You are a helpful AI assistant with access to movie information.
    
    User query: {query}
    
    Movie information:
    {movie_data}
    
    Provide a comprehensive answer to the user's query using the movie information.
    When citing specific facts from the movie information, include a citation number like [1].
    Make sure to be accurate and thorough in your response.
    
    Your answer:
    """

    prompt = PromptTemplate(input_variables=["query", "movie_data"], template=template)
    return LLMChain(llm=llm, prompt=prompt)


# Main function
def movie_query_assistant(query: str, tmdb_api_key: str, llm):
    """Process a query, determine if movie data is needed, and generate a response"""
    # First, analyze if we need movie data
    analyzer_chain = create_query_analyzer_chain(llm)
    analysis_result = analyzer_chain.invoke({"query": query})

    try:
        # Parse the analysis
        analysis = json.loads(analysis_result["text"])
        needs_movie_data = analysis.get("needs_movie_data", False)
        movie_title = analysis.get("movie_title", "")
    except:
        # If parsing fails, assume we don't need movie data
        needs_movie_data = False
        movie_title = ""

    # If we don't need movie data, just answer directly
    if not needs_movie_data or not movie_title:
        print("No movie data needed!")
        return "I'm sorry. Your question doesn't seem to be related to movies so I cannot answer it."
        # return llm.invoke(f"Answer this question based on your knowledge: {query}")

    # If we need movie data, search for the movie
    search_results = search_tmdb(tmdb_api_key, movie_title)

    # If no results, inform the user
    if (
        not search_results
        or not search_results.get("results")
        or len(search_results["results"]) == 0
    ):
        return f"I wanted to provide information about '{movie_title}', but couldn't find any matching movies. Could you please check the movie name or ask a different question?"

    # Get the top result
    top_result = search_results["results"][0]
    movie_id = top_result["id"]

    # Fetch detailed movie data
    movie_data = fetch_tmdb_data(tmdb_api_key, movie_id)

    # If we couldn't get detailed data, use the basic search result
    if not movie_data:
        movie_info = f"""
        Title: {top_result.get('title', 'Unknown')}
        Overview: {top_result.get('overview', 'No overview available')}
        Release Date: {top_result.get('release_date', 'Unknown')}
        Rating: {top_result.get('vote_average', 'Not rated')} (out of 10)
        """
    else:
        # Format the movie data
        movie_info = format_movie_data(movie_data)

    # Generate the response with citations
    response_chain = create_response_generator_chain(llm)
    response = response_chain.invoke({"query": query, "movie_data": movie_info})

    return response["text"]


# Example usage
if __name__ == "__main__":
    TMDB_API_KEY = "" 
    OPENAI_API_KEY = ""
    llm = ChatOpenAI(
        temperature=0.3, model="gpt-4", openai_api_key=OPENAI_API_KEY
    )  # Use a low temperature for more factual responses

    # Test with some example queries
    example_queries = [
        "Tell me about the movie Interstellar",
        "Who directed Inception?",
        # "What are some movies like The Dark Knight?",
        "What's the capital of France?"  # Non-movie query
    ]

    for query in example_queries:
        print(f"\nQuery: {query}")
        print("-" * 50)
        response = movie_query_assistant(query, TMDB_API_KEY, llm)
        print(response)
        print("=" * 50)
