# 正文重定位：工程案例与复现边界

这里分享格式研究、工具接口、失败案例与验证方法，不保存日文剧本、汉化正文或私人项目进度。
原文、译文、字表、ROM、BIOS、字模图、运行截图、存档和补丁清单都由使用者本地提供或生成。
历史 P05 资源是仓库原有内容；本次工具扩展不追加新的游戏文本或资源包。

## 冻结构建与私有输入

默认构建入口为 P06；P05 仅保留内部派生依赖与历史回归。
P06 输出 SHA-256：`12ac7406dbb255e20c682fa11c001ffa37cc626830f3b0310e2bb02554995fa7`。
P06 先从源码派生 P05 的字模槽位 / 字段容量，再读取私有提示配置生成；不在 Git 中存 ROM 提取结果。

```bash
python projects/pure/manage.py build --rom /path/to/original.ngc \
  --text-config /path/to/private-p06-text.json
```

配置结构示例**全部是自造文本**，不能用它冒充冻结版本的真实配置：

```json
{"field_suffixes":{"0x91958":"甲\n乙","0x91b2d":"丙\n丁"}}
```

真实配置留在本地；输出仍须匹配冻结哈希。外置配置前后已实际重建，P05 / P06 哈希不变。
命令不修改原件；自定义翻译属于另一个实验，不应删除冻结校验来冒充 P06。
构建使用新的输出目录或空目录；已有完整且逐字节相同的产物可幂等复验，内容变化必须使用新目录，
不覆盖旧构建或存档。发布使用 POSIX 目录句柄与 no-follow 检查；当前验证环境为 Linux，不据此宣称 macOS 已验收。

## 可逆导出与单条实验

```bash
python -m ngp_localization.textmap --rom /path/to/original.ngc \
  --mapping /path/to/private-mapping.json --offset 0x93377 \
  --out /path/to/new-private-record.json
python projects/pure/manage.py story-sample --rom /path/to/Pure_P06.ngc \
  --text-file /path/to/private-sample.txt --out /path/to/new-private-output
```

小样工具不内置游戏对白，UTF-8 文本由 `--text-file` 提供；换行按文件原样读取，字形必须存在于本地
P06 槽位表。单元测试只用自造的甲乙丙和虚拟槽位。实验保留 FE 入场语义，结束后回到原下一记录。
输出采用独立 ROM / 存档，不能混用原版或 P06 玩家存档。可通过 `PURE_EXPECTED_SAMPLE_SHA`
额外校验调用者已确认的本地小样哈希。

原记录的字节回编相同，不足以证明字符映射或参数语义正确。此案例曾把可变长操作数误当成字形：
文本控制的参数须由 `0x200B65` 读取器规则确定长度，不能一律假设一个字节；详见 [format.md](format.md)。
当前解析器保留原始操作数字节，不静态猜测 RAM 值，未知控制 / 截断立即失败。
OCR 只产生未验收候选，不自动生成“已确认”字表。字形应结合本地位图和多个上下文核对。

## 扩容不能只补零：Flash 几何案例

`build_story.py` 接收私有 inventory、译文 JSON、显式 selection 和必填 `--input-set`；不会自动下载、附带或公开游戏数据。
输入集清单恰含 `inventory`、`translations`、`selection` 三个键，值为对应文件原始字节的 SHA-256。
生产者先完成并发布三份文件，再发布同一版本的清单；消费者按清单验证一次读取的字节快照，拒绝混合版本。
不要在消费者发现不匹配时直接重算清单掩盖生产端竞态。

```bash
python projects/pure/scripts/build_story.py --rom /path/to/Pure_P06.ngc \
  --inventory /path/to/private-inventory.json --translations /path/to/private-translations.json \
  --selection /path/to/private-selection.json --input-set /path/to/private-input-set.json \
  --out /path/to/new-private-build
```

它核对原记录字节、FD / FE 标记、控制码与换行的完整相对顺序、行宽、缺字及保留区。
普通行上限 12 字；定位式对白按原控制段长度约束。超长 `8B` 行仅允许与已映射源文本一致的 ASCII / 括号段，
不能凭含有 `8B` 就放行任意中文长行；其他窄字距设计仍需专门视觉验收。
正文放在文件 `0x100000..0x170000`，新字库从 `0x180000` 开始，字体钩子按文本地址选择字库。

原 8 Mbit 游戏使用擦除块 16 / 17。ROM 扩到 16 Mbit 后，同一块号对应两个普通 64 KiB 块，恰好
覆盖新正文；一个核心的小样成功并未揭露问题，真实 BIOS 的初始化会把正文擦成 FF，导致解释器卡住。
必须同步迁移保存 / 读取地址与擦除块号，而不是把正文再挪开来掩盖存档损坏。

本适配器逐点验证 21 个地址操作数与 4 个擦除常量，再迁到块 32 / 33；最终 `0x1F0000..0x200000`
作为独立存档区初始化为 FF。原通用容量表不改。地址清单 / 新编机器码是游戏特有的工程实现，
不是可直接套给另一游戏的默认值，也不是 ROM / 字库素材包。

## 验收方法与限制

- 本案例的冻结版本、小样及扩容样本分别保存输入 / 输出哈希；不能拿旧样本结果替代新构建验收。
- Beetle 与真实 BIOS / NgpCraft 分别执行独立 OS 进程的保存、读回、推进覆盖和再次读回。
  原生侧另比较代码 / 正文 / 字库未被 Flash 写坏，检查硬件违规计数。
- 即时存档只用于同一 ROM 的受控分支复现，不能当作游戏存档持久化证明；不同构建不可混载 state。
- 基线研究识别 55 个选择调用 / 122 个选项边；静态图和实际输入日志必须分开记账。
  本作还按日期奇偶及 BCD 秒值分支，回归应覆盖合法时钟场景，不修改剧情 RAM 假装到达。
- 记录执行覆盖、逐字视觉检查、语义校对和所有历史组合是不同结论；自动截图不等于人工看完。
- NgpCraft 的黑底正文不可见在原版也出现；推进 / Flash 验证通过不消除该显示问题。
  此案例没有 macOS 或实体 NGPC 验收证据。

公开树只收工具、合成测试、格式说明和可复核的工程结论；实际项目的译文进度与审校记录留在私有工程。
