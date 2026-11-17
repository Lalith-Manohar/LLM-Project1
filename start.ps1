# NEXORA - Single-Command Development Launcher
# Starts FastAPI Backend and React/Vite Frontend in separate PowerShell windows

$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"
$PythonExe = Join-Path $BackendDir ".venv\Scripts\python.exe"
$NodeModulesDir = Join-Path $FrontendDir "node_modules"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "       NEXORA Retail Management & Intelligence System     " -ForegroundColor Cyan
Write-Host "                Development Launcher                      " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Verify Backend Virtual Environment
Write-Host "[1/2] Verifying Python virtual environment..." -ForegroundColor Yellow
if (-not (Test-Path $PythonExe)) {
    Write-Host "[ERROR] Python virtual environment executable not found at:" -ForegroundColor Red
    Write-Host "        $PythonExe" -ForegroundColor Red
    Write-Host "Please set up the virtual environment first:" -ForegroundColor White
    Write-Host "  cd backend" -ForegroundColor White
    Write-Host "  python -m venv .venv" -ForegroundColor White
    Write-Host "  .\.venv\Scripts\pip install -r requirements.txt" -ForegroundColor White
    exit 1
}
Write-Host "      Found: $PythonExe" -ForegroundColor Green

# 2. Verify Frontend Dependencies
Write-Host "[2/2] Verifying Frontend dependencies (node_modules)..." -ForegroundColor Yellow
if (-not (Test-Path $NodeModulesDir)) {
    Write-Host "[ERROR] Frontend dependencies not found at:" -ForegroundColor Red
    Write-Host "        $NodeModulesDir" -ForegroundColor Red
    Write-Host "Please install frontend dependencies first:" -ForegroundColor White
    Write-Host "  cd frontend" -ForegroundColor White
    Write-Host "  npm install" -ForegroundColor White
    exit 1
}
Write-Host "      Found: $NodeModulesDir" -ForegroundColor Green
Write-Host ""

# 3. Launch Backend in separate PowerShell window
Write-Host "Starting FastAPI Backend server in a new window..." -ForegroundColor Cyan
$BackendCommand = "Set-Location '$BackendDir'; & '$PythonExe' -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
Start-Process powershell.exe -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $BackendCommand

# 4. Launch Frontend in separate PowerShell window
Write-Host "Starting React/Vite Frontend client in a new window..." -ForegroundColor Cyan
$FrontendCommand = "Set-Location '$FrontendDir'; npm run dev"
Start-Process powershell.exe -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $FrontendCommand

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "         NEXORA Development Services Launched!            " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Access Points:" -ForegroundColor White
Write-Host "  - Frontend Client:      http://localhost:5173" -ForegroundColor Yellow
Write-Host "  - Backend API:          http://localhost:8000" -ForegroundColor Yellow
Write-Host "  - Swagger Documentation: http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host ""
Write-Host "Process windows will remain open to display real-time logs." -ForegroundColor Gray
Write-Host "Press Ctrl+C in their respective windows to stop the services." -ForegroundColor Gray
Write-Host ""
