import extraccion_urls as extract

def iniciar_proceso():
    archivo_excel = 'dataset/edaSisPricingInt.xlsx'
    extract.extraer_urls_excel(archivo_excel)
    extract.descargar_codigos_fuente()

if __name__ == "__main__":
    iniciar_proceso()