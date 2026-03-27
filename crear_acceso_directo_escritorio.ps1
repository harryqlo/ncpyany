param(
    [string]$ShortcutName = 'North Chrome - Iniciar Sistema'
)

$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$desktopPath = [Environment]::GetFolderPath('Desktop')
$targetPath = Join-Path $projectRoot 'iniciar.bat'
$iconPath = Join-Path $projectRoot 'assets\north-chrome-launcher.ico'
$previewPath = Join-Path $projectRoot 'assets\north-chrome-launcher-preview.png'
$shortcutPath = Join-Path $desktopPath ($ShortcutName + '.lnk')

if (-not (Test-Path $targetPath)) {
    throw "No se encontro iniciar.bat en: $targetPath"
}

Add-Type -AssemblyName System.Drawing

function New-RoundedRectanglePath {
    param(
        [System.Drawing.Rectangle]$Rect,
        [int]$Radius
    )

    $diameter = $Radius * 2
    $path = New-Object System.Drawing.Drawing2D.GraphicsPath
    $path.AddArc($Rect.X, $Rect.Y, $diameter, $diameter, 180, 90)
    $path.AddArc($Rect.Right - $diameter, $Rect.Y, $diameter, $diameter, 270, 90)
    $path.AddArc($Rect.Right - $diameter, $Rect.Bottom - $diameter, $diameter, $diameter, 0, 90)
    $path.AddArc($Rect.X, $Rect.Bottom - $diameter, $diameter, $diameter, 90, 90)
    $path.CloseFigure()
    return $path
}

function New-LauncherBitmap {
    param([int]$Size)

    $bitmap = New-Object System.Drawing.Bitmap $Size, $Size
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
    $graphics.Clear([System.Drawing.Color]::Transparent)

    $canvas = New-Object System.Drawing.Rectangle 0, 0, $Size, $Size
    $backgroundPath = New-RoundedRectanglePath -Rect $canvas -Radius ([Math]::Max([int]($Size * 0.17), 12))
    $backgroundBrush = New-Object System.Drawing.Drawing2D.LinearGradientBrush(
        $canvas,
        [System.Drawing.Color]::FromArgb(255, 10, 42, 108),
        [System.Drawing.Color]::FromArgb(255, 5, 25, 70),
        90
    )
    $graphics.FillPath($backgroundBrush, $backgroundPath)

    $accentBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 247, 122, 43))
    $softAccentBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(235, 255, 149, 62))
    $whiteBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 250, 252, 255))

    $topOrb = New-Object System.Drawing.RectangleF ($Size * 0.56), ($Size * 0.08), ($Size * 0.24), ($Size * 0.24)
    $sideBar = New-Object System.Drawing.RectangleF ($Size * 0.62), ($Size * 0.18), ($Size * 0.09), ($Size * 0.40)
    $baseBar = New-Object System.Drawing.RectangleF ($Size * 0.45), ($Size * 0.48), ($Size * 0.33), ($Size * 0.10)
    $graphics.FillEllipse($softAccentBrush, $topOrb)
    $graphics.FillRectangle($accentBrush, $sideBar)
    $graphics.FillRectangle($accentBrush, $baseBar)

    $fontSize = [Math]::Max([single]($Size * 0.33), 18)
    $font = New-Object System.Drawing.Font('Segoe UI Semibold', $fontSize, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
    $stringFormat = New-Object System.Drawing.StringFormat
    $stringFormat.Alignment = [System.Drawing.StringAlignment]::Center
    $stringFormat.LineAlignment = [System.Drawing.StringAlignment]::Center
    $textRect = New-Object System.Drawing.RectangleF ($Size * 0.12), ($Size * 0.18), ($Size * 0.52), ($Size * 0.42)
    $graphics.DrawString('NC', $font, $whiteBrush, $textRect, $stringFormat)

    $shadowPen = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(60, 255, 255, 255)), ([Math]::Max([single]($Size * 0.02), 2))
    $shadowPen.Alignment = [System.Drawing.Drawing2D.PenAlignment]::Inset
    $graphics.DrawPath($shadowPen, $backgroundPath)

    $shadowPen.Dispose()
    $font.Dispose()
    $stringFormat.Dispose()
    $accentBrush.Dispose()
    $softAccentBrush.Dispose()
    $whiteBrush.Dispose()
    $backgroundBrush.Dispose()
    $backgroundPath.Dispose()
    $graphics.Dispose()

    return $bitmap
}

function Save-BitmapAsIcon {
    param(
        [System.Drawing.Bitmap]$Bitmap,
        [string]$OutputPath
    )

    $icon = [System.Drawing.Icon]::FromHandle($Bitmap.GetHicon())
    try {
        $fileStream = [System.IO.File]::Open($OutputPath, [System.IO.FileMode]::Create)
        try {
            $icon.Save($fileStream)
        }
        finally {
            $fileStream.Dispose()
        }
    }
    finally {
        $icon.Dispose()
    }
}

$bitmap = New-LauncherBitmap -Size 256
try {
    $bitmap.Save($previewPath, [System.Drawing.Imaging.ImageFormat]::Png)
    Save-BitmapAsIcon -Bitmap $bitmap -OutputPath $iconPath
}
finally {
    $bitmap.Dispose()
}

$wshShell = New-Object -ComObject WScript.Shell
$shortcut = $wshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $targetPath
$shortcut.WorkingDirectory = $projectRoot
$shortcut.IconLocation = "$iconPath,0"
$shortcut.Description = 'Inicia North Chrome - Sistema de Bodega'
$shortcut.WindowStyle = 1
$shortcut.Save()

Write-Host "Vista previa PNG generada en: $previewPath"
Write-Host "Icono generado en: $iconPath"
Write-Host "Acceso directo creado en: $shortcutPath"