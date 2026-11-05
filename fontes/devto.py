from common import com_progresso, get, limpar, palavras, passa, ranquear, tags_da_busca, ts

BASE = "https://dev.to/api"


def achatar(nos: list[dict], depth: int = 0) -> list[dict]:
    saida = []
    for n in nos:
        saida.append({
            "author": n["user"].get("name") or n["user"].get("username"),  # usuário apagado vem sem nome
            "score": None,  # a API não expõe score de comentário
            "body": limpar(n["body_html"]),
            "depth": depth,
        })
        saida += achatar(n["children"], depth + 1)
    return saida


def coletar(
    query: str, limit: int = 5, max_comments: int = 30,
    desde: int | None = None, ate: int | None = None, min_comments: int = 0, ordem: str = "relevancia",
) -> list[dict]:
    # Limite: a API pública não tem busca por texto, só por tag. Busca em cada tag da
    # pesquisa (a busca colada e cada palavra), junta tudo sem repetir e ranqueia pelas
    # palavras da busca presentes no título, resumo e tags.
    # Por tag vêm os 100 mais novos (quase sem comentários) e os 100 mais populares do último ano.
    artigos = {}
    for tag in tags_da_busca(query):
        for extra in ({}, {"top": 365}):
            for a in get(f"{BASE}/articles", tag=tag, per_page=100, **extra):
                artigos[a["id"]] = a

    achados = ranquear(
        # a API não filtra: filtramos antes de baixar os comentários
        [a for a in artigos.values()
         if passa(ts(a["published_timestamp"]), a["comments_count"], desde, ate, min_comments)],
        lambda a: f"{a['title']} {a['description']} {a.get('tag_list', '')}",
        palavras(query),
        # desempate: as reações ou, em "recentes", a data
        (lambda a: a["published_timestamp"]) if ordem == "recentes" else (lambda a: a["public_reactions_count"]),
    )

    return com_progresso("devto", achados[:limit], lambda a: por_id(a["id"], max_comments))


def por_id(id: str | int, max_comments: int = 30) -> dict:
    # A listagem só traz o resumo; o artigo completo (body_markdown) vem de /articles/{id}.
    a = get(f"{BASE}/articles/{id}")
    return {
        "source": "devto",
        "id": str(a["id"]),
        "title": a["title"],
        "author": a["user"].get("name") or a["user"].get("username"),
        "url": a["url"],
        "score": a["public_reactions_count"],
        "created_utc": ts(a["published_timestamp"]),
        "selftext": a.get("body_markdown") or a["description"],
        "num_comments": a["comments_count"],
        "comments": achatar(get(f"{BASE}/comments", a_id=a["id"]))[:max_comments],
    }
