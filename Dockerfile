FROM postgres:17

# Instala o PostGIS compatível com a versão do Postgres instalada
RUN apt-get update && apt-get install -y \
    postgresql-17-postgis-3 \
    postgresql-17-postgis-3-scripts \
    && rm -rf /var/lib/apt/lists/*
