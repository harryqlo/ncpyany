# PowerShell version (más robusto)
# Guardar como: backup_automatico.ps1
# Ejecutar: powershell -ExecutionPolicy Bypass -File backup_automatico.ps1

param(
    [string]$SourceDb = "C:\Users\bodega.NORTHCHROME\Downloads\north_chrome2\north_chrome\system\system.db",
    [string]$BackupDir = "C:\Users\bodega.NORTHCHROME\Downloads\north_chrome2\north_chrome\system\backups",
    [int]$RetentionDays = 30,
    [switch]$VerifyRestore
)

# ===================================================================
# FUNCIONES
# ===================================================================

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogEntry = "[$Timestamp] [$Level] $Message"
    Write-Host $LogEntry
    Add-Content -Path $LogFile -Value $LogEntry
}

# ===================================================================
# CONFIGURACIÓN
# ===================================================================

$LogFile = Join-Path $BackupDir "backup.log"
$Date = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$BackupFile = Join-Path $BackupDir "system_$Date.db.backup"

# ===================================================================
# VALIDACIONES
# ===================================================================

if (-not (Test-Path $SourceDb)) {
    Write-Host "❌ ERROR: Archivo BD no encontrado: $SourceDb" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $BackupDir)) {
    Try {
        New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
        Write-Host "✓ Carpeta de backups creada" -ForegroundColor Green
    }
    Catch {
        Write-Host "❌ ERROR al crear carpeta: $_" -ForegroundColor Red
        exit 1
    }
}

# ===================================================================
# CREAR BACKUP
# ===================================================================

Write-Log "Iniciando backup de BD..."
Write-Log "Origen: $SourceDb"
Write-Log "Destino: $BackupFile"

Try {
    Copy-Item -Path $SourceDb -Destination $BackupFile -Force -ErrorAction Stop
    $FileSize = (Get-Item $BackupFile).Length / 1MB
    Write-Log "✓ Backup exitoso ($([Math]::Round($FileSize, 2)) MB)" "SUCCESS"
}
Catch {
    Write-Log "✗ ERROR al copiar: $_" "ERROR"
    exit 1
}

# ===================================================================
# LIMPIAR BACKUPS ANTIGUOS
# ===================================================================

Write-Log "Limpiando backups más antiguos que $RetentionDays días..."
$CutoffDate = (Get-Date).AddDays(-$RetentionDays)
$DeletedCount = 0

Get-ChildItem $BackupDir -Filter "system_*.db.backup" | Where-Object {
    $_.LastWriteTime -lt $CutoffDate
} | ForEach-Object {
    Try {
        Remove-Item -Path $_.FullName -Force
        Write-Log "Eliminado: $($_.Name)" "INFO"
        $DeletedCount++
    }
    Catch {
        Write-Log "ERROR eliminando: $($_.Name) - $_" "ERROR"
    }
}

Write-Log "Backups eliminados: $DeletedCount"

# ===================================================================
# VERIFICACIÓN DE RESTORE (OPCIONAL)
# ===================================================================

if ($VerifyRestore) {
    Write-Log "Iniciando restore test del backup recién creado..."
    $RestoreTestFile = Join-Path $env:TEMP "nc_restore_test_$Date.db"

    Try {
        Copy-Item -Path $BackupFile -Destination $RestoreTestFile -Force -ErrorAction Stop

        $PyScript = @"
import sqlite3
import sys
db = r'''$RestoreTestFile'''
conn = sqlite3.connect(db)
try:
    row = conn.execute("PRAGMA integrity_check").fetchone()
    ok = row and str(row[0]).lower() == "ok"
    print("OK" if ok else f"FAIL:{row[0] if row else 'unknown'}")
    sys.exit(0 if ok else 2)
finally:
    conn.close()
"@

        python -c $PyScript | Out-String | ForEach-Object {
            $Result = $_.Trim()
            if ($Result -like "OK*") {
                Write-Log "✓ Restore test exitoso (integrity_check=ok)" "SUCCESS"
            }
            else {
                Write-Log "✗ Restore test falló: $Result" "ERROR"
                throw "Integrity check failed: $Result"
            }
        }
    }
    Catch {
        Write-Log "✗ ERROR en restore test: $_" "ERROR"
        exit 2
    }
    Finally {
        if (Test-Path $RestoreTestFile) {
            Remove-Item -Path $RestoreTestFile -Force -ErrorAction SilentlyContinue
        }
    }
}

# ===================================================================
# RESUMEN
# ===================================================================

Write-Host ""
Write-Host "╔════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║       BACKUP COMPLETADO EXITOSAMENTE      ║" -ForegroundColor Green
Write-Host "╠════════════════════════════════════════════╣" -ForegroundColor Green
Write-Host "║ Archivo: $($BackupFile.Split('\')[-1])" -ForegroundColor Green
Write-Host "║ Tamaño: $([Math]::Round((Get-Item $BackupFile).Length / 1MB, 2)) MB" -ForegroundColor Green
Write-Host "║ Ubicación: $BackupDir" -ForegroundColor Green
Write-Host "║ Retención: $RetentionDays días" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
