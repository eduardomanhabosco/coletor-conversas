# 🔎 Coletor de conversas → JSON

CLI em Python que busca posts e comentários sobre um tema em várias comunidades abertas e salva tudo num único JSON, organizado por fonte e idioma, pronto para alimentar uma IA depois.

> **Por que não Reddit?** Desde o fim de 2025 o Reddit devolve 403 para scripts, e a API oficial exige aprovação. Decidi não contornar e usar fontes com API aberta.

## 🎯 O que faz
Você digita um tema (ex.: `"como fazer loop"`) e o programa:
1. busca posts em até 15 fontes;
2. coleta o texto do post e os comentários (ou respostas);
3. detecta o idioma de cada post (`langdetect`) e filtra, se você pedir;
4. salva em `output/<tema>_<data>.json`.

## 🌐 Fontes

| Fonte | Busca | Comentários |
|-------|-------|-------------|
| Hacker News | texto | árvore completa |
| Lemmy (lemmy.world) | texto, em todo o fediverso; fica só com os posts que têm as palavras no título | todos, ordenados por score (de 50 em 50) |
| Stack Exchange | texto, em 6 comunidades (`stackoverflow`, `pt.stackoverflow`, `softwareengineering`, `codereview`, `ux`, `pm`) | respostas mais votadas |
| Dev.to | por tags (a busca inteira e cada palavra): os mais novos e os populares do último ano; texto completo do artigo | árvore completa |
| Mastodon (mastodon.social) | por hashtags (a busca inteira e cada palavra), até 200 toots por hashtag | respostas ao toot |
| Discourse (meta.discourse.org) | texto | todos os posts do tópico |

Fóruns abertos (sem login) adicionados depois; o nome da 1ª coluna é o que vai no `--sources`:

| `--sources` | Site | Tipo | Busca | Comentários |
|-------------|------|------|-------|-------------|
| `stackernews` | stacker.news | parecido com o HN (API GraphQL) | texto | árvore, até 6 níveis |
| `tabnews` | tabnews.com.br 🇧🇷 | fórum de dev brasileiro | palavras no título dos ~1.000 posts mais novos + relevantes (a API não tem busca) | árvore completa |
| `programmingdev` | programming.dev | Lemmy só de programação | texto, só comunidades locais | todos |
| `lemmybr` | lemmy.eco.br 🇧🇷 | Lemmy brasileiro | texto, só comunidades locais | todos |
| `python` | discuss.python.org | Discourse | texto | todos os posts do tópico |
| `freecodecamp` | forum.freecodecamp.org | Discourse | texto | todos os posts do tópico |
| `openai` | community.openai.com | Discourse | texto | todos os posts do tópico |
| `rust` | users.rust-lang.org | Discourse | texto | todos os posts do tópico |
| `cursor` | forum.cursor.com | Discourse | texto | todos os posts do tópico |

Cada fonte é um arquivo em `fontes/` com as funções `coletar(query, limit, max_comments, ...)` (busca) e `por_id(id, max_comments)` (um post já conhecido), registrado no dicionário `FONTES` do `coletor.py`. Para outro fórum Discourse ou instância Lemmy, basta uma linha lá:

```python
"godot": discourse.Forum("https://forum.godotengine.org"),
"feddit": lemmy.Instancia("feddit.org", local=True),
```

> Os fóruns Discourse pedem no `robots.txt` que robôs não usem a busca (`/search`). Para uso pessoal, mantenha o volume baixo. O contador de comentários do Lemmy inclui apagados, então às vezes vêm menos que o `num_comments`. O PieFed ficou de fora: o `robots.txt` dele declara `ai-input=no`. O programming.dev pede 60 s entre pedidos (`Crawl-delay`): use poucos posts por vez.

## 🚀 Como rodar
Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python main.py "como fazer loop" --limit 3 --max-comments 10
```
Linux/macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python main.py "como fazer loop" --limit 3 --max-comments 10
```

| Opção | O que faz | Padrão |
|-------|-----------|--------|
| `--sources` | fontes separadas por vírgula | todas |
| `--se-sites` | comunidades do Stack Exchange | as 6 acima |
| `--langs` | idiomas a manter (ex.: `pt,en`) | todos |
| `--limit` | posts por fonte (contando só os que passam nos filtros) | 10 |
| `--min-comments` | descarta posts com menos comentários | 0 |
| `--max-comments` | comentários guardados por post | 30 |
| `--since` / `--until` | só posts deste período (`AAAA-MM-DD`) | sem limite |
| `--sort` | `relevancia` ou `recentes` (os mais novos primeiro) | `relevancia` |
| `--ids` | coleta posts já conhecidos, sem busca (veja abaixo) | — |
| `--delay` | segundos de pausa antes de cada pedido a um site | 0 |

As fontes rodam em paralelo (cada site recebe um pedido por vez), e o terminal mostra o andamento post a post. Os filtros de data e de comentários vão direto na busca quando a API permite (HN, Stack Exchange, Discourse, Stacker News); nas outras, a lista é filtrada antes de baixar os comentários.

**Coletar uma thread específica:** `--ids fonte:id`, separados por vírgula. O tema fica opcional e o arquivo sai como `output/ids_<data>.json`:
```powershell
python main.py --ids hackernews:50338728,python:75823 --max-comments 2000
```
O `id` é o número que aparece na URL do post. No TabNews é `usuario/slug`; no Stack Exchange, `comunidade/numero` (só o número vale para o Stack Overflow).

**Chave do Stack Exchange (opcional):** sem chave, a cota é de 300 pedidos por dia; com a variável `STACKEXCHANGE_KEY`, 10.000. Veja o `.env.example`. No PowerShell: `$env:STACKEXCHANGE_KEY = "sua_chave"`. O programa avisa quando restam menos de 20 pedidos.

**Juntar coletas:** um tema bem coberto pede várias buscas, e cada uma gera um JSON. O `juntar.py` une os arquivos, tira os posts repetidos (mesmo `source` e `id`) e guarda em cada post o campo `"matched_query"`, com as buscas que o trouxeram:
```powershell
python juntar.py output/react_*.json output/vue_*.json -o output/frontend.json
```

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
Campos extras, que só aparecem em alguns casos:
- `"accepted"` (comentário): no Stack Exchange os comentários são as respostas, e `true` marca a que quem perguntou aceitou;
- `"matched_query"` (post): nos arquivos do `juntar.py`, a lista de buscas que trouxeram o post.

O `num_comments` é o número que a API informa e pode ser maior que a lista `comments` (apagados, `--max-comments`).

## 🧪 Testes
Rodam sem internet, com respostas reais das APIs salvas em `tests/fixtures/` (cortadas e com os autores anonimizados):
```bash
pip install -r requirements-dev.txt
pytest
```

## 🗺️ Roadmap
- [x] 6 fontes com formato comum
- [x] +9 fóruns abertos (Stacker News, TabNews, programming.dev, lemmy.eco.br e 5 fóruns Discourse)
- [x] Detecção e filtro de idioma
- [x] `--min-comments` e `--max-comments`
- [x] Filtro por data (`--since` / `--until`), direto na busca
- [x] `--sort`, `--ids`, `--delay`, fontes em paralelo e `juntar.py`
- [x] Testes sem rede (pytest)
- [ ] Front-end (React + TypeScript) com seleção em cascata e botão "Salvar JSON"
- [ ] Resumo por IA

## ⚖️ Uso
Pessoal e educacional. Respeite os termos de cada plataforma. Não commite credenciais (use `.env`).
