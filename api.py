from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from coletor import FONTES, coletar_tudo
from storage import montar

app = FastAPI(title="Coletor de conversas")

# O navegador só deixa o front (localhost:5173, o endereço do Vite) chamar esta API
# se ela avisar que aceita esse endereço. É isso que o CORS faz.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


def lista(texto: str | None) -> list[str] | None:
    # "pt,en" -> ["pt", "en"]; sem valor -> None (significa "todos")
    return texto.split(",") if texto else None


@app.get("/fontes")
def listar_fontes() -> list[str]:
    """Nomes das fontes disponíveis (o front usa para montar os checkboxes)."""
    return list(FONTES)


@app.get("/coletar")
def coletar(
    query: str,
    sources: str | None = None,
    se_sites: str | None = None,
    langs: str | None = None,
    limit: int = 10,
    min_comments: int = 0,
    max_comments: int = 30,
    since: str | None = None,
    until: str | None = None,
) -> dict:
    """Roda a coleta e devolve o mesmo JSON que o main.py grava em output/."""
    try:
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
        )
    except ValueError as e:  # fonte desconhecida ou data inválida
        raise HTTPException(status_code=400, detail=str(e))

    filtros = {
        "sources": sources, "se_sites": se_sites, "langs": langs, "limit": limit,
        "min_comments": min_comments, "max_comments": max_comments, "since": since, "until": until,
    }
    return montar(query, filtros, resultado)
