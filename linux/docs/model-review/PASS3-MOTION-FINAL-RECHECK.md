# 第三轮：candidate-2 动作、取消与方向入口复核

审查日期：2026-11-01。只读冻结候选与真实 Coopanion 素材；没有修改运行代码或模型，没有提交。**候选 2 的旧落地卡死等问题已修，但仍不能整体验收。** 本报告的“FINAL”是约定文件名，不表示全体动作通过。

实际改善：跳跃已有蓄力、收腿、吸震；点头在正面也有头部投影；坐姿明显下降到贴地位置，站起先收足；睡眠取消逐步睁眼并起身；空中取消的双臂和横移能连续交到落地。仍需解决的确定问题是背向空中切表情会快速归地再重播动作、跑步取消丢失竖直速度、尾部接地约束在空中状态切换时跳形，以及转向由叠影改成了整身硬切。坐裙过渡、行走语义、扑翼/舞蹈协调等也仍未达到下述最低要求。

## 快照与证据范围

固定读取：

`/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/candidate-2/linux`

这是第三轮原始基线 `0e50179fb7e9b09db947739eb04f404f61dbfaae` 之后的候选，不是该提交本身。主上下文在当前树所作的新修改没有混入本报告。采样开始及结束核验的 SHA-256 一致：

| 文件 | SHA-256 |
|---|---|
| motion.py | `55dedaef9a20e2afcdb4814389020914f80eed5249dd0044a0dd4de6f0758713` |
| render.py | `3f0d7ceb653f6a6063394c0590849e0317e4181c098aacc645895ce0cd7b5e84` |
| articulation.py | `6f6604230341458c28f9a5ad6483b589817afeab6ccb539435f5e52e9079d939` |
| dynamics.py | `fe583887a85e842cdb9c4ab7a0076e055a593525b7bd2dd447540f48b8b09729` |
| kinematics.py | `df4bb2809804c840cd611ab0b6b3811d9329dc5221dbac2c3c7f457dec485d0f` |
| raster_mesh.py | `9a7e94a42bd05984c47bc4199616d4c37b48964f328aa7870eb7830382bf9b1d` |

使用 `/home/alazif/.local/share/gpt-niang/models/coopanion-dragon-1.1.0` 的真实原图，`QGuiApplication`、`DragonRenderer(model_directory())`、`Animator`，RGB32 `#bcbcbc` 灰底合成。所有诊断在 `linux/test-results/review-pass-3/motion-fix-2/`（ignored，本地证据，不是已随仓库发布的图片）。

**已实际渲染且逐图查看：**

- 全部 30 张 `<动作ID>.png`，每张 20 格，共 600 格。包括 14 个常规时间点及中途取消前、取消后 0/.09/.22/.5/1.5 秒。stand 从稳定坐姿开始，land 从 carried .5 秒开始；一般从 front-left 经真实 `play()` 路由进入动作，再采本体。
- 全部 `peak-cancel-1..6.png`，共 240 格：每项取取消前及后 0/.09/.22/.4/.65/1.2/2 秒。所谓“极值”是在 13 个候选相位中挑最大变化，坐站选 seat 接近 .5、转向选 mix 接近 .5；没有宣称求出数学全局极值。
- `directions-{jump,hop,walk,run,carried,toss}.png`：front/left/right/back 请求，各三个时点；背面 jump/hop 标签明确显示实际已路由到 front-left，不能把它计作背面动作本体通过。
- `dense-{nod,shake,flap,shiver}.png`：front/front-left/right 各六时点；`head-look.png`、`arms-point.png`、`lower-{sit,stand}.png`。
- 旧问题的专门实图：`bug-land-cancel-stuck.png`、`boundary-fall-{jump,toss,carried}.png`、`boundary-bow-end.png`、`sleep-held-cancel.png`。
- 新边界实图：`rear-toss-expression.png`、`run-cancel-0.41.png`、`run-cancel-0.49.png`、`tail-contact-boundaries.png`、`leg-rest-threshold.png`、`direction-cuts-{turn,spin}.png`，以及六张 `entry-*.png`。后者分别是 front-left→wave、back→nod、front→bow、right→sit、front→look-back、back-right→point。
- `diagnostic-dizzy-end-crop.png` 用于复核小图误读：正常结束后的眼睛确实恢复 neutral，没有把缩略图误读当缺陷。

**仅数值/API 检查，不能算视觉通过：** `deep-boundaries.json` 中 8×30=240 项从空闲态进入动作的路由均在限定时间内消费 pending；这里只查未卡队列，不是 240 项逐图验收。另查已落地双重取消，5 秒后 action/pending 为空、fall=False、root_y=0、airborne=False。没有把这些结果替代上述实图。

另专查 raw leg 与 IK 分支的 .001 阈值，实际 jump 在 t≈.00702984s 两侧未见可辨腿/鞋跳形，因此没有仅凭分支存在把它列成失败。

没有穷举 8×30×19，没有验收所有两动作互相替换、全部表情、实际鼠标抓点/抛掷速度、气泡目标或窗口移动。额外生成但未逐图查看的补充表不计覆盖。本轮表情接口用真实 `set_expression()`，没有强制 Pose 绕过自动回前侧；头部方向表也是实际 `play()` 后的方向。常规 advance 步长 1/60 秒，边界用精确小步到达，未用大 dt 绕过 .1 秒上限。

复现脚本是同目录 `sample.py`、`details.py`、`boundaries.py`、`deep_boundaries.py`，原始 Pose 在 `manifest.json`、`cancel-peaks.json`、`boundaries.json`、`deep-boundaries.json`。仓库根目录执行，例如：

```bash
QT_QPA_PLATFORM=offscreen PYTHONPATH=linux/test-results/review-pass-3/candidate-2/linux linux/.venv/bin/python linux/test-results/review-pass-3/motion-fix-2/deep_boundaries.py
```

## 30 项矩阵：本体、结束/取消、入口分别判定

下列 30 行均有实际多时点实图及极值取消图。“通过*”仅指所采可靠方向的最低动作设计成立，不表示静态资产、八方向或全部交互通过。“部分”仍是未达到整项验收。每行基础证据为同名 `<ID>.png` 及按动作表顺序排列的 `peak-cancel-1..6.png`。

方向入口标记：**直接***＝所采直接入口没有额外转向缺陷；其他未逐图方向不外推。**R 未过**＝API 队列能完成，但需要转向的入口继承整身硬切。**N**＝其余方向只有 240 项数值路由证据。原始 motion.py 的 face views 包括侧面，背向条件与侧面条件不可混称。

| ID | 本体 | 自然结束/保持；取消 | 方向入口 | 最低设计、剩余缺陷与具体建议 |
|---|---|---|---|---|
| stand | 部分 | 能先收足再起；所采取消继续起身，无悬空。裙过渡仍未过 | 稳定 front-left 坐姿直接*；其余 N | 骨盆/足分段时序已成立，保留。seat .62–.86 的两套裙轮廓应以遮挡/共同网格交接；不必恢复旧完整 sit 图。 |
| jump | 部分，腿链通过* | 蓄力→伸展→收腿→吸震成立；空中取消全身落地通过*，尾接触开关未过 | front/left/right 直接采样；背向 R 未过 | 已不是整图上下移。保留 125 高度与屈膝链；修尾世界坐标约束。侧面膝被长裙挡住仍比前侧难读，可补裙前后遮挡，不能仅增整图高度。 |
| hop | 部分，短跳通过* | 小幅蹲和短滞空可区分；取消未见旧双臂跳，继承尾开关缺陷 | front/left/right 直接采样；背向 R 未过 | 48 高度、24 收腿可作为小跳；同族不需另画整图。保留较小幅度并让尾接触连续。 |
| look | 通过*（小幅张望） | 眼/头扫视，结束及取消可回收 | front/left/right 直接采样；背向 R 未过 | 新侧面 yaw 实图已有轮廓变化，不再忽略。仍限小角度；更大张望需侧面→三分之四头的连续透视，不扩大平移。 |
| turn | 未过 | 能完成方向和取消收敛；硬换图边界未过 | 自身即方向系统，未过 | .5 阈值整身切换；颈肩髋脚位置、头身比例和服饰剪影不连续。先注册共同骨架再按角度投影/补中间图；踏步不是硬切的补偿。 |
| nod | 通过*（12°小幅点头） | 正面/前侧/右侧有俯仰；单次缓慢低头回正，取消连续 | front/front-left/right 实图直接*；背向 R 未过 | 不是仅 head.y 平移；正面额、眼、下巴相对关系变化可见。保留颈根与小角度网格，扩大幅度前需下巴/颈部遮挡和透视头片。 |
| shake | 通过*（小幅摇头） | 正面和侧面均有 yaw；结束/取消连续 | front/front-left/right 实图直接*；背向 R 未过 | 已修 profile 忽略 yaw；侧面幅度较轻但有真实变化。保持单周期和颈部锚点，不用整头横移代替。 |
| spin | 未过 | 经过八方向并回到原方向；极值取消不再叠两人，但仍切换剪影 | 自身未过 | 每 .2 秒左右切一次方向图。需与 turn 共用注册后的连续方向；支撑足应按转踏相位解约束，当前抬足时 contacts 仍 True。 |
| sit | 部分，终态通过* | 已像贴地坐；足先锁地屈膝，末段抬足前伸；保持有效，取消会起身 | front-left 直接*；其余 R 未过 | pelvis180 已解决上一版主要悬坐；不要继续单改下降量。未过的是中间站裙/坐裙透明轮廓，修遮挡和腰/裙摆共同拓扑。 |
| sleep | 部分，保持/醒来通过* | 闭眼坐姿可保持；取消逐睁眼并收足起身；继承 sit/stand 裙过渡 | front-left 直接*；其余 R 未过 | 可读作坐着睡。坐定后低头放松可进一步延后，但主要阻碍已是裙，不是状态保持或眼睛弹开。 |
| dizzy | 通过* | 髋/上身局部晃动、头补偿；结束/取消表情淡回与姿态回收有效 | front-left 直接*；背向 R 未过；其余 N | 保留固定足和局部失衡；不需要整图摇摆。大幅度才需补平衡步。 |
| walk | 未过“行走”；可读为踏步 | 交替抬靴可见；自然结束/取消身体连续 | front/left/right/back 实图无前置转向；其余 N | 每次摆动回原足位，未定义世界步长。左侧仍被长裙遮得很重。若语义为走动，根速/足轨迹必须同源；否则应明确是原地踏步，不能用 IK 存在证明行走。 |
| run | 部分/未过速度交接 | 位置阶跃和侧向后仰已消失；腾空取消丢失速度 | front/left/right/back 实图；其余 N | 连续 sin 高度已改善。给 root_y 同源导数并让飞行时长/加速度一致；需要更清晰的前落足→支撑后蹬，而不是提高抬膝频率。 |
| wave | 通过*（front） | 肩肘掌起抬/摆动/回收可读；取消连续 | front 直接*；其余 R 未过 | 保留正面专用臂/掌和遮挡，修方向入口即可；八方向手势本体未验收。 |
| bow | 通过*（左侧本体） | 自然结束 pitch 已归零；极值 cancel 眼皮 1→0 瞬开，未完全过 | 左/右路由语义明确；front→left 实图 R 未过 | 腰颈前倾成立。把动作眼皮量也作为可回收通道，约 .12–.18s；不再用全局闭眼强锁 pitch。 |
| shiver | 通过*（轻微局部抖动） | 头/肩小幅高频抖，足稳定；结束/取消连续 | front/front-left/right 实图；背向 R 未过 | 维持局部反向补偿。320px 下比较轻，需要强化时增加肩肘分量，不抖 root。 |
| flap | 未过完整扑翼 | 有短跳/收腿/着地；全身取消改善，尾仍未过 | front/front-left/right 实图；背向 R 未过 | 六次整片翼根摆动配一个短跳，缺下拍推升与回收拍。最低需要翼根/翼肘/翼尖相位差，翼膜可变形或相应源片；不能只转整翼。 |
| dance | 未过协调编排 | 双手和踏步均可见；结束/取消连续 | front 直接*；其余 R 未过 | 手臂现在两周期/3.4s，腿仍 1.7Hz，独立相位无明确乐句。用共享 beat 安排承重脚、跨步、手势峰值和收足；现有骨链够用。 |
| tilt-left | 通过* | 颈部左倾可读，结束/取消连续 | front-left 直接*；其余 N | 保留颈根旋转。未宣称所有背向纹理同等通过。 |
| tilt-right | 通过* | 与左倾可区分，结束/取消连续 | front-left 直接*；其余 N | 同上；维持角色方向语义。 |
| raise-left | 通过*（front） | 解剖左臂在画面右，起抬/保持/回收成立 | front 直接*；其余 R 未过 | 专用肩肘腕链保留；无需为此重画全身。 |
| raise-right | 通过*（front） | 解剖右臂在画面左，与左手可区分；取消连续 | front 直接*；其余 R 未过 | 同上；背向左右手未作视觉外推。 |
| raise-both | 通过*（front） | 双臂可读，所采肩肘/手掌未见脱接，取消连续 | front 直接*；其余 R 未过 | 保留现有臂链；手臂穿头发的遮挡需继续以大图验收。 |
| point | 通过*（默认指向本体） | 抬臂后食指方向可读；本轮腕/掌序列未再见明确双掌；取消连续 | front 直接*；back-right→front 实图 R 未过 | 默认方向本体可用；真实气泡位置绑定、极近/极远目标、遮挡未测，不据 setPointTarget 存在宣告互动通过。 |
| carried | 部分 | 上方 anchor 悬挂、6秒保持成立；释放能全身落地。双臂长时水平伸开仍像飞机 | front/left/right/back 实图；其余 N | 最低是抓点→肩受力→臂腿下垂/轻摆。保留 anchor，调臂到放松下垂，抓点/拖速另做实际 UI 验收。 |
| land | 通过*（屈膝及状态）/尾边界未过 | 取消和再次取消不再重悬空；全身接触交接改善，尾接触仍切形 | front-left 从 carried 直接*；其余 N | 保留唯一 fall/body_return 所有权。下一项先修尾世界接触与空中 face request，勿恢复只混合腿/root 的旧分支。 |
| toss | 未过“受抛”语义 | 是带倾角的高跳，仍主动先蹲；普通取消全身着地改善；背向空中切表情失败 | front/left/right/back 本体实图；背向表情入口明确失败 | 从释放高度/速度进入受抛段，而不是复用跳的蓄力；所有 face/turn 请求应等接地或保留弹道，不归地再重播。 |
| pet | 通过*（固定反馈） | 轻低头/偏头、头发回应和开心淡回；结束/取消连续 | front-left 直接*；背向 R 未过；其余 N | 当前可作为“被摸后的短反馈”。任意接触位置跟随未验收，若需要再接触点驱动。 |
| poke | 通过*（固定反馈） | 局部退让、惊讶和回落可见，足没有随整图横滑；取消连续 | front-left 直接*；背向 R 未过；其余 N | 可保留固定反应；触点方向到 recoil 符号的绑定属于未验收互动范围。 |
| look-back | 未过连续回眸 | 单一头片消除了半透明双头，但 rear→profile→quarter 仍跳剪影；取消也经过离散切片 | 前侧到后侧 R 未过；后侧本体亦未过 | 颈根、耳、下巴和后发需注册；每个阈值前后投影对齐，补遮挡/中间头角度，不能以三个头片的硬选取视作连续转头。 |

## 旧漏洞修复结果

| candidate-1 问题 | candidate-2 实测结果 | 限制 |
|---|---|---|
| land 吸震时 cancel 重播旧 fall、5秒后仍悬空 | **已修**。.325s 取消及双重取消均归地，fall 释放 | 不外推所有动作替换；新的空中 face request 见下文 |
| jump/toss/carried fall→land 双臂瞬收，toss root_x 跳零 | **已修所采边界**。碰地前后 .001s 双臂、root_x 已平滑接续 | 尾状态开关仍有可见跳形，不能称整个轮廓连续 |
| run root_y 0/-12 阶跃 | **位置连续已修** | vertical_velocity 未随曲线更新，取消仍失败 |
| 左右侧 run 后仰 | **已修所采方向** | 不等于步幅/世界支撑足已验收 |
| bow 自然结束 head_pitch 7→0 | **已修**。1.6999/1.7001s 均接近0 | cancel 眼皮仍立即从闭到开 |
| profile 摇头/张望忽略 yaw | **已修小角度表现** | 只采 left/right 小范围，不接受大幅透视外推 |
| sit 悬坐、脚在承重时同步前滑；stand 直接倒放 | **主要路径已修**，终态贴地、收足后起 | 裙的半透明过渡仍未过；脚世界轨迹/碰撞不是本轮全量测量 |
| sleep 取消闭眼立即弹开 | **已修**，短暂逐睁后起身 | 继承坐裙过渡，不是睡姿整体验收 |
| turn/spin 整身交叉淡化双人影 | **双影已消除，连续旋转未修** | 当前是整身硬切；须分别记录，不能把“无双影”当通过 |
| point 多掌/指向不清 | **默认方向实图已改善，所采未再见明确双掌** | 实际气泡目标及其极值未测 |

## 确定缺陷、根因及可执行修法

代码行号均指上面冻结目录下的 `linux/gpt_niang_linux/model/`。

### P1：背向空中 face request 抢走弹道并重播动作

证据：[rear-toss-expression.png](../../test-results/review-pass-3/motion-fix-2/rear-toss-expression.png)，`deep-boundaries.json` 同名项。

复现：`set_view('back')` → `play('toss')` → advance .735s → `set_expression('happy')`。

| 时点 | action / pending | root_y | airborne |
|---|---|---:|---|
| 请求前 | toss / 空 | -165 | True |
| 请求后0 | turn / toss | -165 | False |
| +.07s | turn / toss | -82.5 | False |
| +.14s | turn / toss | 0 | False |
| +.6s | toss / 空 | 0 | False |
| +1.1s | toss / 空 | -103.53 | True |

`motion.py:139–149` 的 `_consume_face_request()` 无条件 `play('turn',keep_air=True)`，绕过 `play():168–173` 的空中落地链；`body_return` .14秒把空中 Pose 混到地面 turn，最后 pending 从头播放 toss。图片明确是先归地再跳一次，不是观察者误读。

**最低修法：** 非 carried 的空中动作/现有 fall 期间只保留 face 请求，落地后消费；或把转向做成弹道之上的独立朝向通道。不要将旧动作 ID 当成从头重播的 resume。若采用延后方案，应保留 expression/speech/listening 的各自请求撤销语义；carried 的持续悬挂可以单独处理。最小回归应覆盖此序列、背向 falling land、speech/listening 两入口，以及中途撤销请求；需要再次实图查看，不只看 pending 为空。

### P1：run 只有连续高度，没有同源速度

证据：[上升取消](../../test-results/review-pass-3/motion-fix-2/run-cancel-0.41.png)、[下降取消](../../test-results/review-pass-3/motion-fix-2/run-cancel-0.49.png)。稳定循环的 phase=.41/.49，有限差分实际 root_y 速度约 -752.93/+752.93 model px/s，Pose.vertical_velocity 均为0。两次在 root_y=-3.708 取消后却生成完全相同的从静止下落：+.016s 为 -3.555、+.05s 为 -2.208。

`dynamics.py:85–88` 只写 sin 高度，没覆盖开头重置的 vertical_velocity。`motion.py:171–173` 恰好使用该值启动 fall。最低应让高度及导数同源，但不能机械补上 ±753 就结案：现有飞行段只有 .1/2.1≈.0476s，12高度所隐含的加速度很大；切到 fall 的1200加速度会使上升取消飞得更高。应选同一物理曲线/加速度，或在剩余飞行段按位置、速度连续交到着地准备。验收包含上升、顶点、下降取消，不能只挑顶点（其速度本就为0）。

### P1：尾接地 soft-limit 被 airborne 布尔开关控制

证据：[tail-contact-boundaries.png](../../test-results/review-pass-3/motion-fix-2/tail-contact-boundaries.png)。jump t=.2999/.3001（离地）及 .9599/.9601（落地）仅相差 .0002 秒，尾中段和尖的曲线仍明显突变。carried 取消触地前后 .001 秒亦有小幅形变切换。

`render.py:554–558` 只在 `not pose.airborne` 时应用 `cy>894` 的指数限位；空中时整条曲线突然恢复未限位形状。该处也没把 painter 后续 root_y/root_angle 计入地面判定。最低修法是在完整世界变换后对尾外轮廓做连续地面约束，再反算局部网格；至少应连续混合接触权重，且由实际高度/接触距离决定，不以 airborne 布尔切整条尾。约束要包括尾厚度与尖端切线，不能只截中心线造成尖端旋转。

### P1：turn/spin 去了双影，但仍是整身与头片的硬切

证据：[turn切点](../../test-results/review-pass-3/motion-fix-2/direction-cuts-turn.png)、[spin切点](../../test-results/review-pass-3/motion-fix-2/direction-cuts-spin.png)、[front-left→wave入口](../../test-results/review-pass-3/motion-fix-2/entry-front-left-wave.png)。切点前后仅 .002s；首个例子 .299→.301s 从前侧原身形变成正面另一套头身比例、服饰与脚位。尾虽按角度连续，头肩/身体/裙仍跳。

`render.py:479–485` 在 mix=.5 选其中一个 view。±12° head_yaw 和踏步没有注册其他部位。`_render_look_back():685–696` 也按 `int(position+.5)` 选择三个不同头片。最低修复应先把颈根、肩、腰/髋、足底、头部尺寸统一，然后对左右可见面与遮挡做小角度投影，并在需要处补中间角度源片；仍需逐一看切点，不接受把阈值改位置或加速播放当修复。若素材短期不足，可明确保留“分方向切换”的功能限制，但不能标为连续转身/回眸通过。

### P2：sit/stand 裙型交接仍有透裙和双轮廓

证据：[sit.png](../../test-results/review-pass-3/motion-fix-2/sit.png) 的 t=.500s、seat≈.684 格能直接看到透明换裙；[lower-sit.png](../../test-results/review-pass-3/motion-fix-2/lower-sit.png)、[lower-stand.png](../../test-results/review-pass-3/motion-fix-2/lower-stand.png) 显示脚路径与终态。骨盆下降和足路径已经合理得多；最终坐姿不再是上版悬坐。主要剩余问题是站裙被压展后与坐裙渐变相叠，中段看得到两套褶边/内部细节。

`render.py:597–603,636–649` 用 seat .62–.86 的 smooth alpha 在两张结构不同的裙之间换图。最低应让腰/髋附近保持一个实心外轮廓，用遮挡遮住腿根、把裙摆展宽纳入共同网格；需要可单独遮挡的前/后裙片时再补片。**不要恢复含旧腿、旧尾的完整 sit 图**，那会重新重复肢体。现有无腿尾坐裙可以保留为末态源片。

### P2：bow cancel 眼皮不是连续通道

`deep-boundaries.json` 的 `bow-cancel-lid`：left bow .85s 取消前 blink=1、eye_closed=True，取消后0s blink=0、eye_closed=False；全身姿态相同，脸立即睁开。`blend_pose():508` 不混合 blink，新的 sleep lid 缓冲只针对 sleeping，expression_from neutral→neutral 也不能补偿动作眼皮。

把动作生成的眼皮量与自然眨眼区分，cancel 记录当前动作眼皮并在 .12–.18s 归零；与 sleep/expression 的闭眼按明确定义组合。正常眨眼不必全部拖长。自然结束已修，本项仅指中途取消。

### P2：剩余运动设计差异

- walk/run：`dynamics.py` 的支撑脚局部 x=-root_x，摆动脚 sin(2πu) 又回原足位，只在画布局部处理。需要结合实际 item/window 运动验证世界足速；本轮未运行桌面窗口，所以不声称已实测窗口滑脚。最低跨步轨迹应有前落足、根前移、后蹬离地，侧裙要允许读出鞋和膝。
- carried：根 anchor 改善了悬挂原理，仍固定双臂60/-80度；如定位为自然拎起，应补受力肩与下垂前臂/足的轻滞后。这里只评价固定反馈，实际鼠标抓点未测。
- toss：仍共用主动蓄力起跳；受抛入口应接受当前高度、水平/竖直速度与角速度，释放时不能额外先蹲。保持 jump/hop 的主动起跳设计即可，不必为每项换全身图。
- flap：现有翼片绕根部 ±30度、6个周期，不形成翅肘/腕折叠；至少两段翼骨或可变形翼网格，下拍与抬升相位对应。
- dance：两次手势周期与1.7Hz腿步没有共同乐句，最低先编一个左右承重的四拍短动作，再安排肩、腕、头、尾的滞后。

## 后续视觉验收

先复核新的 P1 边界，再修资产相关转换；不需要再次用“动作 ID 都能执行”替代验收。保留已通过的屈膝链、坐站时序、睡眠保持、正面小幅点头/摇头和手臂链。

修后至少重拍：背向 toss 顶点切表情及 speech/listening；run 上行/顶点/下行取消；jump/hop/toss/flap 离地与接地前后；turn/spin 全部 .5 切点和六类方向入口；坐裙混合中段；bow cancel 眼皮。看实际灰底连续帧，确认足/尾接触、颈肩轮廓、遮挡与所有权同时成立。数值检查应附上位置与速度，不只 action 名称和布尔标志。

本报告保留 candidate-2 的失败记录；当前树后来收到的修复不自动追认为已通过。上一轮结果仍见 [candidate-1复核](PASS3-MOTION-FIX-RECHECK.md)，原第三轮设计要求见 [PASS3-MOTIONS.md](PASS3-MOTIONS.md)。
