
Write-Host "Aktivuji virtualni prostredi..."
& .\venv\Scripts\Activate.ps1

Write-Host "Prechazim do backend..."
Set-Location backend

Write-Host "Spoustim Uvicorn server..."
python -m uvicorn main:app --reload
