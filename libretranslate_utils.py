"""Utilidades simples para consumir una API compatible con LibreTranslate."""

from __future__ import annotations

import os
import time
from typing import Optional

import requests

LIBRE_URL = os.getenv("LIBRE_URL", "https://libretranslate.com/translate")
_session = requests.Session()
_session.headers.update({"User-Agent": "Tesis-Scraping/translator"})


def translate_text(
    text: str,
    source: str = "pt",
    target: str = "es",
    fmt: str = "text",
    retries: int = 4,
    backoff_base: float = 1.5,
    timeout: int = 30,
) -> str:
    """
    Traduce `text` desde `source` hasta `target` usando una instancia de LibreTranslate.

    Devuelve la cadena traducida o una cadena vacía si la traducción falla.
    """
    if not text or not str(text).strip():
        return ""

    payload = {"q": text, "source": source, "target": target, "format": fmt}
    for attempt in range(retries):
        try:
            resp = _session.post(LIBRE_URL, json=payload, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("translatedText", "")
            if resp.status_code in {429, 502, 503, 504, 520, 522}:
                time.sleep((backoff_base ** attempt) + 0.5)
                continue
            return ""
        except (requests.Timeout, requests.ConnectionError):
            time.sleep((backoff_base ** attempt) + 0.5)
            continue
    return ""
