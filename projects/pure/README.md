# 《秋之回忆 Pure》接手入口

## 当前状态

**P05 是菜单及开场汉化定稿，正文剧情仍为日文。**
包括四项标题菜单、设置和相关提示、存读档及初始化提示、附加内容标签、开场叙述与人物介绍、
图像状态卡和主菜单署名。保留原 LOGO、版权信息及 BGM 原曲名。

这是可重建的工程源码，不包含 ROM；也不是“已完成全文汉化”的项目。

| 项目 | 值 |
| --- | --- |
| 日版文件 | Memories Off - Pure (Japan).ngc |
| 大小 | 1,048,576 字节 |
| CRC32 | 7F919DDE |
| 日版 SHA-256 | `5e304f68ca29fff2def6c5f4209224871156b9502f041d69129d025f0245428d` |
| P05 SHA-256 | `d2b50428d6ae56477178bdbfd99fb1a5cb128c8f38da4463d1ddfb433a22aa13` |
| 状态明细 | [state.json](state.json) |
| 格式与地址 | [format.md](format.md) |
| 后续入口 | [next-steps.md](next-steps.md) |

## 先重建

在仓库根目录：

```bash
python -m pip install -e ".[pure]"
python projects/pure/manage.py fonts
python projects/pure/manage.py build --rom "/path/to/Memories Off - Pure (Japan).ngc"
python -m ngp_localization hash projects/pure/private/p05/Pure_P05.ngc
```

字体如果已有，可用 `fonts --from-dir /path/to/fonts` 导入并检查锁定哈希。
不要把原 ROM 放到公共目录后依靠 `.gitignore` 碰运气；建议一直留在仓库外或 `private/`。

修改字体、构建参数或译文后，若哈希不同，它就是新实验，不是冻结 P05。
需要继续正文时先复制适配器并设新输出；不要删除固定版本的结果断言来让新输出冒充 P05。

## 运行验证

先复用现有两个核心，路径见 [环境说明](../../docs/environment.md)。以下 `/path/to/...` 仅为占位符。

```bash
python projects/pure/manage.py validate --core med --beetle-core /path/to/mednafen_ngp_libretro.so
python projects/pure/manage.py validate --core native --native-root /path/to/NgpCraft_MCP/vendor/emulator
python projects/pure/manage.py menus --beetle-core /path/to/mednafen_ngp_libretro.so
python projects/pure/manage.py persistence --beetle-core /path/to/mednafen_ngp_libretro.so
python projects/pure/manage.py signature --native-root /path/to/NgpCraft_MCP/vendor/emulator
python projects/pure/manage.py transition --core med --beetle-core /path/to/mednafen_ngp_libretro.so
python projects/pure/manage.py transition --core native --native-root /path/to/NgpCraft_MCP/vendor/emulator
```

输出位于 `private/p05/evidence/`。`persistence` 必须在 `menus` 成功退出后运行，
它要读取上一进程实际创建的测试存档，不使用即时存档伪装持久化。

Native 的黑底开场叙述有已知显示失败，脚本会单独报告。路径与时序通过不意味着这个失败消失。
目前录制完整可见开场使用 Med；不是通过改 ROM 规避 Native 差异。

## 有声演示

先完成 Med `validate`，以生成实际标题参考图：

```bash
python projects/pure/manage.py record --beetle-core /path/to/mednafen_ngp_libretro.so
```

需要 FFmpeg。脚本实际从重置运行，播放完整一轮开场，检测标题后按 A，并在主菜单停留。
视频、原始音轨和采样/帧数记录只留在本地忽略目录。

## 正文规模估算

```bash
python projects/pure/manage.py estimate --rom "/path/to/Memories Off - Pure (Japan).ngc"
```

历史初步结果约 5,852 条对话候选，107,803 个显示 glyph token。
**这不是已导出的日文全文**，也不是翻译进度；包含重复、人名、空格和标点，尚未完成可达性分析。

## 文件职责

- `assets/translations_p05.json`：顺序固定的当前译文、排版和开场等待补偿。
- `assets/menu_glyphs.json`：十个 OFL 菜单字形子集。
- `assets/fonts.lock.json`：固定外部字体与哈希。
- `scripts/build_p05.py`：生成全部 P05 文本、字库与限定上下文的钩子。
- `scripts/build_title_p05.py`：原红圈 A、12px 中文提示、双层资源图块。
- `scripts/build_status_art.py`：仅替换三张原图像卡的文字区域。
- `scripts/build_signature_p05.py`：深灰署名字形的实际绘制例程。
- `scripts/environment.py`：统一路径入口。
- `reference/`：原版时点及历史验证摘要，不含 ROM 字节或截图。

完整生成后，本地补丁清单也能独立重建：

```bash
python -m ngp_localization apply --rom "/path/to/original.ngc" --manifest projects/pure/private/p05/P05_patch.json --out /path/to/rebuilt.ngc
```

构建与重建都会校验基线和输出；不允许覆盖原件。
