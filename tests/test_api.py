"""Rotas da API chamadas como funções (o TestClient pediria o httpx, mais uma dependência)."""
import pytest
from fastapi import HTTPException

import api
from coletor import FONTES


def test_toda_fonte_tem_detalhes():
    # registrou uma fonte nova no coletor.py? ela precisa de uma linha no DETALHES da api.py
    assert [d["nome"] for d in api.detalhar_fontes()] == list(FONTES)


def test_coletar_exige_query_ou_ids():
    with pytest.raises(HTTPException) as erro:
        api.coletar()
    assert erro.value.status_code == 400


def test_coletar_por_ids(monkeypatch):
    monkeypatch.setattr(api, "coletar_ids", lambda ids, max_comments: {"hackernews": [{"id": ids[0], "lang": "en"}]})
    dados = api.coletar(ids="hackernews:1")
    assert dados["query"] == "ids"
    assert dados["sources"]["hackernews"]["post_count"] == 1
