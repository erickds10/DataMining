FROM python:3.11-slim

WORKDIR /app

# Dependencias del builder: psycopg2 para Postgres + SQLAlchemy + pandas
RUN pip install --no-cache-dir psycopg2-binary==2.9.9 SQLAlchemy==2.0.35 pandas==2.2.2

COPY build_obt.py /app/

ENTRYPOINT ["python", "build_obt.py"]