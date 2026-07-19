# Xiaomi13Font v1.1.0

本版本加入“OverlayFS 延迟兼容模式”，用于解决全系统 OverlayFS 在 Magisk 字体模块之后挂载，导致小米笔记等应用稍后恢复默认字体的问题。

主要变化：

- GUI 新增“OverlayFS 延迟兼容模式”复选框，默认开启。
- CMD/PowerShell 脚本版默认生成兼容模块。
- OverlayFS 完成健康检查后，再对系统真实字体文件执行延迟绑定。
- 自动解析和去重符号链接目标。
- 在字体模块目录生成 `overlay-compat.log`。
- 不自动重启手机。

已验证环境：小米 13（2211133C / fuxi）、MIUI 14.0.5.0.UMCCNXM、Android 14、Magisk Alpha 30700。

下载说明：

- `Xiaomi13Font-Portable-v1.1.0.zip`：完整便携文件夹版，带图形界面和 ADB。
- `Xiaomi13Font-Script-v1.1.0.zip`：CMD/PowerShell 源码脚本版。

发布包不包含任何第三方字体。请自行选择具有合法使用权的 TTF/OTF 字体。
