FROM python:3.11-slim

WORKDIR /app

# Java é necessário para o driver JDBC do SAP MaxDB
RUN apt-get update && apt-get install -y \
    default-jdk \
    && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/default-java
ENV PATH="$JAVA_HOME/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Garante que a pasta de dados persiste (monte como volume em produção)
RUN mkdir -p dados_ocupacao

CMD ["python", "main.py"]
