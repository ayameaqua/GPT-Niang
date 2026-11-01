# 第三轮动作审查：C8 定向物理复核

日期：2026-11-01。**本轮指定的三个旧故障，在实际 API 路径与所列实图中通过修复复核。此结论不代表 C8 整体可交付，也不撤销转向材质重影的未通过结论。** 本轮只查空中动作替换/重播、carried 释放 toss、sit/stand 的靴长问题，不重跑 30 动作或转向组合。

固定快照：[candidate-8/linux](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/candidate-8/linux)。使用实际本机 Coopanion 资源，仓库 venv、offscreen Qt、冻结树 PYTHONPATH。快照父级 `snapshot.json` 的 224 文件已逐一核对，审查结束仍无哈希差异。运行代码、测试、素材均未修改。

## 覆盖与结论

| 修复项 | 数值/状态覆盖 | 实际审图覆盖 | 结论 |
|---|---|---|---|
| jump/hop/toss/flap 空中重播与互换 | 4×4×3 飞行相位（.30/.525/.76）=48 案例；每例比较旧轨迹与速度、再次请求后的 owner/elapsed、落地后目标、最终退出 | 顶点 .525 的全部16有向组合，每组12时点，共192格；另12格 jump→toss→flap 二次替换 | 指定故障修复通过；没有 C7 的 .14s 拉回地面 |
| run 最后短弧→hop | phase .49/.499 各5种操作：保留、重复hop、改toss、cancel、cancel再hop；10案例 | 两组初次替换24格，三组再次操作36格；含接地±10μs及1ms附近 | 保留原剩余短弧及计时，通过；接地后身体继续收回，没有新增停空 |
| carried→toss | hold=.001/.05/.12/.5/3，5案例；检查初始高度、冲量、顶点、触地两侧、落地结束和延后1.4s | hold=.05/.5/3 各12格，共36格 | 从当前高度直接上抛，落地后不自动重播，通过 |
| sit/stand 及取消近靴压短 | 本体2条、各在 .216/.5/.72s 取消6条，共8条×1501时点，1ms间隔，12008姿态/24016腿记录 | sit、stand、stand .216 cancel、sit .72 cancel，各12格，共48格 | 原失败路径不再不可达，靴长比≈1；实图未复现近靴压缩，通过 |
| 不可达 free 足保靴分支 | 另将 C7 的6个真实失败 Pose 记录喂给 C8 renderer，强制触发分支 | 单独6格，显式标 `C7 captured / C8 renderer only / NOT C8 API` | 保靴分支有效；不保证非法目标不穿地，详见限制 |

**实际逐图查看：30 张灰底接触表，354 格；其中29张/348格来自 C8 实际 API，1张/6格为上述历史姿态注入诊断。** 并未穷举8方向×30动作×19表情。动作全部从默认 front-left 实际 API 进入；sit/stand 也使用真实路由与保持状态。没有强制侧脸表情诊断或转向混合验收。几何计算已按 C8 `_render_leg` 更新，包含 free sole 平移和 untouched-art bypass；没有直接沿用 C7 过时的靴长适配器。

诊断及所有证据：[motion-c8-targeted](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c8-targeted)。主脚本 `review.py`、完整 `records.json`、数值 `numeric.json`；补充脚本 `supplement.py`、记录 `supplement.json`。这些为 ignored 文件。

## 1. 空中重播与互换

[C8 motion.py:174](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/candidate-8/linux/gpt_niang_linux/model/motion.py:174) 现在只有 `carried` 是普通空中替换豁免；原 jump/hop/toss/flap 的飞行高度、速度、重力进入 fall。已经在 fall 内的请求只改 `after_land`，不重置原 fall 对象或 elapsed。

| 原动作↓ / 请求→ | jump | hop | toss | flap |
|---|---|---|---|---|
| jump | 通过 | 通过 | 通过 | 通过 |
| hop | 通过 | 通过 | 通过 | 通过 |
| toss | 通过 | 通过 | 通过 | 通过 |
| flap | 通过 | 通过 | 通过 | 通过 |

此表的“通过”严格对应覆盖表中的48数值案例及顶点16组实图，不延伸到任意方向/时刻/外部鼠标事件。

- 和未被打断的原动作相比，落地前 root_y 最大误差 `1.27530e-12`，vertical_velocity 最大误差 `3.41061e-12`。48例在落地前没有错误清掉 airborne；即时替换的高度没有跳变。
- 48例在剩余飞行40%时再次请求同动作，都保留原 fall owner 和 elapsed。落地后的 `.65s land` 收回完成，再执行排队动作；目标动作结束后没有残余自动循环。
- 顶点的剩余飞行分别为 jump .3300s、hop .2475s、toss .3850s、flap .4125s。实图中双臂、腿、倾斜身体连续收回到落地姿态；没有旧版“空中两靴忽然回地，随后重新蓄力”的抢状态现象。
- 二次改目标的具体例：jump .63s→toss，继续 .132s 后请求 flap。请求前后髋/膝/踝/足坐标最大差为0，fall elapsed不变，after_land由toss改flap；原飞行落地后只执行flap。

代表实图：[jump→jump](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c8-targeted/air-jump-jump.png)、[toss→jump](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c8-targeted/air-toss-jump.png)、[flap→toss](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c8-targeted/air-flap-toss.png)、[二次改目标](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c8-targeted/air-repeat-owner.png)。其余12组合均在同目录 `air-<原>-<新>.png`，已逐图看过。

实图结论仅针对替换过程；没有据此把 flap 的翼骨设计、ground toss 的艺术动作、全部落地力度标为完成。

## 2. run 最后短弧→hop

采用真实 run elapsed=`(2+phase)/2.1`，phase为 .49/.499。剩余原弧分别为 **4.761904762ms / .476190476ms**。初次替换与再次重播/换目标/cancel均保留这段原弧，身体的至少 .14s 收回不再占用 root 飞行时长。

- 10个数值案例没有 owner/elapsed 重启，没有原 root 轨迹偏离。
- .49重播hop、.499改toss、.499 cancel再hop，操作当刻完整髋/膝/踝/足坐标差均为0。
- 接地±10μs的所有这些关节，最大位移分别为 `.01889437`、`.01893309` 模型单位；没有隐藏在 root 连续背后的肢体硬跳。
- 接近1ms的已审图邻帧，最大关节位移为1.84434单位（.49 case，实际间隔.99ms）。身体随原快速短弧接地，继而保留一脚支撑收回另一腿；图中没有新增双脚突然下坠、腾空停留或地面蓄力被错误插到旧飞行中。
- .65s落地阶段后，hop/toss按最新队列正常开始。取消清队列，再请求hop又能入队，未重启飞行。

代表图：[.49→hop](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c8-targeted/run-hop-0.49.png)、[.499→hop](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c8-targeted/run-hop-0.499.png)、[.499改toss](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c8-targeted/run-operation-0.499-replace-toss.png)、[.499取消再hop](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c8-targeted/run-operation-0.499-cancel-then-hop.png)。这些是下半身诊断裁切图，头顶被裁是取样窗口，不是 renderer 新裁切故障。

本项不改变 C5/C7 已过的普通 run cancel 结论，也不延伸到转向材质或真实桌面位移速度。

## 3. carried→toss 直接释放

[C8 motion.py:187](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/candidate-8/linux/gpt_niang_linux/model/motion.py:187) 将 carried→toss 识别为 release；当前位置直接施加 `vy=-430`、`g=1200`，不把toss排到 `after_land`。

| carried保持时间 | 释放前/后root_y | 释放初速 | 到顶点时间 | 释放到地面 |
|---|---:|---:|---:|---:|
| .05s | -1.341634 / -1.341634 | -430 | .358333s | .719773s |
| .12s | -18.778577 / -18.778577 | -430 | .358333s | .757959s |
| .5s | -35 / -35 | -430 | .358333s | .790463s |
| 3s | -35 / -35 | -430 | .358333s | .790463s |

极早 .001s 时 carried root 尚为 `-3.29e-7`，fall 使用已有 `min(-1e-6,height)`，差 `6.71e-7` 单位；这是数值微偏移，不是可见的地面重置。5例都在下一毫秒立即上升，after_land均为空。`.5s`释放在+.14s为-83.44，顶点-112.041667，+.790463s接地；与 C7 的先下降到0再启动地面蓄力完全不同。

实图见：[早释放 .05](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c8-targeted/release-0.05.png)、[完整拎起 .5](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c8-targeted/release-0.5.png)、[持续拎起3秒](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c8-targeted/release-3.0.png)。释放前和当刻位置一致，悬挂姿态连续转为落地姿态；接地后有腿胯吸震收回，之后保持idle。延后1.4s仍没有自动再抛一次。

这里的“无重播”指没有新请求时不自动再次执行toss；用户明确再次请求空中动作，应仍按第1节排队，不能把正常用户重播也禁掉。

## 4. 早伸脚与靴长

[C8 dynamics.py:33](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/candidate-8/linux/gpt_niang_linux/model/dynamics.py:33) 从 seat=.22 开始伸脚。新路径在胯大幅下降时就拉开脚点，避免旧版“先将踝收进两骨链的内不可达圆，再伸脚”。

| 实际API取样 | C7 far/near靴长比 | C8 far/near靴长比 | C8目标髋踝距离 far/near | C8 clamp |
|---|---|---|---|---|
| sit .500s | .876441 / .870572 | 1 / 1 | 59.4612 / 60.8344 | 0 / 0 |
| stand .450s | .876441 / .870572 | 1 / 1 | 59.4612 / 60.8344 | 0 / 0 |
| stand .216s取消，再+.350s | .951340 / .678298 | 1 / 1 | 68.3459 / 71.0541 | 0 / 0 |

far/near 两骨内可达半径仍为25.87236 / 42.06076，并未通过改短作者骨长制造通过。8条轨迹/24016腿记录的靴长比范围为 `0.9999999999999990…1.0000000000000009`；最小内半径裕量+1.20845（sit .5s取消后+.310s，near），所有 ankle clamp=0。contact=True 时 sole 相对各自静态脚底基线漂移为0；free阶段足点均未越到该基线以下。这是各腿作者静态sole点的几何检查，不能等同于逐像素阴影/真实桌面接触求解。

[坐下](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c8-targeted/seat-sit-None.png)、[站起](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c8-targeted/seat-stand-None.png)、[旧最严重取消案例](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c8-targeted/seat-stand-0.216.png)、[坐下后段取消](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c8-targeted/seat-sit-0.72.png)均已实际看图。鞋跟与鞋筒没有旧版近靴突然缩成约2/3的现象；脚收放随骨盆路径连续。裙遮挡仍让部分腿段不可见，不能仅据遮挡下的整人图声称全部膝透视优秀；本轮通过的是指定的不可达/靴压缩故障。

## 5. 单独验证 free 保靴分支的限制

上述新 API 轨迹已避开不可达区，因此它们**没有实际触发** [render.py:685](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/candidate-8/linux/gpt_niang_linux/model/render.py:685) 的非零sole校正。为避免将“分支没执行”当分支通过，另取 C7 `motion-c7-visual/records.json` 中 `reach-stand`、`reach-sit` 的+.34/.35/.36s真实旧姿态，保留原始legs/pelvis/contacts，直接交给C8 renderer。

[历史失败姿态注入图](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c8-targeted/legacy-unreachable-free-boot.png)是**强制诊断，非C8实际API输出**。其中 stand .216s取消+.350s：近靴 clamp=27.78363，原 ankle→sole 比=.678298；C8令sole随actual ankle平移后靴长比=1，真实图中靴不再被压短。其余触发样本同样恢复1。

但这个分支只保刚性，不求地面约束：该历史样本修正后的near sole比静态地面低18.72455单位；+.34与+.36也有类似现象。**这不构成本轮新坐站 API 的失败**，因为新路径不产生这些目标。它是下一次改足目标/转向公共链时应保留的边界：不要认为contact=False就允许脚穿地；若目标不可达且校正会穿地，应在目标生成/骨盆求解层联合修正，再把同一刚性boot交给所有源纹理。不能再次通过缩鞋来补偿。

## 后续最低回归条件

保留本轮实际API案例及原失败时刻；以后改公共腿链/相机注册时至少重看 run .499→hop 的触地两侧、stand .216 cancel+.35、carried .5→toss immediate/+1ms/顶点/触地。数值需同时覆盖髋膝踝足和队列归属，靴长正确不能代替实图；历史注入样本应继续单独标注，不能混入实际API通过率。

转向全身材质重影已由主上下文另行判为不可交付，本轮未重新审图或改判。C8通过这三个定向修复，不等于所有动作、所有方向和全部材质都合格。
