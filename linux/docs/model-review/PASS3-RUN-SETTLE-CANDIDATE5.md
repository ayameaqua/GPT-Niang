# candidate-5：临接地 run 取消与收势定向复核

2026-11-01。**本次指定的修复通过所采样范围：C4 的亚毫秒并脚/抬胯已消失，原短弧保持正确；空中重复取消或替换待执行动作不重启 fall；接地后再取消/替换也未出现新悬空、穿地或硬归零。** 这是针对 run phase=.49/.499 的结论，不是 30 动作整体通过。C4 对头/身体转向硬切的失败判断继续保留，等待下一次专门复核。

只读冻结 `/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/candidate-5/linux`，真实本机 Coopanion 原图，经仓库 venv、Qt offscreen、DragonRenderer/Animator 渲染到 RGB32 灰底。没有修改运行代码或素材，没有提交。主上下文报告的 76 测试通过不是本报告的视觉依据，本轮没有重跑 30×28 全套。

## 覆盖与证据

本轮诊断目录：`linux/test-results/review-pass-3/run-settle-5/`，为 ignored 本地文件。`review.py`、`state.py` 可复现；`observations.json`、`state.json` 保存完整 Pose、fall owner、elapsed、队列与轨迹。常规 advance 不超过 1/60 秒，数值连续检查为 1ms，接触边界使用更小 dt。

**实际渲染并逐图查看 128 格：**

- `single-0.49.png`、`single-0.499.png` 各 16 格：取消后 0–5ms 的 1ms 邻帧、真实接地±10µs、16/40/80/120ms、settle 140ms 前后±10µs、180/350ms。主要看腿、骨盆、手臂与脚部近图。
- 两个相位各四张八格表：`repeat-air-*` 在原剩余飞行中点再次 cancel；`queue-air-*` 在同一点请求 wave；`cancel-ground-*` 在接地后 1ms 再 cancel；`replace-ground-*` 在接地后 1ms 请求 nod。每组看变更前、立即、1/16/70/140/300/800ms，覆盖自然回站或队列交接。
- `view-front/left/right/back.png` 各八格：phase=.499 的起点、接地±10µs、1/40/80/140/350ms。加上默认 front-left，共五方向定向实图；侧后脚部被裙/尾遮挡时，不能据此宣称所有鞋底像素已完整看见。

**仅数值/API检查：** 两相位从取消后 0–350ms 每 1ms 连续采样，各加接地±10µs；额外六组“cancel→cancel / wave→nod / wave→cancel”变更序列，跟踪到 2.1 秒。不是六组额外动画视觉通过，也未检查真实窗口平移下的世界脚锁、所有活动动作替换、空中主动改 jump/hop/carried 等特殊语义。

## 结果

| 检查项 | 结果 | 直接证据 |
|---|---|---|
| 原短弧与接地时刻 | **通过**。phase=.49 剩余 .004761905s，.499 剩余 .000476190s；地面 root_y=0，接地后 airborne=False，没有延长空中展示或二次大跳。 | 两张 `single-*`、完整 Pose/轨迹 |
| C4 亚毫秒收腿抬胯 | **通过修复**。接地时保留原 run 的腿和髋；远腿继续摆动后约 .14s 收回，而不是随残余 .476ms 弧归零。 | [single-0.499.png](../../test-results/review-pass-3/run-settle-5/single-0.499.png) |
| 接地±10µs | **通过所采样边界**。足底落到地面、近脚建立支撑，姿态无离散跳变；远脚仍在摆动是单足支撑状态，不是整人悬空。 | `single-*`、四张 `view-*` |
| .14s settle 结束±10µs | **通过**。腿偏移接近零再退出 settle，没有在分支结束处重新并脚或切髋。 | `single-*` 最后一行及数值 |
| 空中再次 cancel | **通过**。fall 对象和 elapsed 保持，瞬时 root/腿/臂变化均为 0。没有重新等待 .14s 或续出新飞行弧。 | [repeat-air-0.499.png](../../test-results/review-pass-3/run-settle-5/repeat-air-0.499.png)、`state.json` |
| 空中替换待执行动作 | **通过队列交接**。wave 入 after_land，不抢断；wave→nod 只替换队列，最终 land 后执行 nod；wave→cancel 清队列。 | `queue-air-*` 实图；多次替换由 `state.json` 确认 |
| 接地后再 cancel | **通过**。fall 清除，当前姿态由 .22s body_return 收回；没有复活飞行或悬脚卡住。 | [cancel-ground-0.499.png](../../test-results/review-pass-3/run-settle-5/cancel-ground-0.499.png) |
| 接地后改 nod | **通过所采替换**。从当前脚/髋姿态约 .14s 回到 nod 的站立基底，近脚继续支撑。 | [replace-ground-0.499.png](../../test-results/review-pass-3/run-settle-5/replace-ground-0.499.png) |
| 转向视觉 | **未重新验收；继续失败**。wave 在 land 后可能经过 turn；其队列能走到 turn 不等于中间轮廓通过。 | 沿用 [C4 报告](PASS3-MOTION-CANDIDATE4.md) |

phase=.499 的近图与数值：

| 取消后时刻 | root_y | pelvis_y | legFar.y | 接触 |
|---|---:|---:|---:|---|
| 0 | -.3769 | 12.9996 | -43.6004 | 双脚空中 |
| 接地后约 10µs | 0 | ≈13 | 仍约 -44 | 近脚支撑 |
| .001s | 0 | 12.9975 | -44.4314 | 近脚支撑 |
| .040s | 0 | 8.7759 | -57.7237 | 近脚支撑，远腿继续摆动 |
| .080s | 0 | 6.2501 | -34.1198 | 近脚支撑，远腿回落 |
| .120s | 0 | 13.6874 | -4.7019 | 近脚支撑 |
| .13999s | 0 | 18.7111 | -0.0000012 | 双脚接地 |
| .14001s | 0 | 18.7156 | 0 | 双脚接地 |

两相位 1ms 数值记录中，落地后不存在双 contacts=False 的样本。近脚模型 sole 的水平漂移约 1.14e-13、竖直漂移 0；远脚被标记接触后剩余移动最多约 x=.265、y=.985 个模型单位，来源是 `abs(leg.y)<1` 的接触容差。在正常尺寸实图中未看到由此造成的新脚滑或穿地。这里的 sole 包含 renderer 对应源片锚点及 root/leg 平移，是局部模型空间检查；不代表 PetItem 移动窗口后的世界空间足底验收。

phase=.49/.499 的最大相邻 1ms 远腿 y 变化约 .8544 个单位，骨盆 y 变化约 .2612，arm_base 变化约 .4627°；与 C4 在 .476ms 内强制消掉 43.6 单位抬腿和 13 单位髋位移明显不同。视觉上能看到支持腿与摆动腿逐步收回，而非只依赖这些连续数值判断。

`state.py` 在剩余弧 25%、50% 两点分别变更队列：六组的两次操作均保留相同 fall owner 和 elapsed，root/腿/arm_base 瞬时差为 0。wave→nod 最终只执行 nod；wave→cancel 最终不执行 wave。phase=.49 弧内位置误差约 1.7e-13；phase=.499 的后续 1ms 轮询已跨过弧尾，不能用该组轮询声称覆盖所有弧内位置，弧内证据来自 owner/elapsed 记录与前述精确边界图。

## 代码解释与剩余美术范围

冻结 `motion.py` 的 `play()` 在已有空中 land/fall 时只更新 after_land，不重置 elapsed；`pose()` 把姿态回收窗口改为 `max(.14, fall.duration)`，以继续推进的 run 姿态为 source，再按实际 flying 状态决定 root 与 contacts。接地后的再次取消走 body_return，符合此次复核结果。

仍可改善的一处节奏：短 run 停步沿用 land 的 48 单位、约 .325 秒达峰的吸震，骨盆先从约 13 抬到约 6，再沉到约 48；实图有“收步后再深蹲”的感觉。这是连续的二段动作，**不是本次旧瞬跳/悬空故障复发**。后续可按入射速度/高度调小 run 停步的吸震深度和时长，避免小跑停下与高跳落地同样重。无需为本次边界修复增加新素材。

C4 关于连续转向、步态世界速度匹配、翼拍、舞蹈、悬挂自然度等其他未通过/未验收结论继续保留。本轮没有重新裁定这些事项。

## 固定快照

以下 SHA-256 在采样前记录、报告前复算一致：

| 文件 | SHA-256 |
|---|---|
| motion.py | `3231cd1feade9623b604a73167f2121b5d37a1c266eb9a08bbf8b831890b09fe` |
| render.py | `523cb75872ef315f868ffa54382d4d31595ca5d93ea151d5bba94a98ba767556` |
| dynamics.py | `a21cdd5bda66340e12451ea7a662b66c7bcc771192c11122bfddf6847cedd9a2` |
| kinematics.py | `fead77dde73b0fb655e668aacc8d51662a845ee15404565711688e5be07e0b8d` |

唯一 tracked 产物为本简报；诊断只写 `run-settle-5/`。未修改运行代码或模型素材。
