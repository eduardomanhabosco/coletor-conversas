from common import get, limpar, ts

BASE = "https://meta.discourse.org"  # Limite: um fórum só; trocar BASE para outro Discourse


def curtidas(post: dict) -> int:
    # no Discourse, a ação de id 2 é o "like"
    return sum(a.get("count", 0) for a in post.get("actions_summary", []) if a.get("id") == 2)


def coletar(query: str, limit: int = 5, max_comments: int = 30) -> list[dict]:
    topicos = get(f"{BASE}/search.json", q=query).get("topics", [])[:limit]
    posts = []
    for tp in topicos:
        t = get(f"{BASE}/t/{tp['id']}.json")
        # Limite: a API devolve só os ~20 primeiros posts do tópico
        primeiro, *respostas = t["post_stream"]["posts"]
        prof = {}
        comentarios = []
        for p in respostas:
            pai = p.get("reply_to_post_number")
            prof[p["post_number"]] = prof[pai] + 1 if pai in prof else 0
            comentarios.append({
                "author": p["username"],
                "score": curtidas(p),
                "body": limpar(p["cooked"]),
                "depth": prof[p["post_number"]],
            })
        posts.append({
            "source": "discourse",
            "id": str(t["id"]),
            "title": t["title"],
            "author": primeiro["username"],
            "url": f"{BASE}/t/{t['slug']}/{t['id']}",
            "score": t["like_count"],
            "created_utc": ts(t["created_at"]),
            "selftext": limpar(primeiro["cooked"]),
            "num_comments": t["posts_count"] - 1,
            "comments": comentarios[:max_comments],
        })
    return posts
