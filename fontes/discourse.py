from urllib.parse import urlparse

from common import get, limpar, ts


def curtidas(post: dict) -> int:
    # no Discourse, a ação de id 2 é o "like"
    return sum(a.get("count", 0) for a in post.get("actions_summary", []) if a.get("id") == 2)


class Forum:
    """Qualquer fórum feito em Discourse. Para adicionar outro, basta uma linha no coletor.py:
    "godot": discourse.Forum("https://forum.godotengine.org")

    Obs.: o robots.txt dos fóruns Discourse pede que robôs não usem /search.
    Para uso pessoal, mantenha o volume baixo (poucos tópicos por vez).
    """

    def __init__(self, base: str, nome: str | None = None):
        self.base = base.rstrip("/")
        self.nome = nome or f"discourse/{urlparse(base).netloc}"

    def posts_do_topico(self, t: dict, max_comments: int) -> list[dict]:
        # O /t/{id}.json só traz os ~20 primeiros posts; o resto vem de 20 em 20 pelos ids do "stream".
        carregados = t["post_stream"]["posts"]
        ja = {p["id"] for p in carregados}
        faltam = [i for i in t["post_stream"]["stream"] if i not in ja]
        faltam = faltam[: max(0, max_comments + 1 - len(carregados))]
        for k in range(0, len(faltam), 20):
            lote = get(f"{self.base}/t/{t['id']}/posts.json", **{"post_ids[]": faltam[k:k + 20]})
            carregados += lote["post_stream"]["posts"]
        return sorted(carregados, key=lambda p: p["post_number"])

    def coletar(self, query: str, limit: int = 5, max_comments: int = 30) -> list[dict]:
        topicos = get(f"{self.base}/search.json", q=query).get("topics", [])[:limit]
        posts = []
        for tp in topicos:
            t = get(f"{self.base}/t/{tp['id']}.json")
            # post_type 1 = post normal; os outros são avisos automáticos ("tópico fechado" etc.)
            primeiro, *respostas = [p for p in self.posts_do_topico(t, max_comments) if p.get("post_type", 1) == 1]
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
                "source": self.nome,
                "id": str(t["id"]),
                "title": t["title"],
                "author": primeiro["username"],
                "url": f"{self.base}/t/{t['slug']}/{t['id']}",
                "score": t["like_count"],
                "created_utc": ts(t["created_at"]),
                "selftext": limpar(primeiro["cooked"]),
                "num_comments": t["posts_count"] - 1,
                "comments": comentarios[:max_comments],
            })
        return posts


# Fonte original do projeto: o fórum oficial do próprio Discourse.
padrao = Forum("https://meta.discourse.org", nome="discourse")


def coletar(query: str, limit: int = 5, max_comments: int = 30) -> list[dict]:
    return padrao.coletar(query, limit, max_comments)
