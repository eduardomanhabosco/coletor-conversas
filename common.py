import html
import re
from datetime import datetime

import requests

H = {"User-Agent": "estudo-coletor/0.1 (projeto pessoal de estudo)"}


def limpar(texto: str | None) -> str:
    # tira tags HTML e converte &amp; etc.
    return html.unescape(re.sub(r"<[^>]+>", " ", texto or "")).strip()


def ts(iso: str) -> int:
    # data ISO-8601 ("2024-01-31T10:00:00Z") -> segundos desde 1970
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp())


def get(url: str, **params) -> dict | list:
    r = requests.get(url, headers=H, params=params, timeout=15)
    r.raise_for_status()
    return r.json()
