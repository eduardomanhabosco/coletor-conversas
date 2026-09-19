import re

from common import get, limpar, ts

BASE = "https://dev.to/api"


def achatar(nos: list[dict], depth: int = 0) -> list[dict]:
    saida = []
    for n in nos:
        saida.append({
            "author": n["user"]["name"],
            "score": None,  # a API não expõe score de comentário
            "body": limpar(n["body_html"]),
            "depth": depth,
        })
        saida += achatar(n["children"], depth + 1)
    return saida


def coletar(query: str, limit: int = 5, max_comments: int = 30) -> list[dict]:
    # Limite: a API não busca texto livre, só tag; "video editing" vira "videoediting"
    tag = re.sub(r"\W+", "", query.lower())
    posts = []
    for a in get(f"{BASE}/articles", tag=tag, per_page=min(limit, 1000)):
        posts.append({
            "source": "devto",
            "id": str(a["id"]),
            "title": a["title"],
            "author": a["user"]["name"],
            "url": a["url"],
            "score": a["public_reactions_count"],
            "created_utc": ts(a["published_timestamp"]),
            "selftext": a["description"],  # Limite: só o resumo; texto completo em /articles/{id}
            "num_comments": a["comments_count"],
            "comments": achatar(get(f"{BASE}/comments", a_id=a["id"]))[:max_comments],
        })
    return posts
