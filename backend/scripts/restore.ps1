# Restores a backup produced by backup.ps1.
#
# Usage: .\scripts\restore.ps1 backups\20260702_140000
# WARNING: this drops and recreates every table in the target database.

param(
    [Parameter(Mandatory=$true)][string]$BackupDir
)

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

$dumpFile = Join-Path $BackupDir "screening.dump"
if (-not (Test-Path $dumpFile)) {
    throw "No screening.dump found in $BackupDir"
}

$confirm = Read-Host "This will DROP and restore the database at $env:DATABASE_URL. Continue? [y/N]"
if ($confirm -ne "y") { Write-Host "Aborted."; exit 1 }

Write-Host "==> Restoring Postgres database..."
pg_restore --dbname="$env:DATABASE_URL" --clean --if-exists --no-owner $dumpFile

$chromaZip = Join-Path $BackupDir "chroma.zip"
if (Test-Path $chromaZip) {
    Write-Host "==> Restoring ChromaDB persistence dir..."
    Remove-Item -Recurse -Force "data\chroma" -ErrorAction SilentlyContinue
    Expand-Archive -Path $chromaZip -DestinationPath "data" -Force
}

Write-Host "==> Restore complete."
