Write-Host "Kontrola virtualniho prostredi..."

if (-Not (Test-Path ".\venv")) {
    Write-Host "Venv nenalezen, vytvarim nove..."
    python -m venv venv

    Write-Host "Aktivuji nove virtualni prostredi..."
    & .\venv\Scripts\Activate.ps1

    if (Test-Path ".\backend\requirements.txt") {
        Write-Host "Instaluji zavislosti z backend/requirements.txt..."
        pip install --upgrade pip
        pip install -r .\backend\requirements.txt
    }
}
else {
    Write-Host "Venv jiz existuje."
    & .\venv\Scripts\Activate.ps1
}

Write-Host "Prechazim do backend..."
Set-Location backend

Write-Host "Spoustim Uvicorn server..."
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
