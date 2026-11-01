# Candidate 6 动作审查：公共网格回贴失败，转交 C7 复核

2026-11-01。**C6 不通过视觉验收。** 实际渲染中，使用网格的腿、裙、尾与俯仰头面被回贴到错误位置；转圈还保留身体材质半程硬切和头部横条。数值状态连续不能证明这些像素正确。主上下文在本轮中确认并修复公共回贴故障，提供 C7 冻结，因此后续完整逐项判断移至 `PASS3-MOTION-CANDIDATE7.md`；本文件保留 C6 失败，不能被新结果覆盖。

## 边界与覆盖

只读冻结 `linux/test-results/review-pass-3/candidate-6/linux`，使用父级 `snapshot.json` 和真实本机 Coopanion 导入模型；诊断为 Qt offscreen，灰底 RGB32 合成。未改 production、tests 或模型素材。诊断分别位于 `motion-c6-check/`、`motion-c6-visual/`、`run-settle-6/`，均为 ignored。

- 数值/API：30 动作多时点、三种取消/替换、8×30 入口；15,972 个 Pose 检查；30,140 次原纹理手臂缺少作者肘链，不能视作关节通过。250 个处于视角混合的 Pose 没有冒充可重建的静态几何。run 初入、稳定、退出包络共 36 条取消/重复取消/替换轨迹，1 ms 邻帧和接地 ±10 μs。
- 已渲染：`motion-c6-visual` 共 54 张表、781 格，覆盖 30 动作本体及峰值取消、补充物理与头部返回；另有诊断计划边界图和 run 定向图。
- **在 C7 到来前实际逐图查看**：`spin-camera-thresholds-full/head-1/2` 共 48 格，`action-stand/sit/sleep/jump` 共 68 格，以及 6 格 `isolation.png`。没有把其余仅渲染的格数写成已看图。公共回贴失败已足以否决这些视觉结果，其他动作不据此逐项批准。
- `isolation.png` 只在 ignored 诊断进程中临时屏蔽绘制层以定位；正式动作图没有强制 Pose、没有更改生产实现或素材。

## 确定失败

| 优先级 | 失败与复现 | 根因/修法 | C6 证据 |
|---|---|---|---|
| P1，阻断视觉验收 | `spin` 从 front，t=.4105562，左上悬空整条靴腿；stand/sit 时裙漂到头顶左侧；jump/sleep 进入非零俯仰时脸消失，只剩后发底色 | `raster_mesh.py` 的 `draw_mesh()` 原本用 `left/top/right/bottom` 保存目标画布边界；新源片 region 裁切循环再次赋值这些变量，末尾 `original.drawImage(QRectF(left,top,...))` 使用了最后源网格坐标。应独立保存目标画布原点与源 region 坐标，并对真实图像包围盒回归。主上下文已在 C7 修复，C6 仍记失败。 | [action-jump](../../test-results/review-pass-3/motion-c6-visual/action-jump.png)、[action-stand](../../test-results/review-pass-3/motion-c6-visual/action-stand.png)、[隔离图](../../test-results/review-pass-3/motion-c6-visual/isolation.png) |
| P1 | `spin` t=.4105462±.00001（front→front-left mix≈.5），衣领、肩、衣纹与下身绘制显著切换；不是同一轮廓上的连续纹理运动 | `render.py:render()` 仍按 `view_mix<.5` 选整套 native view；`_render_body_palette()` 只使外轮廓趋同，source palette 随 view 换，内部结构未注册。C7 需独立看正常位置图裁定，不用公共漂移故障替代这一判断。 | [full-1](../../test-results/review-pass-3/motion-c6-check/spin-camera-thresholds-full-1.png) |
| P1/P2，交头部代理进一步定位 | 多个头部角度刘海出现水平断层，颈部/发侧有横向带状变形；在角耳独立后仍存在 | `head.py` 的按行皮肤/头发窗口与材质选择须检查；不能以角耳路径连续或没有双影作为脸部通过证据。 | [head-1](../../test-results/review-pass-3/motion-c6-check/spin-camera-thresholds-head-1.png)、[head-2](../../test-results/review-pass-3/motion-c6-check/spin-camera-thresholds-head-2.png) |

## 数值结果与未验收事项

run 的根轨迹误差至多约 3.36e-13，重复取消保持 fall owner/elapsed；单足接触段最大局部 sole 漂移约 1.013 模型单位，没有重新生成长飞行弧。**因为像素位置受公共回贴故障影响，本轮不能把这些状态结果升级为 run 的 C6 视觉通过。**

真实 UV 骨链还触发 18 次 reach clamp 与鞋骨长度比异常：sit t=.50 / stand t=.45 时两腿踝目标被 IK 改写约 14.62/15.79，鞋骨长度比 .876/.871；stand 在 p=.18 取消后 .35s，近腿踝目标被改写 27.78，鞋骨比 .678。后续 C7 定量确认是目标进入两段不等长所形成的内不可达圈，不能将这些距离误称为向外超过总骨长；详见 C7 报告。86 次 contact-off-rest-ground 提示多数属于转身踏步：contacts 没有随抬脚更新，不能将其直接写成“脚穿地”。这是数据语义待核对，而非肉眼确认穿地。

第一次诊断的六个 `leg-length` error 是诊断器未完整镜像 raw-art bypass 的不足：当全部状态 <.001 时，实际 renderer 直接绘原图；诊断仍把微小 pelvis 偏移加到 hip，造成 <.00076 的误报。已仅修诊断脚本并重跑；初次 JSON 保留为 `diagnostics-first-adapter.json`。最终只有 review 级提示，状态为 `NUMERIC_COMPLETE_VISUAL_UNASSESSED`，没有把移除误报当生产修复。

384 尺寸实际记录的 warm 中位渲染耗时约 nod 21.4 ms、jump 29.6 ms、run 28.2 ms、turn 90.9 ms、spin 93.4 ms。此时其他诊断进程可能并行，数字仅为观测；转身每帧约 0.1 秒仍显著限制实时流畅度，不能宣传稳定 30/60 fps。原文件与 rig JSON 在采样前后散列一致；正式转向与动作结论继续看 C7。
