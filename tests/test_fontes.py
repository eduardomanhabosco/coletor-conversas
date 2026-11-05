"""Cada fonte, com as respostas das APIs salvas em tests/fixtures (reais, cortadas e anonimizadas)."""
import json
from pathlib import Path

import pytest

from fontes import devto, discourse, hackernews, lemmy, mastodon, stackernews, stackexchange, tabnews

FIXTURES = Path(__file__).parent / "fixtures"


def rede_falsa(monkeypatch, fonte, rotas: dict[str, str]):
    """Troca o get/post da fonte: a 1ª rota que aparece no pedido escolhe o arquivo de resposta."""
    def falso(url, *args, **kwargs):
        pedido = f"{url} {args} {kwargs}"
        for trecho, arquivo in rotas.items():
            if trecho in pedido:
                return json.loads((FIXTURES / arquivo).read_text(encoding="utf-8"))
        raise AssertionError(f"pedido sem fixture: {pedido}")

    # As fontes fazem "from common import get", então o alvo é o nome dentro do módulo da fonte.
    for nome in ("get", "post"):
        if hasattr(fonte, nome):
            monkeypatch.setattr(fonte, nome, falso)


CASOS = {
    "hackernews": (hackernews, "python", {"/items/": "hackernews/item.json", "/search": "hackernews/search.json"}),
    "lemmy": (lemmy, "python", {"/comment/list": "lemmy/comentarios.json", "/search": "lemmy/search.json"}),
    "stackexchange": (stackexchange, "python decorator", {
        "/answers": "stackexchange/respostas.json", "/search": "stackexchange/search.json"}),
    "devto": (devto, "python", {
        "/comments": "devto/comentarios.json", "/articles/": "devto/artigo.json", "/articles": "devto/artigos.json"}),
    "mastodon": (mastodon, "python", {"/context": "mastodon/contexto.json", "/timelines/tag/": "mastodon/tag.json"}),
    "discourse": (discourse, "asyncio", {
        "/search.json": "discourse/search.json", "/posts.json": "discourse/posts.json", "/t/": "discourse/topico.json"}),
    "stackernews": (stackernews, "bitcoin wallet", {"search(": "stackernews/busca.json", "item(": "stackernews/item.json"}),
    "tabnews": (tabnews, "projeto", {
        "/children": "tabnews/filhos.json", "/contents/": "tabnews/conteudo.json", "/contents": "tabnews/lista.json"}),
}


def confere_contrato(posts: list[dict], max_comments: int):
    assert posts
    for p in posts:
        for campo, tipo in [("source", str), ("id", str), ("title", str), ("url", str), ("created_utc", int),
                            ("selftext", str), ("num_comments", int), ("comments", list)]:
            assert isinstance(p[campo], tipo), campo
        assert p["author"] is None or isinstance(p["author"], str)
        assert p["score"] is None or isinstance(p["score"], int)
        assert len(p["comments"]) <= max_comments
        for c in p["comments"]:
            assert {"author", "score", "body", "depth"} <= set(c)
            assert isinstance(c["body"], str) and c["depth"] >= 0


@pytest.mark.parametrize("nome", CASOS)
def test_fonte_segue_o_contrato(monkeypatch, nome):
    fonte, query, rotas = CASOS[nome]
    rede_falsa(monkeypatch, fonte, rotas)
    confere_contrato(fonte.coletar(query, limit=2, max_comments=3), max_comments=3)


POR_ID = {
    "hackernews": (hackernews, "1", {"/items/": "hackernews/item.json"}),
    "lemmy": (lemmy, "1", {"/comment/list": "lemmy/comentarios.json", "/post": "lemmy/post.json"}),
    "stackexchange": (stackexchange, "pt.stackoverflow/1", {
        "/answers": "stackexchange/respostas.json", "/questions/": "stackexchange/pergunta.json"}),
    "devto": (devto, "1", {"/comments": "devto/comentarios.json", "/articles/": "devto/artigo.json"}),
    "mastodon": (mastodon, "1", {"/context": "mastodon/contexto.json", "/statuses/": "mastodon/status.json"}),
    "discourse": (discourse, "1", {"/posts.json": "discourse/posts.json", "/t/": "discourse/topico.json"}),
    "stackernews": (stackernews, "1", {"item(": "stackernews/item.json"}),
    "tabnews": (tabnews, "usuario/slug", {"/children": "tabnews/filhos.json", "/contents/": "tabnews/conteudo.json"}),
}


@pytest.mark.parametrize("nome", POR_ID)
def test_por_id_segue_o_contrato(monkeypatch, nome):
    fonte, id, rotas = POR_ID[nome]
    rede_falsa(monkeypatch, fonte, rotas)
    confere_contrato([fonte.por_id(id, max_comments=3)], max_comments=3)


def test_stackexchange_marca_a_resposta_aceita(monkeypatch):
    rede_falsa(monkeypatch, stackexchange, POR_ID["stackexchange"][2])
    respostas = stackexchange.por_id("1", max_comments=10)["comments"]
    assert respostas and all(isinstance(c["accepted"], bool) for c in respostas)


def test_mastodon_pagina_a_hashtag(monkeypatch):
    toot = {"created_at": "2026-01-01T00:00:00Z"}
    paginas = {None: [{**toot, "id": str(i)} for i in range(40)], "39": [{**toot, "id": "40"}]}
    pedidos = []

    def falso(url, **kwargs):
        pedidos.append(kwargs["max_id"])
        return paginas[kwargs["max_id"]]

    monkeypatch.setattr(mastodon, "get", falso)
    assert len(mastodon.toots_da_tag("python")) == 41
    assert pedidos == [None, "39"]  # a 2ª página parte do último toot da 1ª; com menos de 40, acabou
    pedidos.clear()
    mastodon.toots_da_tag("python", desde=1798761600)  # 2027-01-01: a 1ª página já é mais velha
    assert pedidos == [None]


def test_discourse_busca_os_posts_que_faltam(monkeypatch):
    # o tópico traz 3 posts carregados e 5 ids no "stream": os 2 que faltam vêm do posts.json
    rede_falsa(monkeypatch, discourse, CASOS["discourse"][2])
    post = discourse.coletar("asyncio", limit=1, max_comments=50)[0]
    assert len(post["comments"]) == 4


def test_stackernews_ignora_comentarios_na_busca(monkeypatch):
    # a busca do Stacker News mistura posts e comentários; só os posts têm título
    rede_falsa(monkeypatch, stackernews, CASOS["stackernews"][2])
    assert len(stackernews.coletar("bitcoin wallet", limit=5, max_comments=3)) == 2


def test_hackernews_filtra_na_busca(monkeypatch):
    rede_falsa(monkeypatch, hackernews, CASOS["hackernews"][2])
    pedidos, falso = [], hackernews.get
    monkeypatch.setattr(hackernews, "get", lambda url, **kw: pedidos.append(kw) or falso(url, **kw))
    hackernews.coletar("python", limit=2, desde=100, ate=200, min_comments=3)
    assert pedidos[0]["numericFilters"] == "num_comments>=3,created_at_i>=100,created_at_i<=200"


def test_filtra_antes_de_baixar_os_comentarios(monkeypatch):
    # O TabNews não filtra na API. Com data no futuro nada passa, e só a listagem (strategy) é pedida:
    # um pedido do corpo ou dos comentários cairia no "pedido sem fixture".
    rede_falsa(monkeypatch, tabnews, {"strategy": "tabnews/lista.json"})
    assert tabnews.coletar("projeto", limit=5, desde=4102444800) == []  # 2100-01-01


def test_lemmy_estrito_exige_as_palavras_no_titulo(monkeypatch):
    # o fixture tem 2 posts com "python" no título e 1 sem
    rede_falsa(monkeypatch, lemmy, CASOS["lemmy"][2])
    assert len(lemmy.coletar("python", limit=5, max_comments=3)) == 2
    solto = lemmy.Instancia("programming.dev", estrito=False)
    assert len(solto.coletar("python", limit=5, max_comments=3)) == 3


def test_tabnews_fica_so_com_titulos_da_busca(monkeypatch):
    rede_falsa(monkeypatch, tabnews, CASOS["tabnews"][2])
    posts = tabnews.coletar("projeto", limit=5, max_comments=3)
    assert len(posts) == 2
