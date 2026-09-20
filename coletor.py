from datetime import datetime, timezone

from fontes import devto, discourse, hackernews, lemmy, mastodon, stackexchange
from idioma import detectar

FONTES = {
    "hackernews": hackernews,
    "lemmy": lemmy,
    "stackexchange": stackexchange,
    "devto": devto,
    "mastodon": mastodon,
    "discourse": discourse,
}


def para_timestamp(dia: str, fim_do_dia: bool = False) -> int:
    """"2026-09-19" -> segundos desde 1970 (UTC). Com fim_do_dia=True, vale 23:59:59 desse dia."""
    try:
        t = datetime.strptime(dia, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        raise ValueError(f"data inválida: {dia!r} (use AAAA-MM-DD)") from None
    return int(t.timestamp()) + (86399 if fim_do_dia else 0)


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
) -> dict[str, list[dict]]:
    """Roda as fontes escolhidas e devolve { "hackernews": [posts...], ... } já filtrado."""
    nomes = sources or list(FONTES)
    desconhecidas = [n for n in nomes if n not in FONTES]
    if desconhecidas:
        raise ValueError(f"fonte desconhecida: {', '.join(desconhecidas)} (use: {', '.join(FONTES)})")

    # datas viram segundos para comparar com o created_utc de cada post
    desde = para_timestamp(since) if since else None
    ate = para_timestamp(until, fim_do_dia=True) if until else None

    resultado = {}
    for nome in nomes:
        # Só o Stack Exchange aceita a opção extra "sites".
        extra = {"sites": se_sites} if nome == "stackexchange" and se_sites else {}
        try:
            posts = FONTES[nome].coletar(query, limit, max_comments, **extra)
        except Exception as e:
            # Fonte fora do ar ou bloqueada: avisa e segue para a próxima,
            # assim uma fonte com problema não derruba as outras.
            print(f"{nome}: FALHOU ({type(e).__name__}: {e})")
            continue

        posts = [p for p in posts if p["num_comments"] >= min_comments]
        if desde is not None:
            posts = [p for p in posts if p["created_utc"] >= desde]
        if ate is not None:
            posts = [p for p in posts if p["created_utc"] <= ate]

        for p in posts:
            p["lang"] = detectar(p)
        if langs:
            posts = [p for p in posts if p["lang"] in langs]

        resultado[nome] = posts
        print(f"{nome}: {len(posts)} posts")
    return resultado
