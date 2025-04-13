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
        self.movie_history = (
            {}
        )  # Track movies queried in each conversation by conversation_id
        self.conversation_movies = (
            {}
        )  # Track the order of movies discussed in each conversation
        self.person_history = (
            {}
        )  # Track people (actors/directors) queried in conversations
        self.conversation_people = (
            {}
        )  # Track the order of people discussed in each conversation

    def _create_query_analyzer_chain(self):
        """Creates a chain that decides if a query requires movie and/or person data"""
        template = """
        Analyze the following query and determine:
        1) Is the query asking about a specific movie or movies?
        2) If yes, what movie titles should be searched for?
        3) For each movie mentioned in the query, please identify it separately.
        4) Does the query refer to previously discussed movies without naming them explicitly?
           This includes phrases like "those movies", "the previous movies", "compare it to those", etc.
        5) Is the query asking about a specific actor or director?
        6) If yes, what actor or director names should be searched for?
        7) For each person mentioned in the query, please identify them separately.
        8) Does the query refer to previously discussed people without naming them explicitly?

        Query: {query}
        Previous Movie Context: {previous_movies}
        Previous People Context: {previous_people}

        Response format (JSON):
        {{{{
          "needs_movie_data": true/false,
          "movie_titles": ["movie title 1", "movie title 2", ...],
          "references_previous_movies": true/false,
          "needs_person_data": true/false,
          "person_names": ["person name 1", "person name 2", ...],
          "references_previous_people": true/false
        }}}}

        Examples:
        - For "Tell me about Inception": {{"needs_movie_data": true, "movie_titles": ["Inception"], "references_previous_movies": false, "needs_person_data": false, "person_names": [], "references_previous_people": false}}
        - For "Compare Inception to Interstellar": {{"needs_movie_data": true, "movie_titles": ["Inception", "Interstellar"], "references_previous_movies": false, "needs_person_data": false, "person_names": [], "references_previous_people": false}}
        - For "What about The Dark Knight? How does it compare to those previous movies?": {{"needs_movie_data": true, "movie_titles": ["The Dark Knight"], "references_previous_movies": true, "needs_person_data": false, "person_names": [], "references_previous_people": false}}
        - For "What's the weather today?": {{"needs_movie_data": false, "movie_titles": [], "references_previous_movies": false, "needs_person_data": false, "person_names": [], "references_previous_people": false}}
        - For "Who is Tom Hanks?": {{"needs_movie_data": false, "movie_titles": [], "references_previous_movies": false, "needs_person_data": true, "person_names": ["Tom Hanks"], "references_previous_people": false}}
        - For "Tell me about Christopher Nolan's films": {{"needs_movie_data": false, "movie_titles": [], "references_previous_movies": false, "needs_person_data": true, "person_names": ["Christopher Nolan"], "references_previous_people": false}}
        - For "What has Meryl Streep acted in?": {{"needs_movie_data": false, "movie_titles": [], "references_previous_movies": false, "needs_person_data": true, "person_names": ["Meryl Streep"], "references_previous_people": false}}
        - For "Compare Quentin Tarantino and Steven Spielberg": {{"needs_movie_data": false, "movie_titles": [], "references_previous_movies": false, "needs_person_data": true, "person_names": ["Quentin Tarantino", "Steven Spielberg"], "references_previous_people": false}}
        """

        prompt = PromptTemplate.from_template(template)
        return prompt | self.llm | StrOutputParser()

    def _create_response_generator_chain(self):
        """Creates a chain that generates responses with movie/person data citations"""
        template = """
        You are a helpful AI assistant with access to movie and person information.
        
        User query: {query}
        
        Available information:
        {data}
        
        Provide a comprehensive answer to the user's query using the provided information.
        
        When citing specific facts, include a numbered citation like [1], [2], etc. 
        at the end of sentences containing information from the sources. Each source should have its own citation number.
        
        For example: 
        - "Inception was directed by Christopher Nolan [1]."
        - "Tom Hanks has won multiple Academy Awards for his performances [2]."
        
        If the query refers to "previous" items like movies or directors/actors etc or makes comparisons without naming specifics, make sure to include
        all relevant information from the context in your answer, with appropriate citations for each.
        
        If comparing multiple items, be sure to include information about each one and make direct comparisons between them.
        Include concrete specific details with citations when making comparisons.
        
        Make sure to be accurate and thorough in your response.
        Only add citation numbers to factual information that comes directly from the data provided.
        
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

    def search_person(self, query: str) -> Optional[Dict[str, Any]]:
        """Search for people (actors/directors) in TMDb API"""
        url = "https://api.themoviedb.org/3/search/person"
        params = {"api_key": self.api_key, "query": query}

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as err:
            print(f"HTTP Error: {err}")
            return None

    def fetch_person_data(self, person_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve person data from TMDb API"""
        url = f"https://api.themoviedb.org/3/person/{person_id}"
        params = {
            "api_key": self.api_key,
            "append_to_response": "images,movie_credits,tv_credits,external_ids",
        }

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

    def format_person_data(self, person_data: Dict[str, Any]) -> str:
        """Format person data into a string for context"""
        # Get basic information
        name = person_data.get("name", "Unknown")
        biography = person_data.get("biography", "No biography available.")
        birthday = person_data.get("birthday", "Unknown")
        place_of_birth = person_data.get("place_of_birth", "Unknown")

        # Sort movies by popularity and get top entries
        directed_movies = []
        acted_movies = []

        # Get directed movies
        if "movie_credits" in person_data and "crew" in person_data["movie_credits"]:
            directed = [
                movie
                for movie in person_data["movie_credits"]["crew"]
                if movie.get("job") == "Director"
            ]
            directed.sort(key=lambda x: x.get("popularity", 0), reverse=True)
            directed_movies = [movie.get("title", "") for movie in directed[:5]]

        # Get acted movies
        if "movie_credits" in person_data and "cast" in person_data["movie_credits"]:
            acted = person_data["movie_credits"]["cast"]
            acted.sort(key=lambda x: x.get("popularity", 0), reverse=True)
            acted_movies = [movie.get("title", "") for movie in acted[:10]]

        # Format the data
        formatted_data = [
            f"Name: {name}",
            f"Born: {birthday} in {place_of_birth}",
            f"Biography: {biography}",
        ]

        if directed_movies:
            formatted_data.append(
                f"Notable Directed Films: {', '.join(directed_movies)}"
            )

        if acted_movies:
            formatted_data.append(f"Notable Acting Roles: {', '.join(acted_movies)}")

        if "known_for_department" in person_data:
            formatted_data.append(f"Known for: {person_data['known_for_department']}")

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

    def extract_person_images(
        self, person_data: Dict[str, Any], max_images: int = 2
    ) -> List[ImageData]:
        """Extract image data from person_data.

        Args:
            person_data: TMDb person data
            max_images: Maximum number of images to extract

        Returns:
            List of ImageData objects
        """
        images = []
        name = person_data.get("name", "Unknown Person")

        # Add profile image if available
        if person_data.get("profile_path"):
            profile_url = f"{self.base_image_url}{person_data['profile_path']}"
            images.append(
                ImageData(
                    url=profile_url,
                    alt=f"{name} profile",
                    caption=f"Official profile for {name}",
                )
            )

        # Add additional images if available
        if "images" in person_data and "profiles" in person_data["images"]:
            profiles = person_data["images"]["profiles"]

            for i, profile in enumerate(
                profiles[: max_images - 1]
            ):  # -1 to account for main profile
                if i >= max_images - 1:  # Limit to max_images including main profile
                    break
                if profile.get("file_path") and profile.get(
                    "file_path"
                ) != person_data.get("profile_path"):
                    img_url = f"{self.base_image_url}{profile['file_path']}"
                    images.append(
                        ImageData(
                            url=img_url,
                            alt=f"{name} image",
                            caption=f"Image of {name}",
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

    def create_person_citations(self, person_data: Dict[str, Any]) -> List[Citation]:
        """Create citations from person data.

        Args:
            person_data: TMDb person data

        Returns:
            List of Citation objects
        """
        person_url = f"https://www.themoviedb.org/person/{person_data['id']}"
        biography = person_data.get("biography", "No biography available.")

        return [
            Citation(
                text=biography, url=person_url, title=f"{person_data['name']} - TMDb"
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
            self.conversation_movies[conversation_id] = []

        if conversation_id and conversation_id not in self.person_history:
            self.person_history[conversation_id] = {}
            self.conversation_people[conversation_id] = []

        # Get the list of previously discussed movies and people for this conversation
        previous_movies = []
        previous_people = []
        if conversation_id:
            if conversation_id in self.conversation_movies:
                previous_movies = self.conversation_movies[conversation_id]
            if conversation_id in self.conversation_people:
                previous_people = self.conversation_people[conversation_id]

        # Create formatted strings of previous items for the analyzer
        previous_movies_str = (
            ", ".join(previous_movies)
            if previous_movies
            else "No previously discussed movies"
        )

        previous_people_str = (
            ", ".join(previous_people)
            if previous_people
            else "No previously discussed people"
        )

        # First, analyze if we need movie data
        analysis_result = await self.analyzer_chain.ainvoke(
            {
                "query": query,
                "previous_movies": previous_movies_str,
                "previous_people": previous_people_str,
            }
        )

        try:
            # Parse the analysis
            analysis = json.loads(analysis_result)
            needs_movie_data = analysis.get("needs_movie_data", False)
            movie_titles = analysis.get("movie_titles", [])
            references_previous_movies = analysis.get(
                "references_previous_movies", False
            )
            needs_person_data = analysis.get("needs_person_data", False)
            person_names = analysis.get("person_names", [])
            references_previous_people = analysis.get(
                "references_previous_people", False
            )
        except Exception as e:
            print(f"Error parsing analysis result: {e}")
            # If parsing fails, assume we don't need special data
            return None, None, None

        # If we don't need movie or person data, return None
        if (
            not needs_movie_data
            and not references_previous_movies
            and not needs_person_data
            and not references_previous_people
        ):
            return None, None, None

        all_data = []
        all_citations = []
        all_images = []

        # Handle movie data if needed
        if needs_movie_data or references_previous_movies:
            movie_result = await self._process_movie_data(
                movie_titles, references_previous_movies, conversation_id
            )

            if movie_result:
                movie_data, movie_citations, movie_images = movie_result
                all_data.extend(movie_data)
                all_citations.extend(movie_citations)
                all_images.extend(movie_images)

        # Handle person data if needed
        if needs_person_data or references_previous_people:
            person_result = await self._process_person_data(
                person_names, references_previous_people, conversation_id
            )

            if person_result:
                person_data, person_citations, person_images = person_result
                all_data.extend(person_data)
                all_citations.extend(person_citations)
                all_images.extend(person_images)

        # If we couldn't find any data, return None
        if not all_data:
            return None, None, None

        # Add citation reference guide at the end
        citation_guide = "\n\nCitation References:"
        for i, citation in enumerate(all_citations):
            citation_guide += f"\n[{i+1}] {citation.title}"

        # Generate the response
        response = await self.response_generator_chain.ainvoke(
            {"query": query, "data": "\n\n".join(all_data) + citation_guide}
        )

        return response, all_citations, all_images

    async def _process_movie_data(
        self,
        movie_titles: List[str],
        references_previous_movies: bool,
        conversation_id: Optional[str] = None,
    ) -> Tuple[List[str], List[Citation], List[ImageData]]:
        """Process movie data based on titles and references.

        Args:
            movie_titles: List of movie titles to process
            references_previous_movies: Whether the query references previous movies
            conversation_id: Optional conversation ID to track history

        Returns:
            Tuple containing:
            - list of formatted movie data strings
            - list of citations
            - list of images
        """
        # If the query references previous movies, include them in the list
        # of movies to process, even if they're not explicitly mentioned
        if (
            references_previous_movies
            and conversation_id
            and conversation_id in self.conversation_movies
        ):
            # Add previously discussed movies that aren't already in movie_titles
            for prev_movie in self.conversation_movies[conversation_id]:
                if prev_movie not in movie_titles:
                    movie_titles.append(prev_movie)

        # If we still don't have any movie titles after checking references, return None
        if not movie_titles:
            return [], [], []

        # Normalize movie titles for lookup and deduplication
        normalized_titles = {title.lower(): title for title in movie_titles}

        # Track movies we've already processed in this query using their normalized titles
        processed_normalized_titles = set()

        # Collect all movie data, both from history and new searches
        all_movie_data = []
        all_citations = []
        all_images = []

        # First, process movies already in history
        if conversation_id and conversation_id in self.movie_history:
            for normalized_title in normalized_titles.keys():
                # Check if this normalized title is in history
                if (
                    normalized_title in self.movie_history[conversation_id]
                    and normalized_title not in processed_normalized_titles
                ):
                    history = self.movie_history[conversation_id][normalized_title]
                    actual_title = history.get(
                        "title", normalized_titles[normalized_title]
                    )

                    formatted_movie_info = f"Movie #{len(all_movie_data) + 1} - {actual_title}:\n{history['data']}"
                    all_movie_data.append(formatted_movie_info)
                    all_citations.append(history["citation"])
                    all_images.extend(history["images"])

                    # Mark as processed
                    processed_normalized_titles.add(normalized_title)

                    # Add to conversation movies if not already there
                    if actual_title not in self.conversation_movies[conversation_id]:
                        self.conversation_movies[conversation_id].append(actual_title)

        # Then process new movies
        for title in movie_titles:
            normalized_title = title.lower()

            # Skip if we've already processed this movie
            if normalized_title in processed_normalized_titles:
                continue

            # Search for the movie
            search_results = self.search_tmdb(title)

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
            actual_title = top_result.get("title", title)

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
                actual_title = movie_data.get("title", title)

                # Extract citations and images
                citation = self.create_citations(movie_data)[0]  # Get first citation
                movie_images = self.extract_images(movie_data)

            # Add to our data collections
            formatted_movie_info = (
                f"Movie #{len(all_movie_data) + 1} - {actual_title}:\n{movie_info}"
            )
            all_movie_data.append(formatted_movie_info)
            all_citations.append(citation)
            all_images.extend(movie_images)

            # Mark as processed
            processed_normalized_titles.add(normalized_title)

            # Store in history for this conversation
            if conversation_id:
                self.movie_history[conversation_id][normalized_title] = {
                    "data": movie_info,
                    "citation": citation,
                    "images": movie_images,
                    "title": actual_title,
                }

                # Add to conversation movies if not already there
                if actual_title not in self.conversation_movies[conversation_id]:
                    self.conversation_movies[conversation_id].append(actual_title)

        # If references_previous_movies is true, include all previous movies that weren't explicitly mentioned
        if (
            references_previous_movies
            and conversation_id
            and conversation_id in self.conversation_movies
        ):
            for prev_title in self.conversation_movies[conversation_id]:
                prev_title_lower = prev_title.lower()
                # Skip if we've already processed this movie in this query
                if prev_title_lower in processed_normalized_titles:
                    continue

                # Find the movie in history by title (case-insensitive)
                movie_found = False
                for title_key, movie_info in self.movie_history[
                    conversation_id
                ].items():
                    stored_title = movie_info.get("title", "").lower()
                    if stored_title == prev_title_lower:
                        formatted_movie_info = f"Movie #{len(all_movie_data) + 1} - {prev_title}:\n{movie_info['data']}"
                        all_movie_data.append(formatted_movie_info)
                        all_citations.append(movie_info["citation"])
                        all_images.extend(movie_info["images"])
                        processed_normalized_titles.add(prev_title_lower)
                        movie_found = True
                        break

                if not movie_found:
                    print(
                        f"Warning: Movie {prev_title} was in conversation history but not found in movie_history"
                    )

        return all_movie_data, all_citations, all_images

    async def _process_person_data(
        self,
        person_names: List[str],
        references_previous_people: bool,
        conversation_id: Optional[str] = None,
    ) -> Tuple[List[str], List[Citation], List[ImageData]]:
        """Process person data based on names and references.

        Args:
            person_names: List of person names to process
            references_previous_people: Whether the query references previous people
            conversation_id: Optional conversation ID to track history

        Returns:
            Tuple containing:
            - list of formatted person data strings
            - list of citations
            - list of images
        """
        # If the query references previous people, include them in the list
        if (
            references_previous_people
            and conversation_id
            and conversation_id in self.conversation_people
        ):
            # Add previously discussed people that aren't already in person_names
            for prev_person in self.conversation_people[conversation_id]:
                if prev_person not in person_names:
                    person_names.append(prev_person)

        # If we still don't have any person names after checking references, return empty lists
        if not person_names:
            return [], [], []

        # Normalize person names for lookup and deduplication
        normalized_names = {name.lower(): name for name in person_names}

        # Track people we've already processed in this query using their normalized names
        processed_normalized_names = set()

        # Collect all person data, both from history and new searches
        all_person_data = []
        all_citations = []
        all_images = []

        # First, process people already in history
        if conversation_id and conversation_id in self.person_history:
            for normalized_name in normalized_names.keys():
                # Check if this normalized name is in history
                if (
                    normalized_name in self.person_history[conversation_id]
                    and normalized_name not in processed_normalized_names
                ):
                    history = self.person_history[conversation_id][normalized_name]
                    actual_name = history.get("name", normalized_names[normalized_name])

                    formatted_person_info = f"Person #{len(all_person_data) + 1} - {actual_name}:\n{history['data']}"
                    all_person_data.append(formatted_person_info)
                    all_citations.append(history["citation"])
                    all_images.extend(history["images"])

                    # Mark as processed
                    processed_normalized_names.add(normalized_name)

                    # Add to conversation people if not already there
                    if actual_name not in self.conversation_people[conversation_id]:
                        self.conversation_people[conversation_id].append(actual_name)

        # Then process new people
        for name in person_names:
            normalized_name = name.lower()

            # Skip if we've already processed this person
            if normalized_name in processed_normalized_names:
                continue

            # Search for the person
            search_results = self.search_person(name)

            # If no results, skip this person
            if (
                not search_results
                or not search_results.get("results")
                or len(search_results["results"]) == 0
            ):
                continue

            # Get the top result
            top_result = search_results["results"][0]
            person_id = top_result["id"]
            actual_name = top_result.get("name", name)

            # Fetch detailed person data
            person_data = self.fetch_person_data(person_id)

            # If we couldn't get detailed data, use the basic search result
            if not person_data:
                person_info = f"""
                Name: {top_result.get('name', 'Unknown')}
                Known For: {top_result.get('known_for_department', 'Unknown')}
                """

                # Create minimal citations and images
                citation = Citation(
                    text=f"Information about {top_result.get('name', 'Unknown')}",
                    url=f"https://www.themoviedb.org/person/{top_result['id']}",
                    title=f"{top_result.get('name', 'Unknown')} - TMDb",
                )

                person_images = []
                if top_result.get("profile_path"):
                    profile_url = f"{self.base_image_url}{top_result['profile_path']}"
                    person_images.append(
                        ImageData(
                            url=profile_url,
                            alt=f"{top_result.get('name', 'Unknown')} profile",
                            caption=f"Profile for {top_result.get('name', 'Unknown')}",
                        )
                    )
            else:
                # Format the person data for context
                person_info = self.format_person_data(person_data)
                actual_name = person_data.get("name", name)

                # Extract citations and images
                citation = self.create_person_citations(person_data)[
                    0
                ]  # Get first citation
                person_images = self.extract_person_images(person_data)

            # Add to our data collections
            formatted_person_info = (
                f"Person #{len(all_person_data) + 1} - {actual_name}:\n{person_info}"
            )
            all_person_data.append(formatted_person_info)
            all_citations.append(citation)
            all_images.extend(person_images)

            # Mark as processed
            processed_normalized_names.add(normalized_name)

            # Store in history for this conversation
            if conversation_id:
                if conversation_id not in self.person_history:
                    self.person_history[conversation_id] = {}

                self.person_history[conversation_id][normalized_name] = {
                    "data": person_info,
                    "citation": citation,
                    "images": person_images,
                    "name": actual_name,
                }

                # Add to conversation people if not already there
                if conversation_id not in self.conversation_people:
                    self.conversation_people[conversation_id] = []

                if actual_name not in self.conversation_people[conversation_id]:
                    self.conversation_people[conversation_id].append(actual_name)

        # If references_previous_people is true, include all previous people that weren't explicitly mentioned
        if (
            references_previous_people
            and conversation_id
            and conversation_id in self.conversation_people
        ):
            for prev_name in self.conversation_people[conversation_id]:
                prev_name_lower = prev_name.lower()
                # Skip if we've already processed this person in this query
                if prev_name_lower in processed_normalized_names:
                    continue

                # Find the person in history by name (case-insensitive)
                person_found = False
                if conversation_id in self.person_history:
                    for name_key, person_info in self.person_history[
                        conversation_id
                    ].items():
                        stored_name = person_info.get("name", "").lower()
                        if stored_name == prev_name_lower:
                            formatted_person_info = f"Person #{len(all_person_data) + 1} - {prev_name}:\n{person_info['data']}"
                            all_person_data.append(formatted_person_info)
                            all_citations.append(person_info["citation"])
                            all_images.extend(person_info["images"])
                            processed_normalized_names.add(prev_name_lower)
                            person_found = True
                            break

                if not person_found:
                    print(
                        f"Warning: Person {prev_name} was in conversation history but not found in person_history"
                    )

        return all_person_data, all_citations, all_images
