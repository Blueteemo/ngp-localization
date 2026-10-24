# 环境：先复用，再补缺项

## 最小构建环境

Python 3.11+，Pillow 12.3.0。安装 Pure 可选依赖会同时安装 NumPy 2.3.5，供模拟器前端和录制使用。
这组版本来自实际工程环境；换版本后需重新核对 P05 输出，不能直接修改预期哈希。

```bash
python -m pip install -e ".[pure]"
python -m ngp_localization doctor
python projects/pure/manage.py fonts
```

`fonts` 使用固定上游发布，验证 ZIP 和 OTF 的 SHA-256。网络不可用时，可从已有字库目录导入：

```bash
python projects/pure/manage.py fonts --from-dir /path/to/existing-fonts
```

目录下需要 `fusion10/` 和 `fusion12/` 的 zh_hans OTF；也可直接把两份 OTF 放在该目录下。
字库锁定信息在 `projects/pure/assets/fonts.lock.json`，许可在 `LICENSES/`。

## 已有 NgpCraft 环境

优先复用已有 checkout，给 `--native-root` 指向包含 `core/native.py`、`cpp/` 和 `hle_bios/` 的目录。
本案例固定源码是 NgpCraft MCP 的提交：

```text
256e26bfb4a1b11d8e1acc79491a2af3adb93537
```

首次确实缺环境时：

```bash
git clone https://github.com/Tixul/NgpCraft_MCP .deps/NgpCraft_MCP
git -C .deps/NgpCraft_MCP checkout 256e26bfb4a1b11d8e1acc79491a2af3adb93537
cmake -S .deps/NgpCraft_MCP/vendor/emulator/cpp -B .deps/NgpCraft_MCP/vendor/emulator/cpp/build -DCMAKE_BUILD_TYPE=Release
cmake --build .deps/NgpCraft_MCP/vendor/emulator/cpp/build --parallel 2
```

适配器明确调用 `set_timing_silicon(10, 8)`，并逐帧排空音频。
使用固定项目随附的 HLE BIOS，不下载真实 BIOS。HLE 路径有已知显示差异，见验证文档。

如果要接 MCP，Node.js 最低 20，具体工具注册表以固定 checkout 的 `src/tools/index.js` 为准。
已提交的 README 文档修复不是模拟器功能更新。构建 P05 或直接调用核心无需运行 Node/MCP。

## 已有 Beetle/Mednafen 环境

给 `--beetle-core` 指向已有 libretro 核心。历史基线固定源码：

```text
a50d5ac288a81f2104ddf43195a4efdd15c72227
```

缺少时再按上游构建：

```bash
git clone https://github.com/libretro/beetle-ngp-libretro .deps/beetle-ngp-libretro
git -C .deps/beetle-ngp-libretro checkout a50d5ac288a81f2104ddf43195a4efdd15c72227
make -C .deps/beetle-ngp-libretro -j2
```

Linux 产物通常为 `mednafen_ngp_libretro.so`。其他平台请传入实际动态库路径，不把 Linux 路径当作跨平台保证。
本仓库的菜单、录制检查不依赖额外 bus-dump 导出；可选只读诊断补丁见 `tools/patch_beetle_dump.py`。

## 参数与环境变量

日常用 `manage.py --native-root /path --beetle-core /path`，无需记住环境变量。
已有自动化也可以使用：`PURE_OUTPUT`、`PURE_BASELINE`、`PURE_ROM`、`PURE_FONT_ROOT`、
`NGP_NATIVE_ROOT`、`NGP_BEETLE_CORE`。这些变量仅影响本地路径，不提交机器专属配置。

有声录制额外需要 PATH 中的 FFmpeg 和 ffprobe。依赖缺失应报告具体缺项，不能用一张正常截图宣称环境完整。
