#!/usr/bin/env python3
"""
Detecta texto en portugués dentro de items_desde_txt.csv, lo traduce al español
usando libretranslate_utils (si está disponible) y marca cada fila con:
  - EN: contenido ya estaba en español (sin cambios)
  - ET: contenido traducido desde portugués a español

Si la traducción falla (por ejemplo, no hay acceso a un servicio LibreTranslate),
la fila permanece en portugués pero se registra un aviso en la terminal.
"""
import csv
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

BASE_PATH = Path(__file__).resolve().parent
CSV_PATH = BASE_PATH / "llm_artifacts" / "items_desde_txt.csv"

TEXT_COLUMNS = [
    "title",
    "description",
    "breadcrumbs",
    "product_name",
    "brand",
    "reference",
    "unit",
    "price_text",
    "information_text",
    "description_text",
    "features_text",
    "specifications_text",
    "benefits_text",
    "details_text",
    "other_sections",
]

PT_KEYWORDS = {
    "loja",
    "produto",
    "produtos",
    "promoção",
    "promoções",
    "quantidade",
    "frete",
    "carrinho",
    "parcelado",
    "cartão",
    "cartao",
    "ofertas",
    "aproveite",
    "unidades",
    "sabor",
    "economia",
    "prateleira",
    "atacado",
    "preço",
    "precos",
    "preço:",
    "lançamento",
    "lancamento",
    "disponível",
    "disponivel",
}

PT_CHARS_PATTERN = re.compile(r"[ãõâêôûáéíóúç]+", re.IGNORECASE)

try:
    ROOT_PATH = BASE_PATH.parent
    if str(ROOT_PATH) not in sys.path:
        sys.path.insert(0, str(ROOT_PATH))
    from libretranslate_utils import translate_text
except ImportError:
    print("[ERROR] No se pudo importar libretranslate_utils. Ejecuta desde la raíz del proyecto.")
    sys.exit(1)


def detect_portuguese(text: str) -> bool:
    if not text:
        return False
    lowered = text.lower()
    if PT_CHARS_PATTERN.search(lowered):
        return True
    return any(keyword in lowered for keyword in PT_KEYWORDS)


translator_available = True
translator_warned = False


def translate_pt_to_es(text: str, cache: Dict[str, str]) -> Tuple[str, bool]:
    if not text or not detect_portuguese(text):
        return text, False

    cached = cache.get(text)
    if cached is not None:
        translated = cached
    else:
        global translator_available, translator_warned
        if not translator_available:
            return text, False
        try:
            translated = translate_text(text, source="pt", target="es", retries=1, timeout=5)
        except Exception as exc:
            if not translator_warned:
                print(f"[WARN] Falló la traducción vía LibreTranslate ({exc}); el resto se mantendrá en portugués.")
                translator_warned = True
            translator_available = False
            cache[text] = text
            return text, False
        if not translated or not translated.strip():
            if not translator_warned:
                print("[WARN] No se obtuvo respuesta del traductor LibreTranslate; el resto se mantendrá en portugués.")
                translator_warned = True
            translator_available = False
            cache[text] = text
            return text, False
        cache[text] = translated

    if translated and translated.strip() and translated != text:
        return translated, True
    return text, False


def translate_sections(sections_raw: str, cache: Dict[str, str]) -> Tuple[str, bool]:
    if not sections_raw:
        return sections_raw, False
    try:
        data = json.loads(sections_raw)
    except json.JSONDecodeError:
        return sections_raw, False

    modified = False
    for key, value in list(data.items()):
        if isinstance(value, list):
            new_list: List[str] = []
            for item in value:
                translated, changed = translate_pt_to_es(item, cache)
                modified = modified or changed
                new_list.append(translated)
            data[key] = new_list
        elif isinstance(value, str):
            translated, changed = translate_pt_to_es(value, cache)
            data[key] = translated
            modified = modified or changed

    if modified:
        return json.dumps(data, ensure_ascii=False), True
    return sections_raw, False


def translate_csv():
    if not CSV_PATH.exists():
        print(f"[ERROR] No se encontró {CSV_PATH}. Ejecuta previamente limpiar_htmls.py.")
        return

    with open(CSV_PATH, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    if "es_status" not in fieldnames:
        fieldnames.append("es_status")

    cache: Dict[str, str] = {}
    translated_rows = []
    translated_count = 0
    pt_detected_without_translation = 0

    for row in rows:
        row_translated = False
        for col in TEXT_COLUMNS:
            original_text = row.get(col, "")
            if original_text:
                translated, changed = translate_pt_to_es(original_text, cache)
                if changed:
                    row[col] = translated
                    row_translated = True
        sections_raw = row.get("sections", "")
        sections_translated, sections_changed = translate_sections(sections_raw, cache)
        if sections_changed:
            row["sections"] = sections_translated
            row_translated = True

        row["es_status"] = "ET" if row_translated else "EN"
        if row_translated:
            translated_count += 1
        elif sections_raw and detect_portuguese(sections_raw):
            pt_detected_without_translation += 1

        translated_rows.append(row)

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in translated_rows:
            writer.writerow(row)

    print(f"✅ Archivo actualizado: {CSV_PATH.relative_to(BASE_PATH.parent)}")
    print(f"   Filas traducidas (ET): {translated_count}")
    if pt_detected_without_translation:
        print(f"   Aviso: {pt_detected_without_translation} filas podrían seguir en portugués (sin traducción disponible).")


if __name__ == "__main__":
    translate_csv()
