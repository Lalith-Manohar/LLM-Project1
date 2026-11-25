# NEXORA - Automated Windows Setup and Development Launcher
# Automatically prepares Python virtual environment, installs missing dependencies,
# verifies essential model/data assets, and launches FastAPI and React/Vite in separate windows.

$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"
$VenvDir = Join-Path $BackendDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$RequirementsFile = Join-Path $BackendDir "requirements.txt"
$NodeModulesDir = Join-Path $FrontendDir "node_modules"
$PackageJson = Join-Path $FrontendDir "package.json"
$PackageLock = Join-Path $FrontendDir "package-lock.json"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "       NEXORA Retail Management & Intelligence System     " -ForegroundColor Cyan
Write-Host "            Automated Setup & Development Launcher        " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

# Helper: Test if a local TCP port is already listening
function Test-PortListening ($port) {
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $iar = $tcp.BeginConnect("127.0.0.1", $port, $null, $null)
        $wait = $iar.AsyncWaitHandle.WaitOne(200, $false)
        if ($wait -and $tcp.Connected) {
            $tcp.EndConnect($iar)
            $tcp.Close()
            return $true
        }
        $tcp.Close()
        return $false
    } catch {
        return $false
    }
}

# Helper: Discover a compatible Python 3.10+ executable on Windows
function Find-CompatiblePython {
    $candidates = @(
        @{ Cmd = "py"; Args = @("-3.11") },
        @{ Cmd = "py"; Args = @("-3.12") },
        @{ Cmd = "py"; Args = @("-3.10") },
        @{ Cmd = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"; Args = @() },
        @{ Cmd = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"; Args = @() },
        @{ Cmd = "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe"; Args = @() },
        @{ Cmd = "$env:ProgramFiles\Python311\python.exe"; Args = @() },
        @{ Cmd = "$env:ProgramFiles\Python312\python.exe"; Args = @() },
        @{ Cmd = "$env:ProgramFiles\Python310\python.exe"; Args = @() },
        @{ Cmd = "C:\Python311\python.exe"; Args = @() },
        @{ Cmd = "C:\Python312\python.exe"; Args = @() },
        @{ Cmd = "C:\Python310\python.exe"; Args = @() },
        @{ Cmd = "py"; Args = @("-3") },
        @{ Cmd = "python"; Args = @() },
        @{ Cmd = "python3"; Args = @() }
    )

    foreach ($c in $candidates) {
        $cmd = $c.Cmd
        $argsList = $c.Args
        if ($cmd -like "*\*" -and -not (Test-Path $cmd)) { continue }
        if ($cmd -in @("py", "python", "python3") -and -not (Get-Command $cmd -ErrorAction SilentlyContinue)) { continue }
        try {
            $fullArgs = $argsList + @("-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
            $output = & $cmd $fullArgs 2>$null
            if ($LASTEXITCODE -eq 0 -and $output -match "^\d+\.\d+") {
                $parts = $output.Trim().Split(".")
                $maj = [int]$parts[0]
                $min = [int]$parts[1]
                if ($maj -eq 3 -and $min -ge 10) {
                    return @{
                        Cmd = $cmd
                        Args = $argsList
                        Version = $output.Trim()
                    }
                }
            }
        } catch {}
    }
    return $null
}

# -------------------------------------------------------------
# STEP 1: Verify Essential Datasets and Trained Model Artifacts
# -------------------------------------------------------------
Write-Host "[1/4] Verifying essential machine learning assets..." -ForegroundColor Yellow
$RequiredAssets = @(
    "backend\ml\data\processed\daily_product_demand.csv",
    "backend\ml\models\models_metadata.json",
    "backend\ml\models\demand_model_7d.joblib",
    "backend\ml\models\demand_model_15d.joblib",
    "backend\ml\models\demand_model_30d.joblib",
    "backend\ml\models\demand_model_90d.joblib"
)

$MissingAssets = @()
foreach ($assetRel in $RequiredAssets) {
    $assetPath = Join-Path $ProjectRoot $assetRel
    if (-not (Test-Path $assetPath)) {
        $MissingAssets += $assetRel
    }
}

if ($MissingAssets.Count -gt 0) {
    Write-Host ""
    Write-Host "[ERROR] Essential inference assets are missing from the repository:" -ForegroundColor Red
    foreach ($m in $MissingAssets) {
        Write-Host "  - $m" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "Please ensure you have downloaded the complete repository from branch 'uni_api_submission'." -ForegroundColor White
    Write-Host "Pre-trained models and processed time series are required for automated forecasting." -ForegroundColor White
    exit 1
}
Write-Host "      All 6 essential datasets and trained models verified." -ForegroundColor Green

$ExperimentalAssets = @(
    "backend\ml\models_task12\models_metadata.json",
    "backend\ml\models_task12\demand_model_7d.joblib",
    "backend\ml\models_task12\demand_model_15d.joblib",
    "backend\ml\models_task12\demand_model_30d.joblib",
    "backend\ml\models_task12\demand_model_90d.joblib"
)
$FoundExp = 0
foreach ($expRel in $ExperimentalAssets) {
    if (Test-Path (Join-Path $ProjectRoot $expRel)) { $FoundExp++ }
}
if ($FoundExp -eq $ExperimentalAssets.Count) {
    Write-Host "      Task 12 experimental models verified (all 4 horizons present)." -ForegroundColor Green
} else {
    Write-Host "      [INFO] Task 12 experimental models not fully present ($FoundExp/$($ExperimentalAssets.Count)). Experimental endpoints will report 503." -ForegroundColor Gray
}

# -------------------------------------------------------------
# STEP 2: Automatically Prepare Python Virtual Environment
# -------------------------------------------------------------
Write-Host "[2/4] Verifying Python virtual environment..." -ForegroundColor Yellow

$VenvUsable = $false
if (Test-Path $VenvPython) {
    try {
        $check = & $VenvPython -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($LASTEXITCODE -eq 0 -and $check -match "^\d+\.\d+") {
            $VenvUsable = $true
            Write-Host "      Found existing virtual environment: $VenvPython ($check)" -ForegroundColor Green
        }
    } catch {}
}

if (-not $VenvUsable) {
    Write-Host "      Virtual environment not found or invalid. Discovering host Python..." -ForegroundColor Yellow
    $hostPython = Find-CompatiblePython

    if (-not $hostPython) {
        Write-Host ""
        Write-Host "[ERROR] Compatible Python 3.10+ was not found on this computer." -ForegroundColor Red
        Write-Host "NEXORA requires Python 3.10, 3.11, or 3.12 (Python 3.11 recommended)." -ForegroundColor White
        Write-Host ""
        Write-Host "To resolve this:" -ForegroundColor White
        Write-Host "  1. Download Python from: https://www.python.org/downloads/windows/" -ForegroundColor Cyan
        Write-Host "  2. Run the installer and check the box: 'Add python.exe to PATH'." -ForegroundColor White
        Write-Host "  3. Open a new PowerShell window and run .\start.ps1 again." -ForegroundColor White
        exit 1
    }

    Write-Host "      Found host Python: $($hostPython.Cmd) $($hostPython.Args -join ' ') (Version $($hostPython.Version))" -ForegroundColor Green
    Write-Host "      Creating virtual environment at $VenvDir..." -ForegroundColor Yellow

    $createArgs = $hostPython.Args + @("-m", "venv", "$VenvDir")
    & $hostPython.Cmd $createArgs
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $VenvPython)) {
        Write-Host "[ERROR] Failed to create virtual environment." -ForegroundColor Red
        exit 1
    }
    Write-Host "      Virtual environment created successfully." -ForegroundColor Green
}

# -------------------------------------------------------------
# STEP 2B: Verify / Install Backend Dependencies
# -------------------------------------------------------------
$BackendMarker = Join-Path $VenvDir ".requirements_hash"
$ReqHash = (Get-FileHash -Path $RequirementsFile -Algorithm SHA256).Hash
$NeedsBackendInstall = $true

if (Test-Path $BackendMarker) {
    $SavedReqHash = (Get-Content $BackendMarker -ErrorAction SilentlyContinue).Trim()
    if ($SavedReqHash -eq $ReqHash) {
        try {
            $importCheck = & $VenvPython -c "import fastapi, uvicorn, pydantic, pydantic_settings, pandas, numpy, sklearn, joblib; print('READY')" 2>$null
            if ($LASTEXITCODE -eq 0 -and $importCheck -match "READY") {
                $NeedsBackendInstall = $false
            }
        } catch {}
    }
}

if ($NeedsBackendInstall) {
    Write-Host "      Installing backend dependencies from requirements.txt..." -ForegroundColor Yellow
    & $VenvPython -m pip install --disable-pip-version-check -r "$RequirementsFile"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to install backend dependencies via pip." -ForegroundColor Red
        exit 1
    }
    Set-Content -Path $BackendMarker -Value $ReqHash
    Write-Host "      Backend dependencies installed and verified." -ForegroundColor Green
} else {
    Write-Host "      Backend dependencies already satisfied." -ForegroundColor Green
}

# -------------------------------------------------------------
# STEP 2C: Auto-initialize Derived Datasets & Price Index (Fresh Clone)
# -------------------------------------------------------------
$CleanSalesCsv = Join-Path $ProjectRoot "backend\ml\data\processed\clean_gross_sales.csv"
$RawSalesCsv = Join-Path $ProjectRoot "backend\ml\data\raw\online_retail_II.csv"

if (-not (Test-Path $CleanSalesCsv) -and (Test-Path $RawSalesCsv)) {
    Write-Host "      Derived sales dataset (clean_gross_sales.csv) missing. Running preprocessing..." -ForegroundColor Yellow
    Push-Location (Join-Path $ProjectRoot "backend")
    try {
        & $VenvPython -m ml.src.preprocessing
        if ($LASTEXITCODE -eq 0 -and (Test-Path $CleanSalesCsv)) {
            Write-Host "      Derived sales dataset generated successfully." -ForegroundColor Green
        } else {
            Write-Host "      [WARNING] Preprocessing did not complete cleanly." -ForegroundColor Yellow
        }
    } finally {
        Pop-Location
    }
}

# -------------------------------------------------------------
# STEP 3: Verify Node.js, npm, and Frontend Dependencies
# -------------------------------------------------------------
Write-Host "[3/4] Verifying Frontend environment (Node.js & npm)..." -ForegroundColor Yellow

$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
$npmCmd = Get-Command npm -ErrorAction SilentlyContinue

if (-not $nodeCmd -or -not $npmCmd) {
    Write-Host ""
    Write-Host "[ERROR] Node.js or npm is not installed or not in PATH." -ForegroundColor Red
    Write-Host "NEXORA frontend requires Node.js (v18+ recommended)." -ForegroundColor White
    Write-Host ""
    Write-Host "To resolve this:" -ForegroundColor White
    Write-Host "  1. Download Node.js LTS from: https://nodejs.org/" -ForegroundColor Cyan
    Write-Host "  2. Complete installation using standard defaults." -ForegroundColor White
    Write-Host "  3. Open a new PowerShell window and run .\start.ps1 again." -ForegroundColor White
    exit 1
}

$nodeVer = (& node --version 2>$null).Trim()
$npmVer = (& npm --version 2>$null).Trim()
Write-Host "      Found Node.js $nodeVer and npm $npmVer." -ForegroundColor Green

if (-not (Test-Path $PackageJson)) {
    Write-Host "[ERROR] Frontend package.json not found at: $PackageJson" -ForegroundColor Red
    exit 1
}

$FrontendMarker = Join-Path $NodeModulesDir ".package_lock_hash"
$LockHash = ""
if (Test-Path $PackageLock) {
    $LockHash = (Get-FileHash -Path $PackageLock -Algorithm SHA256).Hash
}

$ViteBin = Join-Path $NodeModulesDir "vite\bin\vite.js"
$NeedsFrontendInstall = $true

if ((Test-Path $NodeModulesDir) -and (Test-Path $ViteBin) -and (Test-Path $FrontendMarker)) {
    $SavedLockHash = (Get-Content $FrontendMarker -ErrorAction SilentlyContinue).Trim()
    if ($SavedLockHash -eq $LockHash) {
        $NeedsFrontendInstall = $false
    }
}

if ($NeedsFrontendInstall) {
    Write-Host "      Installing frontend dependencies..." -ForegroundColor Yellow
    Push-Location $FrontendDir
    try {
        if (Test-Path $PackageLock) {
            npm ci
        } else {
            npm install
        }
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] Failed to install frontend dependencies." -ForegroundColor Red
            exit 1
        }
        if ($LockHash) {
            Set-Content -Path $FrontendMarker -Value $LockHash
        }
        Write-Host "      Frontend dependencies installed and verified." -ForegroundColor Green
    } finally {
        Pop-Location
    }
} else {
    Write-Host "      Frontend dependencies already satisfied." -ForegroundColor Green
}

# -------------------------------------------------------------
# STEP 4: Start Backend & Await Subsystem Readiness
# -------------------------------------------------------------
Write-Host "[4/4] Starting FastAPI Backend server and awaiting readiness..." -ForegroundColor Yellow

if (Test-PortListening 8000) {
    Write-Host "      [WARNING] Port 8000 is already active on 127.0.0.1." -ForegroundColor Yellow
    Write-Host "                An existing FastAPI instance may already be running." -ForegroundColor Yellow
}

# Launch FastAPI backend in dedicated window
Write-Host "      Launching FastAPI Backend server in a separate window..." -ForegroundColor Cyan
$BackendCommand = "Set-Location '$BackendDir'; & '$VenvPython' -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
Start-Process powershell.exe -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $BackendCommand

# Poll readiness probe (http://127.0.0.1:8000/ready)
Write-Host "      Awaiting backend model and dataset initialization..." -ForegroundColor Yellow
$ReadyUrl = "http://127.0.0.1:8000/ready"
$HealthUrl = "http://127.0.0.1:8000/health"
$MaxWaitSec = 25
$StartTime = Get-Date
$BackendReady = $false

while (((Get-Date) - $StartTime).TotalSeconds -lt $MaxWaitSec) {
    try {
        $resp = Invoke-RestMethod -Uri $ReadyUrl -Method Get -TimeoutSec 2 -ErrorAction Stop
        if ($resp -and $resp.status -eq "ready") {
            $BackendReady = $true
            break
        }
    } catch {
        # Check if HTTP 503 was returned (server is alive but initialization is still in progress)
        if ($_.Exception.Response -and $_.Exception.Response.StatusCode.value__ -eq 503) {
            # Subsystems are still loading
        }
    }
    Start-Sleep -Milliseconds 700
}

if (-not $BackendReady) {
    Write-Host ""
    Write-Host "[ERROR] FastAPI backend failed readiness verification within $MaxWaitSec seconds." -ForegroundColor Red
    try {
        $healthResp = Invoke-RestMethod -Uri $HealthUrl -Method Get -TimeoutSec 2 -ErrorAction Stop
        Write-Host "        Liveness probe (/health) is ALIVE: $($healthResp.status), but readiness probe (/ready) failed." -ForegroundColor Yellow
        Write-Host "        One or more models or historical dataset failed initialization." -ForegroundColor Red
    } catch {
        Write-Host "        Backend process did not respond on http://127.0.0.1:8000 within timeout." -ForegroundColor Red
    }
    Write-Host "        Check the backend PowerShell console window for tracebacks." -ForegroundColor White
    exit 1
}

Write-Host "      Backend is fully READY (4 ML models verified, historical sales data indexed)." -ForegroundColor Green

# Secondary diagnostic probe: Experimental subsystem readiness
$ExpReadyUrl = "http://127.0.0.1:8000/api/v1/experimental/ready"
try {
    $expResp = Invoke-RestMethod -Uri $ExpReadyUrl -Method Get -TimeoutSec 2 -ErrorAction Stop
    if ($expResp -and $expResp.status -eq "ready") {
        Write-Host "      Experimental subsystem is READY (Task 12 models loaded, price service verified)." -ForegroundColor Green
    } else {
        Write-Host "      [INFO] Experimental subsystem reports degraded/unready status: $($expResp.status)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "      [INFO] Experimental subsystem did not report readiness." -ForegroundColor Gray
}

# -------------------------------------------------------------
# STEP 5: Launch React/Vite Frontend Client
# -------------------------------------------------------------
if (Test-PortListening 5173) {
    Write-Host "      [INFO] Port 5173 is already in use. Vite will use the next available port." -ForegroundColor Yellow
}

Write-Host "Starting React/Vite Frontend client in a separate window..." -ForegroundColor Cyan
$FrontendCommand = "Set-Location '$FrontendDir'; npm run dev"
Start-Process powershell.exe -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $FrontendCommand

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "         NEXORA Development Services Launched!            " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Access Points:" -ForegroundColor White
Write-Host "  - Frontend Client:            http://localhost:5173" -ForegroundColor Yellow
Write-Host "  - Backend API:                http://localhost:8000" -ForegroundColor Yellow
Write-Host "  - Swagger Documentation:       http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host "  - Liveness Health Probe:      http://localhost:8000/health" -ForegroundColor Yellow
Write-Host "  - Readiness Health Probe:     http://localhost:8000/ready" -ForegroundColor Yellow
Write-Host "  - Experimental Readiness:     http://localhost:8000/api/v1/experimental/ready" -ForegroundColor Yellow
Write-Host "  - Experimental Forecast API:  http://localhost:8000/api/v1/experimental/forecast/predict" -ForegroundColor Yellow
Write-Host ""
Write-Host "Server Management:" -ForegroundColor White
Write-Host "  - Both servers are running in separate PowerShell windows with real-time logs." -ForegroundColor Gray
Write-Host "  - To stop the services: Press Ctrl+C in each window or close the windows." -ForegroundColor Gray
Write-Host "  - To restart services: Run .\start.ps1 again at any time." -ForegroundColor Gray
Write-Host ""
