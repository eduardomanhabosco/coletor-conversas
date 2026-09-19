import argparse

import hn_client
from storage import salvar


parser = argparse.ArgumentParser(
    description="Coleta conversas sobre um tema e salva em JSON"
)

parser.add_argument("query")
parser.add_argument(
    "--limit",
    type=int,
    default=10,
    help="posts por fonte",
)
parser.add_argument(
    "--min-comments",
    type=int,
    default=0,
)
parser.add_argument(
    "--max-comments",
    type=int,
    default=30,
    help="comentários guardados por post",
)

args = parser.parse_args()

posts = hn_client.coletar(
    args.query,
    args.limit,
    args.max_comments,
)

posts = [
    post
    for post in posts
    if post["num_comments"] >= args.min_comments
]

caminho = salvar(
    args.query,
    vars(args),
    {"hackernews": posts},
)

print(f"{len(posts)} posts salvos em {caminho}")
