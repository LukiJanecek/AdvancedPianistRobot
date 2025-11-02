# ✅ Bázový image pro Raspberry Pi (ARM)
FROM python:3.11-slim

# Nastavení pracovní složky v kontejneru
WORKDIR /app

# Kopíruj požadavky a nainstaluj závislosti
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Zbytek kódu
COPY . .

# Nastavení příkazů pro spuštění
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
