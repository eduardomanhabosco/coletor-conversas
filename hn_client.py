import html
import json
import re
import sys

import requests

H = {"User-Agent": "estudo-coletor/0.1 (projeto pessoal de estudo)"}
BASE = "https://hn.algolia.com/api/v1"


def limpar(texto: str | None) -> str:
    # tira tags HTML e converte &amp; etc.
    return html.unescape(re.sub(r"<[^>]+>", " ", texto or "")).strip()


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


def coletar(query: str, limit: int = 5, max_comments: int = 30) -> list[dict]:
    r = requests.get(
        f"{BASE}/search",
        headers=H,
        timeout=15,
        params={
            "query": query,
            "tags": "story",
            "hitsPerPage": limit,
        },
    )
    r.raise_for_status()

    posts = []

    for hit in r.json()["hits"]:
        rid = hit["objectID"]

        item = requests.get(
            f"{BASE}/items/{rid}",
            headers=H,
            timeout=15,
        ).json()

        posts.append({
            "source": "hackernews",
            "id": rid,
            "title": hit["title"],
            "author": hit["author"],
            "url": f"https://news.ycombinator.com/item?id={rid}",
            "score": hit["points"],
            "created_utc": hit["created_at_i"],
            "selftext": limpar(item.get("text")),
            "num_comments": hit["num_comments"],
            "comments": achatar(item)[:max_comments],
        })

    return posts


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "video editing"

    print(
        json.dumps(
            coletar(q, limit=2, max_comments=3),
            ensure_ascii=False,
            indent=2,
        )
    )