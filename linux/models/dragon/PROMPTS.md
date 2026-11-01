# 生成记录

2026-10-31，全部补画使用内置 `image_gen.imagegen`，`transparent_background=true`。原角色参考为固定 Coopanion v1.1.0 发布包的 `thumb.png`，SHA-256 见 NOTICE。首轮的矩形裁片方案已由完整主体提取替代；生成源图不覆盖，运行裁片保留被选择主体及邻接抗锯齿的原RGBA。以下是实际提示词。

## source/turnaround.png

参考：原包缩略图。

```text
Use case: identity-preserve. Asset type: production character turnaround for a Qt layered animated desktop companion. Input image 1 is the exact character identity/style reference. Draw the SAME chibi dragon girl, matching her two-head-tall proportions, delicate white/lilac hair, white segmented horns, purple eyes, pointed ears, white ornate long dress with lavender underskirt/side ruffles, knot/flower hair ornament, lilac bat wings, white scaled tail with purple tip. Create one clean 4-column x 2-row orthographic turnaround atlas with 8 equally spaced full-body neutral standing figures, exact order: top row FRONT, FRONT-LEFT three-quarter (faces viewer left), LEFT PROFILE, BACK-LEFT three-quarter; bottom row BACK, BACK-RIGHT three-quarter, RIGHT PROFILE, FRONT-RIGHT three-quarter. Transparent background in all cells, no floor, no shadow, no labels/text, no grid marks, no extra characters. Full horns, tail, wings and feet must fit each cell with generous margin. Feet aligned on same baseline, identical scale and design. Neutral relaxed arms at sides. Preserve asymmetrical hair ornament on same anatomical side, and correct opaque back-of-head and dress back: do not paste eyes on rear views. The result will be sliced into eight view assets; keep EVERY figure wholly inside its own cell, and make each distinct orientation anatomically clear. Soft clean anime line art and pastel shading exactly matching input, not pixel art, not 3D.
```

该图是设计参考，不是已完成的八视角绑定；部分装饰方向和轮廓仍需复核。

## source/back-parts-draft.png

参考：原包缩略图、上述八视角设定图。

```text
Use case: identity-preserve. Production exploded LAYER ATLAS for the exact chibi white/lavender dragon girl in input1; input2 is supporting turnaround only. One asset, one TRUE BACK view looking away, same 2-head proportion and ornate costume. Transparent background. 4 columns by 3 rows of separate opaque painted anatomical parts. Every cell contains ONLY its named separated part, centered, no text/labels/grid, generous empty margins, NO assembled figures. Cell order row-major: 1 complete HEAD seen from behind (horns + top back hair down to neck, NO face/eyes, hair below shoulders excluded); 2 LONG BACK HAIR from neck to calves (upper attachment fully painted, no head/horns); 3 TORSO + long white dress and lilac skirt ruffles to hem, viewed from rear with reconstructed hidden surfaces, no head/hair/arms/wings/tail/legs; 4 LEFT ARM including shoulder sleeve, elbow, hand, hanging down with rounded fully painted attachment; 5 RIGHT ARM same; 6 LEFT lilac bat WING including full root; 7 RIGHT lilac bat WING including full root; 8 whole WHITE SCALED TAIL lavender pointed tip, curving left as seen from back; 9 LEFT LEG with shoe, ankle frills (entire thigh to toe, even hidden areas); 10 RIGHT LEG with shoe, entire thigh to toe; 11 white/lavender skirt FRONT OVERLAP strip seen from back, for layering across hip; 12 EMPTY transparent. Painted in same delicate anime linework, white/lavender shading as source. Correct back-of-dress and opaque back-of-hair. Do not include eyes, mouth or nose anywhere. No shadows, no background, no extra accessories. All parts must be independently usable sprite cutouts with clean alpha, maintain original proportions within each part, fit cells fully. This will be mechanically sliced into cells and bound to joints; never let a part cross a cell border.
```

躯干单元错误地附带了手臂，不用于绑定；以下单独补画替换它。实际格子不是严格等分，切割矩形由 `assemble_dragon.py` 明确记录。

## source/left-parts-draft.png

参考：原包缩略图。

```text
Use case: identity-preserve. Production sprite LAYER ATLAS, not a completed character illustration. Same exact chibi dragon girl identity as image 1, delicate white hair, lavender horns/wings, ornate white and lilac dress, scaled white tail, two-head-tall proportions. Draw TRUE LEFT PROFILE (nose points left) separated parts, all on transparent background. A strictly regular 4 columns by 3 rows grid, 12 equal rectangular cells, with every part inside its cell and ample empty margin. No text or grid lines. Row 1: [HEAD with horns, bangs, ear, violet eye and face, and short neck-length side hair, NO long back hair], [LONG BACK HAIR without head/face/horns, full separate opaque neck-to-calf locks], [TORSO AND SKIRT without head/hair/arms/hands/wings/tail/legs: a headless ARM-LESS ornate dress body, shoulders end as rounded skin attachment stumps], [near ARM from shoulder to hand with sleeve, hanging down]. Row 2: [far ARM from shoulder to hand with sleeve], [near lavender BAT WING including root], [far BAT WING including root], [WHITE SCALED TAIL with lavender pointed tip, same leftward profile direction as character]. Row 3: [near LEG thigh to shoe with ankle frills], [far LEG thigh to shoe], [small ornate WAIST/APRON front skirt overlap, no legs], [EMPTY]. No assembled figure or extra detached parts. All hidden attachment surfaces must be fully painted and opaque. The torso/dress MUST NOT contain any arms or hands; those belong ONLY in their separate cells. Head and hair separate with enough overlap for head rotation. Keep original costume design and painted line quality. These cutout pieces will be individually cropped and attached to animated joints; don't cross cell borders.
```

当前用于身体的试验绑定；头部已由后续空白脸补图替换，口型和眼睛在 Qt 中绘制。裙长和手臂连接需要后续美术检查。

## source/back-dress.png

参考：原包缩略图、背面拆件草图。

```text
Use case: precise-object-edit. Make ONE isolated production cutout of ONLY the torso and dress seen from directly behind for the SAME chibi girl. Input1 character costume reference, input2 exploded parts reference. Correct the body from upper row third slot of input2. Remove ALL arms, hands, sleeves, head, hair, horns, wings, tail and legs. Keep ONLY the BACK neck/shoulder skin stumps, back bodice with white ornate fabric, waist and full rear white/lavender long skirt ruffles. Arms are separate sprites: absolutely NO painted hands, fingers, forearms, upper arms or hanging sleeves anywhere on this body cutout. It must be a proper rear garment design, not a front apron with chest ornaments. Visible pale back neckline with a small bow closure; skirt rear folds consistent with the original dress. Complete hidden fabric under the long hair/wings and under arm attachments so they can move away. Preserve the original white and lavender palette, fine anime linework and two-head-tall chibi body proportions. Center this single arm-less head-less back dress sprite on a fully transparent canvas with ample margins, no other objects, no text, no shadow.
```

另一次透明边缘清理实验没有采用；原图在 Qt 不透明背景合成中不存在查看器显示的彩色边缘噪点，因此没有用程序破坏或阈值化其视觉 alpha。


## 后续八视角补图

以下均使用内置 `image_gen.imagegen`、真实透明背景；提示词原文另存为普通文本，便于复用。

| 制作文件 | 实际提示词 | 参考 |
| --- | --- | --- |
| `source/front-parts.png` | [front-prompt.txt](source/front-prompt.txt) | 原包缩略图 |
| `source/right-parts.png` | [right-prompt.txt](source/right-prompt.txt) | 原包缩略图 |
| `source/front-right-parts.png` | [front-right-prompt.txt](source/front-right-prompt.txt) | 原包缩略图、右侧拆件 |
| `source/back-left-parts.png` | [back-left-prompt.txt](source/back-left-prompt.txt) | `back-reference.png`、`back-dress.png` |
| `source/back-right-parts.png` | [back-right-prompt.txt](source/back-right-prompt.txt) | `back-reference.png`、`back-dress.png` |
| `source/left-head-parts.png` | [left-head-prompt.txt](source/left-head-prompt.txt) | 原包缩略图 |

第一轮右前侧和后侧的错误方向图未采用。后侧最终图依据已生成的背面重新制作；其误加的翼饰和长靴没有用于绑定，改用已有后侧部件。新脸部留白用于独立眨眼、视线、眉毛与口型，不能将制作文件中的空白脸当成最终合成效果。各视角仍有美术精修待办；八视角接触表以实际 Qt 合成为准。

## 按视觉审查补图：source/revision-2/

| 文件 | 提示词 | 参考与用途 |
| --- | --- | --- |
| front-reference.png | 无新生成 | 从已生成的turnaround第一格裁出的正面参考，不是运行分片 |
| front-head.png | [原文](source/revision-2/front-head-prompt.txt) | 原包缩略图、正面参考；单一短发头，保留空白脸，去掉重复发层 |
| front-right-head.png | [原文](source/revision-2/front-right-head-prompt.txt) | 新正面头；向右三分之四头，结饰保留解剖侧 |
| front-dress.png | [原文](source/revision-2/front-dress-prompt.txt) | 清理后的旧正面裙单片；只修掉错误裸肤楔形与内裙瓣 |
| front-right-dress.png | [原文](source/revision-2/front-right-dress-prompt.txt) | 清理后的旧右前裙单片；改短中央前摆、保留侧裙 |
| arm-raised.png | [原文](source/revision-2/arm-raised-prompt.txt) | 原角色缩略图与新正面头；独立张掌举手姿势 |
| arm-point.png | [原文](source/revision-2/arm-point-prompt.txt) | 同上；独立伸食指姿势 |

本轮先尝试的四格衣片和整件新衣裙仍附带袖子/重复侧裙，未导入运行模型，也没有为了适配而强行压缩；改为针对已存在裙片做局部修正。运行模型不直接使用本目录的原始画布，统一按 `source-selections.json` 提取主体，再按 `rig-layouts.json` 绑定。

此前对“查看噪点”的描述不能涵盖真正的高alpha邻格污染。专项审查已区分二者，本轮提取工具删除未选中的连通部件，不对主体全局阈值化透明通道。源PNG保持原样，制作/运行资源SHA-256由组装脚本更新。

## 细节修复补图：source/revision-3/

全部使用内置 `image_gen.imagegen`，保留生成的透明通道；原 PNG 与完整提示词均保存在本仓库。

| 文件 | 提示词 | 参考与用途 |
| --- | --- | --- |
| arm-joints.png | [原文](source/revision-3/arm-joints-prompt.txt) | 原包缩略图、上轮抬手；上臂、前臂袖片、张掌和食指手形四片，供连续肘腕绑定 |
| back-dress.png | [原文](source/revision-3/back-dress-prompt.txt) | 原正背裙；去掉后背错误的尖形围裙，保留后颈小结与外侧褶边 |
| back-left-dress.png | [原文](source/revision-3/back-left-dress-prompt.txt) | 原左后裙、新正背裙；保留左后透视和肩口，改为连续后摆 |
| back-right-dress.png | [原文](source/revision-3/back-right-dress-prompt.txt) | 原右后裙、新正背裙；同上，保留右后透视 |
| rear-limbs.png | [原文](source/revision-3/rear-limbs-prompt.txt) | 原包缩略图、正背臂/腿；后侧近/远手臂、近/远鞋跟四片，对侧逐肢镜像 |

手臂的肩、肘、腕 UV 和后侧四肢/衣片连接点在 `rig-layouts.json` 中手工登记；组装脚本仍只提取原 RGBA，不用程序生成新的角色笔画。后脑/长发的分层区域在运行合成中处理，源图不被改写。缩小预滤波仅用于显示采样，缓存上限64项；不阈值化源 alpha。

## 第三轮尾巴／头部制作：source/revision-4/ 与 revision-5/

全部仍使用内置 `image_gen.imagegen`；生成源PNG未覆盖，提示词保存在同名 `-prompt.txt`。

| 文件组 | 用途与实际提示词 |
| --- | --- |
| revision-4/tail-left、tail-right、tail-back-left、tail-back-right、tail-back | 五份完整方向尾巴；对应 `tail-*-prompt.txt`，经完整主体提取进入 common，尾根／六段UV在puppet.json实标 |
| revision-4/head-left67、head-left112、head-right247、head-right292 | 第一批中间方向头，提示词同名；保留可回溯的备用路径，当前完整头材质使用revision-5 |
| revision-5/core-front、core-front-left、core-left67、core-left、core-left112、core-back-left、core-back、core-back-right、core-right247、core-right、core-right292、core-front-right | 十二份无五官／无附属角耳的干净头；提示词 `core-*-prompt.txt`；head.json登记源裁框、颈点与五官锚点，原生整片绘制，眼口动态合成 |
| revision-5/hairpin、ear-back | 独立发饰和耳背材质；提示词同名；原生角耳轮廓从本机导入PNG只读引用，耳背按相同alpha轮廓取色 |

卷发独立束和共享衣物表面的试验没有通过视觉审查，不作为运行素材发布。颈块／后发的alpha裁区是运行时分层处理，原始生成PNG保持原样；不执行Coopanion脚本。详见[本轮记录](../../docs/model-review/PASS3-FIXES.md)与[来源限制](NOTICE.md)。
