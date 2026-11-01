# 动作状态修复复查：调度、过渡、保持与替换

复查日期：2026-10-31。只读检查，未修改运行代码或角色素材。此报告针对主上下文进行中的一批修复，不是最终视觉验收，也不替代 [原动作／表情矩阵](MOTIONS-EXPRESSIONS.md)。

**首次快照结论：普通路由能够收敛，carry 保持／释放与落地头发更新已修复；发现混合中点漏底、转动中面向请求丢失等五项问题。主上下文已据此修改，第二轮定向复查见第 6 节。首次失败证据保留，不能与后续版本混为一项结果。**

**最终状态复查：第三轮已通过本报告中剩余的持续动作／面向请求交叉替换，以及按来源撤销请求的定向案例。本轮记录的具体状态失败复现均已得到修复验证；视觉重影、关节连接与新手势资产仍需主上下文后续验收。第三轮范围与快照见第 7 节。**

## 1. 快照边界与实测范围

主上下文并行修改专用手掌、指向贴图及渲染，所以本次把三份 Python 源码复制到 ignored 诊断目录，再通过 `importlib` 按原模块名加载快照。以下行号、结果均对应该快照，而非之后的工作树版本。

| 文件 | SHA-256 |
| --- | --- |
| `model/motion.py` | `0405df3a4e291d59b6620446bc48b3c6c7d5f1e71c009167747d75fa6a98a834` |
| `model/render.py` | `8d8a80cb9708d584a97a3d41318959205f8d4df8274bdf6a6901b5a9b6734491` |
| `model/item.py` | `bbdc655f60200f32b82b12c9f61fe10b8fbf182e633f3ca0a202ecccbf1b309e` |
| `tests/test_model_repairs.py` | `3856e8b2e1098a16fde9db34c2b1e6bc54d039b470198bcdfa5e285658afe475` |

快照与诊断脚本：`linux/test-results/review/motion/state-recheck/`，原始数值结果为 `results.json`。图片均由 Qt 先渲染透明图，再合成到 `Format_RGB32` 的 `#bcbcbc` 灰底。代码快照固定；贴图从当时工作树加载，专用手势素材仍在调整，未对其外观作验收结论。

实际运行覆盖如下：

| 检查 | 实际范围 | 结果及限制 |
| --- | --- | --- |
| 独立动作路由 | 8 个初始方向 × 29 个动作；每项推进 `.45 s`，步长 `.01 s` | 232 项，无残留 `pending` 或卡住的 `turn`。这里确认进入动作，不代表长动作已播完或姿态合格。 |
| 替换路由 | 8 × 29 × 29；首动作 `.08 s` 时替换，随后推进 `.45 s` | 6,728 个有序对，无转身路由滞留；不代表替换画面连续。 |
| 取消清理 | 8 × 29；`.24 s` 时开启 speech/listening 后 `cancel`，再推进 `2 s` | 232 项均无幽灵 pending、seat、sleeping、carry、speech、listening 或残留表情。取消本身是硬重置。 |
| 转动期间的脸部请求 | 初始 front/back/back-left/back-right × turn/spin × `.01/.15/.25 s` × expression/speaking/listening | 72 项，走真实 `DragonItem` 公共槽；36 项最终仍在无脸的后三个方向。见 R2。 |
| 视图混合端点 | 每个方向起始的 spin，各 8 个片段的结束前 `1 μs`，128 px 渲染 | 64 项与目标纯视图的预乘字节最大差为 1；此项通过不能证明中点正确。 |
| 视图混合中点 | 8 个相邻方向对，`mix=.5`；另有独立 1×1 不透明白色夹具 | 8 项最大预乘字节误差均为 64；白色夹具 alpha=191，期望 255。见 R1。 |
| 持续状态 | carried 超过 10 s、rear carried→表情回脸→carried→land；sit/sleep 各结束后保持 5 s，再 stand | 保持、恢复与释放数值正确；暂停后状态不变。 |
| 人工逐图查看 | `blend-alpha-leak.png`、`transition-replace.png`、`angry-idle-command.png`、`seat-smooth.png` | 仅这四张灰底接触表；未重做全部方向、表情与新手掌素材的视觉审查。 |

本轮没有声称穷举 `8×29×19` 视觉组合。`seat-smooth.png` 是强制指定 seat、冻结其它姿态的渲染诊断；其余接触表来自具体动作／替换时刻。`72` 项脸部请求使用实际 API，没有用 `set_view` 绕过请求后的路由。

运行方式：

```bash
QT_QPA_PLATFORM=offscreen PYTHONPATH=linux linux/.venv/bin/python linux/test-results/review/motion/state-recheck/recheck.py
QT_QPA_PLATFORM=offscreen PYTHONPATH=linux linux/.venv/bin/python -m unittest discover -s linux/tests -p 'test_model*.py' -v
```

本次现有测试为 **22 项中 21 项通过、1 项失败**。失败是 `test_checked_in_views_and_hashes_render_without_the_private_source_pack`：`back/arm-far.png` 文件 SHA 已是 `c41e427d…`，清单仍为 `f7658fad…`。素材仍在制作，因此记录为收尾时必须重建清单并复跑的检查，不能写成整套测试已通过，也不能据此否定已通过的运动状态断言。

## 2. 已确认生效的修复

| 修复点 | 证据 | 本轮结论 |
| --- | --- | --- |
| angry/scared 不再覆盖活动手势 | `test_expression_does_not_replace_active_hand_gesture`；front/raise-both 的两臂角度与 neutral 相同 | 活动手势保护生效；进入／退出情绪基础姿态仍有 R4 跳变。 |
| carry 独立权重 | `.4 s` 后与继续 10 s 后均 `carry=1`，臂角为 `60/-80°`；根部保持约 `-30` 位移 | 不再在 carried 的 1.5 s 时长结束后掉回站姿。 |
| carry→rear 表情路由 | `back/carried` 持有时请求 happy：`pending=carried`，转身期间 carry 始终 1，结束恢复 carried | 此非转动中的请求路径能够保留持有状态。 |
| carry→land | 同 clock 切换时仍 carry=1；`.11 s` 后约 `.5`，`.23 s` 后 0 | 释放渐变有效。`cancel` 清零是显式重置语义，不作为渐变失败。 |
| land 的头发 warp 回填 | `motion.py:303–304` 在 land 修改后写回；现有回归通过 | 原始 source 的 hairBack／hairFront 均能获得落地扰动。 |
| run／bow 的方向符号 | left/right run 与 bow 断言通过；front run upper 无 roll；back 分支读码同 front | 身体前倾符号已分方向。此结论不涵盖每一条肢体和新贴图的视觉质量。 |
| 手势／鞠躬／坐姿的先转向 | 232 项路由结果 | 五个 hand gesture 进入 front，bow 进入 left/right，sit/sleep 进入 front-left；未发现路由自循环。 |
| rear 普通表情请求 | 非 turn/spin 时能先 turn 至 front-left；profile 请求保持方向 | 单次路径有效；转动中的请求见 R2。 |
| sit/sleep 持续状态 | 完成后继续 5 s，seat=1；sleeping 仅 sleep 保持 true；stand 后均归零 | 坐与睡的持有语义没有因透明度过渡而丢失。 |
| seat `.5` 阈值 | `render.py:382–386` 使用 smooth alpha；实际查看 `.49/.50/.51` | 原先一次性的硬切已消失；中间的双轮廓仍是视觉限制，见第 4 节。 |

## 3. 需要修复的问题

### R1 — P1：PLUS 与 painter opacity 组合没有实现预乘线性混合

位置：快照 `render.py:341–349`。

当前先用 `opacity=1-mix` 画第一幅，再设置 `CompositionMode_Plus` 和 `opacity=mix` 画第二幅。在当前 Qt 栅格路径中，这不等于 `first*(1-mix)+second*mix`：加法饱和与 opacity 插值的组合会降低重叠区 alpha。

可独立复现，不依赖任何角色素材：两张 `Format_ARGB32_Premultiplied` 的 1×1 opaque white，在 `.5/.5` 混合后实际 raw BGRA=`[191,191,191,191]`，应为 `[255,255,255,255]`。8 个真实相邻视图对在中点与线性期望的最大字节差均为 64。64 项端点测试最大差仅 1，因此现有“有 mix”“端点到达”断言会漏掉此问题。

已查看证据：`linux/test-results/review/motion/state-recheck/blend-alpha-leak.png`。第三栏为当前实现，会漏灰底；第四栏是诊断脚本先预加权后全 opacity PLUS 的参考结果。参考仍有两姿态重影，但没有同样的混合公式错误。

建议修法：分别把 first/second 以权重画到各自透明的预乘 buffer，再以 `opacity=1` 的 PLUS 相加；或者直接对四个预乘通道进行线性插值。实测前者的白色结果为 `[254,254,254,254]`，仅有量化误差 1。不要只把第一幅改成另一种 composition mode，然后仍把半透明 opacity 放在 PLUS 步骤上。

回归／验收：增加 opaque/transparent/部分 alpha 的独立颜色夹具，mix 取 `0/.25/.5/.75/1`，预乘 BGRA 与公式差应不超过 1–2；纯 opaque 重叠区不得掉到约 191。之后在灰底逐图检查 8 个相邻方向中点。数值通过后，双轮廓和画风差异仍需单独视觉判断。

### R2 — P1：转身／转圈期间的面向请求被丢弃

位置：`motion.py:88–97`，特别是 `self.action not in ("turn","spin")`；`item.py:199–211` 的当前 view 检查。

复现 A：`front → play(turn) → advance(.01) → setSpeaking(True)`，转身完成后为 `back`，speech 仍 true，但没有可见口型。请求时当前 view 有脸，所以 `item.py` 连面向请求都未提交；它没有检查当前转身的终点。

复现 B：`back → play(spin) → advance(.15) → setExpression(happy)`，请求时为 back-right，`set_expression` 因 action 为 spin 跳过转向，spin 最后回到 back。表情值已更新，但视觉目标没有实现。listening 同类问题。

72 个实际公共 API 样本中，36 个最终仍在 back/back-left/back-right。其余最终有脸的一半是既有 turn/spin 目标恰好有脸，不是请求被正确调度的证据。

建议修法：把“需要可见面部”作为独立意图保存，并在 orientation 过渡完成时消费；或者重定向目标，但保留当前 pending 动作并保持视角过渡连续。`setSpeaking/Listening` 应统一调用该路由，而不是只看当前离散 view。**不要简单删除 guard**：直接再次 `play(turn)` 会重置 elapsed/pending，可能造成抖动、手势队列丢失或反复重入。

建议明确取消规则：后来的显式 `setView`／reset 可以清除面向意图；`setSpeaking(False)`／`setListening(False)` 应取消仅由该状态产生、尚未执行的面向请求，不能清掉用户仍需的 expression 面向请求。

回归／验收：上述 72 项都应在有限时间内结束于允许展示面部的方向；另外覆盖 auto-turn→pending hand gesture 中插入 expression/speech/listening，确认 pending 只执行一次、不丢失、不循环。若产品明确允许转圈优先，应在转圈后自动兑现尚未取消的面向意图。

### R3 — P2：替换动作会丢失正在混合的视角，立即回跳

位置：`motion.py:105–136` 重置 action/elapsed；`motion.py:188–195` 只在 action 为 turn/spin 时生成 blend。

复现：front 执行 turn，在 `.08 s` 时 Pose 为 `front + front-left*.896`，调用 `play(stand)` 后不推进时间，立即变成纯 front。实际灰底接触表 `transition-replace.png` 第一、二栏可直接看到轮廓回跳。替换为其它动作／新的自动转向也会从当前离散 `self.view` 重起，丢弃已显示的混合部分。

6,728 个替换对的 liveness 通过仅证明不会卡住，不能证明这一连续性。

建议修法：让朝向过渡成为独立于 action 的状态，保存连续角度或 segment+mix，新动作使用该状态而非把 elapsed 归零即抹掉；较小改法可以先完成当前片段，再兑现新动作，但应明确覆盖旧 pending。只取当前占比最大的视图能减轻跳变，不能做到连续。

回归／验收：在每个片段 mix `.1/.5/.9` 时替换成 stand、carried、另一个自动转向动作；同一 clock 下请求前后首帧应相等或沿已有过渡继续，不能退回 source 端点。显式 reset/cancel 当前为硬重置，若保留此产品语义，应与普通动作替换区别对待。

### R4 — P2：情绪手臂基础层在动作开始／结束时硬开关

位置：`motion.py:275–279`。

活动手势不再被 angry/scared 覆盖，但新条件 `if not a or a=="shiver"` 把情绪臂角变成了离散开关。最简单复现不涉及新手掌素材：angry idle 的臂角是 `[-10,+12]`；同 clock `play(stand)` 后立即变成 `[0,0]`；自然结束时又立即加回 `[-10,+12]`。`angry-idle-command.png` 已实际查看。scared 走同一分支；此处 scared 只读代码确认，没有单独出图。

建议修法：把情绪姿态作为连续基础层，在动作进入／退出的包络内淡出／恢复；动作峰值由手势层主导。实现时不要简单在所有手势结果上无权重地叠加旧偏角，否则会重新破坏专用手势。

回归／验收：同 clock idle→stand/jump/hand 的首帧、自然结束前后相邻帧，armFar/armNear 不应出现固定 10/12° 跳变；活动手势峰值仍与 neutral 手势目标一致。

### R5 — P2：缺失目标视图时，自动转向与 readiness 不一致

位置：`motion.py:120–125` 的目标方向、`item.py:106–111,169–174,218–220`。

实际在 renderer 中暂时移除 optional front rig，再经公共 `play(wave)` 和每帧 `_ensure_view` 执行：动作先转向 front；`.4 s` 结束时 `_ensure_view` 把 view 回退到 front-left，但 wave 已启动，继续用旧 FL 旋转手臂。没有循环，但“手势先到 front 使用专用贴图”的新约束失效。`motions` 仍将 wave 视为 ready，因为目前仅 turn/spin 检查 `turns_ready()`。

建议修法：在 controller 中按动作目标检查能力；缺失 front、left/right 等必需 target 时，选择明确且受测的 fallback 或标为未就绪。路由不应依赖每帧 `_ensure_view` 事后纠正目标。若采用 fallback，应避免让缺失视图渲染成 source 基底却保留错误的 view 名称。

回归／验收：至少覆盖缺失 front 的五个手势、缺失 left/right 的 bow，以及缺失中间视图时的 face-return。确认 readiness、最终动作与实际使用素材一致，并保持原包基底可用。

## 4. 视觉限制与本轮没有宣称的结论

`seat-smooth.png` 显示 `.49/.50/.51` 已没有阈值硬切。但站立腿、原裙摆与坐姿整图在中段同时可见，翼／尾也淡出，因此属于贴图溶解过渡，不能描述成已有连续膝／髋关节坐下动作。本轮不把它当新的状态错误；后续视觉验收仍需实际 `.0→.8 s` 时序、脚底基线与遮挡检查。

修正 R1 的线性混合后，转身仍是不同画面的淡入淡出，不等于有实体旋转的中间形状。`blend-alpha-leak.png` 第四栏能看到前／侧面双眼、双轮廓叠影；此限制应与 alpha 算法 bug 分开记录。

本轮未重新验收 19 个表情定位、所有头颈／肩肘／腿翼尾连接、8 方向尺度一致性、专用 raised/point 资产的解剖方向和遮挡。原报告仍是这些项目的修复依据。当前状态测试通过不意味着这些视觉项目已关闭。

## 5. 主上下文建议执行顺序

1. 先修 R1，用独立预乘颜色夹具封住中点漏底，再看真实转身。
2. 修 R2，统一面向意图与 action pending 的关系，明确完成、替换、取消规则。
3. 把 R3 的 orientation 生命周期与 action 替换拆开，再复跑 232／6,728／72 项状态探针；对取消与替换分别定义验收。
4. 修 R4 的表情层权重和 R5 的缺失 target 降级行为。
5. 手势资产稳定后重建资产清单、复跑全部 model 测试，再单独做动作峰值、开始、结束与连接部位的视觉验收。

本报告的 232／6,728／72 等数字仅限上述固定采样时刻和状态空间。后续实现若改变状态机，应更新诊断假设并重新执行，不能沿用本报告作为新版本通过证明。

## 6. 第二轮修后定向复查

第二轮固定源码位于 `linux/test-results/review/motion/state-recheck/v2/`，探针为同目录 `recheck.py`，数据为 `results.json`。本轮没有重跑 232／6,728 全量状态组合；只补查实际变动点。

| 文件 | 第二轮 SHA-256 |
| --- | --- |
| `motion.py` | `d1940abff27dfd96f2ffcf732433ba8e183b5f69d957d7312034842b23e66c5f` |
| `render.py` | `a211963fa1d7df00e7214e1f56c48a53098b3e88ebd33f07a7514d463ce92a2b` |
| `item.py` | `5f573e9ba3a55ccfa46aa5703460abfaa7083a54fd657049af3c02e346d74814` |

| 原问题／修补 | 本轮实测结果 | 状态 |
| --- | --- | --- |
| R1：第二张图先预加权，再全 opacity PLUS | 8 个真实相邻方向对中点，与预乘线性期望最大字节差从 64 降到 1 | 数学错误已修；不把双轮廓视觉问题一并关闭。 |
| R2：`request_face_view` 与 `face_requested` | 原 72 个公共 API 交错全部最终有脸且 flag 清空 | 原复现通过；下面的交叉替换仍失败。 |
| face request 与 pending 同时存在 | back 起始五手势、bow、sit、sleep 的 auto-turn 在 `.03 s` 时连续请求 happy/speaking/listening | 8 项均到目标方向，pending 清空且原动作启动；没有路由循环或动作丢失。 |
| R3：`.12 s` settle | front turn `.08 s` 时替换 stand，同 clock 的 `view/blend_view/mix` 完全一致；settle `.1 s` 时新动作 elapsed=0，`.13 s` 时 elapsed≈`.01` | 朝向连续性和新动作计时通过；未验收完整身体姿态混合。 |
| settle 期间再次替换／取消 | 上例 settle `.06 s` 时再替换 bow，保存当前 mix；随后 cancel 并继续推进 | 新路由收敛，取消后无 pending 或动作复活。 |
| R4：emotion 独立权重和动作 env | angry 先保持 `.3 s`，idle→stand 同 clock 臂角均 `[-9.2095,11.2095]`；自然结束相邻帧仅正常小变化 | 原 10/12° 开关跳变已修；未证明任意动作之间的整身切换都连续。 |
| R5：`motion_ready` 目标／variants 校验 | 移除 front rig 后，五个 hand gesture 的 ready 全为 false | 缺 front 的原复现已修；bow 缺左右目标仅读码确认，未另出图。 |

### R2b — P1：face_requested 在更换成持续动作后仍可能永不消费

第二轮新增的实际复现：

```python
a.set_view("back")
a.play("spin")
advance(a, .03)
a.set_expression("happy")
a.play("carried")
advance(a, 3)
```

结果为 `view=back, action=carried, carry=1, face_requested=True, settling=None`。当前仅在 action 的完成分支消费 face_requested，而 carried 不会完成，所以面向意图永久滞留。将 carried 换成 run，3 s 后同样仍在 back，需要等 12 s 动作结束才会消费；stand 则在结束后才回脸。

建议在 settle 完成／新动作实际启动的边界消费尚存的面向意图；若处于 rear 且不在 turn/spin，先插入 face-return 并保留新动作作为 pending。注意避免用重复 `play(turn)` 把 settle／pending 再次重置。不能仅在自然动作完成时检查。

### R2c — P2：说话／聆听撤销后，旧面向意图仍执行

实测 `front→turn→setSpeaking(True)→setSpeaking(False)`，最后仍额外转向 front-left。虽然 speech 已 false，`face_requested` 这个单 bool 仍代表曾经发出的请求。若期望 False 撤销尚未执行的面向动作，需要按 expression/speech/listening 区分请求来源，并在对应状态关闭时移除来源；否则应明确约定一次 True 就提交不可撤销的面向命令。

此项是取消语义的边界，不能与 R2b 的永久滞留等同；后者是明确未兑现仍有效的面向请求。主上下文已收到两个复现。

## 7. 第三轮收尾复查：剩余交叉请求已通过

最后固定快照为 `linux/test-results/review/motion/state-recheck/v3/`：

| 文件 | 第三轮 SHA-256 |
| --- | --- |
| `motion.py` | `d0b0f3996d6e9288c54525e04cf1d82a36ffb7f88765e500498ab2d4ab4bba87` |
| `render.py` | `a211963fa1d7df00e7214e1f56c48a53098b3e88ebd33f07a7514d463ce92a2b` |
| `item.py` | `eac40649fc6dd448efe65db88fd881a129a40a1a40dc76be122e8f4416f54212` |

实现新增 `face_reasons`，`request_face_view(reason, enabled)` 按来源添加／撤销意图，`advance` 在 settle 结束后、动作计时前调用 `_consume_face_request()`。此轮继续使用第二轮的小范围探针，没有重跑 6,728 个替换对。

实际验证结果：

| 案例 | 第三轮结果 |
| --- | --- |
| R2b：back→spin `.03 s`→happy→carried | 替换后 `.13 s` 已为 `turn/pending=carried`；再 `.5 s` 到 front-left/carried，carry=1，flag/reasons 清空，不再永久滞留。 |
| 同路径替换 run／stand | 均先回可见面部方向，再进入所请求动作，不等 run 的 12 s 结束。 |
| R2c：turn 中 speech True→False | 只剩原用户 turn，最后 back；没有额外回脸。 |
| listening True→False | 同上，撤销自己的尚未兑现意图。 |
| expression 与 speech/listening 并存后关闭状态 | 关闭状态后 `face_reasons == {"expression"}`，最终仍兑现表情面向请求。 |
| speech 与 listening 并存后关闭其中一个 | 另一个来源仍保留，最终回脸；两种撤销次序均实测。 |
| 带面向意图的 settle/carried 随后 cancel | 继续推进 2 s，action/pending/face_requested/reasons/carry 全部清空，无幽灵回脸。 |
| 原 72 项交错及 8 项 pending 动作夹插 | 继续通过，没有因来源集合引入循环或丢动作。 |
| 8 方向混合中点、emotion 边界、settle 替换、缺 front readiness | 第二轮定向探针在第三轮快照继续通过。 |

完整数值分别保留于 `v3/results.json` 与 `v3/reason-checks.json`。新增的 8 个来源／撤销／持有断言全部通过。

本轮到此结束状态审查。首次“21/22”的整套测试记录仍是首次快照结果；第三轮只进行了上述定向验证，没有重跑最终资产清单或宣布全部模型测试通过。后续 UV 重标定、手势图更新以及转身／坐下的双轮廓视觉验收，应由主上下文在最终素材版本完成。
