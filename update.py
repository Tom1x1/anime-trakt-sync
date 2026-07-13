import requests
import os
from datetime import datetime, timedelta
TRAKT_CLIENT_SECRET = os.getenv("TRAKT_CLIENT_SECRET")
TRAKT_REFRESH_TOKEN = os.getenv("TRAKT_REFRESH_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")
TRAKT_CLIENT_ID = os.getenv("TRAKT_CLIENT_ID")
TRAKT_ACCESS_TOKEN = os.getenv("TRAKT_ACCESS_TOKEN")
TRAKT_USERNAME = os.getenv("TRAKT_USERNAME")

def refresh_trakt_token():
    print("🔄 Renovando access token...")

    response = requests.post(
        "https://api.trakt.tv/oauth/token",
        json={
            "refresh_token": TRAKT_REFRESH_TOKEN,
            "client_id": TRAKT_CLIENT_ID,
            "client_secret": TRAKT_CLIENT_SECRET,
            "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
            "grant_type": "refresh_token"
        }
    )

    data = response.json()

    new_access_token = data["access_token"]
    new_refresh_token = data["refresh_token"]

    print("✅ Token renovado com sucesso!")

    # Atualiza o secret TRAKT_ACCESS_TOKEN no GitHub
    update_github_secret("TRAKT_ACCESS_TOKEN", new_access_token)
    update_github_secret("TRAKT_REFRESH_TOKEN", new_refresh_token)

    return new_access_token

def update_github_secret(secret_name, secret_value):
    import base64
    from nacl import encoding, public

    # Pega chave pública do repositório
    url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/actions/secrets/public-key"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    response = requests.get(url, headers=headers)
    public_key = response.json()["key"]
    key_id = response.json()["key_id"]

    # Criptografa o novo valor
    public_key_obj = public.PublicKey(public_key.encode(), encoding.Base64Encoder())
    sealed_box = public.SealedBox(public_key_obj)
    encrypted = sealed_box.encrypt(secret_value.encode())
    encrypted_value = base64.b64encode(encrypted).decode()

    # Atualiza secret
    url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/actions/secrets/{secret_name}"
    requests.put(
        url,
        headers=headers,
        json={
            "encrypted_value": encrypted_value,
            "key_id": key_id
        }
    )
    
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

print("✅ Listas atualizadas!")
