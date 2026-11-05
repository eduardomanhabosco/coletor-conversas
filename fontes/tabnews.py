import unicodedata

from common import get, palavras, ranquear, ts

BASE = "https://www.tabnews.com.br/api/v1"
PAGINAS_NOVOS = 10  # Limite: a API não tem busca; olhamos os ~1.000 posts mais novos + os "relevantes"


def sem_acento(texto: str) -> str:
    # "programação" -> "programacao", para a busca casar com ou sem acento
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


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


def coletar(query: str, limit: int = 5, max_comments: int = 30) -> list[dict]:
    # Junta as listas "relevant" e "new" sem repetir e ranqueia pelas palavras da busca no título.
    conteudos = {}
    for estrategia, paginas in (("relevant", 2), ("new", PAGINAS_NOVOS)):
        for pagina in range(1, paginas + 1):
            lote = get(f"{BASE}/contents", strategy=estrategia, page=pagina, per_page=100)
            for c in lote:
                if c.get("type", "content") == "content":  # ignora anúncios ("ad")
                    conteudos[c["id"]] = c
            if len(lote) < 100:
                break

    achados = ranquear(
        list(conteudos.values()),
        lambda c: sem_acento(c["title"] or ""),
        [sem_acento(p) for p in palavras(query)],
        lambda c: c["tabcoins"],
    )

    posts = []
    for c in achados[:limit]:
        caminho = f"{BASE}/contents/{c['owner_username']}/{c['slug']}"
        completo = get(caminho)
        posts.append({
            "source": "tabnews",
            "id": c["id"],
            "title": c["title"],
            "author": c["owner_username"],
            "url": f"https://www.tabnews.com.br/{c['owner_username']}/{c['slug']}",
            "score": c["tabcoins"],
            "created_utc": ts(c["published_at"] or c["created_at"]),
            "selftext": completo.get("body") or "",
            "num_comments": c["children_deep_count"],
            "comments": achatar(get(f"{caminho}/children"))[:max_comments],
        })
    return posts
