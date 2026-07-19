# Xiaomi13Font v1.2.0

本版本以 v1.0.0 为基准，完整保留原来的界面、按钮布局、字体检查、生成方式和直接安装流程。

唯一功能性增加位于生成的 Magisk 模块内部：

- 自动加入 OverlayFS 延迟兼容脚本 `service.sh`。
- 等待全系统 OverlayFS 健康检查完成后重新绑定字体。
- 自动解析和去重真实字体目标。
- 在模块目录记录 `overlay-compat.log`。
- 不在生成器界面增加新的复选框或设置项。
- 不自动重启手机。

已验证环境：小米 13（2211133C / fuxi）、MIUI 14.0.5.0.UMCCNXM、Android 14、Magisk Alpha 30700。

下载说明：

- `Xiaomi13Font-Portable-v1.2.0.zip`：完整便携文件夹版，界面与 v1.0.0 一致。
- `Xiaomi13Font-Script-v1.2.0.zip`：CMD/PowerShell 源码脚本版。

发布包不包含任何第三方字体。
