from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from fontTools.ttLib import TTFont


APP_NAME = "Xiaomi13Font"
APP_VERSION = "1.0.0"
AUTHOR = "lzhp529"
MODULE_ID = "xiaomi13_fuxi_global_font"
DEVICE_CODENAME = "fuxi"
MIN_ANDROID_API = 34


SYSTEM_ALIASES = [
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
]


PRODUCT_ALIASES = [
    "MiClock.otf",
    "MiClockMono.otf",
    "MiClockThin.otf",
    "MiClockTibetan-Thin.ttf",
    "MiClockUyghur-Thin.ttf",
    "MiSansC_3.005.ttf",
]


@dataclass
class FontInfo:
    family: str
    full_name: str
    postscript_name: str
    glyph_count: int
    cmap_count: int
    is_variable: bool
    coverage: dict[str, bool]


def clean_prop_value(value: str) -> str:
    return re.sub(r"[\r\n]+", " ", value).strip()


def safe_filename(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(" .")
    return value or "font"


def get_name(font: TTFont, name_id: int) -> str:
    values: list[str] = []
    if "name" not in font:
        return ""
    for record in font["name"].names:
        if record.nameID != name_id:
            continue
        try:
            value = record.toUnicode().strip()
        except Exception:
            continue
        if value and value not in values:
            values.append(value)
    return values[0] if values else ""


def analyze_font(path: Path) -> FontInfo:
    if path.suffix.lower() not in {".ttf", ".otf"}:
        raise ValueError("当前仅支持 TTF/OTF。TTC 字体合集需要先拆分。")
    font = TTFont(str(path), lazy=True)
    family = get_name(font, 1) or path.stem
    full_name = get_name(font, 4) or family
    postscript_name = get_name(font, 6)
    cmap: set[int] = set()
    if "cmap" in font:
        for table in font["cmap"].tables:
            cmap.update(table.cmap.keys())
    coverage_points = {
        "常用中文“中”": 0x4E2D,
        "常用中文“国”": 0x56FD,
        "生僻字“𠮷”": 0x20BB7,
        "英文 A": 0x0041,
        "数字 0": 0x0030,
        "彩色表情 😀": 0x1F600,
    }
    coverage = {label: codepoint in cmap for label, codepoint in coverage_points.items()}
    glyph_count = len(font.getGlyphOrder())
    is_variable = "fvar" in font
    font.close()
    return FontInfo(
        family=family,
        full_name=full_name,
        postscript_name=postscript_name,
        glyph_count=glyph_count,
        cmap_count=len(cmap),
        is_variable=is_variable,
        coverage=coverage,
    )


def module_customize_script(include_clock: bool) -> str:
    system_aliases = "\n".join(SYSTEM_ALIASES)
    product_aliases = "\n".join(PRODUCT_ALIASES if include_clock else [])
    return f'''#!/system/bin/sh

SKIPUNZIP=0

DEVICE="$(getprop ro.product.device)"
API="$(getprop ro.build.version.sdk)"

ui_print "****************************************"
ui_print " Xiaomi 13 Android 14 全局字体模块"
ui_print " 作者：{AUTHOR}"
ui_print "****************************************"

if [ "$DEVICE" != "{DEVICE_CODENAME}" ]; then
  abort "! 此模块仅适配小米13（{DEVICE_CODENAME}），当前设备：$DEVICE"
fi

if [ "$API" -lt {MIN_ANDROID_API} ]; then
  abort "! 此模块要求 Android 14 / API 34 或更高版本，当前 API：$API"
fi

FONT_DIR="$MODPATH/system/fonts"
PRODUCT_FONT_DIR="$MODPATH/system/product/fonts"
BASE_FONT="Xiaomi13GlobalFont.ttf"

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
ui_print "- 已建立系统字体多链接覆盖"
ui_print "- 保留系统原生 fonts.xml"
ui_print "- 模块 ID：{MODULE_ID}"
ui_print "- 安装完成后请手动重启"

set_perm_recursive "$MODPATH" 0 0 0755 0644
'''


def zip_text_entry(zf: zipfile.ZipFile, name: str, content: str, mode: int = 0o644) -> None:
    info = zipfile.ZipInfo(name, datetime.now().timetuple()[:6])
    info.create_system = 3
    info.external_attr = (0o100000 | mode) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    zf.writestr(info, content.encode("utf-8"))


def zip_file_entry(zf: zipfile.ZipFile, name: str, source: Path, mode: int = 0o644) -> None:
    info = zipfile.ZipInfo(name, datetime.now().timetuple()[:6])
    info.create_system = 3
    info.external_attr = (0o100000 | mode) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    with source.open("rb") as src, zf.open(info, "w") as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)


def generate_module(font_path: Path, output_dir: Path, include_clock: bool = True) -> tuple[Path, FontInfo]:
    info = analyze_font(font_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    display_name = clean_prop_value(info.full_name or info.family or font_path.stem)
    timestamp = datetime.now().strftime("%Y.%m.%d-%H%M")
    version_code = int(time.time())
    module_prop = f'''id={MODULE_ID}
name=小米13 Android 14 - {display_name}（全局版）
version={timestamp}
versionCode={version_code}
author={AUTHOR}
description=适配小米13 fuxi / MIUI 14.0.5 / Android 14 的全局字体模块。覆盖 MIUI、MiType、Roboto、Serif、等宽字体及可选时钟字体，保留系统原生 fonts.xml。
'''
    output_name = safe_filename(f"Xiaomi13Font_{display_name}_{timestamp}.zip")
    output_path = output_dir / output_name
    temp_path = output_dir / f".{output_name}.tmp"
    if temp_path.exists():
        temp_path.unlink()
    with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zip_text_entry(zf, "META-INF/com/google/android/update-binary", "#!/sbin/sh\n#MAGISK\n", 0o755)
        zip_text_entry(zf, "META-INF/com/google/android/updater-script", "#MAGISK\n")
        zip_text_entry(zf, "module.prop", module_prop)
        zip_text_entry(zf, "system.prop", "ro.miui.ui.font.mi_font_path=null\n")
        zip_text_entry(zf, "customize.sh", module_customize_script(include_clock), 0o755)
        zip_file_entry(zf, "system/fonts/Xiaomi13GlobalFont.ttf", font_path)
    with zipfile.ZipFile(temp_path, "r") as zf:
        names = zf.namelist()
        if any("\\" in name for name in names):
            raise RuntimeError("压缩包出现 Windows 反斜杠路径，已停止生成。")
        required = {
            "module.prop",
            "customize.sh",
            "system.prop",
            "system/fonts/Xiaomi13GlobalFont.ttf",
            "META-INF/com/google/android/update-binary",
        }
        missing = sorted(required.difference(names))
        if missing:
            raise RuntimeError(f"模块缺少必要文件：{', '.join(missing)}")
    if output_path.exists():
        output_path.unlink()
    temp_path.replace(output_path)
    return output_path, info


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def find_adb() -> Path:
    candidates: list[Path] = []
    bundle_root = Path(getattr(sys, "_MEIPASS", app_root()))
    candidates.append(bundle_root / "tools" / "platform-tools" / "adb.exe")
    candidates.append(app_root() / "tools" / "platform-tools" / "adb.exe")
    path_adb = shutil.which("adb")
    if path_adb:
        candidates.append(Path(path_adb))
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("未找到 adb.exe。请使用完整便携包，或把 ADB 加入系统 PATH。")


def run_command(args: list[str], timeout: int = 60) -> str:
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        creationflags=creationflags,
    )
    output = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0:
        raise RuntimeError(output.strip() or f"命令执行失败：{result.returncode}")
    return output.strip()


def get_connected_device(adb: Path) -> str:
    output = run_command([str(adb), "devices"], timeout=20)
    devices = []
    for line in output.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            devices.append(parts[0])
    if not devices:
        raise RuntimeError("未检测到已授权的手机。请开启 USB 调试并允许此电脑。")
    if len(devices) > 1:
        raise RuntimeError("检测到多台设备，请只保留一台手机连接。")
    device = run_command([str(adb), "shell", "getprop", "ro.product.device"], timeout=20).strip()
    if device != DEVICE_CODENAME:
        raise RuntimeError(f"当前设备为 {device or '未知'}，工具只适配小米13（{DEVICE_CODENAME}）。")
    return devices[0]


def copy_module_to_phone(module_path: Path) -> str:
    adb = find_adb()
    get_connected_device(adb)
    remote_dir = "/sdcard/Download/Xiaomi13Font"
    remote_path = f"{remote_dir}/{safe_filename(module_path.name)}"
    run_command([str(adb), "shell", "mkdir", "-p", remote_dir], timeout=20)
    run_command([str(adb), "push", str(module_path), remote_path], timeout=120)
    return remote_path


def install_module_to_phone(module_path: Path) -> str:
    adb = find_adb()
    get_connected_device(adb)
    remote_path = "/data/local/tmp/xiaomi13font-module.zip"
    run_command([str(adb), "push", str(module_path), remote_path], timeout=120)
    output = run_command(
        [str(adb), "shell", "su", "-c", f"magisk --install-module {remote_path}"],
        timeout=180,
    )
    verify = run_command(
        [
            str(adb),
            "shell",
            "su",
            "-c",
            f"cat /data/adb/modules_update/{MODULE_ID}/module.prop 2>/dev/null || "
            f"cat /data/adb/modules/{MODULE_ID}/module.prop 2>/dev/null",
        ],
        timeout=30,
    )
    try:
        run_command([str(adb), "shell", "rm", "-f", remote_path], timeout=20)
    except Exception:
        pass
    if f"id={MODULE_ID}" not in verify:
        raise RuntimeError("Magisk 返回后未找到待启用模块，请查看安装输出。\n" + output)
    return output


class Xiaomi13FontApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} v{APP_VERSION} - 作者 {AUTHOR}")
        self.geometry("860x720")
        self.minsize(780, 650)
        self.font_path = tk.StringVar()
        self.output_dir = tk.StringVar(value=str(Path.home() / "Documents" / "Xiaomi13Font" / "Output"))
        self.include_clock = tk.BooleanVar(value=True)
        self.info_text = tk.StringVar(value="尚未选择字体")
        self.current_info: FontInfo | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")

        main = ttk.Frame(self, padding=18)
        main.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(main, text="小米13 Android 14 全局字体模块生成器", font=("Microsoft YaHei UI", 18, "bold"))
        title.pack(anchor=tk.W)
        ttk.Label(
            main,
            text="适配：Xiaomi 13（2211133C / fuxi）｜MIUI 14.0.5｜Android 14｜Magisk Alpha 30700",
        ).pack(anchor=tk.W, pady=(4, 16))

        font_box = ttk.LabelFrame(main, text="1. 选择字体", padding=12)
        font_box.pack(fill=tk.X)
        row = ttk.Frame(font_box)
        row.pack(fill=tk.X)
        ttk.Entry(row, textvariable=self.font_path).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(row, text="选择 TTF/OTF", command=self.choose_font).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Label(font_box, textvariable=self.info_text, wraplength=790, justify=tk.LEFT).pack(anchor=tk.W, pady=(10, 0))

        output_box = ttk.LabelFrame(main, text="2. 输出设置", padding=12)
        output_box.pack(fill=tk.X, pady=(12, 0))
        output_row = ttk.Frame(output_box)
        output_row.pack(fill=tk.X)
        ttk.Entry(output_row, textvariable=self.output_dir).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(output_row, text="选择目录", command=self.choose_output_dir).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Checkbutton(output_box, text="同时覆盖小米锁屏/时钟字体（全局模式，默认开启）", variable=self.include_clock).pack(anchor=tk.W, pady=(10, 0))

        action_box = ttk.LabelFrame(main, text="3. 生成与安装", padding=12)
        action_box.pack(fill=tk.X, pady=(12, 0))
        ttk.Button(action_box, text="仅生成 Magisk 模块", command=lambda: self.start_action("generate")).pack(side=tk.LEFT)
        ttk.Button(action_box, text="生成并复制到手机", command=lambda: self.start_action("copy")).pack(side=tk.LEFT, padx=10)
        ttk.Button(action_box, text="生成并直接安装", command=lambda: self.start_action("install")).pack(side=tk.LEFT)

        ttk.Label(
            main,
            text="直接安装会绕过 MiXplorer Content URI，因此不会出现 Invalid Uri。工具不会自动重启手机。",
            foreground="#9b4d00",
        ).pack(anchor=tk.W, pady=(10, 0))

        log_box = ttk.LabelFrame(main, text="运行日志", padding=8)
        log_box.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        self.log = tk.Text(log_box, height=14, wrap=tk.WORD, state=tk.DISABLED, font=("Consolas", 10))
        scrollbar = ttk.Scrollbar(log_box, orient=tk.VERTICAL, command=self.log.yview)
        self.log.configure(yscrollcommand=scrollbar.set)
        self.log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.write_log(f"{APP_NAME} v{APP_VERSION} 已启动。作者：{AUTHOR}")

    def write_log(self, text: str) -> None:
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, text.rstrip() + "\n")
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def thread_log(self, text: str) -> None:
        self.after(0, self.write_log, text)

    def choose_font(self) -> None:
        selected = filedialog.askopenfilename(
            title="选择字体",
            filetypes=[("字体文件", "*.ttf *.otf"), ("TTF 字体", "*.ttf"), ("OTF 字体", "*.otf")],
        )
        if not selected:
            return
        self.font_path.set(selected)
        try:
            info = analyze_font(Path(selected))
            self.current_info = info
            coverage = "，".join(f"{key}:{'有' if value else '无'}" for key, value in info.coverage.items())
            self.info_text.set(
                f"字体：{info.full_name}｜字形：{info.glyph_count:,}｜Unicode 映射：{info.cmap_count:,}｜"
                f"{'可变字体' if info.is_variable else '静态字体'}\n{coverage}"
            )
            self.write_log(f"已读取字体：{selected}")
        except Exception as exc:
            self.current_info = None
            self.info_text.set(f"字体检查失败：{exc}")
            messagebox.showerror("字体检查失败", str(exc))

    def choose_output_dir(self) -> None:
        selected = filedialog.askdirectory(title="选择模块输出目录", initialdir=self.output_dir.get())
        if selected:
            self.output_dir.set(selected)

    def start_action(self, action: str) -> None:
        path = Path(self.font_path.get().strip().strip('"'))
        if not path.is_file():
            messagebox.showwarning("请选择字体", "请先选择有效的 TTF/OTF 字体文件。")
            return
        output_dir = Path(self.output_dir.get().strip().strip('"'))
        include_clock = bool(self.include_clock.get())
        threading.Thread(
            target=self._run_action,
            args=(action, path, output_dir, include_clock),
            daemon=True,
        ).start()

    def _run_action(self, action: str, font_path: Path, output_dir: Path, include_clock: bool) -> None:
        try:
            self.thread_log("正在生成模块……")
            module_path, info = generate_module(font_path, output_dir, include_clock)
            self.thread_log(f"生成成功：{module_path}")
            self.thread_log(f"字体字形数量：{info.glyph_count:,}")
            if action == "copy":
                self.thread_log("正在复制到手机……")
                remote = copy_module_to_phone(module_path)
                self.thread_log(f"已复制到：{remote}")
                self.after(0, messagebox.showinfo, "完成", f"模块已生成并复制到手机：\n{remote}")
            elif action == "install":
                self.thread_log("正在通过 ADB 调用 Magisk 安装……")
                output = install_module_to_phone(module_path)
                self.thread_log(output)
                self.thread_log("安装成功。请确认 Magisk 模块开关后手动重启手机。")
                self.after(0, messagebox.showinfo, "安装成功", "模块已安装并等待重启生效。\n工具不会自动重启手机。")
            else:
                self.after(0, messagebox.showinfo, "生成成功", f"模块已生成：\n{module_path}")
        except Exception as exc:
            self.thread_log(f"失败：{exc}")
            self.after(0, messagebox.showerror, "操作失败", str(exc))


def main() -> None:
    app = Xiaomi13FontApp()
    app.mainloop()


if __name__ == "__main__":
    main()
