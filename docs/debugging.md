# 动态调试入口

先用实际画面确定目标字段，再追踪读取和绘制。Pure 已确认的核心地址见项目 format 文档。

NgpCraft MCP 通过固定上游 checkout 使用；连接器是否已注册要实际检查。
可优先查看这些工具的**当前输入 schema 和实现**，再调用，不能从旧说明猜参数：

| 工具 | 用途 |
| --- | --- |
| `ngpc_emu_native_run` | 加载用户自备 ROM/状态，运行、按键与截图 |
| `ngpc_emu_memory_dump` | 读取相关 RAM/VRAM，确认文本指针、字形缓冲与显示状态 |
| `ngpc_emu_trace_exec` | 围绕已定位入口记录指令与调用路径 |
| `ngpc_emu_watchpoint` | 查指定地址的读取/写入来源，先确认对应核心的实现限制 |
| `ngpc_emu_tilemap_info` | 检查两层 tilemap，避免遗漏覆盖层 |
| `ngpc_emu_tiles_view` | 查看字体/图像 tiles |
| `ngpc_emu_palette_info` | 解释颜色、透明索引和调色板复用 |
| `ngpc_disasm` | 对选定地址段反汇编，验证钩子与跳转编码 |

没有接入 MCP 也可以使用项目中的直接核心适配器与上游 CLI。
固定版本的工具注册表位于上游 `src/tools/index.js`；文档修复 PR 不会自动增加工具功能。

一个有效的调查记录应包括：输入 ROM 哈希、目标画面、相关地址、观察到的读写、
提出的假设、最小修改及前后运行证据。不要只留下“扫描到某种重复字节”的结论。
