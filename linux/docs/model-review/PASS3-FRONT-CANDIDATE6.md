# 第三轮：Candidate 6 前向／头部正式视觉审核

结论：**C6 不通过。C7 仅修复了整身网格回贴错位，头部仍不通过。** 本报告区分已看到的渲染结果、数值诊断与尚待下一候选验证的修改；未因新增投影参数、分层或测试通过而判定视觉合格。

## 冻结范围与证据

- 审核日期：2026-11-01。最终冻结校验：15:26:48 +08:00。
- C6：../../test-results/review-pass-3/candidate-6/linux；snapshot.json 的 227 个文件全部匹配。
- C7：../../test-results/review-pass-3/candidate-7/linux；snapshot.json 的 224 个文件全部匹配。仅作为修复回贴位置后的定点复查，不覆盖 C6 结论。
- 两版 head.py 相同，SHA256：c7ec64898d36a0822686de1a9c062009812e412d59c8da9129bf1ce51de8036f。
- 两版 silhouette.py 相同，SHA256：de8ab81801382a053c45965e2c063b230a7c30aca94baba239e27b92a05b4163。
- C6 raster_mesh.py：e0ed83bf70910ff31b20af1abb454fd1499b78b8bf6b719b454ff7dce9d832b5。
- C7 raster_mesh.py：cff84b9f508a8199b8cd1a17b13e333e28e8905605ec35ef3c4ed7c662d10ecf。
- [完整冻结校验](../../test-results/review-pass-3/front-fix-7/freeze-verification.json)。生产代码与冻结树均未修改，原始私有模型素材未复制到仓库。

运行使用仓库 linux/.venv/bin/python，QT_QPA_PLATFORM=offscreen，PYTHONPATH 只指向对应候选的 linux。所有截图均经过 QPainter 合成到 RGB32 灰底，背景 #b8bec8；本报告的白斑、横带和碎裂不是透明图查看器放大低 alpha 噪点。静态 clock=1；实际动作通过 Animator.advance 以不超过 1/120 秒步长推进，未一次调用大 dt。

脚本：[C6 review.py](../../test-results/review-pass-3/front-fix-6/review.py)、[C6 isolate.py](../../test-results/review-pass-3/front-fix-6/isolate.py)、[C7 core-checks.py](../../test-results/review-pass-3/front-fix-7/core-checks.py)、[C7 detail.py](../../test-results/review-pass-3/front-fix-7/detail.py)。头部隔离图用于定位材质／角度问题；涉及头颈和动作结论均另看了真实 Animator → DragonRenderer 全身合成，未把隔离图当成绑定验收。

## 审核状态

| 项目 | 结果 | 实际观察与限制 |
|---|---|---|
| 12 个 native 清头壳的最终合成 | 失败 | 多个正面／侧面出现白斑、粉色大块阴影及横向细条，原清头壳并没有相同斑块。 |
| front、front-left、front-right、left、right 五官镜像 | 局部通过 | 白眼、虹膜、睫毛、眉的朝向一致；未再见先前 right 眼组交叉。肤色问题阻止整脸通过。 |
| 五方向各 19 表情＋neutral speech .85 | 基础差分有效，整体不通过 | happy、wink、sad、cry、angry、pout、surprised 等有可辨眼口变化；wink 在双眼视角只闭一眼，单眼侧脸闭可见眼。腮红／泪滴出现。白斑遮盖脸部体积。 |
| front / left / right nod | 动作机制改善，整体待修 | C7 0/.3/.6/.9/1.2 秒可见脸与头顶相对运动，侧面有绕颈前俯；不再是整个头只上下平移。12°最大俯仰仍需在干净脸部下复核自然感。 |
| left / right bow | 头颈局部连接无新增大缝 | C7 0/.425/.85/1.275/1.7 秒显示身体前倾、头颈随动；并不表示肩臂、全动作或全身已通过其他组审核。 |
| 两侧 look-back | 失败 | 启动短时间内头壳明显横向波浪／撕裂，多处材质切换；见下文精确时刻。即使只有一个头也不符合连续回眸。 |
| 110–113° / 244–248° 耳叶 | 旧双重缩宽问题未再按旧结论判失败 | 法向宽度保持后不再把整耳第二次等比缩小；但当前坏头壳遮挡了整体自然感，不能签署耳动画通过。 |
| 135° / 315° 耳前背材质 | 局部改善 | 同 alpha、同 root/tip 上混色，未再看到旧“直接换成另一张窄叶轮廓”的问题。 |
| 0° / 180° 附近耳遮挡 | 失败，P2 | ±.01° 时整耳前后层级硬换，左右耳轮流出现／消失。 |
| C6 整身衣片／尾／腿回贴 | 失败；C7 定点修复有效 | C6 真实 Animator 全身也发生位移；C7 actual-full-8 已恢复相应部件位置。不能用 C6 图指控 C7 仍同样错位。 |

19 表情图是直接调用 LayeredHead.draw 的头部隔离证据，不包含 renderer 的外围 expression accent 绘制。这些图不证明 thinking/confused 等外围符号缺失，也不能替代“表情中断在 0 秒连续”“完整说话周期闭口间歇”的时序验收。C6 全动作输出已保留，但受到整身回贴缺陷影响；本报告不借其未逐项复看的帧宣称全动作通过。

## P1-1：原 face 的烘焙阴影被当作通用肤色贴进新脸

证据：[12 native 头部](../../test-results/review-pass-3/front-fix-6/static-head-12.png)、[正面分层](../../test-results/review-pass-3/front-fix-6/layers-front.png)、[左侧分层](../../test-results/review-pass-3/front-fix-6/layers-left.png)、[右侧分层](../../test-results/review-pass-3/front-fix-6/layers-right.png)。每张分层图依次为原清头壳、mapped skin、mapped hair、skin window。

原清头壳皮肤为连续浅肤色，mapped skin 单层已带有不属于新脸的大块白／粉斑。私有原 face.png 还含原刘海形状的粉色投影和腮红，不是均匀皮肤 albedo。head.py:279–290 将该 face_palette 全宽重新映射到新脸两窗口；原本应跟随原发型的阴影被拉进新额头、鼻侧和脸颊。这不是 clean-core PNG 绘制了相同斑点，也不是五官 atlas 自身损坏。

最低修复：皮肤 zone 1/3 和头发 zone 0/2/4 从同一个选定清头壳、同一个纵向 phase、同一 source UV 取材质。native 角度下两者合并应近似原 PNG；原 atlas 仅提供眉眼嘴等独立五官，停止用旧 face.png 提供新头的皮肤明暗。

验收：先移除眼口和饰物，逐一比较 12 native 的“skin＋hair”与原清头壳。在 1×灰底和 2×近景中，脸不能多出原 PNG 没有的白块、旧刘海阴影或横向接缝，再加回全部表情。

## P1-2：用五官包围盒裁皮肤，产生矩形额头／鼻侧边界

head.py:99–106 用所有五官 feature rect 的范围再扩 28 模型像素来限制肤色 flood；此矩形不是皮肤外轮廓，不能覆盖高额头、侧脸鼻梁等区域。左侧分层图可见额头和鼻前沿有笔直硬边：ROI 外原肤色留在 hair 中，ROI 内又画入另一套皮肤材质。两个问题叠加，形成“贴了一个矩形脸”的效果。

最低修复：在完整 alpha 头壳中识别与嘴／脸种子相连的肤色区域，阈值覆盖本片真实粉色阴影；五官框只用于五官摆放与寻找种子。必要时每图提供明确的皮肤遮罩，不用统一矩形替代脸部解剖边界。需排除白发和头壳外部，不能把放宽阈值变成整头都算肤色。

验收：left/right 的额头、鼻尖、颊缘没有水平或垂直 ROI 截线；双皮肤窗口沿真实刘海闭合；所有 native 的 skin/hair 分区合成保持原画。front/right 的 19 表情与 speech .85 需重新看灰底近景。

## P1-3：逐行“无皮肤”被误当成“无脸帧”，发壳出现百像素横向波浪

证据：[C7 78.75° ±.01°](../../test-results/review-pass-3/front-fix-7/head-boundary-78.75.png)、[C7 123.75°](../../test-results/review-pass-3/front-fix-7/head-boundary-123.75.png)、[C7 235°](../../test-results/review-pass-3/front-fix-7/head-boundary-235.png)、[逐行数值](../../test-results/review-pass-3/front-fix-7/row-jumps.json)。图中不是只有细线，刘海／后脑／发梢被整条拉向左右，再在下一条恢复，轮廓也出现波浪。

head.py:134–143 的 row 返回 hasSkin=False，可能只是“这条扫描线位于刘海／额头上方”；paired_rows:176–186 却把另一帧此行有皮肤时的无皮肤窗口直接移到头壳最左／最右侧。下一条扫描线条件改变又恢复 crown→neck 的中央轴，导致条带 lattice 的分区边界瞬间跳位。

已从真实 C7 数据核对：

| 角度 | 相邻模型 y | common 分区最大 X 跳变 | 状态 |
|---|---|---:|---|
| 78.75° | 270→271 | 153.24 px | hasSkin [False,False]→[True,False]，对应分界 x454.65→301.42 |
| 123.75° | 287→288 | 157.47 px | 后脑／有脸帧行分区突然换侧 |
| 235° | 279→280 | 152.21 px | 镜侧同类分区切换 |

最低修复：明确区分 frame.face is None 与本行 skin is None。真后脑帧的虚拟窗口应根据相邻脸朝向在整个高度保持同一闭合侧；有脸帧被刘海遮住的行，应在本片脸局部轴／邻接有效窗口之间连续闭合。不要按另一个输入“此行碰巧有无肤色”切换整条的语义。对窗口坐标沿 y 作连续插值，并保持 left≤w1≤w2≤w3≤w4≤right；顺序正确仍不代表相邻行斜率合理。

验收：先看 78.75、101.25、120、123.75、130、235、236.25、303.75 的头部；再看以下真实动作。连续 1 模型像素的行不能由隐藏状态切换制造 100–150 px 横跳。不能把拒绝自交 quad 数为零当成通过。

- 左回眸：[0–.504 秒，每 .0336 秒](../../test-results/review-pass-3/front-fix-7/back-left-look-back-dense.png)。.0672 秒为130.63°开始明显；.1008 秒125.64°、.1344 秒119.21°大面积发壳波浪；.3024 秒76.68°额头及下发又出现断带。
- 右回眸：[同采样](../../test-results/review-pass-3/front-fix-7/back-right-look-back-dense.png)。.1008 秒234.36°、.1344 秒240.79°后脑起伏；.3024 秒283.32°及.4032 秒305.64°又有发壳／颈部横向破碎。
- [实际时间／角度表](../../test-results/review-pass-3/front-fix-7/look-back-dense.json)。这是完整 Renderer 的回眸路径，不是人为构造一个运行时不会到达的角度。

## P1-4：分段中点仍直接换发纹，轮廓配准不能证明转头连续

head.py:202 的 preferred=first if t<.5 else second 让所有非零头发窗口同时换材质。原图发顶分缝、卷发线、下缘卷束不相同；即使两侧外轮廓落在同一位置，内部发纹也会在中点换形。

证据：[78.75° 中点](../../test-results/review-pass-3/front-fix-6/boundary-78.75.png)、[123.75° 中点](../../test-results/review-pass-3/front-fix-6/boundary-123.75.png)、[303.75° 中点](../../test-results/review-pass-3/front-fix-6/boundary-303.75.png)。±.01° 的相邻图之间可见发顶分缝和卷束改形，远大于 .02° 应有的微小位移。该问题与 P1-3 叠加，应在修好行几何后再隔离量化，不能把几何修完就自动删除此项。

辅助差分：[boundary-delta.json](../../test-results/review-pass-3/front-fix-6/boundary-delta.json) 比较同镜头 ±.01° 两张 RGB32 图，以离灰底任一通道大于16的像素并集作头部有效范围。该范围中任一 RGB 通道差大于20的像素占比，在78.75°为28.03%、123.75°为34.13%、303.75°为28.56%；12个中点均在23%–36%。这些数值支持已看到的换发纹现象，不把差分阈值自身当成视觉验收标准。

最低修复方向：为相邻片定义共享的发顶分缝、刘海束界、侧卷根／尖，使内部材质也有对应；只在不可见区域或已配准的小发束局部转换。若两张原画的卷束拓扑不同，应补兼容的中间原画／拆独立发束，不能用整头透明重影掩盖。禁止重新把整块后脑纹理挤成脸。

验收：逐一停在每个头材质中点±.01°，背景、脖子和五官固定比较发纹；之后以实际 turn/spin/look-back 连续播放确认无发型瞬变。外轮廓连续、没有双头只是必要条件。

## P2-1：细横条是实际采样／拼条缺陷，与上述大波浪分开修

native 的静止 front、front-left、right 等也有多条细横线，原 PNG 中没有。它们在真实 Qt 灰底合成、mapped hair 单层及 RGB32 输出中均可见，不能归因于低 alpha 查看器噪点。

silhouette.py:27–58 每个三角形使用独立的非整数 bounded source QRectF，且临边使用扩 .5 的 clip；同一原图在不同条带可能产生不同采样相位。这一机制为需要 A/B 验证的定位，不能仅凭代码阅读断言它是全部细条的唯一原因。

最低验证：同一 native 角度只在诊断进程中改为整幅纹理采样，或 floor/ceil 到整像素的源边界，保持 target 网格完全相同，对比 mapped hair。若细条消失则采样路径修复成立；若只减少，继续查 row rounding 和相邻 quad 的重叠。P1-3 的百像素几何跳变须单独修，不能指望整数源采样修好它。

## P2-2：0°／180° 整耳的前后层级突然交换

证据：[正面 ±.01°](../../test-results/review-pass-3/front-fix-6/boundary-0.png)、[背面 ±.01°](../../test-results/review-pass-3/front-fix-6/boundary-180.png)。背面最明显：左耳的一小块三角突然消失，右耳出现；正面也会左右轮换。耳叶此时仍有面积，不是恰好 edge-on 隐藏后才换面。

根因位于 head.py:331、348–369：sign(sin(angle)) 直接选 near，另一整只耳在 surface 前画；越过符号边界后，两只耳交换 surface 前后。耳背纹理已经映射到相同 alpha 并平滑混色，此项是遮挡层级问题，不应回滚到旧耳背轮廓。

最低修复：让每只耳按相对于头壳的局部深度／遮罩连续显露，尤其0°和180°附近两耳都由同一头壳遮挡规则处理。可在局部遮挡 mask 内过渡前后贡献，不能让整个非零耳叶瞬间换层。角根也共用此层序，应同时检查，但本轮明确看到的跳变证据为耳叶。

验收：0、180±.1、±.01 和实际跨越该角度的连续转头，耳轮廓、耳尖、肤色均连续；同时保留135/315的同 alpha 前背混色与110–113/244–248的合理投影宽度。

## 点头、侧面鞠躬与五官的具体观察

证据：[C7 front nod 近景](../../test-results/review-pass-3/front-fix-7/front-nod-close.png)、[left nod](../../test-results/review-pass-3/front-fix-7/left-nod-close.png)、[right bow](../../test-results/review-pass-3/front-fix-7/right-bow-close.png)。正面头顶较稳定，眼／脸向下、刘海随面部曲面变化；侧面后脑与面部绕颈产生不同运动。因此不能继续引用旧报告说本版点头“只有整体 y 平移”。不过当前坏皮肤和横条使额头体积难以判断，最终自然点头应在 C8 清晰合成下再确认，尤其极值时下巴—领口间隙与角根是否同步。

五个有脸方向的差分已逐张看过：[front](../../test-results/review-pass-3/front-fix-6/faces-front-20.png)、[front-left](../../test-results/review-pass-3/front-fix-6/faces-front-left-20.png)、[left](../../test-results/review-pass-3/front-fix-6/faces-left-20.png)、[right](../../test-results/review-pass-3/front-fix-6/faces-right-20.png)、[front-right](../../test-results/review-pass-3/front-fix-6/faces-front-right-20.png)。19种基础表情与说话嘴的静态可辨性已有改善，不把旧 flip、单眼 wink 和泪滴丢失问题重复列成当前失败。下一轮还必须复核脸差分混合中断的0秒连续性、真实说话开闭周期、nod/look-back 叠表情，以及结束／取消后面部与姿态恢复；静态20格没有覆盖这些时序性质。

## C7 回贴修复与下一轮顺序

[C6 真实 Animator 全身](../../test-results/review-pass-3/front-fix-6/actual-full-8.png) 中衣片、身体和尾的明显错位并非人工清空 transforms 造成；[C7 同镜头](../../test-results/review-pass-3/front-fix-7/actual-full-8.png) 确认 raster_mesh 原点变量修复后相应部件归位。C6 失败记录保留，C7 不重复此缺陷。

下一轮先复核 native 的 skin＋hair 同原图，再修/验连续窗口行几何，再看材质中点、耳遮挡边界，最后回到完整动作和表情组合。主上下文已告知正在修肤色源、全头连通 mask 与源采样，但这些 live 改动不属于 C6/C7，须以新的冻结候选实际渲染后更新结论。本审核未修改生产实现、rig 或素材。
