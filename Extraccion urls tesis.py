import pandas as pd
import requests
import os

def extraer_urls_excel(archivo_excel, nombre_columna='URL', nombre_archivo_salida='urls.txt', hoja=0):
    # Leer el Excel
    df = pd.read_excel(archivo_excel, sheet_name=hoja)

    urls = df[nombre_columna].dropna()

    with open(nombre_archivo_salida, 'w', encoding='utf-8') as archivo:
        for url in urls:
            archivo.write(str(url) + '\n')

    print(f"Se han guardado todas las URLs en '{nombre_archivo_salida}'.")

def descargar_codigos_fuente(nombre_archivo_urls='urls.txt', carpeta_destino='paginas_descargadas'):
    os.makedirs(carpeta_destino, exist_ok=True)

    with open(nombre_archivo_urls, 'r', encoding='utf-8') as archivo:
        urls = archivo.readlines()

    for i, url in enumerate(urls, start=1):
        url = url.strip()
        if not url:
            continue
        try:
            print(f"Descargando ({i}/{len(urls)}): {url}")
            respuesta = requests.get(url, timeout=10)
            respuesta.raise_for_status()  

            nombre_archivo = os.path.join(carpeta_destino, f'pagina_{i}.txt')
            with open(nombre_archivo, 'w', encoding='utf-8') as f:
                f.write(respuesta.text)

        except requests.RequestException as e:
            print(f"Error al descargar {url}: {e}")

    print(f"\nTodos los códigos fuente se han guardado en '{carpeta_destino}'.")


archivo_excel = 'C:\\Users\\Usuario\\Downloads\\edaSisPricingInt.xlsx'

extraer_urls_excel(archivo_excel)


descargar_codigos_fuente()
