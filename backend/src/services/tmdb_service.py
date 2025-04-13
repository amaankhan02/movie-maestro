import json
from typing import Any, Dict, List, Optional, Tuple

import requests
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from ..config import settings
from ..models import Citation, ImageData


class TMDbService:
    """Service for interacting with The Movie Database (TMDb) API."""

    def __init__(self, api_key: str, llm: ChatOpenAI):
        """Initialize the TMDb service.

        Args:
            api_key: TMDb API key
            llm: LangChain LLM instance
        """
        self.api_key = api_key
        self.llm = llm
        self.base_image_url = "https://image.tmdb.org/t/p/original/"
        self.analyzer_chain = self._create_query_analyzer_chain()
        self.response_generator_chain = self._create_response_generator_chain()

    def _create_query_analyzer_chain(self) -> LLMChain:
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
        return LLMChain(llm=self.llm, prompt=prompt)

    def _create_response_generator_chain(self) -> LLMChain:
        """Creates a chain that generates responses with movie data citations"""
        template = """
        You are a helpful AI assistant with access to movie information.
        
        User query: {query}
        
        Movie information:
        {movie_data}
        
        Provide a comprehensive answer to the user's query using the movie information.
        When citing specific facts from the movie information, include the source [TMDb] at the end of sentences containing information 
        from the TMDb database. For example: "Interstellar was directed by Christopher Nolan [TMDb]."
        
        Make sure to be accurate and thorough in your response.
        Only add [TMDb] to factual information that comes directly from the movie data provided.
        
        Your answer:
        """

        prompt = PromptTemplate(
            input_variables=["query", "movie_data"], template=template
        )
        return LLMChain(llm=self.llm, prompt=prompt)

    def fetch_tmdb_data(self, movie_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve movie data from TMDb API"""
        url = f"https://api.themoviedb.org/3/movie/{movie_id}"
        params = {
            "api_key": self.api_key,
            "append_to_response": "images,credits,keywords,watch/providers",
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as err:
            print(f"HTTP Error: {err}")
            return None

    def search_tmdb(self, query: str) -> Optional[Dict[str, Any]]:
        """Search for movies in TMDb API"""
        url = "https://api.themoviedb.org/3/search/movie"
        params = {"api_key": self.api_key, "query": query}

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as err:
            print(f"HTTP Error: {err}")
            return None

    def format_movie_data(self, movie_data: Dict[str, Any]) -> str:
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

    def extract_images(
        self, movie_data: Dict[str, Any], max_images: int = 3
    ) -> List[ImageData]:
        """Extract image data from movie_data.

        Args:
            movie_data: TMDb movie data
            max_images: Maximum number of images to extract

        Returns:
            List of ImageData objects
        """
        images = []

        # Add poster if available
        if movie_data.get("poster_path"):
            poster_url = f"{self.base_image_url}{movie_data['poster_path']}"
            images.append(
                ImageData(
                    url=poster_url,
                    alt=f"{movie_data['title']} poster",
                    caption=f"Official poster for {movie_data['title']}",
                )
            )

        # Add backdrop images
        backdrops = movie_data.get("images", {}).get("backdrops", [])
        for i, backdrop in enumerate(
            backdrops[: max_images - 1]
        ):  # -1 to account for poster
            if i >= max_images - 1:  # Limit to max_images including poster
                break
            backdrop_url = f"{self.base_image_url}{backdrop['file_path']}"
            images.append(
                ImageData(
                    url=backdrop_url,
                    alt=f"{movie_data['title']} scene",
                    caption=f"Scene from {movie_data['title']}",
                )
            )

        return images

    def create_citations(self, movie_data: Dict[str, Any]) -> List[Citation]:
        """Create citations from movie data.

        Args:
            movie_data: TMDb movie data

        Returns:
            List of Citation objects
        """
        movie_url = f"https://www.themoviedb.org/movie/{movie_data['id']}"
        overview = movie_data.get("overview", "No overview available.")

        return [
            Citation(
                text=overview, url=movie_url, title=f"{movie_data['title']} - TMDb"
            )
        ]

    async def process_movie_query(
        self, query: str
    ) -> Tuple[Optional[str], Optional[List[Citation]], Optional[List[ImageData]]]:
        """Process a query, determine if movie data is needed, and generate a response.

        Args:
            query: User query

        Returns:
            Tuple containing:
            - response text or None if not movie related
            - list of citations or None
            - list of images or None
        """
        # First, analyze if we need movie data
        analysis_result = await self.analyzer_chain.ainvoke({"query": query})

        try:
            # Parse the analysis
            analysis = json.loads(analysis_result["text"])
            needs_movie_data = analysis.get("needs_movie_data", False)
            movie_title = analysis.get("movie_title", "")
        except:
            # If parsing fails, assume we don't need movie data
            return None, None, None

        # If we don't need movie data, return None
        if not needs_movie_data or not movie_title:
            return None, None, None

        # Search for the movie
        search_results = self.search_tmdb(movie_title)

        # If no results, return None
        if (
            not search_results
            or not search_results.get("results")
            or len(search_results["results"]) == 0
        ):
            return None, None, None

        # Get the top result
        top_result = search_results["results"][0]
        movie_id = top_result["id"]

        # Fetch detailed movie data
        movie_data = self.fetch_tmdb_data(movie_id)

        # If we couldn't get detailed data, use the basic search result
        if not movie_data:
            movie_info = f"""
            Title: {top_result.get('title', 'Unknown')}
            Overview: {top_result.get('overview', 'No overview available')}
            Release Date: {top_result.get('release_date', 'Unknown')}
            Rating: {top_result.get('vote_average', 'Not rated')} (out of 10)
            """

            # Create minimal citations and images
            citations = [
                Citation(
                    text=top_result.get("overview", "No overview available"),
                    url=f"https://www.themoviedb.org/movie/{top_result['id']}",
                    title=f"{top_result.get('title', 'Unknown')} - TMDb",
                )
            ]

            images = []
            if top_result.get("poster_path"):
                poster_url = f"{self.base_image_url}{top_result['poster_path']}"
                images.append(
                    ImageData(
                        url=poster_url,
                        alt=f"{top_result.get('title', 'Unknown')} poster",
                        caption=f"Official poster for {top_result.get('title', 'Unknown')}",
                    )
                )
        else:
            # Format the movie data for context
            movie_info = self.format_movie_data(movie_data)

            # Extract citations and images
            citations = self.create_citations(movie_data)
            images = self.extract_images(movie_data)

        # Generate the response
        response = await self.response_generator_chain.ainvoke(
            {"query": query, "movie_data": movie_info}
        )

        return response["text"], citations, images
