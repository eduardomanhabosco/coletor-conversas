from common import com_progresso, get, limpar

BASE = "https://hn.algolia.com/api/v1"


def achatar(no: dict, depth: int = 0) -> list[dict]:
    # transforma a árvore de comentários numa lista simples, com a profundidade
    saida = []

    for filho in no.get("children", []):
        if filho.get("text"):  # ignora comentários apagados
            saida.append({
                "author": filho.get("author"),
                "score": None,  # HN não expõe score de comentário
                "body": limpar(filho["text"]),
                "depth": depth,
            })

        saida += achatar(filho, depth + 1)

    return saida


def coletar(
    query: str, limit: int = 5, max_comments: int = 30,
    desde: int | None = None, ate: int | None = None, min_comments: int = 0, ordem: str = "relevancia",
) -> list[dict]:
    # Os filtros vão na própria busca, então o limit conta só os posts que passam neles.
    filtros = [f"num_comments>={min_comments}"]
    if desde is not None:
        filtros.append(f"created_at_i>={desde}")
    if ate is not None:
        filtros.append(f"created_at_i<={ate}")
    busca = "search_by_date" if ordem == "recentes" else "search"
    hits = get(
        f"{BASE}/{busca}", query=query, tags="story", hitsPerPage=limit, numericFilters=",".join(filtros),
    )["hits"]

    # o num_comments da busca é o que o HN informa (conta também os apagados)
    return com_progresso(
        "hackernews", hits,
        lambda hit: {**por_id(hit["objectID"], max_comments), "num_comments": hit["num_comments"]},
    )


def por_id(id: str, max_comments: int = 30) -> dict:
    # o /items/{id} traz o post e a árvore inteira de comentários
    item = get(f"{BASE}/items/{id}")  # get já faz raise_for_status e tenta de novo em 429
    comentarios = achatar(item)
    return {
        "source": "hackernews",
        "id": str(item["id"]),
        "title": item.get("title") or "",
        "author": item.get("author"),
        "url": f"https://news.ycombinator.com/item?id={item['id']}",
        "score": item.get("points"),
        "created_utc": item["created_at_i"],
        "selftext": limpar(item.get("text")),
        "num_comments": len(comentarios),
        "comments": comentarios[:max_comments],
    }
