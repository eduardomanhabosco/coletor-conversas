import os
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import common
from coletor import FONTES, coletar_ids, coletar_tudo
from storage import montar

app = FastAPI(title="Coletor de conversas")

# O navegador só deixa o front chamar esta API se ela avisar que aceita o endereço dele.
# É isso que o CORS faz. Padrão: o Vite (localhost:5173); outros endereços vão na variável
# CORS_ORIGINS, separados por vírgula.
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Para o front montar os checkboxes: site, idioma principal e como a fonte busca.
DETALHES = {
    "hackernews": ("news.ycombinator.com", "en", "texto"),
    "lemmy": ("lemmy.world", "en", "texto, com as palavras no título"),
    "stackexchange": ("stackexchange.com", "en", "texto"),
    "devto": ("dev.to", "en", "tags"),
    "mastodon": ("mastodon.social", "en", "hashtags"),
    "discourse": ("meta.discourse.org", "en", "texto"),
    "stackernews": ("stacker.news", "en", "texto"),
    "tabnews": ("tabnews.com.br", "pt", "palavras no título dos posts recentes"),
    "programmingdev": ("programming.dev", "en", "texto, com as palavras no título"),
    "lemmybr": ("lemmy.eco.br", "pt", "texto, com as palavras no título"),
    "python": ("discuss.python.org", "en", "texto"),
    "freecodecamp": ("forum.freecodecamp.org", "en", "texto"),
    "openai": ("community.openai.com", "en", "texto"),
    "rust": ("users.rust-lang.org", "en", "texto"),
    "cursor": ("forum.cursor.com", "en", "texto"),
}


def lista(texto: str | None) -> list[str] | None:
    # "pt,en" -> ["pt", "en"]; sem valor -> None (significa "todos")
    return texto.split(",") if texto else None


@app.get("/fontes")
def listar_fontes() -> list[str]:
    """Nomes das fontes disponíveis (o front usa para montar os checkboxes)."""
    return list(FONTES)


@app.get("/fontes/detalhes")
def detalhar_fontes() -> list[dict]:
    """Nome, site, idioma principal e tipo de busca de cada fonte."""
    return [
        {"nome": nome, "site": site, "idioma": idioma, "busca": busca}
        for nome, (site, idioma, busca) in DETALHES.items()
    ]


@app.get("/coletar")
def coletar(
    query: str | None = None,
    ids: str | None = None,
    sources: str | None = None,
    se_sites: str | None = None,
    langs: str | None = None,
    limit: int = 10,
    min_comments: int = 0,
    max_comments: int = 30,
    since: str | None = None,
    until: str | None = None,
    sort: Literal["relevancia", "recentes"] = "relevancia",
    delay: float = 0,
) -> dict:
    """Roda a coleta e devolve o mesmo JSON que o main.py grava em output/.
    Com ids (fonte:id separados por vírgula), coleta esses posts direto e a query fica opcional."""
    if not query and not ids:
        raise HTTPException(status_code=400, detail="informe query ou ids")
    # ponytail: o delay é global no processo; duas coletas ao mesmo tempo usam o da última
    common.ATRASO = delay
    try:
        if ids:
            resultado = coletar_ids(lista(ids), max_comments=max_comments)
        else:
            resultado = coletar_tudo(
                query,
                sources=lista(sources),
                limit=limit,
                max_comments=max_comments,
                min_comments=min_comments,
                langs=lista(langs),
                se_sites=lista(se_sites),
                since=since,
                until=until,
                sort=sort,
            )
    except ValueError as e:  # fonte desconhecida, id ou data inválida
        raise HTTPException(status_code=400, detail=str(e))

    filtros = {
        "ids": ids, "sources": sources, "se_sites": se_sites, "langs": langs, "limit": limit,
        "min_comments": min_comments, "max_comments": max_comments, "since": since, "until": until,
        "sort": sort, "delay": delay,
    }
    return montar(query or "ids", filtros, resultado)
