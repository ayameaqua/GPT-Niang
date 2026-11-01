# 第三轮：Candidate 8 头部专项复核

**结论：头部整体仍不通过。** 原生角度的肤色、矩形额头缺陷已修好，取消动作的瞬间连续性有效；中间角度仍有严重几何条带和半透明双发纹。另确认了细横线的光栅覆盖原因、耳背黑块的取色原因，以及正／背面角耳半透明穿发问题。本轮不审核或认可 C8 的身体材质混合。

## 冻结与方法

- 冻结树：../../test-results/review-pass-3/candidate-8/linux。
- 校验时刻：2026-11-01 16:10:03 +08:00；snapshot.json 的224个文件全部匹配，未改冻结／live代码与素材。[校验记录](../../test-results/review-pass-3/front-fix-8/freeze-verification.json)。
- snapshot SHA256：ee36d1b7563871fdba2757038c816a8d031f486b089bf874c590d82093c615b4。
- head.py：5fe8d18430106f122282f8946915c287766c4bd489ee44da5ff2073506d70219。
- silhouette.py：da6e8fae91f8c2edc6883b0831a490b7a2a4c48cf388bcf6fc980f154726536b。
- 使用 live linux/.venv/bin/python，QT_QPA_PLATFORM=offscreen，PYTHONPATH 只指向 C8。灰底为 RGB32、#b8bec8，经真实 QPainter 合成；静态 clock=1，动作以不超过1/120秒的步长推进。
- 诊断目录：../../test-results/review-pass-3/front-fix-8/。其中 sampling.py、seams.py 只在独立进程内临时替换 draw_quad 作 A/B 对照，没有编辑生产函数。临时修改所得图明确标为 memory only，不当作 C8 的已修结果。

实际检查了12个原生头、12个材质中点、全部24个边界的±.01°对照，关键点另有±.1°；两侧耳的指定角区；五个有脸方向的19表情＋speech .85；五方向 nod 0–1.35秒；两侧 look-back 启动密集序列；7处取消前／0秒／后续返回。

## 项目判定

| 项目 | 判定 | 依据 |
|---|---|---|
| 12 native 的本色皮肤 | 修复有效 | 不再出现 C6/C7 的大白斑、旧刘海阴影及矩形额头边界；皮肤与清头壳相符。 |
| native 头顶／脸的 alpha | 仍有 P2 细条 | 未见新的大块头顶缺洞；细横条仍贯穿头发和皮肤，已通过内存 A/B 定位到逐三角 AA clip 覆盖。 |
| 3个旧 row-jump 位置 | 仍失败，P1 | 原150px级切换已消失，但12–26px/行的窗口／轮廓变化仍带动大片头发变形，实际 donor 图有折皱。 |
| 材质中点±epsilon | 硬切已消除，视觉仍失败 | 两侧图连续，但中帧有双卷发、双刘海线、半透明碎片和部分双下巴边缘。 |
| 眼／眉／嘴是否重复画 | 本轮未见整套双五官 | native差分和回眸帧中五官为单份；不能因此忽略脸轮廓／头发材质重影。 |
| 0°／180°角耳遮挡 | 旧硬换边已修，仍有 P2 | 非零面积耳叶不再瞬间换层，但两侧交界处出现半透明角耳穿过发壳。 |
| 135°／315°耳前背换面 | alpha连续性有效，耳背颜色失败 | 轮廓未瞬换；耳背取色产生纯黑块，157.5°明显露出耳根黑洞。 |
| 110–113°／244–248°耳投影 | 未再见旧二次等比缩小 | 当前耳叶姿态持续变化；周围坏发壳使整体转头仍不能通过。 |
| 五方向 nod | 本轮最低动作表达通过 | 有绕颈的可辨前俯，脸与发顶相对移动，侧面后脑与脸不同向运动；未见新增头颈脱节。保留材质／遮挡缺陷，不扩大为整头模型通过。 |
| nod取消 | 通过本轮样本 | front/left/right在.6秒取消，瞬间画面一致，随后恢复，没有头部突然跳回。 |
| look-back取消 | 状态衔接通过，视觉路径失败 | 两侧在.2/.55秒取消均保持瞬间画面，返回时仍经过扭曲／重影的中间头。 |

## P1：皮肤扫描线和 alpha 极值仍被用作大片发壳的几何边界

最直接证据是混合前的 donor 分离图：[78.75°](../../test-results/review-pass-3/front-fix-8/donors-78.75.png)、[123.75°](../../test-results/review-pass-3/front-fix-8/donors-123.75.png)、[303.75°](../../test-results/review-pass-3/front-fix-8/donors-303.75.png)。每图左列是第一张原画单独投影，中列是第二张单独投影，右列才是两者混合。左右两列本身已经弯折／横切，因此这不是仅由透明混合制造的视觉错觉。

head.py:140–153 的 row 仍直接采用扫描得到的皮肤窗口，RasterPalette.bounds 仍采用每行 alpha 最左／最右极值；_hair:208–229 将这些边界用于整条侧发和后脑的源／目标 UV 比例。某束卷发结束、下一束出现，或刘海遮住一部分皮肤，会改变扫描线极值；这种局部轮廓变化被传递到大片发壳，形成整排横向扭曲。区分 frame.face 与 row.skin 修掉了旧的150px级语义跳边，但没有解决此种绑定。

[逐行记录](../../test-results/review-pass-3/front-fix-8/row-jumps.json) 的关键位置如下。索引0/5为外轮廓，1–4为两皮肤窗口边界。

| 角度 | y相邻行 | 最大X变化 | 位置 |
|---|---|---:|---|
| 78.75° | 450→451 | 20.15px | 内窗口 index3；两行均有皮肤 |
| 123.75° | 343→344 | 12.57px | 右侧外轮廓 index5 |
| 123.75° | 310→311 | 约10.69px | 左外轮廓及闭合窗口一起变化 |
| 235° | 435→436 | 13.75px | 左外轮廓 index0 |
| 303.75° | 402→403 | 26.49px | 内窗口 index1 |
| 303.75° | 294→295 | 20.68px | 内窗口 index1，刘海横切位置附近 |

这些数值用于定位，不能反过来要求真实卷发轮廓处处平滑。问题在于局部 alpha／肤色边缘拖动了整块纹理，不是卷发自身不能有急弯。

建议将几何 cage 和 coverage mask 分开：用发顶、颞侧、颊／下巴、颈点等平滑解剖轴驱动空间映射；肤色连通 mask 与原 alpha 只决定覆盖区域。不能把逐像素刘海开闭、卷束终止当成全头横向缩放轴。对独立侧卷采用固定根／尖及内部束界约束，让它们保留自身形状。top/neck/bottom 共相位可以保留，但仅三个纵向锚点不够对齐下巴和不同高度的卷束。

验收：先关闭混合，只看每个 donor 投影；78.75、123.75、235、303.75都应无横向折线、上下段突然错开。单材质几何未通过前，不用混合降低错误的对比度。

## P1：统一窗口后的 premult 混合仍产生两套发纹与局部双轮廓

[12中点总览](../../test-results/review-pass-3/front-fix-8/midpoints-12.png) 显示：所有相邻材质中点都有不同程度的双线，123.75/236.25的后脑下发、56.25的前侧刘海、303.75的额发／下卷尤其明显。78.75的下巴边缘也没有完全重合。五官单独绘制成功避免了整套双眼，但不能抵消两张底图的不同下巴和发束。

head.py:316–324 的 albedo 把两张图投到相同的五个窗口，再作 premult color mix。窗口一致只对齐了区间边界，未对应内部发顶分缝、侧发根、每束卷发的路径与尖端；一张图透明处与另一张的实心卷发混合后还会得到半透明卷束。把最终 alpha 改为 max／union 最多减少透灰，不能消除两套线稿，不应视为根治。

建议：先为相邻头建立共享的发束拓扑和束内对应点；有同一根／同一尖的束可做局部形变与小范围材质替换。若两个原画中的卷束数量／遮挡顺序不兼容，需要修订对应原画或补兼容中间图，而不是继续对整幅发壳交叉淡化。头皮、脸、刘海和侧卷分别处理，避免把后脑纹理挤进脸区。

±.01°的所有中点对照已实际查看：[22.5–101.25组](../../test-results/review-pass-3/front-fix-8/mid-pairs-0.png)、[123.75–236.25组](../../test-results/review-pass-3/front-fix-8/mid-pairs-1.png)、[258.75–337.5组](../../test-results/review-pass-3/front-fix-8/mid-pairs-2.png)。这里没有旧硬切；两张几乎相同的图都处于坏的混合状态，所以 C0 连续不能证明视觉合格。12 native 的边界对照为 [组0](../../test-results/review-pass-3/front-fix-8/native-pairs-0.png)、[组1](../../test-results/review-pass-3/front-fix-8/native-pairs-1.png)、[组2](../../test-results/review-pass-3/front-fix-8/native-pairs-2.png)。

真实回眸证据：[左侧0–.504秒](../../test-results/review-pass-3/front-fix-8/back-left-look-back-dense.png)、[右侧同采样](../../test-results/review-pass-3/front-fix-8/back-right-look-back-dense.png)。左侧.1008秒125.64°为后发重影／波浪，.3024秒76.68°为侧卷双线，.4032秒54.36°为额发分段；右侧.1008秒234.36°、.3024秒283.32°、.4032秒305.64°分别复现相应问题。未认可画面中的身体混合。

## P2：细横条来自逐三角抗锯齿覆盖，整数源采样未完全修复

native正面和侧面的头顶、脸仍有细密水平线。对 silhouette.draw_quad 作了只存在于诊断进程的 A/B：

1. 当前 C8 的整数 source region 改为整幅 image 采样，细线几乎不变。
2. 移除 clip stroker 扩边，整头出现更明显的水平灰线。
3. clip stroker 从.5改1或2，正面／左侧头发和脸的细线明显消失。

证据：[采样方式对照](../../test-results/review-pass-3/front-fix-8/sampling-0.png)、[123.75°采样对照](../../test-results/review-pass-3/front-fix-8/sampling-123.75.png)、[正面.5/1/2扩边](../../test-results/review-pass-3/front-fix-8/seams-0.png)、[左侧扩边](../../test-results/review-pass-3/front-fix-8/seams-90.png)。第二个角度的粗几何条带和双线并没有被采样改变修好。

定位：每个三角形分别抗锯齿裁剪后，以 SourceOver 合成，邻接边的部分覆盖并不自动加成不透明。C8的.5离屏像素覆盖仍不足。可先让共享边有足够的实际像素覆盖，或采用一次性共享网格光栅化；本轮1–2的实验是可重复的局部修法。验收时必须同时检查 alpha外缘是否变厚、皮肤窗口是否被越界污染、不同输出尺度下的共享边，不能把扩大所有边当作无条件最终方案。

## P2：连续深度现在以半透明叠在头壳上，角耳可穿发

[0°边界](../../test-results/review-pass-3/front-fix-8/boundary-0.png)、[180°边界](../../test-results/review-pass-3/front-fix-8/boundary-180.png) 不再左右突然换耳，但在180°两角根区明显可同时看到角与后脑发线，正面耳与侧发也呈半透明叠层。

head.py:370–374 对整个部件使用单个 depth，depth=0 时 hidden=.5，再用半透明的 surface 做 DestinationOut。结果是把相交部分变半透明，而不是给出不透明头壳前／后的空间遮挡。38×26的根部椭圆重画只能盖一小圈，无法覆盖完整相交区。

建议使用部件局部深度与头壳深度／区域遮罩，让耳或角的可见边界移动。边界可抗锯齿，实心区域不应按全局角度渐成透明。0/180附近尤其需保证相交区域只有一个前景表面；不要为避免硬换层而牺牲实体遮挡。

## P2：耳背 UV 从透明区取了黑色，再套用原耳实心 alpha

157.5°可见耳根纯黑洞，见12中点总览。运行期分离材质：[ear-materials.png](../../test-results/review-pass-3/front-fix-8/ear-materials.png)、[像素记录](../../test-results/review-pass-3/front-fix-8/ear-materials.json)。该证据只留ignored，不发布私有原耳纹理。

- earLeft 原素材：alpha>200且RGB每通道<32的像素为0；生成的 earLeftBack 有342个，源裁片bbox x4–19、y22–59。
- earRight 原素材同类像素为0；earRightBack有15个，bbox x62–65、y38–46。

head.py:26–65 的 ear_back_material 用 srows 沿用有效行的bounds，但对应输出行的实际像素可能仍全透明。采样alpha<16后只向中心横移10%，未再次确认取到了非透明颜色，就复制RGB到原耳不透明alpha；根点负轴区间尤其容易落入空行，得到实心黑块。

直接修法：先将映射的纵向坐标落到最近有效行，再在该行寻找有效像素，或为耳背透明区域预先作最近有效颜色扩边。每次回退后重新验证alpha；完全找不到有效颜色时保留原耳RGB。保留当前同一alpha/root/tip的优点，不能把透明黑写入实心耳叶。

135/315前背颜色变化本身连续：[135°](../../test-results/review-pass-3/front-fix-8/boundary-135.png)、[315°](../../test-results/review-pass-3/front-fix-8/boundary-315.png)。连续性不等于材质无黑洞。指定投影区见 [左耳](../../test-results/review-pass-3/front-fix-8/left-ear.png)、[右耳](../../test-results/review-pass-3/front-fix-8/right-ear.png)。

## 点头、取消和表情的已验证范围

nod实际近景：[front](../../test-results/review-pass-3/front-fix-8/front-nod.png)、[front-left](../../test-results/review-pass-3/front-fix-8/front-left-nod.png)、[left](../../test-results/review-pass-3/front-fix-8/left-nod.png)、[right](../../test-results/review-pass-3/front-fix-8/right-nod.png)、[front-right](../../test-results/review-pass-3/front-fix-8/front-right-nod.png)。0/.15/.3/.45/.6/.75/.9/1.05/1.2/1.35秒呈一次可辨前俯与返回，最大俯仰时没有旧版整个头仅沿y移动的观感；脸和发顶相对运动，侧面后发位置随前俯变化。此最低动作表达可以认可，但本报告的发壳、根部半透明等缺陷仍须修。

7处取消均查看了取消前、同一时刻取消后、+.04/.08/.12/.18/.22/.30秒：front/left/right nod在.6秒；back-left/back-right look-back各在.2和.55秒。头部近景780×780范围在取消0秒均为完全一致的像素，[记录](../../test-results/review-pass-3/front-fix-8/cancel-zero-delta.json)。实际序列也没有忽然切回；代表：[正面nod](../../test-results/review-pass-3/front-fix-8/cancel-front-nod-0.6.png)、[左回眸极值](../../test-results/review-pass-3/front-fix-8/cancel-back-left-look-back-0.55.png)、[右回眸途中](../../test-results/review-pass-3/front-fix-8/cancel-back-right-look-back-0.2.png)。返回所经过的坏中间材质仍使回眸视觉失败。

五方向各19表情＋neutral speech .85已逐图查看：[front](../../test-results/review-pass-3/front-fix-8/faces-front-20.png)、[front-left](../../test-results/review-pass-3/front-fix-8/faces-front-left-20.png)、[left](../../test-results/review-pass-3/front-fix-8/faces-left-20.png)、[right](../../test-results/review-pass-3/front-fix-8/faces-right-20.png)、[front-right](../../test-results/review-pass-3/front-fix-8/faces-front-right-20.png)。皮肤改本片材质后差分更清楚，wink／单眼、泪滴、腮红与口形未见回归。静态20格不覆盖真实speech闭口间歇、外围accent或表情中断时序，本报告没有把这些未重测项目列为通过。

下一轮应先提交无混合的单材质中间头几何，再验证发束对应／局部材质转换；同时修复三个可独立处理的P2（裁剪接缝、实心遮挡、耳背取色）。保留已通过的本色皮肤和取消状态恢复。每一步仍以真实灰底图与连续动作验收，不能只用C0、无自交或脚本通过结案。
