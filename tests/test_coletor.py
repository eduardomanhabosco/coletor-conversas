"""coletar_tudo, storage e utilitários do common, sem rede."""
import copy

import pytest

import common
from coletor import FONTES, coletar_ids, coletar_tudo, para_timestamp
from common import limpar, palavras, ranquear
from juntar import juntar
from storage import montar

EN = "This is a long enough English sentence about web frameworks, databases and deployment."
PT = "Esta é uma frase em português, longa o bastante, sobre frameworks web e bancos de dados."


class FonteFalsa:
    def __init__(self, posts=None, erro=None):
        self.posts, self.erro = posts or [], erro

    def coletar(self, query, limit, max_comments, **kwargs):
        if self.erro:
            raise self.erro
        return copy.deepcopy(self.posts)

    def por_id(self, id, max_comments):
        return next(p for p in self.coletar("", 0, max_comments) if p["id"] == id)


def post_falso(id: str, dia: str, num_comments: int, texto: str) -> dict:
    return {
        "source": "falsa", "id": id, "title": texto, "author": None, "url": "", "score": None,
        "created_utc": para_timestamp(dia), "selftext": texto, "num_comments": num_comments, "comments": [],
    }


POSTS = [
    post_falso("1", "2024-01-10", 5, EN),
    post_falso("2", "2025-03-01", 0, EN),
    post_falso("3", "2025-06-01", 8, PT),
    post_falso("4", "2026-01-01", 9, EN),
]


def test_filtros_de_data_e_comentarios(monkeypatch):
    monkeypatch.setitem(FONTES, "falsa", FonteFalsa(POSTS))
    r = coletar_tudo("x", sources=["falsa"], min_comments=1, since="2025-01-01", until="2025-12-31")
    assert [p["id"] for p in r["falsa"]] == ["3"]


def test_filtro_de_idioma(monkeypatch):
    monkeypatch.setitem(FONTES, "falsa", FonteFalsa(POSTS))
    r = coletar_tudo("x", sources=["falsa"], langs=["pt"])
    assert [p["id"] for p in r["falsa"]] == ["3"]
    assert r["falsa"][0]["lang"] == "pt"


def test_fonte_com_erro_nao_derruba_as_outras(monkeypatch):
    monkeypatch.setitem(FONTES, "quebrada", FonteFalsa(erro=RuntimeError("fora do ar")))
    monkeypatch.setitem(FONTES, "falsa", FonteFalsa(POSTS))
    r = coletar_tudo("x", sources=["quebrada", "falsa"])
    assert list(r) == ["falsa"] and len(r["falsa"]) == 4


def test_fontes_em_paralelo_mantem_a_ordem(monkeypatch):
    monkeypatch.setitem(FONTES, "b", FonteFalsa(POSTS))
    monkeypatch.setitem(FONTES, "a", FonteFalsa(POSTS[:1]))
    assert list(coletar_tudo("x", sources=["b", "a"])) == ["b", "a"]


def test_pedir_espera_o_delay_e_o_retry_after(monkeypatch):
    class Resposta:
        def __init__(self, status, headers=None):
            self.status_code, self.headers = status, headers or {}

        def raise_for_status(self):
            assert self.status_code == 200

        def json(self):
            return {"ok": True}

    respostas = [Resposta(429, {"Retry-After": "7"}), Resposta(200)]
    esperas = []
    monkeypatch.setattr(common.requests, "request", lambda *a, **kw: respostas.pop(0))
    monkeypatch.setattr(common.time, "sleep", esperas.append)
    monkeypatch.setattr(common, "ATRASO", 2)
    assert common.get("https://exemplo") == {"ok": True}
    assert esperas == [2, 7, 2]  # delay, o que o 429 pediu, delay de novo


def test_fonte_desconhecida():
    with pytest.raises(ValueError):
        coletar_tudo("x", sources=["nao_existe"])


def test_coletar_ids(monkeypatch):
    monkeypatch.setitem(FONTES, "falsa", FonteFalsa(POSTS))
    monkeypatch.setitem(FONTES, "quebrada", FonteFalsa(erro=RuntimeError("fora do ar")))
    r = coletar_ids(["falsa:3", "quebrada:1", "falsa:1"])
    assert [p["id"] for p in r["falsa"]] == ["3", "1"] and "quebrada" not in r
    assert r["falsa"][0]["lang"] == "pt"
    with pytest.raises(ValueError):
        coletar_ids(["falsa:1", "nao_existe:2", "falsa"])


def test_montar_agrupa_por_idioma():
    posts = [{"id": "1", "lang": "pt"}, {"id": "2", "lang": "en"}, {"id": "3", "lang": "pt"}]
    fonte = montar("x", {}, {"falsa": posts})["sources"]["falsa"]
    assert fonte["post_count"] == 3
    assert fonte["languages"]["pt"]["post_count"] == 2
    assert fonte["languages"]["en"]["post_count"] == 1


def test_juntar_tira_repetidos_e_guarda_as_buscas():
    def coleta(query, ids):
        posts = [{"source": "falsa", "id": i, "lang": "en"} for i in ids]
        return montar(query, {}, {"falsa": posts})

    junto = juntar([coleta("react", ["1", "2"]), coleta("vue", ["2", "3"])])
    assert [(p["id"], p["matched_query"]) for p in junto["falsa"]] == [
        ("1", ["react"]), ("2", ["react", "vue"]), ("3", ["vue"])]
    # juntar de novo um arquivo já juntado mantém as buscas
    de_novo = juntar([montar("x", {}, junto), coleta("svelte", ["3"])])
    assert de_novo["falsa"][2]["matched_query"] == ["vue", "svelte"]


def test_limpar_tira_tags_e_entidades():
    assert limpar("<b>Tom &amp; Jerry</b>") == "Tom & Jerry"
    assert limpar(None) == ""


def test_limpar_mantem_paragrafos_listas_e_codigo():
    assert limpar("Para 1<p>Para 2") == "Para 1\n\nPara 2"  # formato do HN
    assert limpar("<p>a</p>\n<p>b</p>") == "a\n\nb"
    assert limpar("<ul><li>um</li><li>dois</li></ul>") == "- um\n- dois"
    assert limpar("<pre><code>x = 1\n    y = 2</code></pre>fim") == "x = 1\n    y = 2\nfim"
    assert limpar("use <code>map</code>.") == "use map."


def test_ranquear_exige_duas_palavras():
    itens = [{"t": "future of frontend"}, {"t": "the future"}, {"t": "frontend future today"}]
    achados = ranquear(itens, lambda i: i["t"], palavras("future frontend"), lambda i: len(i["t"]))
    assert [i["t"] for i in achados] == ["frontend future today", "future of frontend"]


def test_palavras_mantem_termos_curtos():
    assert palavras("Go vs C# for AI agents") == ["go", "c#", "ai", "agents"]
    assert palavras("PR review of code") == ["pr", "review", "code"]


def test_palavras_ignora_as_comuns():
    assert palavras("which database") == ["database"]
    assert palavras("como fazer um site") == ["fazer", "site"]


def test_ranquear_por_palavra_inteira_e_sem_acento():
    itens = [{"t": "JavaScript tips"}, {"t": "Java tips"}, {"t": "Programação em C# e Java"}]

    def achados(query):
        return [i["t"] for i in ranquear(itens, lambda i: i["t"], palavras(query), lambda i: len(i["t"]))]

    assert achados("java") == ["Programação em C# e Java", "Java tips"]
    assert achados("programacao C#") == ["Programação em C# e Java"]
