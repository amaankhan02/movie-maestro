import json
from typing import Any, Dict, List, Optional, Tuple

import requests
from langchain.prompts import PromptTemplate
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
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
        self.movie_history = {}  # Track movies queried in each conversation

    def _create_query_analyzer_chain(self):
        """Creates a chain that decides if a query requires movie data"""
        template = """
        Analyze the following query and determine:
        1) Is the query asking about a specific movie or movies?
        2) If yes, what movie titles should be searched for?
        3) For each movie mentioned in the query, please identify it separately.

        Query: {query}

        Response format (JSON):
        {{{{
          "needs_movie_data": true/false,
          "movie_titles": ["movie title 1", "movie title 2", ...] (or empty list if none)
        }}}}

        Examples:
        - For "Tell me about Inception": {{"needs_movie_data": true, "movie_titles": ["Inception"]}}
        - For "Compare Inception to Interstellar": {{"needs_movie_data": true, "movie_titles": ["Inception", "Interstellar"]}}
        - For "What's the weather today?": {{"needs_movie_data": false, "movie_titles": []}}
        """

        prompt = PromptTemplate.from_template(template)
        return prompt | self.llm | StrOutputParser()

    def _create_response_generator_chain(self):
        """Creates a chain that generates responses with movie data citations"""
        template = """
        You are a helpful AI assistant with access to movie information.
        
        User query: {query}
        
        Movie information:
        {movie_data}
        
        Provide a comprehensive answer to the user's query using the movie information.
        
        When citing specific facts from the movie information, include a numbered citation like [1], [2], etc. 
        at the end of sentences containing information from the sources. Each movie should have its own citation number.
        
        For example: 
        - "Inception was directed by Christopher Nolan [1]."
        - "Interstellar explores themes of space travel and time dilation [2]."
        
        If comparing multiple movies, be sure to include information about each movie and make direct comparisons between them.
        Make sure to be accurate and thorough in your response.
        Only add citation numbers to factual information that comes directly from the movie data provided.
        
        Your answer:
        """

        prompt = PromptTemplate.from_template(template)
        return prompt | self.llm | StrOutputParser()

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
        self, query: str, conversation_id: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[List[Citation]], Optional[List[ImageData]]]:
        """Process a query, determine if movie data is needed, and generate a response.

        Args:
            query: User query
            conversation_id: Optional conversation ID to track movie history

        Returns:
            Tuple containing:
            - response text or None if not movie related
            - list of citations or None (numbered sequentially according to movie order)
            - list of images or None
        """
        # Initialize conversation history if it doesn't exist
        if conversation_id and conversation_id not in self.movie_history:
            self.movie_history[conversation_id] = {}

        # First, analyze if we need movie data
        analysis_result = await self.analyzer_chain.ainvoke({"query": query})

        try:
            # Parse the analysis
            analysis = json.loads(analysis_result)
            needs_movie_data = analysis.get("needs_movie_data", False)
            movie_titles = analysis.get("movie_titles", [])
        except Exception as e:
            print(f"Error parsing analysis result: {e}")
            # If parsing fails, assume we don't need movie data
            return None, None, None

        # If we don't need movie data, return None
        if not needs_movie_data or not movie_titles:
            return None, None, None

        # Filter out movies we've already queried in this conversation
        new_movies = []
        if conversation_id:
            for title in movie_titles:
                if title.lower() not in self.movie_history[conversation_id]:
                    new_movies.append(title)
        else:
            new_movies = movie_titles

        # Collect all movie data, both from history and new searches
        all_movie_data = []
        all_citations = []
        all_images = []

        # First, get data for new movies
        for i, movie_title in enumerate(new_movies):
            # Search for the movie
            search_results = self.search_tmdb(movie_title)

            # If no results, skip this movie
            if (
                not search_results
                or not search_results.get("results")
                or len(search_results["results"]) == 0
            ):
                continue

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
                citation = Citation(
                    text=top_result.get("overview", "No overview available"),
                    url=f"https://www.themoviedb.org/movie/{top_result['id']}",
                    title=f"{top_result.get('title', 'Unknown')} - TMDb",
                )

                movie_images = []
                if top_result.get("poster_path"):
                    poster_url = f"{self.base_image_url}{top_result['poster_path']}"
                    movie_images.append(
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
                citation = self.create_citations(movie_data)[0]  # Get first citation
                movie_images = self.extract_images(movie_data)

            # Add to our data collections
            formatted_movie_info = f"Movie #{len(all_movie_data) + 1} - {top_result.get('title', 'Unknown')}:\n{movie_info}"
            all_movie_data.append(formatted_movie_info)
            all_citations.append(citation)
            all_images.extend(movie_images)

            # Store in history for this conversation
            if conversation_id:
                self.movie_history[conversation_id][movie_title.lower()] = {
                    "data": movie_info,
                    "citation": citation,
                    "images": movie_images,
                }

        # Now get data for previously queried movies that are relevant to this query
        if conversation_id:
            for title in movie_titles:
                title_lower = title.lower()
                if title_lower in self.movie_history[
                    conversation_id
                ] and title_lower not in [m.lower() for m in new_movies]:
                    history = self.movie_history[conversation_id][title_lower]
                    formatted_movie_info = f"Movie #{len(all_movie_data) + 1} - {title}:\n{history['data']}"
                    all_movie_data.append(formatted_movie_info)
                    all_citations.append(history["citation"])
                    all_images.extend(history["images"])

        # If we couldn't find any movie data, return None
        if not all_movie_data:
            return None, None, None

        # Add citation reference guide at the end
        citation_guide = "\n\nCitation References:"
        for i, citation in enumerate(all_citations):
            citation_guide += f"\n[{i+1}] {citation.title}"

        # Generate the response
        response = await self.response_generator_chain.ainvoke(
            {"query": query, "movie_data": "\n\n".join(all_movie_data) + citation_guide}
        )

        return response, all_citations, all_images
