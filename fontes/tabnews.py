from common import com_progresso, get, palavras, passa, ranquear, ts

BASE = "https://www.tabnews.com.br/api/v1"
PAGINAS_NOVOS = 10  # Limite: a API não tem busca; olhamos os ~1.000 posts mais novos + os "relevantes"


def achatar(nos: list[dict], depth: int = 0) -> list[dict]:
    saida = []
    for n in nos:
        saida.append({
            "author": n["owner_username"],
            "score": n["tabcoins"],
            "body": n.get("body") or "",  # Markdown
            "depth": depth,
        })
        saida += achatar(n.get("children", []), depth + 1)
    return saida


def coletar(
    query: str, limit: int = 5, max_comments: int = 30,
    desde: int | None = None, ate: int | None = None, min_comments: int = 0, ordem: str = "relevancia",
) -> list[dict]:
    # Junta as listas "relevant" e "new" sem repetir e ranqueia pelas palavras da busca no título.
    # Em "recentes", só a lista "new", com o desempate pela data em vez dos tabcoins.
    recentes = ordem == "recentes"
    listas = (("new", PAGINAS_NOVOS),) if recentes else (("relevant", 2), ("new", PAGINAS_NOVOS))
    conteudos = {}
    for estrategia, paginas in listas:
        for pagina in range(1, paginas + 1):
            lote = get(f"{BASE}/contents", strategy=estrategia, page=pagina, per_page=100)
            for c in lote:
                if c.get("type", "content") == "content":  # ignora anúncios ("ad")
                    conteudos[c["id"]] = c
            if len(lote) < 100:
                break

    achados = ranquear(
        # a API não filtra: filtramos antes de baixar o corpo e os comentários
        [c for c in conteudos.values()
         if passa(ts(c["published_at"] or c["created_at"]), c["children_deep_count"], desde, ate, min_comments)],
        lambda c: c["title"] or "",
        palavras(query),
        (lambda c: c["published_at"] or c["created_at"]) if recentes else (lambda c: c["tabcoins"]),
    )

    return com_progresso(
        "tabnews", achados[:limit], lambda c: por_id(f"{c['owner_username']}/{c['slug']}", max_comments),
    )


def por_id(id: str, max_comments: int = 30) -> dict:
    # No TabNews o post é identificado por "usuario/slug", como na URL.
    caminho = f"{BASE}/contents/{id}"
    c = get(caminho)  # a listagem não traz o corpo; o conteúdo completo traz tudo
    return {
        "source": "tabnews",
        "id": c["id"],
        "title": c["title"],
        "author": c["owner_username"],
        "url": f"https://www.tabnews.com.br/{c['owner_username']}/{c['slug']}",
        "score": c["tabcoins"],
        "created_utc": ts(c["published_at"] or c["created_at"]),
        "selftext": c.get("body") or "",
        "num_comments": c["children_deep_count"],
        "comments": achatar(get(f"{caminho}/children"))[:max_comments],
    }
