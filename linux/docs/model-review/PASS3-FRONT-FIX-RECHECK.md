# 第三轮前向审查：修后候选 1

结论：**候选 1 整体不通过**。点头已经不再只是旧版的整头上下平移；侧面点头能够辨认为绕颈前俯，前向点头也出现方向变化。但前向面部被过度压缩，曲面深度有硬断层，网格会产生实际横缝；左右纯侧面的 yaw 完全没有生效，摇头仍不成立。不能因加入 `head_pitch/head_yaw` 或三角网格就验收。

本轮可以明确通过的修复：**右侧嘴定位、纯侧面可见眼的 wink、侧面皮肤遮罩对齐，以及普通头部动作取消瞬间的几何姿态连续**。这些通过项不代表自然说话、完整表情过渡或整个头部动作已经通过。

## 冻结对象与复现

- 输入只使用 `linux/test-results/review-pass-3/candidate-1/linux/`；与基线报告 `PASS3-FRONT.md` 的 `0e50179fb7e9b09db947739eb04f404f61dbfaae` 分开。
- 首次冻结核验时间：**2026-11-01 11:07:31 +08:00**。诊断原模型另复制到 `front-fix-1/imported-model/`，避免本机导入模型后续变化。
- 运行时断言 `motion.py`、`render.py` 和扩展模型路径均来自候选冻结树。完成复核时重算全部输入 SHA256，**0 项不一致**。`view_errors=[]` 仅证明加载无异常，不是视觉通过证据。
- 完整清单：[snapshot.json](../../test-results/review-pass-3/front-fix-1/snapshot.json)。主要输入 SHA256 如下；行号均指该候选冻结文件，不指主上下文正在修改的工作树。

| 文件（相对于冻结 linux/） | SHA256 |
| --- | --- |
| `gpt_niang_linux/model/kinematics.py` | `67ff046b9a08b5aae7e2b9301c3837908adb8adecc40621e9cf886f60fa3d5ef` |
| `gpt_niang_linux/model/raster_mesh.py` | `410096b7e94c98131507da420e3dae3227f89e3695d1159bbac9bbe1d14cd633` |
| `gpt_niang_linux/model/render.py` | `95ea225ee4eef4569923cada91d9eb52ac7a07881934cac4a16b122c61c6a22a` |
| `gpt_niang_linux/model/motion.py` | `155f6d621602e5445280bae65d835a1e9f052ae89d93057d9065806ab34b027c` |
| `gpt_niang_linux/model/dynamics.py` | `9d920760de03e7566ed548fa92d2b14f83842b7a4b3914c438b0a53d5ceb307a` |
| `models/dragon/right/rig.json` | `c09e559353b74c57aff867d45f25c3ea62713632cb16a0daca084b8223a1ec19` |
| `models/dragon/left/rig.json` | `07e28b9d956e081b633036a62974b9156844c69677e6c89a8db657bce10b49f1` |

使用原仓库 `linux/.venv/bin/python`，`QT_QPA_PLATFORM=offscreen`，`PYTHONDONTWRITEBYTECODE=1`，`PYTHONPATH=linux/test-results/review-pass-3/candidate-1/linux`。脚本为诊断目录的 `common.py`、`check.py`、`diagnose.py`。全部画面经实际 Qt 渲染，再用 QPainter 合成到不透明 RGB32 灰底；主要输出 1280px，另直接渲染 320px 检查实际桌宠尺寸。时钟从 1 开始、步长不超过 1/120 秒。未编辑任何运行文件、rig 或素材；只有另述的进程内替换用于隔离根因，替换后恢复原函数。

覆盖：五个脸向 × nod / shake / look / tilt-left / tilt-right，各 11 个实际时间点（包括结束后）；五方向五动作取消前及取消后 0 / 55 / 110 / 165 / 220 / 300ms；额外在运动中段而非仅极值点取消；左右侧面各 19 表情 × 静默/最大 speech；五方向点头峰值结合 neutral / wink / happy / cry 与说话。固定 pitch/yaw ±12° 仅用于分离投影效应，**负 pitch -12° 是压力样本，不是实际 nod 轨迹**。实际 nod 第一峰值为 +12.1°，look 的负 pitch 约 -4°。

`point` 对真实气泡的绑定、跨视角转身和回眸重影仍由主上下文处理，不列为本候选已经修好的项目；本轮也不重新宣告其他手势通过。

## 五方向逐项判定

“最低可辨”只描述动作语义有没有出现；最终列仍要求材质、轮廓、连接和结束稳定。

| 方向 | nod | shake | look | tilt-left / tilt-right | 普通取消 |
| --- | --- | --- | --- | --- | --- |
| front | **失败**；低头最低可辨，峰值眼睛和下半脸被压扁，头顶分段变形 | **失败**；小幅左右转意图可辨，但为弹性脸形、存在硬折层和网格闪变 | **失败**；有视线/头部方向变化，继承投影畸变 | **通过本轮几何复核**；左右倾斜可辨，取样未见新颈缝 | **几何通过**；表情/口型连续失败 |
| front-left（原基底） | **失败**；头部俯仰可辨，脸部压缩，发层变化不自然 | **失败**；有小幅方向变化，但头顶曲面不连续 | **失败**；同投影问题；部分表情符号双绘 | **通过本轮几何复核**；仍使用平面 roll，不等于侧向转头 | **几何通过**；表情/口型连续失败 |
| front-right | **失败**；俯仰可辨，下脸与颊部受到非均匀压缩 | **失败**；变形可见但不够像稳定头壳转动 | **失败**；同曲面/栅格问题 | **通过本轮几何复核**；取样轮廓连续 | **几何通过**；表情/口型连续失败 |
| left | **动作几何最低通过，成片失败**；确实绕颈前俯，继承网格横缝与清晰度跳变 | **失败**；yaw 不参与计算，头壳根本不转 | **失败**；仅余小幅 pitch，缺少左右张望 | **通过本轮几何复核**；是画面内倾斜，不能拿它替代 yaw | **几何通过**；表情/口型连续失败 |
| right | **动作几何最低通过，成片失败**；绕颈前俯可见，网格横缝尤其清楚 | **失败**；与 left 同根因 | **失败**；与 left 同根因 | **通过本轮几何复核**；未发现新颈部大裂缝 | **几何通过**；表情/口型连续失败 |

证据：[nod 连续时点](../../test-results/review-pass-3/front-fix-1/action-nod.png)、[shake 连续时点](../../test-results/review-pass-3/front-fix-1/action-shake.png)、[look 连续时点](../../test-results/review-pass-3/front-fix-1/action-look.png)、[tilt-left](../../test-results/review-pass-3/front-fix-1/action-tilt-left.png)、[tilt-right](../../test-results/review-pass-3/front-fix-1/action-tilt-right.png)、[独立 pitch 对照](../../test-results/review-pass-3/front-fix-1/probe-pitch.png)、[独立 yaw 对照](../../test-results/review-pass-3/front-fix-1/probe-yaw.png)。本轮判断来自这些实际合成时间采样和细节对照，不宣称已观看未生成的视频。

## 阻断项与具体修法

### F1 · P0：深度场在头顶有真实硬跳变

`kinematics.py:72–75` 先给椭球正深度，随后在 `y < by + bh*.29` 区间改用另一段负深度，两段在边界没有连续衔接。正面 `box=[190,65,470,470]` 的分界是 **y=201.3**。对 x=425 的两个相邻输入点：

| 输入 | pitch=12.1° 的输出 y | yaw=11° 的输出 x |
| --- | --- | --- |
| y=201.299 | 207.046459 | 424.999964 |
| y=201.301 | 226.689103 | 442.878247 |

输入只差 **0.002**，输出却相差 **19.642644 竖向单位**或 **17.878283 横向单位**。这不是平滑透视，而是在头冠附近强行折一段；提升网格密度无法修复数学不连续。具体测量见 [projection-metrics.json](../../test-results/review-pass-3/front-fix-1/projection-metrics.json)。

最低修法：删除硬分支，把头壳、额头、发根表面的深度做成至少位置连续、最好一阶连续的场；给一组明确的额头/眼线/鼻/下巴/颈根 3D 或 2.5D 控制点，再对它们做同一刚体俯仰/偏航投影。角和呆毛不应被整张面片的椭球深度任意压扁；可作为独立固定在头壳上的层。先验收一个正面头在 0→12.1→0° 的实际序列，再推广其余方向。

### F2 · P0：颈部权重覆盖了脸，造成“软纸片”压缩

`kinematics.py:74` 的 `neck_weight=(ny-y)/(bh*.12)` 对整个头图生效。正面颈点 `[425,460]`，权重从 **y=403.6** 开始衰减，穿过眼睛下半部、嘴和下巴，而不是只作用在颈桥。

在**实际 nod 峰值 +12.1°**，正面参考眼框 y=370..424 的高度由 54 变为 **42.137819（缩短 22.0%）**；眼中心 `[370,397]` 与嘴中心 `[425,438]` 的竖向间距由 41 变为 **24.509530（缩短 40.2%）**。对比同角度 `cos(12.1°)≈0.978`，可知不是整体正常投影缩短，主要是深度和颈权重造成下脸内挤。证据为 [pitch 对照](../../test-results/review-pass-3/front-fix-1/probe-pitch.png) 与 [点头加表情/说话](../../test-results/review-pass-3/front-fix-1/nod-expression-combos.png)。

最低修法：**固定颈骨节点，不等于把屏幕上接近颈高度的全部头部像素深度归零。** 下巴表面可以在颈节点前方，低头时投影遮住颈部；保留脸/下颌的连续曲面和体积，另做受下颌遮挡的颈桥，颈桥下端固定领口。不要简单把衰减带从 y=403.6 挪到下巴下面的 3px 内，否则只是制造更陡的新折层。五官可继续与脸共曲面，但眼白、虹膜、睫毛和嘴须共用同一局部面/UV，不再分别挤向颈点。此次没有在实际动作取样中看到大面积灰色颈断口；**失败点是脸形和连接运动方式，不能凭“没断开”判自然**。

### F3 · P0：纯侧面 yaw 被提前返回分支丢弃

`kinematics.py:55–61` 的 left/right 分支只按 `pitch*direction` 做 2D 旋转，立即 return，完全不读取 yaw。对左右侧面各取 9 个头部点，`pitch=0,yaw=11°` 相对中立的最大位移均为 **0.0**。`dynamics.py:33` 的 shake 只设置 yaw，结果只是触发网格重采样，头壳没有任何摇头运动；look 的 yaw 同样丢失，只剩约 -4° pitch。

最低修法：侧面也必须有真实 yaw 方案。优先把相邻方向的头部控制点映射到同一颈节点，用共享拓扑/轮廓插值或具备遮挡关系的层投影；纯侧面向正面转时，额头、鼻尖、近眼、耳根都应沿不同轨迹变化。若单张侧面素材不能暴露原本被遮的面部，需补中间头图或使用已有相邻头组并校准相同地标。不要以左右平移、roll 或整头透明交叉淡化代替；也不要仅把侧面塞入当前正面椭球公式，它没有侧面鼻/耳和可见性结构。最低允许小角度转动，但在真实桌宠尺寸须能辨出摇头方向变化。

### F4 · P0：三角子图采样产生横缝，启用网格时清晰度跳变

`raster_mesh.py:44` 在每个三角 clip 内以单元子矩形 `drawImage(sourceRect)` 取样。右侧 yaw=.011° 时 `head_point` 数学上仍是恒等映射，但角/发冠出现横线；yaw=0° 的原渲染路径没有该线。把相同离屏头图一次直接绘制，线也消失。这证明横线来自网格栅格化，**不是源素材裁片碎屑，也不是透明预览低 alpha 噪点**。

已做两种隔离：[恒等映射对照](../../test-results/review-pass-3/front-fix-1/seam-isolation.png)、[320px 原生尺寸阈值对照](../../test-results/review-pass-3/front-fix-1/seam-threshold-320.png)。后者显示 `.009→.011` 时头图清晰度变化，即使头坐标不变；`render.py:587/730` 的 `.01` 分支切换了不同取样流水线。

一个经过**仅内存试验**的可执行修正：保留三角 transform/clip，把该行改为 `painter.drawImage(QPointF(0,0), image)`，即每个 clip 都从同一整幅纹理采样。右侧恒等映射、右侧 pitch12、正面 yaw11 和 pitch12.1 的横缝均消失，见 [whole-source trial](../../test-results/review-pass-3/front-fix-1/seam-whole-source-trial.png)。这只证明该取样缝可以如此消除，不证明所有网格边、性能或投影已合格。还需统一零角度与非零角度的离屏分辨率、MIP 选择和过滤；用同一流水线渲染零角度，或确保两条路径输出一致，避免进入/退出动作时全头突然变糊/变清。

### F5 · P1：原基底表情符号被画两遍

`_render_projected_head` 调用 `_render_source(scope='front-head')` 把 ♯ / ··· / ? 等符号画入头部离屏图，外层 `_render_source` 在投影之后又走一次符号绘制。front-left angry、thinking、confused 在 yaw12 的灰底图中出现错位的双符号，见 [source-accents.png](../../test-results/review-pass-3/front-fix-1/source-accents.png)。

修法：明确符号的唯一绘制层。建议符号不烘入脸的曲面网格，只让其锚点经 `head_point` 变换，最后绘制一次；若选择随头表面变形，也必须禁止外层再画。查 `_render_source` 的 scope guard（约 621 行之后），不要只在普通视图分支修。

### F6 · P2：发层没有统一的俯仰/偏航根部运动

`_render_projected_head` 只收集前头/head、hairFront、ahoge，hairBack 留在旧路径。头壳倾斜而后发根不随 pitch/yaw 走，当前靠发层重叠遮住连接。在大图中能看见前头与后发运动关系欠自然，但本轮实际范围未确认有大面积发根裂口，不能把它写成已经观测到的断裂。

最低设计：把后发根也挂到同一颈骨/头壳投影，发尾再用独立滞后和摆动；用后发—颈桥—头壳—五官—前发的明确遮挡顺序。角、饰物应保持局部形状，随头骨移动；不能和颊部共用任意软变形。不要重画当前已对齐的静态脸来掩盖动态数学问题。

## 左右侧面 19 表情与说话

两侧 **19×2** 画面逐一检查；19 项的皮肤覆盖、可见眼对齐及嘴不越出脸这一狭义几何检查均通过。`right/rig.json` 的 `face.features.mouth=[98,90,11,9]` 把嘴中心放回约模型坐标 `[518.550,391.978]`；最大 speech 仍在脸内。`render.py:267` 的单眼 wink 索引修正确实闭合了可见眼。皮肤 mask 和脸的 warpY、右侧翻转同步后，检查到的闭眼、说话和 nod 组合未再出现旧版眼白残留/嘴飞出头外。

下表将本轮修复的几何与表情含义分开。语义“通过”仅表示最基本识别，不代表已经达到原画级表现；这些表情绘制机制大多沿用旧版。

| 表情 | 左/右侧面几何 | 最低语义判定及仍需处理的内容 |
| --- | --- | --- |
| neutral | 通过 | 通过：平静基准 |
| happy | 通过 | 通过：闭眼、笑嘴可辨 |
| wink | 通过 | 通过本次修复：唯一可见眼闭合；侧面不要求不存在的远眼同时可见 |
| love | 通过 | 通过：爱心瞳/脸红可辨 |
| shy | 通过 | 通过最低识别：脸红和偏视；仍可增强回避神态 |
| surprised | 通过 | 通过最低识别：张口/眼部变化；不可与说话口型混为一类 |
| angry | 通过 | **失败**：主要是眼部压扁，小眉被发遮住，怒意弱、容易读作困倦 |
| sad | 通过 | **失败**：与 worried/scared 的小眉/弯嘴差别不足，原有表现不足仍在 |
| sleepy | 通过 | 通过最低识别：半闭眼可辨；与说话组合仍须有疲倦口型 |
| thinking | 通过 | **失败**：侧面仅靠很小的上视，缺少足够可见的思考神态 |
| smug | 通过 | 通过最低识别：半眼和笑嘴组合；可继续提高与 sleepy 的区分 |
| pout | 通过 | **失败**：圆孔式嘴更像发音/惊讶，不像收唇鼓嘴 |
| worried | 通过 | **失败**：与 sad/scared 区分弱 |
| determined | 通过 | **失败**：小幅眉旋转/眼压缩不足以表达认真，眉的遮挡仍是限制 |
| flustered | 通过 | 通过最低识别：明显的闭眼形和脸红 |
| scared | 通过 | **失败**：与 worried/惊讶/说话嘴重合过多 |
| excited | 通过 | 通过最低识别：亮瞳和笑嘴 |
| cry | 通过 | 通过最低识别：闭眼和泪水；取消时泪水消失突兀，见下节 |
| confused | 通过 | **失败**：侧面小眉变化和约 2.5° 倾斜不足，不能靠极小变化宣告完整疑惑表情 |

证据为 [left 第1页](../../test-results/review-pass-3/front-fix-1/expressions-left-page-1.png)、[第2页](../../test-results/review-pass-3/front-fix-1/expressions-left-page-2.png)、[第3页](../../test-results/review-pass-3/front-fix-1/expressions-left-page-3.png)、[第4页](../../test-results/review-pass-3/front-fix-1/expressions-left-page-4.png)、[第5页](../../test-results/review-pass-3/front-fix-1/expressions-left-page-5.png)；[right 第1页](../../test-results/review-pass-3/front-fix-1/expressions-right-page-1.png)、[第2页](../../test-results/review-pass-3/front-fix-1/expressions-right-page-2.png)、[第3页](../../test-results/review-pass-3/front-fix-1/expressions-right-page-3.png)、[第4页](../../test-results/review-pass-3/front-fix-1/expressions-right-page-4.png)、[第5页](../../test-results/review-pass-3/front-fix-1/expressions-right-page-5.png)。

**speech 的嘴部定位通过，自然说话失败。** 现有 `.35+.65*abs(sin(12t))` 没有真正闭嘴间隙，且渲染主要是圆椭圆缩放；最大 speech 把多个表情的专用笑/弯/嘟嘴覆盖为同一个 O。下一步至少提供闭合、微开、横向开、圆唇几种口型及停顿，保留情绪的嘴角方向，不需要一开始就实现音素识别。对弱表情先调整眉的可见区域和独立眼睑形，而不是继续用整眼 y 缩放代替所有眼神。

## 取消、结束与持续

**旧版普通取消的几何瞬移已修复，通过。** `motion.py:220` 保存完整 pose，`blend_pose` 确实包括 head pitch/yaw、roll/平移/缩放、root、gaze 等；本轮全部五方向五动作在取消 +0ms 与取消前相同的对应几何字段一致，之后约 220ms 回归。额外在动作仍快速运动时取消，仍无位置跳变，见 [cancel-moving.png](../../test-results/review-pass-3/front-fix-1/cancel-moving.png)、[cancel-tilt-left.png](../../test-results/review-pass-3/front-fix-1/cancel-tilt-left.png) 及 `cancel-*.png`。正常结束后也没有保留上一帧的头角。

**完整取消的表情/口型过渡仍失败。** `blend_pose` 的 keys（约478行）不包含 expression、eye_closed、speech、tear，cancel 同帧设回 neutral 并停止 speech。happy/cry 说话时取消，头还停在原角度，眼睛已经突然张开、嘴突然关闭、泪水突然消失。[cancel-face-material.png](../../test-results/review-pass-3/front-fix-1/cancel-face-material.png) 显示这一点。若产品要求取消同时结束表情，仍应给材质一个短过渡；若仅取消动作，应保留当前表情和独立说话状态。推荐拆开动作取消与情绪/发声生命周期，而不是让完整头组交叉淡化，后者会重现双眼重影。

另有 P2 的速度连续性：当前 blend 保存位置而不保存速度。运动中段的有限差分显示，shake 取消前 yaw 速度约 **+200.03°/s**，取消后首个 1/120s 约 **-3.92°/s**；nod 从 **-103.38°/s** 变为 **-2.77°/s**；tilt-left 从 **-68.32°/s** 变为 **+1.77°/s**。这不是旧版的几何瞬移，不能混淆；但视觉上会突然刹停再返回。可用当前速度初始化短阻尼回位/Hermite 段，避免逆向急刹。正常 nod 0.8s 两次、shake 0.8s 三次的节奏也应在投影修好后看实速，再决定是否减为一次主动作加衰减回位，不能只在静态峰值验收。

归零时仍会跨过网格启用阈值，因此 F4 的清晰度闪变会出现在动作结束和取消末尾；几何通过不覆盖此渲染问题。

## 建议实施顺序与验收门槛

1. 先修 F4 的三角取样缝、统一零角度渲染路径；以 320px 和 1280px 的同图恒等映射验证没有横线/清晰度跳变。仅此步骤不能验收自然动作。
2. 用一个 front 头修 F1/F2：连续深度、脸/下颌保体积、独立颈桥、角和发根合理跟随。保留当前静态 rig 与五官布局，避免边修动态边改变身份比例。实际播放 0→12.1→0°；脸不应挤成带状，嘴不得向眼线大幅聚拢，领口与颈下端稳定。
3. 给 left/right 补真实 yaw 路径；比较鼻尖—近眼—耳根三个地标，不能全头恒等或仅整体平移。必要时补头部中间图或带共享地标的邻向头组；禁止透明叠双脸。
4. 修 F5 符号唯一层和后发根绑定；选 angry/thinking/confused 与 nod/shake 组合检查。前发可遮五官，后发可遮颈，但遮挡应有明确顺序，不能靠渲染残影隐藏错误。
5. 保留已通过的右嘴、wink、mask 修复；再补取消的表情/发声生命周期与回位速度。最后处理弱表情和有闭合/停顿的 speech。

新候选必须再次冻结。至少看五方向每动作起始、前中后段、极值、正常结束以及正/负运动速度时取消；组合 happy/wink/cry/speech，并同时看原生尺寸和放大头部。通过标准是动作可辨、脸型/发量身份稳定、头壳和五官作为同一立体对象运动、颈与领无裂缝、角/饰物不被压成软片、发层不穿脸、取消无位置/材质突变、启停无清晰度闪变。自动测试和 landmark 数值可用于定位，**最后必须看实际 Qt 合成的连续动作效果**。
