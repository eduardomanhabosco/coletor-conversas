from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from common import avisar, passa
from fontes import devto, discourse, hackernews, lemmy, mastodon, stackernews, stackexchange, tabnews
from idioma import detectar

FONTES = {
    "hackernews": hackernews,
    "lemmy": lemmy,
    "stackexchange": stackexchange,
    "devto": devto,
    "mastodon": mastodon,
    "discourse": discourse,
    # fóruns abertos (sem login) adicionados depois
    "stackernews": stackernews,
    "tabnews": tabnews,
    "programmingdev": lemmy.Instancia("programming.dev", local=True),
    "lemmybr": lemmy.Instancia("lemmy.eco.br", local=True),
    "python": discourse.Forum("https://discuss.python.org"),
    "freecodecamp": discourse.Forum("https://forum.freecodecamp.org"),
    "openai": discourse.Forum("https://community.openai.com"),
    "rust": discourse.Forum("https://users.rust-lang.org"),
    "cursor": discourse.Forum("https://forum.cursor.com"),
}


def para_timestamp(dia: str, fim_do_dia: bool = False) -> int:
    """"2026-09-19" -> segundos desde 1970 (UTC). Com fim_do_dia=True, vale 23:59:59 desse dia."""
    try:
        t = datetime.strptime(dia, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        raise ValueError(f"data inválida: {dia!r} (use AAAA-MM-DD)") from None
    return int(t.timestamp()) + (86399 if fim_do_dia else 0)


def coletar_ids(ids: list[str], max_comments: int = 30) -> dict[str, list[dict]]:
    """Coleta posts já conhecidos, sem busca: ["hackernews:123", "python:456"] -> { "hackernews": [post], ... }"""
    pares = [item.partition(":")[::2] for item in ids]  # "hackernews:123" -> ("hackernews", "123")
    invalidos = [f"{n}:{i}" for n, i in pares if n not in FONTES or not i]
    if invalidos:
        raise ValueError(f"id inválido: {', '.join(invalidos)} (use fonte:id, ex.: hackernews:50338728)")

    resultado = {}
    for nome, id in pares:
        try:
            post = FONTES[nome].por_id(id, max_comments)
        except Exception as e:  # post apagado ou fonte fora do ar: avisa e segue
            print(f"{nome}:{id}: FALHOU ({type(e).__name__}: {e})")
            continue
        post["lang"] = detectar(post)
        resultado.setdefault(nome, []).append(post)
        print(f"{nome}:{id}: {len(post['comments'])} comentários")
    return resultado


def coletar_tudo(
    query: str,
    sources: list[str] | None = None,
    limit: int = 10,
    max_comments: int = 30,
    min_comments: int = 0,
    langs: list[str] | None = None,
    se_sites: list[str] | None = None,
    since: str | None = None,
    until: str | None = None,
    sort: str = "relevancia",
) -> dict[str, list[dict]]:
    """Roda as fontes escolhidas e devolve { "hackernews": [posts...], ... } já filtrado."""
    nomes = sources or list(FONTES)
    desconhecidas = [n for n in nomes if n not in FONTES]
    if desconhecidas:
        raise ValueError(f"fonte desconhecida: {', '.join(desconhecidas)} (use: {', '.join(FONTES)})")
    if sort not in ("relevancia", "recentes"):
        raise ValueError(f"ordem inválida: {sort!r} (use relevancia ou recentes)")

    # datas viram segundos para comparar com o created_utc de cada post
    desde = para_timestamp(since) if since else None
    ate = para_timestamp(until, fim_do_dia=True) if until else None

    # Os filtros vão para a busca de cada fonte (assim o --limit conta só os posts que passam).
    filtros = {"desde": desde, "ate": ate, "min_comments": min_comments}

    def uma_fonte(nome: str) -> list[dict] | None:
        # Só o Stack Exchange aceita a opção extra "sites".
        extra = {"sites": se_sites} if nome == "stackexchange" and se_sites else {}
        try:
            posts = FONTES[nome].coletar(query, limit, max_comments, ordem=sort, **filtros, **extra)
        except Exception as e:
            # Fonte fora do ar ou bloqueada: avisa e segue, assim uma fonte com problema não derruba as outras.
            avisar(f"{nome}: FALHOU ({type(e).__name__}: {e})")
            return None
        # rede de segurança: filtra de novo, caso a fonte não tenha conseguido filtrar
        return [p for p in posts if passa(p["created_utc"], p["num_comments"], **filtros)]

    # Uma tarefa por fonte: cada site recebe um pedido por vez, mas os sites rodam ao mesmo tempo,
    # e a coleta leva mais ou menos o tempo da fonte mais lenta.
    with ThreadPoolExecutor(max_workers=6) as pool:
        tarefas = {nome: pool.submit(uma_fonte, nome) for nome in nomes}

    resultado = {}
    for nome, tarefa in tarefas.items():  # na ordem pedida, não na ordem em que terminaram
        posts = tarefa.result()
        if posts is None:
            continue
        for p in posts:
            p["lang"] = detectar(p)  # aqui, fora das tarefas: o langdetect não foi feito para threads
        if langs:
            posts = [p for p in posts if p["lang"] in langs]
        resultado[nome] = posts
        print(f"{nome}: {len(posts)} posts")
    return resultado
