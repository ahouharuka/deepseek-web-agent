# DeepSeek Web Agent

这是一个实验性的、需要人工监督的编码 Agent：DeepSeek 网页端负责规划，本地 Python 程序负责校验并执行受限工具。

> [!WARNING]
> 本项目是非官方研究原型，与 DeepSeek 无隶属或背书关系。它依赖可能随时变化的网页界面。处理真实代码前请阅读 [安全说明](SECURITY.md)。

## 工作原理

```text
用户任务
→ 本地程序把工具说明发送给 DeepSeek
→ DeepSeek 返回一个 JSON 工具请求
→ 本地策略校验工具、参数、路径和权限
→ 本地执行工具并返回结果
→ 循环直到 final
```

Python 程序本身就是 Agent runtime，不需要另接 Codex、Claude Code 或本地模型。

## 安装与运行

需要 Python 3.11+、Chrome 或 Edge，以及 DeepSeek 网页账号。

```powershell
git clone https://github.com/ahouharuka/deepseek-web-agent.git
cd deepseek-web-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

离线 Demo：

```powershell
python main.py --demo --workspace acceptance_project --yes
```

网页模式：

```powershell
python main.py --web --workspace C:\path\to\project --yes `
  --skill code-explainer "解释入口、模块、数据流和测试；保持只读。"
```

首次运行会打开专用浏览器配置，请自行登录 DeepSeek 并保持窗口打开。

Python 修复示例：

```powershell
python main.py --web --workspace C:\path\to\project --yes `
  --skill python-bugfix --reasoning auto --max-steps 20 `
  "修复失败测试，不得修改 tests；采用最小源码补丁并重新验证。"
```

## 权限边界

- `--workspace` 是文件访问边界，路径逃逸会被拒绝。
- `--yes` 只自动批准读取；写文件和运行测试仍需确认。
- 不提供任意 Shell、删除、移动、依赖安装或 Git 写操作。
- `.env`、私钥、浏览器配置、日志、虚拟环境等敏感路径默认隐藏并拒绝读取。
- 读取成功的源码会通过网页发送给 DeepSeek；审计日志会在本地明文保存工具结果。

请始终选择范围狭窄、不含隐私与密钥的工作区。详细威胁模型见 [SECURITY.md](SECURITY.md)。

## Skill 与推理模式

```powershell
python main.py --workspace C:\path\to\project --list-skills
```

Skill 必须通过 `--skill` 显式加载，只规定工作方法，不能增加工具或权限。

`--reasoning` 支持 `off`、`on`、`auto`。自动模式会为 `python-bugfix` 和修复/调试任务开启“深度思考”，普通读取与 `code-explainer` 默认关闭。

## 当前限制

- 仅支持 Python `unittest` 和 UTF-8 文本。
- DeepSeek 页面更新可能导致选择器失效。
- 任务暂不支持进程重启后的断点恢复。
- 不适合无人值守或敏感生产仓库。

完整参数：

```powershell
python main.py --help
```

## 许可证

[MIT](LICENSE)
