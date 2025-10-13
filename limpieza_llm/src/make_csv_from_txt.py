import os, re, csv, argparse, unicodedata
from pathlib import Path

def strip_accents(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

def normalize_spaces(s: str) -> str:
    return re.sub(r'\s+', ' ', s).strip()

def detect_currency_and_price(text: str):
    """
    Extrae un precio y moneda si aparecen en el TXT.
    Soporta patrones comunes: $1.234,56 | $ 1.234 | COP 12.345 | ARS 1.699,00 | 1699.00
    Devuelve (price_raw:str, currency_raw:str) o ("","") si no encontró.
    """
    t = text

    # patrones con código de moneda
    m = re.search(r'\b(COP|ARS|CLP|MXN|PEN|BRL|USD|EUR)\s*([\d\.\,]+)', t, flags=re.I)
    if m:
        code = m.group(1).upper()
        num = m.group(2)
        # normalizar: quitar miles y usar punto decimal
        num_norm = num.replace('.', '').replace(',', '.')
        return num_norm, code

    # patrones con símbolo $
    m = re.search(r'[$]\s*([\d\.\,]+)', t)
    if m:
        num = m.group(1)
        num_norm = num.replace('.', '').replace(',', '.')
        # si no hay código, deja moneda vacía y tú la llenas luego si quieres
        return num_norm, ""

    # número “sueltos” con decimal
    m = re.search(r'\b(\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{2})|\d+[.,]\d{2})\b', t)
    if m:
        num = m.group(1)
        num_norm = num.replace('.', '').replace(',', '.')
        return num_norm, ""

    return "", ""

def build_row_from_txt(filepath: Path, default_country: str, default_seller: str):
    """
    Heurística mínima:
    - title: primera línea no vacía
    - description: todo el texto (limpio)
    - breadcrumbs: vacío (si tienes forma de inferirlos, puedes llenarlos)
    - price_raw/currency_raw: intenta detectar
    """
    raw = filepath.read_text(encoding="utf-8", errors="ignore")
    lines = [normalize_spaces(l) for l in raw.splitlines()]
    lines = [l for l in lines if l]  # quita vacías

    title = lines[0] if lines else filepath.stem
    description = normalize_spaces(raw)
    price_raw, currency_raw = detect_currency_and_price(raw)

    return {
        "title": title[:200],
        "description": description[:2000],  # limita para no hacer archivos gigantes
        "breadcrumbs": "",
        "price_raw": price_raw,
        "currency_raw": currency_raw,
        "url": "",            # si la tienes, mejor; si no, vacío
        "seller": default_seller,
        "availability": "unknown",
        "country": default_country
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_dir", required=True, help="Carpeta con TXT limpios")
    ap.add_argument("--out_csv", required=True, help="Ruta del CSV de salida")
    ap.add_argument("--country", default="", help="País (ej: CO, AR, CL...)")
    ap.add_argument("--seller", default="", help="Nombre del retailer si aplica")
    args = ap.parse_args()

    in_dir = Path(args.in_dir)
    out_csv = Path(args.out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    txt_files = sorted(in_dir.glob("*.txt"))
    if not txt_files:
        print(f"[WARN] No encontré .txt en {in_dir}")
        return

    cols = ["title","description","breadcrumbs","price_raw","currency_raw","url","seller","availability","country"]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for p in txt_files:
            row = build_row_from_txt(p, args.country, args.seller)
            w.writerow(row)

    print(f"[OK] Generado: {out_csv} ({len(txt_files)} filas)")

if __name__ == "__main__":
    main()
