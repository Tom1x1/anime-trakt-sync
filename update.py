import requests
import os
from datetime import datetime, timedelta

TRAKT_CLIENT_ID = os.getenv("TRAKT_CLIENT_ID")
TRAKT_ACCESS_TOKEN = os.getenv("TRAKT_ACCESS_TOKEN")
TRAKT_USERNAME = os.getenv("TRAKT_USERNAME")

headers_trakt = {
    "Content-Type": "application/json",
    "trakt-api-version": "2",
    "trakt-api-key": TRAKT_CLIENT_ID,
    "Authorization": f"Bearer {TRAKT_ACCESS_TOKEN}"
}

def get_current_season():
    month = datetime.utcnow().month
    if month in [1,2,3]:
        return "WINTER"
    elif month in [4,5,6]:
        return "SPRING"
    elif month in [7,8,9]:
        return "SUMMER"
    else:
        return "FALL"

def fetch_anime(query):
    response = requests.post(
        "https://graphql.anilist.co",
        json={"query": query}
    )
    return response.json()["data"]["Page"]["media"]

def update_trakt_list(list_slug, anime_list):
    url = f"https://api.trakt.tv/users/{TRAKT_USERNAME}/lists/{list_slug}/items"
    
    # Limpar lista antes
    requests.delete(url, headers=headers_trakt)
    
    shows = []
    for anime in anime_list:
        if anime["idMal"]:
            shows.append({
                "ids": {"mal": anime["idMal"]}
            })

    requests.post(url, headers=headers_trakt, json={"shows": shows})

# ===============================
# animes-da-temporada
# ===============================

season = get_current_season()
year = datetime.utcnow().year

query_season = f"""
query {{
  Page(perPage: 50) {{
    media(season: {season}, seasonYear: {year}, type: ANIME) {{
      idMal
    }}
  }}
}}
"""

season_anime = fetch_anime(query_season)
update_trakt_list("animes-da-temporada", season_anime)

# ===============================
# proximos-lancamentos
# ===============================

query_upcoming = """
query {
  Page(perPage: 50) {
    media(status: NOT_YET_RELEASED, type: ANIME, sort: START_DATE) {
      idMal
    }
  }
}
"""

upcoming_anime = fetch_anime(query_upcoming)
update_trakt_list("proximos-lancamentos", upcoming_anime)

print("✅ Listas atualizadas!")
