# 第三轮动作审核：候选 10（冻结，只读）

审查日期：2026-11-01。冻结树：`linux/test-results/review-pass-3/candidate-10/linux`，224 个快照文件核对无变化。使用真实本机 Coopanion 原图、仓库 venv、offscreen Qt Renderer；未改 production、测试或素材。C11 的宣布修复不追溯改写本报告结论。

**结论：C8 物理/取消逻辑在 C10 中保持；恢复原生头、长发与服装没有把 jump/nod/run/sit 退回整图移动。30 项都有实际关键帧与极值取消图。C10 仍不能判全 V1 视觉通过：回眸后发/颈部合成有可见错误，转身只达到有限方向帧动画，强制旧 Pose 的旋转地面约束仍失败。**

## 覆盖与方法

- 已逐张看 53 张灰底接触表、556 个单元。其中实际 Animator 路径 51 表/546 单元；旧历史 Pose 6 单元和人为边界 Pose 4 单元单独标注，不冒充 C10 API 产生的状态。
- 每个动作 10 帧：起始、18%、所选极值、78%、102%、150% 时点，及极值取消后 0/.07/.22/.8 秒。wave 的 18% 与所选极值相同，因此不是 10 个独立时间点。另补每个动作取消后 2 秒，全部 idle 且双足支撑；sit/sleep/carried 的未取消序列确认保持。
- 额外看 front nod、left/right bow、BL/BR look-back、front walk/run 各 12 帧；sit/stand 及旧故障取消路径共 48 帧；carried 释放 12 帧；run .49/.499 → hop 各 12 帧；walk/run 一周期、shiver 一周期与 wave 的 .5–.741 秒区段各 12 帧。wave 补图是区段，不宣称完整手腕周期。
- 连续数值：48 空中重播/互换、10 个 run 边界操作、5 种 carried 持有时间释放、8 条坐站路径各 1501 个 1 ms 帧。数值用于检验约束，实际图用于判读关节与服装，不互相替代。
- 只读代码确认 `motion.py`、`dynamics.py` 与 C8 相同；逐图覆盖不限于代码确认，但**没有**穷举 8×30×19、全部动作替换对、所有鼠标拖拽速度，也没有逐像素验收所有被衣物遮住的关节。
- 图中某些头顶缺失来自专门放大腿脚的诊断 crop（原图 1024 后裁 190,410,650,610），不作为 Renderer 裁切缺陷。

脚本/原始记录：[native.py](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/native.py)、[numeric.py](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/numeric.py)、[floor.py](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/floor.py)、[finish.py](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/finish.py)、[numeric.json](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/numeric.json)。

## 30 动作逐项矩阵

以下每行均为“已实际采样”。“回收正常”只指本轮所选入口/极值取消序列，不等于全部组合通过。常规动作的本体达到基本可读门槛；标注未验收/失败处保留。

| 动作 | 本体运动与视觉结论 | 持续、结束、取消/入口结论 | 实图 |
|---|---|---|---|
| stand | 先收足、再抬骨盆；近靴不再压短 | sit → stand；中途取消仍完成站起 | [关键帧](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/native-stand.png) |
| jump | 蓄力屈膝、伸展、腾空、吸震均可读 | 空中取消/重播/互换续原 flight | [关键帧](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/native-jump.png) |
| hop | 比 jump 短且低，足与骨盆实际变化 | 同上；另核 run 临接地 → hop | [关键帧](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/native-hop.png) |
| look | 眼神/头部小转向可区分 | 回收正常；不是全身转向 | [关键帧](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/native-look.png) |
| turn | 8 原画方向帧＋踏步；有限帧成立 | 取消到邻近方向，尾回展开；连续转面未通过 | [关键帧](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/native-turn.png) |
| nod | 正面实看俯仰与五官投影，不只上下移 | 普通结束/极值取消均回收 | [关键帧](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/native-nod.png) |
| shake | 头 yaw 左右反向，身体支撑保持 | 回收正常；原画纹理的透视幅度有限 | [关键帧](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/native-shake.png) |
| spin | 方向帧顺序成圈、踏步/尾遮挡可读 | 取消邻近方向正常；连续 3D 未通过 | [关键帧](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/native-spin.png) |
| sit | 锁足下降后提前伸足，低座与单裙铺展可读 | 持续终态保留；取消先收足再起 | [关键帧](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/native-sit.png) |
| sleep | 坐低、闭眼/头垂与呼吸可读 | 保持不自行退出；取消闭眼与全身回收 | [关键帧](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/native-sleep.png) |
| dizzy | 眩晕眼和摆动明确 | 取消及自然结束眼部回收 | [关键帧](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/native-dizzy.png) |
| walk | 交替支撑、摆腿/鞋抬起，非整图左右移 | 步态一周期另看；取消回到双足支撑 | [关键帧](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/native-walk.png) |
| run | 交替支撑＋短腾空与手臂摆动明确 | 临接地反复取消、替换数值/实图通过 | [关键帧](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/native-run.png) |
| wave | 正面解剖左手抬至脸旁，手腕小幅挥动 | 回收正常；小尺寸挥动幅度偏弱 | [关键帧](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/native-wave.png) |
| bow | 左右侧均有躯干/头俯仰，眼闭后恢复 | 极值取消无旧 blink 长留 | [关键帧](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/native-bow.png) |
| shiver | 高频小幅抖动可辨，幅度很轻 | 一周期 12 帧另看；停止后稳定 | [关键帧](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/native-shiver.png) |
| flap | 翼根摆动与起落成立；主要仍是整翼根旋转 | 空中取消通过；缺肘/翼尖分段折叠，丰富飞行未验收 | [关键帧](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/native-flap.png) |
| dance | 双臂与交替步/摇身形成简化舞步 | 回收正常；不等同复杂舞蹈设计验收 | [关键帧](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/native-dance.png) |
| tilt-left | 向解剖左侧歪头可区分 | 回收正常 | [关键帧](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/native-tilt-left.png) |
| tilt-right | 与左歪反向 | 回收正常 | [关键帧](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/native-tilt-right.png) |
| raise-left | 正面角色左臂＝画面右侧，实际抬手 | 回收正常；未穷举遮挡/表情组合 | [关键帧](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/native-raise-left.png) |
| raise-right | 与左抬相反，非复用同一只手 | 同上 | [关键帧](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/native-raise-right.png) |
| raise-both | 双臂同时抬起 | 同上 | [关键帧](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/native-raise-both.png) |
| point | 指向手型与开放掌型不同 | 回收正常；本轮不重做逐指造型验收 | [关键帧](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/native-point.png) |
| carried | 锚定悬挂，腿下垂与双臂抬起 | 保持后取消落地；释放直接给向上速度 | [关键帧](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/native-carried.png) |
| land | 着地预备 → 吸震 → 支撑恢复 | 从 carried 入口含前置 flight，非 duration 后立即 idle | [关键帧](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/native-land.png) |
| toss | 向上抛物线、落下吸震成立 | carried → toss 从当前高度释放；无重播 | [关键帧](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/native-toss.png) |
| pet | 头部接受抚摸的倾斜/闭眼反馈 | 结束与极值取消回收 | [关键帧](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/native-pet.png) |
| poke | 短缩身/表情反应可读 | 结束与极值取消回收 | [关键帧](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/native-poke.png) |
| look-back | 背侧身体固定，12 头帧回眸可读 | 状态通过；BL/BR 旧后发上段与 BR 暖色颈块仍使视觉失败 | [关键帧](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/native-look-back.png) |

## 物理证据与边界

**空中重播/互换保留当前 flight：通过本轮 48 数值案例。** jump/hop/toss/flap 四源×四目标×三个空中时点：root 相对原弧最大误差 1.2753×10⁻¹² px，vy 最大误差 3.4106×10⁻¹² px/s。反复操作保留 owner/elapsed，after_land 排队，旧飞行与落地完成才启动新动作。此处是数值全 48，不声称每一对另绘了完整图；本轮实际图覆盖 4 本体取消与 run→hop、carried→toss。

**run 临接地没有新增悬空停留：通过。** phase .49/.499 剩余旧弧分别 4.761905 ms / .476190 ms；5 类操作（不再操作、再次请求、替换、取消等，具体见 JSON）均保留原弧。root 误差 0；接地 ±10 μs 的髋/膝/踝/sole 最大位移约 .0189 px，不只核 root。实图没有鞋先停半空而身体继续坠落、没有接地后再补一次空中跳动；落地后支撑腿先接住，另一腿有支撑地回收。[.49 图](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/run-hop-0.49.png)、[.499 图](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/run-hop-0.499.png)、[完整跑步周期](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/cycle-run.png)。

**carried→toss 直接释放：通过。** 持有 .001/.05/.12/.5/3 秒均立即进入向上速度 −430 px/s、g=1200。持有 .5 秒时 y=−35，释放顶点 +.358333 秒/y=−112.04167，落地 +.790463 秒；从当前高度起飞，无地面蓄力、无自动重播。接地后吸震并最终 idle。[释放 12 帧](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/release.png)。

**坐站和旧压靴问题：正常路径通过。** 8×1501=12008 个姿态、24016 个腿采样，boot 比例为 1（浮点误差量级），无 ankle clamp；最小内侧可达余量约 +1.20845 px，支撑 sole 漂移为 0。鞋先随伸腿抬起，stand 收足后再起身；旧取消窗口也未复发近靴压成半长。衣裙遮住部分大腿/膝，仅能验可见鞋、骨盆路径与数值关节约束，不能据此宣称完全正确的膝部美术透视。[坐下](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/seat-sit-None.png)、[站起](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/seat-stand-None.png)、[stand .216 取消](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/seat-stand-0.216.png)、[sit .72 取消](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/seat-sit-0.72.png)。

**free 足地面修复：未旋转旧姿态通过，旋转边界失败。** 将 C7 真实记录的 stand .216 取消后 .34/.35/.36 与 sit 对应旧 Pose 注入 C10 Renderer；直接捕获 Renderer 传给 skin_point 的 rest/posed 链，避免只用诊断公式自证。旧 near .35 在 C8 的 +18.72455 px 穿地，在 C10 为 0，boot 比例仍 1。可是给同一旧 Pose 强制 root_angle=+12°，near sole 仍低于世界地面 9.56060 px；−12° 时 far 低 12.50542 px。这是 **Renderer 防御边界缺陷，不是已重现的正常 C10 API 故障**。正常本轮 468 关键帧没有触发 floor fallback、压靴或 free sole >1.5 px 穿地标记。[历史图](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/floor-historical.png)、[强制边界图](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/floor-stress.png)、[真实渲染骨链记录](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/floor-records.json)。

根因在冻结 `render.py::_render_leg` 的 `floor=restSoleY-root_y` 与水平圆交点，漏了 root_angle/root_anchor。最低修法是将世界地面逆变换成局部直线，与同一可达半径求交，sole 始终 = actualAnkle + rigidBootVector；contact 足不能为了修 free 足而挪开。C11 需重测 ±12° 与实际原路径。固定 hip/有限骨长下完全无交点的任意非法 Pose 不在本轮通过承诺内。

## 原生材质恢复后的视觉结论

1. 原生头、长发与衣服纹样保住；本轮普通 nod/bow/jump/run/sit 图未复发 C9 行拉伸条带，也未出现 C6 公共网格回贴原点错位。front nod 的脸/头俯仰能读到，side bow 的头颈/躯干配合也能读到，不是只移动整张位图。[正面点头](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/detail-nod-front.png)、[左侧鞠躬](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/detail-bow-left.png)、[右侧鞠躬](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/detail-bow-right.png)。
2. **C10 回眸合成仍失败。** 背侧长发旧图上段短卷与新朝向头相叠，回眸时出现不随头附着的发段；BR 原生无脸头还露出独立暖色颈块。可见于转身经过 BR 与 look-back 背右序列。状态和回收正确不使此项视觉通过。修法应局部清理无脸头的旧颈块，并对 BL/BR 后发旧上段做有边界的 mask；不能再全头/全身跨视角透明混合。[BL 回眸](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/detail-look-back-back-left.png)、[BR 回眸](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c10/detail-look-back-back-right.png)。
3. turn/spin 已明确是 8 原画方向帧；轮廓/材质在帧边界有可见切换，头回眸为 12 帧。有限帧产品定义可以成立，但本报告**不把它改名为连续 3D 或连续转面通过**。尾保持遮挡再展开，未看到旧全身 alpha 混合双脸/双鞋。需连续转面时应另立轮廓与语义 UV 验收，不能只加帧混合。
4. 动作设计仍有保留：flap 主要为翼根驱动整翼，没有新翼肘与翼尖折叠；dance 是简化舞步；wave 在 320 观察尺寸手腕摆动偏小；shiver 高频而幅度轻。这些不是状态机失效，也不能等同所有原包动画质量已经匹配。

## 性能与后续验收

384 渲染、每动作 16 个后续样本的中位数：nod 24.68 ms、jump 32.90 ms、run 31.43 ms、turn 19.11 ms、spin 24.72 ms。run 最大 46.70 ms，turn 一次达 342.60 ms（方向素材/cache 转换路径，尚未单独归因）。本机同进程测量并非隔离性能基准；不能用 turn 中位数掩盖首遇方向卡顿，也不承诺 60 fps。

C10 保留的问题应分别验收：C11 地面直线修复要用旧 Pose 0/±12° 实际 Renderer 链与图片核验、boot 比例≈1、sole 世界地面残差≈0，外加正常坐站/取消与临接地路径无回归；mask 修复要看 BL/BR 回眸与返回、固定背侧原画形象。全 V1 仍需方向/表情专项、性能和真实桌面交互验收；本报告只提供动作专项证据。
