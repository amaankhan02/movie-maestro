import json
from typing import Any, Dict, List, Tuple

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI


class QueryRouterService:
    """Service for routing queries to appropriate data sources."""

    def __init__(self, llm: ChatOpenAI):
        """Initialize the query router service.

        Args:
            llm: LangChain LLM instance
        """
        self.llm = llm
        self.router_chain = self._create_router_chain()

    def _create_router_chain(self):
        """Creates a chain that decides which data source(s) to use for a query"""
        template = """
        Determine which data source(s) would be most appropriate to answer this movie-related query:

        Query: {query}

        Available sources:
        1. TMDB API - Best for factual information about specific movies, actors, directors, release dates, ratings, 
           and basic movie details like cast, crew, and plot.
        2. Wikipedia - Best for background information, film history, cultural context, thematic analysis, and 
           general film knowledge, for comparing movies, or recommending movies. Wikipedia is also best for open ended questions, and should
           be used unless the query is about a specific movie or director/actor.

        For each source, evaluate if it's needed to answer the query comprehensively.
        General rules:
        - If the query is only about a specific movie, director, or actors information, or only involves a very basic comparison use TMDB.
        - If the query involves intermediate or advanced comparison or more open ended questions, use Wikipedia as well with TMDb.

        Response format (JSON):
        {{{{
          "tmdb": {{{{
            "needed": true/false,
            "explanation": "Brief explanation why TMDB is needed or not needed"
          }}}},
          "wikipedia": {{{{
            "needed": true/false,
            "explanation": "Brief explanation why Wikipedia is needed or not needed"
          }}}}
        }}}}

        Examples:
        - For "What is the plot of Inception?": 
          {{"tmdb": {{"needed": true, "explanation": "TMDB is needed for basic plot information"}}, 
            "wikipedia": {{"needed": false, "explanation": "Wikipedia not needed for basic plot details of only one movie"}}}}
        
        - For "Compare Cars with Toy Story":
          {{"tmdb": {{"needed": true, "explanation": "TMDB is needed for basic plot information"}}, 
            "wikipedia": {{"needed": false, "explanation": "Wikipedia not needed for comparing basic details of movies"}}}}
        
        - For "What are some movies similar in plot to The Dark Knight?": 
          {{"tmdb": {{"needed": true, "explanation": "TMDB is needed for plot information when a movie is provided."}}, 
            "wikipedia": {{"needed": true, "explanation": "Wikipedia is needed when comparing movies or for open ended questions like this."}}}}
        
        - For "What is the history of science fiction films?": 
          {{"tmdb": {{"needed": false, "explanation": "TMDB isn't needed for film history context"}}, 
            "wikipedia": {{"needed": true, "explanation": "Wikipedia is needed for film history information and for open ended questions."}}}}
        
        - For "Who directed The Dark Knight and what themes does it explore?": 
          {{"tmdb": {{"needed": true, "explanation": "TMDB needed for director information"}}, 
            "wikipedia": {{"needed": true, "explanation": "Wikipedia needed for thematic analysis"}}}}
        
        - For "What are Christopher Nolan's films?": 
          {{"tmdb": {{"needed": true, "explanation": "TMDB needed for filmography information"}}, 
            "wikipedia": {{"needed": false, "explanation": "Wikipedia not needed for a basic question involving just one director."}}}}
            
        - For "How did Pulp Fiction impact cinema?": 
          {{"tmdb": {{"needed": true, "explanation": "TMDB needed for basic film info"}}, 
            "wikipedia": {{"needed": true, "explanation": "Wikipedia needed for cultural impact analysis, theme, and/or advanced plot details and information."}}}}
        """

        prompt = PromptTemplate.from_template(template)
        return prompt | self.llm | StrOutputParser()

    async def route_query(self, query: str) -> Dict[str, bool]:
        """Route a query to the appropriate data sources.

        Args:
            query: The user query

        Returns:
            Dictionary specifying which data sources to use
        """
        try:
            router_result = await self.router_chain.ainvoke({"query": query})
            analysis = json.loads(router_result)

            # Extract routing decisions
            use_tmdb = analysis.get("tmdb", {}).get("needed", False)
            use_wikipedia = analysis.get("wikipedia", {}).get("needed", False)

            # Return routing decisions
            return {"use_tmdb": use_tmdb, "use_wikipedia": use_wikipedia}
        except Exception as e:
            print(f"Error in query router: {e}")
            # Default to using both sources if there's an error
            return {"use_tmdb": True, "use_wikipedia": True}
