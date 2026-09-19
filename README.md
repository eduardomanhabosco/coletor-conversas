# 🔎 Coletor de conversas → JSON

CLI em Python que busca posts e comentários sobre um tema em várias comunidades abertas e salva tudo num único JSON, organizado por fonte e idioma, pronto para alimentar uma IA depois.

> **Por que não Reddit?** Desde o fim de 2025 o Reddit devolve 403 para scripts, e a API oficial exige aprovação. Decidi não contornar e usar fontes com API aberta.

## 🎯 O que faz
Você digita um tema (ex.: `"como fazer loop"`) e o programa:
1. busca posts em até 6 fontes;
2. coleta o texto do post e os comentários (ou respostas);
3. detecta o idioma de cada post (`langdetect`) e filtra, se você pedir;
4. salva em `output/<tema>_<data>.json`.

## 🌐 Fontes

| Fonte | Busca | Comentários |
|-------|-------|-------------|
| Hacker News | texto | árvore completa |
| Lemmy (lemmy.world) | texto | por post, ordenados por score |
| Stack Exchange | texto, em 6 comunidades (`stackoverflow`, `pt.stackoverflow`, `softwareengineering`, `codereview`, `ux`, `pm`) | respostas mais votadas |
| Dev.to | por tag | árvore completa |
| Mastodon (mastodon.social) | por hashtag | respostas ao toot |
| Discourse (meta.discourse.org) | texto | posts do tópico |

Cada fonte é um arquivo em `fontes/` com uma função `coletar(query, limit, max_comments)`, então adicionar uma nova é criar um arquivo e registrá-lo no `main.py`.

## 🚀 Como rodar
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python main.py "como fazer loop" --limit 3 --max-comments 10
```

| Opção | O que faz | Padrão |
|-------|-----------|--------|
| `--sources` | fontes separadas por vírgula | todas |
| `--se-sites` | comunidades do Stack Exchange | as 6 acima |
| `--langs` | idiomas a manter (ex.: `pt,en`) | todos |
| `--limit` | posts por fonte | 10 |
| `--min-comments` | descarta posts com menos comentários | 0 |
| `--max-comments` | comentários guardados por post | 30 |

## 📦 Formato do JSON
```
fonte → idioma → posts → comentários
```
```json
{
  "query": "...", "collected_at": "...", "filters": {},
  "sources": {
    "hackernews": {
      "post_count": 3,
      "languages": {
        "en": {"post_count": 3, "posts": [
          {"source": "hackernews", "id": "", "title": "", "author": "", "url": "",
           "score": 0, "created_utc": 0, "selftext": "", "num_comments": 0, "lang": "en",
           "comments": [{"author": "", "score": 0, "body": "", "depth": 0}]}
        ]}
      }
    }
  }
}
```

## 🗺️ Roadmap
- [x] 6 fontes com formato comum
- [x] Detecção e filtro de idioma
- [x] `--min-comments` e `--max-comments`
- [ ] Filtro por data (`--since` / `--until`)
- [ ] Front-end (React + TypeScript) com seleção em cascata e botão "Salvar JSON"
- [ ] Resumo por IA

## ⚖️ Uso
Pessoal e educacional. Respeite os termos de cada plataforma. Não commite credenciais (use `.env`).
