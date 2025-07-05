import pandas as pd 
import subprocess 
import os 
 
archivo_excel = os.path.join('dataset', 'edaSisPricingNuevo.xlsx') 
 
def extraer_urls_excel(archivo_excel, columna_url='URL', columna_tipo='Tipo Pagina', hoja=0): 
    carpeta_destino = os.path.join('dataset', 'datos_extraidos') 
    os.makedirs(carpeta_destino, exist_ok=True) 
    
    # Rutas de archivos de salida
    ruta_estaticas = os.path.join(carpeta_destino, 'estaticas.txt')
    ruta_dinamicas = os.path.join(carpeta_destino, 'dinamicas.txt')
 
    # Leer el archivo Excel
    ruta_absoluta = os.path.abspath(archivo_excel) 
    print(f"Buscando archivo en: {ruta_absoluta}")
    print(f"¿Existe el archivo? {os.path.exists(archivo_excel)}")
    
    if not os.path.exists(archivo_excel):
        print("ERROR: El archivo Excel no existe en la ruta especificada")
        return 0, 0
    
    df = pd.read_excel(ruta_absoluta, sheet_name=hoja) 
    
    # Filtrar filas donde tanto URL como Tipo Pagina no sean nulos
    df_limpio = df.dropna(subset=[columna_url, columna_tipo])
    
    # Separar URLs por tipo
    urls_estaticas = df_limpio[df_limpio[columna_tipo] == 'E'][columna_url]
    urls_dinamicas = df_limpio[df_limpio[columna_tipo] == 'D'][columna_url]
    
    # Guardar URLs estáticas
    with open(ruta_estaticas, 'w', encoding='utf-8') as archivo: 
        for url in urls_estaticas: 
            archivo.write(str(url) + '\n') 
    
    # Guardar URLs dinámicas
    with open(ruta_dinamicas, 'w', encoding='utf-8') as archivo: 
        for url in urls_dinamicas: 
            archivo.write(str(url) + '\n') 
 
    print(f"URLs estáticas guardadas en: {ruta_estaticas} ({len(urls_estaticas)} URLs)")
    print(f"URLs dinámicas guardadas en: {ruta_dinamicas} ({len(urls_dinamicas)} URLs)")
    
    return len(urls_estaticas), len(urls_dinamicas)
 
 
def descargar_paginas_scrapy_y_selenium(): 
    try: 
        project_dir = os.path.join(os.path.dirname(os.getcwd()), 'web_scraper_spi') 
 
        command = f"cd {project_dir} && scrapy crawl page_downloader" 
        subprocess.run(command, shell=True, check=True) 
 
        print("Descarga completada con Scrapy!") 
    except Exception as e: 
        print(f"Error al ejecutar Scrapy: {e}") 

def extraccion_controller(): 
    try:
        # Extraer URLs separadas por tipo
        num_estaticas, num_dinamicas = extraer_urls_excel(archivo_excel)
        
        if num_estaticas == 0 and num_dinamicas == 0:
            print("No se procesaron URLs. Verificar archivo Excel.")
            return
        # Ejecutar descarga
        descargar_paginas_scrapy_y_selenium()
        
        print(f"Proceso completado: {num_estaticas} URLs estáticas y {num_dinamicas} URLs dinámicas procesadas")
    except Exception as e:
        print(f"Error en el proceso de extracción: {e}")

# Función adicional para verificar los tipos de página en el Excel
def verificar_tipos_pagina(archivo_excel, columna_tipo='Tipo Pagina', hoja=0):
    """Función auxiliar para verificar qué tipos de página existen en el Excel"""
    try:
        ruta_absoluta = os.path.abspath(archivo_excel)
        df = pd.read_excel(ruta_absoluta, sheet_name=hoja)
        tipos_unicos = df[columna_tipo].value_counts()
        print("Tipos de página encontrados:")
        print(tipos_unicos)
        return tipos_unicos
    except Exception as e:
        print(f"Error al verificar tipos de página: {e}")
        return None