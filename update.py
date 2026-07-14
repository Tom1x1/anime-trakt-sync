import requests
import os
from datetime import datetime, timedelta
TRAKT_ACCESS_TOKEN = os.getenv("TRAKT_ACCESS_TOKEN")
TRAKT_CLIENT_ID = os.getenv("TRAKT_CLIENT_ID")
TRAKT_USERNAME = os.getenv("TRAKT_USERNAME")
TRAKT_CLIENT_SECRET = os.getenv("TRAKT_CLIENT_SECRET")
TRAKT_REFRESH_TOKEN = os.getenv("TRAKT_REFRESH_TOKEN")

headers_trakt = {
    "Content-Type": "application/json",
    "trakt-api-version": "2",
    "trakt-api-key": TRAKT_CLIENT_ID,
    "Authorization": f"Bearer {TRAKT_ACCESS_TOKEN}"
}

def refresh_trakt_token():
    global TRAKT_ACCESS_TOKEN, headers_trakt

    print("🔄 Token expirado. Renovando...")

    response = requests.post(
        "https://api.trakt.tv/oauth/token",
        headers={"Content-Type": "application/json"},
        json={
            "refresh_token": TRAKT_REFRESH_TOKEN,
            "client_id": TRAKT_CLIENT_ID,
            "client_secret": TRAKT_CLIENT_SECRET,
            "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
            "grant_type": "refresh_token"
        }
    )

    if response.status_code != 200:
        print("❌ Erro ao renovar:", response.text)
        raise Exception("Falha ao renovar token")

    data = response.json()

    TRAKT_ACCESS_TOKEN = data["access_token"]

    headers_trakt["Authorization"] = f"Bearer {TRAKT_ACCESS_TOKEN}"

    print("✅ Token renovado com sucesso!")

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
    base_url = f"https://api.trakt.tv/users/{TRAKT_USERNAME}/lists/{list_slug}/items"

    shows = []

    # =============================
    # 1️⃣ Converter animes para IDs do Trakt
    # =============================
    for anime in anime_list:
        if anime.get("title") and anime["title"].get("romaji"):
            name = anime["title"]["romaji"]

            search = requests.get(
                "https://api.trakt.tv/search/show",
                headers=headers_trakt,
                params={"query": name}
            )

            if search.status_code == 401:
                refresh_trakt_token()
                search = requests.get(
                    "https://api.trakt.tv/search/show",
                    headers=headers_trakt,
                    params={"query": name}
                )

            results = search.json()

            if results:
                trakt_id = results[0]["show"]["ids"]["trakt"]
                shows.append({"ids": {"trakt": trakt_id}})

    print(f"🔄 Atualizando lista {list_slug} com {len(shows)} itens")

    # =============================
    # 2️⃣ Buscar itens atuais da lista
    # =============================
    current_items = requests.get(base_url, headers=headers_trakt)

    if current_items.status_code == 401:
        refresh_trakt_token()
        current_items = requests.get(base_url, headers=headers_trakt)

    current_data = current_items.json()

    # =============================
    # 3️⃣ Remover todos os itens atuais
    # =============================
    if current_data:
        items_to_remove = {
            "shows": [
                {"ids": {"trakt": item["show"]["ids"]["trakt"]}}
                for item in current_data
                if item.get("show")
            ]
        }

        print(f"🗑 Removendo {len(items_to_remove['shows'])} itens antigos")

        requests.post(
            base_url + "/remove",
            headers=headers_trakt,
            json=items_to_remove
        )

    # =============================
    # 4️⃣ Adicionar novos itens
    # =============================
    if shows:
        requests.post(
            base_url,
            headers=headers_trakt,
            json={"shows": shows}
        )

    print(f"✅ Lista {list_slug} atualizada com sucesso!\n")

            # Se token expirou
            if search.status_code == 401:
                refresh_trakt_token()
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
        response = requests.put(
            url,
            headers=headers_trakt,
            json={"shows": shows}
        )

        if response.status_code == 401:
            refresh_trakt_token()
            requests.post(
                url,
                headers=headers_trakt,
                json={"shows": shows}
            )

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

print("✅ Listas atualizadas!")
