# 第三轮动作定向复核：候选 11

2026-11-01。冻结树 `linux/test-results/review-pass-3/candidate-11/linux`；snapshot 实际列出 225 文件，逐项哈希一致。代码、测试和素材只读；仅写本报告与 ignored 诊断。使用真实本机 Coopanion 素材、Qt 实际 Renderer，非几何占位图。

**本轮结论：C10 已明确的旧 Pose ±12° free 足穿地修复通过定向验收，boot 刚性保持；坐站/取消、抓抛释放、run 临接地路径未见回归。不扩大为全 30 动作重新验收，也不判全 V1 或连续 3D 转向通过。** [C10 完整 30 项报告](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/docs/model-review/PASS3-MOTION-CANDIDATE10.md)保留原失败记录，本报告只追加 C11 证据。

## 实际覆盖

已逐张查看 10 张灰底接触表、102 单元：旧 C7 记录 6 Pose × root_angle 0/+12/−12 共 18；正常路径 7 组×12 共 84（sit、stand、stand .216 取消、sit .72 取消、carried→toss、run .49/.499→hop）。只有 18 个历史/人为旋转单元绕过 Animator，均标 `HISTORICAL/FORCED / NOT C11 API`。

84 个正常图使用 C10 已记录的实际 API Pose 在 C11 真实 Renderer 重渲染，确保与旧图同一时点、避免 dt 差异。已独立确认 C10/C11 `motion.py` 与 `dynamics.py` 相同；另用 C11 Animator 重跑 48 空中重播/互换、10 run 边界操作、5 持有时长释放与 8×1501 坐站连续帧。其 air/run/release/seat 数组与 C10 逐项完全相等。因此“同姿态渲染对比”和“新候选实际 API 回归”分别有证据；没有把保存 Pose 冒充重新驱动完整 API 的图。

诊断不仅重写计算公式：在内存包装 `_render_leg` 与 `skin_point`，捕获 production 实际传入 skinning 的 rest/posed 髋—膝—踝—sole 链；回调返回原函数结果，不改渲染。102 Pose 中捕获到 184 条活动腿链，剩余 20 条走原生静态纹理 bypass，不伪称也经过了 skinning。诊断公式与真实捕获的 boot 比例/地面残差最大差 1.14×10⁻¹³。

脚本与完整数值：[targeted.py](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c11/targeted.py)、[targeted.json](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c11/targeted.json)、[numeric.py](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c11/numeric.py)、[numeric.json](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c11/numeric.json)。

## 旧失败的前后值

所有坐标均为设计像素；渲染整体画布平移是共同常数，地面残差已消去该常数。`sole_ground_delta > 0` 表示低于脚本对应的 world floor；boot ratio 是实际 ankle→sole 长度 / authored ankle→sole 长度。

| 历史 stand .216 取消后 .35 秒的强制角度 | C10 故障腿/穿地 | C11 同腿穿地 | C11 boot |
|---|---:|---:|---:|
| 0° | near 在 C10 已从 C8 +18.72455 修到 0 | 0 | 1 ± 浮点误差 |
| +12° | near +9.56060 px | +1.14×10⁻¹³ px | 1 ± 浮点误差 |
| −12° | far +12.50542 px | 0 | 1 ± 浮点误差 |

六个历史 Pose 全部 0/±12° 的实测加上 84 个正常图，最大正向地面残差 1.13687×10⁻¹³ px，最大 boot 比例误差 1.99840×10⁻¹⁵，没有异常记录。图上近/远靴长度与踝接缝保持，不再依靠压靴使足底留地。旧旋转姿态本来是人为压力输入，整身/衣裙仍按强制 root_angle 倾斜；这里只验 foot floor，不将任意旋转下的裙摆外观判为合法 API 动作。

实图：[0° 六帧](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c11/historical-angle-0.png)、[+12° 六帧](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c11/historical-angle-12.png)、[−12° 六帧](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c11/historical-angle--12.png)。

冻结 `render.py:608–620` 的修法对应实际变换：`normal=(sin(angle), cos(angle))`、局部 floor 常量含 root_y/root_anchor；在同一 reach circle 与该直线求交，重新解膝踝，sole = actualAnkle + 原刚性 foot vector。contact 足不走 free 足修正。此实现修中了 C10 漏掉 root rotation 的根因。

## 原路径回归

| 路径 | 实测值/图上结论 | 本轮状态 |
|---|---|---|
| 48 空中重播/互换 | root 最大误差 1.2753×10⁻¹² px，vy 最大误差 3.4106×10⁻¹²；owner/elapsed、after_land 保持，无错误项 | 数值通过；未逐对新画完整序列 |
| run .49/.499，5 类重复/取消/替换操作 | 旧弧分别剩 4.761905/.476190 ms；owner/elapsed 保持，root 误差 0；接地 ±10 μs 的全腿关键点位移仍 ≤.0189331 px | 数值与代表图通过 |
| carried 持有 .001/.05/.12/.5/3 → toss | 即刻 −430 px/s，自当前高度释放；持有 .5 时 y=−35，落地 +.790463 秒 | 数值与 12 帧通过 |
| sit/stand 本体及各 .216/.5/.72 取消 | 12008 Pose/24016 腿；boot 最大比例误差 9.9920×10⁻¹⁶，ankle clamp=0，contact sole 漂移=0，free sole 最大地面残差 −1.14×10⁻¹³ px | 数值与 4 组代表图通过 |

图中 sit 仍先下降、再伸足至低座；stand/取消先收足再起。旧近靴缩短窗口没有复发；手臂与骨盆接着地准备、鞋落地后有支撑地回收。run 极短剩余弧没有延长成悬停、再次腾空或接地后脚还停半空。native 衣裙/长发与 C10 同时点保持，未见新的条带拉伸或公共网格漂移。

实图：[sit](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c11/seat-sit-None.png)、[stand](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c11/seat-stand-None.png)、[stand .216 取消](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c11/seat-stand-0.216.png)、[sit .72 取消](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c11/seat-sit-0.72.png)、[抓抛](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c11/release.png)、[run .49](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c11/run-hop-0.49.png)、[run .499](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/motion-c11/run-hop-0.499.png)。

## 结论边界

本轮只关闭 C10 所列可达旧 Pose 旋转地面约束问题。固定 hip/有限骨长、floor 与可达圆无交点的任意非法 Pose 不在通过范围；contact 不可达时的任意人工输入也没有扩大承诺。正常 API 轨迹在本轮坐站扫描不需要 clamp。

没有重新评判 C11 后颈/后发 mask 的全方向视觉，其专项由正面/方向审查负责；C10 的回眸失败不能仅因代码宣称修复自动改成通过。转身仍按有限方向原画帧理解，连续转面未验收；C10 的性能尖峰也未在本轮重新基准测试。已确认的新 floor 修复无须重启已完成的 30×全组合采样，后续若修改腿链/足底/根旋转来源，应保留本套旧姿态和临接地回归。
