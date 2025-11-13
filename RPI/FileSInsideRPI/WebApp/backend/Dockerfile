# ✅ Backend (FastAPI / uvicorn)
FROM python:3.11-slim

WORKDIR /app

# závislosti
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# kód
COPY . .

# port pro uvicorn
EXPOSE 8000

# spuštění backendu
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
