from datetime import datetime, timezone
from urllib.parse import urlparse

from common import com_progresso, get, limpar, passa, ts


def dia(segundos: int) -> str:
    # 1735689600 -> "2025-01-01", o formato dos filtros after:/before: da busca
    return datetime.fromtimestamp(segundos, timezone.utc).strftime("%Y-%m-%d")


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

    def coletar(
        self, query: str, limit: int = 5, max_comments: int = 30,
        desde: int | None = None, ate: int | None = None, min_comments: int = 0, ordem: str = "relevancia",
    ) -> list[dict]:
        # Os filtros vão na própria busca (com 1 dia de folga, para não perder o dia da borda).
        # A busca é por post: um tópico antigo com resposta nova também vem, por isso
        # filtramos de novo pela data do tópico antes de baixá-lo.
        q = query
        if desde is not None:
            q += f" after:{dia(desde - 86400)}"
        if ate is not None:
            q += f" before:{dia(ate + 1)}"
        if min_comments:
            q += f" min_posts:{min_comments + 1}"  # o 1º post do tópico também conta
        if ordem == "recentes":
            q += " order:latest"
        topicos = [
            tp for tp in get(f"{self.base}/search.json", q=q).get("topics", [])
            if passa(ts(tp["created_at"]), tp["posts_count"] - 1, desde, ate, min_comments)
        ][:limit]
        return com_progresso(self.nome, topicos, lambda tp: self.por_id(tp["id"], max_comments))

    def por_id(self, id: str | int, max_comments: int = 30) -> dict:
        # o id é o número do tópico (o da URL .../t/<slug>/<id>)
        t = get(f"{self.base}/t/{id}.json")
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
        return {
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
        }


# Fonte original do projeto: o fórum oficial do próprio Discourse.
padrao = Forum("https://meta.discourse.org", nome="discourse")


def coletar(query: str, limit: int = 5, max_comments: int = 30, **filtros) -> list[dict]:
    return padrao.coletar(query, limit, max_comments, **filtros)


def por_id(id: str, max_comments: int = 30) -> dict:
    return padrao.por_id(id, max_comments)
