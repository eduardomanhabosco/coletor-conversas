import re

from common import get, limpar, ts

BASE = "https://mastodon.social/api/v1"


def coletar(query: str, limit: int = 5, max_comments: int = 30) -> list[dict]:
    # Limite: só busca por hashtag (a busca por texto exige login); "video editing" vira "videoediting"
    tag = re.sub(r"\W+", "", query.lower())
    posts = []
    for s in get(f"{BASE}/timelines/tag/{tag}", limit=min(limit, 40)):
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
