from common import com_progresso, conta, get, palavras, passa, ranquear, ts


class Instancia:
    """Uma instância Lemmy (ou PieFed, que copia a API do Lemmy com api="alpha").

    local=True busca só nas comunidades da própria instância. Isso evita o ruído
    da busca federada (posts de política etc. que só citam uma palavra da busca).
    estrito=True (padrão) fica só com os posts que têm as palavras da busca no título.
    """

    def __init__(
        self, dominio: str, local: bool = False, api: str = "v3", nome: str | None = None, estrito: bool = True,
    ):
        self.dominio = dominio
        self.local = local
        self.base = f"https://{dominio}/api/{api}"
        self.nome = nome or f"lemmy/{dominio}"
        self.estrito = estrito

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

    def coletar(
        self, query: str, limit: int = 5, max_comments: int = 30,
        desde: int | None = None, ate: int | None = None, min_comments: int = 0, ordem: str = "relevancia",
    ) -> list[dict]:
        # A API não filtra por data nem por comentários: com filtro (ou na busca estrita, que
        # também descarta posts), pedimos o máximo (50) e filtramos antes de baixar os comentários.
        filtrando = desde is not None or ate is not None or min_comments > 0 or self.estrito
        achados = get(
            f"{self.base}/search",
            q=query, type_="Posts", sort="New" if ordem == "recentes" else "TopAll",
            limit=50 if filtrando else min(limit, 50),
            listing_type="Local" if self.local else "All",
        )["posts"]
        achados = [
            x for x in achados
            if passa(ts(x["post"]["published"]), x["counts"]["comments"], desde, ate, min_comments)
        ]
        if self.estrito:
            # A busca da API casa as palavras em qualquer parte do post ("which database" trazia
            # posts de política). Exigimos as palavras no título; o corpo desempata e, depois, vale
            # a ordem da API.
            ps = palavras(query)
            achados = ranquear(achados, lambda x: titulo(x["post"]), ps, lambda x: conta(ps, x["post"].get("body") or ""))
        return com_progresso(self.nome, achados[:limit], lambda x: self.montar_post(x, max_comments))

    def por_id(self, id: str, max_comments: int = 30) -> dict:
        # o id é o número do post nesta instância (o da URL https://lemmy.world/post/<id>)
        return self.montar_post(get(f"{self.base}/post", id=id)["post_view"], max_comments)

    def montar_post(self, x: dict, max_comments: int) -> dict:
        # x é o "post_view" da API: post, creator e counts
        p = x["post"]
        return {
            "source": self.nome,
            "id": str(p["id"]),
            "title": titulo(p),
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
        }


def titulo(post: dict) -> str:
    return post.get("name") or post.get("title") or ""  # Lemmy usa "name"; PieFed, "title"


def nome_de(usuario: dict) -> str | None:
    return usuario.get("name") or usuario.get("user_name")  # PieFed usa "user_name"


# Fonte original do projeto: lemmy.world, buscando em todo o fediverso.
padrao = Instancia("lemmy.world", nome="lemmy")


def coletar(query: str, limit: int = 5, max_comments: int = 30, **filtros) -> list[dict]:
    return padrao.coletar(query, limit, max_comments, **filtros)


def por_id(id: str, max_comments: int = 30) -> dict:
    return padrao.por_id(id, max_comments)
