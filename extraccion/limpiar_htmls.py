import os
from pathlib import Path
from bs4 import BeautifulSoup

def limpiar_archivos_dinamicos():
    # Ruta base: carpeta donde está este script
    base_path = Path(__file__).resolve().parent

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

    for html_file in archivos_html:
        try:
            with open(html_file, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f, "html.parser")

            # Eliminar etiquetas innecesarias
            for tag in soup(["script", "style", "header", "footer", "nav", "aside", "noscript"]):
                tag.decompose()

            # Extraer texto del <body>
            body = soup.body
            if body:
                texto = body.get_text(separator="\n", strip=True)
                texto_limpio = "\n".join(
                    [line.strip() for line in texto.splitlines() if line.strip()]
                )
            else:
                texto_limpio = ""

            # Guardar como TXT con mismo nombre
            nombre_txt = html_file.stem + ".txt"
            txt_path = txt_dir / nombre_txt
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(texto_limpio)

            print(f"✅ Limpio y guardado: {txt_path.name}")

        except Exception as e:
            print(f"❌ Error limpiando {html_file.name}: {e}")

if __name__ == "__main__":
    limpiar_archivos_dinamicos()
