from common import get, ts


class Instancia:
    """Uma instância Lemmy (ou PieFed, que copia a API do Lemmy com api="alpha").

    local=True busca só nas comunidades da própria instância. Isso evita o ruído
    da busca federada (posts de política etc. que só citam uma palavra da busca).
    """

    def __init__(self, dominio: str, local: bool = False, api: str = "v3", nome: str | None = None):
        self.dominio = dominio
        self.local = local
        self.base = f"https://{dominio}/api/{api}"
        self.nome = nome or f"lemmy/{dominio}"

    def comentarios(self, post_id: int, max_comments: int) -> list[dict]:
        # A API entrega no máximo 50 por página; vamos pedindo páginas até ter tudo.
        saida, vistos, pagina = [], set(), 1
        while len(saida) < max_comments:
            lote = get(
                f"{self.base}/comment/list",
                post_id=post_id, sort="Top", type_="All", limit=50, page=pagina,
            )["comments"]
            novos = [c for c in lote if c["comment"]["id"] not in vistos]
            if not novos:  # página vazia ou repetida: acabou
                break
            vistos.update(c["comment"]["id"] for c in novos)
            saida += novos
            if len(lote) < 50:
                break
            pagina += 1
        return saida[:max_comments]

    def coletar(self, query: str, limit: int = 5, max_comments: int = 30) -> list[dict]:
        achados = get(
            f"{self.base}/search",
            q=query, type_="Posts", sort="TopAll", limit=min(limit, 50),
            listing_type="Local" if self.local else "All",
        )["posts"]
        posts = []
        for x in achados:
            p = x["post"]
            posts.append({
                "source": self.nome,
                "id": str(p["id"]),
                "title": p.get("name") or p.get("title"),  # Lemmy usa "name"; PieFed, "title"
                "author": nome_de(x["creator"]),
                "url": p.get("ap_id") or f"https://{self.dominio}/post/{p['id']}",
                "score": x["counts"]["score"],
                "created_utc": ts(p["published"]),
                "selftext": p.get("body") or "",
                "num_comments": x["counts"]["comments"],
                "comments": [
                    {
                        "author": nome_de(c["creator"]),
                        "score": c["counts"]["score"],
                        "body": c["comment"].get("content") or c["comment"].get("body") or "",
                        "depth": c["comment"].get("path", "0.x").count(".") - 1,  # path = "0.id.id..."
                    }
                    for c in self.comentarios(p["id"], max_comments)
                    if not (c["comment"].get("deleted") or c["comment"].get("removed"))
                ],
            })
        return posts


def nome_de(usuario: dict) -> str | None:
    return usuario.get("name") or usuario.get("user_name")  # PieFed usa "user_name"


# Fonte original do projeto: lemmy.world, buscando em todo o fediverso.
padrao = Instancia("lemmy.world", nome="lemmy")


def coletar(query: str, limit: int = 5, max_comments: int = 30) -> list[dict]:
    return padrao.coletar(query, limit, max_comments)
