"""Junta várias coletas num JSON só, sem posts repetidos.

python juntar.py output/a.json output/b.json -o output/junto.json
"""
import argparse
import json
from pathlib import Path

from storage import montar


def juntar(coletas: list[dict]) -> dict[str, list[dict]]:
    """{ fonte: [posts] } sem repetir (source, id). Cada post guarda em "matched_query"
    as buscas que o trouxeram; se o mesmo post veio em mais de uma, fica a 1ª cópia."""
    fontes: dict[str, dict[tuple, dict]] = {}
    for dados in coletas:
        for nome, fonte in dados["sources"].items():
            posts = fontes.setdefault(nome, {})
            for idioma in fonte["languages"].values():
                for p in idioma["posts"]:
                    # um arquivo já juntado traz a lista pronta
                    buscas = p.get("matched_query") or [dados["query"]]
                    guardado = posts.setdefault((p["source"], p["id"]), {**p, "matched_query": []})
                    guardado["matched_query"] += [b for b in buscas if b not in guardado["matched_query"]]
    return {nome: list(posts.values()) for nome, posts in fontes.items()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Junta coletas (JSONs do main.py) sem posts repetidos")
    parser.add_argument("arquivos", nargs="+", help="JSONs gerados pelo main.py")
    parser.add_argument("-o", "--saida", required=True, help="arquivo de saída, ex.: output/junto.json")
    args = parser.parse_args()

    coletas = [json.loads(Path(a).read_text(encoding="utf-8")) for a in args.arquivos]
    fontes = juntar(coletas)
    dados = montar(" + ".join(c["query"] for c in coletas), {"arquivos": args.arquivos}, fontes)

    Path(args.saida).parent.mkdir(parents=True, exist_ok=True)
    Path(args.saida).write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(len(p) for p in fontes.values())
    print(f"{total} posts únicos de {len(coletas)} arquivos, salvo em {args.saida}")
