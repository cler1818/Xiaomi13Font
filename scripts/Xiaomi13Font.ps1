param(
    [Parameter(Position = 0)]
    [string]$FontPath,

    [ValidateSet('Generate', 'Copy', 'Install')]
    [string]$Action
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$AppName = 'Xiaomi13Font'
$Author = 'lzhp529'
$ModuleId = 'xiaomi13_fuxi_global_font'
$DeviceCodename = 'fuxi'
$MinApi = 34
$ScriptRoot = if ($env:XIAOMI13FONT_SCRIPT_ROOT) {
    $env:XIAOMI13FONT_SCRIPT_ROOT.TrimEnd('\')
} else {
    Split-Path -Parent $MyInvocation.MyCommand.Path
}
$OutputDir = Join-Path $ScriptRoot 'Output'

$SystemAliases = @(
    'MiSansVF.ttf', 'MiSansVF_Overlay.ttf', 'MiLanProVF.ttf',
    'MitypeVF.ttf', 'MitypeMonoVF.ttf', 'MitypeClock.otf', 'MitypeClockMono.otf',
    'Miui-Thin.ttf', 'Miui-Light.ttf', 'Miui-Regular.ttf', 'Miui-Medium.ttf', 'Miui-Bold.ttf',
    'MiuiEx-Light.ttf', 'MiuiEx-Regular.ttf', 'MiuiEx-Bold.ttf',
    'Roboto-Regular.ttf', 'RobotoStatic-Regular.ttf', 'Roboto-Thin.ttf', 'Roboto-ThinItalic.ttf',
    'Roboto-Light.ttf', 'Roboto-LightItalic.ttf', 'Roboto-Medium.ttf', 'Roboto-MediumItalic.ttf',
    'Roboto-Bold.ttf', 'Roboto-BoldItalic.ttf', 'Roboto-Black.ttf', 'Roboto-BlackItalic.ttf',
    'Roboto-Italic.ttf', 'NotoSerif-Regular.ttf', 'NotoSerif-Italic.ttf',
    'NotoSerif-Bold.ttf', 'NotoSerif-BoldItalic.ttf', 'DroidSansMono.ttf', 'CutiveMono.ttf',
    'CarroisGothicSC-Regular.ttf', 'SourceSansPro-Regular.ttf', 'SourceSansPro-Italic.ttf',
    'SourceSansPro-SemiBold.ttf', 'SourceSansPro-SemiBoldItalic.ttf',
    'SourceSansPro-Bold.ttf', 'SourceSansPro-BoldItalic.ttf'
)

$ProductAliases = @(
    'MiClock.otf', 'MiClockMono.otf', 'MiClockThin.otf',
    'MiClockTibetan-Thin.ttf', 'MiClockUyghur-Thin.ttf', 'MiSansC_3.005.ttf'
)

function Write-Info([string]$Text) {
    Write-Host "[Xiaomi13Font] $Text" -ForegroundColor Cyan
}

function Get-SafeFileName([string]$Name) {
    $invalid = [IO.Path]::GetInvalidFileNameChars()
    foreach ($char in $invalid) {
        $Name = $Name.Replace([string]$char, '_')
    }
    $Name = $Name.Trim().TrimEnd('.')
    if ([string]::IsNullOrWhiteSpace($Name)) { return 'font' }
    return $Name
}

function Select-FontFile {
    Add-Type -AssemblyName System.Windows.Forms
    $dialog = New-Object System.Windows.Forms.OpenFileDialog
    $dialog.Title = '选择用于生成全局模块的 TTF/OTF 字体'
    $dialog.Filter = '字体文件 (*.ttf;*.otf)|*.ttf;*.otf|TTF 字体 (*.ttf)|*.ttf|OTF 字体 (*.otf)|*.otf'
    $dialog.Multiselect = $false
    if ($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) {
        throw '未选择字体。'
    }
    return $dialog.FileName
}

function Get-FontFamilyName([string]$Path) {
    try {
        Add-Type -AssemblyName System.Drawing
        $collection = New-Object System.Drawing.Text.PrivateFontCollection
        $collection.AddFontFile($Path)
        if ($collection.Families.Count -gt 0) {
            $name = $collection.Families[0].Name
            $collection.Dispose()
            return $name
        }
        $collection.Dispose()
    } catch {
        Write-Warning "无法读取字体内部名称，将使用文件名：$($_.Exception.Message)"
    }
    return [IO.Path]::GetFileNameWithoutExtension($Path)
}

function Add-ZipTextEntry {
    param(
        [IO.Compression.ZipArchive]$Archive,
        [string]$EntryName,
        [string]$Content,
        [int]$Mode = 420
    )
    $entry = $Archive.CreateEntry($EntryName, [IO.Compression.CompressionLevel]::Optimal)
    $entry.ExternalAttributes = (($Mode -bor 32768) -shl 16)
    $writer = New-Object IO.StreamWriter($entry.Open(), (New-Object Text.UTF8Encoding($false)))
    try { $writer.Write($Content) } finally { $writer.Dispose() }
}

function Add-ZipFileEntry {
    param(
        [IO.Compression.ZipArchive]$Archive,
        [string]$EntryName,
        [string]$SourcePath
    )
    $entry = $Archive.CreateEntry($EntryName, [IO.Compression.CompressionLevel]::Optimal)
    $entry.ExternalAttributes = ((420 -bor 32768) -shl 16)
    $source = [IO.File]::OpenRead($SourcePath)
    $target = $entry.Open()
    try { $source.CopyTo($target) } finally { $target.Dispose(); $source.Dispose() }
}

function Get-CustomizeScript {
    $template = @'
#!/system/bin/sh

SKIPUNZIP=0
DEVICE="$(getprop ro.product.device)"
API="$(getprop ro.build.version.sdk)"

ui_print "****************************************"
ui_print " Xiaomi 13 Android 14 全局字体模块"
ui_print " 作者：__AUTHOR__"
ui_print "****************************************"

if [ "$DEVICE" != "__DEVICE__" ]; then
  abort "! 此模块仅适配小米13（__DEVICE__），当前设备：$DEVICE"
fi

if [ "$API" -lt __MIN_API__ ]; then
  abort "! 此模块要求 Android 14 / API 34 或更高版本，当前 API：$API"
fi

FONT_DIR="$MODPATH/system/fonts"
PRODUCT_FONT_DIR="$MODPATH/system/product/fonts"
BASE_FONT="Xiaomi13GlobalFont.ttf"
mkdir -p "$FONT_DIR" "$PRODUCT_FONT_DIR"

SYSTEM_ALIASES="
__SYSTEM_ALIASES__
"

PRODUCT_ALIASES="
__PRODUCT_ALIASES__
"

for NAME in $SYSTEM_ALIASES; do
  rm -f "$FONT_DIR/$NAME"
  ln -s "$BASE_FONT" "$FONT_DIR/$NAME"
done

for NAME in $PRODUCT_ALIASES; do
  rm -f "$PRODUCT_FONT_DIR/$NAME"
  ln -s "../../fonts/$BASE_FONT" "$PRODUCT_FONT_DIR/$NAME"
done

ui_print "- 设备校验通过：$DEVICE / API $API"
ui_print "- 已建立系统与时钟字体多链接覆盖"
ui_print "- 保留系统原生 fonts.xml"
ui_print "- 模块 ID：__MODULE_ID__"
ui_print "- 安装完成后请手动重启"
set_perm_recursive "$MODPATH" 0 0 0755 0644
'@
    return $template.Replace('__AUTHOR__', $Author).
        Replace('__DEVICE__', $DeviceCodename).
        Replace('__MIN_API__', [string]$MinApi).
        Replace('__MODULE_ID__', $ModuleId).
        Replace('__SYSTEM_ALIASES__', ($SystemAliases -join "`n")).
        Replace('__PRODUCT_ALIASES__', ($ProductAliases -join "`n"))
}

function New-FontModule([string]$SelectedFont) {
    if (-not (Test-Path -LiteralPath $SelectedFont -PathType Leaf)) {
        throw "字体文件不存在：$SelectedFont"
    }
    $extension = [IO.Path]::GetExtension($SelectedFont).ToLowerInvariant()
    if ($extension -notin @('.ttf', '.otf')) {
        throw '当前仅支持 TTF/OTF。TTC 字体合集需要先拆分。'
    }

    New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
    $family = (Get-FontFamilyName $SelectedFont) -replace "[`r`n]", ' '
    $timestamp = Get-Date -Format 'yyyy.MM.dd-HHmm'
    $versionCode = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    $moduleProp = @"
id=$ModuleId
name=小米13 Android 14 - $family（全局版）
version=$timestamp
versionCode=$versionCode
author=$Author
description=适配小米13 fuxi / MIUI 14.0.5 / Android 14 的全局字体模块。覆盖 MIUI、MiType、Roboto、Serif、等宽及小米时钟字体，保留系统原生 fonts.xml。
"@

    $fileName = Get-SafeFileName "Xiaomi13Font_${family}_${timestamp}.zip"
    $outputPath = Join-Path $OutputDir $fileName
    if (Test-Path -LiteralPath $outputPath) { Remove-Item -LiteralPath $outputPath -Force }

    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $stream = [IO.File]::Open($outputPath, [IO.FileMode]::CreateNew)
    $archive = New-Object IO.Compression.ZipArchive($stream, [IO.Compression.ZipArchiveMode]::Create, $false)
    try {
        Add-ZipTextEntry $archive 'META-INF/com/google/android/update-binary' "#!/sbin/sh`n#MAGISK`n" 493
        Add-ZipTextEntry $archive 'META-INF/com/google/android/updater-script' "#MAGISK`n"
        Add-ZipTextEntry $archive 'module.prop' $moduleProp
        Add-ZipTextEntry $archive 'system.prop' "ro.miui.ui.font.mi_font_path=null`n"
        Add-ZipTextEntry $archive 'customize.sh' (Get-CustomizeScript) 493
        Add-ZipFileEntry $archive 'system/fonts/Xiaomi13GlobalFont.ttf' $SelectedFont
    } finally {
        $archive.Dispose()
        $stream.Dispose()
    }

    $verifyStream = [IO.File]::OpenRead($outputPath)
    $verifyArchive = New-Object IO.Compression.ZipArchive($verifyStream, [IO.Compression.ZipArchiveMode]::Read, $false)
    try {
        $names = @($verifyArchive.Entries | ForEach-Object FullName)
        if ($names | Where-Object { $_ -match '\\' }) { throw 'ZIP 中检测到反斜杠路径。' }
        foreach ($required in @('module.prop', 'customize.sh', 'system.prop', 'system/fonts/Xiaomi13GlobalFont.ttf')) {
            if ($required -notin $names) { throw "ZIP 缺少：$required" }
        }
    } finally {
        $verifyArchive.Dispose()
        $verifyStream.Dispose()
    }

    Write-Info "模块生成成功：$outputPath"
    return $outputPath
}

function Get-AdbPath {
    $bundled = Join-Path $ScriptRoot 'tools\platform-tools\adb.exe'
    if (Test-Path -LiteralPath $bundled) { return $bundled }
    $command = Get-Command adb -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    throw '未找到 adb.exe。请使用完整脚本包。'
}

function Assert-Xiaomi13([string]$Adb) {
    $devices = & $Adb devices
    if ($LASTEXITCODE -ne 0) { throw 'ADB 无法启动。' }
    $authorized = @($devices | Select-String "`tdevice$")
    if ($authorized.Count -ne 1) { throw '请只连接一台已授权 USB 调试的手机。' }
    $device = (& $Adb shell getprop ro.product.device).Trim()
    if ($device -ne $DeviceCodename) { throw "当前设备为 $device，本工具仅适配小米13（fuxi）。" }
}

function Copy-ToPhone([string]$ModulePath) {
    $adb = Get-AdbPath
    Assert-Xiaomi13 $adb
    $remoteDir = '/sdcard/Download/Xiaomi13Font'
    $remotePath = "$remoteDir/$([IO.Path]::GetFileName($ModulePath))"
    & $adb shell mkdir -p $remoteDir | Out-Null
    & $adb push $ModulePath $remotePath
    if ($LASTEXITCODE -ne 0) { throw '复制到手机失败。' }
    Write-Info "已复制到手机：$remotePath"
}

function Install-ToMagisk([string]$ModulePath) {
    $adb = Get-AdbPath
    Assert-Xiaomi13 $adb
    $remote = '/data/local/tmp/xiaomi13font-module.zip'
    & $adb push $ModulePath $remote
    if ($LASTEXITCODE -ne 0) { throw '传输模块失败。' }
    & $adb shell su -c "magisk --install-module $remote"
    if ($LASTEXITCODE -ne 0) { throw 'Magisk 安装失败，请查看上方输出。' }
    $verify = & $adb shell su -c "cat /data/adb/modules_update/$ModuleId/module.prop 2>/dev/null || cat /data/adb/modules/$ModuleId/module.prop 2>/dev/null"
    if (($verify -join "`n") -notmatch "id=$ModuleId") { throw '未检测到已安装模块。' }
    & $adb shell rm -f $remote | Out-Null
    Write-Host '安装成功。请手动重启手机，脚本不会自动重启。' -ForegroundColor Green
}

try {
    Write-Host "$AppName - 小米13 Android 14 全局字体模块生成器" -ForegroundColor Green
    Write-Host "作者：$Author`n"
    if ([string]::IsNullOrWhiteSpace($FontPath)) { $FontPath = Select-FontFile }
    $FontPath = (Resolve-Path -LiteralPath $FontPath).Path
    Write-Info "已选择字体：$FontPath"

    if ([string]::IsNullOrWhiteSpace($Action)) {
        Write-Host "`n请选择操作："
        Write-Host '  1. 仅生成模块'
        Write-Host '  2. 生成并复制到手机'
        Write-Host '  3. 生成并直接安装到 Magisk（绕过 Invalid Uri）'
        $choice = Read-Host '输入 1/2/3'
        $Action = switch ($choice) {
            '2' { 'Copy' }
            '3' { 'Install' }
            default { 'Generate' }
        }
    }

    $module = New-FontModule $FontPath
    if ($Action -eq 'Copy') { Copy-ToPhone $module }
    if ($Action -eq 'Install') { Install-ToMagisk $module }
    exit 0
} catch {
    Write-Host "失败：$($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
