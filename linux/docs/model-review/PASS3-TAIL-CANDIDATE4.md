# 候选4尾巴与后向复核

候选4仍不能判为修复完成。五向原画和普通动作定长链可以保留，新的坐姿尾骨根点也正确；剩余主要问题是 **B 尾干仍会误绑到叶片段**、**三个后向的转向层级瞬切**、**B 落地时尾弯被逐顶点压平**。旧圆形叶权重边界和 MLS 双尾已消失，但这不等于叶片归属及转向表现已全部正确。

## 审查对象与方法

- 固定实现：`/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/candidate-4/linux`。
- 191 个冻结文件的路径／SHA-256 集合摘要：`f2d1c766e15d6e5b9543cb39afadfe917d5c2d4ed35f6ca88ef7059ebe47ce9e`。逐文件信息见诊断目录 `snapshot.json`。
- 诊断目录：`/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/rear-candidate-4/`。
- 使用 live venv、冻结 PYTHONPATH、Qt offscreen，渲染 768×768，再合成到不透明 RGB32 灰底。检查完整角色与隔离尾巴。普通动作以 .025 秒步进；转向以 .01 秒步进并精确补齐 .005 等目标时刻。
- 静态检查 8 向，重点 L、R、BL、B、BR。普通动作采样 walk、run、jump、land、sit、bow、carried。转向／spin 共 260 帧；另外 3211 个无转向收尾的普通姿态用于根和定长链数值复核。
- 对比诊断仅在独立进程中临时替换绘制函数／参数；未改冻结或当前运行文件、PNG、JSON 素材。更密网格、关闭地面钳制、源区域 gate 都是归因实验，不是已应用修复。

## 已确认改善及其边界

### 原画、根与定长链

L/R 的粗尾根、弧线、背刺边和单紫叶保持原画方向；BL/BR 的外弯体积稳定；B 的轴向窄构图和低位紫叶也可保留。没有复现早期统一 ribbon 的背向内折，也没有静态双叶。

![八向完整角色和隔离尾巴](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/rear-candidate-4/static-eight.png)

普通姿态的正确根目标是 `upper.map(coccyx_point(camera_angle or view_angle, seat))`。3211 个有效样本的尾骨目标误差与最终映射 root 误差均为 0；五段长度最大相对变化为 `2.22e-15`。这里排除了 `turn_tail>0` 与 turn/spin；收尾阶段主动缩短的隐藏链不能混入普通 FK 的定长统计。

深坐最终实际为 front-left。seat=1 时局部尾骨 `(482.27565,652)`，upper 后根 `(462.27565,831.85683)`，与实际根完全一致。五段原长／姿态长分别为约 `186.188、143.169、60.571、37.950、80.433`，没有候选3的 34% 轴向压缩。原先坐垫样紫条在本轮实图中也没有复现。`native-fk-and-ground.json` 为本轮有效统计；较早 `root-and-length.json` 中约 .968 的长度变化来自隐藏链，不是普通动作回归。

![鞠躬、深坐、拎起根部](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/rear-candidate-4/deep-root-closeup.png)

### 旧叶片圆边界确实消失，但另有误绑

沿候选3旧圆边界的同一探针，源间距 `.002796`，本轮映射间距也为 `.002796`，B mid 误差为 0。只能说明原圆规则已移除；下文新的不透明边缘探针仍失败。

### 转向隐藏中段没有明显双尾／针状穿出

260 帧中有 80 帧 `turn_tail≥.999`。将同姿态完整角色与临时不画尾巴的角色作 RGB 差分（任一通道差≥12），其中 68 帧为 0；其余 12 帧只有侧面衣发边缘 3–7 像素，最大约 5×3 像素。16 倍局部图也没有独立长针轮廓。这属于细边残留，不能把它描述成旧版大面积针尖泄露。

L/R 收尾过程在实图中只保留一条尾及一片叶，逐渐进入裙后。数学上隐藏链会缩短，故隐藏过程不应称为严格定长叶骨；但本次可见采样没有发现严重挤成针或第二叶尖。主要转向失败是后向层级瞬切。

## P1：B 尾干仍被最近叶段截走，旧问题换了边界

复现：`back + land(.325)`。源 `common/tail-back.png` 为 610×1391。粗尾干左侧相邻像素：

| 项目 | 像素 A | 像素 B |
|---|---|---|
| 源像素 | (168,636) | (168,637) |
| 源 UV | (.27540984,.45722502) | (.27540984,.45794393) |
| alpha | 251 | 251 |
| 原画放入世界框后 | (394.76,793.67) | (394.76,793.88) |
| nearest 段 | 0：root→mid | 4：leafBase→tip |
| 动作映射后 | (363.88175,828.25980) | (329.59297,840.51338) |

源仅差 `.21` 世界单位，动作后跳 `36.41251`。这些像素位于白色粗尾干，并非叶片或透明缝。全局最近线段仍允许回弯附近的粗尾干归给邻近紫叶末端；随后 `i==last && dot>=0` 又把它锁成刚性叶权重。

位置：冻结 `gpt_niang_linux/model/render.py:660–672` 的 nearest 选段与叶片权重。普通 8×12 网格把断界摊成左侧鼓包／小鳍；仅将诊断网格提高到 32×48、64×96，会显出横向长刺。提高网格密度不能修复错误归属。

![源尾干误归属探针](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/rear-candidate-4/back-source-ownership-probe.png)

![普通网格、密网格及地面约束对照](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/rear-candidate-4/back-mesh-ground-comparison.png)

**可实施修正：** 给 B 叶片和连续尾干明确的源区域／权重拓扑，不能继续只按全局 nearest。叶片候选 ROI 可从 `x<250, y>780`（UV `u<.40984,v>.56075`）开始，再沿紫叶外轮廓、叶颈画闭合 mask；尾干 root→mid 区（明确包含 `(168,636)`）禁止最后一段权重。低弯、细段、叶颈之间只在真实相邻连接处分配过渡，避免空间靠近却不相邻的部位争权。需要一起校验网格顶点和覆盖叶／干边界的三角形，不能只修不透明像素的权重查询。

只做上述粗 ROI gate 的诊断，探针跳变即从 `36.41251` 回到 `.21`，并消除实图鼓包。这证明归因成立，但这个矩形 gate 尚不是整叶／叶颈所有姿态的最终 mask。

![现状与仅诊断源区域约束](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/rear-candidate-4/back-leaf-region-comparison.png)

验收：B 的 land `.2/.325/.45`、run `3.525`、carried `.75`，完整图和隔离图都无横向鳍／割腰；记录上述探针及周边不透明像素的连续性；加密网格不能重新显出长刺。数据见 `nearest-ownership-boundaries.json`、`leaf-region-probe.json`。

## P2：三个后向尾巴尚未收回就降层，展开结束才瞬间恢复

冻结 `render.py:903` 在任何 `turn_tail>0` 时把整尾改为 z=2.2。B 原来在裙前，BL/BR 原来有大段在后裙前。收尾刚开始，几乎没移动的尾巴就整块掉到裙后；展开最后一刻又恢复原层级。

| spin 起始方向 | t=0 可见尾像素 | t=.01 | t=1.59 | t=1.6 |
|---|---:|---:|---:|---:|
| left | 5747 | 5746 | 5729 | 5749 |
| right | 9010 | 9034 | 9044 | 9078 |
| back-left | 8142 | 2712 | 2637 | 8143 |
| back | 3639 | 5 | 0 | 3679 |
| back-right | 9555 | 4266 | 4198 | 9462 |

更直接的 B turn：t=.005 时 `turn_tail≈.00003`，轮廓几乎没收回，可见尾已经从 3639 像素变成 5 像素。BL spin 最后 .01 秒多出约 5506 像素完整粗尾弧。这是层级开关造成的瞬隐／瞬现，不是相邻方向双图混合。

![B 瞬隐和 BL 最后一帧突然补回尾干](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/rear-candidate-4/rear-layer-pop.png)

**可实施修正：** 收尾先保持对应原画的正确前后分区，让可见轮廓移动到衣发遮罩内，再交换被遮住的材料／层级；展开时先在完全遮挡阶段恢复目标方向原本的层级，再展开。不要把 `turn_tail>0` 当成整尾降层条件。如果使用遮罩，需依据衣发实际遮挡轮廓逐渐吞没尾体，而不是把整个可见粗尾瞬间挪到后裙下面。

验收：三个后向分别检查首尾 .005/.01/.02 秒；可见面积连续变化。中间维持单条尾，仍不得引入双图／双尾尖。证据数据见 `turn-visibility.json` 与各向 `*-turn-dense.png`、`*-spin-dense.png`。

## P2：B 落地不穿地，但低弯体积被压成水平条

B land `.2–.45` 的低弯从圆厚截面变成平底白条；在完整角色中可见。冻结 `render.py:676–679` 对每个映射顶点单独钳制实际 worldY，避免穿地的同时也压扁了截面。

land `.325`：

- FK low 中心 y=`975.54539`，钳制后为 `968.71351`。
- 源不透明像素采样的最低位置，未钳制 y=`997.62636`，钳制后 y=`968.99885`，最大表面位移 `28.62751`。
- 每 4 像素采样的 30488 个不透明点中，3284 个受压（位移>.01）。

`back-mesh-ground-comparison.png` 下排仅诊断关闭 floor，可看出原来应保有的圆弧；上排真实输出则被压平。这个问题独立于叶片误绑，修叶片 mask 后仍存在。

尾巴的底边扫描最大 worldY=`969.16667`，出现在 B land `.275`，与地面969相差 .167，属于当前 .6 渲染比例下的像素边界量化，不应报为明显穿地。run 样本 B 最低点为962.5。结论是接地位置基本有效，表面体积不合格。

**可实施修正：** 在生成 posed 骨链时以尾体半径约束 low／相邻段，求得能容纳整个截面的离地中心；通过有限的前两段转角调整或低弯接触姿态吸收落地位移。最后逐顶点钳制只能处理很小的残差，不能承担约29单位的主形变。B 当前 low 中心应留出实际低弯半径后再落到地面上方；不应把中心975和表面998一起挤到969。

验收：地面边界仍在969附近，低弯白鳞和圆弧截面保留；放大图中不存在长水平压缩带；接触姿态前后 .025 秒采样不突然弹开。证据见 `native-fk-and-ground.json`、`ground-boundaries.png`、`back-skin-closeup.png`。

## 方向、动作覆盖与现有限制

| 初始方向 | 本轮尾巴结论 | 动作方向的真实行为 |
|---|---|---|
| left | 普通粗尾、根和叶正常；收尾可见区未见针状物 | bow/jump/carried 保持 left；sit 最终 front-left |
| right | 普通粗尾、根和叶正常；收尾可见区未见针状物 | bow/jump/carried 保持 right；sit 最终 front-left |
| back-left | 普通原画和定长链可保留；转向首尾层级跳变 | bow 转 left；jump 转 front-left；sit 转 front-left；carried 保持 back-left |
| back | 静态可保留；普通 land 的误绑和压地体积失败；转向几乎整尾瞬隐 | bow 转 left；jump 转 front-left；sit 转 front-left；carried 保持 back |
| back-right | 普通原画和定长链可保留；转向首尾层级跳变 | bow 转 right；jump 转 front-left；sit 转 front-left；carried 保持 back-right |

因此没有声称已实现“背面深坐／背面跳跃／背面鞠躬”：实际播放会先转到支持方向。当前身体仍由8张关键原画进行材料切换；密集转向可看见方向离散变化。本轮确认它不再使用 MLS 全身双图，但不能把当前效果描述为完整连续转身。更密头图不属于这个冻结快照的验收范围。

本轮建议先解决 B 的显式源区域权重，再处理后向层级切换，最后把落地约束从大幅表面压平改到骨链。无需因上述问题重新生成五向静态尾图。
