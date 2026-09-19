import argparse

from fontes import devto, discourse, hackernews, lemmy, mastodon, stackexchange
from idioma import detectar
from storage import salvar

FONTES = {
    "hackernews": hackernews,
    "lemmy": lemmy,
    "stackexchange": stackexchange,
    "devto": devto,
    "mastodon": mastodon,
    "discourse": discourse,
}

parser = argparse.ArgumentParser(description="Coleta conversas sobre um tema e salva em JSON")

parser.add_argument("query")
parser.add_argument(
    "--sources",
    default=",".join(FONTES),
    help="fontes separadas por vírgula (padrão: todas)",
)
parser.add_argument(
    "--se-sites",
    help="comunidades do Stack Exchange, separadas por vírgula (padrão: lista em fontes/stackexchange.py)",
)
parser.add_argument(
    "--langs",
    help="idiomas a manter, separados por vírgula (ex.: pt,en). Padrão: todos",
)
parser.add_argument("--limit", type=int, default=10, help="posts por fonte")
parser.add_argument("--min-comments", type=int, default=0)
parser.add_argument("--max-comments", type=int, default=30, help="comentários guardados por post")

args = parser.parse_args()

# Resultado final: { "hackernews": [posts...], "lemmy": [posts...], ... }
resultado = {}

# --sources chega como texto ("hackernews,lemmy"); split(",") vira uma lista
# e o for passa por uma fonte de cada vez.
for nome in args.sources.split(","):
    # Nome que não existe em FONTES (ex.: erro de digitação): para o programa
    # e mostra as opções válidas.
    if nome not in FONTES:
        parser.error(f"fonte desconhecida: {nome} (use: {', '.join(FONTES)})")

    # Só o Stack Exchange aceita a opção extra "sites". Se o usuário passou
    # --se-sites, vira lista ("pt.stackoverflow,ux" -> ["pt.stackoverflow", "ux"]).
    # Nas outras fontes, "extra" fica vazio e não muda nada.
    extra = {"sites": args.se_sites.split(",")} if nome == "stackexchange" and args.se_sites else {}

    try:
        # FONTES[nome] é o módulo da fonte (ex.: fontes/lemmy.py). Chama o
        # coletar() dele; o ** entrega o "extra" como argumentos nomeados.
        posts = FONTES[nome].coletar(args.query, args.limit, args.max_comments, **extra)
    except Exception as e:
        # Fonte fora do ar ou bloqueada: avisa e segue para a próxima,
        # assim uma fonte com problema não derruba as outras.
        print(f"{nome}: FALHOU ({type(e).__name__}: {e})")
        continue

    # Mantém só os posts com comentários suficientes (--min-comments).
    posts = [p for p in posts if p["num_comments"] >= args.min_comments]

    # Detecta o idioma de cada post e, se --langs foi passado, descarta os outros.
    for p in posts:
        p["lang"] = detectar(p)
    if args.langs:
        posts = [p for p in posts if p["lang"] in args.langs.split(",")]

    resultado[nome] = posts
    print(f"{nome}: {len(resultado[nome])} posts")

# Grava tudo num único JSON em output/ e mostra o caminho.
# vars(args) guarda os filtros usados dentro do próprio JSON.
caminho = salvar(args.query, vars(args), resultado)
print(f"salvo em {caminho}")
