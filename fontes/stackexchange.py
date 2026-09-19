from common import get, limpar

BASE = "https://api.stackexchange.com/2.3"
# comunidades padrão; lista completa em https://api.stackexchange.com/2.3/sites
SITES = ["stackoverflow", "pt.stackoverflow", "softwareengineering", "codereview", "ux", "pm"]


def coletar_site(site: str, query: str, limit: int, max_comments: int) -> list[dict]:
    perguntas = get(
        f"{BASE}/search/advanced",
        q=query, site=site, sort="relevance", order="desc",
        pagesize=min(limit, 100), filter="withbody",
    )["items"]
    posts = []
    for q in perguntas:
        # aqui os "comentários" são as respostas, da mais votada para a menos
        respostas = get(
            f"{BASE}/questions/{q['question_id']}/answers",
            site=site, sort="votes", order="desc",
            pagesize=min(max_comments, 100), filter="withbody",
        )["items"]
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
                for a in respostas
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
