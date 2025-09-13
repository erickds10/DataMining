# Imagen base oficial de Mage
FROM mageai/mageai:latest

# Establecer directorio de trabajo
WORKDIR /home/src

# (Opcional) Instala dependencias adicionales que usarán tus pipelines
# Por ejemplo: requests, pandas, psycopg2, sqlalchemy
RUN pip install --no-cache-dir requests pandas psycopg2 sqlalchemy
