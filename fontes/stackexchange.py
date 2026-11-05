import os

from common import avisar, get, limpar

BASE = "https://api.stackexchange.com/2.3"
# comunidades padrão; lista completa em https://api.stackexchange.com/2.3/sites
SITES = ["stackoverflow", "pt.stackoverflow", "softwareengineering", "codereview", "ux", "pm"]
# Chave opcional (registre um app em https://stackapps.com/apps/oauth/register): sobe a cota
# de 300 para 10.000 pedidos por dia. Sem ela, o requests simplesmente não envia o parâmetro.
CHAVE = os.environ.get("STACKEXCHANGE_KEY") or None


def api(caminho: str, **params) -> dict:
    r = get(f"{BASE}/{caminho}", key=CHAVE, **params)
    if r.get("quota_remaining", 999) < 20:
        avisar(f"stackexchange: restam só {r['quota_remaining']} pedidos hoje (a STACKEXCHANGE_KEY sobe a cota)")
    return r


def buscar_respostas(site: str, ids: list[int]) -> dict[int, list[dict]]:
    """Busca as respostas de várias perguntas de uma vez: { id_da_pergunta: [respostas] }.

    A API aceita até 100 ids separados por ";" numa chamada só. Isso poupa a cota
    diária (300 pedidos sem chave), que 1 chamada por pergunta gastaria rápido.
    """
    por_pergunta: dict[int, list[dict]] = {}
    for pagina in range(1, 6):  # Limite: até 5 páginas de 100 respostas por comunidade
        r = api(
            f"questions/{';'.join(map(str, ids))}/answers",
            site=site, sort="votes", order="desc", pagesize=100, page=pagina, filter="withbody",
        )
        for a in r["items"]:
            por_pergunta.setdefault(a["question_id"], []).append(a)
        if not r["has_more"]:
            break
    return por_pergunta


def coletar_site(
    site: str, query: str, limit: int, max_comments: int,
    desde: int | None = None, ate: int | None = None, min_comments: int = 0, ordem: str = "relevancia",
) -> list[dict]:
    # Os filtros vão na própria busca (o requests não envia os parâmetros que valem None).
    perguntas = api(
        "search/advanced",
        q=query, site=site, sort="creation" if ordem == "recentes" else "relevance", order="desc",
        pagesize=min(limit, 100), filter="withbody",
        fromdate=desde, todate=ate, answers=min_comments or None,
    )["items"]
    if not perguntas:
        return []

    # aqui os "comentários" são as respostas, da mais votada para a menos
    respostas = buscar_respostas(site, [q["question_id"] for q in perguntas])
    return [montar_post(site, q, respostas.get(q["question_id"], []), max_comments) for q in perguntas]


def por_id(id: str, max_comments: int = 30) -> dict:
    # "12345" (no Stack Overflow) ou "<comunidade>/12345", ex.: "pt.stackoverflow/12345"
    site, _, numero = id.rpartition("/")
    site = site or "stackoverflow"
    q = api(f"questions/{numero}", site=site, filter="withbody")["items"][0]
    return montar_post(site, q, buscar_respostas(site, [q["question_id"]]).get(q["question_id"], []), max_comments)


def montar_post(site: str, q: dict, respostas: list[dict], max_comments: int) -> dict:
    return {
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
                "accepted": a.get("is_accepted", False),  # a resposta que quem perguntou aceitou
            }
            for a in respostas[:max_comments]
        ],
    }


def coletar(
    query: str, limit: int = 5, max_comments: int = 30, sites: list[str] | None = None, **filtros,
) -> list[dict]:
    posts = []
    for site in sites or SITES:
        try:
            posts += coletar_site(site, query, limit, max_comments, **filtros)
        except Exception as e:  # um site inválido/fora do ar não derruba os outros
            avisar(f"stackexchange/{site}: FALHOU ({type(e).__name__})")
    return posts
