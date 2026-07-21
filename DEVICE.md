# 设备适配与技术记录

## 基准设备

- 产品名称：Xiaomi 13
- 中国大陆型号：2211133C
- Android 设备代号：fuxi
- CPU ABI：arm64-v8a
- 系统版本：MIUI 14.0.5.0.UMCCNXM
- Android 版本：14
- Android API：34
- 构建标识：UKQ1.230705.002 release-keys
- 安全补丁：2023-10-01
- Root 管理器：Magisk Alpha
- Magisk 构建：e8a58776-alpha
- Magisk 版本码：30700

## 当前系统字体入口

基准系统的 `/system/etc/fonts.xml` 使用以下主要入口：

- 默认 `sans-serif`：`MiSansVF_Overlay.ttf`
- 简体/繁体中文前置字体：`Roboto-Regular.ttf`
- MIUI/MiPro 字体族：`MiSansVF_Overlay.ttf`
- MiType 字体族：`MitypeVF.ttf`
- MiType Mono：`MitypeMonoVF.ttf`
- MiuiEx：`MiuiEx-Regular.ttf`、`MiuiEx-Bold.ttf`、`MiuiEx-Light.ttf`
- 时钟：`MitypeClock.otf`、`MitypeClockMono.otf`

`/system/fonts/MiSansVF_Overlay.ttf` 在原系统中可能是指向 `/data/system/fonts/theme_webview/Roboto-Regular.ttf` 的链接，这是 MIUI 主题字体机制的一部分。

## 为什么不替换 fonts.xml

旧教程或旧字体模块通常携带完整 `/system/etc/fonts.xml`。不同 Android 版本的 XML 内容差异较大：

- 旧字体模块样本约 32 KB；
- MIUI 14 Android 13 教程附件约 78 KB；
- 本机 Android 14 当前配置约 81 KB。

直接覆盖可能丢失 Android 14 新增字体族、fallback 配置或 XML 属性。Xiaomi13Font 保留系统 XML，只覆盖 XML 已经引用的字体文件名。

## 一份字体、多链接方案

模块只保存一份真实字体：

```text
/system/fonts/GlobalFont.ttf
```

安装时使用相对符号链接覆盖多个系统字体名。优点：

- 避免把同一字体复制几十次；
- 模块体积更小；
- 所有覆盖入口保持一致；
- 更换字体时只需要更新一份真实字体；
- 同一个模块 ID 可以可靠替换旧版本。

## 兼容性边界

### 全系统 OverlayFS

本机安装的 `cler1818_full_system_overlayfs` 会在开机完成后较晚挂载 `/system`、`/product` 等 OverlayFS。普通 Magisk 字体模块的文件挂载发生得更早，因此可能先显示自定义字体，随后又被 OverlayFS 的系统快照遮住。应用已经缓存的字体还会暂时保留，造成“过一段时间、重新进入页面后恢复默认字体”的现象。

勾选 OverlayFS 延迟兼容模式后，模块根目录的 `service.sh` 会确认 OverlayFS 日志更新时间属于本次开机，同时确认 `/system`、`/product` 的实际 OverlayFS 挂载连续稳定，再对真实字体目标执行延迟 bind mount。符号链接经 `readlink -f` 解析并去重；每次绑定后校验 SHA-256，失败最多重试三轮。执行结果写入模块目录的 `overlay-compat.log`。取消勾选时不生成该脚本。

v1.3.0 的已知问题：`overlay.log` 保留旧启动记录时，脚本可能提前约几十秒执行，随后被 OverlayFS 再次遮住。v1.4.0 已通过本次开机日志时间、真实挂载状态和连续稳定检查修复。

该模式专门验证于：

- 小米 13 / fuxi
- MIUI 14.0.5.0.UMCCNXM / Android 14
- Magisk Alpha e8a58776-alpha / 30700
- `cler1818_full_system_overlayfs`

兼容脚本不会修改 OverlayFS 模块本身，也不会自动重启设备。

本工具安装脚本要求：

```text
ro.product.device=fuxi
ro.build.version.sdk>=34
```

目前没有承诺支持：

- HyperOS；
- Android 15 或更高版本；
- 小米 13 国际版不同系统分支；
- KernelSU/APatch；
- 非 fuxi 设备。

系统 OTA 后应先确认 `/system/etc/fonts.xml` 与字体路径是否仍然一致，再继续使用。
