# 候选11：BL／BR 后发上缘与尾巴遮挡定向复核

**本次定向修补通过：回眸旧短卷残留、BR 暖色后颈块已清理；BL／BR 长发下段、尾根遮挡与尾叶完整性保留。** 24 帧中未发现本范围新增 P1/P2。此结论承接 C10 的尾巴／原生衣物专项，不代表完整 V1、所有动作或全部头部方向已经通过。

## 冻结与范围

- 冻结目录：`linux/test-results/review-pass-3/candidate-11/linux`，其父级 snapshot.json 实际列出 225 文件。
- 文件集合 SHA-256：`0d5e4f57b9b07bae3137854e022812ab704185cfedb3a50d4170466613dd5eba`。
- Qt offscreen、768×768、不透明灰底，实际运行冻结实现；采样前后 hash 一致。未修改生产代码、素材或冻结树。
- 每个 BL／BR 分别采 native 1 帧、look-back `0/.28/.56/1.4/2.52/2.8`、land `.325`、carried `.75`、spin `.24/.8/1.36`，共 24 帧、10 组。
- 脚本：`linux/test-results/review-pass-3/tail-c11-check.py`。全部证据及记录在 `rear-candidate-11/`。`compare.py` 生成同姿态 C10／C11 对照，`targeted-rollup.json` 保存结果。

与 C10 冻结相比，生产相关变更落在 head.py、render.py 和 BL／BR rig 数据；原生长发／尾巴 PNG 没有重画。新增的 model_motion_evidence.py 为工具文件。此次没有重复跑 C10 的 283 帧全批动作，也没有把 C11 小范围结果扩展到未采样状态。

## 后发上缘与回眸

C10 的 hair-back 从原 head.png 的 v=.4 开始、到 v=.52 淡入：对应 BL world y357.382→445.097，BR y349.265→434.545。这段仍含旧头部短卷，头转走后会留在旧身体方向的耳侧／颈侧位置。

C11 保留原 box 与整个下段，只调整两个 `rig.json` 的 hair-back `sourceWindow`、`fadeTop`：

| 方向 | 新起始 v | 新淡入结束 v | 对应 world y | 原 box 保持 |
|---|---:|---:|---|---|
| BL | .567750409 | .608792607 | 480→510 | x185.788、y65、470×730.955 |
| BR | .583961737 | .626175839 | 480→510 | x189.500616、y65、470×710.663 |

实际全身对照确认：BL／BR look-back `.56` 和 `1.4` 的旧侧面悬空短卷消失，颈部与新头帧、长发上缘仍连接；没有形成横向硬截面、大片缺口或断发缝。BR native 原先露在短发和长发之间的独立暖色后颈块已消失。侧向与回程 `.28/2.52` 的侧向头帧以及开始／结束也已看，未见旧短卷重新浮现。

![同姿态 C10 与 C11：后颈色块及回眸旧短卷清理](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/rear-candidate-11/c10-c11-upper-hair-comparison.png)

以上只复核后发上缘与头颈交接；12 个头部方向帧的身份、脸部细节及各姿态整体验收仍由头部专项负责。

## 长发长度和尾巴没有被误裁

对同一 native 姿态的实际 hairBack 隔离图比较，screen y≥450 区域每个像素完全一致，最大通道差为 0。下表的发尾行采用 alpha≥128、每两行扫描；可见尾像素由全身图与禁画尾巴图的 RGB 任一通道差≥12 定义。

| 项目 | BL C10→C11 | BR C10→C11 |
|---|---|---|
| 长发最下采样行 | 606→606 | 594→594 |
| 可见尾像素数 | 8142→8142 | 9556→9556 |
| 可见尾范围 x/y | [346,573,546,681]，不变 | [139,556,356,683]，不变 |

这些数据与实图相符：卷束的中下段宽度和长度保留；尾根仍从长发后侧接入，粗干从下缘绕出，紫叶仍完整在发外。没有因去掉上缘短卷而暴露尾巴切口，也没有将长发缩成 C9 的窄条。

## 落地、拎起与收尾遮挡

BL／BR land `.325` 和 carried `.75` 已看全身：发尾与尾干同时跟随身体，长发没有吞掉紫叶或压出第二尾尖。落地时粗干仍有厚度，没有白色截平线；拎起时根部继续藏在长发与身体后缘，未出现悬空断根。24 帧尾根映射与 `upper(coccyx_point(angle, seat))` 的最大误差为 0；该数值仅作为实图连接关系的佐证。

两组 spin 的 `.24/.8/1.36` 共 6 个 fully tucked 样本全部为 0 可见尾像素，已查看整身及裸尾隔离表。去除较高位置的旧发片没有使细尾边、针状物或第二紫叶从发缝泄漏。方向切换仍为原生八向帧动画，本次没有把它声称为连续三维转向。

![BR 回眸全过程：长发与尾叶保留](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/rear-candidate-11/look-back-back-right/full-contact.png)

![BL 收尾三个时点](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/rear-candidate-11/spin-back-left/full-contact.png)

## 接受边界

接受 C11 对 BL／BR 后发上缘的清理，以及这次定向样本中的长发长度、尾根遮挡、落地／拎起尾形和收尾隐藏。未发现需要新增修复的 P1/P2。

C10 报告保留的范围限制继续有效：BL／B／BR 请求 jump 会先自动转 FL，后续跳跃不能称作原地背向跳；八向切帧不能称作连续三维转身；完整 V1、所有动作组合与头部专项仍需各自验收。此次不重跑背向 jump，也没有用后侧 land 样本替代未实现的背向跳跃。
