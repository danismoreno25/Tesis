import os
from pathlib import Path
from bs4 import BeautifulSoup

def limpiar_archivos_dinamicos():
    base_path = Path(__file__).resolve().parent
    html_dir = base_path / "dataset" / "paginas"
    txt_dir = base_path / "dataset" / "txt_limpios"
    txt_dir.mkdir(parents=True, exist_ok=True)

    for html_file in html_dir.glob("*.html"):
        with open(html_file, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")

        # Eliminar scripts, estilos, headers, footers, navs
        for tag in soup(["script", "style", "header", "footer", "nav"]):
            tag.decompose()

        body = soup.body
        if body:
            texto = body.get_text(separator="\n")
            texto_limpio = "\n".join([line.strip() for line in texto.splitlines() if line.strip()])
        else:
            texto_limpio = ""

        # Guardar como .txt con el mismo nombre
        nombre_txt = html_file.stem + ".txt"
        txt_path = txt_dir / nombre_txt
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(texto_limpio)
        print(f"✅ Limpio y guardado: {txt_path}")

# Ejecutar
if __name__ == "__main__":
    limpiar_archivos_dinamicos()
