# Xiaomi13Font

Xiaomi13Font 是面向小米 13（代号 `fuxi`）的 Android 14 / MIUI 14 全局字体 Magisk 模块生成器。

作者：lzhp529

项目提供两种成品：

- 完整便携文件夹版：带图形界面和内置 ADB，解压即用。
- CMD 脚本版：包含 `Xiaomi13Font.cmd` 与可修改的 PowerShell 源码。

工具不会附带任何第三方字体。用户需要自行选择具有合法使用权的 TTF/OTF 字体。

## 已验证的设备环境

本项目最初在以下设备上开发和验证：

| 项目 | 信息 |
|---|---|
| 手机 | Xiaomi 13 |
| 型号 | 2211133C |
| 设备代号 | fuxi |
| MIUI | MIUI 14.0.5.0.UMCCNXM |
| Android | Android 14 |
| API | 34 |
| CPU 架构 | arm64-v8a |
| 安全补丁 | 2023-10-01 |
| Root | Magisk Alpha |
| Magisk 版本 | e8a58776-alpha / 30700 |

其他系统版本、HyperOS、其他手机型号或其他 Root 方案没有经过验证。模块安装脚本会检查设备代号，非 `fuxi` 设备默认拒绝安装。

## 功能

- 选择本地 `.ttf` 或 `.otf` 字体。
- 图形版可以读取字体名称、字形数量、Unicode 映射数量和基础字符覆盖情况。
- 自动生成符合现代 Magisk/Alpha 格式的 ZIP。
- ZIP 内部统一使用 `/`，避免 Windows 压缩工具产生反斜杠路径。
- 所有生成模块固定使用同一个模块 ID：`xiaomi13_fuxi_global_font`。
- 安装新的字体模块时会更新旧模块，不会让多个字体模块互相争抢挂载。
- 使用“一份真实字体 + 多个符号链接”的方式节省空间。
- 覆盖常用 MIUI、MiType、MiuiEx、Roboto、Serif、等宽和 Source Sans 字体族。
- 可同时覆盖部分小米锁屏与时钟字体。
- 保留设备当前 Android 14 原生 `fonts.xml`，不会用旧系统 XML 覆盖新系统配置。
- 自动写入 `ro.miui.ui.font.mi_font_path=null`。
- 默认启用“OverlayFS 延迟兼容模式”：等待全系统 OverlayFS 完成后，再把字体绑定到实际系统字体文件，避免稍后被 OverlayFS 遮住。
- 兼容脚本会在模块目录写入 `overlay-compat.log`，便于检查成功、跳过和失败的字体入口。
- 支持仅生成、复制到手机、直接调用 Magisk 安装。
- 永不自动重启手机。

## 下载与使用

请在仓库的 Releases 页面下载成品。

### 完整便携版

1. 下载 `Xiaomi13Font-Portable-vX.Y.Z.zip`。
2. 完整解压 ZIP，不要直接在压缩软件内运行。
3. 双击 `Xiaomi13Font.exe`。
4. 选择 TTF/OTF 字体。
5. 保持“覆盖小米锁屏/时钟字体”开启即可获得最大覆盖范围。
6. 如果手机装有全系统 OverlayFS，请保持“OverlayFS 延迟兼容模式”开启（默认已开启）。
7. 选择以下操作之一：
   - 仅生成 Magisk 模块；
   - 生成并复制到手机；
   - 生成并直接安装。
8. 安装成功后，在 Magisk 模块页面确认开关处于开启状态，再手动重启手机。

如果选择直接安装，需要：

- 手机开启 USB 调试；
- 手机上允许当前电脑的 USB 调试授权；
- Magisk 已为 Shell 授予超级用户权限；
- 同一时间只连接一台 Android 设备。

### CMD 脚本版

1. 下载 `Xiaomi13Font-Script-vX.Y.Z.zip`。
2. 完整解压。
3. 双击 `Xiaomi13Font.cmd`。
4. 在弹出的窗口中选择 TTF/OTF 字体。
5. 按提示选择生成、复制或直接安装。

也可以从命令行调用：

```bat
Xiaomi13Font.cmd "D:\Fonts\MyFont.ttf" -Action Install
```

CMD 文件负责启动同目录的 `Xiaomi13Font.ps1`。PowerShell 文件是完整可读源码，方便以后适配新的 Magisk 或 MIUI 规则。

## 模块覆盖范围

模块默认建立 41 个系统字体链接，包括：

- `MiSansVF.ttf`、`MiSansVF_Overlay.ttf`、`MiLanProVF.ttf`
- `MitypeVF.ttf`、`MitypeMonoVF.ttf`
- `Miui-*`、`MiuiEx-*`
- `Roboto-*`、`RobotoStatic-Regular.ttf`
- `NotoSerif-*`
- `DroidSansMono.ttf`、`CutiveMono.ttf`
- `SourceSansPro-*`

开启时钟覆盖时，另外建立 6 个产品字体链接：

- `MiClock.otf`
- `MiClockMono.otf`
- `MiClockThin.otf`
- `MiClockTibetan-Thin.ttf`
- `MiClockUyghur-Thin.ttf`
- `MiSansC_3.005.ttf`

字体模块无法强制替换以下内容：

- 应用 APK 内自带的字体；
- 图片、Canvas 路径或 Web 字体；
- 所选字体中不存在的字符；
- 彩色表情字体；
- 某些厂商组件中硬编码的数字或图标字体。

当所选字体缺少某个字符时，Android 会回退到系统字体。建议选择具有完整中文、英文和数字覆盖的字体。

## Invalid Uri 是什么

部分版本的 MiXplorer 会把字体模块以类似下面的 Content URI 交给 Magisk：

```text
content://com.mixplorer.silver.file/...
```

Magisk Alpha 可能无法打开这个 URI，安装页面会停在：

```text
- Copying zip to temp directory
! Invalid Uri
```

相关日志通常为：

```text
FileNotFoundException: No content provider
```

这表示 Magisk 无法访问 MiXplorer 的文件提供器，不代表模块 ZIP 损坏。

解决方法：

1. 使用 Android 系统文件选择器选择 ZIP；
2. 使用支持标准 Storage Access Framework 的文件管理器；
3. 或使用 Xiaomi13Font 的“生成并直接安装”。

直接安装会把 ZIP 传输到：

```text
/data/local/tmp/xiaomi13font-module.zip
```

然后执行：

```text
magisk --install-module /data/local/tmp/xiaomi13font-module.zip
```

因此完全绕过 MiXplorer Content URI。

## 模块结构

生成的模块大致结构如下：

```text
META-INF/
  com/google/android/update-binary
  com/google/android/updater-script
module.prop
customize.sh
service.sh
system.prop
system/
  fonts/
    Xiaomi13GlobalFont.ttf
```

`customize.sh` 在安装时创建字体链接。模块不会打包旧版 `fonts.xml`，从而降低 Android 系统升级后字体配置不匹配的风险。

`service.sh` 是 v1.1.0 新增的 OverlayFS 延迟兼容脚本。它等待开机完成；检测到 `cler1818_full_system_overlayfs` 时，会继续等待其日志出现“健康检查通过”，再延迟 5 秒进行绑定。若未安装该 OverlayFS 模块，则采用普通延迟绑定。脚本最长等待 180 秒，绝不会自动重启手机。

运行记录位于：

```text
/data/adb/modules/xiaomi13_fuxi_global_font/overlay-compat.log
```

## 卸载与故障恢复

正常卸载：

1. 打开 Magisk/Alpha；
2. 进入模块页面；
3. 移除 Xiaomi13Font 模块；
4. 重启手机。

模块 ID：

```text
xiaomi13_fuxi_global_font
```

如果安装后无法正常进入系统，可以在 Recovery 或具有 Root 权限的 ADB 环境中删除：

```text
/data/adb/modules/xiaomi13_fuxi_global_font
```

也可以进入 Magisk 安全模式禁用所有模块。

任何 Root 模块都有风险。安装前请保证重要资料已备份，并确认拥有可用的救砖方案。

## 从源码构建

构建环境：

- Windows 10/11 x64
- Python 3.12
- PyInstaller
- fontTools

运行：

```powershell
./build.ps1 -Version 1.1.0
```

构建脚本会：

1. 下载 Google 官方 Android platform-tools；
2. 安装指定的 Python 构建依赖；
3. 生成 PyInstaller 文件夹便携版；
4. 生成 CMD/PowerShell 脚本包；
5. 把两个 ZIP 放入 `artifacts` 目录。

仓库也提供 GitHub Actions 工作流，可通过手动运行或推送 `v*` 标签构建成品。

## 参考资料

- 酷安《Miui14全局字体教程》：https://www.coolapk.com/feed/45227377
- Magisk 模块开发文档：https://topjohnwu.github.io/Magisk/guides.html
- Android platform-tools：https://developer.android.com/tools/releases/platform-tools

## 字体版权

本项目不提供、复制或分发任何第三方字体。字体文件可能受到著作权、商标或单独许可协议保护。请仅使用你有权使用和修改的字体，生成的模块也请勿在没有授权的情况下公开传播。

## 作者

lzhp529
