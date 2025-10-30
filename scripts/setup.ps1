# Requires: PowerShell 5+, Python 3 on PATH (py launcher preferred)
param(
    [string]$VenvPath = ".venv"
)

Write-Host "==> Setting up virtual environment at $VenvPath" -ForegroundColor Cyan

if (-Not (Test-Path $VenvPath)) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        py -3 -m venv $VenvPath
    } else {
        python -m venv $VenvPath
    }
}

$activate = Join-Path $VenvPath "Scripts\Activate.ps1"
if (-Not (Test-Path $activate)) {
    Write-Error "Activation script not found at $activate"
    exit 1
}

Write-Host "==> Activating virtual environment" -ForegroundColor Cyan
. $activate

Write-Host "==> Upgrading pip/setuptools/wheel" -ForegroundColor Cyan
python -m pip install -U pip setuptools wheel

if (Test-Path "requirements.txt") {
    Write-Host "==> Installing dependencies from requirements.txt" -ForegroundColor Cyan
    pip install -r requirements.txt
} elseif (Test-Path "pyproject.toml" -or Test-Path "setup.py") {
    Write-Host "==> Installing project in editable mode" -ForegroundColor Cyan
    pip install -e .
} else {
    Write-Warning "No requirements.txt or project metadata found. Skipping installs."
}

if (-Not (Test-Path ".env") -and (Test-Path ".env.example")) {
    Write-Host "==> Creating .env from .env.example" -ForegroundColor Cyan
    Copy-Item .env.example .env
    Write-Host "   Edit .env to fill in real values" -ForegroundColor Yellow
}

Write-Host "==> Done. Next steps:" -ForegroundColor Green
Write-Host "   1) Edit .env with your credentials (if needed)"
Write-Host "   2) Run tests:    pytest" 
Write-Host "   3) Run server:   python src/main.py"

