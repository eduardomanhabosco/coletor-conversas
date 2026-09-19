# 🔎 Coletor de conversas → JSON

CLI em Python que busca posts e comentários sobre um tema e salva tudo em JSON, num formato pronto para alimentar uma IA depois.

> **Status:** 🚧 em estudo. O Reddit passou a bloquear scripts (403), então estou testando fontes abertas com API oficial.

## 🎯 Objetivo
Você digita um texto (ex.: "como aprender a editar vídeo") e o programa:
1. busca posts sobre o tema;
2. coleta o texto e os comentários mais votados;
3. filtra por idioma (`pt`, `en`... até 12 idiomas);
4. salva em `output/<tema>_<data>.json`.

## 🧪 O que já existe
- Ambiente com `venv` + `requests` + `langdetect`
- `REDDIT ATALHO/teste.py`: testa 7 fontes abertas e mostra qual devolve JSON:
  Hacker News, Stack Exchange, Lemmy, Mastodon, Dev.to, Bluesky, Discourse

## 🚀 Como rodar
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python "REDDIT ATALHO\teste.py"
```

## 🗺️ Roadmap
- [x] Planejamento e ambiente
- [x] Teste de fontes alternativas
- [ ] Cliente HTTP com retry/backoff
- [ ] Busca com filtro de idioma e `--min-comments`
- [ ] Coleta de comentários
- [ ] Gravação do JSON + CLI (`argparse`)
- [ ] Resumo por IA

## ⚖️ Uso
Pessoal e educacional. Respeite os termos de cada plataforma. Não commite credenciais (use `.env`).
