# DeepSeek Web Agent

把你在终端中输入的一句话交给 DeepSeek 网页端规划，再由本地程序读取、修改指定项目中的文件并运行受限测试。

> [!WARNING]
> 这是非官方研究原型，与 DeepSeek 无隶属或背书关系。不要用于含有隐私、密钥或敏感生产代码的目录。

## 推荐：直接使用图形客户端

不会敲命令也可以使用。图形客户端提供项目目录选择、自然语言任务输入、操作确认弹窗、运行过程显示和多轮会话。

1. 打开仓库的 **Actions → desktop builds**，进入最新一次成功的构建。
2. Windows 下载 `DeepSeekWebAgent-windows`，完整解压后双击 `DeepSeekWebAgent.exe`。
3. Mac 根据处理器下载 Apple Silicon 或 Intel 版本的 DMG，把应用拖入“应用程序”。
4. 在客户端中选择 Agent 可以访问的项目目录。
5. 在“给 Agent 的指令”中直接输入自然语言任务，然后点击“开始会话并发送”。
6. 第一次使用时，在客户端打开的专用浏览器窗口中登录 DeepSeek。
7. Agent 写文件或运行代码前会显示确认窗口；看清预览后再批准。只读查看可以自动批准。

例如直接输入：

```text
先查看项目目录和必要文件，然后新建 hello.py，实现打印 Hello World；完成后运行并验证结果。
```

第一项任务结束后，继续输入补充要求并点击“发送下一项任务”，即可使用同一段 DeepSeek 对话。当前安装包尚未购买代码签名，Windows SmartScreen 或 macOS Gatekeeper 可能显示提示；请只运行从本仓库下载的版本。平台说明见 `README-Windows.txt` 和 `README-macOS.txt`。

下面的命令行方式主要供开发者、自动化脚本或需要更多启动参数的用户使用。

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

## 多轮会话

加入 `--interactive`，任务完成后可以继续在终端输入下一项任务，浏览器和 DeepSeek 对话不会关闭：

```powershell
python main.py --web --interactive --workspace "D:\Projects\my-app" --yes "先查看目录和关键文件，解释项目结构。"
```

第一项任务完成后，终端会显示：

```text
继续输入下一项任务（输入 /exit 结束）：
```

此时可以继续输入，例如：

```text
根据刚才看到的结构，为 calculator.py 增加除零处理并运行测试。
```

输入 `/exit` 即可结束会话。

任务执行过程中，如果 Agent 缺少必须由你决定的信息，它也会显示：

```text
Agent 需要你的补充信息：
...
你的回复：
```

直接输入回答即可。它会把回答交回同一个 DeepSeek 会话，然后继续原任务，不会从头开始。

对于复杂任务，Agent 可以按需多次查看目录、读取文件和搜索源码，再执行修改。读取文件只是调查步骤，不会阻止它继续完成任务。

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

新建一个 Python 文件（最好明确写出文件名）：

```powershell
python main.py --web --workspace "D:\Projects\empty-demo" --yes "新建 hello.py，文件内容为 print('hello world')。除此之外不要读取或修改其他文件。"
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
- 新建多行代码时使用逐行传输，避免网页 Markdown 破坏 `__name__` 等源码字符。
- 经你批准后运行指定 Python 文件，读取报错并继续修复验证。
- 运行固定的 Python `unittest` 测试命令。

它不能执行任意 Shell，不能删除、移动文件，不能安装依赖，也不能执行 Git 写操作。

## 权限和安全提示

- `--workspace` 决定它能看到哪些文件；不要把个人主目录或包含多个项目的大目录作为工作区。
- 成功读取的源码会通过网页发送给 DeepSeek。
- `--yes` 只自动批准读取。写入和运行测试仍需你在终端输入 `y`。
- `.env`、私钥、浏览器配置、日志、虚拟环境和常见凭据目录会被隐藏并拒绝读取。
- Python 文件和测试本质上是本机代码，只对你信任的项目批准运行。

完整威胁模型见 [SECURITY.md](SECURITY.md)。

## 常见问题

**我应该在 DeepSeek 网页里输入指令吗？**

不用。把指令放在 `python main.py ... "指令"` 的最后。程序会自动发送。

**为什么终端在等我？**

如果画面显示 `[y/N]`，程序正在等待你批准写文件或运行测试。查看上方预览后输入 `y` 或拒绝。

**为什么浏览器打开后没有继续？**

确认你已经在程序弹出的专用浏览器窗口里登录 DeepSeek，并且聊天输入框已经出现。不要关闭该窗口。

**为什么简单的新建文件任务反复扫描目录？**

请给出明确文件名，例如“新建 `hello.py`”，并尽量把 `--workspace` 指向一个小而明确的项目目录。像“写一个 `.py` 文档”这样的描述没有文件名，在包含多个项目和已有 Python 文件的大目录中容易产生歧义。

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
