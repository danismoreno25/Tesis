#!/usr/bin/env python3
import csv
import json
import sys
from pathlib import Path


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


def load_items_dataset(csv_path: Path):
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            price_amount = row.get("price_amount")
            try:
                row["price_amount"] = float(price_amount) if price_amount else None
            except ValueError:
                row["price_amount"] = None
            sections_raw = row.get("sections", "")
            if sections_raw:
                try:
                    row["sections"] = json.loads(sections_raw)
                except json.JSONDecodeError:
                    row["sections"] = {}
            else:
                row["sections"] = {}
            rows.append(row)
    return rows


def main():
    base_path = Path(__file__).resolve().parent
    project_root = base_path.parent
    dataset_csv = base_path / "llm_artifacts" / "items_desde_txt.csv"
    if not dataset_csv.exists():
        print(f"[ERROR] No se encontró {dataset_csv}. Ejecuta primero limpiar_htmls.py.")
        return

    pipeline_src = project_root / "limpieza_llm" / "src"
    if not pipeline_src.exists():
        print("[ERROR] No se encontró limpieza_llm/src; imposible generar llm_cleaned_decisions.")
        return
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
    except ImportError as exc:
        print(f"[ERROR] No se pudo importar pipeline_with_config: {exc}")
        return

    rows = load_items_dataset(dataset_csv)
    if not rows:
        print("[WARN] items_desde_txt.csv está vacío; no se generó ninguna decisión.")
        return

    config_path = project_root / "limpieza_llm" / "config" / "categories.yaml"
    config = None
    try:
        config = try_load_yaml(str(config_path))
    except Exception as exc:
        print(f"[WARN] Configuración inválida ({config_path.name}): {exc}. Se usará DEFAULT_CONFIG.")
        config = DEFAULT_CONFIG
    if not config:
        config = DEFAULT_CONFIG

    try:
        canon = Canonicalizer(config)
    except Exception as exc:
        print(f"[ERROR] No fue posible inicializar Canonicalizer: {exc}")
        return

    def sort_key(row: dict):
        primary = (row.get("product_name") or row.get("title") or "").strip().lower()
        secondary = str(row.get("source_id") or "")
        return (primary, secondary)

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
        prompt = build_prompt(prompt_row)
        data = llm_call(prompt, canon)
        judgement = data.get("judgement", {})
        normalized = data.get("normalized", {})
        reasons = judgement.get("reasons") or []

        decision_row = dict(row)
        decision_row["category_canonical"] = normalized.get("category")
        decision_row["decision"] = "keep" if judgement.get("keep_or_discard") == "keep" else "discard"
        decision_row["match_score"] = judgement.get("match_score")
        decision_row["reasons"] = ";".join(reasons)
        decision_rows.append(decision_row)

    decision_rows_sorted = sorted(decision_rows, key=sort_key)
    llm_csv_path = base_path / "dataset" / "llm_cleaned_decisions.csv"
    llm_jsonl_path = base_path / "dataset" / "llm_cleaned_decisions.jsonl"
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


if __name__ == "__main__":
    main()
