# Backs up the BauOS SQLite database to a local backup folder with a
# timestamped filename, and prunes backups older than 30 days.

$ErrorActionPreference = "Stop"

$sourceDb = "C:\Users\Laura de Santis\Documents\bauos-invoice-mvp\bauos.db"
$backupDir = "C:\Users\Laura de Santis\Documents\BauOS-Backups"
$retentionDays = 30

if (-not (Test-Path $backupDir)) {
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
}

if (-not (Test-Path $sourceDb)) {
    Write-Output "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - No database file found at $sourceDb, skipping backup."
    exit 0
}

$timestamp = Get-Date -Format "yyyy-MM-dd_HHmm"
$destination = Join-Path $backupDir "bauos_$timestamp.db"

Copy-Item -Path $sourceDb -Destination $destination -Force
Write-Output "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - Backed up to $destination"

$cutoff = (Get-Date).AddDays(-$retentionDays)
Get-ChildItem -Path $backupDir -Filter "bauos_*.db" |
    Where-Object { $_.LastWriteTime -lt $cutoff } |
    ForEach-Object {
        Remove-Item $_.FullName -Force
        Write-Output "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - Removed old backup $($_.Name)"
    }
