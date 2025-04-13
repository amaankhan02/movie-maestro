import json
from typing import Any, Dict, List, Optional, Tuple

import requests
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from ..models import Citation, ImageData


class WikipediaService:
    """Service for interacting with the Wikipedia API."""

    def __init__(self, llm: ChatOpenAI):
        """Initialize the Wikipedia service.

        Args:
            llm: LangChain LLM instance
        """
        self.llm = llm
        self.base_url = "https://en.wikipedia.org/api/rest_v1"
        self.search_url = "https://en.wikipedia.org/w/api.php"
        self.analyzer_chain = self._create_query_analyzer_chain()
        self.wiki_history = {}  # Track Wikipedia topics queried by conversation_id

    def _create_query_analyzer_chain(self):
        """Creates a chain that decides if a query requires Wikipedia data"""
        template = """
        Analyze the following query and determine if it is asking for general knowledge, 
        film history, cultural context, thematic analysis or background information
        that would be best answered using Wikipedia.

        Query: {query}

        Response format (JSON):
        {{{{
          "needs_wikipedia_data": true/false,
          "search_terms": ["search term 1", "search term 2", ...],
          "is_movie_related": true/false,
          "explanation": "Brief explanation of why Wikipedia is or isn't relevant for this query"
        }}}}

        Examples:
        - For "What is the history of film noir?": {{"needs_wikipedia_data": true, "search_terms": ["film noir history"], "is_movie_related": true, "explanation": "This asks about film history which Wikipedia covers well"}}
        - For "Explain the cultural impact of Star Wars": {{"needs_wikipedia_data": true, "search_terms": ["Star Wars cultural impact"], "is_movie_related": true, "explanation": "This asks about cultural context which Wikipedia covers well"}}
        - For "What are the major themes in Pulp Fiction?": {{"needs_wikipedia_data": true, "search_terms": ["Pulp Fiction film themes analysis"], "is_movie_related": true, "explanation": "This asks about thematic analysis which Wikipedia covers well"}}
        - For "What is the plot of Inception?": {{"needs_wikipedia_data": false, "search_terms": [], "is_movie_related": true, "explanation": "This is better answered using TMDb as it's asking for basic movie information"}}
        - For "Who directed The Godfather?": {{"needs_wikipedia_data": false, "search_terms": [], "is_movie_related": true, "explanation": "This is asking for factual movie information best answered by TMDb"}}
        - For "What are the benefits of meditation?": {{"needs_wikipedia_data": true, "search_terms": ["meditation benefits"], "is_movie_related": false, "explanation": "This asks for general knowledge not related to movies"}}
        """

        prompt = PromptTemplate.from_template(template)
        return prompt | self.llm | StrOutputParser()

    def search_wikipedia(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Search Wikipedia for articles related to the query.

        Args:
            query: The search query
            limit: Maximum number of results to return

        Returns:
            List of search results
        """
        params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "srprop": "snippet",
        }

        try:
            response = requests.get(self.search_url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("query", {}).get("search", [])
        except requests.exceptions.HTTPError as err:
            print(f"HTTP Error: {err}")
            return []

    def fetch_article_content(self, page_title: str) -> Optional[Dict[str, Any]]:
        """Fetch the content of a Wikipedia article.

        Args:
            page_title: Title of the Wikipedia page

        Returns:
            Dictionary containing article content or None if not found
        """
        # First, get the normalized title and page ID
        params = {
            "action": "query",
            "format": "json",
            "titles": page_title,
            "prop": "info|extracts|pageimages",
            "inprop": "url",
            "exintro": 1,
            "explaintext": 1,
            "pithumbsize": 500,
        }

        try:
            response = requests.get(self.search_url, params=params)
            response.raise_for_status()
            data = response.json()

            # Extract the page data
            pages = data.get("query", {}).get("pages", {})
            if not pages or "-1" in pages:
                return None

            page_id = next(iter(pages))
            return pages[page_id]
        except requests.exceptions.HTTPError as err:
            print(f"HTTP Error: {err}")
            return None

    def create_citations(self, article_data: Dict[str, Any]) -> List[Citation]:
        """Create citations from Wikipedia article data.

        Args:
            article_data: Wikipedia article data

        Returns:
            List of Citation objects
        """
        if not article_data or "missing" in article_data:
            return []

        url = article_data.get(
            "fullurl", f"https://en.wikipedia.org/wiki/{article_data.get('title', '')}"
        )
        extract = article_data.get("extract", "No content available.")
        title = article_data.get("title", "Wikipedia article")

        return [Citation(text=extract, url=url, title=f"{title} - Wikipedia")]

    def extract_images(self, article_data: Dict[str, Any]) -> List[ImageData]:
        """Extract images from Wikipedia article data.

        Args:
            article_data: Wikipedia article data

        Returns:
            List of ImageData objects
        """
        images = []
        if not article_data or "missing" in article_data:
            return images

        # Extract the thumbnail if available
        if "thumbnail" in article_data:
            thumbnail = article_data["thumbnail"]
            title = article_data.get("title", "Wikipedia article")
            images.append(
                ImageData(
                    url=thumbnail.get("source", ""),
                    alt=f"{title} image",
                    caption=f"Image from Wikipedia article: {title}",
                )
            )

        return images

    async def process_wikipedia_query(
        self, query: str, conversation_id: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[List[Citation]], Optional[List[ImageData]]]:
        """Process a query, determine if Wikipedia data is needed, and fetch the relevant information.

        Args:
            query: User query
            conversation_id: Optional conversation ID to track query history

        Returns:
            Tuple containing:
            - Wikipedia data formatted as a string or None if not Wikipedia related
            - list of citations or None
            - list of images or None
        """
        # Initialize conversation history if it doesn't exist
        if conversation_id and conversation_id not in self.wiki_history:
            self.wiki_history[conversation_id] = []

        # Analyze if this query needs Wikipedia data
        analysis_result = await self.analyzer_chain.ainvoke({"query": query})

        try:
            # Parse the analysis
            analysis = json.loads(analysis_result)
            needs_wikipedia = analysis.get("needs_wikipedia_data", False)
            search_terms = analysis.get("search_terms", [])
            is_movie_related = analysis.get("is_movie_related", False)
            explanation = analysis.get("explanation", "")
        except Exception as e:
            print(f"Error parsing Wikipedia analysis result: {e}")
            return None, None, None

        # If we don't need Wikipedia data, return None
        if not needs_wikipedia or not search_terms:
            return None, None, None

        # Get the Wikipedia search results
        all_article_data = []
        all_citations = []
        all_images = []

        # Search for each term
        for term in search_terms:
            search_results = self.search_wikipedia(term)

            if not search_results:
                continue

            # Get the content for the top result
            top_result = search_results[0]
            article_data = self.fetch_article_content(top_result.get("title", ""))

            if not article_data:
                continue

            # Extract the article text
            article_text = article_data.get("extract", "")
            if not article_text:
                continue

            # Format the data
            formatted_data = f"Wikipedia information about '{article_data.get('title', '')}':\n{article_text}"
            all_article_data.append(formatted_data)

            # Create citations and extract images
            citations = self.create_citations(article_data)
            all_citations.extend(citations)

            images = self.extract_images(article_data)
            all_images.extend(images)

            # Add to history
            if conversation_id:
                self.wiki_history[conversation_id].append(article_data.get("title", ""))

        # If we couldn't find any data, return None
        if not all_article_data:
            return None, None, None

        # Format all the data as a single string
        formatted_data = "\n\n".join(all_article_data)

        # Return the raw data for further processing
        return formatted_data, all_citations, all_images
