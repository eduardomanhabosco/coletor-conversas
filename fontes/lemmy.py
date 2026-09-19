from common import get, ts

BASE = "https://lemmy.world/api/v3"


def coletar(query: str, limit: int = 5, max_comments: int = 30) -> list[dict]:
    achados = get(
        f"{BASE}/search", q=query, type_="Posts", sort="TopAll", limit=min(limit, 50)
    )["posts"]
    posts = []
    for x in achados:
        p = x["post"]
        cs = get(
            f"{BASE}/comment/list",
            post_id=p["id"], sort="Top", type_="All", limit=min(max_comments, 50),
        )["comments"]
        posts.append({
            "source": "lemmy",
            "id": str(p["id"]),
            "title": p["name"],
            "author": x["creator"]["name"],
            "url": p["ap_id"],
            "score": x["counts"]["score"],
            "created_utc": ts(p["published"]),
            "selftext": p.get("body") or "",
            "num_comments": x["counts"]["comments"],
            "comments": [
                {
                    "author": c["creator"]["name"],
                    "score": c["counts"]["score"],
                    "body": c["comment"]["content"],
                    "depth": c["comment"]["path"].count(".") - 1,  # path = "0.id.id..."
                }
                for c in cs
                if not (c["comment"]["deleted"] or c["comment"]["removed"])
            ],
        })
    return posts
