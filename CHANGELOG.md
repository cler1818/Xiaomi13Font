# Changelog

## 1.3.0 - 2026-07-19

- 改回真正的原始 1.0 六按钮程序架构。
- 恢复“安装并重启手机”“检测手机”“一键重启手机”“打开目录”等完整功能。
- 恢复固定模块 ID `fuxi_a14_inugami_momo_global_font` 和主字体名 `GlobalFont.ttf`。
- 新增可勾选、可取消的 OverlayFS 延迟兼容模式，默认开启。
- 多字体集合改为中文提示，并保留完整原文件继续制作模块。
- 字体详细检查失败时不再阻止生成、复制、安装或重启。
- CMD 版保留原始六项菜单，并支持 `-DisableOverlayCompat`。

## 1.2.0 - 2026-07-19

- 完整恢复并保留 v1.0.0 的图形界面、按钮布局、字体检查、生成和直接安装流程。
- 不在界面增加 OverlayFS 设置项，避免改变原有使用方式。
- 仅在生成的 Magisk 模块内部自动加入 `service.sh` 延迟兼容脚本。
- 保留 OverlayFS 健康检查等待、真实目标解析、去重绑定和运行日志功能。
- 重新验证便携 EXE、CMD 生成和 ADB/Magisk 直接安装流程。

## 1.1.0 - 2026-07-19

- 新增“OverlayFS 延迟兼容模式”，GUI 默认开启，CMD/PowerShell 版固定开启。
- 生成模块新增 `service.sh`，等待全系统 OverlayFS 健康检查完成后重新绑定字体。
- 对符号链接使用 `readlink -f` 解析真实目标，并自动去重。
- 同时处理 `/system/fonts`、`/product/fonts` 与 `/system/product/fonts` 字体入口。
- 新增模块内 `overlay-compat.log`，记录每个挂载目标及统计结果。
- 未安装或已禁用 OverlayFS 时自动使用普通延迟绑定。
- 修复全系统 OverlayFS 晚挂载后，小米笔记等应用重新加载时恢复默认字体的问题。

## 1.0.0 - 2026-07-18

- 首次公开版本。
- 提供完整便携 GUI 版与 CMD/PowerShell 脚本版。
- 支持 TTF/OTF 字体生成 Magisk 模块。
- 固定使用统一模块 ID，支持新字体替换旧字体。
- 支持 41 个系统字体入口与 6 个小米时钟字体入口。
- 保留 Android 14 原生 `fonts.xml`。
- 支持 ADB 复制与 Magisk 直接安装。
- 绕过 MiXplorer Content URI，解决 `Invalid Uri`。
- 增加设备检查、ZIP 路径检查和基础字体覆盖检查。
