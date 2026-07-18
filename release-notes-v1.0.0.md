# Xiaomi13Font v1.0.0

首个公开版本，作者 lzhp529。

## 下载文件

- `Xiaomi13Font-Portable-v1.0.0.zip`：完整便携文件夹版，解压后运行 `Xiaomi13Font.exe`。
- `Xiaomi13Font-Script-v1.0.0.zip`：CMD + PowerShell 脚本版，解压后运行 `Xiaomi13Font.cmd`。

## 主要功能

- 选择本地 TTF/OTF 字体并生成 Magisk 全局字体模块。
- 所有模块固定使用 `xiaomi13_fuxi_global_font` ID，新字体会更新旧字体。
- 覆盖 MIUI、MiType、Roboto、Serif、等宽字体和小米时钟字体。
- 保留当前 Android 14 原生 `fonts.xml`。
- 支持生成、复制到手机和直接调用 Magisk 安装。
- 直接安装绕过 MiXplorer Content URI，解决 `Invalid Uri`。
- 不会自动重启手机。

## 已验证设备

- Xiaomi 13 / 2211133C / fuxi
- MIUI 14.0.5.0.UMCCNXM
- Android 14 / API 34
- Magisk Alpha e8a58776-alpha / 30700

本 Release 不包含任何第三方字体文件。请确保你有权使用所选择的字体。
