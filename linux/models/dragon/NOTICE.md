# 角色素材来源与适用限制

本目录 PNG、制作图及角色造型衍生素材 **不包含在仓库代码的 MIT 授权中**。不声称模型的原角色形象为本项目原创。

角色基于 [zhengjihuaren/coopanion-gpt-dragon v1.1.0](https://github.com/zhengjihuaren/coopanion-gpt-dragon/releases/tag/v1.1.0)，发布包 SHA-256：`ec84d07a2144fb1850d5c85dddc558b5bd12cbf35560d0d8ee25ca1832ac7836`。原包作者明确说明形象来自网络、未取得原角色授权，仅作个人使用和非商业分享；禁止商用，分享需保留来源，不得改后声称原创。原作者提供的说明不代表其拥有或能授予全部原角色权利。

本项目沿用上述自用、非商业分享与署名边界；新增侧面/背面与补件是使用内置 OpenAI ImageGen 参考该形象生成，再进行文件切割、层级整理与 Qt 绑定。生成工具的使用不改变底层角色权利。不授予对角色造型额外的商业使用许可。

原始 30 个 PNG、`model.json`、`figure.json` 和 README 通过固定发布包在用户本机导入，不随本目录复制；原包 README 随导入保留。`source/` 和派生 cutout PNG 是本次制作文件，保留本说明和源链接。两个其他参考项目本轮未复制资源。

Qt 动画控制与渲染代码为本项目独立实现，没有导入或执行 `figure.js`，也没有复制 Coopanion 的 AGPL 宿主、kit 或渲染器。原宿主及其许可信息仍见[上游固定提交](https://github.com/Pal-AI-Lab/Coopanion/tree/91293b3e31b94397a8f2eb79dffec40f4c6d8817)。若后续实际复用宿主代码，需要另行履行其许可条件。
