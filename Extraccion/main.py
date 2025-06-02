import Extraccion_urls


def iniciar_proceso():
    archivo_excel = 'Extraccion\Dataset\edaSisPricingInt.xlsx'
    
    # Extraer URLs del archivo Excel
    Extraccion_urls.extraer_urls_excel(archivo_excel)
    
    # Descargar los códigos fuente de las URLs extraídas
    Extraccion_urls.descargar_codigos_fuente()