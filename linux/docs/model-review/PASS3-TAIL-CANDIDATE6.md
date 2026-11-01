# 候选6尾巴／后向定向审查：确认失败

候选6不能通过。公共网格绘制把中间画布贴回了源贴图小格的位置，导致尾巴漂到头侧、动作腿片悬空、裙片错位，并使有pitch的头壳被裁离正常位置。这个问题在不带任何诊断hook的独立新进程中直接调用 `DragonRenderer.render` 也能复现。

主上下文收到定位后提供了候选7，后续审查单独进行；本报告保留候选6真实失败状态，不用候选7结果覆盖它。

## 范围与固定版本

- 冻结：`/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/candidate-6/linux`。
- 文件数：227；集合hash：`53bfce6226ba288ce357406d1f22c808191ccc7afe98734c166d543d6ef87a50`。
- 38个case、353帧正式定向采样已完成：尾巴回归8帧、连续转向177帧、取消／替换120帧、蹲起48帧。
- Qt offscreen、768×768、RGB32不透明灰底；完整角色、裸尾、body/hair调色板及投影头部隔离均有证据。
- 冻结执行前后hash一致，viewErrors为空。没有修改冻结或live运行文件、模型素材。
- 诊断目录：`/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/rear-candidate-6`。`records.json`保留每帧实际动作、方向、尾材质、骨链、三探针、轮廓和像素差分。脚本为ignored目录中的 `tail-c6-check.py`。

## P1：源小格裁切变量覆盖世界画布原点

具体位置：冻结 `gpt_niang_linux/model/raster_mesh.py`。

1. `draw_mesh`先用映射后的世界顶点计算`left/top/right/bottom`，建立中间画布，并以`(-left,-top)`平移绘制（约36–43行）。
2. 新增的源贴图局部裁切，在三角循环内再次赋值同名`left/top/right/bottom`，这些值现在是源纹理小格边界（约66–68行）。
3. 结尾 `original.drawImage(QRectF(left,top,output.width(),output.height()),output)` 使用了最后一格的源坐标，丢失原来的世界画布原点（约70行）。

因此几何和蒙皮函数完全正确时，整个已绘制部件仍会被平移到错误位置。静态B的数学尾根为 `(425,683)`，最终mapping也返回同一点；正确渲染屏幕位置应约为 `(345,541.8)`，实际粗尾根却出现在头左侧、约 `(190,290)`，不能用root误差为0判为通过。

![候选6独立直接渲染：背面静态尾巴漂到头侧](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/rear-candidate-6/direct-c6-back-idle-0.png)

B land .325时，普通腿／裙／尾网格也受到同样错误影响。头部在有pitch/yaw时会进入 `head.py` 的 `draw_mesh` 投影分支，因此头壳消失、角耳仍留在原处，亦由同一回贴原点错误解释；无需先假定角耳原画或头壳素材缺失。

![候选6独立直接渲染：落地时网格部件错位](/home/alazif/projects/Project2/MyProjects/DesktopPet/GPT-Niang/linux/test-results/review-pass-3/rear-candidate-6/direct-c6-back-land-0.325.png)

**可实施修法：** 使用互不复用的 `canvas_left/canvas_top` 与 `source_left/source_top`，最终回贴始终使用画布的世界原点。保持有限源矩形裁切本身，避免因为修原点而撤回有效的三角裁切。增加实际像素bbox验证，覆盖identity映射、非零世界box、有root／head pitch的网格以及透明末行；只比较map函数或顶点值不足以检出此错。

## 尾巴旧问题的数值状态与视觉限制

候选6中，B256场已将前轮内弯探针恢复为正常 `.21`。粗干 `(168,636)→(168,637)` 探针也是 `.21`；旧圆边界仍为 `.00279598`；静态root和骨段长度正常。它们说明权重部分的改动仍在，但不能抵消上面的最终绘制失败。

353帧中的尾收放、取消、深坐整段同样被公共错位污染。没有将头旁漂浮的尾图作为正常收尾来验收，也没有用错误位置上的轮廓面积宣称后向遮挡通过。body/hair调色板本身使用另一条strip路径，其材质切换仍可在隔离图里查看，但完整角色的综合结论必须待原点错误修正后的独立冻结版本复核。

## 后续验收要求

- 直接渲染B静态和land .325，整尾、腿、裙、头壳回到正确世界位置；其余普通动作不再出现悬空碎片。
- 重看三个后向spin的收尾、完全隐藏、展开，确认尾与后发的真实遮挡关系。
- 相邻方向切换时同时比较body/hair隔离和整身，区分轮廓连续与纹理跳变。
- 坐起、取消前后连续帧应保住尾骨连接，不在settling结束时跳回旧方向。

候选7正在使用同样计划另行采样，结果将写入单独报告。
