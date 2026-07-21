# Xiaomi13Font v1.4.0

小米 13（fuxi）MIUI 14 / Android 14 全局字体 Magisk 模块生成器。

作者：lzhp529

v1.4.0 保留最初原始 1.0 的六按钮界面和全部功能，并修复 OverlayFS 旧日志导致延迟挂载提前执行的问题。

## 原始界面与功能完整保留

图形版保留以下六个按钮：

1. 生成模块到电脑
2. 生成并复制到手机
3. 生成并安装 Magisk
4. 安装并重启手机
5. 检测手机
6. 一键重启手机

同时保留：更改目录、打开目录、运行进度条、详细日志、手机/Root/Magisk 检测、复制后 SHA-256 校验、安装完成验证和所有重启确认窗口。

固定模块 ID：

```text
fuxi_a14_inugami_momo_global_font
```

主字体文件名：

```text
GlobalFont.ttf
```

以后安装新字体会更新替换旧字体，不会产生多个不同 ID 的字体模块。

## OverlayFS 延迟兼容模式

界面增加一个复选框：

```text
OverlayFS 延迟兼容模式（默认开启，可取消）
```

勾选后，生成模块包含 `service.sh`。v1.4.0 不再仅搜索日志中的“健康检查通过”，而是同时执行以下检查：

- OverlayFS 日志修改时间必须属于本次开机，避免读取上一次启动遗留的成功记录。
- `/system` 与 `/product` 的 `cler1818_full_overlayfs` 挂载必须真实存在。
- 挂载状态连续三次检查稳定后，再额外等待 8 秒。
- 每个字体目标绑定后立即比较 SHA-256。
- 校验失败时最多自动重试三轮，每轮间隔 10 秒。

这可以解决 OverlayFS 比字体模块晚几十秒完成，导致小米笔记编辑页、WebView 或后来启动的应用重新使用系统默认字体的问题。

日志位置：

```text
/data/adb/modules/fuxi_a14_inugami_momo_global_font/overlay-compat.log
```

取消勾选后生成传统模块，不包含 `service.sh`。

## 多字体集合与检查失败

部分文件虽然扩展名为 `.ttf` 或 `.otf`，内部实际包含两个或更多字体，fontTools 可能返回：

```text
specify a font number between 0 and 1 (inclusive)
```

v1.4.0 会使用中文提示：

- 检测到多字体集合时，使用第一个字体读取显示名称和基本信息。
- 生成模块时保留完整原始字体文件，不拆分、不修改。
- 即使详细检查完全失败，也允许继续生成、复制、安装或安装并重启。
- 检查失败不代表文件一定损坏，但最终能否显示由 Android 字体加载器决定。

## 使用方法

### 便携 EXE 版

1. 完整解压 `Xiaomi13Font-Portable-v1.4.0.zip`。
2. 双击 `字体模块生成器.exe`。
3. 选择 TTF/OTF 字体。
4. 按需要勾选或取消 OverlayFS 延迟兼容模式。
5. 点击六个操作按钮之一。

“安装并重启手机”和“一键重启手机”都会在真正重启前弹出确认窗口。

### CMD 脚本版

双击 `字体模块生成器.cmd`，然后按照原始六项菜单操作。CMD 默认启用 OverlayFS 兼容模式；需要关闭时可使用：

```bat
字体模块生成器.cmd -DisableOverlayCompat
```

## 已验证设备

- 手机：Xiaomi 13 / 2211133C
- 设备代号：fuxi
- MIUI：V14.0.5.0.UMCCNXM
- Android：14 / API 34
- Magisk：Alpha e8a58776-alpha / 30700

## Invalid Uri

MiXplorer 可能向 Magisk 提供无法访问的私有 `content://` 地址，从而提示 `Invalid Uri`。本工具会把模块推送到 `/data/local/tmp/lzhp529-global-font.zip`，再调用 `magisk --install-module`，不会经过 MiXplorer 文件地址。

## 字体版权

项目和 Release 不附带任何第三方字体。请只使用你有权使用的 TTF/OTF 文件。

## 构建

```powershell
./build.ps1 -Version 1.4.0
```

生成：

- `artifacts/Xiaomi13Font-Portable-v1.4.0.zip`
- `artifacts/Xiaomi13Font-Script-v1.4.0.zip`
