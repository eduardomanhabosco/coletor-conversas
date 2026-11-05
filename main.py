import argparse

import common
from coletor import FONTES, coletar_ids, coletar_tudo
from storage import salvar


def lista(texto: str | None) -> list[str] | None:
    # "pt,en" -> ["pt", "en"]; sem valor -> None (significa "todos")
    return texto.split(",") if texto else None


parser = argparse.ArgumentParser(description="Coleta conversas sobre um tema e salva em JSON")

parser.add_argument("query", nargs="?", help="o tema da busca (opcional com --ids)")
parser.add_argument(
    "--ids",
    help="posts já conhecidos, sem busca: fonte:id separados por vírgula (ex.: hackernews:50338728,python:12345)",
)
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
parser.add_argument(
    "--sort", choices=["relevancia", "recentes"], default="relevancia",
    help="relevancia (padrão) ou recentes (os mais novos primeiro)",
)
parser.add_argument(
    "--delay", type=float, default=0,
    help="segundos de pausa antes de cada pedido a um site (padrão: 0); use se um site pedir calma (429)",
)

args = parser.parse_args()
if not args.query and not args.ids:
    parser.error("informe o tema da busca ou --ids")
common.ATRASO = args.delay

try:
    if args.ids:
        resultado = coletar_ids(lista(args.ids), max_comments=args.max_comments)
    else:
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
            sort=args.sort,
        )
except ValueError as e:  # fonte desconhecida, id ou data inválida
    parser.error(str(e))

# Grava tudo num único JSON em output/ e mostra o caminho (com --ids, ids_<data>.json).
# vars(args) guarda os filtros usados dentro do próprio JSON.
caminho = salvar(args.query or "ids", vars(args), resultado)
print(f"salvo em {caminho}")
