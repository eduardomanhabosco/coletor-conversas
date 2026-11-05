import html
import re
import threading
import time
import unicodedata
from datetime import datetime

import requests

H = {"User-Agent": "estudo-coletor/0.1 (projeto pessoal de estudo)"}
TIMEOUT = 60  # threads grandes (Hacker News, Discourse) passavam dos 15 s antigos
# Pausa (em segundos) antes de cada pedido; o main.py preenche com o --delay. Com as fontes em
# paralelo, vale para cada fonte, ou seja, para cada site.
ATRASO = 0.0
_trava = threading.Lock()
CURTAS = {"go", "ai", "ia", "ui", "ux", "js", "ts", "c#", "r"}  # termos de 1-2 letras que contam na busca
# Palavras comuns que não dizem o tema: "which database" tem que casar com "database", não com "which".
COMUNS = {
    "the", "and", "for", "with", "which", "what", "how", "why", "who", "when", "where", "are", "was",
    "can", "does", "should", "from", "that", "this", "your", "you", "about", "into", "than", "have", "has",
    "que", "para", "com", "uma", "como", "qual", "quais", "por", "dos", "das", "nos", "nas", "pelo",
    "pela", "sobre", "mais", "sem", "isso", "esse", "essa", "este", "esta", "quando", "onde", "porque",
}


def limpar(texto: str | None) -> str:
    # Tira as tags HTML e converte &amp; etc., mas mantém parágrafos, itens de lista e
    # blocos de código em linhas separadas (o HN separa parágrafos só com <p>).
    texto = re.sub(r"<p(\s[^>]*)?>", "\n\n", texto or "", flags=re.I)
    texto = re.sub(r"<li(\s[^>]*)?>", "\n- ", texto, flags=re.I)
    texto = re.sub(r"<br\s*/?>|</(p|pre|div|blockquote|h[1-6])>", "\n", texto, flags=re.I)
    texto = html.unescape(re.sub(r"<[^>]+>", "", texto))
    texto = re.sub(r"[ \t]+\n", "\n", texto)  # só o espaço no fim da linha; o recuo do código fica
    return re.sub(r"\n{3,}", "\n\n", texto).strip()


def ts(iso: str) -> int:
    # data ISO-8601 ("2024-01-31T10:00:00Z") -> segundos desde 1970
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp())


def sem_acento(texto: str) -> str:
    # "programação" -> "programacao", para a busca casar com ou sem acento
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def passa(criado: int, num_comments: int, desde: int | None, ate: int | None, min_comments: int) -> bool:
    # Filtros de data (em segundos, como o created_utc) e de comentários. As fontes aplicam antes
    # de baixar os comentários, para o --limit contar só os posts que ficam.
    return (desde is None or criado >= desde) and (ate is None or criado <= ate) and num_comments >= min_comments


def palavras(query: str) -> list[str]:
    # "future of frontend" -> ["future", "frontend"]: ignora palavras de 1-2 letras como "of",
    # menos os termos de CURTAS ("Go", "AI"...) e siglas escritas em maiúsculas ("QA", "PR"),
    # e as palavras de COMUNS ("which", "como"...).
    termos = re.findall(r"\w+[#+]*", query)  # o [#+]* mantém "C#" e "C++" inteiros
    return [
        t.lower() for t in termos
        if (len(t) > 2 or t.lower() in CURTAS or (len(t) == 2 and t.isupper())) and t.lower() not in COMUNS
    ]


def tags_da_busca(query: str) -> list[str]:
    # Dev.to e Mastodon só buscam por tag. Tentamos a busca inteira colada
    # ("futureoffrontend") e cada palavra sozinha ("future", "frontend"), sem repetir.
    # Tag não tem "#" nem "+", então "c#" e "c++" ficam de fora.
    colada = "".join(re.findall(r"\w+", query.lower()))
    return list(dict.fromkeys([colada, *(p for p in palavras(query) if p.isalnum())]))


def casa(palavra: str, texto: str) -> bool:
    # Palavra inteira: "java" não casa "javascript". Não dá para usar \b, que falha depois do "#" de "c#".
    return re.search(rf"(?<!\w){re.escape(palavra)}(?!\w)", texto) is not None


def conta(ps: list[str], texto: str) -> int:
    # quantas palavras da busca aparecem inteiras no texto, sem ligar para acento e maiúsculas
    texto = sem_acento(texto).lower()
    return sum(casa(sem_acento(p), texto) for p in ps)


def ranquear(itens: list[dict], texto_de, ps: list[str], desempate) -> list[dict]:
    """Ordena pelos posts que têm mais palavras da busca (inteiras e sem acento). Exige pelo menos
    2 palavras (ou 1, se a busca só tem uma), para não trazer posts que casam só com "future".
    Em empate total, fica a ordem original (o sorted é estável mesmo com reverse=True)."""
    minimo = min(2, len(ps))
    pontuados = [(conta(ps, texto_de(i)), i) for i in itens]
    validos = [x for x in pontuados if x[0] >= minimo]
    return [i for _, i in sorted(validos, key=lambda x: (x[0], desempate(x[1])), reverse=True)]


def avisar(texto: str):
    # As fontes rodam em paralelo: a trava evita linhas misturadas no terminal, e o flush
    # mostra o andamento na hora.
    with _trava:
        print(texto, flush=True)


def com_progresso(nome: str, itens: list, montar) -> list[dict]:
    # Monta um post por item mostrando o andamento, já que cada post pode levar vários pedidos.
    posts = []
    for n, item in enumerate(itens, 1):
        posts.append(montar(item))
        avisar(f"{nome}: post {n}/{len(itens)} ({len(posts[-1]['comments'])} comentários)")
    return posts


def pedir(metodo: str, url: str, **kw) -> dict | list:
    # Se o site responder 429 (muitas requisições), espera o que ele pedir e tenta de novo (até 3x).
    for tentativa in range(3):
        if ATRASO:
            time.sleep(ATRASO)
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
