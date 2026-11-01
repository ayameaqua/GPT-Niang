# 第三轮候选3：独立尾原画、普通动作与转向复核

**静态原画、侧面遮挡和普通接地已显著改善，但候选3仍有两个P1问题：新B主尾干被误分到刚性叶骨；整幅角色MLS转向又把正确原画压出折片和第二套半透明轮廓。** 另有深坐近根段缩短约34%的体积问题。主上下文已决定替换全身MLS转向；本报告保留该冻结版本的证据，不把尚未冻结的新方向方案算作已验证。

本轮只读候选3运行文件和素材；未改代码、角色图或提交。数值根正确的结论与实际表面问题分别记录。

## 1. 冻结基线和采样

- `linux/test-results/review-pass-3/candidate-3/linux`，182个冻结文件的聚合SHA-256为`61aec4317af11839c656ee1878617eb87fa9ccaa78d357aea671d43331cba711`；[逐文件快照](../../test-results/review-pass-3/rear-candidate-3/snapshot.json)。
- 仓库venv、冻结PYTHONPATH、Qt offscreen；.025s逐步推进。证据使用RGB32不透明灰底。
- 八向静态；五个侧后起始方向的run、jump、land、carried、sit、bow多时点；八组相邻视图混合0/.25/.5/.75/1；从B启动spin的实际时间线。
- 非转向密采样共**2,032帧**：land 0–.65s、walk/run 3–4.2s、sit 0–2s、jump 0–1.85s、bow 0–2.3s、carried 0–2s。动作会自动转向的帧记录实际view/motion；有视图混合的帧从普通接地扫描排除，另作转向检查。
- [八向静态完整／裸尾](../../test-results/review-pass-3/rear-candidate-3/static-eight.png)。[L动作](../../test-results/review-pass-3/rear-candidate-3/left-actions.png)、[R动作](../../test-results/review-pass-3/rear-candidate-3/right-actions.png)、[BL动作](../../test-results/review-pass-3/rear-candidate-3/back-left-actions.png)、[B动作](../../test-results/review-pass-3/rear-candidate-3/back-actions.png)、[BR动作](../../test-results/review-pass-3/rear-candidate-3/back-right-actions.png)。
- [动作记录与实际映射节点](../../test-results/review-pass-3/rear-candidate-3/records.json)、[地面扫描](../../test-results/review-pass-3/rear-candidate-3/ground-scan.json)、[根与骨段长度扫描](../../test-results/review-pass-3/rear-candidate-3/root-and-length.json)。

坐标为模型设计坐标，地面y=969。像素最低点测量包含整体root_y与root_angle，不把本地尾坐标当作世界接地点。

## 2. 已改善且应保留的内容

| 检查项 | 冻结候选3实际结果 |
|---|---|
| 五向原画 | L/R/BL/BR独立弧形和新轴向B均已装入。静态中未再复现旧R/BR腹侧背刺、旧B丝带自折叠。 |
| L/R遮挡 | mid之后在z4.2绘制，粗根保留裙后，头发层序保持；比整尾裙后只露紫叶明显改善。 |
| 新B静态 | 中央背脊、竖向粗段和低处回弯成立，紫叶位于后发下方；没有用旧侧U缩窄冒充背面。 |
| 叶片一般形状 | 单向小摆时多数方向保持一枚完整紫叶，原先沿尾弧压成小三叉的问题没有再出现。B的叶骨误收问题见第3节。 |
| 解剖根跟随 | 2,032帧中`_tail_mapping(restRoot)`与`_tail_geometry`中upper变换后的根误差为0。深鞠躬／拎起完整合成也未见新断根。 |
| 接地边界 | 所有普通扫描帧的alpha>128轮廓均高于969；全局最低余量11.5单位，出现在实际FL坐姿过渡。旧run近落脚的airborne开关穿地未再复现。 |

[接地最接近地面的帧](../../test-results/review-pass-3/rear-candidate-3/ground-boundaries.png)中红线为969。代表性最差余量：L land28.17、run31.50、jump28.17；B land/run均16.50。B jump一行的最差值落在尚未起跳的转向起始帧，**不是背面跳跃已实现的证据**；具体实际方向在JSON里。

尾地面现在按实际世界Y处理，没有airborne布尔开关。当前扫描没有触发穿地，也没有必要把旧候选2的接地失败继续记为本轮未修。

## 3. P1：新B主尾干被误判为刚性叶片，普通动作产生折边和鼓包

位置：冻结`model/render.py:648–675`，尤其662–664附近的叶骨归属条件：

```python
if dx*leaf[0]+dy*leaf[1]>=0 and hypot(dx,dy)<lengths[-1]*1.6:
    weights=[0.]*(len(lengths)-1)+[1.]
```

这是以叶根为圆心、半径为叶长1.6倍、再取朝叶尖的半平面。新B是窄竖U，回收叶片旁边就是向下的主尾干。这个几何区域把主尾干mid也包括进去。像素随后随叶骨，已经计算出的主干mid节点却仍被作为cage锚点使用。

[背面裸尾放大](../../test-results/review-pass-3/rear-candidate-3/back-skin-closeup.png)可见：land有局部折边，run3.525s和carried.75s粗尾中段出现突起、宽度突变。完整角色的一部分被长发遮住，不能以遮挡作为表面正确的证据。该问题不依赖转向MLS，普通动作就会发生。

在真实白尾实心区域取探针，源UV约`(.6297883,.4719648)`，alpha=253；它位于root→mid段约82.956%处，恰好跨过上述叶片圆形归属边界。两侧源点只相差**.002796设计单位**，映射却产生以下不连续：

| 动作／时间 | 相邻源点映射距离 | 实际mid像素与posed mid差 |
|---|---:|---:|
| idle 0 | 3.6898 | 3.4790 |
| land .325s | **22.2651** | **16.7112** |
| run 3.525s | 17.0858 | 15.4695 |
| carried .75s | 11.5239 | 10.5402 |

land .325s的具体位置：圆外点映到`(439.6287,818.9739)`，圆内点映到`(437.9178,796.7746)`；正确posed mid为`(442.6345,837.0157)`，实际mid像素却映到`(441.3213,820.3562)`。详见[leaf-ownership.json](../../test-results/review-pass-3/rear-candidate-3/leaf-ownership.json)。

**可执行修复：** 为每片建立真实叶区域mask或源多边形，不再由全方向统一的圆圈和朝向半平面判定。新B的610×1391裁片中，紫叶＋接合白颈位于约`x=0..245,y=780..1165`，即`u≤.40,v≈.56..84`，可作为第一轮局部区域；误收主干探针u≈.630、mid u≈.654都应排除。最终切面沿真实细颈，接合处保留小范围平滑权重，主尾干权重连续。

**验收：** 用同一实心探针跨边界不再出现宏观位移；root/mid/low/thin的可见纹理跟随各自节点，紫叶内部仍保持刚性；B land/run/carried放大裸尾无折边、鼓包或鳞片突然转向。仅移除全身MLS不会修掉此问题。

## 4. P2：深坐近根段轴向缩短约34%，原图变为短厚双鼓包

[深动作完整／裸尾对照](../../test-results/review-pass-3/rear-candidate-3/deep-root-closeup.png)的FL sit1.3s、2.0s显示：白尾近根长斜段压成横向厚块，腹侧出现双鼓包。完整角色因裙片覆盖，问题比裸尾轻，但尾巴并未保持近似固定体积。

位置：`render.py:629–645`的节点生成只把根位移乘`follow=(1-t)**2`加给后续点；`kinematics.py:61–77`又按新的骨段长度缩放源片轴向。它不是固定骨长的转动链。

从L触发sit，t=1.075s实际已经是FL，seat=.63898：root→mid从186.188缩到122.232，**缩短34.35%**。到2s深坐仍从186.188缩到129.224（缩短约30.6%），根由(425,683)移到约(405,862.800)。[seat-compression.json](../../test-results/review-pass-3/rear-candidate-3/seat-compression.json)记录最坏时点。

这是大幅坐姿变化，并非“尾巴小幅摇摆”的等比范围。建议在深坐时用固定段长／允许有限投影缩短的链解，把剩余长度转为侧向收弯；若当前源姿态无法容纳，补坐姿尾差分。不要通过加厚截面或把坏形藏进裙片解决。一般鞠躬中段只有小幅长度变化，本轮未见同等级体积问题。

此项优先级低于B叶权重和转向；不应因本节而推翻静态新原画。

## 5. P1历史：整幅角色MLS对齐后混图，尾轮廓仍折叠／双影

主上下文已明确将替换这条转向路线，本节仅记录冻结候选3的实测。

位置：`render.py:496–512`。转向先把两套完整角色渲染为图片，再把包括头、肩、脚、尾六点的全身cage映射到共同位置，以24×32截图网格重塑，最后混合两张图。**当前不是只混尾材质，也不是只改变某个尾关节。**

[关键尾转向灰底表](../../test-results/review-pass-3/rear-candidate-3/critical-tail-turns.png)、[八组全角色转向](../../test-results/review-pass-3/rear-candidate-3/adjacent-turns.png)中：

- BL→B mix=.5时，原本正常的弧形白尾被压出三角斜片，叶片挤进粗尾；mix=.75时尾干和叶颈趋近细柱。
- B→BR mix=.25–.75仍可见另一套半透明宽尾边缘，叶片描边也发生错位。六点接近不等于整幅轮廓、背刺和叶瓣边缘重合。
- FR→F mix=.5把尾弧和叶片压成细针；mix=.75又从底部拉出斜片。不是合理的绘制背面，而是两套方向相反原画被共同目标压缩。
- 完整角色中衣发、袖口和后裙同时出现双轮廓，尾的可见性也随各图自身遮挡变化。尾纹理完好无法抵消这一层整幅图变形。

实际`Animator.play('spin')`从B出发同样复现：[spin尾时间线](../../test-results/review-pass-3/rear-candidate-3/spin-back-tail.png)、[spin完整角色](../../test-results/review-pass-3/rear-candidate-3/spin-back-full.png)。约.1s为B→BR中间态、.7s为FR→F细针、1.5s为BL→B折片。并非只在人工设置view_mix时才会出现。

建议与主上下文已选方向一致：尾从全身混图中分离，一时刻只绘制一套原画；方向间通过受限关节或补画的收尾姿态把叶与外露段收入真实衣发遮挡区，在遮挡处换源再展开。不能把BL/B/BR整幅尾面强压到一条共同弧上。新路线需另冻复核，本报告不作预先通过。

## 6. 方向路由和普通动作结论

L/R的jump采样保持原侧向；三个后向请求jump会先转到FL。sit全部转FL；bow按所在侧路由L/R。run、walk、carried、land在侧后方向保持请求视角。实际路由已写入动作记录，不把后向请求成功等同于后向动作已经实现。

非转向侧后根连接本轮可保留：L bow.8s根从(475,683)到约(511.639,671.175)，R相应到(338.361,671.175)，均跟随upper，完整图没有源根从臀后漂离。B carried.75s根在(425,683.287)，也未出现旧漂根；但主干仍受第3节叶权重误收影响。

验收优先顺序为：先修B真实叶mask和连续权重，再复查普通land/run/carried；深坐保体积另处理；新的单素材转向独立冻结检查。保留已通过的五向原画、侧面分层、实际世界接地和upper根绑定，不需要再退回直片投影。
