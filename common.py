import html
import re
import time
from datetime import datetime

import requests

H = {"User-Agent": "estudo-coletor/0.1 (projeto pessoal de estudo)"}
TIMEOUT = 60  # threads grandes (Hacker News, Discourse) passavam dos 15 s antigos


def limpar(texto: str | None) -> str:
    # tira tags HTML e converte &amp; etc.
    return html.unescape(re.sub(r"<[^>]+>", " ", texto or "")).strip()


def ts(iso: str) -> int:
    # data ISO-8601 ("2024-01-31T10:00:00Z") -> segundos desde 1970
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp())


def palavras(query: str) -> list[str]:
    # "future of frontend" -> ["future", "frontend"] (ignora palavras de 1-2 letras como "of")
    return [w for w in re.findall(r"\w+", query.lower()) if len(w) > 2]


def tags_da_busca(query: str) -> list[str]:
    # Dev.to e Mastodon só buscam por tag. Tentamos a busca inteira colada
    # ("futureoffrontend") e cada palavra sozinha ("future", "frontend"), sem repetir.
    colada = "".join(re.findall(r"\w+", query.lower()))
    return list(dict.fromkeys([colada, *palavras(query)]))


def ranquear(itens: list[dict], texto_de, ps: list[str], desempate) -> list[dict]:
    """Ordena pelos posts que têm mais palavras da busca. Exige pelo menos 2 palavras
    (ou 1, se a busca só tem uma), para não trazer posts que casam só com "future"."""
    minimo = min(2, len(ps))
    pontuados = [(sum(p in texto_de(i).lower() for p in ps), i) for i in itens]
    validos = [x for x in pontuados if x[0] >= minimo]
    return [i for _, i in sorted(validos, key=lambda x: (x[0], desempate(x[1])), reverse=True)]


def pedir(metodo: str, url: str, **kw) -> dict | list:
    # Se o site responder 429 (muitas requisições), espera o que ele pedir e tenta de novo (até 3x).
    for tentativa in range(3):
        r = requests.request(metodo, url, headers=H, timeout=TIMEOUT, **kw)
        if r.status_code == 429 and tentativa < 2:
            espera = r.headers.get("Retry-After", "5")
            time.sleep(int(espera) if espera.isdigit() else 5)
            continue
        r.raise_for_status()
        return r.json()


def get(url: str, **params) -> dict | list:
    return pedir("GET", url, params=params)


def post(url: str, dados: dict) -> dict:
    # usado pelas APIs GraphQL (ex.: Stacker News), que recebem a consulta num POST
    return pedir("POST", url, json=dados)
