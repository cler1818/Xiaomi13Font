from __future__ import annotations

import hashlib
import re
import shutil
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from fontTools.ttLib import TTFont, TTLibError


AUTHOR = "lzhp529"
FIXED_MODULE_ID = "fuxi_a14_inugami_momo_global_font"
BASE_FONT_NAME = "GlobalFont.ttf"

SYSTEM_ALIASES = (
    "MiSansVF.ttf",
    "MiSansVF_Overlay.ttf",
    "MiLanProVF.ttf",
    "MitypeVF.ttf",
    "MitypeMonoVF.ttf",
    "MitypeClock.otf",
    "MitypeClockMono.otf",
    "Miui-Thin.ttf",
    "Miui-Light.ttf",
    "Miui-Regular.ttf",
    "Miui-Medium.ttf",
    "Miui-Bold.ttf",
    "MiuiEx-Light.ttf",
    "MiuiEx-Regular.ttf",
    "MiuiEx-Bold.ttf",
    "Roboto-Regular.ttf",
    "RobotoStatic-Regular.ttf",
    "Roboto-Thin.ttf",
    "Roboto-ThinItalic.ttf",
    "Roboto-Light.ttf",
    "Roboto-LightItalic.ttf",
    "Roboto-Medium.ttf",
    "Roboto-MediumItalic.ttf",
    "Roboto-Bold.ttf",
    "Roboto-BoldItalic.ttf",
    "Roboto-Black.ttf",
    "Roboto-BlackItalic.ttf",
    "Roboto-Italic.ttf",
    "NotoSerif-Regular.ttf",
    "NotoSerif-Italic.ttf",
    "NotoSerif-Bold.ttf",
    "NotoSerif-BoldItalic.ttf",
    "DroidSansMono.ttf",
    "CutiveMono.ttf",
    "CarroisGothicSC-Regular.ttf",
    "SourceSansPro-Regular.ttf",
    "SourceSansPro-Italic.ttf",
    "SourceSansPro-SemiBold.ttf",
    "SourceSansPro-SemiBoldItalic.ttf",
    "SourceSansPro-Bold.ttf",
    "SourceSansPro-BoldItalic.ttf",
)

PRODUCT_ALIASES = (
    "MiClock.otf",
    "MiClockMono.otf",
    "MiClockThin.otf",
    "MiClockTibetan-Thin.ttf",
    "MiClockUyghur-Thin.ttf",
    "MiSansC_3.005.ttf",
)


class ModuleBuildError(RuntimeError):
    pass


@dataclass(frozen=True)
class FontInfo:
    path: Path
    display_name: str
    family_name: str
    subfamily_name: str
    glyph_count: int
    codepoint_count: int
    cjk_count: int
    cjk_ext_b_count: int
    ascii_complete: bool
    has_common_chinese: bool
    has_color_emoji: bool
    is_variable: bool
    axes: tuple[str, ...]
    sha256: str
    size: int
    inspection_note: str = ""

    @property
    def warning(self) -> str:
        warnings: list[str] = []
        if self.inspection_note:
            warnings.append(self.inspection_note)
        if not self.ascii_complete:
            warnings.append("英文字母或数字覆盖不完整")
        if self.cjk_count < 3000:
            warnings.append("常用中文覆盖较少")
        if not self.has_common_chinese:
            warnings.append("缺少常用汉字“中/国/字/体”")
        if not self.has_color_emoji:
            warnings.append("不含彩色表情（将继续使用系统表情）")
        return "；".join(warnings)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _font_names(font: TTFont, name_id: int) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    name_table = font.get("name")
    if name_table is None:
        return result
    records = sorted(
        (record for record in name_table.names if record.nameID == name_id),
        key=lambda record: (record.langID not in (0x0804, 0x0004), record.platformID),
    )
    for record in records:
        try:
            value = record.toUnicode().strip()
        except Exception:
            continue
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _fallback_font_info(path: Path, reason: str) -> FontInfo:
    return FontInfo(
        path=path,
        display_name=path.stem,
        family_name=path.stem,
        subfamily_name="未知",
        glyph_count=0,
        codepoint_count=0,
        cjk_count=0,
        cjk_ext_b_count=0,
        ascii_complete=False,
        has_common_chinese=False,
        has_color_emoji=False,
        is_variable=False,
        axes=(),
        sha256=sha256_file(path),
        size=path.stat().st_size,
        inspection_note=f"字体详细检查失败，已按原文件继续制作：{reason}",
    )


def inspect_font(font_path: str | Path, allow_unreadable: bool = False) -> FontInfo:
    path = Path(font_path).expanduser().resolve()
    if not path.is_file():
        raise ModuleBuildError(f"字体文件不存在：{path}")
    if path.suffix.lower() not in {".ttf", ".otf"}:
        raise ModuleBuildError("仅支持单字体 TTF/OTF；TTC 字体合集需要先拆分")

    collection_note = ""
    try:
        font = TTFont(str(path), lazy=False, recalcBBoxes=False, recalcTimestamp=False)
    except (TTLibError, OSError, ValueError) as exc:
        if "specify a font number" in str(exc).lower():
            try:
                font = TTFont(str(path), fontNumber=0, lazy=False, recalcBBoxes=False, recalcTimestamp=False)
                collection_note = "检测到多字体集合，信息按第 1 个字体读取；生成时保留完整原文件"
            except Exception as collection_exc:
                if allow_unreadable:
                    return _fallback_font_info(path, str(collection_exc))
                raise ModuleBuildError(f"无法读取字体集合：{collection_exc}") from collection_exc
        elif allow_unreadable:
            return _fallback_font_info(path, str(exc))
        else:
            raise ModuleBuildError(f"无法读取字体：{exc}") from exc

    try:
        full_names = _font_names(font, 4)
        family_names = _font_names(font, 1)
        subfamily_names = _font_names(font, 2)
        family_name = family_names[0] if family_names else (full_names[0] if full_names else path.stem)
        subfamily_name = subfamily_names[0] if subfamily_names else "Regular"
        display_name = family_name
        if subfamily_name.lower() not in {"regular", "normal", "標準體", "标准体"}:
            display_name = f"{family_name} {subfamily_name}"

        codepoints: set[int] = set()
        cmap = font.get("cmap")
        if cmap is not None:
            for table in cmap.tables:
                codepoints.update(table.cmap.keys())

        glyph_count = len(font.getGlyphOrder())
        cjk_count = sum(1 for cp in codepoints if 0x4E00 <= cp <= 0x9FFF)
        cjk_ext_b_count = sum(1 for cp in codepoints if 0x20000 <= cp <= 0x2A6DF)
        ascii_required = set(range(0x30, 0x3A)) | set(range(0x41, 0x5B)) | set(range(0x61, 0x7B))
        common_chinese = {ord(char) for char in "中国字体你好测试"}
        has_color_emoji = any(table in font for table in ("COLR", "CBDT", "sbix", "SVG "))
        is_variable = "fvar" in font
        axes: tuple[str, ...] = ()
        if is_variable:
            axes = tuple(axis.axisTag for axis in font["fvar"].axes)

        return FontInfo(
            path=path,
            display_name=display_name,
            family_name=family_name,
            subfamily_name=subfamily_name,
            glyph_count=glyph_count,
            codepoint_count=len(codepoints),
            cjk_count=cjk_count,
            cjk_ext_b_count=cjk_ext_b_count,
            ascii_complete=ascii_required.issubset(codepoints),
            has_common_chinese=common_chinese.issubset(codepoints),
            has_color_emoji=has_color_emoji,
            is_variable=is_variable,
            axes=axes,
            sha256=sha256_file(path),
            size=path.stat().st_size,
            inspection_note=collection_note,
        )
    finally:
        font.close()


def safe_filename(value: str, fallback: str = "字体") -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", value).strip(" .")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return (cleaned or fallback)[:80]


def safe_prop(value: str) -> str:
    return re.sub(r"[\r\n]+", " ", value).strip()


def _module_prop(info: FontInfo, version: str, version_code: int) -> str:
    display = safe_prop(info.display_name)
    return (
        f"id={FIXED_MODULE_ID}\n"
        f"name=小米13 Android 14 - {display}（全局版）\n"
        f"version={version}\n"
        f"versionCode={version_code}\n"
        f"author={AUTHOR}\n"
        "description=小米13 fuxi / Android 14+ 全局字体模块；"
        f"当前字体：{display}；使用单字体多链接方案，覆盖 MIUI、MiType、Roboto、"
        "Serif、等宽及小米时钟字体；保留系统原生 fonts.xml。\n"
    )


def _customize_script(info: FontInfo) -> str:
    system_aliases = "\n".join(SYSTEM_ALIASES)
    product_aliases = "\n".join(PRODUCT_ALIASES)
    font_name = safe_prop(info.display_name).replace('"', "'")
    return f'''#!/system/bin/sh

SKIPUNZIP=0
DEVICE="$(getprop ro.product.device)"
API="$(getprop ro.build.version.sdk)"

ui_print "****************************************"
ui_print " 小米13 Android 14 全局字体模块"
ui_print " 字体：{font_name}"
ui_print " 作者：{AUTHOR}"
ui_print "****************************************"

if [ "$DEVICE" != "fuxi" ]; then
  abort "! 此模块仅为小米13（fuxi）制作，当前设备：$DEVICE"
fi

if [ "$API" -lt 34 ]; then
  abort "! 此模块要求 Android 14 或更高版本，当前 API：$API"
fi

FONT_DIR="$MODPATH/system/fonts"
PRODUCT_FONT_DIR="$MODPATH/system/product/fonts"
BASE_FONT="{BASE_FONT_NAME}"

[ -f "$FONT_DIR/$BASE_FONT" ] || abort "! 模块内主字体文件缺失"
mkdir -p "$FONT_DIR" "$PRODUCT_FONT_DIR"

SYSTEM_ALIASES="
{system_aliases}
"

PRODUCT_ALIASES="
{product_aliases}
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
ui_print "- 已建立 {len(SYSTEM_ALIASES)} 个系统字体链接"
ui_print "- 已建立 {len(PRODUCT_ALIASES)} 个时钟字体链接"
ui_print "- 保留当前系统原生 fonts.xml"
ui_print "- 安装完成后请重启"

set_perm_recursive "$MODPATH" 0 0 0755 0644
'''


def _overlay_compat_service() -> str:
    system_aliases = "\n".join(SYSTEM_ALIASES)
    product_aliases = "\n".join(PRODUCT_ALIASES)
    return f'''#!/system/bin/sh
MODDIR="${{0%/*}}"
FONT="$MODDIR/system/fonts/{BASE_FONT_NAME}"
LOG="$MODDIR/overlay-compat.log"
OVERLAY_MOD="/data/adb/modules/cler1818_full_system_overlayfs"
OVERLAY_LOG="$OVERLAY_MOD/overlay.log"
exec >>"$LOG" 2>&1
echo "==== $(date '+%F %T') OverlayFS delayed font compatibility ===="
until [ "$(getprop sys.boot_completed)" = "1" ]; do sleep 2; done
if [ -d "$OVERLAY_MOD" ] && [ ! -f "$OVERLAY_MOD/disable" ] && [ ! -f "$OVERLAY_MOD/remove" ]; then
  echo "OverlayFS module detected; waiting for health check"
  WAITED=0
  while [ "$WAITED" -lt 180 ]; do
    grep -q "健康检查通过" "$OVERLAY_LOG" 2>/dev/null && break
    sleep 2
    WAITED=$((WAITED + 2))
  done
  [ "$WAITED" -ge 180 ] && echo "OverlayFS wait timed out; continuing"
  sleep 5
else
  echo "OverlayFS absent or disabled; using normal delayed bind"
  sleep 8
fi
[ -f "$FONT" ] || {{ echo "ERROR: font missing: $FONT"; exit 1; }}
SYSTEM_ALIASES="
{system_aliases}
"
PRODUCT_ALIASES="
{product_aliases}
"
SEEN="|"; OK=0; SKIP=0; FAIL=0
bind_one() {{
  ENTRY="$1"
  [ -e "$ENTRY" ] || {{ SKIP=$((SKIP + 1)); return; }}
  TARGET="$(readlink -f "$ENTRY" 2>/dev/null)"
  [ -n "$TARGET" ] && [ -f "$TARGET" ] || {{ SKIP=$((SKIP + 1)); return; }}
  case "$SEEN" in *"|$TARGET|"*) return ;; esac
  SEEN="${{SEEN}}${{TARGET}}|"
  if mount --bind "$FONT" "$TARGET"; then
    echo "OK: $ENTRY -> $TARGET"; OK=$((OK + 1))
  else
    echo "FAIL: $ENTRY -> $TARGET"; FAIL=$((FAIL + 1))
  fi
}}
for NAME in $SYSTEM_ALIASES; do bind_one "/system/fonts/$NAME"; done
for NAME in $PRODUCT_ALIASES; do
  bind_one "/product/fonts/$NAME"
  bind_one "/system/product/fonts/$NAME"
done
echo "Completed: ok=$OK skip=$SKIP fail=$FAIL"
'''


def _zip_info(arcname: str, mode: int) -> zipfile.ZipInfo:
    now = datetime.now()
    info = zipfile.ZipInfo(
        filename=arcname.replace("\\", "/"),
        date_time=(now.year, now.month, now.day, now.hour, now.minute, now.second),
    )
    info.create_system = 3
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (mode & 0xFFFF) << 16
    return info


def _write_text(zf: zipfile.ZipFile, arcname: str, text: str, executable: bool = False) -> None:
    mode = 0o100755 if executable else 0o100644
    zf.writestr(_zip_info(arcname, mode), text.encode("utf-8"), compress_type=zipfile.ZIP_DEFLATED)


def _write_font(zf: zipfile.ZipFile, source: Path, arcname: str) -> None:
    info = _zip_info(arcname, 0o100644)
    with source.open("rb") as src, zf.open(info, "w", force_zip64=True) as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)


def generate_module(
    font_path: str | Path,
    output_zip: str | Path,
    overlay_compat: bool = True,
) -> tuple[Path, FontInfo]:
    info = inspect_font(font_path, allow_unreadable=True)
    output = Path(output_zip).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    version = datetime.now().strftime("%Y.%m.%d-%H%M%S")
    version_code = int(time.time())
    module_prop = _module_prop(info, version, version_code)
    customize = _customize_script(info)

    try:
        with zipfile.ZipFile(
            output,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
            allowZip64=True,
        ) as zf:
            _write_text(zf, "META-INF/com/google/android/update-binary", "#!/sbin/sh\n#MAGISK\n", True)
            _write_text(zf, "META-INF/com/google/android/updater-script", "#MAGISK\n")
            _write_text(zf, "module.prop", module_prop)
            _write_text(zf, "system.prop", "ro.miui.ui.font.mi_font_path=null\n")
            _write_text(zf, "customize.sh", customize, True)
            if overlay_compat:
                _write_text(zf, "service.sh", _overlay_compat_service(), True)
            _write_font(zf, info.path, f"system/fonts/{BASE_FONT_NAME}")
    except Exception as exc:
        if output.exists():
            output.unlink()
        raise ModuleBuildError(f"生成模块失败：{exc}") from exc

    validate_module(output, info.sha256)
    return output, info


def validate_module(module_zip: str | Path, expected_font_sha256: str | None = None) -> dict[str, object]:
    path = Path(module_zip).expanduser().resolve()
    required = {
        "META-INF/com/google/android/update-binary",
        "META-INF/com/google/android/updater-script",
        "module.prop",
        "system.prop",
        "customize.sh",
        f"system/fonts/{BASE_FONT_NAME}",
    }
    with zipfile.ZipFile(path, "r") as zf:
        names = zf.namelist()
        bad_paths = [name for name in names if "\\" in name]
        missing = sorted(required.difference(names))
        if bad_paths:
            raise ModuleBuildError(f"压缩包存在错误路径分隔符：{bad_paths}")
        if missing:
            raise ModuleBuildError(f"压缩包缺少必要文件：{missing}")
        if "#MAGISK" not in zf.read("META-INF/com/google/android/update-binary").decode("utf-8", "replace"):
            raise ModuleBuildError("update-binary 缺少 #MAGISK 标识")

        digest = hashlib.sha256()
        with zf.open(f"system/fonts/{BASE_FONT_NAME}", "r") as font_stream:
            for block in iter(lambda: font_stream.read(1024 * 1024), b""):
                digest.update(block)
        font_sha256 = digest.hexdigest()
        if expected_font_sha256 and font_sha256.lower() != expected_font_sha256.lower():
            raise ModuleBuildError("模块内字体哈希与原字体不一致")

        module_prop = zf.read("module.prop").decode("utf-8", "replace")
        if f"id={FIXED_MODULE_ID}" not in module_prop:
            raise ModuleBuildError("模块 ID 不正确")

    return {
        "path": str(path),
        "size": path.stat().st_size,
        "entries": names,
        "font_sha256": font_sha256,
        "module_id": FIXED_MODULE_ID,
    }


def default_output_name(info: FontInfo) -> str:
    return f"{safe_filename(info.display_name)}_小米13全局字体模块_lzhp529.zip"
