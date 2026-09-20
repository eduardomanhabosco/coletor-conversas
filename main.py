import argparse

from coletor import FONTES, coletar_tudo
from storage import salvar


def lista(texto: str | None) -> list[str] | None:
    # "pt,en" -> ["pt", "en"]; sem valor -> None (significa "todos")
    return texto.split(",") if texto else None


parser = argparse.ArgumentParser(description="Coleta conversas sobre um tema e salva em JSON")

parser.add_argument("query")
parser.add_argument(
    "--sources",
    help=f"fontes separadas por vírgula (padrão: todas). Opções: {', '.join(FONTES)}",
)
parser.add_argument(
    "--se-sites",
    help="comunidades do Stack Exchange, separadas por vírgula (padrão: lista em fontes/stackexchange.py)",
)
parser.add_argument("--langs", help="idiomas a manter, separados por vírgula (ex.: pt,en). Padrão: todos")
parser.add_argument("--limit", type=int, default=10, help="posts por fonte")
parser.add_argument("--min-comments", type=int, default=0)
parser.add_argument("--max-comments", type=int, default=30, help="comentários guardados por post")
parser.add_argument("--since", help="só posts a partir desta data (AAAA-MM-DD)")
parser.add_argument("--until", help="só posts até esta data (AAAA-MM-DD)")

args = parser.parse_args()

try:
    resultado = coletar_tudo(
        args.query,
        sources=lista(args.sources),
        limit=args.limit,
        max_comments=args.max_comments,
        min_comments=args.min_comments,
        langs=lista(args.langs),
        se_sites=lista(args.se_sites),
        since=args.since,
        until=args.until,
    )
except ValueError as e:  # fonte desconhecida ou data inválida
    parser.error(str(e))

# Grava tudo num único JSON em output/ e mostra o caminho.
# vars(args) guarda os filtros usados dentro do próprio JSON.
caminho = salvar(args.query, vars(args), resultado)
print(f"salvo em {caminho}")
