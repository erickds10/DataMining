FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copiar requirements
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY src /app/src

# Entry point: nuestro script CLI
ENTRYPOINT ["python", "-m", "src.build_features"]