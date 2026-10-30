# 生成记录

2026-10-31，全部使用内置 `image_gen.imagegen`，`transparent_background=true`。原角色参考为固定 Coopanion v1.1.0 发布包的 `thumb.png`，SHA-256 见 NOTICE。生成结果保留原透明通道；工程脚本只按记录的矩形切割、裁到 alpha 边界并建立绑定。以下是实际提示词。

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

当前用于试验绑定；脸部仍为整片，侧面表情与口型请求会转回原基底。裙长和手臂连接需要后续美术检查。

## source/back-dress.png

参考：原包缩略图、背面拆件草图。

```text
Use case: precise-object-edit. Make ONE isolated production cutout of ONLY the torso and dress seen from directly behind for the SAME chibi girl. Input1 character costume reference, input2 exploded parts reference. Correct the body from upper row third slot of input2. Remove ALL arms, hands, sleeves, head, hair, horns, wings, tail and legs. Keep ONLY the BACK neck/shoulder skin stumps, back bodice with white ornate fabric, waist and full rear white/lavender long skirt ruffles. Arms are separate sprites: absolutely NO painted hands, fingers, forearms, upper arms or hanging sleeves anywhere on this body cutout. It must be a proper rear garment design, not a front apron with chest ornaments. Visible pale back neckline with a small bow closure; skirt rear folds consistent with the original dress. Complete hidden fabric under the long hair/wings and under arm attachments so they can move away. Preserve the original white and lavender palette, fine anime linework and two-head-tall chibi body proportions. Center this single arm-less head-less back dress sprite on a fully transparent canvas with ample margins, no other objects, no text, no shadow.
```

另一次透明边缘清理实验没有采用；原图在 Qt 不透明背景合成中不存在查看器显示的彩色边缘噪点，因此没有用程序破坏或阈值化其视觉 alpha。
