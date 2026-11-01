# 候选9共享长发／衣物与尾巴回归

**结论：不采用 C9。** 共享表面在实际原生视角和转身里没有保持角色造型：左右侧长发缩成窄带并被衣体遮住；衣物出现长细条和两套前襟拼接。两项均为 P2，不是按旧原画差分判失败，也不依赖头部或四肢的问题。尾巴本轮定向回归正常，不能由此认定整角色可交付。

## 基线与采样

- 冻结目录：`linux/test-results/review-pass-3/candidate-9/linux`，234 文件。
- 文件集合 SHA-256：`2c655e761a9f704b60ec937fb4b500cdd2de9ed9e1e97946ab49f76dfca54790`。
- 诊断目录：`linux/test-results/review-pass-3/rear-candidate-9/`；主采样脚本为 `tail-c9-check.py`。
- 27 个 case、181 帧：八向原生静态 8，尾巴／落地回归 20，转向 96，取消 24，坐起及替换 33。Qt offscreen、768×768、不透明灰底；全身、裸尾、共享长发、共享衣物均隔离查看。
- 实际 spin 采到各 22.5° 半角及 85/89/91/95°、265/269/271/275° 的侧向邻域；不使用微小时间差本身作为失败标准。
- 主采样与报告结束复核时冻结 hash 均一致，viewErrors 为空。未改 production、素材或冻结树。诊断中材质显隐只发生在独立 Python 进程。

## P2：侧向长发体积不足，整身变成短发观感

原生 left 的裸长发层在 alpha≥128 的边界约为 screen `(366,428)–(431,607)`，宽 65；back 为 `(218,428)–(472,607)`，宽 254。右侧同样只有约 65 像素宽。这里不是要求所有视角一样宽，而是实际侧面只剩一条贴进衣体的窄带，肩下长发几乎不可见，转到后侧又重新长出一大块长发。

把同一帧完整渲染与“只关闭 SharedLongHair.draw”的渲染比较，RGB 任一通道差≥12 的可见长发面积如下。该操作只用于确认哪些像素属于下段长发，不改变头部发壳和短卷发。

| 视角 | 可见长发像素 | 可见区域 bbox |
|---|---:|---|
| F | 8159 | 218,423–472,596 |
| FL | 3750 | 273,426–461,597 |
| L | 339 | 385,425–413,532 |
| BL | 21226 | 276,425–486,609 |
| B | 25404 | 218,424–473,609 |
| BR | 21816 | 215,424–424,609 |
| R | 1163 | 244,475–288,591 |
| FR | 2497 | 239,418–423,581 |

实际全身及 spin 接触表也显示相同现象：接近正侧面时只剩肩上的短发，背向时长发体积大幅回归。变化可以是连续的，但连续并没有保持合理的造型。

![八向肩下实际可见长发](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/rear-candidate-9/hair-visible-native.png)

原因位置在冻结 [hair.py:101](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/candidate-9/linux/gpt_niang_linux/model/hair.py:101)：underside 的横截面由 `z=-depth(y)*sqrt(1-(dx/radius)^2)` 决定。正侧面时 x 投影主要剩 z 的范围；后面仍是一个平面，侧向投影面积为零，不能补出侧面厚度。后发本体还与更宽的衣体截面重叠，被角色既有层序遮住。这里的 depth 排序只解决长发内部面片顺序，没有建立长发与衣物共享的真实遮挡体。

480→530 接缝在当前静态中没有形成独立、清晰的断层空隙；不能把裸长发图的裁切上缘单独当成穿帮。确定失败是侧向体积与可见长度。若将来重做真正连续表面，需要有实际侧厚度、后缘与衣体间距，并按侧面完整轮廓验收；仅增加网格密度或移动同一平面不能解决。当前应退出此共享长发路径，保留原生长发。

## P2：衣物四区 UV 没有建立衣片对应，细条与双前襟仍在

原生 front-left 就能复现，不必经过转向：完整角色左侧约 screen x=194→278、y=550→700 有一条细长裙条，与主要裙体之间隔着大片透明区域。深坐后它变成约 x=126→250 的斜向贴地长条。body 隔离图中完全相同，排除了尾巴与四肢。

同时，45° 左前视角能看到两组前襟／短前片并排：一组来自 front，一组来自 left。它们没有成为同一件衣服的同一前片，而是各自完整插入一个固定材质区。22.5°、67.5° 与右前半角仍可见这种不一致；后向的主体更完整，但不能据后向通过忽略前侧静态已改变的结构。

![原生 FL 站立与深坐的四材质来源隔离](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/rear-candidate-9/garment-panel-isolation.png)

上图每行从左到右为 all/front/left/back/right，其他三个材质只在诊断进程被改成透明。**细长条在 front-only 中仍然完整存在**；left-only 提供右边那套前襟／短片；back-only 在此角度不可见，right-only 仅有极少边缘像素。因此不能再将整条问题简单归因于平均 normal 裁格，或者误认为是后材质在切线处泄露。

冻结 [volume.py:64](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/candidate-9/linux/gpt_niang_linux/model/volume.py:64) 从衣物行抽取轴和左右外半径；[volume.py:81](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/candidate-9/linux/gpt_niang_linux/model/volume.py:81) 再以 `axis + radius*sin(delta)` 采整张方向图。语义网格内部的前片边、开衩边、玫瑰、斜尖和后裙层级并未成为不同衣片的 UV 边界。四张方向画里重复出现的前襟因此会被同时铺到不同四分区；原插画透明处又不等同于物理环面上的开口，投影后留下细条与大缺口。

真实 ellipse tangent 的逐行裁剪已在这份冻结代码中使用。`solid_material()` 存在但未调用，本报告没有将撤回的扩色黑底误记为 C9 现象。问题是当前实际材质分区与衣片拓扑不一致；恢复不分区域的扩色也不能正确保留前裙开口。

![实际 spin 半角中的共享衣物](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/rear-candidate-9/garment-half-angle-closeups.png)

未来若继续表面方案，应让前襟／短前片在表面上只存在一次，左右侧材质只贡献真实侧片，前开衩与后裙实体分别建面。需要建立局部衣片边界后再取 UV；不能把整个 front/left/back/right 插画分别当成四块互不重复的材质。本轮不继续给此临时表面加补丁，退出共享衣物路径更符合当前交付范围。

## 尾巴定向回归正常

以下结论同时查看了裸尾和完整合成，没有用 root 数值代替视觉检查：

- B land `.2/.325/.45` 保留厚干与圆弯；未见旧的割腰、白色水平薄条、紫叶异常压缩。
- L/BL/BR/R land `.2/.325/.45`、B run `3.525`、B carried `.75` 与深坐／起身中的尾根保持连接。坐姿左侧细条经上面的来源隔离确认属于裙，不是尾巴新生分叉。
- 181 个实际尾调用姿态相对 `upper(coccyx_point(angle,seat))` 的 root 误差最大为 0；64 个普通未收拢姿态的骨长相对变化最大 `1.55e-15`。
- B 的旧粗干与内缘探针在四个落地时点映射距离均约 `.21`；旧圆边界探针约 `.00279598`，未恢复不连续认领。
- 58 个 fully tucked 采样中，整身与禁画尾巴的 RGB≥12 差异均为 0，没有薄尾边或第二叶泄露。此结论只覆盖这批角度和动作，不代替换回原生衣发后的遮挡回归。
- 三个后向 spin 的首尾可见面积连续；没有旧版最后一帧突然补回大片尾巴的现象。

| 起始方向 | t=0 | .005 | 1.59 | 1.6 |
|---|---:|---:|---:|---:|
| BL | 8010 | 8010 | 8011 | 8053 |
| B | 3611 | 3599 | 3583 | 3601 |
| BR | 8805 | 8820 | 8810 | 8860 |

![B 落地裸尾回归](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/rear-candidate-9/regression-back/tail-contact.png)

## 坐起、取消及范围边界

深坐→stand、深坐请求 spin 的真实先站后转队列、起身取消、B land 最低点替换 spin 均已采样。五个明确命令即时边界（后三向 spin 取消、起身取消、land→spin）前后像素差为 0；后续帧没有尾根突然跳回旧方向。衣物的贴地细条和侧发不可见仍贯穿这些动作，不能称整段坐起通过。

未观察到本批新长发单独穿透地面的确证，但侧发大部分被衣物遮住，不能据“没有可见穿地”反推该发面完整正确。SharedLongHair 的地面处理还以中心末端高度为依据，未来任何真实表面路线都应使用实际轮廓检查，而不是仅检查这一中心点。

C9 相比 C7 不再以同一个半角阈值硬换整张 body/hair，且此次没有沿用 C7 的极小时间差指标判它失败；本轮失败来自可见造型本身。头部专项交前向审查；四肢仍走旧 view 路径的硬切不在本报告通过范围。

后续候选按原生 clean-core、原生衣服／长发与尾骨动作验收，转身明确为**原生八向帧动画**。连续三维补间仍未验收，不应把离散八向描述成连续 3D。更换衣发后须重新检查尾回缩的实际遮挡；C9 的 58 个隐藏样本通过不能直接转移到新候选。

证据和数值索引：`summary.json`、`records.json`、`rollup.json`、`hair-visible-native.json`、`garment-panel-isolation.json`；八向汇总图为 `native-eight-{full,body,hair,tail}.png`。四材质诊断脚本 `rear-candidate-9/details.py` 只写 ignored 证据。
