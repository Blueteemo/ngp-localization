# 来源与许可

自有工具、工程说明和项目适配代码采用根目录 MIT 许可，署名 Blueteemo / 千岚之夏。

## 字体

Fusion Pixel Font 2026.10.16，作者 TakWolf，SIL Open Font License 1.1。
下载地址、压缩包和所用 OTF 的 SHA-256 在 `projects/pure/assets/fonts.lock.json`。
本仓库不提交字体二进制。完整授权及上游组件授权在 `LICENSES/`。

`projects/pure/assets/menu_glyphs.json` 是沿用《Cure.》工程的十个 Fusion
12px 字形的位图子集，带项目像素调整及历史上移处理；仍按 OFL 分发，不改为 MIT。
Pure 构建时统一下移一行，与其他字形基线一致。该 JSON 不含商业 ROM 原字形、
原始补丁 before 字节、个人资料库标识或私有链接。

## 外部工具

- [NgpCraft MCP](https://github.com/Tixul/NgpCraft_MCP)：使用固定提交
  `256e26bfb4a1b11d8e1acc79491a2af3adb93537` 的 emulator 子目录。
  不复制其源码或 HLE BIOS；使用时保留其 MIT 等原有许可。
- [Beetle NGP](https://github.com/libretro/beetle-ngp-libretro)：用于另一核心验证及录制。
  不复制核心源码或二进制；按原项目 GPL 许可自行构建。
- Pillow、NumPy、FFmpeg：由使用者安装，许可归各自项目。

游戏标题仅用于标识案例。商业 ROM、原版游戏资源、完整剧本、BIOS 转储、玩家存档
均不包含在仓库中。原游戏数据由运行脚本在用户自备 ROM 中读取。
