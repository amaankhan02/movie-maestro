import json
from typing import Any, Dict, List, Optional, Tuple

import requests
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from ..config import settings
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
        self.summarizer_chain = self._create_content_summarizer_chain()
        self.search_term_generator = self._create_search_term_generator()
        self.wiki_history = {}  # Track Wikipedia topics queried by conversation_id
        self.cache = {}  # Simple in-memory cache for Wikipedia articles

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

    def _create_content_summarizer_chain(self):
        """Creates a chain that summarizes Wikipedia content to extract the most relevant information"""
        template = """
        You are tasked with summarizing Wikipedia content to extract only the most relevant information 
        for the user's query. Focus on extracting key facts, details, and insights that directly answer 
        the question rather than including all information from the article.
        
        User query: {query}
        
        Wikipedia content: 
        {content}
        
        Provide a concise summary (max 300 words) that includes:
        1. The most relevant facts and information related to the query
        2. Key dates, people, events, or concepts if relevant
        3. Significant context needed to understand the topic
        
        Exclude:
        - Peripheral details not directly related to the query
        - Excessive background information
        - Redundant information
        
        Your summary:
        """

        prompt = PromptTemplate.from_template(template)
        return prompt | self.llm | StrOutputParser()

    def _create_search_term_generator(self):
        """Creates a chain that generates appropriate Wikipedia search terms for a query."""
        template = """
        Given a user query that needs Wikipedia information but lacks specific search terms,
        generate 1-3 effective search terms for Wikipedia that would find relevant articles.
        
        For movie-related queries requesting recommendations, lists, or general information,
        try to identify category articles, film genres, or specific topics that Wikipedia would have articles about.
        
        User query: {query}
        
        Examples:
        - For "what are good family movies", appropriate search terms might be ["family film", "children's film genre", "G-rated movies"]
        - For "action movies with car chases", appropriate search terms might be ["car chase sequences", "action film", "automotive action scenes"]
        - For "movies about time travel", appropriate search terms might be ["time travel in fiction", "time travel films", "science fiction film"]
        
        Respond with a JSON array of 1-3 search terms that would find relevant Wikipedia articles:
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
        # Check cache first
        cache_key = f"search:{query}"
        if cache_key in self.cache:
            return self.cache[cache_key]

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
            results = data.get("query", {}).get("search", [])

            # Cache the results
            self.cache[cache_key] = results
            return results
        except requests.exceptions.HTTPError as err:
            print(f"HTTP Error: {err}")
            return []

    def fetch_article_content(self, page_title: str) -> Optional[Dict[str, Any]]:
        """Fetch the content of a Wikipedia article using extended mode.

        Args:
            page_title: Title of the Wikipedia page

        Returns:
            Dictionary containing article content or None if not found
        """
        # Check cache first
        cache_key = f"article:{page_title}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Parameters for extended mode (intro + key sections)
        params = {
            "action": "query",
            "format": "json",
            "titles": page_title,
            "prop": "info|extracts|pageimages",
            "inprop": "url",
            "exsentences": 20,  # Get first 20 sentences (intro + a bit more)
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
            result = pages[page_id]

            # Cache the result
            self.cache[cache_key] = result
            return result
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
        """Process a query and fetch relevant information from Wikipedia.

        Args:
            query: User query
            conversation_id: Optional conversation ID to track query history

        Returns:
            Tuple containing:
            - Wikipedia data formatted as a string or None if not found
            - list of citations or None
            - list of images or None
        """
        # Initialize conversation history if it doesn't exist
        if conversation_id and conversation_id not in self.wiki_history:
            self.wiki_history[conversation_id] = []

        # Extract potential search terms directly from the query
        search_terms = []

        # Try to use the query directly as a search term
        clean_query = query.strip().rstrip("?")
        if len(clean_query.split()) <= 5:  # If the query is short enough
            search_terms.append(clean_query)

        # If no direct search terms or query is too long, generate search terms using LLM
        if not search_terms or len(clean_query.split()) > 5:
            try:
                print(f"Generating search terms with LLM for query: {query}")
                search_terms_result = await self.search_term_generator.ainvoke(
                    {"query": query}
                )

                # Parse the JSON array of search terms
                try:
                    generated_terms = json.loads(search_terms_result)
                    if generated_terms and isinstance(generated_terms, list):
                        search_terms = generated_terms
                        print(f"Generated search terms: {search_terms}")
                    else:
                        # If not a list or empty, try to extract from non-JSON text
                        fallback_terms = [
                            term.strip() for term in search_terms_result.split(",")
                        ]
                        fallback_terms = [term for term in fallback_terms if term]
                        if fallback_terms:
                            search_terms = fallback_terms
                            print(f"Extracted search terms from text: {search_terms}")
                except Exception as e:
                    # Fallback in case we don't get valid JSON
                    print(f"Error parsing generated search terms: {e}")
                    # Try to extract terms by splitting the text
                    fallback_terms = [
                        term.strip() for term in search_terms_result.split(",")
                    ]
                    fallback_terms = [term for term in fallback_terms if term]
                    if fallback_terms:
                        search_terms = fallback_terms
            except Exception as e:
                print(f"Error generating search terms: {e}")
                # Last fallback: use the query itself
                search_terms = [clean_query]

        # If we still have no search terms, return None
        if not search_terms:
            print("No search terms could be generated. Returning empty result.")
            return None, None, None

        print(f"Using extended mode for Wikipedia query: {query}")
        print(f"Search terms: {search_terms}")

        # Get the Wikipedia search results
        all_article_data = []
        all_citations = []
        all_images = []

        # Search for each term (limit to 2 terms maximum for faster processing)
        for term in search_terms[:2]:
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

            # Summarize the content to make it more concise and relevant
            if len(article_text.split()) > 150:
                try:
                    summarized_text = await self.summarizer_chain.ainvoke(
                        {"query": query, "content": article_text}
                    )
                    article_text = summarized_text
                except Exception as e:
                    print(f"Error summarizing Wikipedia content: {e}")
                    # Fall back to the original text if summarization fails

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
