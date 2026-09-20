from common import get, limpar, palavras, ranquear, tags_da_busca, ts

BASE = "https://mastodon.social/api/v1"


def coletar(query: str, limit: int = 5, max_comments: int = 30) -> list[dict]:
    # Limite: a busca por texto exige login; só a linha do tempo de hashtag é pública.
    # Busca em cada tag da pesquisa (a busca colada e cada palavra), junta tudo sem repetir
    # e ranqueia pelas palavras da busca presentes no toot e nas hashtags dele.
    toots = {}
    for tag in tags_da_busca(query):
        for s in get(f"{BASE}/timelines/tag/{tag}", limit=40):
            toots[s["id"]] = s

    achados = ranquear(
        list(toots.values()),
        lambda s: f"{limpar(s['content'])} {' '.join(t['name'] for t in s['tags'])}",
        palavras(query),
        lambda s: s["favourites_count"],
    )

    posts = []
    for s in achados[:limit]:
        texto = limpar(s["content"])
        respostas = get(f"{BASE}/statuses/{s['id']}/context")["descendants"]
        prof = {s["id"]: -1}  # profundidade de cada toot; o post original conta como -1
        comentarios = []
        for r in respostas:
            prof[r["id"]] = prof.get(r["in_reply_to_id"], -1) + 1
            comentarios.append({
                "author": r["account"]["acct"],
                "score": r["favourites_count"],
                "body": limpar(r["content"]),
                "depth": prof[r["id"]],
            })
        posts.append({
            "source": "mastodon",
            "id": s["id"],
            "title": texto[:80],  # toot não tem título
            "author": s["account"]["acct"],
            "url": s["url"],
            "score": s["favourites_count"],
            "created_utc": ts(s["created_at"]),
            "selftext": texto,
            "num_comments": s["replies_count"],
            "comments": comentarios[:max_comments],
        })
    return posts
