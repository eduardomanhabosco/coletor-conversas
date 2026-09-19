import requests

  # Identificação honesta: dizemos quem somos, sem fingir ser navegador
H = {"User-Agent": "estudo-coletor/0.1 (projeto pessoal de estudo)"}

  # (nome, url, chave da lista dentro do JSON; None = o JSON já é a lista)
FONTES = [
      ("Hacker News", "https://hn.algolia.com/api/v1/search?query=video+editing&tags=comment&hitsPerPage=3", "hits"),
      ("Stack Exchange", "https://api.stackexchange.com/2.3/search/advanced?q=video+editing&site=stackoverflow&pagesize=3", "items"),
      ("Lemmy", "https://lemmy.world/api/v3/search?q=video+editing&type_=Comments&limit=3", "comments"),
      ("Mastodon", "https://mastodon.social/api/v1/timelines/tag/videoediting?limit=3", None),
      ("Dev.to", "https://dev.to/api/articles?tag=videoediting&per_page=3", None),
      ("Bluesky", "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts?q=video+editing&limit=3", "posts"),
      ("Discourse", "https://meta.discourse.org/search.json?q=video", "posts"),
  ]

for nome, url, chave in FONTES:
      try:
          r = requests.get(url, headers=H, timeout=15)
          tipo = r.headers.get("content-type", "")[:30]
          try:
              d = r.json()
              n = len(d[chave]) if chave else len(d)
              print(f"{nome}: {r.status_code} {tipo} -> {n} itens")
          except ValueError:
              print(f"{nome}: {r.status_code} {tipo} -> NÃO veio JSON")
      except Exception as e:
          print(f"{nome}: FALHOU ({type(e).__name__})")