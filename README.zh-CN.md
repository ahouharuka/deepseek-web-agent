# DeepSeek Web Agent

把你在终端中输入的一句话交给 DeepSeek 网页端规划，再由本地程序读取、修改指定项目中的文件并运行受限测试。

> [!WARNING]
> 这是非官方研究原型，与 DeepSeek 无隶属或背书关系。不要用于含有隐私、密钥或敏感生产代码的目录。

## 最重要的：在哪里输入指令？

指令直接写在启动命令的最后，并用英文双引号包起来：

```powershell
python main.py --web --workspace "你的项目目录" --yes "你要它完成的任务"
```

例如，要让它解释 `D:\Projects\my-app`：

```powershell
python main.py --web --workspace "D:\Projects\my-app" --yes "阅读这个项目，告诉我它的用途、入口文件和主要模块。不要修改文件。"
```

例如，要让它修复测试：

```powershell
python main.py --web --workspace "D:\Projects\my-app" --yes --skill python-bugfix --reasoning auto --max-steps 20 "运行测试，找出失败原因并修复。不要修改 tests 目录。修改后重新运行测试。"
```

上面命令中：

- `--web`：使用 DeepSeek 网页端。
- `--workspace "..."`：它能访问的项目目录，也是文件访问边界。
- `--yes`：自动允许只读操作；没有它，每次读取也会询问你。
- 最后的双引号内容：你的自然语言指令。它不是在 DeepSeek 输入框里手动填写的。
- `--skill python-bugfix`：可选，加载 Python 修复工作流程。
- `--reasoning auto`：让程序根据任务决定是否开启“深度思考”。

## 从零开始

需要 Python 3.11+、Chrome 或 Edge，以及 DeepSeek 网页账号。

```powershell
git clone https://github.com/ahouharuka/deepseek-web-agent.git
cd deepseek-web-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

先运行离线演示，确认程序安装正常：

```powershell
python main.py --demo --workspace acceptance_project --yes "列出文件并说明这个示例项目。"
```

然后运行真实网页模式：

```powershell
python main.py --web --workspace "D:\Projects\my-app" --yes "先列出文件，再简要说明项目结构。不要修改文件。"
```

第一次运行时会弹出一个专用 Chrome/Edge 窗口：

1. 在该窗口登录 DeepSeek。
2. 保持窗口打开，不需要自己把指令粘贴进聊天框。
3. 程序会自动发送指令、读取 DeepSeek 的 JSON 请求并执行本地工具。
4. 遇到写文件或运行测试时，终端会显示预览并询问 `[y/N]`。
5. 确认无误后输入 `y` 再按 Enter；输入其他内容或直接按 Enter 会拒绝操作。
6. 任务完成后，最终回答会显示在终端里。

## 常用指令示例

只读解释项目：

```powershell
python main.py --web --workspace "D:\Projects\my-app" --yes --skill code-explainer "解释项目入口、模块关系、数据流和测试结构。保持只读。"
```

寻找某项功能的位置：

```powershell
python main.py --web --workspace "D:\Projects\my-app" --yes "找出用户登录功能由哪些文件实现，并说明调用流程。不要修改文件。"
```

修改一个小功能：

```powershell
python main.py --web --workspace "D:\Projects\my-app" --yes "给 calculator.py 的 divide 函数补充除数为零的错误处理，并运行现有测试。不要修改测试。"
```

查看可用 Skill：

```powershell
python main.py --workspace "D:\Projects\my-app" --list-skills
```

查看所有参数：

```powershell
python main.py --help
```

## 它能做什么？

- 列出目录、读取 UTF-8 文本、搜索文本、查看文件信息。
- 精确替换一行或一个唯一匹配的文本块。
- 新建受支持的文本文件，但不会覆盖已有文件。
- 运行固定的 Python `unittest` 测试命令。

它不能执行任意 Shell，不能删除、移动文件，不能安装依赖，也不能执行 Git 写操作。

## 权限和安全提示

- `--workspace` 决定它能看到哪些文件；不要把个人主目录或包含多个项目的大目录作为工作区。
- 成功读取的源码会通过网页发送给 DeepSeek。
- `--yes` 只自动批准读取。写入和运行测试仍需你在终端输入 `y`。
- `.env`、私钥、浏览器配置、日志、虚拟环境和常见凭据目录会被隐藏并拒绝读取。
- Python 测试本质上是本机代码，只对你信任的项目批准运行测试。

完整威胁模型见 [SECURITY.md](SECURITY.md)。

## 常见问题

**我应该在 DeepSeek 网页里输入指令吗？**

不用。把指令放在 `python main.py ... "指令"` 的最后。程序会自动发送。

**为什么终端在等我？**

如果画面显示 `[y/N]`，程序正在等待你批准写文件或运行测试。查看上方预览后输入 `y` 或拒绝。

**为什么浏览器打开后没有继续？**

确认你已经在程序弹出的专用浏览器窗口里登录 DeepSeek，并且聊天输入框已经出现。不要关闭该窗口。

**任务结束后想暂时保留浏览器怎么办？**

在命令中加入 `--keep-browser-open`。

## 工作原理

```text
终端里的自然语言指令
→ 本地程序自动发送到 DeepSeek 网页
→ DeepSeek 返回 JSON 工具请求
→ 本地策略检查工具、参数、路径和用户批准
→ 本地执行受限工具并把结果发回 DeepSeek
→ 循环直到 DeepSeek 给出最终回答
```

Python 程序本身就是 Agent runtime，不需要另接 Codex、Claude Code 或本地模型。

## 当前限制

- 仅支持 Python `unittest` 和 UTF-8 文本。
- DeepSeek 页面更新可能导致网页自动化暂时失效。
- 任务暂不支持进程重启后的断点恢复。
- 不适合无人值守或敏感生产仓库。

## 许可证

[MIT](LICENSE)
