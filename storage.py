import json
import re
from datetime import datetime, timezone
from pathlib import Path


def salvar(
    query: str,
    filters: dict,
    fontes: dict[str, list[dict]],
) -> Path:
    agora = datetime.now(timezone.utc)

    dados = {
        "query": query,
        "collected_at": agora.isoformat(),
        "filters": filters,
        "sources": {
            nome: {
                "post_count": len(posts),
                "posts": posts,
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
