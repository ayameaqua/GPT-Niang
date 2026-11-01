# 第三轮：Candidate 14 颈部遮罩收尾复核

**结论：本次指定的定向修复项通过。** 四个方向的主颈块及悬空颈外描边保持清除；C13 被擦掉的相邻发线恢复；C12 的成串透明孔没有返回。左右回眸在 .3024 秒取消的实际序列未见新头颈断口、悬空旧侧卷或附属部件丢失，不需要补 nape 桥。

此结论仅覆盖本轮四方向、指定回眸/取消及颈部遮罩收尾，不是重新验收全部动作/表情/身体/尾巴。当前仍是有限原画方向帧，连续3D转头不在通过结论内。此前各候选的失败记录继续保留：[C10/C11](PASS3-FRONT-CANDIDATE10.md)、[C12](PASS3-FRONT-CANDIDATE12.md)、[C13](PASS3-FRONT-CANDIDATE13.md)。

## 冻结与方法

冻结目录 `linux/test-results/review-pass-3/candidate-14/linux`。2026-11-01 18:24:19 +08:00 校验 snapshot 所列 **225 文件全部匹配**；[verification.json](../../test-results/review-pass-3/front-fix-14/verification.json)保留完整记录。

| 文件 | SHA-256 |
| --- | --- |
| snapshot.json | `0703d13be410f4b34a0ad71f160faa3086a948d275fc0137e1c63604c5792568` |
| model/head.py | `beedfeb5882701c112615fe656e7db1cc821f43adf19206e21d2cc7c8b8f62dc` |
| model/render.py | `87f98c56ef2151d4cfa28eb7852ab8971045a7d2c26ff63a6e9c1e0b86bf437c` |
| model/motion.py | `f44f808a6170a39134f13aa335ee4761921860164b821c8172b56524ec52e139` |
| models/dragon/head.json | `afa8a2bfd796f568488d5232d28cdcc186d10593c968ea7e25480e91114727b4` |

与C13快照相比，运行实现的变更仅为 `head.py`；另有文档、progress及测试文件变化。render、motion、head绑定JSON与后侧rig未变。

用live `linux/.venv/bin/python`，冻结PYTHONPATH、`QT_QPA_PLATFORM=offscreen`、`PYTHONDONTWRITEBYTECODE=1`，实际调用Qt renderer。所有判断图先用QPainter合成RGB32灰底。动作按不大于1/120秒步进，静态clock=1。没有修改冻结/live生产代码或素材，没有重跑完整动作矩阵。

## 实际查看与逐项结果

| 方向/项目 | 实际结果 | 判定 |
| --- | --- | --- |
| back-right 225° | 大粉色颈带及下垂外边未返回；中央两束短卷的紫色下轮廓恢复 | 通过 |
| right 270° | U形颈底线与主颈块清除；前侧长束贴颈边重新连续，没有圆孔 | 通过 |
| right247 247.5° | 竖颈边清除；两侧卷发实体、卷尖及轮廓保留 | 通过 |
| right292 292.5° | 主颈岛清除；脸前发束内侧线恢复，未新增下巴缺口 | 通过 |
| R292右上小肤色三角 | 保留；由下巴和两侧发束围合，完整姿态未见悬空块或额外截底 | 保持现状，不扩大ROI |
| 左/右 .3024秒回眸 | 新方向头与身体颈领相接，旧侧发残片未重现，角/耳/呆毛正常 | 通过指定时点 |
| 取消后0/.04/.08/.12/.18/.22秒 | 即时图不跳；随后按有限方向帧恢复，未见新断颈或残片 | 通过指定恢复序列 |

四方向均实际查看完整头和2.5倍颈部近照：[四头完整图](../../test-results/review-pass-3/front-fix-14/heads-4.png)、[C10/C13/C14近照对照](../../test-results/review-pass-3/front-fix-14/neck-comparison.png)。后者第三列可直接看到本轮恢复的发线；不是仅由mask参数推断。

[左回眸/取消](../../test-results/review-pass-3/front-fix-14/back-left-cancel.png)、[右回眸/取消](../../test-results/review-pass-3/front-fix-14/back-right-cancel.png)均已实际查看。取消前与取消后0秒的完整RGB图逐字节一致，见 [cancel-zero-delta.json](../../test-results/review-pass-3/front-fix-14/cancel-zero-delta.json)；该数值只补充即时连续性，恢复过程仍以实际序列判断。

## 修复成立的原因与边界

C14仍由已标定ROI选择真正的颈部主连通块，组件内部清空；组件外的halo只在其半径3邻域存在**原始未mask alpha<32**时清理。于是暴露在透明背景边的旧颈描边会去掉，颈与头发两侧都为实体的内部界线得以保留。源图中的零星暖色点不再获准独立扩张；因此同时解决了C12孔洞与C13发线损伤。

本轮范围内未发现仍需修复的P1/P2。无需新增桥片、修改原画或继续扩大暖色清理区域。若未来更换core素材、改变neck/box或扩展转头实现，这组ROI与原alpha外域约束仍需按实际图重新验证，当前结果不外推到那些尚未发生的改动。

诊断脚本及原始截图保留在 ignored 的 [front-fix-14](../../test-results/review-pass-3/front-fix-14/)，本子代理仅新增本报告及诊断文件，未提交或修改运行资产。
