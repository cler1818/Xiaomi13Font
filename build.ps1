param([string]$Version = '1.3.0')

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Tools = Join-Path $Root 'tools'
$PlatformTools = Join-Path $Tools 'platform-tools'
$Build = Join-Path $Root 'build'
$Dist = Join-Path $Root 'dist'
$Artifacts = Join-Path $Root 'artifacts'

if (-not (Test-Path -LiteralPath (Join-Path $PlatformTools 'adb.exe'))) {
    New-Item -ItemType Directory -Force -Path $Tools | Out-Null
    $download = Join-Path $Tools 'platform-tools.zip'
    Invoke-WebRequest 'https://dl.google.com/android/repository/platform-tools-latest-windows.zip' -OutFile $download
    Expand-Archive -LiteralPath $download -DestinationPath $Tools -Force
    Remove-Item -LiteralPath $download -Force
}

python -m pip install -r (Join-Path $Root 'requirements-build.txt')
foreach ($path in @($Build, $Dist, $Artifacts)) {
    if (Test-Path -LiteralPath $path) {
        $resolved = (Resolve-Path -LiteralPath $path).Path
        if (-not $resolved.StartsWith($Root, [StringComparison]::OrdinalIgnoreCase)) { throw "拒绝清理项目外目录：$resolved" }
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}
New-Item -ItemType Directory -Force -Path $Artifacts | Out-Null

python -m PyInstaller --noconfirm --clean --onedir --windowed --name FontModuleMaker `
    --distpath $Dist --workpath $Build --specpath $Build --paths (Join-Path $Root 'src') `
    --collect-submodules fontTools.ttLib.tables --hidden-import fontTools.cffLib `
    (Join-Path $Root 'src\font_module_maker.py')

$Portable = Join-Path $Dist 'Xiaomi13Font-Portable'
Move-Item -LiteralPath (Join-Path $Dist 'FontModuleMaker') -Destination $Portable
Copy-Item -LiteralPath $PlatformTools -Destination (Join-Path $Portable 'adb') -Recurse
New-Item -ItemType Directory -Force -Path (Join-Path $Portable 'source'),(Join-Path $Portable 'ExportedModules') | Out-Null
Copy-Item -LiteralPath (Join-Path $Root 'src\module_core.py'),(Join-Path $Root 'src\font_module_maker.py'),(Join-Path $Root 'requirements-build.txt') -Destination (Join-Path $Portable 'source')
Copy-Item -LiteralPath (Join-Path $Root 'README.md'),(Join-Path $Root 'DEVICE.md') -Destination $Portable

$Script = Join-Path $Artifacts 'Xiaomi13Font-Script'
New-Item -ItemType Directory -Force -Path $Script,(Join-Path $Script 'ExportedModules') | Out-Null
Copy-Item -LiteralPath (Join-Path $Root 'scripts\FontModuleMaker.ps1'),(Join-Path $Root 'scripts\FontModuleMaker.cmd'),(Join-Path $Root 'README.md'),(Join-Path $Root 'DEVICE.md') -Destination $Script
Copy-Item -LiteralPath $PlatformTools -Destination (Join-Path $Script 'adb') -Recurse

$PortableZip = Join-Path $Artifacts "Xiaomi13Font-Portable-v$Version.zip"
$ScriptZip = Join-Path $Artifacts "Xiaomi13Font-Script-v$Version.zip"
tar -a -cf $PortableZip -C $Dist (Split-Path $Portable -Leaf)
tar -a -cf $ScriptZip -C $Artifacts (Split-Path $Script -Leaf)
Write-Host "Built: $PortableZip"
Write-Host "Built: $ScriptZip"
