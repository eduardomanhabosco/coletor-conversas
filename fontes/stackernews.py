from common import post, ts

BASE = "https://stacker.news/api/graphql"
PROFUNDIDADE = 6  # GraphQL não tem recursão: pedimos respostas até 6 níveis
MAX_PAGINAS = 5  # cada página da busca traz ~21 itens (posts e comentários misturados)

BUSCA = """
query($q: String, $cursor: String) {
  search(q: $q, sort: "match", cursor: $cursor) {
    cursor
    items { id title url text createdAt ncomments sats user { name } }
  }
}"""


def campos_comentario(nivel: int) -> str:
    filhos = f" comments {{ comments {{ {campos_comentario(nivel - 1)} }} }}" if nivel > 1 else ""
    return f"id text sats user {{ name }}{filhos}"


ITEM = f"""
query($id: ID!) {{
  item(id: $id) {{ comments(sort: "top") {{ comments {{ {campos_comentario(PROFUNDIDADE)} }} }} }}
}}"""


def achatar(nos: list[dict], depth: int = 0) -> list[dict]:
    saida = []
    for n in nos:
        saida.append({
            "author": (n.get("user") or {}).get("name"),
            "score": n.get("sats"),  # no Stacker News o "voto" é em sats (satoshis)
            "body": n.get("text") or "",
            "depth": depth,
        })
        saida += achatar((n.get("comments") or {}).get("comments", []), depth + 1)
    return saida


def coletar(query: str, limit: int = 5, max_comments: int = 30) -> list[dict]:
    # A busca devolve posts e comentários misturados; só os posts têm título.
    achados, cursor = [], None
    for _ in range(MAX_PAGINAS):
        r = post(BASE, {"query": BUSCA, "variables": {"q": query, "cursor": cursor}})["data"]["search"]
        achados += [i for i in r["items"] if i["title"]]
        cursor = r["cursor"]
        if len(achados) >= limit or not cursor:
            break

    posts = []
    for i in achados[:limit]:
        item = post(BASE, {"query": ITEM, "variables": {"id": i["id"]}})["data"]["item"]
        posts.append({
            "source": "stackernews",
            "id": i["id"],
            "title": i["title"],
            "author": (i.get("user") or {}).get("name"),
            "url": f"https://stacker.news/items/{i['id']}",
            "score": i["sats"],
            "created_utc": ts(i["createdAt"]),
            "selftext": i.get("text") or i.get("url") or "",  # post de link não tem texto
            "num_comments": i["ncomments"],
            "comments": achatar(item["comments"]["comments"])[:max_comments],
        })
    return posts
