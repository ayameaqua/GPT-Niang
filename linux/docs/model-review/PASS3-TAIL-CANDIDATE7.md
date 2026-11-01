# 候选7尾巴／后向连续转向复核

候选7修复了候选6的公共画布回贴错位，尾巴旧四项回归、深坐和取消命令的即时连续性均正常。但新的body/hair连续转向仍有两项P2：**中间角度后发被拉成水平错层**，以及**跨过相邻角度中点时整份裙／发材质突然切换**。不能据此把整体连续转向判为完成。

## 固定版本与覆盖

- 冻结目录：`/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/candidate-7/linux`。
- 224文件，集合SHA-256：`0eefe58d9321b587bebc96c1fd27fbb1ba7b054ca156a829ecf70df933ba89f4`。
- 诊断目录：`/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/rear-candidate-7/`。
- 38个case、353帧：尾巴回归8、相邻／spin转向177、取消及替换120、蹲起48。0.01秒推进并精确补齐命令前后／相邻方向中点。Qt offscreen，768×768，不透明灰底；实际整身、裸尾、body/hair调色板与投影头部均分开查看。
- 冻结前后hash一致，viewErrors为空，paletteRejectedDelta最大为0。这些数值没有替代视觉判断。
- 候选6的确认失败另存于 [候选6报告](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/docs/model-review/PASS3-TAIL-CANDIDATE6.md)，不以本轮修复覆盖旧结果。

## P2：逐行alpha极值把细发尖变化传给整行发束，产生水平错层

复现：BL→B、B→BR的受控相邻turn约.2994秒，L→BL也可见。后发隔离图中，连续发束被切成多道横向偏移带，发尾还出现波纹状压缩。完整合成上也可见，且这部分完全不需要脸部图层就能复现。

根因位于冻结 `gpt_niang_linux/model/silhouette.py:69–84` 的`RasterPalette.rows/bounds`及`104–107`的横向映射：每一行只取alpha最左／最右极值和一个centre，然后整行沿这两段横轴缩放。某个细发尖在下一行结束，会使极值大跳；这个变化随即影响所有同一行的内部发束。

| 原画调色板 | 相邻行世界y | 轮廓跳变示例 |
|---|---:|---|
| BL hair | 782 | left 423→490，跳67 |
| B hair | 794 | left 377→480，跳103 |
| BR hair | 747 | right 559→462，跳97 |
| B body裙摆 | 948 | left 296→393、right 554→457，各跳97 |

共享网格顶点、有限画布和三角绘制虽然避免无限外溢，却不会消除这种错误的横向缩放场。增加绘制rows也不能修正由轮廓数据产生的畸变。

**归因实验：** 仅在诊断进程将palette.rows做半径10的三角加权平滑，保持原画、动作、角度、绘制流程不变。BL→B的明显横条大幅减轻；B→BR底部也改善，但仍保留部分非自然的起伏。这是定位用的对照，不是已落地修复，也没有将简单平滑视为最终方案。

![冻结原始轮廓与仅诊断平滑的对照](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/rear-candidate-7/hair-row-envelope-diagnostic.png)

**可实施修法：** 先给左右轮廓包络做稳定平滑／限斜率，固定发根、主要发束端点、腰与裙摆关键点；避免单根发尖或一片裙褶的末端控制整个横截面。更稳妥的是按主要发束、裙片建立多列对应网格：让发束中心和真实边界各自连续，而非只用整张图的left/centre/right。根、腰、裙叉与下摆须保持一致的语义高度，不能把不同视角任意比例的行当成同一解剖位置。

验收时同时看完整角色和hair隔离图，在112.5°、157.5°、202.5°附近连续扫角，不应有横向接缝、波浪压缩、发束突然加粗。数据见`palette-row-jumps.json`，诊断脚本为ignored目录的`hair-c7-smooth-probe.py`。

## P2：连续外包络没有使内部裙褶／发束连续，半角处仍整图换形

冻结 `render.py:530` 根据`view_mix<.5`选择整张原画；`605–608`再用该view的整份body/hair材质进行轮廓配准。半角前后是两套原画，内部发束、领口、裙褶和花边没有对应约束。因此即使外包络已经插值，切材料时仍会明显跳纹、换形。

隔离body与hair后，用任一RGB通道差≥12计数；不包含头壳、角耳、脸、手臂或尾巴。下表是独立连续推进的.3秒附近、相隔.0006秒两帧，因浮点边界落点，实际材料切换在.3→.3006秒：

| 方向／隔离层 | 跨切换边界变化像素 | 同侧相邻.0006秒变化像素 |
|---|---:|---:|
| BL→B hair | 26355 | 34 |
| BL→B body | 29892 | 262 |
| B→BR hair | 23042 | 386 |
| B→BR body | 29714 | 857 |
| L→BL hair | 43724 | 1813 |
| L→BL body | 35925 | 175 |

这不是仅仅纹理亮度轻微差别：图中能看到整束卷发和整块裙褶位置改变。353帧主采样在约.3秒的同一个边界，也记录了整身4万至6万余像素变化；后一帧通常大幅回落。body/hair隔离证据已经排除了前向组正在处理的脸斑／横条干扰。

![半角材质切换前后：独立body与hair层](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/rear-candidate-7/body-hair-material-switch.png)

**可实施修法：** 给同一件裙片／同一束后发建立跨视角的内部锚点（发束根—中段—尖端，领口—腰缝—裙叉—花边端点），先让重要纹理和部件轮廓在切换姿态重合，再按真实遮挡边界切换局部材质。几何或纹样差异无法配准的区域需要专门中间原画。单纯把阈值.5挪到别处，只会移动跳变；恢复整角色双图混合则会重新引入双轮廓，不能作为该问题的验收方案。

验收在157.5°等切换角左右以很小角度步进，既看包络又看发束／裙褶内部。不能只凭`paletteRejectedDelta=0`或两帧bbox接近通过。完整数据见`body-hair-material-switch.json`。

## 尾巴旧问题回归：本轮通过

候选6的公共回贴错误修复后，实图中的尾巴、腿、裙、带pitch头壳已回到正常位置。B land .2/.325/.45的裸尾保留圆厚低弯，未恢复水平白条；完整角色里也没有漂到头旁或穿裙脱根。

- 旧圆边界探针映射距离保持`.00279598`。
- 粗干`(168,636)→(168,637)`保持`.21`。
- B内缘`(316,1166)→(317,1166)`在256场下也保持`.21`，前轮2.044局部拉伸未复现。
- 353个实际尾绘制姿态的尾骨目标与映射root误差为0。排除主动收拢的隐藏链后，91个普通姿态的骨长最大相对变化为`1.67e-15`。

三个后向spin首尾可见尾面积保持连续：

| 方向 | t=0 | .005 | 1.59 | 1.6 |
|---|---:|---:|---:|---:|
| BL | 8142 | 8135 | 8058 | 8144 |
| B | 3661 | 3661 | 3654 | 3668 |
| BR | 9556 | 9554 | 9427 | 9467 |

没有候选4中最后一帧突然补出数千像素粗尾的现象，亦未见双叶或长针。

![候选7背面落地整身回归](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/rear-candidate-7/regression-back/full-contact.png)

完全隐藏时仍保留小发缝泄露：多数为2–30像素，R↔BR中间方向最大66像素，分布在约30×21像素范围内。它随新的后发变形遮罩变化，没有形成独立完整尾尖，暂保留为P3。应在修后发轮廓后再次检查，必要时用局部遮罩覆盖真正收拢的残留；不要恢复整尾瞬间降层。

## 蹲起、取消、替换与整段行为

18个带明确命令边界的case，命令执行前瞬间与执行后瞬间的RGB像素差全部为0。后续5/20/60/140/240ms中，尾巴恢复展开；本轮未见旧方向整尾突然返回或尾骨断开。相邻转向中点取消后的身体仍会受到上述材质／轮廓问题影响，不能据即时差为0宣称后续视觉完美。

深坐站起及“深坐请求spin”按实际队列先站再转，根连接保持；半坐取消、起身取消、B落地最低位改为spin也没有立即跳位。由B请求sit会先转到front-left，报告未将其标为背面坐姿。静态脸斑／脸部横条交前向审查，本报告不重复判定。

![深坐请求转身：真实先站再转队列](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/rear-candidate-7/deep-seat-queued-spin/full-contact.png)

整体观感的主要剩余障碍是两项P2，而非旧尾巴形状或根坐标。建议先稳定后发／裙摆包络，再处理内部对应与材质切换。修复后只需重采相邻侧后转向、spin中段、该处取消和少量尾遮挡回归；无需重新生成五向尾图或重复全套普通动作。
