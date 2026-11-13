import re
import unicodedata


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = texto.encode("ascii", "ignore").decode("ascii").lower()
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    return texto.strip()


def palabras(texto_normalizado):
    return texto_normalizado.split()


def limpiar_dato(texto):
    texto = re.sub(r'["\x00-\x1f\x7f]', " ", texto or "")
    return re.sub(r"\s+", " ", texto).strip()
