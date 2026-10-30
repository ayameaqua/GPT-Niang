# GPT-Niang Linux（0.1.0-dev1）

面向 KDE Plasma / Wayland 的源码预览版。使用 **PySide6 / Qt Quick 普通 Wayland 窗口 + KWin 专用 Remember 规则**，位置由 KWin 管理，尺寸由应用保存。没有安装常驻 KWin 脚本、Layer Shell、XWayland follower 或额外 worker 服务。

本 Fork：[ayameaqua/GPT-Niang](https://github.com/ayameaqua/GPT-Niang)。上游版本为 1.3.6，基线固定在 [`0f43bb54ee413d4fc8e95f03b4248834b468d6b5`](https://github.com/T7moris/GPT-Niang/commit/0f43bb54ee413d4fc8e95f03b4248834b468d6b5)。开始实施时与上游 `main` 相同。Windows/macOS 代码与共享额度核心保持原样。

后续角色扩展见 [Qt 龙娘分层动画与对话气泡实施计划](docs/COOPANION-DRAGON-PLAN.md)：以 Coopanion 龙娘形象包为基底，V1 补全多视角与交互，V2 增加骑自行车。当前已开始实施，可动原型与侧面/背面试验绑定见文末；完整 V1 和自行车尚未完成。

## 安装和启动

需要 Python 3.10–3.15（含 venv）、Node.js 20+、Codex CLI、KDE Plasma 6 / Wayland，以及可用的 Codex ChatGPT 登录。首次安装需要联网下载 Qt wheel。Ubuntu 缺少 venv 时先安装 `python3-venv`。

```bash
git clone https://github.com/ayameaqua/GPT-Niang.git
cd GPT-Niang
git switch linux/qt-wayland
./linux/setup.sh
./linux/packaging/install.sh --with-kwin-rules
./linux/run.sh
```

`setup.sh` 只写项目自己的 `.venv/`；锁定 `PySide6-Essentials==6.12.0` 与 `shiboken6==6.12.0`。Essentials 已包含本项目需要的 Qt Quick、Controls、DBus、Test；不需要 WebEngine。`run.sh` 清除外来的 Qt 插件/库路径，避免系统 Qt 和 wheel 混用。路径包含空格时正常工作。

安装器创建用户级 `org.gptniang.Linux.desktop`，应用菜单搜索 **GPT-Niang Linux** 即可启动。入口引用当前源码目录，之后不要移动或删除此目录；移动后重新安装入口。只安装桌面入口可省略 `--with-kwin-rules`，再按下文手动导入规则。没有配置登录自动启动。

首次终端运行会保存检测到的 Node/Codex 绝对路径；图形启动器即使 PATH 不含 nvm 也可启动。路径失效时重新检查 PATH、用户 bin 及 nvm 版本目录，不读取 shell 启动文件。也可在设置中填写绝对路径。Codex 的登录继续由 Codex CLI 维护。

## 操作

- 单击角色：打开/收起额度气泡；重复点击保持普通交互。
- 按住角色超过系统拖动阈值：请求合成器原生移动。拖动结束不触发单击。
- 右键角色：查看额度、刷新、语录、尺寸预设、设置、退出。
- 设置：尺寸 60%–250%，80%/100%/140% 预设；语录开关、可执行文件路径、KDE 规则入口。
- `./linux/run.sh --settings`：打开设置；已运行时通过会话 D-Bus 打开已有实例的设置。

输入区域按角色 PNG 的 alpha 轮廓生成，保留内部空洞；气泡打开后才加入其圆角区域。固定画布避免气泡开合改变角色原点。Qt 和输入区域统一使用逻辑像素，设备缩放仅影响图片渲染。

## KDE 位置规则

默认位置和置顶由 KDE 管理；应用没有不生效的绝对坐标、重置位置或置顶开关。实际窗口匹配条件：

| 字段 | 精确值 |
| --- | --- |
| app ID / 窗口类 | `org.gptniang.Linux` |
| 角色标题 | `GPT-Niang Pet` |
| 设置标题（排除） | `GPT-Niang Settings` |
| 位置策略 | Remember，配置值 `positionrule=4` |
| 尺寸策略 | 不设置，应用负责 |
| 置顶 | 默认不设置 / 关闭 |

自动管理工具只增删自己的 `gpt-niang-linux-position-v1` 分组与规则列表，保留其他分组原文；写入前备份既有文件，重复安装保留 KWin 已记住的位置。**先退出桌宠、关闭 KDE 规则编辑器，再执行：**

```bash
python3 linux/integrations/kde/rules.py install
python3 linux/integrations/kde/rules.py status
python3 linux/integrations/kde/rules.py remove
```

`status` 只报告配置是否存在，不能证明命中或实际恢复。复杂/重复 KConfig 分组会要求使用 KDE 编辑器，避免猜测改写。

手动方式：系统设置 → 窗口管理 → 窗口规则 → 导入 `linux/integrations/kde/gpt-niang.kwinrule` → 应用。用“检测窗口属性”核对上述 app ID 和精确标题，检查是否有更早的冲突规则。自动安装与手动导入选一种即可。需要置顶时，在该角色专用规则中设置；不要对整个 app ID 强制位置/尺寸。

若显示布局变化后角色不可操作：先通过 `--settings` 打开已有实例，再退出桌宠；删除本项目的位置规则后重新安装（初始位置 `40,40`），重新启动。手动导入的规则在 KDE 编辑器中删除。普通 Wayland 客户端不能独自可靠地找回离屏窗口，所以没有伪造的“重置位置”按钮。

## 额度、错误与进程

Python 用 QProcess 启动一个 Node JSONL 适配器，直接导入共享 `usage.mjs`、`plan.mjs` 和刷新/快照合并函数。只调用初始化及只读账户/额度 RPC，不创建聊天或模型任务；官方接口语义见 [Codex App Server](https://learn.chatgpt.com/docs/app-server)。不收集 API Key，不复制凭据，不把账户身份、原始 stderr 或额度写进日志/设置。

启动查询一次，正常每 60 秒刷新；点击时检查数据时效；失败按 60 / 120 / 300 秒退避，仍可手动重试。手动刷新有 2 秒节流。适配器同一时刻只运行一项查询，重复请求合并为至多一次后续查询。

窗口数量、标签、套餐与重置时间取自实际标准化结果。支持个人额度和任意数量的展示窗口，不按套餐猜额度。旧数据保留最近成功时间，失败尝试时间单独显示；过期不会补满。同账户失败可保留快照；身份未知/变更立即清除。快照仅在内存中，重启后重新确认账户。

上游查询预算为 18 秒，特定路由失败另有 10 秒回退；UI 外层 35 秒超时。Node 与其 Codex 子进程在独立进程组中，正常退出先请求 shutdown，超过 1.5 秒强制清理；Node 崩溃也清理该组。GUI 被 SIGKILL 时 stdin EOF / 父进程检测使 Node 清理子进程。单实例使用内核 flock，遗留锁文件不影响重启，没有自建后台 socket。

## 诊断与测试

```bash
./linux/run.sh --diagnose
./linux/run.sh --settings
./linux/run.sh --quit-after 15
cd linux
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -v
node --test tests/adapter.test.mjs
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software ./run.sh --smoke-test
```

`--diagnose` 不创建窗口/查询；`--quit-after` 是有界的真实交互运行，会正常读取额度。`--smoke-test` 加载角色、气泡和设置，不连接账户；可附加 `--capture /absolute/path.png` 保存本应用画面。offscreen 不代表 Wayland 穿透或拖动通过。真实启动输出应包含 **`QPA=wayland`**，仅有会话环境变量不足以确认后端。

自动化测试覆盖 JSONL 分包/大小限制、请求合并、跨账户清理、失败快照、EOF 清理、设置损坏恢复、最小 PATH / nvm / 空格路径、alpha 空洞、拖动取消、过期不补满和规则安全增删。独立 Linux CI 保留现有 Windows/macOS 工作流。

开发用的一次性 KWin 验收探针：

```bash
linux/.venv/bin/python linux/tests/kwin_probe.py --pid PET_PID
linux/.venv/bin/python linux/tests/kwin_probe.py --pid PET_PID --move 300 120
```

它只读指定 PID + app ID 的窗口，移动时只操作精确角色标题；退出必定卸载，不写 KWin 启用项、不供应用使用。用于测试合成器位置和规则重启恢复，不能替代真实鼠标拖动。实测记录与仍待人工验收项目见 [VALIDATION.md](VALIDATION.md)。

配置位置：`$XDG_CONFIG_HOME/gpt-niang/settings.json`（默认 `~/.config/`）；最多约 768 KiB 的轮转日志：`$XDG_STATE_HOME/gpt-niang/linux.log`（默认 `~/.local/state/`）；会话锁：`$XDG_RUNTIME_DIR/gpt-niang-linux.lock`。坏配置保留为 `settings.corrupt-*.json` 并回到默认设置。

## 卸载与许可

退出桌宠、关闭 KDE 规则编辑器后运行：

```bash
./linux/packaging/uninstall.sh
```

移除用户级桌面入口和自动安装的项目规则，保留源码、venv、用户设置及 KWin 配置备份。手动导入的规则须在 KDE 编辑器里移除。之后可自行删除源码目录；不触碰 Codex 登录。

代码遵循仓库 MIT 许可；角色图片及衍生图标不适用代码 MIT。保留共享素材中的 [角色使用声明](../gpt-niang-usage/assets/CHARACTER-NOTICE.txt)、[生成来源](../gpt-niang-usage/assets/生成说明.md) 和 [语录许可](../gpt-niang-usage/assets/quotes-LICENSE.txt)，按上游允许范围随非商业项目副本分发。

## 分层龙娘模型原型（2026-10-31）

已接入原包左前侧的 19 种表情、16/18 个基线动作与歪头/抬手；新增左侧面、背面试验绑定。八视角、转身/转圈和完整 V1 尚未完成。模型通过固定发布包本地导入，第三方 JavaScript 不执行；缺失资源时回到静态角色。使用与验收范围见 [模型工作区](models/dragon/README.md)，角色素材适用限制见 [来源说明](models/dragon/NOTICE.md)。
