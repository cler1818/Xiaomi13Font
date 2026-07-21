from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from module_core import (
    AUTHOR,
    FIXED_MODULE_ID,
    FontInfo,
    ModuleBuildError,
    default_output_name,
    generate_module,
    inspect_font,
)


CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
REMOTE_EXPORT_DIR = "/sdcard/Download/FontModules"
REMOTE_INSTALL_ZIP = "/data/local/tmp/lzhp529-global-font.zip"
APP_VERSION = "1.4.0"


def application_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def find_adb() -> Path | None:
    candidates = [
        application_dir() / "adb" / "adb.exe",
        Path(__file__).resolve().parent.parent / "adb" / "adb.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    system_adb = shutil.which("adb")
    return Path(system_adb).resolve() if system_adb else None


def format_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{size} B"


class CommandError(RuntimeError):
    pass


class AdbClient:
    def __init__(self, adb_path: Path, logger):
        self.adb_path = adb_path
        self.logger = logger

    def run(self, *args: str, timeout: int = 120, check: bool = True) -> subprocess.CompletedProcess[str]:
        command = [str(self.adb_path), *args]
        self.logger("ADB: " + " ".join(args))
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                creationflags=CREATE_NO_WINDOW,
            )
        except subprocess.TimeoutExpired as exc:
            raise CommandError("ADB 操作超时；若手机弹出 Shell 超级用户请求，请允许后重试") from exc
        output = "\n".join(part.strip() for part in (completed.stdout, completed.stderr) if part.strip())
        if output:
            self.logger(output)
        if check and completed.returncode != 0:
            raise CommandError(output or f"ADB 命令失败，退出码 {completed.returncode}")
        return completed

    def one_device(self) -> str:
        completed = self.run("devices", "-l")
        devices: list[str] = []
        unauthorized: list[str] = []
        offline: list[str] = []
        for line in completed.stdout.splitlines()[1:]:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            serial = parts[0]
            state = parts[1] if len(parts) > 1 else ""
            if state == "device":
                devices.append(serial)
            elif state == "unauthorized":
                unauthorized.append(serial)
            elif state == "offline":
                offline.append(serial)
        if unauthorized:
            raise CommandError("手机尚未授权 USB 调试，请在手机上点击允许")
        if offline:
            raise CommandError("手机 ADB 状态为 offline，请重新插拔数据线")
        if not devices:
            raise CommandError("没有检测到手机，请确认数据线和 USB 调试")
        if len(devices) > 1:
            raise CommandError("检测到多台 ADB 设备，请只保留一台手机连接")
        return devices[0]

    def shell_text(self, command: str, root: bool = False, timeout: int = 120) -> str:
        self.one_device()
        if root:
            quoted = "'" + command.replace("'", "'\\''") + "'"
            completed = self.run("shell", "su", "-c", quoted, timeout=timeout)
        else:
            completed = self.run("shell", command, timeout=timeout)
        return completed.stdout.strip()

    def device_info(self) -> dict[str, str]:
        serial = self.one_device()
        props = {}
        for key in (
            "ro.product.model",
            "ro.product.device",
            "ro.build.version.release",
            "ro.build.version.sdk",
            "ro.build.version.incremental",
        ):
            props[key] = self.run("shell", "getprop", key).stdout.strip()
        root_output = self.shell_text("id", root=True)
        if "uid=0" not in root_output:
            raise CommandError("Shell 没有获得 Root 权限")
        props["magisk"] = self.shell_text("magisk -v; magisk -V", root=True)
        props["serial"] = serial
        return props

    def ensure_target_device(self) -> dict[str, str]:
        info = self.device_info()
        if info.get("ro.product.device") != "fuxi":
            raise CommandError(f"当前设备不是小米13 fuxi：{info.get('ro.product.device')}")
        try:
            sdk = int(info.get("ro.build.version.sdk", "0"))
        except ValueError:
            sdk = 0
        if sdk < 34:
            raise CommandError(f"当前系统低于 Android 14：API {sdk}")
        return info

    def copy_to_phone(self, module_zip: Path) -> str:
        self.one_device()
        self.run("shell", "mkdir", "-p", REMOTE_EXPORT_DIR)
        remote = f"{REMOTE_EXPORT_DIR}/{module_zip.name}"
        self.run("push", str(module_zip), remote, timeout=300)
        local_hash = self._sha256_local(module_zip)
        remote_hash = self.shell_text(f"sha256sum '{remote}' | cut -d ' ' -f 1")
        if remote_hash.lower() != local_hash.lower():
            raise CommandError("复制到手机后的文件哈希不一致")
        return remote

    def install_module(self, module_zip: Path) -> str:
        info = self.ensure_target_device()
        self.logger(
            f"设备：{info.get('ro.product.model')} / {info.get('ro.product.device')} / "
            f"Android {info.get('ro.build.version.release')} / API {info.get('ro.build.version.sdk')}"
        )
        self.run("push", str(module_zip), REMOTE_INSTALL_ZIP, timeout=300)
        try:
            completed = self.run(
                "shell",
                "su",
                "-c",
                f"magisk --install-module {REMOTE_INSTALL_ZIP}",
                timeout=300,
            )
            output = "\n".join((completed.stdout, completed.stderr))
            if "- Done" not in output and "Done" not in output:
                raise CommandError("Magisk 未返回安装完成标志，请检查上方日志")
            pending = self.shell_text(
                f"for P in /data/adb/modules/{FIXED_MODULE_ID}/module.prop "
                f"/data/adb/modules_update/{FIXED_MODULE_ID}/module.prop; do "
                "[ -f \"$P\" ] && cat \"$P\"; done; exit 0",
                root=True,
            )
            if f"id={FIXED_MODULE_ID}" not in pending:
                raise CommandError("Magisk 安装后未找到目标模块")
            return output.strip()
        finally:
            self.run("shell", "rm", "-f", REMOTE_INSTALL_ZIP, check=False)

    def reboot(self) -> None:
        self.one_device()
        self.run("reboot", timeout=30)

    @staticmethod
    def _sha256_local(path: Path) -> str:
        import hashlib

        digest = hashlib.sha256()
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()


class FontModuleMakerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"小米13 全局字体模块生成器 v{APP_VERSION} - {AUTHOR}")
        self.root.geometry("900x720")
        self.root.minsize(820, 650)

        self.font_path: Path | None = None
        self.font_info: FontInfo | None = None
        self.last_module: Path | None = None
        self.output_dir = application_dir() / "导出模块"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.adb_path = find_adb()
        self.action_buttons: list[ttk.Button] = []

        self.font_path_var = tk.StringVar(value="尚未选择字体")
        self.output_var = tk.StringVar(value=str(self.output_dir))
        self.overlay_compat_var = tk.BooleanVar(value=True)
        self.info_var = tk.StringVar(value="支持 TTF/OTF；TTC 需要先拆分。")
        self.status_var = tk.StringVar(value="就绪")

        self._build_ui()
        self.log(f"固定模块 ID：{FIXED_MODULE_ID}")
        self.log(f"作者：{AUTHOR}")
        self.log(f"ADB：{self.adb_path if self.adb_path else '未找到'}")

    def _build_ui(self) -> None:
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("Title.TLabel", font=("Microsoft YaHei UI", 18, "bold"))
        style.configure("Section.TLabelframe.Label", font=("Microsoft YaHei UI", 11, "bold"))
        style.configure("Action.TButton", font=("Microsoft YaHei UI", 10), padding=(10, 8))

        main = ttk.Frame(self.root, padding=16)
        main.pack(fill="both", expand=True)

        ttk.Label(main, text="小米13 Android 14 全局字体模块生成器", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            main,
            text="固定模块 ID，新字体会更新替换旧字体；保留系统原生 fonts.xml。",
        ).pack(anchor="w", pady=(4, 14))

        font_box = ttk.LabelFrame(main, text="1. 选择字体", style="Section.TLabelframe", padding=12)
        font_box.pack(fill="x")
        row = ttk.Frame(font_box)
        row.pack(fill="x")
        ttk.Entry(row, textvariable=self.font_path_var, state="readonly").pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="选择 TTF/OTF", command=self.select_font, style="Action.TButton").pack(side="left", padx=(10, 0))
        ttk.Label(font_box, textvariable=self.info_var, wraplength=820, justify="left").pack(anchor="w", pady=(10, 0))

        output_box = ttk.LabelFrame(main, text="2. 电脑导出位置", style="Section.TLabelframe", padding=12)
        output_box.pack(fill="x", pady=(12, 0))
        output_row = ttk.Frame(output_box)
        output_row.pack(fill="x")
        ttk.Entry(output_row, textvariable=self.output_var, state="readonly").pack(side="left", fill="x", expand=True)
        ttk.Button(output_row, text="更改目录", command=self.select_output_dir).pack(side="left", padx=(10, 0))
        ttk.Button(output_row, text="打开目录", command=self.open_output_dir).pack(side="left", padx=(8, 0))
        ttk.Checkbutton(
            output_box,
            text="OverlayFS 延迟兼容模式（默认开启，可取消）",
            variable=self.overlay_compat_var,
        ).pack(anchor="w", pady=(10, 0))

        action_box = ttk.LabelFrame(main, text="3. 生成、安装与重启", style="Section.TLabelframe", padding=12)
        action_box.pack(fill="x", pady=(12, 0))
        actions = ttk.Frame(action_box)
        actions.pack(fill="x")
        button_specs = (
            ("生成模块到电脑", self.generate_only),
            ("生成并复制到手机", self.generate_and_copy),
            ("生成并安装 Magisk", self.generate_and_install),
            ("安装并重启手机", self.generate_install_reboot),
            ("检测手机", self.detect_phone),
            ("一键重启手机", self.reboot_phone),
        )
        for index, (text, command) in enumerate(button_specs):
            button = ttk.Button(actions, text=text, command=command, style="Action.TButton")
            button.grid(row=index // 3, column=index % 3, sticky="ew", padx=5, pady=5)
            actions.columnconfigure(index % 3, weight=1)
            self.action_buttons.append(button)

        status_row = ttk.Frame(main)
        status_row.pack(fill="x", pady=(12, 6))
        self.progress = ttk.Progressbar(status_row, mode="indeterminate", length=180)
        self.progress.pack(side="left")
        ttk.Label(status_row, textvariable=self.status_var).pack(side="left", padx=(10, 0))

        log_box = ttk.LabelFrame(main, text="运行日志", style="Section.TLabelframe", padding=8)
        log_box.pack(fill="both", expand=True)
        self.log_text = tk.Text(log_box, height=12, wrap="word", font=("Consolas", 9), state="disabled")
        scrollbar = ttk.Scrollbar(log_box, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def log(self, message: str) -> None:
        def append():
            self.log_text.configure(state="normal")
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_text.insert("end", f"[{timestamp}] {message.rstrip()}\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")

        if threading.current_thread() is threading.main_thread():
            append()
        else:
            self.root.after(0, append)

    def set_busy(self, busy: bool, status: str = "") -> None:
        def update():
            state = "disabled" if busy else "normal"
            for button in self.action_buttons:
                button.configure(state=state)
            if busy:
                self.progress.start(10)
            else:
                self.progress.stop()
            self.status_var.set(status or ("处理中…" if busy else "就绪"))

        if threading.current_thread() is threading.main_thread():
            update()
        else:
            self.root.after(0, update)

    def run_task(self, title: str, task, success_message: str | None = None) -> None:
        self.set_busy(True, title)

        def worker():
            try:
                result = task()
                if success_message:
                    self.log(success_message)
                self.root.after(0, lambda: messagebox.showinfo("完成", success_message or "操作完成"))
                return result
            except Exception as exc:
                self.log(f"失败：{exc}")
                self.root.after(0, lambda exc=exc: messagebox.showerror("操作失败", str(exc)))
            finally:
                self.set_busy(False, "就绪")

        threading.Thread(target=worker, daemon=True).start()

    def select_font(self) -> None:
        selected = filedialog.askopenfilename(
            title="选择字体文件",
            filetypes=(("字体文件", "*.ttf *.otf"), ("TTF 字体", "*.ttf"), ("OTF 字体", "*.otf")),
        )
        if not selected:
            return
        self.font_path = Path(selected)
        self.font_path_var.set(str(self.font_path))
        self.info_var.set("正在检查字体…")

        def task():
            info = inspect_font(self.font_path, allow_unreadable=True)
            self.font_info = info
            variable = "是" + (f"（{', '.join(info.axes)}）" if info.axes else "") if info.is_variable else "否"
            warning = info.warning or "未发现明显覆盖问题"
            details = (
                f"名称：{info.display_name}　大小：{format_size(info.size)}　字形：{info.glyph_count:,}　"
                f"码位：{info.codepoint_count:,}\n"
                f"常用中日韩汉字：{info.cjk_count:,}　扩展 B：{info.cjk_ext_b_count:,}　"
                f"可变字体：{variable}\n提示：{warning}"
            )
            self.root.after(0, lambda: self.info_var.set(details))
            self.log(details)
            if info.inspection_note:
                self.root.after(
                    0,
                    lambda: messagebox.showwarning(
                        "字体检查提示",
                        "字体详细检查未完全通过。\n\n"
                        f"{info.inspection_note}\n\n"
                        "仍然可以生成模块、安装到手机或安装并重启。",
                    ),
                )

        self.run_task("检查字体", task, "字体检查完成")

    def select_output_dir(self) -> None:
        selected = filedialog.askdirectory(title="选择模块导出目录", initialdir=str(self.output_dir))
        if selected:
            self.output_dir = Path(selected).resolve()
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self.output_var.set(str(self.output_dir))

    def open_output_dir(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        os.startfile(self.output_dir)

    def require_font(self) -> Path:
        if self.font_path is None or not self.font_path.is_file():
            raise ModuleBuildError("请先选择 TTF/OTF 字体")
        return self.font_path

    def build_module(self) -> Path:
        font_path = self.require_font()
        info = self.font_info or inspect_font(font_path, allow_unreadable=True)
        self.font_info = info
        self.output_dir.mkdir(parents=True, exist_ok=True)
        output = self.output_dir / default_output_name(info)
        self.log(f"开始生成：{output}")
        module_path, _ = generate_module(font_path, output, self.overlay_compat_var.get())
        self.last_module = module_path
        self.log(f"模块生成成功：{module_path}")
        self.log(f"模块大小：{format_size(module_path.stat().st_size)}")
        return module_path

    def adb(self) -> AdbClient:
        adb_path = self.adb_path or find_adb()
        if adb_path is None:
            raise CommandError("未找到 adb.exe；请确认便携目录中的 adb 文件夹完整")
        return AdbClient(adb_path, self.log)

    def generate_only(self) -> None:
        self.run_task("生成模块", self.build_module, "模块已导出到电脑")

    def generate_and_copy(self) -> None:
        def task():
            module = self.build_module()
            remote = self.adb().copy_to_phone(module)
            self.log(f"已复制到手机：{remote}")

        self.run_task("生成并复制", task, "模块已生成并复制到手机 Download/FontModules")

    def generate_and_install(self) -> None:
        def task():
            module = self.build_module()
            self.adb().install_module(module)
            self.log("Magisk 安装成功，等待重启生效")

        self.run_task("生成并安装", task, "Magisk 模块已安装；请重启手机后生效")

    def generate_install_reboot(self) -> None:
        if not messagebox.askyesno(
            "确认安装并重启",
            "将生成字体模块、通过 Root 安装到 Magisk，然后立即重启手机。\n\n是否继续？",
        ):
            return

        def task():
            module = self.build_module()
            client = self.adb()
            client.install_module(module)
            self.log("安装成功，即将重启手机")
            client.reboot()

        self.run_task("安装并重启", task, "模块已安装，手机正在重启")

    def detect_phone(self) -> None:
        def task():
            info = self.adb().device_info()
            message = (
                f"序列号：{info.get('serial')}\n"
                f"型号：{info.get('ro.product.model')}\n"
                f"设备：{info.get('ro.product.device')}\n"
                f"Android：{info.get('ro.build.version.release')} / API {info.get('ro.build.version.sdk')}\n"
                f"版本：{info.get('ro.build.version.incremental')}\n"
                f"Magisk：{info.get('magisk')}"
            )
            self.log(message)

        self.run_task("检测手机", task, "手机、Root 和 Magisk 检测正常")

    def reboot_phone(self) -> None:
        if not messagebox.askyesno("确认重启", "确定立即重启已连接的手机吗？"):
            return
        self.run_task("重启手机", lambda: self.adb().reboot(), "重启命令已发送")


def main() -> None:
    if len(sys.argv) >= 4 and sys.argv[1] == "--build-module":
        generate_module(sys.argv[2], sys.argv[3])
        return
    root = tk.Tk()
    FontModuleMakerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
