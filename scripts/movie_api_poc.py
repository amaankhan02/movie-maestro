import json
import os

import requests


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
    url = f"https://api.themoviedb.org/3/search/movie"
    params = {"api_key": api_key, "query": query}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as err:
        print(f"HTTP Error: {err}")
        return None


TMDB_API_KEY = ""
MOVIE_ID = 157336  # Interstellar

# # Fetch and prepare data


def test_fetch_tmdb_data():
    movie_data = fetch_tmdb_data(TMDB_API_KEY, MOVIE_ID)
    # print(movie_data)
    
    # this isn't actually json data just write to a text file
    document = (
        f"Title: {movie_data['title']}\n"
        f"Overview: {movie_data['overview']}\n"
        f"Director: {[crew['name'] for crew in movie_data['credits']['crew'] if crew['job'] == 'Director']}\n"
        f"Cast: {[member['name'] for member in movie_data['credits']['cast'][:5]]}\n"
        f"Themes: {[kw['name'] for kw in movie_data['keywords']['keywords']]}\n"
        f"Watch Providers: {movie_data['watch/providers']['results']['US']['flatrate']}"
        # Watch Providers actually shows a 'logo_path' field for different providers, so you can probably embed that as well if you want
    )

    with open("movie_test.txt", "w", encoding="utf-8") as f:
        f.write(document)


def test_search_tmdb():
    data = search_tmdb(TMDB_API_KEY, "interstellar")
    # Write directly to file with UTF-8 encoding
    with open("search_test.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    test_fetch_tmdb_data()
    # test_search_tmdb()
