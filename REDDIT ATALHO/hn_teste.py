import requests

H = {"User-Agent": "estudo-coletor/0.1 (projeto pessoal de estudo)"}

# 1 história sobre o tema
hit = requests.get(
    "https://hn.algolia.com/api/v1/search",
    params={"query": "video editing", "tags": "story", "hitsPerPage": 1},
    headers=H,
    timeout=15,
).json()["hits"][0]
print(hit["title"], "| id:", hit["objectID"], "| comentários:", hit["num_comments"])

# a história completa, com a árvore de comentários
item = requests.get(
    f"https://hn.algolia.com/api/v1/items/{hit['objectID']}",
    headers=H,
    timeout=15,
).json()
print(len(item["children"]), "comentários de 1º nível")
print(item["children"][0]["text"][:200])
