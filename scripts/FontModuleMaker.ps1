param(
    [string]$FontPath = '',
    [ValidateSet('Prompt', 'Generate', 'Copy', 'Install', 'InstallReboot', 'Detect', 'Reboot')]
    [string]$Mode = 'Prompt',
    [switch]$DisableOverlayCompat
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Author = 'lzhp529'
$ModuleId = 'fuxi_a14_inugami_momo_global_font'
$BaseFontName = 'GlobalFont.ttf'
$ScriptRoot = if ($env:FONT_MODULE_MAKER_SCRIPT_ROOT) {
    $env:FONT_MODULE_MAKER_SCRIPT_ROOT.TrimEnd('\')
} else {
    Split-Path -Parent $MyInvocation.MyCommand.Path
}
$OutputDir = Join-Path $ScriptRoot '导出模块'
$Adb = Join-Path $ScriptRoot 'adb\adb.exe'

$SystemAliases = @(
    'MiSansVF.ttf', 'MiSansVF_Overlay.ttf', 'MiLanProVF.ttf',
    'MitypeVF.ttf', 'MitypeMonoVF.ttf', 'MitypeClock.otf', 'MitypeClockMono.otf',
    'Miui-Thin.ttf', 'Miui-Light.ttf', 'Miui-Regular.ttf', 'Miui-Medium.ttf', 'Miui-Bold.ttf',
    'MiuiEx-Light.ttf', 'MiuiEx-Regular.ttf', 'MiuiEx-Bold.ttf',
    'Roboto-Regular.ttf', 'RobotoStatic-Regular.ttf',
    'Roboto-Thin.ttf', 'Roboto-ThinItalic.ttf', 'Roboto-Light.ttf', 'Roboto-LightItalic.ttf',
    'Roboto-Medium.ttf', 'Roboto-MediumItalic.ttf', 'Roboto-Bold.ttf', 'Roboto-BoldItalic.ttf',
    'Roboto-Black.ttf', 'Roboto-BlackItalic.ttf', 'Roboto-Italic.ttf',
    'NotoSerif-Regular.ttf', 'NotoSerif-Italic.ttf', 'NotoSerif-Bold.ttf', 'NotoSerif-BoldItalic.ttf',
    'DroidSansMono.ttf', 'CutiveMono.ttf', 'CarroisGothicSC-Regular.ttf',
    'SourceSansPro-Regular.ttf', 'SourceSansPro-Italic.ttf',
    'SourceSansPro-SemiBold.ttf', 'SourceSansPro-SemiBoldItalic.ttf',
    'SourceSansPro-Bold.ttf', 'SourceSansPro-BoldItalic.ttf'
)

$ProductAliases = @(
    'MiClock.otf', 'MiClockMono.otf', 'MiClockThin.otf',
    'MiClockTibetan-Thin.ttf', 'MiClockUyghur-Thin.ttf', 'MiSansC_3.005.ttf'
)

function Write-Title {
    Clear-Host
    Write-Host '============================================================' -ForegroundColor Cyan
    Write-Host ' 小米13 Android 14 全局字体模块生成器' -ForegroundColor Cyan
    Write-Host " 作者：$Author" -ForegroundColor Cyan
    Write-Host " 固定模块 ID：$ModuleId" -ForegroundColor DarkCyan
    Write-Host '============================================================' -ForegroundColor Cyan
}

function Select-FontFile {
    Add-Type -AssemblyName System.Windows.Forms
    $dialog = New-Object System.Windows.Forms.OpenFileDialog
    $dialog.Title = '选择 TTF/OTF 字体'
    $dialog.Filter = '字体文件 (*.ttf;*.otf)|*.ttf;*.otf|TTF 字体 (*.ttf)|*.ttf|OTF 字体 (*.otf)|*.otf'
    $dialog.Multiselect = $false
    if ($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) {
        return $null
    }
    return $dialog.FileName
}

function ConvertTo-SafeName([string]$Name) {
    foreach ($char in [System.IO.Path]::GetInvalidFileNameChars()) {
        $Name = $Name.Replace([string]$char, '_')
    }
    $Name = $Name.Trim().TrimEnd('.')
    if ([string]::IsNullOrWhiteSpace($Name)) { return '字体' }
    if ($Name.Length -gt 80) { return $Name.Substring(0, 80) }
    return $Name
}

function Add-TextEntry($Archive, [string]$EntryName, [string]$Content, [bool]$Executable = $false) {
    $entry = $Archive.CreateEntry($EntryName, [System.IO.Compression.CompressionLevel]::Optimal)
    $mode = if ($Executable) { 493 } else { 420 }
    $entry.ExternalAttributes = (($mode -bor 32768) -shl 16)
    $stream = $entry.Open()
    try {
        $utf8 = New-Object System.Text.UTF8Encoding($false)
        $writer = New-Object System.IO.StreamWriter($stream, $utf8)
        try { $writer.Write($Content) } finally { $writer.Dispose() }
    } finally {
        $stream.Dispose()
    }
}

function Add-FileEntry($Archive, [string]$EntryName, [string]$SourcePath) {
    $entry = $Archive.CreateEntry($EntryName, [System.IO.Compression.CompressionLevel]::Optimal)
    $target = $entry.Open()
    $source = [System.IO.File]::OpenRead($SourcePath)
    try { $source.CopyTo($target) } finally { $source.Dispose(); $target.Dispose() }
}

function New-FontModule([string]$FontPath) {
    if (-not (Test-Path -LiteralPath $FontPath -PathType Leaf)) {
        throw "字体文件不存在：$FontPath"
    }
    $extension = [System.IO.Path]::GetExtension($FontPath).ToLowerInvariant()
    if ($extension -notin @('.ttf', '.otf')) {
        throw '仅支持 TTF/OTF；TTC 字体合集需要先拆分'
    }

    New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
    $fontName = [System.IO.Path]::GetFileNameWithoutExtension($FontPath)
    $safeName = ConvertTo-SafeName $fontName
    $outputZip = Join-Path $OutputDir ($safeName + '_小米13全局字体模块_lzhp529.zip')
    if (Test-Path -LiteralPath $outputZip) {
        Remove-Item -LiteralPath $outputZip -Force
    }

    $now = Get-Date
    $version = $now.ToString('yyyy.MM.dd-HHmmss')
    $versionCode = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    $cleanFontName = ($fontName -replace '[\r\n]+', ' ').Trim()

    $moduleProp = @"
id=$ModuleId
name=小米13 Android 14 - $cleanFontName（全局版）
version=$version
versionCode=$versionCode
author=$Author
description=小米13 fuxi / Android 14+ 全局字体模块；当前字体：$cleanFontName；使用单字体多链接方案，覆盖 MIUI、MiType、Roboto、Serif、等宽及小米时钟字体；保留系统原生 fonts.xml。
"@

    $customizeTemplate = @'
#!/system/bin/sh

SKIPUNZIP=0
DEVICE="$(getprop ro.product.device)"
API="$(getprop ro.build.version.sdk)"

ui_print "****************************************"
ui_print " 小米13 Android 14 全局字体模块"
ui_print " 字体：__FONT_NAME__"
ui_print " 作者：__AUTHOR__"
ui_print "****************************************"

if [ "$DEVICE" != "fuxi" ]; then
  abort "! 此模块仅为小米13（fuxi）制作，当前设备：$DEVICE"
fi

if [ "$API" -lt 34 ]; then
  abort "! 此模块要求 Android 14 或更高版本，当前 API：$API"
fi

FONT_DIR="$MODPATH/system/fonts"
PRODUCT_FONT_DIR="$MODPATH/system/product/fonts"
BASE_FONT="GlobalFont.ttf"

[ -f "$FONT_DIR/$BASE_FONT" ] || abort "! 模块内主字体文件缺失"
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
ui_print "- 已建立系统和时钟字体链接"
ui_print "- 保留当前系统原生 fonts.xml"
ui_print "- 安装完成后请重启"

set_perm_recursive "$MODPATH" 0 0 0755 0644
'@
    $customize = $customizeTemplate.Replace('__FONT_NAME__', $cleanFontName.Replace('"', "'"))
    $customize = $customize.Replace('__AUTHOR__', $Author)
    $customize = $customize.Replace('__SYSTEM_ALIASES__', ($SystemAliases -join "`n"))
    $customize = $customize.Replace('__PRODUCT_ALIASES__', ($ProductAliases -join "`n"))

    $serviceTemplate = @'
#!/system/bin/sh
MODDIR="${0%/*}"
FONT="$MODDIR/system/fonts/GlobalFont.ttf"
LOG="$MODDIR/overlay-compat.log"
OVERLAY_MOD="/data/adb/modules/cler1818_full_system_overlayfs"
OVERLAY_LOG="$OVERLAY_MOD/overlay.log"
exec >>"$LOG" 2>&1
echo "==== $(date '+%F %T') OverlayFS delayed font compatibility v1.4 ===="
until [ "$(getprop sys.boot_completed)" = "1" ]; do sleep 2; done
[ -f "$FONT" ] || { echo "ERROR: font missing: $FONT"; exit 1; }

NOW_EPOCH="$(date +%s)"
UPTIME_SEC="$(awk '{print int($1)}' /proc/uptime 2>/dev/null)"
[ -n "$UPTIME_SEC" ] || UPTIME_SEC=0
BOOT_EPOCH=$((NOW_EPOCH - UPTIME_SEC - 5))

overlay_ready() {
  LOG_MTIME="$(stat -c %Y "$OVERLAY_LOG" 2>/dev/null)"
  [ -n "$LOG_MTIME" ] && [ "$LOG_MTIME" -ge "$BOOT_EPOCH" ] || return 1
  tail -n 80 "$OVERLAY_LOG" 2>/dev/null | grep -q "健康检查通过" || return 1
  grep -q "overlay cler1818_full_overlayfs_system " /proc/self/mountinfo || return 1
  grep -q "overlay cler1818_full_overlayfs_product " /proc/self/mountinfo || return 1
  return 0
}

if [ -d "$OVERLAY_MOD" ] && [ ! -f "$OVERLAY_MOD/disable" ] && [ ! -f "$OVERLAY_MOD/remove" ]; then
  echo "OverlayFS detected; boot_epoch=$BOOT_EPOCH"
  WAITED=0
  STABLE=0
  while [ "$WAITED" -lt 240 ]; do
    if overlay_ready; then
      STABLE=$((STABLE + 1))
      [ "$STABLE" -ge 3 ] && break
    else
      STABLE=0
    fi
    sleep 2
    WAITED=$((WAITED + 2))
  done
  if [ "$STABLE" -lt 3 ]; then
    echo "ERROR: OverlayFS was not ready for this boot after ${WAITED}s"
    exit 1
  fi
  echo "OverlayFS ready and stable after ${WAITED}s; settling 8s"
  sleep 8
else
  echo "OverlayFS absent or disabled; normal delayed bind 8s"
  sleep 8
fi
SYSTEM_ALIASES="
__SYSTEM_ALIASES__
"
PRODUCT_ALIASES="
__PRODUCT_ALIASES__
"
FONT_HASH="$(sha256sum "$FONT" 2>/dev/null | awk '{print $1}')"
[ -n "$FONT_HASH" ] || { echo "ERROR: cannot hash module font"; exit 1; }

apply_pass() {
SEEN="|"; OK=0; VERIFIED=0; SKIP=0; FAIL=0
bind_one() {
  ENTRY="$1"
  [ -e "$ENTRY" ] || { echo "SKIP missing: $ENTRY"; SKIP=$((SKIP + 1)); return; }
  TARGET="$(readlink -f "$ENTRY" 2>/dev/null)"
  [ -n "$TARGET" ] && [ -f "$TARGET" ] || { echo "SKIP unresolved: $ENTRY"; SKIP=$((SKIP + 1)); return; }
  case "$SEEN" in *"|$TARGET|"*) return ;; esac
  SEEN="${SEEN}${TARGET}|"
  BEFORE="$(sha256sum "$TARGET" 2>/dev/null | awk '{print $1}')"
  if [ "$BEFORE" = "$FONT_HASH" ]; then VERIFIED=$((VERIFIED + 1)); return; fi
  if mount --bind "$FONT" "$TARGET"; then
    AFTER="$(sha256sum "$TARGET" 2>/dev/null | awk '{print $1}')"
    if [ "$AFTER" = "$FONT_HASH" ]; then
      echo "OK: $ENTRY -> $TARGET"; OK=$((OK + 1))
    else
      echo "FAIL verify: $ENTRY -> $TARGET ($AFTER)"; FAIL=$((FAIL + 1))
    fi
  else
    echo "FAIL: $ENTRY -> $TARGET"; FAIL=$((FAIL + 1))
  fi
}
for NAME in $SYSTEM_ALIASES; do bind_one "/system/fonts/$NAME"; done
for NAME in $PRODUCT_ALIASES; do
  bind_one "/product/fonts/$NAME"
  bind_one "/system/product/fonts/$NAME"
done
echo "Pass $PASS: ok=$OK verified=$VERIFIED skip=$SKIP fail=$FAIL"
}

PASS=1
while [ "$PASS" -le 3 ]; do
  apply_pass
  [ "$FAIL" -eq 0 ] && break
  PASS=$((PASS + 1))
  [ "$PASS" -le 3 ] && sleep 10
done
echo "Completed: pass=$PASS ok=$OK verified=$VERIFIED skip=$SKIP fail=$FAIL font_hash=$FONT_HASH"
'@
    $service = $serviceTemplate.Replace('__SYSTEM_ALIASES__', ($SystemAliases -join "`n"))
    $service = $service.Replace('__PRODUCT_ALIASES__', ($ProductAliases -join "`n"))

    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $fileStream = [System.IO.File]::Open($outputZip, [System.IO.FileMode]::CreateNew)
    try {
        $archive = [System.IO.Compression.ZipArchive]::new(
            $fileStream,
            [System.IO.Compression.ZipArchiveMode]::Create,
            $false,
            [System.Text.Encoding]::UTF8
        )
        try {
            Add-TextEntry $archive 'META-INF/com/google/android/update-binary' "#!/sbin/sh`n#MAGISK`n" $true
            Add-TextEntry $archive 'META-INF/com/google/android/updater-script' "#MAGISK`n"
            Add-TextEntry $archive 'module.prop' ($moduleProp.TrimStart() + "`n")
            Add-TextEntry $archive 'system.prop' "ro.miui.ui.font.mi_font_path=null`n"
            Add-TextEntry $archive 'customize.sh' $customize $true
            if (-not $DisableOverlayCompat) {
                Add-TextEntry $archive 'service.sh' $service $true
            }
            Add-FileEntry $archive "system/fonts/$BaseFontName" $FontPath
        } finally {
            $archive.Dispose()
        }
    } finally {
        $fileStream.Dispose()
    }

    $zipCheck = [System.IO.Compression.ZipFile]::OpenRead($outputZip)
    try {
        $names = @($zipCheck.Entries | ForEach-Object FullName)
        $required = @(
            'META-INF/com/google/android/update-binary',
            'META-INF/com/google/android/updater-script',
            'module.prop', 'system.prop', 'customize.sh', "system/fonts/$BaseFontName"
        )
        foreach ($item in $required) {
            if ($item -notin $names) { throw "生成的模块缺少文件：$item" }
        }
        if ($names | Where-Object { $_ -match '\\' }) {
            throw '压缩包路径包含反斜杠，已停止使用该模块'
        }
    } finally {
        $zipCheck.Dispose()
    }

    Write-Host "模块生成成功：$outputZip" -ForegroundColor Green
    Write-Host ("模块大小：{0:N2} MB" -f ((Get-Item -LiteralPath $outputZip).Length / 1MB))
    return $outputZip
}

function Invoke-Adb([string[]]$Arguments, [switch]$IgnoreError) {
    if (-not (Test-Path -LiteralPath $Adb)) {
        throw "找不到 ADB：$Adb"
    }
    Write-Host ('ADB: ' + ($Arguments -join ' ')) -ForegroundColor DarkGray
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $output = & $Adb @Arguments 2>&1
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousPreference
    }
    if ($output) { $output | ForEach-Object { Write-Host $_ } }
    if (-not $IgnoreError -and $exitCode -ne 0) {
        throw "ADB 命令失败，退出码：$exitCode"
    }
    return @($output)
}

function Assert-OneDevice {
    $lines = Invoke-Adb -Arguments @('devices', '-l')
    $deviceLines = @($lines | Where-Object { $_ -match '^\S+\s+device\b' })
    if ($lines | Where-Object { $_ -match '\s+unauthorized\b' }) {
        throw '手机尚未授权 USB 调试，请在手机上点击允许'
    }
    if ($deviceLines.Count -eq 0) { throw '没有检测到手机，请检查数据线和 USB 调试' }
    if ($deviceLines.Count -gt 1) { throw '检测到多台设备，请只连接一台手机' }
}

function Test-Phone {
    Assert-OneDevice
    $model = ([string](Invoke-Adb -Arguments @('shell', 'getprop', 'ro.product.model') | Select-Object -Last 1)).Trim()
    $device = ([string](Invoke-Adb -Arguments @('shell', 'getprop', 'ro.product.device') | Select-Object -Last 1)).Trim()
    $android = ([string](Invoke-Adb -Arguments @('shell', 'getprop', 'ro.build.version.release') | Select-Object -Last 1)).Trim()
    $sdk = ([string](Invoke-Adb -Arguments @('shell', 'getprop', 'ro.build.version.sdk') | Select-Object -Last 1)).Trim()
    $root = Invoke-Adb -Arguments @('shell', 'su', '-c', 'id')
    if (($root -join "`n") -notmatch 'uid=0') { throw 'Shell 没有获得 Root 权限' }
    $magisk = Invoke-Adb -Arguments @('shell', 'su', '-c', 'magisk -v; magisk -V')
    Write-Host "设备：$model / $device / Android $android / API $sdk" -ForegroundColor Green
    Write-Host ('Magisk：' + ($magisk -join ' ')) -ForegroundColor Green
    if ($device -ne 'fuxi') { throw "当前设备不是小米13 fuxi：$device" }
    if ([int]$sdk -lt 34) { throw "当前系统低于 Android 14：API $sdk" }
}

function Copy-ModuleToPhone([string]$ModuleZip) {
    Assert-OneDevice
    Invoke-Adb -Arguments @('shell', 'mkdir', '-p', '/sdcard/Download/FontModules') | Out-Null
    $remote = '/sdcard/Download/FontModules/' + [System.IO.Path]::GetFileName($ModuleZip)
    Invoke-Adb -Arguments @('push', $ModuleZip, $remote) | Out-Null
    Write-Host "已复制到手机：$remote" -ForegroundColor Green
}

function Install-MagiskModule([string]$ModuleZip) {
    Test-Phone
    $remote = '/data/local/tmp/lzhp529-global-font.zip'
    Invoke-Adb -Arguments @('push', $ModuleZip, $remote) | Out-Null
    try {
        $installOutput = Invoke-Adb -Arguments @('shell', 'su', '-c', "magisk --install-module $remote")
        if (($installOutput -join "`n") -notmatch 'Done') {
            throw 'Magisk 没有返回安装完成标志'
        }
        Write-Host 'Magisk 模块安装成功，重启后生效。' -ForegroundColor Green
    } finally {
        Invoke-Adb -Arguments @('shell', 'rm', '-f', $remote) -IgnoreError | Out-Null
    }
}

function Restart-Phone {
    Assert-OneDevice
    Invoke-Adb -Arguments @('reboot') | Out-Null
    Write-Host '重启命令已发送。' -ForegroundColor Green
}

try {
    Write-Title
    $selectedFont = $FontPath
    if ([string]::IsNullOrWhiteSpace($selectedFont)) {
        $selectedFont = Select-FontFile
    }
    if (-not $selectedFont) {
        Write-Host '已取消。'
        exit 0
    }

    Write-Host "选择字体：$selectedFont"
    $moduleZip = New-FontModule $selectedFont

    if ($Mode -ne 'Prompt') {
        switch ($Mode) {
            'Generate' { Write-Host '已完成电脑导出。' -ForegroundColor Green }
            'Copy' { Copy-ModuleToPhone $moduleZip }
            'Install' { Install-MagiskModule $moduleZip }
            'InstallReboot' { Install-MagiskModule $moduleZip; Restart-Phone }
            'Detect' { Test-Phone }
            'Reboot' { Restart-Phone }
        }
        exit 0
    }

    Write-Host ''
    Write-Host '[1] 仅生成到电脑（已完成）'
    Write-Host '[2] 复制模块到手机 Download/FontModules'
    Write-Host '[3] 直接安装到 Magisk（绕过 Invalid Uri）'
    Write-Host '[4] 安装到 Magisk 并立即重启手机'
    Write-Host '[5] 仅检测手机、Root 和 Magisk'
    Write-Host '[6] 仅重启已连接的手机'
    $choice = Read-Host '请选择 1-6'

    switch ($choice) {
        '1' { Start-Process explorer.exe -ArgumentList "/select,`"$moduleZip`"" }
        '2' { Copy-ModuleToPhone $moduleZip }
        '3' { Install-MagiskModule $moduleZip }
        '4' {
            $confirm = Read-Host '安装成功后将立即重启手机，输入 YES 继续'
            if ($confirm -ceq 'YES') {
                Install-MagiskModule $moduleZip
                Restart-Phone
            } else {
                Write-Host '已取消安装并重启。' -ForegroundColor Yellow
            }
        }
        '5' { Test-Phone }
        '6' {
            $confirm = Read-Host '将立即重启手机，输入 YES 继续'
            if ($confirm -ceq 'YES') { Restart-Phone } else { Write-Host '已取消重启。' -ForegroundColor Yellow }
        }
        default { Write-Host '未执行额外操作，模块已经保存在电脑。' -ForegroundColor Yellow }
    }
} catch {
    Write-Host ''
    Write-Host ('操作失败：' + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
