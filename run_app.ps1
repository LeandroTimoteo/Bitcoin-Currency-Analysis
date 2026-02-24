param(
  [int]$Port = 8501
)

$ErrorActionPreference = "Stop"

$repoRoot = $PSScriptRoot
$streamlit = Join-Path $repoRoot ".venv\\Scripts\\streamlit.exe"
$appPath = Join-Path $repoRoot "Scripts\\app.py"
$logDir = Join-Path $repoRoot ".logs"

if (-not (Test-Path $streamlit)) {
  throw "Não encontrei $streamlit. Ative/crie a venv primeiro."
}
if (-not (Test-Path $appPath)) {
  throw "Não encontrei $appPath."
}

if (-not (Test-Path $logDir)) {
  New-Item -ItemType Directory -Path $logDir | Out-Null
}

$outLog = Join-Path $logDir ("streamlit-{0}.out.log" -f $Port)
$errLog = Join-Path $logDir ("streamlit-{0}.err.log" -f $Port)

$args = @(
  "run", $appPath,
  "--server.address", "127.0.0.1",
  "--server.port", "$Port",
  "--server.headless", "true"
)

$proc = Start-Process -FilePath $streamlit -ArgumentList $args -PassThru -NoNewWindow -RedirectStandardOutput $outLog -RedirectStandardError $errLog

$uri = "http://127.0.0.1:$Port"
$deadline = (Get-Date).AddSeconds(25)
$ownerPid = $null
while ((Get-Date) -lt $deadline) {
  $conn = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($conn) {
    $ownerPid = [int]$conn.OwningProcess
    break
  }
  if ($proc.HasExited) { break }
  try {
    $r = Invoke-WebRequest -UseBasicParsing $uri -TimeoutSec 2
    if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) { break }
  } catch {
    Start-Sleep -Milliseconds 500
  }
}

if (-not $ownerPid) {
  $conn = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($conn) { $ownerPid = [int]$conn.OwningProcess }
}

if (-not $ownerPid -and $proc.HasExited) {
  Write-Host "Falhou ao iniciar o Streamlit. Logs:"
  Write-Host "  $outLog"
  Write-Host "  $errLog"
  throw "Processo do Streamlit encerrou (PID inicial: $($proc.Id))."
}

Start-Process $uri | Out-Null
if ($ownerPid) {
  Write-Host "App aberto no navegador: $uri (PID: $ownerPid). Logs: $logDir"
} else {
  Write-Host "App aberto no navegador: $uri (PID inicial: $($proc.Id)). Logs: $logDir"
}

if ($ownerPid) {
  Wait-Process -Id $ownerPid -ErrorAction SilentlyContinue
} else {
  Wait-Process -Id $proc.Id -ErrorAction SilentlyContinue
}
