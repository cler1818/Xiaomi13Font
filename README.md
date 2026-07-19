# Xiaomi13Font v1.3.0

小米 13（fuxi）MIUI 14 / Android 14 全局字体 Magisk 模块生成器。

作者：lzhp529

v1.3.0 严格以最初制作的原始 1.0 六按钮版本为基础，只增加 OverlayFS 延迟兼容模式和字体检查容错。

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

勾选后，生成模块包含 `service.sh`。脚本会等待开机完成；如果检测到 `cler1818_full_system_overlayfs`，继续等待其日志出现“健康检查通过”，然后再把模块字体绑定到实际系统字体目标，解决 OverlayFS 晚挂载后小米笔记等应用恢复默认字体的问题。

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

v1.3.0 会改为中文提示：

- 检测到多字体集合时，使用第一个字体读取显示名称和基本信息。
- 生成模块时保留完整原始字体文件，不拆分、不修改。
- 即使详细检查完全失败，也允许继续生成、复制、安装或安装并重启。
- 检查失败不代表文件一定损坏，但最终能否显示由 Android 字体加载器决定。

## 使用方法

### 便携 EXE 版

1. 完整解压 `Xiaomi13Font-Portable-v1.3.0.zip`。
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
./build.ps1 -Version 1.3.0
```

生成：

- `artifacts/Xiaomi13Font-Portable-v1.3.0.zip`
- `artifacts/Xiaomi13Font-Script-v1.3.0.zip`
