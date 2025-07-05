from api_trading import obtener_indicadores
import os

# Lista directa de países LATAM
paises_latam = [
    "argentina", "brasil", "chile", "colombia", "4cuador",
    "México", "Perú", "Uruguay", "Paraguay", "Bolivia"
]

# Obtener los datos
df = obtener_indicadores(paises_latam)

# Crear carpeta si no existe
os.makedirs("extraccion/dataset", exist_ok=True)

# Guardar en JSON (en lugar de Excel)
ruta_salida = "extraccion/dataset/indicadores_latam.json"
df.to_json(ruta_salida, orient="records", indent=4, force_ascii=False)

print("🔍 Iniciando extracción de datos...")

df = obtener_indicadores(paises_latam)

print("📊 Datos obtenidos, guardando...")

# Crear carpeta
os.makedirs("extraccion/dataset", exist_ok=True)

# Guardar JSON
ruta_salida = "extraccion/dataset/indicadores_latam.json"
df.to_json(ruta_salida, orient="records", indent=4, force_ascii=False)

print("✅ Datos guardados en JSON en:", ruta_salida)
