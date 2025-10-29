import csv
import json
import sys
from pathlib import Path
from bs4 import BeautifulSoup
from collections import defaultdict
import re

def limpiar_archivos_dinamicos():
    # Ruta base: carpeta donde está este script
    base_path = Path(__file__).resolve().parent
    project_root = base_path.parent

    pipeline_funcs = None
    pipeline_src = project_root / "limpieza_llm" / "src"
    if pipeline_src.exists():
        sys_path_str = str(pipeline_src)
        if sys_path_str not in sys.path:
            sys.path.append(sys_path_str)
        try:
            from pipeline_with_config import (
                try_load_yaml,
                Canonicalizer,
                build_prompt,
                llm_call,
                DEFAULT_CONFIG,
            )
            pipeline_funcs = {
                "try_load_yaml": try_load_yaml,
                "Canonicalizer": Canonicalizer,
                "build_prompt": build_prompt,
                "llm_call": llm_call,
                "DEFAULT_CONFIG": DEFAULT_CONFIG,
            }
        except ImportError as exc:
            print(f"[WARN] No se pudo importar pipeline_with_config (se omitirá la generación de llm_cleaned_decisions): {exc}")
    else:
        print("[WARN] Directorio limpieza_llm/src no encontrado; se omitirá la generación de llm_cleaned_decisions.")

    pipeline_config_path = project_root / "limpieza_llm" / "config" / "categories.yaml"

    # Rutas a las carpetas de entrada y salida
    html_dir = base_path / "dataset" / "paginas_descargadas"
    txt_dir = base_path / "dataset" / "txt_limpios"
    txt_dir.mkdir(parents=True, exist_ok=True)

    # Verificar existencia de carpeta HTML
    if not html_dir.exists():
        print(f"⚠️ La carpeta {html_dir} no existe.")
        return

    # Obtener todos los archivos HTML
    archivos_html = list(html_dir.glob("*.html"))
    if not archivos_html:
        print("⚠️ No se encontraron archivos HTML para limpiar.")
        return

    print(f"🧹 Limpiando {len(archivos_html)} archivos HTML...")

    # Patrones y expresiones para filtrar información relevante
    skip_keywords = (
        "cookie",
        "aviso de privacidad",
        "aceptar",
        "cargando comentarios",
        "mostrar más",
        "mostrar mas",
        "comparte",
        "combo",
        "cantidad máxima",
        "equivale a",
        "agregar",
        "añadir",
        "suscríbete",
        "suscribete",
        "inicio",
        "carrito",
        "categoría",
        "categorias",
        "login",
        "ingresar",
        "registr",
        "imágenes del producto",
        "imagenes del producto",
        "promociones exclusivas",
    )
    stop_sections = (
        "productos relacionados",
        "también te puede interesar",
        "tambien te puede interesar",
        "te puede interesar",
        "clientes también compraron",
        "clientes tambien compraron",
        "otros productos",
    )
    section_aliases = {
        "informacion": "Información",
        "información": "Información",
        "descripcion": "Descripción",
        "descripción": "Descripción",
        "especificaciones": "Especificaciones",
        "caracteristicas": "Características",
        "caracteristicas importantes": "Características",
        "características": "Características",
        "características importantes": "Características",
        "beneficios": "Beneficios",
        "detalles": "Detalles",
    }
    category_keywords = {
        "supermercado",
        "despensa",
        "granos y semillas",
        "categorías",
        "categorias",
        "departamento",
    }
    price_regex = re.compile(
        r"(?P<symbol>[\$€£₡S\/RD\.Bs]*\s?)(?P<amount>\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})|\d+)",
        re.IGNORECASE,
    )
    currency_indicators = (
        "$",
        "€",
        "£",
        "₡",
        "₲",
        "₱",
        "S/",
        "RD$",
        "US$",
        "Bs",
        "R$",
        "Q",
    )
    measurement_regex = re.compile(
        r"\b\d+[.,]?\d*\s?(?:kg|g|gr|gramos|l|lt|litro|litros|ml|cc|oz|lb|libras|unidades|unidad|pza|pzas|pieza|piezas|botella|bolsa)\b",
        re.IGNORECASE,
    )
    currency_code_regex = re.compile(r'currency"\s*:\s*"([A-Z]{3})"')

    symbol_to_currency = {
        "S/": "PEN",
        "RD$": "DOP",
        "US$": "USD",
        "R$": "BRL",
        "Bs": "VES",
        "Bs.": "VES",
        "₡": "CRC",
        "¢": "CRC",
        "Q": "GTQ",
        "₲": "PYG",
        "C$": "NIO",
        "L": "HNL",
    }
    currency_to_country = {
        "ARS": "AR",
        "BRL": "BR",
        "BOB": "BO",
        "CLP": "CL",
        "COP": "CO",
        "CRC": "CR",
        "DOP": "DO",
        "GTQ": "GT",
        "MXN": "MX",
        "PAB": "PA",
        "PEN": "PE",
        "PYG": "PY",
        "USD": "US",
        "UYU": "UY",
        "VES": "VE",
        "HNL": "HN",
        "NIO": "NI",
        "SVC": "SV",
    }

    def normalize_amount(amount_str: str):
        if not amount_str:
            return None
        cleaned = amount_str.replace(" ", "")
        if cleaned.count(",") and cleaned.count("."):
            if cleaned.rfind(",") > cleaned.rfind("."):
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        elif cleaned.count(","):
            parts = cleaned.split(",")
            if len(parts[-1]) in (1, 2):
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        else:
            cleaned = cleaned.replace(",", "")
        try:
            return float(cleaned)
        except ValueError:
            return None

    def parse_price_components(price_text: str, currency_hint: str):
        if not price_text:
            return None, currency_hint if currency_hint else None, ""
        text = price_text.strip()
        currency_code = currency_hint.upper() if currency_hint else None
        match_paren = re.search(r"\(([A-Z]{2,5})\)", text)
        if match_paren:
            currency_code = match_paren.group(1).upper()
            text = text[:match_paren.start()].strip()
        match = price_regex.search(text)
        amount = None
        symbol = ""
        if match:
            symbol = match.group("symbol").strip()
            amount_str = match.group("amount").strip()
            amount = normalize_amount(amount_str)
        if not currency_code and symbol:
            currency_code = symbol_to_currency.get(symbol) or symbol_to_currency.get(symbol.rstrip("."))
        return amount, currency_code, symbol

    def infer_country_from_currency(currency_code: str) -> str:
        if not currency_code:
            return ""
        return currency_to_country.get(currency_code.upper(), "")

    def safe_join(values, separator=" | "):
        if not values:
            return ""
        filtered = [v.strip() for v in values if v]
        return separator.join(filtered)

    def concat_sentences(values):
        if not values:
            return ""
        filtered = [v.strip() for v in values if v]
        return " ".join(filtered)

    def line_has_price(line: str) -> bool:
        if not any(ind in line for ind in currency_indicators):
            return False
        return bool(price_regex.search(line))

    def should_skip(line: str) -> bool:
        lower = line.lower()
        return any(keyword in lower for keyword in skip_keywords)

    def should_stop(line: str) -> bool:
        lower = line.lower()
        return any(keyword in lower for keyword in stop_sections)

    def clean_lines(raw_lines):
        cleaned_lines = []
        seen = set()
        pending_key = None

        for line in raw_lines:
            stripped = line.strip()
            if not stripped:
                continue

            normalized = stripped.lower()

            if should_stop(stripped):
                break

            if should_skip(stripped):
                continue

            if all(ch in ".•-*–—" for ch in stripped):
                continue

            if normalized in category_keywords:
                continue

            if stripped.replace(" ", "") == ":" and cleaned_lines:
                pending_key = cleaned_lines.pop()
                seen.discard(pending_key.lower())
                continue

            if stripped.endswith(":"):
                pending_key = stripped[:-1].strip()
                continue

            if pending_key:
                combined = f"{pending_key}: {stripped}"
                if combined.lower() not in seen:
                    cleaned_lines.append(combined)
                    seen.add(combined.lower())
                pending_key = None
                continue

            # Evitar duplicados exactos en minúsculas
            if normalized in seen:
                continue

            cleaned_lines.append(stripped)
            seen.add(normalized)

        return cleaned_lines

    def extract_currency_code(raw_html: str):
        match = currency_code_regex.search(raw_html)
        if match:
            return match.group(1)
        return None

    def extract_measurement(lines):
        for line in lines:
            match = measurement_regex.search(line)
            if match:
                return match.group(0)
        return None

    def extract_price(lines):
        for line in lines:
            if not any(ind in line for ind in currency_indicators):
                continue
            match = price_regex.search(line)
            if match:
                symbol = match.group("symbol").strip()
                amount = match.group("amount").strip()
                if amount.replace("0", "").replace(".", "").replace(",", ""):
                    return f"{symbol}{amount}".strip()
        return None

    def extract_reference(lines):
        for line in lines:
            if line.lower().startswith("referencia:"):
                return line.split(":", 1)[1].strip()
        return None

    def extract_seller(lines):
        for line in lines:
            lower = line.lower()
            if lower.startswith("vendido y entregado por:"):
                return line.split(":", 1)[1].strip()
        return None

    def extract_product_and_brand(lines):
        producto = None
        marca = None
        for index, line in enumerate(lines):
            lower = line.lower()
            if lower in section_aliases:
                continue
            if producto is None and len(line.split()) > 1:
                producto = line
                continue
            if producto and marca is None:
                if ":" in line:
                    continue
                if lower in section_aliases:
                    continue
                if len(line.split()) <= 4:
                    marca = line
                    break
        return producto, marca

    def extract_sections(lines):
        sections = defaultdict(list)
        current_section = None
        for line in lines:
            normalized = line.lower()
            if normalized in section_aliases:
                current_section = section_aliases[normalized]
                continue
            if ":" in line and line.split(":", 1)[0].lower() in section_aliases:
                section_key = section_aliases[line.split(":", 1)[0].lower()]
                sections[section_key].append(line.split(":", 1)[1].strip())
                current_section = section_key
                continue
            if current_section:
                sections[current_section].append(line)
        return sections

    dataset_rows = []
    items_csv_path = base_path / "llm_artifacts" / "items_desde_txt.csv"
    llm_csv_path = base_path / "dataset" / "llm_cleaned_decisions.csv"
    llm_jsonl_path = base_path / "dataset" / "llm_cleaned_decisions.jsonl"

    def serialize_for_csv(row: dict, fieldnames):
        serialized = {}
        for field in fieldnames:
            value = row.get(field, "")
            if value is None:
                serialized[field] = ""
            elif isinstance(value, float):
                serialized[field] = f"{value:.2f}"
            elif isinstance(value, (list, dict)):
                serialized[field] = json.dumps(value, ensure_ascii=False)
            else:
                serialized[field] = value
        return serialized

    def sort_key(row: dict):
        primary = (row.get("product_name") or row.get("title") or "").strip().lower()
        secondary = str(row.get("source_id") or "")
        return (primary, secondary)

    def write_items_dataset(rows: list):
        if not rows:
            print("[WARN] No se generaron filas para items_desde_txt.csv.")
            return
        rows_sorted = sorted(rows, key=sort_key)
        items_csv_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "source_id",
            "title",
            "description",
            "breadcrumbs",
            "price_raw",
            "currency_raw",
            "url",
            "seller",
            "availability",
            "country",
            "product_name",
            "brand",
            "reference",
            "unit",
            "price_amount",
            "price_currency",
            "price_symbol",
            "price_text",
            "information_text",
            "description_text",
            "features_text",
            "specifications_text",
            "benefits_text",
            "details_text",
            "other_sections",
            "sections",
            "txt_path",
            "html_path",
            "es_status",
        ]
        with open(items_csv_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows_sorted:
                writer.writerow(serialize_for_csv(row, fieldnames))
        print(f"📄 Dataset actualizado: {items_csv_path.relative_to(project_root)} ({len(rows_sorted)} filas, orden ascendente por producto)")

    def generate_llm_outputs(rows: list):
        if not rows:
            return
        if not pipeline_funcs:
            print("[WARN] No se generaron llm_cleaned_decisions.* (pipeline no disponible).")
            return
        cfg = None
        try:
            cfg = pipeline_funcs["try_load_yaml"](str(pipeline_config_path))
        except Exception as exc:
            print(f"[WARN] Configuración {pipeline_config_path.name} inválida: {exc}. Se usará DEFAULT_CONFIG.")
            cfg = pipeline_funcs.get("DEFAULT_CONFIG")
        if not cfg:
            cfg = pipeline_funcs.get("DEFAULT_CONFIG")
        try:
            canon = pipeline_funcs["Canonicalizer"](cfg)
        except Exception as exc:
            print(f"[WARN] Falló la inicialización del canonicalizador: {exc}")
            return

        decision_rows = []
        for row in rows:
            prompt_row = {
                "title": row.get("title", ""),
                "description": row.get("description", ""),
                "breadcrumbs": row.get("breadcrumbs", ""),
                "price_raw": row.get("price_raw", ""),
                "currency_raw": row.get("currency_raw", ""),
                "url": row.get("url", ""),
                "seller": row.get("seller", ""),
                "availability": row.get("availability", ""),
                "country": row.get("country", ""),
            }
            prompt = pipeline_funcs["build_prompt"](prompt_row)
            data = pipeline_funcs["llm_call"](prompt, canon)
            judgement = data.get("judgement", {})
            normalized = data.get("normalized", {})
            reasons = judgement.get("reasons") or []

            decision_row = dict(row)
            decision_row["category_canonical"] = normalized.get("category")
            decision_row["decision"] = "keep" if judgement.get("keep_or_discard") == "keep" else "discard"
            decision_row["match_score"] = judgement.get("match_score")
            decision_row["reasons"] = ";".join(reasons)
            decision_rows.append(decision_row)

        if not decision_rows:
            print("[WARN] No se generaron filas para llm_cleaned_decisions.")
            return

        decision_rows_sorted = sorted(decision_rows, key=sort_key)
        llm_csv_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "source_id",
            "title",
            "description",
            "breadcrumbs",
            "price_raw",
            "currency_raw",
            "url",
            "seller",
            "availability",
            "country",
            "product_name",
            "brand",
            "reference",
            "unit",
            "price_amount",
            "price_currency",
            "price_symbol",
            "price_text",
            "information_text",
            "description_text",
            "features_text",
            "specifications_text",
            "benefits_text",
            "details_text",
            "other_sections",
            "sections",
            "txt_path",
            "html_path",
            "es_status",
            "category_canonical",
            "decision",
            "match_score",
            "reasons",
        ]
        with open(llm_csv_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for row in decision_rows_sorted:
                writer.writerow(serialize_for_csv(row, fieldnames))
        with open(llm_jsonl_path, "w", encoding="utf-8") as jf:
            for row in decision_rows_sorted:
                json.dump(row, jf, ensure_ascii=False)
                jf.write("\n")
        print(f"🤖 Archivo actualizado: {llm_csv_path.relative_to(project_root)} ({len(decision_rows_sorted)} filas, orden ascendente por producto)")
        print(f"🤖 Archivo actualizado: {llm_jsonl_path.relative_to(project_root)} ({len(decision_rows_sorted)} filas)")

    for html_file in archivos_html:
        try:
            with open(html_file, "r", encoding="utf-8") as f:
                raw_html = f.read()
                soup = BeautifulSoup(raw_html, "html.parser")

            # Eliminar etiquetas innecesarias
            for tag in soup(["script", "style", "header", "footer", "nav", "aside", "noscript"]):
                tag.decompose()

            # Extraer texto del <body>
            body = soup.body
            if body:
                texto = body.get_text(separator="\n", strip=True)
                lineas_limpias = clean_lines(texto.splitlines())
            else:
                lineas_limpias = []

            currency_code = extract_currency_code(raw_html)
            producto, marca = extract_product_and_brand(lineas_limpias)
            precio = extract_price(lineas_limpias)
            unidad = extract_measurement(lineas_limpias)
            referencia = extract_reference(lineas_limpias)
            vendedor = extract_seller(lineas_limpias)
            secciones_originales = extract_sections(lineas_limpias)

            monto_precio, currency_detected, price_symbol = parse_price_components(precio, currency_code)
            currency_final = currency_detected or currency_code
            price_raw_value = f"{monto_precio:.2f}" if monto_precio is not None else ""
            country_code = infer_country_from_currency(currency_final)

            secciones_limpias = {}
            salida = []
            if producto:
                salida.append(f"Producto: {producto}")
            if marca:
                salida.append(f"Marca: {marca}")
            if referencia:
                salida.append(f"Referencia: {referencia}")
            if unidad:
                salida.append(f"Unidad de medida: {unidad}")
            if vendedor:
                salida.append(f"Vendido por: {vendedor}")
            if precio:
                if currency_final:
                    salida.append(f"Precio: {precio} ({currency_final})")
                else:
                    salida.append(f"Precio: {precio}")
            elif currency_final:
                salida.append(f"Moneda: {currency_final}")

            for nombre_seccion, contenidos in secciones_originales.items():
                depurados = []
                for texto_seccion in contenidos:
                    if should_skip(texto_seccion):
                        continue
                    if line_has_price(texto_seccion):
                        continue
                    if texto_seccion.lower().startswith("vendido y entregado por:"):
                        continue
                    if texto_seccion.lower() in section_aliases:
                        continue
                    depurados.append(texto_seccion)
                if depurados:
                    secciones_limpias[nombre_seccion] = depurados
                    salida.append(f"{nombre_seccion}: {' '.join(depurados)}")

            texto_limpio = "\n".join(salida)

            # Guardar como TXT con mismo nombre
            nombre_txt = html_file.stem + ".txt"
            txt_path = txt_dir / nombre_txt
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(texto_limpio)

            information_text = concat_sentences(secciones_limpias.get("Información", []))
            description_text = concat_sentences(secciones_limpias.get("Descripción", []))
            features_text = safe_join(secciones_limpias.get("Características", []))
            specifications_text = safe_join(secciones_limpias.get("Especificaciones", []))
            benefits_text = safe_join(secciones_limpias.get("Beneficios", []))
            details_text = safe_join(secciones_limpias.get("Detalles", []))
            other_sections_dict = {
                nombre: safe_join(contenidos)
                for nombre, contenidos in secciones_limpias.items()
                if nombre not in {"Información", "Descripción", "Características", "Especificaciones", "Beneficios", "Detalles"}
            }
            other_sections_text = "; ".join(
                f"{nombre}: {texto}"
                for nombre, texto in other_sections_dict.items()
                if texto
            )
            description_field = concat_sentences(
                [
                    information_text,
                    description_text,
                    specifications_text,
                    benefits_text,
                    details_text,
                ]
            )
            breadcrumbs_field = " > ".join(
                [value for value in (marca, unidad, referencia) if value]
            )
            seller_value = vendedor if vendedor else "Desconocido"

            dataset_row = {
                "source_id": html_file.stem,
                "title": producto or html_file.stem,
                "description": description_field,
                "breadcrumbs": breadcrumbs_field,
                "price_raw": price_raw_value,
                "currency_raw": currency_final or "",
                "url": "",
                "seller": seller_value,
                "availability": "unknown",
                "country": country_code or "unknown",
                "product_name": producto or "",
                "brand": marca or "",
                "reference": referencia or "",
                "unit": unidad or "",
                "price_amount": monto_precio,
                "price_currency": currency_final or "",
                "price_symbol": price_symbol,
                "price_text": precio or "",
                "information_text": information_text,
                "description_text": description_text,
                "features_text": features_text,
                "specifications_text": specifications_text,
                "benefits_text": benefits_text,
                "details_text": details_text,
                "other_sections": other_sections_text,
                "sections": secciones_limpias,
                "txt_path": str(txt_path.relative_to(base_path)),
                "html_path": str(html_file.relative_to(base_path)),
                "es_status": "EN",
            }
            dataset_rows.append(dataset_row)

            print(f"✅ Limpio y guardado: {txt_path.name}")

        except Exception as e:
            print(f"❌ Error limpiando {html_file.name}: {e}")

    write_items_dataset(dataset_rows)
    generate_llm_outputs(dataset_rows)

if __name__ == "__main__":
    limpiar_archivos_dinamicos()
