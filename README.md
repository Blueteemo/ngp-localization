# NGP 汉化实践与工具

**把实际做过的 Neo Geo Pocket／Color 汉化工程，整理成别人和 Agent 可以接手的资料与工具。**

当前可运行案例是《秋之回忆 Pure》的 **P05 菜单及开场汉化定稿**，提供生成源码、
固定字体依赖、重建校验、模拟器验证和有声录制入口。《无限轮回：Cure.》目前作为经验案例整理。

NGP 在仓库名中是平台系列统称。目前两款实际案例均为 **NGPC**，不宣称已适配所有 NGP／NGPC 游戏。

> **给 Agent：先读 [AGENTS.md](AGENTS.md)，再读 [Pure 接手入口](projects/pure/README.md)。**
> 本仓库首版建设不等于陌生 Agent 接手验收通过；该验收尚未开展。

## 当前能做什么

| 内容 | 当前状态 |
| --- | --- |
| 从自备日版 ROM 生成 Pure P05 | 已迁移源码并确认输出 SHA-256 与冻结版本相同 |
| 字形位图编解码、受保护补丁重建 | 有可运行工具及不依赖 ROM 的测试 |
| 菜单、存读档、署名切换及开场检查 | 提供双核心适配脚本及历史观测记录 |
| 实际游戏画面与声音录制 | 提供 Beetle 录制入口；游戏画面不作为公开仓库素材提交 |
| Pure 全剧情汉化 | **未开始**；只有正文规模的初步估算，尚无完整日文字表和 Unicode 剧本导出 |
| Cure 完整工程重建 | 本首版未迁入；目前提供案例说明和方法总结 |

## 快速开始

需要 Python 3.11+。原版 ROM 请自行提供，仓库不会查找或下载替代版本。

```bash
python -m venv .venv
# 在你的终端激活 .venv 后：
python -m pip install -e ".[pure]"
python -m ngp_localization doctor --rom "/path/to/Memories Off - Pure (Japan).ngc"
python projects/pure/manage.py fonts
python projects/pure/manage.py build --rom "/path/to/Memories Off - Pure (Japan).ngc"
```

输出默认在被 Git 忽略的 `projects/pure/private/p05/`，应得到：

- `Pure_P05.ngc`：可直接启动的 ROM。
- `P05_patch.json`：**从你自己的 ROM 本地生成**的带校验补丁清单，不提交到 Git。

预期 ROM SHA-256：

```text
d2b50428d6ae56477178bdbfd99fb1a5cb128c8f38da4463d1ddfb433a22aa13
```

仅重建 P05 不需要 Node.js、MCP 服务或模拟器。运行验证时，按
[环境说明](docs/environment.md) 接入已有核心；不要为了 MCP 重新搭建已有环境。

## 阅读路线

- [Pure 工程与运行命令](projects/pure/README.md)
- [Pure 已确认的文本、字库及资源格式](projects/pure/format.md)
- [Pure 当前状态与下一步](projects/pure/next-steps.md)
- [环境和依赖](docs/environment.md)
- [汉化工作流程](docs/workflow.md)
- [真实问题与修正](docs/pitfalls.md)
- [验证与有声录制](docs/validation.md)
- [Cure 案例](projects/cure/README.md)

## 工具自检

```bash
python -m unittest discover -s tests -v
python tools/check_public_tree.py
```

CI 不需要商业 ROM，也不会运行游戏。它只检查公开工具、语法及公开文件边界。
实际游戏检查结果需要明确记录 ROM 哈希、核心版本、输入序列与截图。

## 发布内容与许可

自有代码和说明采用 MIT。字体及字形子集保留 OFL 与原组件许可，见 [NOTICE.md](NOTICE.md)。
不包含商业 ROM、原版资源、完整剧情、真实 BIOS、玩家存档、个人云盘链接或环境凭据。

制作署名：**千岚之夏** · GitHub：**Blueteemo**
