# Backs up the Postgres database (pg_dump, custom format) and the ChromaDB
# persistence directory (zip) into backend/backups/<timestamp>/.
#
# Usage: .\scripts\backup.ps1
# Requires: pg_dump on PATH (matching the target Postgres major version).

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^\s*([^#=]+)=(.*)$') {
            [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim())
        }
    }
}

if (-not $env:DATABASE_URL) {
    throw "DATABASE_URL is not set (check .env)"
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$outDir = "backups\$timestamp"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

Write-Host "==> Dumping Postgres database..."
pg_dump --dbname="$env:DATABASE_URL" --format=custom --file="$outDir\screening.dump"

Write-Host "==> Archiving ChromaDB persistence dir..."
if (Test-Path "data\chroma") {
    Compress-Archive -Path "data\chroma" -DestinationPath "$outDir\chroma.zip" -Force
} else {
    Write-Host "    (data\chroma not found, skipping)"
}

Write-Host "==> Backup complete: $outDir"
Get-ChildItem $outDir | Format-Table Name, Length
