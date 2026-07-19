param(
    [string]$Version = '1.2.0'
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Tools = Join-Path $Root 'tools'
$PlatformTools = Join-Path $Tools 'platform-tools'
$Build = Join-Path $Root 'build'
$Dist = Join-Path $Root 'dist'
$Artifacts = Join-Path $Root 'artifacts'

function Get-PlatformTools {
    if (Test-Path -LiteralPath (Join-Path $PlatformTools 'adb.exe')) { return }
    Write-Host 'Downloading official Android platform-tools...'
    New-Item -ItemType Directory -Force -Path $Tools | Out-Null
    $zip = Join-Path $Tools 'platform-tools.zip'
    Invoke-WebRequest -Uri 'https://dl.google.com/android/repository/platform-tools-latest-windows.zip' -OutFile $zip
    Expand-Archive -LiteralPath $zip -DestinationPath $Tools -Force
    Remove-Item -LiteralPath $zip -Force
}

Get-PlatformTools
python -m pip install -r (Join-Path $Root 'requirements-build.txt')

foreach ($path in @($Build, $Dist, $Artifacts)) {
    if (Test-Path -LiteralPath $path) {
        $resolved = (Resolve-Path -LiteralPath $path).Path
        if (-not $resolved.StartsWith($Root, [StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to clean path outside project: $resolved"
        }
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}
New-Item -ItemType Directory -Force -Path $Artifacts | Out-Null

$binaryArgs = @()
foreach ($name in @('adb.exe', 'AdbWinApi.dll', 'AdbWinUsbApi.dll')) {
    $path = Join-Path $PlatformTools $name
    if (Test-Path -LiteralPath $path) {
        $binaryArgs += '--add-binary'
        $binaryArgs += "$path;tools/platform-tools"
    }
}

$pyinstallerArgs = @(
    '--noconfirm',
    '--clean',
    '--onedir',
    '--windowed',
    '--name', 'Xiaomi13Font',
    '--distpath', $Dist,
    '--workpath', $Build,
    '--specpath', $Build,
    '--collect-all', 'fontTools'
) + $binaryArgs + @(
    (Join-Path $Root 'src\xiaomi13font_tool.py')
)

python -m PyInstaller @pyinstallerArgs

$PortableDir = Join-Path $Dist 'Xiaomi13Font'
Copy-Item -LiteralPath (Join-Path $Root 'README.md') -Destination $PortableDir
Copy-Item -LiteralPath (Join-Path $Root 'DEVICE.md') -Destination $PortableDir
Copy-Item -LiteralPath (Join-Path $Root 'THIRD_PARTY_NOTICES.md') -Destination $PortableDir

$PortableZip = Join-Path $Artifacts "Xiaomi13Font-Portable-v$Version.zip"
Push-Location $PortableDir
try { tar -a -cf $PortableZip * } finally { Pop-Location }

$ScriptDir = Join-Path $Artifacts 'Xiaomi13Font-Script'
New-Item -ItemType Directory -Force -Path $ScriptDir | Out-Null
Copy-Item -LiteralPath (Join-Path $Root 'scripts\Xiaomi13Font.cmd') -Destination $ScriptDir
Copy-Item -LiteralPath (Join-Path $Root 'scripts\Xiaomi13Font.ps1') -Destination $ScriptDir
Copy-Item -LiteralPath (Join-Path $Root 'README.md') -Destination $ScriptDir
Copy-Item -LiteralPath (Join-Path $Root 'DEVICE.md') -Destination $ScriptDir
New-Item -ItemType Directory -Force -Path (Join-Path $ScriptDir 'tools') | Out-Null
Copy-Item -LiteralPath $PlatformTools -Destination (Join-Path $ScriptDir 'tools') -Recurse

$ScriptZip = Join-Path $Artifacts "Xiaomi13Font-Script-v$Version.zip"
Push-Location $ScriptDir
try { tar -a -cf $ScriptZip * } finally { Pop-Location }

Write-Host "Built: $PortableZip" -ForegroundColor Green
Write-Host "Built: $ScriptZip" -ForegroundColor Green
