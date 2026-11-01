# 第三轮候选 3：前向、回眸与头部过渡复核

**结论：失败，不能作为视觉验收版本。** 回眸的整头 MLS 把角、耳、头壳拉成折叠网格；转身和旋转仍在混合两套完整人物轮廓。默认 320 像素渲染也能直接看出尖片状头部与多层重影。段间连续性及眼口表情中断确实改善，应独立保留这些修复。

本报告只对应冻结候选 3，不评价主上下文正在实施的拆层版本。审查期间未修改运行代码、模型素材或 rig。

## 1. 固定输入与检查方法

- 输入：`linux/test-results/review-pass-3/candidate-3/linux`；Python 使用仓库 `linux/.venv/bin/python`，`PYTHONPATH` 只指向冻结树。
- 首次采样：2026-11-01 12:09:02 +08:00；输入复核：12:27:44 +08:00。冻结实现、素材及诊断目录内原 Coopanion 副本共 217 个文件，SHA-256 与首次清单全部一致。
- [完整清单](../../test-results/review-pass-3/front-fix-3/snapshot.json)；`view_errors` 为空仅说明加载成功，不代表视觉合格。
- 原生 Qt 合成：1280 设计尺寸及 320 实际显示尺寸；先经 `QPainter` 合成至 RGB32 灰底 `#b8bec8` 再检查。因此本文重影、透明发丝、折叠均是合成结果，不是透明 PNG 查看器的低 alpha 噪点。
- Animator 以不超过 1/120 秒步长推进；静态时钟从 1 秒开始。另录制真实动作 30 fps 连续帧，共 262 帧：BL/BR 回眸各 91、正面转身 25、FR 旋转 55。判读依据是连续接触表和逐帧静图；同帧 MP4 也已导出供人工播放。

| 核心输入 | SHA-256 |
| --- | --- |
| `model/render.py` | `c80cf3d37865fe55205a796dcbd2e1f5872a51c1e33a42c6c4f505b49baebc8e` |
| `model/motion.py` | `690f4acf5df7bab5592cc030b3d9ed600a0e08f3d6645988a10b669ea48a8825` |
| `model/kinematics.py` | `30bd55c318d6fa0cffc71aeea56535d2623d4b5baea71b1a4807b78b7e637740` |

## 2. 逐项结论

| 项目 | 判定 | 实际结果 |
| --- | --- | --- |
| BL→L→FL 回眸 | **失败 P0** | 第一段中部头壳收成尖片，角耳穿插；第二段仍有多层脸、头发和角的透明轮廓。 |
| BR→R→FR 回眸 | **失败 P0** | 同类折叠和重影，第二段 R→FR 也有实际网格反转。 |
| 回眸段间位置 `position=1.0`、末端 `2.0` | 通过局部连续性 | 侧面交接附近没有候选 2 的硬切；不能据此判整条轨迹通过。 |
| 回眸身体、后发绘制次数 | 通过本项 | `rear-base` 只画一次；残余双头来自两套头图变形/混合。 |
| front 转身、FR 旋转 | **失败 P0** | 头、袖、裙、手、翼的双轮廓贯穿过渡；L↔BL 区间同时出现头壳塌缩。 |
| 后发旧水平硬裁边 | 通过旧缺陷消除；外观仍待修 | `.40` 起窗、`.40/.52` 渐隐消除旧硬横线；头变窄时仍显露半透明的上段发梢。 |
| 中途表情切换/取消，眼口及泪层 | 通过本次 3 组连续性 | `+0s` 与调用前完全同图，见下文 RGB 证据。 |
| angry/confused/thinking 情绪符号中断 | **失败 P2** | `♯/?/···` 在取消的零时刻直接消失，未跟随完整表情权重。 |
| 五脸向小幅 nod/shake、look/tilt 回归采样 | 保留候选 2 的有限结论 | 本轮重新采样；未见新增横缝、眼口脱离或大面积颈裂。小幅动作可用的结论不外推到大角度转头。 |
| 左右侧 19 稳态表情、说话与点头组合 | 本轮抽查未见回归 | 单眼 wink、右嘴位置、肤色遮罩及笑口保持有效；不包含上述符号中断与跨视角混合失败。 |
| 气泡指向与 QML 四尺寸 | 本轮不复测 | 沿用候选 2 已记录证据，未把其结论扩展到转身。 |

## 3. P0：回眸整头 MLS 折叠

证据：[BL 分段采样](../../test-results/review-pass-3/front-fix-3/priority-back-left.png)、[BR 分段采样](../../test-results/review-pass-3/front-fix-3/priority-back-right.png)、[BL 真实 30 fps 第一页](../../test-results/review-pass-3/front-fix-3/continuous-back-left-look-back-1.png)、[BL 视频](../../test-results/review-pass-3/front-fix-3/back-left-look-back.mp4)。`look_back=.25` 即第一段的 50%，不是段间边界。

冻结 `render.py:812–849` 在颈部对齐后，将所有共同可见的角、耳、呆毛、头顶及脸点交给同一个 `cage_mapper`。后侧与侧面中，同一解剖角的屏幕左右顺序会交换。例如 BL 的左右角根 x 约为 337/484，而 L 为 542/304；全局平面没有正确的遮挡换序方式。`kinematics.py:14` 的逐点加权 similarity 不保证整个场保向，也没有折叠保护。

排除 hidden 面部点是必要修复，但不足以解决可见角耳本身的拓扑换序。即使完全不使用脸点，BL→L 仍会让头壳随角根相交而反折。改变权重、增加网格密度或缩短混合时间都不能提供缺失的侧后脸形。

按实际 18×24 网格检查每个源图，以下计数只包含三角形中心源 alpha >32 的区域；每个源图总计 864 个三角形。面积比为有符号面积比，负数就是局部反转。

| 过渡 50% | 源图 | 有色区域反转三角形 | 有色区域接近塌缩三角形 |
| --- | --- | ---: | ---: |
| BL→L | BL / L | 20 / 25 | 8 / 17 |
| L→FL | L / FL | 3 / 1 | 3 / 3 |
| BR→R | BR / R | 6 / 15 | 8 / 2 |
| R→FR | R / FR | 12 / 6 | 2 / 1 |

[完整几何诊断](../../test-results/review-pass-3/front-fix-3/mesh-fold-metrics.json)。这解释实际图像的折纸现象；反过来，即使反转数降为零，也不能替代视觉验收。

**最低修法：** 停止整头网格跨越角耳遮挡换序。头壳只用不换序的头顶、颈、可见下巴/侧轮廓点作小范围形变；左右角、左右耳、饰物各自保留身份与局部刚性，按朝向切换远近层。隐藏下巴或眼点不能投到后脑纹理。后脑到侧脸缺少真实中间轮廓，需补 112.5°/247.5°；侧脸到前侧补 67.5°/292.5°。完整拆角需要无角头壳补全，详见第 7 节。

## 4. P0：转身、旋转仍在混合两个人物轮廓

证据：[front 实际转身连续帧](../../test-results/review-pass-3/front-fix-3/continuous-front-turn-1.png)、[FR 实际旋转连续帧](../../test-results/review-pass-3/front-fix-3/continuous-front-right-spin-1.png)、[front→FL 中间三帧](../../test-results/review-pass-3/front-fix-3/priority-turn-front.png)、[FL→L](../../test-results/review-pass-3/front-fix-3/priority-turn-front-left.png)。

冻结 `render.py:498–513` 仍先渲染两个完整人物，再以 `_view_anchors` 的头、腰、肩、脚底和尾点进行整幅 24×32 网格变形，最后 `_mix`。Premultiplied alpha 修正了颜色运算，但两套不重合轮廓仍各带部分透明度：front→FL 已能看到双套发尾、裙摆、翼缘；FL→L 又出现两套脸平面。

**最低修法：** 身体也需按躯干、两臂、裙、两腿、翼尾分层；只显示一个当前解剖部件轮廓，以转轴、深度和遮挡完成转向。纹理过渡仅限已对齐且拓扑一致的局部区域；不能再把整帧淡入淡出当转身。肩/脚按屏幕 x 排序不能长期替代解剖左右身份。先修局部层与中间姿态，再检查每段 25%、50%、75% 及完整转动，不以端点正确结案。

## 5. 已改善的边界与仍残留的发根

`look_back` 在 `.499999/.5/.500001` 和 `.999999/1` 取样，保持其他姿态完全一致。两侧段间最大 RGB 通道差仅 2–3，末端最大 4；所有比较均无通道差大于 24 的像素。说明 `position=1.0` 交接的零阶连续性成立。见[边界接触表](../../test-results/review-pass-3/front-fix-3/segment-boundaries.png)及[数值](../../test-results/review-pass-3/front-fix-3/boundary-metrics.json)。

后发扩窗渐隐消除了上一版硬平切线，且 `rear-base` 单次绘制避免身体重叠。不过侧面/前侧头比后侧冠片窄时，后发上端会露出淡淡的独立发梢。应让头根处有不透明的真实发层交叠，并用稳定的头壳/颈遮罩遮住属于被遮挡区域的源纹理；不要把渐隐范围继续加大直到发根透明。当前最强重影仍来自整头混合，须先移除该失败路径再判断是否还需发根补片。

## 6. 表情中断：主体修好，特效符号漏接权重

三组均在过渡途中中断：neutral→happy 后取消；happy→neutral 中途改 cry；happy→cry 后取消。保持时钟不推进，调用前与 `+0s` 全图 RGB 的平均差、最大差均为 **0**。`motion.py` 保存完整分布、`render.py:252` 遍历 `face_weights` 的修复有效。证据：[中断接触表](../../test-results/review-pass-3/front-fix-3/face-interrupted-transition.png)。

剩余问题来自 `render.py:799–810`：情绪符号按 `pose.expression` 单值选择。FL/right 在 neutral→angry/confused/thinking 的 80ms 取消，符号在零时刻消失。FL 三项分别有 348/223/111 个像素通道变化超过 24，最大差 137；right 为 218/147/75，最大差 72。眼口则保持当前混合状态。证据：[特效中断](../../test-results/review-pass-3/front-fix-3/accent-interrupted-transition.png)。

修法：原基底特效和扩展 `_head_accent` 都使用同一个 `face_weights` 分布，逐状态绘制对应特效并乘当前权重；确保只画一次、位置由当前头部变换决定。验收需同时检查符号切入、切出、中途取消和两种带符号表情互切，零时刻连续，结束时无残影。

重新生成的 [nod](../../test-results/review-pass-3/front-fix-3/action-nod.png)、[shake](../../test-results/review-pass-3/front-fix-3/action-shake.png)、[点头取消](../../test-results/review-pass-3/front-fix-3/cancel-nod.png)、[点头/表情/说话组合](../../test-results/review-pass-3/front-fix-3/nod-expression-combos.png)、[左侧 19 表情](../../test-results/review-pass-3/front-fix-3/expressions-full-head-left.png)、[右侧 19 表情](../../test-results/review-pass-3/front-fix-3/expressions-full-head-right.png)支持“先前小角度修复未明显回归”的有限结论。侧面仍是小幅转头，不是大范围自然换脸。

## 7. 8 向保守拆片与补图交付

机器可读建议：[head-partitions.json](../../test-results/review-pass-3/front-fix-3/head-partitions.json)。含 8 向、解剖左右身份、源文件/尺寸、模型坐标 polygon、实际源 PNG 像素 polygon、安全根切线、核心保留侧、8–10 模型像素重叠。left/right 的源像素已逆现有 `warpY`，不是直接按显示 bbox 线性换算。人工边界约有 3–6 模型像素不确定性，抽取前须看标注并保留墨线。

| 现有头 | 可直接做的工作 | 必须保留/补全 |
| --- | --- | --- |
| 原 FL | 复用原 `tex/horns.png` 两个角连通片，`tex/ear-near.png`、`tex/ear-far.png` 独立耳层 | 保留原头壳及饰物身份；不要先合并再从头图重裁。 |
| front、L、R、FR 烘焙头 | 先按安全线拆露出的角杆/角尖、耳尖，局部刚性验证 | 当前 polygon **不是完整角根切除许可**。整块与头皮交叠的角根留核心；完整转动需要干净无角头壳/颞部补图。 |
| back、BL、BR | 保留后脑冠片和长发身份，拆露出部分 | 后脑纹理不承担脸的显现；不要挤压后脑去填侧脸。隐藏耳不能从头发纹理硬裁。 |

标注图：`front-fix-3/partition-{front,left,right,front-right,back-left,back-right,back}-source.png`。红线为保守部件范围，绿线为根切线。**核心只去掉切线尖端一侧的对应露出部分，不得减去整个 polygon；根侧保持不透明，移动片在根侧重叠并向内羽化。** 大角根球仍烘焙在头壳，意味着保守拆片只能作局部验证，不能作为大角度转动最终素材。

| 新头朝向 | 主要参考 | 应画出的真实变化 |
| --- | --- | --- |
| 112.5°，BL 与 L 之间 | L 的脸/鼻/近眼/角身份 + BL 的后脑发根 | 从后侧刚露出的近侧脸轮廓；远眼仍隐藏，耳与角按真实遮挡。 |
| 67.5°，L 与 FL 之间 | L 侧脸 + 原 FL 分层素材 | 近眼形状向前侧变化，远眼仅初露；饰物不能跳边。 |
| 247.5°，BR 与 R 之间 | R 侧脸 + BR 后脑 | 右侧对应的刚露脸姿态；不可镜像后把饰物放错解剖侧。 |
| 292.5°，R 与 FR 之间 | R + 当前 FR 短前发/脸型 | 远眼初露，嘴/下巴随方向转，保留当前短前发身份。 |

最好一次交付干净头壳、两角、两耳、饰物/流苏、前后发层及五官定位；若只补整头扁平图，仍需要清理隐藏区域才能进行完整独立角耳运动。

## 8. 下一候选验收门槛

1. 同时检查 BL→L→FL、BR→R→FR 每段 0/25/50/75/100%，以及正反向完整 30 fps 轨迹；两侧在所有中间帧都应保持单个完整头壳。
2. 角、耳可因遮挡逐渐消失或出现，但不拉着脸/发顶翻折；不得出现多角、多耳、半透明的第二张脸。隐藏五官只通过真实新视角素材/遮罩出现。
3. 转身与旋转检查全身，裙/手/翼不能留下第二套透明轮廓；脚底与身体转轴保持合理连接。
4. 保留候选 3 通过的段间及眼口中断连续性，补齐情绪符号；单独检查动作结束、取消时的零时刻连续与恢复过程。
5. 同时以 320 与 1280 灰底合成检查；几何无反转、单元测试通过只是必要诊断，最终需中间帧轮廓、连接和动作含义都成立。

诊断代码、连续帧、MP4 与建议 JSON 全在 ignored 的 `linux/test-results/review-pass-3/front-fix-3/`。本报告是本次新增的唯一 tracked 文件。
