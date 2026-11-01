# 第三轮前向审查：候选 2 冻结复核

**候选 2 整体仍不通过。** 基础点头、摇头投影、嘴和眨眼、稳定表情取消、说话闭口间歇、气泡实际指向都有实质改善；本轮不再把候选 1 的硬折层、面部严重压缩、侧面 yaw 完全无效、网格横缝列作未修复问题。当前主要阻断是 **turn/spin 的整身关键帧跳变、look-back 的整头关键帧跳变及后发平切边暴露**。另确认表情过渡在中途再次取消/切换时仍会跳变。

本报告只描述候选 2。主上下文在收到反馈后进行的地标配准、后发渐变窗口和完整表情权重修复，尚未进入本冻结树，不能据此宣布本报告中的问题已通过。

## 输入、方法和覆盖

- 唯一实现输入：`linux/test-results/review-pass-3/candidate-2/linux/`。初始输入快照时间：**2026-11-01 11:36:11 +08:00**。
- Python：原仓库 `linux/.venv/bin/python`；`QT_QPA_PLATFORM=offscreen`、`PYTHONDONTWRITEBYTECODE=1`、`PYTHONPATH` 指向上述冻结 linux。运行时模块与扩展资源目录均有断言。
- 原 Coopanion 模型复制到诊断目录 `imported-model/` 固定使用；完整输入 SHA256 见 [snapshot.json](../../test-results/review-pass-3/front-fix-2/snapshot.json)。完成复核时再次核对，**0 项变化**。
- 所有图像使用实际 Qt 合成，在 RGB32 灰底上检查，避免透明查看器低 alpha 噪点混入判断。常规为 1280px，另直接渲染 320px 原生尺寸。模型坐标尚未加渲染偏移 `(150,220)`；每帧推进不超过 1/120 秒。
- 五个脸向各检查 nod / shake / look / tilt-left / tilt-right 的 11 个时间点及取消；左右侧面 19 表情的静默与最大 speech；稳定表情取消、表情过渡被打断、连续 speech；turn/spin 两个起始方向的每个关键帧边界；左右后侧回眸的进入、保持、退出边界。还加载冻结 `Main.qml`，实测四个尺寸的气泡坐标、自动显示与指尖射线。
- QML 检查使用隔离设置和空额度数据，不调用额度查询。冻结树未带静态应用 assets，故仅在诊断进程把文案/隐藏的备用图片路径指向 `qml-fixtures/`；3D/2D 角色素材、QML 布局和绑定保持冻结版本，未修改运行文件。

| 冻结文件 | SHA256 |
| --- | --- |
| `model/kinematics.py` | `df4bb2809804c840cd611ab0b6b3811d9329dc5221dbac2c3c7f457dec485d0f` |
| `model/raster_mesh.py` | `9a7e94a42bd05984c47bc4199616d4c37b48964f328aa7870eb7830382bf9b1d` |
| `model/render.py` | `3f0d7ceb653f6a6063394c0590849e0317e4181c098aacc645895ce0cd7b5e84` |
| `model/motion.py` | `55dedaef9a20e2afcdb4814389020914f80eed5249dd0044a0dd4de6f0758713` |
| `qml/Main.qml` | `2e60826bc9cc6f0492b596e527843c997126503aa2de01203958807b8e953a53` |

表中 model 路径均位于冻结 `linux/gpt_niang_linux/` 下。证据、脚本和参数记录统一在 `linux/test-results/review-pass-3/front-fix-2/`，没有把工作树的新代码混入。

## 头部动作：已改善的内容与边界

| 方向 | nod | shake | look | tilt-left / tilt-right | 取消几何 |
| --- | --- | --- | --- | --- | --- |
| front | **最低可辨通过**：1.2 秒一次低头回位，脸形不再被挤扁；不是旧版的整头上下平移 | **最低可辨通过**：小幅左右偏航可见，头壳/五官共面 | **最低可辨通过**：偏航和轻微俯仰可辨 | **通过本轮检查** | **通过** |
| front-left | **最低可辨通过**：脸与头顶相对运动连续 | **最低可辨通过**，仍属小角度效果 | **最低可辨通过** | **通过本轮检查** | **通过** |
| front-right | **最低可辨通过**：下脸压缩已明显消除 | **最低可辨通过**，尚非完整转面 | **最低可辨通过** | **通过本轮检查** | **通过** |
| left | **最低可辨通过**：绕颈前俯明确 | **小幅偏航最低可辨**；幅度偏弱，不能等同于大幅侧向转面 | **最低可辨通过**；幅度偏弱 | **通过本轮检查** | **通过** |
| right | **最低可辨通过**：前俯与回位可见 | **小幅偏航最低可辨**；五方向中尤其轻微 | **最低可辨通过**；幅度偏弱 | **通过本轮检查** | **通过** |

这里“最低可辨通过”只认可当前小角度桌宠动作，不能外推到大角度转向、回眸或完整角色动画质量。纯侧面采样的 yaw11° 最大位移从上一版的 0 变为 left **9.51**、right **6.04** 模型单位（9 个诊断采样点，不是整个头的全局最大值），在 320px 全画布约为 2.38px / 1.51px。侧面效果仍更接近轻微面部偏转；要提高幅度应补可见面或共享轮廓，不能无限放大平面扭曲。

实证改善：正面实际 pitch12° 的眼框高度从 54 变为 **52.81997**，约为正常 `cos(12°)` 缩短；眼中心—嘴中心竖向间距从 41 变为 **40.90014**，不再缩短约 40%。旧 y=201.3 分界两侧输入差 0.002，当前输出差仅 **0.002496**，旧版约 19.64 的断层已消失。颈是独立连接层，脸面可以前移遮住颈；本轮实际动作样本未见新增的大块灰色颈裂缝或五官穿到头外。

证据：[nod](../../test-results/review-pass-3/front-fix-2/action-nod.png)、[shake](../../test-results/review-pass-3/front-fix-2/action-shake.png)、[look](../../test-results/review-pass-3/front-fix-2/action-look.png)、[tilt-left](../../test-results/review-pass-3/front-fix-2/action-tilt-left.png)、[tilt-right](../../test-results/review-pass-3/front-fix-2/action-tilt-right.png)、[独立 pitch](../../test-results/review-pass-3/front-fix-2/probe-pitch.png)、[独立 yaw](../../test-results/review-pass-3/front-fix-2/probe-yaw.png)、[geometry-metrics.json](../../test-results/review-pass-3/front-fix-2/geometry-metrics.json)。固定 -12° pitch 图是压力对照，不是实际 nod 轨迹；实际 nod 0→12→0°，look 负 pitch 约 -4°。

**网格横缝修复通过。** 恒近零角度对照未再出现旧版角/发冠横线。零角度现在同样先合成头图，清晰度切换已大幅改善。仍有一个 P2 级残差：`_render_projected_head` 在 `.001` 处仍走 `_draw_texture` 或 `draw_mesh` 两条最终取样路径。`.0009→.0011` 在 320px 头部 ROI 的平均 RGB 差约 front 1.12 / right 0.97（0–255），119 个以下像素差超过 24；1280px 残差更低。当前对照只见轻微边缘锐度变化，**不再按候选 1 的明显横缝/全头变糊判阻断**。可继续统一最终采样，避免反复过零时边缘闪动。见 [近零角度原生尺寸对照](../../test-results/review-pass-3/front-fix-2/near-zero-mesh-threshold.png)。

## P0：turn / spin 已无双身，但整身换图仍明显跳变

候选 2 的 `render.py:479–485` 在 `view_mix<.5` 选择前方向，否则选择后方向，只给头加一个夹到 ±12° 的 yaw；身体、发量、袖口、裙摆、翅膀直接换成另一方向。`.6s turn` 与 `1.6s spin` 的短跨步和连续尾角不能补足身体/头部轮廓的连续性。

最直接证据是正面 turn 的 **t=.074→.076s**：两帧仅差 2ms，却从短发正面换成原基底左前侧的长发/侧裙/侧手。脸宽、头顶、两角、耳、后发长度、肩和衣裙轮廓同时改变；这不仅是转了 45°，还包含不同方向绘制与装配的身份比例差异。下一次 `.224→.226s` 又从左前侧整套换成纯左侧。普通头部小角度投影无法遮盖这些差异。

| 边界（1280px 合成，头/肩 ROI 750×600） | 前一个同样 2ms 间隔中，通道差>24 的像素数 | 跨边界 2ms 的数量 |
| --- | ---: | ---: |
| front turn .075s | 1 | **134,635** |
| front turn .225s | 0 | **117,441** |
| front spin .100s | 90 | **134,329** |
| front-right turn .075s | 24 | **108,967** |

差分用于确认不连续位置，不是仅以像素数评价动画。实际并排图同样能看到明显换人式轮廓变化：[turn 细节](../../test-results/review-pass-3/front-fix-2/switch-detail-1.png)、[spin/右前细节](../../test-results/review-pass-3/front-fix-2/switch-detail-2.png)、[全部 turn 边界](../../test-results/review-pass-3/front-fix-2/turn-switch-pairs.png)、[全部 spin 边界](../../test-results/review-pass-3/front-fix-2/spin-switch-pairs.png)。

最低修法：先保证相邻方向在共享头部/身体地标上对应，再给地标连续轨迹；纹理只在已经配准、轮廓重合的局部范围内短过渡。头、后发、胸腹、袖、裙、腿、翼不能仅按整张图透明叠加，也不能头配准后就宣布整身已修好。各方向的发长、头量、衣裙长度要先回到同一个角色。若现有素材不能在不拉坏脸/角的情况下过渡，应补中间角度图。验收应看每个边界前后 1–2ms 和正常速度，而不是只看 8 张静止方向都可加载。

## P0 / P1：look-back 仍换头，且暴露后发平切边

`render.py:_render_look_back` 使用 `index=int(look_back*2+.5)` 在后侧、侧、前侧三个完整头之间选择。首轮进入约 **.16448s / .33952s** 发生硬切；退出约 **2.385s / 2.599s** 反向硬切。身体和自身后发保留，确实消除了旧版双头，但头冠、角、耳、脸和刘海仍瞬间换形。

左右后侧四个进入边界，2ms 跨边界的头/肩 ROI 大差异像素数分别为 **104,811 / 85,271 / 79,511 / 75,783**；对应边界前的 2ms 为 811 / 2,905 / 1,860 / 326。见 [左后回眸细节](../../test-results/review-pass-3/front-fix-2/switch-detail-3.png)、[右后回眸细节](../../test-results/review-pass-3/front-fix-2/switch-detail-4.png)、[完整进入/保持/退出](../../test-results/review-pass-3/front-fix-2/look-back-switch-pairs.png)。

**另一个独立的 P1 装配问题不能被“只换单头”掩盖：** 换成侧头后，原后发上缘的水平裁切边裸露，尤其右后侧头的下巴右侧/颈后出现平直缺口，左后侧也有。原后头盖住的后发裁切面，在窄侧头下面没有得到覆盖；颈、后发与新头之间会读成一块图压在另一块截断图上。这里是实际 RGB32 合成的边缘，不是低 alpha 查看噪点。单纯给头做地标配准不能保证此缺口消失。

最低修法：头部采用共享解剖地标配准，后发根同时做连续连接；通过真实后发上段的有控制重叠、颈后桥或专用补片覆盖旧平切线。保留角色自身长后发是对的，但后发**根部**仍需随头根改变，发尾可以滞后。不要把隐藏脸点施加到后脑/发幕纹理上，不要把鼻、眼从后发像素拉出来。前侧头到后侧身体的贴合还需要检查下巴高度、颈根、耳根和角的同一身份。

## 指向气泡：四尺寸的实际 QML 绑定通过

直接加载冻结 `Main.qml`，读取 `character` 与 `quotaBubble` 的实际几何；执行 point 后气泡均自动显示。使用当前手部图的 indexTipUV/indexRay、实际手部旋转、upper 变换和完整画布映射，把指尖射线还原到 QML 窗口坐标，检查是否指向真实气泡底边中心。没有用旧的固定目标点替代实际 UI。

| scale | character 尺寸 | 气泡底中心（窗口 px） | 传入 point_target（模型坐标） | 射线垂距（窗口 px） |
| ---: | ---: | --- | --- | ---: |
| 0.6 | 192×192 | (182,338) | (490,-300) | 7.1e-14 |
| 1.0 | 320×320 | (182,338) | (490,-268) | 1.8e-14 |
| 1.5 | 480×480 | (252,338) | (490,-252) | 2.3e-13 |
| 2.0 | 640×640 | (332,338) | (490,-244) | 7.5e-13 |

四项都在指尖射线的正向，目标距指尖约 103.10 / 163.95 / 240.02 / 316.09px；不是向后延长线“碰巧命中”。这些浮点误差可视为数值零，屏幕落像素仍受抗锯齿和尺寸影响。实际截图也确认手指方向可读：[四尺寸 QML 接触表](../../test-results/review-pass-3/front-fix-2/point-qml-scales.png)、[原始量测](../../test-results/review-pass-3/front-fix-2/point-qml-metrics.json)。此表只验收**目标绑定与指向方向**，不替代其他手势中肩肘腕连接的独立审查。

## 表情、说话、取消

**保留修复通过：** 左右侧的 wink 闭合可见眼，右嘴没有再飞出脸，warpY/flip 后的 skin mask 与五官匹配。19×2 的侧面静默/最大 speech 和五脸向点头组合未发现旧眼白残留或嘴越界。原基底 ♯ / ··· / ? 双绘也已修复：[source-accents.png](../../test-results/review-pass-3/front-fix-2/source-accents.png)。

这轮补看了完整头图，避免裁掉头顶状态符号后误判语义。侧面 19 项的最低判定如下；“通过”并不声称面部表演丰富，符号辅助的项明确列出。

| 表情 | 最低判定 | 说明 |
| --- | --- | --- |
| neutral | 通过 | 正常基准 |
| happy | 通过 | 闭眼笑嘴明确 |
| wink | 几何/动作通过 | 可见眼闭合；纯侧面与 happy 的区分受单眼信息限制 |
| love | 通过 | 爱心瞳/脸红可辨 |
| shy | 最低通过 | 偏视和脸红；面部变化仍轻 |
| surprised | 最低通过 | 张口与 ! 辅助 |
| angry | 最低通过 | 半眼、皱嘴、♯ 辅助；去掉符号后怒意仍偏弱 |
| sad | 最低通过 | 完整图可见泪滴与弯嘴 |
| sleepy | 最低通过 | 半眼与小开口 |
| thinking | 符号辅助最低通过 | 上视和 ···；面部本身仍不足 |
| smug | 最低通过 | 半眼笑嘴，与 sleepy 的口部不同 |
| pout | **语义仍未通过** | 已改唇形、不再直接用旧圆孔，但原生尺寸仍很难读为嘟嘴 |
| worried | **语义仍未通过** | 小眉/弯嘴/圆点不足以稳定区分担忧，建议独立眼睑和眉内侧变化 |
| determined | **语义仍未通过** | 与 neutral 的变化太轻，认真神态不稳定可辨 |
| flustered | 通过 | 明显闭眼形与脸红 |
| scared | 最低通过 | 当前缩瞳、眼白与开口组合比旧版明确 |
| excited | 最低通过 | 亮瞳和笑嘴 |
| cry | 通过 | 闭眼与明显泪水 |
| confused | 符号辅助最低通过 | ? 和轻歪头；建议继续增强眉眼差异 |

完整头证据：[左侧 19 表情](../../test-results/review-pass-3/front-fix-2/expressions-full-head-left.png)、[右侧 19 表情](../../test-results/review-pass-3/front-fix-2/expressions-full-head-right.png)。`expressions-{left,right}-page-{1..5}.png` 另保留口眼近景的静默/最大 speech 配对，`nod-expression-combos.png` 保留动作叠加。

**基础说话通过本轮修复。** speech 已有真正归零/闭口段，happy 的开口也保留笑嘴轮廓，不再所有情绪统一 O；见 [speech 时间序列](../../test-results/review-pass-3/front-fix-2/speech-timeline.png)。当前仍是固定周期的通用说话动画，未验证音素同步或自然句读，不作这两项的通过声明。

**稳定状态取消通过，过渡中断仍失败。** 五方向五动作共 25 组在 cancel+0 的全部对应几何字段最大差为 **0.0**。已经稳定的 happy/cry 说话状态取消时，眼睛、嘴和泪水也开始平滑回归，不再同帧全部跳回 neutral；见 [稳定表情取消](../../test-results/review-pass-3/front-fix-2/cancel-face-transition.png)。

但在 neutral→happy 的 160ms 过渡进行到 **80ms** 时取消，原本 50% neutral + 50% happy 的脸立刻变成 **100% happy**，再向 neutral 过渡；happy→neutral 进行到80ms时切 cry，则先瞬间回到100% neutral；happy→cry 进行到80ms时取消，泪水/嘴也同帧跳到完整 cry。见 [中断对照](../../test-results/review-pass-3/front-fix-2/face-interrupted-transition.png) 和 [状态记录](../../test-results/review-pass-3/front-fix-2/face-interrupted-records.json)。

根因在 `motion.py` 的 `set_expression/play/cancel`：`face_transition` 只保存目标/前一个 expression 字符串，丢了当下正在显示的权重分布。最低修法是从**当前可见混合状态**重启新过渡，而不是从上一目标名称重启；眼睑、嘴角、泪水也要继承当前状态。长期应将眼睑开度/眉角/嘴形参数连续插值，局部纹理透明混合会出现灰淡眼睛，不能无限替代自然睁闭眼。前述稳定取消通过不覆盖这个可重复的 P1 中断缺陷。

## 交给实现方的头部 cage 与补图建议

已按要求手工读取候选 2 的实际头部合成，提供 [head-cages.json](../../test-results/review-pass-3/front-fix-2/head-cages.json)：**8 个方向 × 19 个地标**，包含颈、双角根/尖、双耳根/尖、发顶、刘海中点、双眼中心、嘴、下巴、鼻、额头与呆毛。每点给模型坐标、headBox UV、可见性、选点方法和估计误差；`cages/*-grid.png`、`*-landmarks.png` 可直接检查位置。没有用 bbox 四角冒充解剖点。

左右按角色自身定义，带结饰的一侧为 left。背侧被挡的眼/嘴/下巴明确为 hidden estimate、visibility=0，不能把它们当作原图真实可见结构。当前颈点是原 rig attachment，不是下巴位置。角身份跨生成视角的对应仍需分层检查；直接把所有点组成一张无分层网格可能交叉折叠，尤其不能让角和脸互相牵拉。

推荐先用这些地标校准 **BL→L→FL、BR→R→FR**。如果配准后仍有明显轮廓变化，应补四个明确中间头向：**112.5°、67.5°、247.5°、292.5°**（沿仓库 VIEW_ANGLES 约定），分别表现近眼初现、远眼逐渐露出的阶段；保持同一对角、同一饰物侧、脸宽、头量和下巴高度。JSON 中有逐张要求。此建议仍需由下一冻结候选的实际连续效果确认，不能把数据文件存在当作视觉完成。

## 下一轮验收重点

1. 保留本轮已通过的小角度头部投影、右嘴/wink/mask、气泡坐标和稳定取消，不通过修改静态身份比例掩盖跨视角问题。
2. 在每个 turn/spin 与 look-back 边界前后至少各取1–2ms，检查颈根、眼线、角、耳、发量、衣裙与肩是否连续。配准应先消除轮廓跳变，随后才做局部材质短过渡；不能回到整头/整身透明叠双影。
3. 检查窄侧头下面的后发上缘平切线；扩大窗口/渐变必须使用真实后发上段，不可用模糊把缺口藏起来。必要时补颈后/发根片。
4. 表情过渡在40/80/120ms分别再次取消和换表情，要求事件+0时可见状态不跳；speech 开关也须保留当前 amount。
5. 新实现再次冻结后复核。图像对齐数值、无异常和自动测试只用于定位与回归，最终仍要看实际 Qt 连续动作、原生桌宠尺寸与放大连接细节。
