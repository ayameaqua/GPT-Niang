# 第三轮：Candidate 10 原生方向头帧复核

**C10 结论：头发整体形象明显恢复，五官及前向小幅头动作回归项通过；仍有两个 P1，不能把 C10 判为完整通过。** 右后/右侧原生头图重新露出烘焙颈块，左右回眸仍暴露身体后发裁片里的旧短卷。两项都是真实 Qt 合成缺陷，不是透明图查看器噪点。文末独立记录 C11 的定向修复结果，不追改 C10 的失败结论。

本轮只复核头部、表情及头部动作连接。截图中的手势、肢体、尾巴、衣服不因此获得验收。原生有限帧转向按帧动画评价，不能称作已经通过连续 3D 转头。

## 冻结依据与实际覆盖

冻结目录为 `linux/test-results/review-pass-3/candidate-10/linux`。2026-11-01 18:03:21 +08:00 校验 snapshot 所列 **224 文件全部匹配**；完整记录见 [verification.json](../../test-results/review-pass-3/front-fix-10/verification.json)。

| 文件 | SHA-256 |
| --- | --- |
| snapshot.json | `f2b8313e8b052b5c004625b0e31c20c033a75f125fc83cc9091f00b61665fc08` |
| model/head.py | `926fe85141e5307bd13c09a8652010fc5ef97946cf576514625d263e01ebb490` |
| model/render.py | `d9ddc3a73cf55061fedef94d7b82e1c778169a08107dd444971120f17f51f083` |
| model/motion.py | `f44f808a6170a39134f13aa335ee4761921860164b821c8172b56524ec52e139` |
| models/dragon/head.json | `5203fe596ac18619cf2c7fc404b2a43701148b47fe1b80d3e78ac93690d28e41` |

使用 live `linux/.venv/bin/python`、冻结 PYTHONPATH、`QT_QPA_PLATFORM=offscreen` 和 `PYTHONDONTWRITEBYTECODE=1`。实际调用 renderer 或其 `layered_head.draw`；所有判断图先经 QPainter 合成到 RGB32 灰底 `#b8bec8`。动作以不大于 1/120 秒步进，避免单次 advance 截断。静态 clock=1 并关闭自然眨眼/摆动；动作保留实际 Animator 姿态。没有修改实现或素材，没有依据软件测试数量认定视觉合格。

| 检查项 | 判定 | 实际证据/限制 |
| --- | --- | --- |
| 8 原生头 +4 中间头 | 发型恢复；右侧颈块 **P1 失败** | [12 方向](../../test-results/review-pass-3/front-fix-10/static-head-12.png)，全部实际查看 |
| front/FL/L/R/FR 的 nod | 最低可辨俯仰及头颈绑定通过 | 5 张 `*-nod.png` 的多时点；[正面](../../test-results/review-pass-3/front-fix-10/front-nod.png)、[左侧](../../test-results/review-pass-3/front-fix-10/left-nod.png)、[右侧](../../test-results/review-pass-3/front-fix-10/right-nod.png) |
| 8 起始方向 × nod/shake/tilt-left/tilt-right/look | 已逐张查看 8 接触表，共 200 帧；未新增头脸双影或明显断颈 | `head-actions-{view}.png`，每动作采 0、25%、50%、75%、100% 时点。背向的部分动作会先自动转向，不能宣称在原背向直接点头通过 |
| BL/BR look-back | **P1 失败** | [左回眸](../../test-results/review-pass-3/front-fix-10/back-left-look-back-dense.png)、[右回眸](../../test-results/review-pass-3/front-fix-10/back-right-look-back-dense.png)，0–.504 秒每 .0336 秒实际查看 |
| 5 面向 ×19 表情 +静态 speech | 五官布局回归项通过 | 5 张 `faces-*-20.png` 全部实际查看，单眼、眉/眼映射、嘴、泪及腮红未见新双份或越脸 |
| happy + speech + nod，5 面向 | 组合口型回归项通过 | 5 张 `talk-*.png` 全部实际查看；0–.44 秒和 speech 关闭后 .04/.08/.12 秒。开闭口有间歇，笑眼保持，嘴在同一脸面内 |
| 7 组点头/回眸取消 | 取消即时连续性及恢复机制通过；回眸经过同样的坏旧侧发 | [取消汇总](../../test-results/review-pass-3/front-fix-10/cancels-summary.png)、[0秒逐像素一致记录](../../test-results/review-pass-3/front-fix-10/cancel-zero-delta.json)。图像比较之外实际查看恢复过程 |

19 表情静态与一个代表性说话/点头组合不等于检查了“19 表情 × 所有动作”的全部笛卡尔积。

## P1-1：完整原生头图带回不属于头层的颈块

`head.py:315–328` 将角度量化为原生头帧，直接绘制整张 `first.image`，恢复了原生皮肤/刘海/短卷的对应关系。但 `HeadFrame._skin_rows` 在 C10 的第109行对无脸帧直接返回；有脸帧也仅处理由嘴附近洪泛找到的肤色连通域，未处理与脸分离的颈岛。因此 `core-back-right.png` 的颈块完全留下，`core-right.png` 及右侧中间图的独立颈块也被整张绘制。

症状：225° 后脑下多出水平截底的粉色颈带；270° 发梢之间多出裸露颈片；247.5°、292.5°出现相应的粉色窄块。它们叠在身体自己的颈/衣领/后发上，不是合法的第二段颈骨。放大对照见 [C10/C11 颈部比较](../../test-results/review-pass-3/front-fix-11/neck-closeup.png)，左列保留 C10 原始失败证据。

以下为已扣除每片原 neck 偏移后的统一头坐标，公共颈点 `(425,460)`；不包含诊断图的 `(150,220)` 平移。原生完整分辨率统计采用 alpha≥180，弱/强暖色两组阈值交叉确认，数值仅用于定位，结论已由实际图验证。

| 方向 | 主要颈块 x 范围 | y 范围 | 说明 |
| --- | --- | --- | --- |
| back-right 225° | 371.21–470.32 | 438.59–488.88 | 无脸帧，整块颈带 |
| right 270° | 381.26–450.85 | 426.86–479.88 | 颈顶高于430；另有 x429.64–448.20/y424.87–446.08 小片 |
| right247 247.5° | 416.66–439.76 | 438.19–481.17 | 另有 x391–399/y470–479 小岛 |
| right292 292.5° | 380.18–418.76 | 440.14–475.89 | 下巴下另有 x438.62–462.45/y441.84–462.27 颈三角 |

完整数据见 [neck-components.json](../../test-results/review-pass-3/front-fix-10/neck-components.json)。不能把该文件里所有 y>420 的肤色分量都当颈：270°、247.5°的右侧较大分量仍包含下巴。

最低修复：先在完整原生 alpha 上找肤色分量，无脸帧也执行；保留嘴连通脸域，清理独立颈岛。独立岛搜索前沿至少覆盖 y420，不能只裁 y468 以下。清掉肤色后还须检查紫色外描边；用组件邻接的小范围 mask 覆盖描边，不应整块矩形擦除相邻卷发。验收为四个方向隔离头图无粉色颈岛、无下垂颈边；完整 idle/nod/tilt 和回眸中身体颈/领正常露出且没有新增发梢缺口。

## P1-2：后侧身体 hair-back 仍包含旧头侧卷，回眸后悬空

BL/BR 的 `rig.json` 中 `hair-back` 使用各自 `head.png`，C10 的 `sourceWindow=[0,.4,1,.6]`、`fadeTop=[.4,.52]` 仍保留旧图中短头发的两侧卷梢。`render.py:920–926` 在回眸先画一次 `rear-base`，再画新朝向头；后发属于身体保留层，因此旧短卷不随头转走。实际约 .1344 秒起，新头移开处显出灰白悬空卷片；到 .4032/.504 秒仍在脸旁，与新的头发没有连接。

这次没有整头双影；问题是**一张身体长发裁片中烘焙了旧短发内容**。它经过 fadeTop 后本来就有低 alpha，在 RGB32 灰底成片可见，不能归为查看器的透明 RGB 噪点。

源绑定：BL hair-back box `[185.788,65,470,730.955]`，BR `[189.500616,65,470,710.663]`。旧 .40 上缘分别约 worldY357/349，.52 渐隐结束约445/434；悬空旧卷主体落在 y365–430。[BL 隔离标尺](../../test-results/review-pass-3/front-fix-10/hair-grid-back-left.png)、[BR 隔离标尺](../../test-results/review-pass-3/front-fix-10/hair-grid-back-right.png) 是实际原裁片、灰底与世界坐标线。

最低修复：后侧身体长发只保留 worldY480 以下的真实长发，顶部480→510局部渐入，完整头层继续提供上方短发。不要统一改变所有方向的后发裁线，更不要再生成一套卷发替代原角色。验收需看两侧回眸 0–.55 秒及取消返回；旧卷必须消失，头层与身体长发交界不能出现新断口。BR core 的最低边约 y490，故必须实际检查480–510交界，而不能只验证mask参数。

## 动作与有限方向帧的边界

C10 的前向点头不再只有整头上下平移：完整头面在小幅 pitch 下投影，眼/口与脸面一致，侧面下巴相对颈点发生俯仰；12°的一次1.2秒点头至少可辨。摇头的小 yaw 与歪头的颈点旋转也有各自含义。这里通过的是当前小幅动作与连接，不代表有真实多轴三维骨架，也不代表可任意扩大角度。

`motion.py:241–247` 对背向的 nod/shake/look 等需要脸的动作先请求转到 front-left。实际 [BR 动作表](../../test-results/review-pass-3/front-fix-10/head-actions-back-right.png) 可见先转向再执行；它不能作为“后脑方向直接点头已验收”的证据。tilt-left/right 在原背向执行，已查看其连接。

方向头帧间仍有可见停顿和轮廓跳换，尤其 FL 与生成的侧面图发长/头部体积不同。`head.py` 取最近原生角，回眸用12帧，身体转向用8帧；这是一种明确的有限帧方案。整图混色和行拉伸不再出现，但“没有混色”本身不能证明连续。若将来恢复连续转头，必须重新处理方向图之间的头体积、发长和遮挡，另行验收。

## C11 独立修复快照：两项主体修复，颈描边仍需收尾

此节仅针对后续冻结 `candidate-11/linux`，不更改上述 C10 结论。2026-11-01 18:03:22 +08:00 校验 snapshot **225 文件全部匹配**；[完整校验](../../test-results/review-pass-3/front-fix-11/verification.json)。snapshot=`5a9af08363ccfcde458e93f17afc7a8cd67e3335f6b5f4b4ea3c71e11aaf2905`，head.py=`7c22266d4e9cd320bcb9bb14b662abe09314bea5e4fefc2875c7082d45877383`，render.py=`87f98c56ef2151d4cfa28eb7852ab8971045a7d2c26ff63a6e9c1e0b86bf437c`。head.json 与 motion.py 同 C10。

C11 总体暖色mask处理无脸帧及独立颈岛；BL/BR身体后发改480→510。实际查看12原生静态、两侧回眸0/.1008/.1344/.168/.2352/.3024/.4032/.504/.55秒、.55秒取消后0/.04/.08/.12/.18/.22秒，以及 R/BR/FL/L 的idle/nod/左右tilt。

- **旧悬空短卷修复通过。** [左回眸](../../test-results/review-pass-3/front-fix-11/back-left-look-back-targeted.png)、[右回眸](../../test-results/review-pass-3/front-fix-11/back-right-look-back-targeted.png)、[左取消](../../test-results/review-pass-3/front-fix-11/back-left-cancel.png)、[右取消](../../test-results/review-pass-3/front-fix-11/back-right-cancel.png)。中央头颈有身体颈/领连接，样本中未见必须另补 nape 桥的缺口。角、耳、呆毛和发饰仍在；大接触表缩小后误认角消失，放大原图已排除，不记录为运行缺陷。
- **烘焙颈块主体已清，仍有 P2 描边残留。** [颈部近照](../../test-results/review-pass-3/front-fix-11/neck-closeup.png) 的C11列：225°两侧下垂紫线；270°原U形颈底曲线；247.5°两条竖边；292.5°下巴下的颈斜边。它们不是发线，也不是灰底噪点。现mask只删除暖色像素，没有包含偏紫/暗色外轮廓；430前沿还漏掉R的部分上端。
- 修法应把独立颈岛前沿放至420，并沿确定组件扩约2–3模型单位去掉外描边，保持嘴连通脸域不扩。组件bbox只能约束搜索区域，不能直接矩形清空，否则会割掉插入该区域的合法卷发。需要下一冻结快照的四方向近照及完整头颈定向复核，C11尚不宣称这项完全收尾。

本报告及 ignored 诊断为本子代理唯一改动；冻结与 live production、原始私有纹理均只读。
