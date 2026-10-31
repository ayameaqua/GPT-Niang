# 龙娘模型工作区

这是现有 Qt 程序的第一轮可动模型实现，**尚未完成计划中的模型 V1**。不依赖 Cubism 或 Coopanion 宿主，不执行外部 JavaScript。

**2026-10-31 已完成两轮修复。** 首轮重做正面/右前侧头与短前摆、清理完整裁片并逐视角标定关节；第二轮补充分段肘腕、后侧专用四肢、后发遮挡和回眸服装。见[首轮记录](../../docs/model-review/FIXES.md)与[细节修复](../../docs/model-review/DETAIL-FIXES.md)。八方向继续保留试验标记，接口数量不等于完整视觉验收。

- 原包左前侧：30 个分片、19 种表情、全部 18 个基线动作；坐下、睡觉保留持续姿态。
- 新增：左右歪头、左右抬手、双手举起、指向锚点、回眸、拎起保持、放下、画布内抛落、摸头和戳一戳。招手、抬手、指向与跳舞先转正面，使用上臂、前臂袖片、手掌三段关节；招手主要摆腕，指尖随腕点重新瞄准锚点。
- 八视角均已接入：正面、左右前侧、左右侧面、左右后侧、背面。原包左前侧为主要基底，其余七个方向为试验绑定，独立补图，不翻转整只角色冒充背面。
- 前侧及侧面使用 Qt 独立绘制眨眼、视线与说话口型。背面表情请求转向前侧；坐下/睡觉先转到原包姿态。转身逐步经过中间视角，转圈经过八方向并回到起始方向。
- 部分翼/尾等附属部件在相邻视角复用。后侧臂腿改用专用的近/远侧分片，对侧仅逐肢镜像；后裙改为连续后摆，保留颈后小结。后发保持长发体积，肩部在发下，近侧前臂末端在发前；回眸只换侧面头组。
- 继续完善：八方向衣褶/饰物的细微一致性与所有表情/动作组合的逐帧视觉验收。现有分段关节是 Qt 栅格分片实现，仍不标记完整 V1 验收通过。
- 本轮没有实现对话输入/生成服务或自行车。额度气泡沿用现有功能。

![八视角模型原型](preview-contact.png)

## 使用

先运行 `./linux/setup.sh`。从[固定 v1.1.0 发布页](https://github.com/zhengjihuaren/coopanion-gpt-dragon/releases/tag/v1.1.0)下载 `gpt-dragon-v1.1.0.zip`，然后在仓库根目录运行：

```bash
./linux/run.sh --import-model /absolute/path/gpt-dragon-v1.1.0.zip
./linux/run.sh --model-preview
./linux/run.sh --model-preview --model-view front
```

导入后需重启已运行的桌宠。重新导入会检查受管目录；发现资源被改动时，先保留 `.backup-时间戳` 目录再修复。导入命令检查固定 SHA-256，将 PNG、JSON 和原包 README 保存至 `$XDG_DATA_HOME/gpt-niang/models/coopanion-dragon-1.1.0`（默认 `~/.local/share`）。它不会安装、导入或执行 `figure.js`。未导入、资源损坏或设置关闭模型时，主窗口使用原静态角色。运行中的新版本可通过 `--model-preview` 打开动作面板。

右键角色也可打开模型预览。面板提供逐项表情/动作、朝向、暂停、0.1–2 倍速、复位、连接点、口型和倾听开关。预览不自动查询账户。关闭预览后桌宠继续运行；右键菜单或设置可退出。主窗口保留原生拖动，拖动触发拎起/放下表现；普通点击显示额度，双击触发摸头表现。长时间原生拖动受原有 1.5 秒 release 看门狗限制，当前无法从普通 Wayland 客户端确认完整的全桌面拖动/抛掷状态。

## 实现与资源

`gpt_niang_linux/model/` 包含独立的确定性动作状态机、QPainter 层级合成、连续纹理变形和 QML 接口。头部与身体有独立枢轴；呼吸、表情、视线、手势、口型和持续坐姿分别计算，不修改角色累计尺寸。纹理按实际 DPR 绘制并限制到源设计画布的分辨率，输入区取同一帧 alpha 的逻辑坐标区域，避免 GPU 回读和过期的静态 mask。纹理变形缓存有上限。

`source/` 是内置 ImageGen 生成的设定图/拆件制作文件。原始拆件图中不适用的躯干单元不使用；背面躯干以单独重绘的 `back-dress.png` 为准。透明图片查看器确会误显低 alpha 像素，但专项审查同时确认了多处 alpha≥128 的真实串格碎片，灰底合成仍可见，且会改变部件外接框和缩放。应逐片核对源图、抗锯齿与合法分离装饰；不能把所有碎片归为查看噪点，也不能全局阈值化透明通道来掩盖它们。

各视角子目录保存提取的 PNG 与 JSON 绑定；`views.json` 标记其试验状态。`source-selections.json` 记录主体选区，`rig-layouts.json` 记录每个方向的尺寸/枢轴/源内UV，不再套用通用格框或自动肤色关节。部分原始臂腿通过 `sourcePart` 在本机引用。以下命令重现裁片和绑定；工程脚本只处理现有纹理与几何：

```bash
QT_QPA_PLATFORM=offscreen ./linux/.venv/bin/python linux/tools/assemble_dragon.py
QT_QPA_PLATFORM=offscreen PYTHONPATH=linux ./linux/.venv/bin/python linux/tools/model_preview.py --out linux/test-results/model --frames --audit
```

第二条命令生成逐起始方向的动作接触表、可见脸方向的表情表、300帧渲染采样和演示帧。采样不代表长时间性能或逐帧美术验收。缺少方向时转身/转圈禁用；缺少专用掌部资源时，对应手势禁用。

来源及适用限制见 [NOTICE.md](NOTICE.md)，完整生成提示词见 [PROMPTS.md](PROMPTS.md)，实现状态见 [progress.json](progress.json)。完整目标仍以 [实施计划](../../docs/COOPANION-DRAGON-PLAN.md)为准。
