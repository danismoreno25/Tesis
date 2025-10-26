cat > libretranslate_utils.py << 'EOF'
import os, time, requests
LIBRE_URL = os.getenv("LIBRE_URL", "https://libretranslate.com/translate")
_session = requests.Session()
_session.headers.update({"User-Agent": "Tesis-Scraping/translator"})
def translate_text(text: str, source="pt", target="es", fmt="text",
                   retries=4, backoff_base=1.5, timeout=30) -> str:
    if not text or not str(text).strip():
        return ""
    payload = {"q": text, "source": source, "target": target, "format": fmt}
    for attempt in range(retries):
        try:
            resp = _session.post(LIBRE_URL, json=payload, timeout=timeout)
            if resp.status_code == 200:
                return resp.json().get("translatedText", "")
            if resp.status_code in (429, 502, 503, 504, 520, 522):
                time.sleep((backoff_base ** attempt) + 0.5); continue
            return ""
        except (requests.Timeout, requests.ConnectionError):
            time.sleep((backoff_base ** attempt) + 0.5); continue
    return ""
EOF
cat > libretranslate_utils.py << 'EOF'
import os, time, requests
LIBRE_URL = os.getenv("LIBRE_URL", "https://libretranslate.com/translate")
_session = requests.Session()
_session.headers.update({"User-Agent": "Tesis-Scraping/translator"})
def translate_text(text: str, source="pt", target="es", fmt="text",
                   retries=4, backoff_base=1.5, timeout=30) -> str:
    if not text or not str(text).strip():
        return ""
    payload = {"q": text, "source": source, "target": target, "format": fmt}
    for attempt in range(retries):
        try:
            resp = _session.post(LIBRE_URL, json=payload, timeout=timeout)
            if resp.status_code == 200:
                return resp.json().get("translatedText", "")
            if resp.status_code in (429, 502, 503, 504, 520, 522):
                time.sleep((backoff_base ** attempt) + 0.5); continue
            return ""
        except (requests.Timeout, requests.ConnectionError):
            time.sleep((backoff_base ** attempt) + 0.5); continue
    return ""
EOF
