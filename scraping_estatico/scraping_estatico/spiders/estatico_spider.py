import scrapy
import pandas as pd
import os


class EstaticoSpider(scrapy.Spider):
    name = "estatico_spider"

    def start_requests(self):
        ruta_excel = "extraccion_variables_eda/edaSisPricingInt_variables.xlsx"
        df = pd.read_excel(ruta_excel)

        estaticas = df[df["Formato"] == "E"][["Pais", "Variables", "Link"]].dropna()

        self.url_a_nombre = {
            row["Link"]: (
                row["Pais"].strip(),
                row["Variables"].strip()
            )
            for _, row in estaticas.iterrows()
        }

        for url in self.url_a_nombre:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        pais, variable = self.url_a_nombre[response.url]

        # Extraer <body>
        body = response.xpath("//body").get()

        # Limpiar el body: quitar scripts, estilos, footers, headers, etc.
        selector = scrapy.Selector(text=body)

        contenido_limpio = selector.xpath(
            "//body//*[not(self::script or self::style or self::footer or self::header or self::nav)]//text()"
        ).getall()

        texto_final = "\n".join([line.strip() for line in contenido_limpio if line.strip()])

        # Crear ruta
        nombre_archivo = f"{pais.lower().replace(' ', '_')}_{variable.lower().replace(' ', '_')}.txt"
        ruta_guardado = os.path.join("extraccion_variables_eda", "dataset", "paginas", nombre_archivo)

        os.makedirs(os.path.dirname(ruta_guardado), exist_ok=True)

        with open(ruta_guardado, "w", encoding="utf-8") as f:
            f.write(texto_final)

        self.logger.info(f"Guardado: {ruta_guardado}")
