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

    shows = []

    for anime in anime_list:
        if anime.get("title") and anime["title"].get("romaji"):
            name = anime["title"]["romaji"]

            search = requests.get(
                "https://api.trakt.tv/search/show",
                headers=headers_trakt,
                params={"query": name}
            )

            results = search.json()

            if results:
                trakt_id = results[0]["show"]["ids"]["trakt"]

                shows.append({
                    "ids": {"trakt": trakt_id}
                })

    print(f"Enviando {len(shows)} animes para {list_slug}")

    if len(shows) > 0:
        requests.post(url, headers=headers_trakt, json={"shows": shows})

# ===============================
# animes-da-temporada
# ===============================

season = get_current_season()
year = datetime.utcnow().year

query_season = f"""
query {{
  Page(perPage: 50) {{
    media(
      season: {season},
      seasonYear: {year},
      type: ANIME,
      status: RELEASING
    ) {{
      title {{
        romaji
      }}
    }}
  }}
}}
"""

season_anime = fetch_anime(query_season)
print(f"Temporada retornou {len(season_anime)} animes")
update_trakt_list("animes-da-temporada", season_anime)

# ===============================
# proximos-lancamentos
# ===============================

query_upcoming = """
query {
  Page(perPage: 50) {
    media(
      status: NOT_YET_RELEASED,
      type: ANIME,
      sort: START_DATE
    ) {
      title {
        romaji
      }
    }
  }
}
"""

upcoming_anime = fetch_anime(query_upcoming)
print(f"Upcoming retornou {len(upcoming_anime)} animes")
update_trakt_list("proximos-lancamentos", upcoming_anime)

# ===============================
# episodios-hoje
# ===============================

today_start = int(datetime.utcnow().replace(hour=0, minute=0, second=0).timestamp())
today_end = int(datetime.utcnow().replace(hour=23, minute=59, second=59).timestamp())

query_today = f"""
query {{
  Page(perPage: 50) {{
    airingSchedules(
      airingAt_greater: {today_start},
      airingAt_lesser: {today_end}
    ) {{
      media {{
        title {{
          romaji
        }}
      }}
    }}
  }}
}}
"""

response_today = requests.post(
    "https://graphql.anilist.co",
    json={"query": query_today}
)

today_data = response_today.json()["data"]["Page"]["airingSchedules"]

today_anime = [item["media"] for item in today_data]

print(f"Episódios hoje retornou {len(today_anime)} animes")

update_trakt_list("episodios-hoje", today_anime)

# ===============================
# estreias-da-semana
# ===============================

query_all_season = f"""
query {{
  Page(perPage: 50) {{
    media(
      season: {season},
      seasonYear: {year},
      type: ANIME
    ) {{
      title {{
        romaji
      }}
      startDate {{
        year
        month
        day
      }}
    }}
  }}
}}
"""

response_week = requests.post(
    "https://graphql.anilist.co",
    json={"query": query_all_season}
)

season_data = response_week.json()["data"]["Page"]["media"]

week_anime = []

seven_days_ago = datetime.utcnow() - timedelta(days=7)

for anime in season_data:
    sd = anime.get("startDate")
    if sd and sd["year"] and sd["month"] and sd["day"]:
        start_date = datetime(sd["year"], sd["month"], sd["day"])
        if start_date >= seven_days_ago:
            week_anime.append(anime)

print(f"Estreias semana retornou {len(week_anime)} animes")

update_trakt_list("estreias-da-semana", week_anime)

print("✅ Listas atualizadas!")
