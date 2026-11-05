# Fica na raiz para o pytest achar os módulos do projeto (common, coletor, fontes...).
import pytest
import requests


@pytest.fixture(autouse=True)
def sem_rede(monkeypatch):
    # Nenhum teste acessa a internet: uma requisição de verdade falha na hora.
    def bloqueia(*args, **kwargs):
        raise RuntimeError("teste tentou acessar a rede")

    monkeypatch.setattr(requests, "request", bloqueia)
