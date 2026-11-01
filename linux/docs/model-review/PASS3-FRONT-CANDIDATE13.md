# 第三轮：Candidate 13 颈部连通域定向复核

**结论：C12 的 P1 成串透明孔已修复；四个主颈块及悬空颈外边清除，头颈连接保持。仍有 P2：无条件半径3膨胀擦掉了颈块与合法头发相接的内部描边。** 本轮可确认大问题收敛，但该发线损伤尚未完全收尾。

本轮仅检查225/270/247.5/292.5四头方向、左右回眸/取消及相邻发线/身体颈领。没有重新进行全部动作、五官或身体专项，不扩展模型方案。此前失败记录见 [C10/C11](PASS3-FRONT-CANDIDATE10.md) 与 [C12](PASS3-FRONT-CANDIDATE12.md)。

## 冻结与证据

冻结 `linux/test-results/review-pass-3/candidate-13/linux`；2026-11-01 18:17:37 +08:00 校验 **225 文件全部匹配**，见 [verification.json](../../test-results/review-pass-3/front-fix-13/verification.json)。snapshot SHA-256=`9c84cfaccb9b27fcd977c7776abb10e610523e4a0c1ca62699386dbca2096302`；head.py=`a4bbb76d12c9caaa011afc2f61e5ac86197d6bcaedcc5a6d4c6c42cbe4eecdef`；head.json=`afa8a2bfd796f568488d5232d28cdcc186d10593c968ea7e25480e91114727b4`。render.py、motion.py及后侧rig同C12。

使用live venv、冻结PYTHONPATH、offscreen实际Qt渲染和RGB32灰底。原图、冻结/live实现均只读。诊断与内存试验位于 ignored 的 [front-fix-13](../../test-results/review-pass-3/front-fix-13/)。

四方向近照：[C10/C11/C13同镜头对照](../../test-results/review-pass-3/front-fix-13/neck-comparison.png)。左右回眸实际采0/.1008/.1344/.168/.2352/.3024/.4032/.504/.55秒；.55秒取消后0/.04/.08/.12/.18/.22秒；另查R/BR/FL/L idle、nod .6、tilt-left/right .9秒。上述图均已实际查看。

| 项目 | 结果 |
| --- | --- |
| C12侧发圆孔 | **修复通过**；R/247/292和FL/L发束恢复实体，原零星暖色纹理不再被扩成孔 |
| 四个主颈块 | **清除通过**；未见原粉色截底矩形/窄岛重新出现 |
| 悬空颈外边 | **清除通过**；R的U形颈底、225/247的下垂线已去掉 |
| 相邻发线 | **P2未通过**；BR中央短卷边缘明显缺紫线，R前束贴颈处同类损伤 |
| 左右回眸及取消nape | 未见新的中央连接空隙；不需要另补桥片；身体后发旧悬空短卷也未返回 |
| R292右上小肤色三角 | 本轮建议保留；完整姿态中由下巴与两侧头发围合，未见悬空块或额外截底，不能仅因非嘴连通就继续扩大ROI |

[左回眸](../../test-results/review-pass-3/front-fix-13/back-left-look-back-targeted.png)、[右回眸](../../test-results/review-pass-3/front-fix-13/back-right-look-back-targeted.png)、[左取消](../../test-results/review-pass-3/front-fix-13/back-left-cancel.png)、[右取消](../../test-results/review-pass-3/front-fix-13/back-right-cancel.png)、[右侧动作](../../test-results/review-pass-3/front-fix-13/right-neck-actions.png)保留实际连接证据。当前仍是有限方向原画帧；这些定向结果不等于连续3D转头通过。

## P2：膨胀没有区分颈外边与颈/发内部交界

C13 `head.json.neckMaskRegions` 的矩形只用于选择真实连通分量，这一点正确。`_skin_rows` 在ROI内洪泛并选面积≥32的最大组件，已避免把白发噪点作为颈岛。但随后仍对整个组件周围所有半径3采样格无条件清零。颈组件上方贴着短卷时，原本属于发束的紫色边线同样在距离3以内，于是被擦成无描边的白色梢。

最清楚位置为统一头坐标BR中央短卷约 x400–447、y449–465；R前束与颈相接的内侧轮廓也受影响。它比C12的密集大孔轻，但对原画轮廓的改动是真实的，不能写成“相邻发线完全保持”。

最低修正是在现有颈组件选择之后分开处理：组件内部照常清空；对于外扩halo中的非组件像素，只有它同时接近**未修改原图的透明外域**时才清理。这样真正露在外面的颈描边会去掉，两侧都是实体的颈/发内部界线会保留。透明外域必须取原图alpha，不能取刚刚清空颈之后的alpha，否则所有内边也会被判为邻接透明。

## 内存试验：外域约束能恢复相邻发线

[halo-trial.png](../../test-results/review-pass-3/front-fix-13/halo-trial.png)左列C13、右列内存试验。脚本 [halo-trial.py](../../test-results/review-pass-3/front-fix-13/halo-trial.py)重新读取未修改原生crop，保持C13的ROI/最大组件选择和组件内部mask，仅让半径3 halo在其原始alpha邻域含alpha<32时清零。脚本只替换当前诊断进程的 `HeadFrame.image`，未写生产文件或素材。

实际图显示：BR中央两束短卷的连续紫色轮廓恢复，R/247/292贴颈发线也恢复；大颈岛及悬空颈外边仍被去掉，没有C12成串孔洞。试验保留的halo采样格数量与部分世界坐标在 [halo-trial.json](../../test-results/review-pass-3/front-fix-13/halo-trial.json)，只作定位，不作为视觉通过依据。

该试验是可实施的小范围修正建议，不替下一冻结运行版预先验收。下一轮只需同样四方向近照及左右回眸/取消复核，重点确认内部发线保留而悬空颈边未回归；不用新增桥片或继续扩大R292小三角的ROI。
