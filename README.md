# NGP／NGPC 研究与汉化技术实践

**从实际游戏工程出发，记录 Neo Geo Pocket／Color 的研究方法、汉化技术与可复现工具。**

这里整理动态调试、文本与字库分析、图块和调色板调查、文本重定位、界面与存档验证，
以及模拟器对照和有声录制的经验，供研究者和 Agent 在新项目中参考。

方法来自《秋之回忆 Pure》和《无限轮回：Cure.》的实际工程。目前两款案例均为 **NGPC**；
NGP 在仓库名中是平台系列统称。方法可供迁移参考，具体编码、地址、字体和资源格式仍需逐游戏确认。

## 从哪里开始

| 你的目标 | 阅读入口 |
| --- | --- |
| 研究另一款游戏 | [新项目研究路线](docs/research.md) → [工作流程](docs/workflow.md) → [动态调试](docs/debugging.md) |
| 查找遇到过的技术问题 | [实际问题、调查与可复用经验](docs/pitfalls.md) |
| 设计验证与录制方案 | [验证的层级与有声录制](docs/validation.md) |
| 重建或继续 Pure | [Pure 工程入口](projects/pure/README.md) → [已确认格式](projects/pure/format.md) → [状态与下一步](projects/pure/next-steps.md) |
| 了解 Cure 经验 | [Cure 案例](projects/cure/README.md) |
| 由 Agent 接手 | [AGENTS.md](AGENTS.md)，先按任务选择路线 |

## 技术内容与复用范围

| 内容 | 可以复用的部分 | 需要逐游戏确认的部分 |
| --- | --- | --- |
| 动态调试 | 从画面追踪文本读取、绘制、字形和显存写入的方法 | 地址、调用约定、脚本状态与断点 |
| 文本与字库 | 分离文本和控制码、字形去重、最小修改与对照验证 | 编码、控制码、字形尺寸和位排列 |
| 图块与调色板 | 检查多图层、透明色、资源冲突和可见墨迹边界 | 图块分配、调色板占用和场景生命周期 |
| 补丁重建 | `ngp_localization/patch.py` 的基线哈希、原字节保护和输出哈希检查 | 补丁位置与内容；该工具仅支持等长写入 |
| 字形编解码 | `ngp_localization/glyph12.py` 的已验证实现可作格式分析案例 | 它是 Pure 的 12×12、18 字节格式，不是平台通用字库格式 |
| 验证与录制 | 分层取证、跨进程存档、双核心对照、帧数与 PCM 样本核对 | 输入序列、断言、核心接口和时间基 |

项目脚本保留在 `projects/<game>/`。已有工具和案例可运行，不代表新游戏可直接套用，
也不代表已经具备自动识别文本、通用解包或一键汉化能力。

## 实战案例

| 案例 | 已有成果 | 当前公开工程范围 |
| --- | --- | --- |
| [秋之回忆 Pure](projects/pure/README.md) | P05 菜单及开场汉化定稿 | 生成源码、固定字体依赖、重建校验、双核心验证及 Beetle 有声录制入口 |
| [无限轮回：Cure.](projects/cure/README.md) | 简体中文汉化定稿与正文重定位经验 | 案例说明和方法总结；完整重建工程尚未迁入 |

Pure P05 迁移后的输出 SHA-256 已确认与冻结版本相同。Pure 全剧情汉化尚未开始，
完整日文字表与 Unicode 剧本导出尚未建立。陌生 Agent 独立接手验收尚未开展。
各项历史验证的覆盖范围和已知失败见项目记录，不能由构建成功推断全剧情通过。

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
