from common import get, limpar

BASE = "https://api.stackexchange.com/2.3"
# comunidades padrão; lista completa em https://api.stackexchange.com/2.3/sites
SITES = ["stackoverflow", "pt.stackoverflow", "softwareengineering", "codereview", "ux", "pm"]


def buscar_respostas(site: str, ids: list[int]) -> dict[int, list[dict]]:
    """Busca as respostas de várias perguntas de uma vez: { id_da_pergunta: [respostas] }.

    A API aceita até 100 ids separados por ";" numa chamada só. Isso poupa a cota
    diária (300 pedidos sem chave), que 1 chamada por pergunta gastaria rápido.
    """
    por_pergunta: dict[int, list[dict]] = {}
    for pagina in range(1, 6):  # Limite: até 5 páginas de 100 respostas por comunidade
        r = get(
            f"{BASE}/questions/{';'.join(map(str, ids))}/answers",
            site=site, sort="votes", order="desc", pagesize=100, page=pagina, filter="withbody",
        )
        for a in r["items"]:
            por_pergunta.setdefault(a["question_id"], []).append(a)
        if not r["has_more"]:
            break
    return por_pergunta


def coletar_site(site: str, query: str, limit: int, max_comments: int) -> list[dict]:
    perguntas = get(
        f"{BASE}/search/advanced",
        q=query, site=site, sort="relevance", order="desc",
        pagesize=min(limit, 100), filter="withbody",
    )["items"]
    if not perguntas:
        return []

    # aqui os "comentários" são as respostas, da mais votada para a menos
    respostas = buscar_respostas(site, [q["question_id"] for q in perguntas])

    posts = []
    for q in perguntas:
        posts.append({
            "source": f"stackexchange/{site}",
            "id": str(q["question_id"]),
            "title": limpar(q["title"]),
            "author": q.get("owner", {}).get("display_name"),
            "url": q["link"],
            "score": q["score"],
            "created_utc": q["creation_date"],
            "selftext": limpar(q.get("body")),
            "num_comments": q["answer_count"],
            "comments": [
                {
                    "author": a.get("owner", {}).get("display_name"),
                    "score": a["score"],
                    "body": limpar(a.get("body")),
                    "depth": 0,
                }
                for a in respostas.get(q["question_id"], [])[:max_comments]
            ],
        })
    return posts


def coletar(query: str, limit: int = 5, max_comments: int = 30, sites: list[str] = SITES) -> list[dict]:
    posts = []
    for site in sites:
        try:
            posts += coletar_site(site, query, limit, max_comments)
        except Exception as e:  # um site inválido/fora do ar não derruba os outros
            print(f"  stackexchange/{site}: FALHOU ({type(e).__name__})")
    return posts
