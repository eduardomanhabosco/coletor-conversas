from common import com_progresso, get, limpar, palavras, passa, ranquear, tags_da_busca, ts

BASE = "https://mastodon.social/api/v1"
PAGINAS = 5  # páginas de 40 toots por hashtag


def toots_da_tag(tag: str, desde: int | None = None) -> list[dict]:
    # A timeline vem do mais novo para o mais velho, 40 por vez; o max_id (último toot da página)
    # pede a página seguinte. Para antes se já passou da data "desde".
    toots, max_id = [], None
    for _ in range(PAGINAS):
        lote = get(f"{BASE}/timelines/tag/{tag}", limit=40, max_id=max_id)
        toots += lote
        if len(lote) < 40 or (desde is not None and ts(lote[-1]["created_at"]) < desde):
            break
        max_id = lote[-1]["id"]
    return toots


def coletar(
    query: str, limit: int = 5, max_comments: int = 30,
    desde: int | None = None, ate: int | None = None, min_comments: int = 0, ordem: str = "relevancia",
) -> list[dict]:
    # Limite: a busca por texto exige login; só a linha do tempo de hashtag é pública.
    # Busca em cada tag da pesquisa (a busca colada e cada palavra), junta tudo sem repetir
    # e ranqueia pelas palavras da busca presentes no toot e nas hashtags dele.
    toots = {}
    for tag in tags_da_busca(query):
        for s in toots_da_tag(tag, desde):
            toots[s["id"]] = s

    achados = ranquear(
        # a API não filtra: filtramos antes de baixar as respostas
        [s for s in toots.values() if passa(ts(s["created_at"]), s["replies_count"], desde, ate, min_comments)],
        lambda s: f"{limpar(s['content'])} {' '.join(t['name'] for t in s['tags'])}",
        palavras(query),
        # desempate: as curtidas ou, em "recentes", a data
        (lambda s: s["created_at"]) if ordem == "recentes" else (lambda s: s["favourites_count"]),
    )

    return com_progresso("mastodon", achados[:limit], lambda s: montar_post(s, max_comments))


def por_id(id: str, max_comments: int = 30) -> dict:
    return montar_post(get(f"{BASE}/statuses/{id}"), max_comments)


def montar_post(s: dict, max_comments: int) -> dict:
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
    return {
        "source": "mastodon",
        "id": s["id"],
        "title": " ".join(texto.split())[:80],  # toot não tem título; a 1ª parte do texto, numa linha
        "author": s["account"]["acct"],
        "url": s["url"],
        "score": s["favourites_count"],
        "created_utc": ts(s["created_at"]),
        "selftext": texto,
        "num_comments": s["replies_count"],
        "comments": comentarios[:max_comments],
    }
