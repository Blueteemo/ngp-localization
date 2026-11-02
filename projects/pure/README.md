# 《秋之回忆 Pure》接手入口

## 当前状态

**截至 2026-11-02，云盘最新菜单及开场汉化定稿为 P06（2026-10-27），正文剧情仍为日文。**
包括四项标题菜单、设置和相关提示、存读档及初始化提示、附加内容标签、开场叙述与人物介绍、
图像状态卡和主菜单署名。保留原 LOGO、版权信息及 BGM 原曲名。

P06 修正了存读档确认界面“是／否”的行位，保留 P05 的主菜单署名时机等行为。
P06 适配器已同步；结合用户本地提示配置，从日版原件构建的哈希与定稿一致。对外统一使用 P06；内部保留 P05 派生依赖及历史回归入口。
固定字模与预留容量由 P05 源码现场派生，不在公开树提交从 ROM 抽取的字模或补丁清单。

正文工具读取外部私有输入，提供受控 FE 小样、显式记录扩容与存档几何校验。
仓库不附带全文汉化数据或私人译文进度。见 [工程案例与接口](story-progress.md) 和 [验收检查表](next-steps.md)。

这是可重建的工程源码，不包含 ROM；也不是“已完成全文汉化”的项目。

| 项目 | 值 |
| --- | --- |
| 日版文件 | Memories Off - Pure (Japan).ngc |
| 大小 | 1,048,576 字节 |
| CRC32 | 7F919DDE |
| 日版 SHA-256 | `5e304f68ca29fff2def6c5f4209224871156b9502f041d69129d025f0245428d` |
| P06 SHA-256 | `12ac7406dbb255e20c682fa11c001ffa37cc626830f3b0310e2bb02554995fa7` |
| 状态明细 | [state.json](state.json) |
| 格式与地址 | [format.md](format.md) |
| 后续入口 | [next-steps.md](next-steps.md) |

## 重建 P06

在仓库根目录：

```bash
python -m pip install -e ".[pure]"
python projects/pure/manage.py fonts
python projects/pure/manage.py build --rom "/path/to/Memories Off - Pure (Japan).ngc" --text-config /path/to/private-p06-text.json
python -m ngp_localization hash projects/pure/private/p06/Pure_P06.ngc
```

P06 的 `--text-config` 为私有输入；结构使用自造示例说明，见 [工程案例](story-progress.md)。
省略版本默认 P06；`--text-config` 仍为必填私有输入。`--version p05` 仅保留作历史回归，不要求另存一套成品。

字体如果已有，可用 `fonts --from-dir /path/to/fonts` 导入并检查锁定哈希。
不要把原 ROM 放到公共目录后依靠 `.gitignore` 碰运气；建议一直留在仓库外或 `private/`。

修改字体、构建参数或译文后，若哈希不同，它就是新实验，不是冻结 P06。
需要继续正文时先复制适配器并设新输出；不要删除固定版本的结果断言来让新输出冒充 P06。

## 验证入口

P06 的跨进程保存、取消、读回与覆盖验证：

```bash
python projects/pure/manage.py interactions --beetle-core /path/to/mednafen_ngp_libretro.so
```

默认读取 `private/p06/Pure_P06.ngc`，证据写入新的 `private/p06/evidence/p06-interactions/`。
每个独立进程默认最多运行 300 秒，可通过有限正值 `PURE_STAGE_TIMEOUT` 调整；超时或失败会停止
后续阶段并保存 `failure.json`，不能当作成功。不会自动清除已有测试存档或证据目录。

历史 `validate`、`menus`、`persistence`、`signature`、`transition`、`record` 仍保留原 P05 路径和时序
用于回归，不自动等同 P06 验收。其环境要求见 [环境说明](../../docs/environment.md)，旧命令及证据可查 Git 历史。
Native 黑底开场叙述存在已知显示失败；路径与存读档通过不能掩盖它。录制需要 FFmpeg，视频和截图只留本地。

## 正文规模估算

```bash
python projects/pure/manage.py estimate --rom "/path/to/Memories Off - Pure (Japan).ngc"
```

历史初步结果约 5,852 条对话候选，107,803 个显示 glyph token。
**这不是已导出的日文全文**，也不是翻译进度；包含重复、人名、空格和标点，尚未完成可达性分析。

## 文件职责

- `assets/translations_p05.json`：顺序固定的 P05 译文、排版和开场等待补偿。
- `assets/menu_glyphs.json`：十个 OFL 菜单字形子集。
- `assets/fonts.lock.json`：固定外部字体与哈希。
- `scripts/build_p06.py`：默认冻结入口；`build_p05.py` 保留内部派生 / 历史回归，均调用 `build_source.py`。
- `scripts/build_story_sample.py`：读取本地文本的单条 FE 实验，不内置游戏对白、不覆盖 P06。
- `scripts/interactions.py`：保存、取消、跨进程读取、覆盖后再读取。
- `scripts/glyph_atlas.py`、`ocr_candidates.py`：本地字模核对与未验收 OCR 候选。
- `scripts/build_title_p05.py`：原红圈 A、12px 中文提示、双层资源图块。
- `scripts/build_status_art.py`：仅替换三张原图像卡的文字区域。
- `scripts/build_signature_p05.py`：深灰署名字形的实际绘制例程。
- `scripts/environment.py`：统一路径入口。
- `reference/`：原版时点及历史验证摘要，不含 ROM 字节或截图。

完整生成后，本地补丁清单也能独立重建：

```bash
python -m ngp_localization apply --rom "/path/to/original.ngc" --manifest projects/pure/private/p06/P06_patch.json --out /path/to/rebuilt.ngc
```

构建与重建都会校验基线和输出；不允许覆盖原件。
