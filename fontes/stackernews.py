import time

from common import com_progresso, palavras, passa, post, ranquear, ts

BASE = "https://stacker.news/api/graphql"
PROFUNDIDADE = 6  # GraphQL não tem recursão: pedimos respostas até 6 níveis
MAX_PAGINAS = 5  # cada página da busca traz ~21 itens (posts e comentários misturados)
CAMPOS = "id title url text createdAt ncomments sats user { name }"

BUSCA = f"""
query($q: String, $sort: String, $cursor: String, $when: String, $from: String, $to: String) {{
  search(q: $q, sort: $sort, cursor: $cursor, when: $when, from: $from, to: $to) {{
    cursor
    items {{ {CAMPOS} }}
  }}
}}"""


def campos_comentario(nivel: int) -> str:
    filhos = f" comments {{ comments {{ {campos_comentario(nivel - 1)} }} }}" if nivel > 1 else ""
    return f"id text sats user {{ name }}{filhos}"


ITEM = f"""
query($id: ID!) {{
  item(id: $id) {{
    {CAMPOS}
    comments(sort: "top") {{ comments {{ {campos_comentario(PROFUNDIDADE)} }} }}
  }}
}}"""


def achatar(nos: list[dict], depth: int = 0) -> list[dict]:
    saida = []
    for n in nos:
        saida.append({
            "author": (n.get("user") or {}).get("name"),
            "score": n.get("sats"),  # no Stacker News o "voto" é em sats (satoshis)
            "body": n.get("text") or "",
            "depth": depth,
        })
        saida += achatar((n.get("comments") or {}).get("comments", []), depth + 1)
    return saida


def coletar(
    query: str, limit: int = 5, max_comments: int = 30,
    desde: int | None = None, ate: int | None = None, min_comments: int = 0, ordem: str = "relevancia",
) -> list[dict]:
    # A busca devolve posts e comentários misturados; só os posts têm título.
    # Com data, a busca usa when="custom" e o período em milissegundos.
    variaveis = {"q": query, "sort": "new" if ordem == "recentes" else "match"}
    if desde is not None or ate is not None:
        variaveis |= {"when": "custom", "from": str((desde or 0) * 1000), "to": str((ate or int(time.time())) * 1000)}
    achados, cursor = [], None
    for _ in range(MAX_PAGINAS):
        r = post(BASE, {"query": BUSCA, "variables": {**variaveis, "cursor": cursor}})["data"]["search"]
        novos = [
            i for i in r["items"]
            if i["title"] and passa(ts(i["createdAt"]), i["ncomments"], desde, ate, min_comments)
        ]
        if ordem == "recentes":
            # O sort "new" casa qualquer palavra da busca ("bitcoin wallet" traz todo post de bitcoin):
            # ficamos só com os que têm as palavras no título ou no texto, do mais novo ao mais velho.
            novos = ranquear(novos, lambda i: f"{i['title']} {i.get('text') or ''}", palavras(query),
                             lambda i: i["createdAt"])
        achados += novos
        cursor = r["cursor"]
        if len(achados) >= limit or not cursor:
            break

    return com_progresso("stackernews", achados[:limit], lambda i: por_id(i["id"], max_comments))


def por_id(id: str, max_comments: int = 30) -> dict:
    i = post(BASE, {"query": ITEM, "variables": {"id": id}})["data"]["item"]
    return {
        "source": "stackernews",
        "id": i["id"],
        "title": i["title"],
        "author": (i.get("user") or {}).get("name"),
        "url": f"https://stacker.news/items/{i['id']}",
        "score": i["sats"],
        "created_utc": ts(i["createdAt"]),
        "selftext": i.get("text") or i.get("url") or "",  # post de link não tem texto
        "num_comments": i["ncomments"],
        "comments": achatar(i["comments"]["comments"])[:max_comments],
    }
