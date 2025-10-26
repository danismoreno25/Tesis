cat > text_cleaning.py << 'EOF'
import re
from html import unescape
NOISE_PATTERNS = [
    r"\bcookies?\b", r"Cloudflare", r"Verificar que usted es un ser humano",
    r"Pol[ií]tica(s)? de Cookies?", r"Centro de preferencia de la privacidad",
    r"Aguarde\.\.\.", r"Ray ID:", r"reCAPTCHA", r"uso de cookies",
    r"este sitio web utiliza cookies", r"aceptar( las)? cookies"
]
NOISE_RE = re.compile("|".join(NOISE_PATTERNS), re.IGNORECASE)
def basic_clean(s: str, max_len=2000) -> str:
    if not s: return ""
    s = unescape(str(s))
    s = re.sub(r"\s+", " ", s).strip()
    if NOISE_RE.search(s): return ""
    return s[:max_len]
EOF
