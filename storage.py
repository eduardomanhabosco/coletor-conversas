import json
import re
from datetime import datetime, timezone
from pathlib import Path


def por_idioma(posts: list[dict]) -> dict:
    """Agrupa os posts pelo campo "lang": {"pt": {"post_count": 2, "posts": [...]}, ...}"""
    grupos: dict[str, list[dict]] = {}
    for post in posts:
        grupos.setdefault(post["lang"], []).append(post)
    return {
        lang: {"post_count": len(itens), "posts": itens}
        for lang, itens in grupos.items()
    }


def salvar(
    query: str,
    filters: dict,
    fontes: dict[str, list[dict]],
) -> Path:
    agora = datetime.now(timezone.utc)

    # formato: sources -> <fonte> -> languages -> <idioma> -> posts -> comments
    dados = {
        "query": query,
        "collected_at": agora.isoformat(),
        "filters": filters,
        "sources": {
            nome: {
                "post_count": len(posts),
                "languages": por_idioma(posts),
            }
            for nome, posts in fontes.items()
        },
    }

    slug = re.sub(r"\W+", "_", query.lower()).strip("_")

    Path("output").mkdir(exist_ok=True)

    caminho = Path("output") / f"{slug}_{agora:%Y%m%d_%H%M%S}.json"

    caminho.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return caminho
