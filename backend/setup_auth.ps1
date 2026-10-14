param(
  [switch]$RepairMissingSecret
)

$ErrorActionPreference = 'Stop'

$backend = Split-Path -Parent $MyInvocation.MyCommand.Path
$envPath = Join-Path $backend '.env'

if ($RepairMissingSecret) {
  $lines = @()
  if (Test-Path $envPath) {
    $lines = @(Get-Content -Path $envPath)
  }

  $secretLineIndex = -1
  for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match '^\s*SENTINEL_AUTH_SECRET\s*=') {
      $secretLineIndex = $i
      break
    }
  }

  $bytes = [byte[]]::new(32)
  $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
  $generator.GetBytes($bytes)
  $generator.Dispose()
  $generatedSecret = [Convert]::ToBase64String($bytes)
  $replacement = "SENTINEL_AUTH_SECRET=$generatedSecret"

  if ($secretLineIndex -ge 0) {
    $lines[$secretLineIndex] = $replacement
  } else {
    $lines += $replacement
  }

  Set-Content -Path $envPath -Value $lines -Encoding utf8
  Remove-Variable generatedSecret -ErrorAction SilentlyContinue
  Write-Host 'Authentication secret repaired in backend/.env; existing settings were preserved.'
  exit 0
}

if (Test-Path $envPath) {
  Write-Host "backend/.env already exists. Remove it only if you intend to reconfigure authentication."
  exit 0
}

$bytes = [byte[]]::new(32)
$generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$generator.GetBytes($bytes)
$generator.Dispose()
$secret = [Convert]::ToBase64String($bytes)
$password = Read-Host 'Bootstrap admin password (minimum 12 characters)' -AsSecureString
$passwordText = [Runtime.InteropServices.Marshal]::PtrToStringBSTR(
  [Runtime.InteropServices.Marshal]::SecureStringToBSTR($password)
)

if ($passwordText.Length -lt 12) {
  throw 'Bootstrap password must be at least 12 characters.'
}

@"
AUTH_ENABLED=true
SENTINEL_AUTH_SECRET=$secret
AUTH_TOKEN_TTL_SECONDS=28800
SENTINEL_BOOTSTRAP_ADMIN_USERNAME=admin
SENTINEL_BOOTSTRAP_ADMIN_PASSWORD=$passwordText
GPS_MODE=simulation
DISPATCH_MODE=simulation
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,http://127.0.0.1:5174
"@ | Set-Content -Path $envPath -Encoding utf8

Remove-Variable passwordText -ErrorAction SilentlyContinue
Write-Host 'Authentication configuration created in backend/.env.'