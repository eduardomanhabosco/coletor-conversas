from langdetect import DetectorFactory, LangDetectException, detect

DetectorFactory.seed = 0  # o langdetect sorteia; fixar a semente dá o mesmo resultado a cada execução

MIN_CHARS = 60  # abaixo disso o texto é curto demais para detectar bem


def detectar(post: dict) -> str:
    """Devolve o código do idioma do post ("pt", "en"...) ou "??" se não deu para detectar."""
    texto = f"{post['title']} {post['selftext']}"
    if len(texto) < MIN_CHARS:
        # post curto: junta os primeiros comentários para dar mais texto ao detector
        texto += " " + " ".join(c["body"] for c in post["comments"][:3])
    try:
        codigo = detect(texto)
    except LangDetectException:  # texto vazio ou só símbolos
        return "??"
    return codigo.split("-")[0]  # o langdetect devolve "zh-cn"/"zh-tw"; guardamos só "zh"
